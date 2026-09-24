"""ORD-0282 第一段：独立取树 + 逐字节核对 + 落地代到底有没有那一格（先量，不猜）。

判据 ①：自己 GET 镜像尖（必须 == 45b0a5e2…），从 GitHub tarball 干净导出，不用任何车道工作树。
这一段只回答三件事：
  A 尖/提交/tree 各是多少，我的候选代 7c806fa 与它是什么祖先关系；
  B 落地代那两件（main.py / 0272 门文件）的 blob 是多少，与命令里点名的期望值对不对得上；
  C 落地代树里到底有没有 `_fill_plan_generation_receipts`（缝）与 `test_G9`（那一格）——
    有 ⇒ 第二段跑两进程 rig；没有 ⇒ 只能按判据 ④ 的第三态记，并把差异写清。
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUN = Path("D:/moodle/_qoder_f_run")
RCP = RUN / "o225_receipts"
TIP_EXPECT = "45b0a5e281cae9c37715173afd3ac5778f309ca7"
CAND = "7c806fab58e872060cb5811ff96c770b40dad165"
MAIN_BEFORE = "416ea4f210e967130710a900cdecd20e7a1b5eca"
GATE_CAND_BLOB = "799fbd2fe9d28433405408ddec1d7405b2d1c9d9"
R3_BLOB = "fc35335aadffb8f0de6f8030e9fc5a747f24f463"
GR = "Canshu-King/CityNexus"
BRANCH = "mirror/integration-frontend-apple-pass1"
EXPORT = RUN / "e_0282_45b0a5e"
TARBALL = RUN / "o282_landed.tar.gz"
OUT = RCP / "ord0282_phase1_landing_tree.json"
TOK = Path(r"D:/moodle/_qoder_recovery_20260919/.api_tok_20260920").read_text(encoding="utf-8").strip()
HDRS = {"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
        "User-Agent": "citynexus-lane-f"}
PATHS = ["backend/app/main.py", "backend/tests/test_qoder_ord0272_continuation.py",
         "backend/app/schemas.py", "contracts/openapi.yaml",
         "live_checks/audit_closure_coordinates_r3.py"]


def get(path, raw=False, tries=6):
    for a in range(tries):
        try:
            req = urllib.request.Request("https://api.github.com" + path)
            for k, v in HDRS.items():
                req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read()
                return (body, None) if raw else (json.loads(body.decode()), None)
        except Exception as exc:  # noqa: BLE001
            print("  GET retry", a + 1, type(exc).__name__, str(exc)[:70])
            time.sleep(2 + 2 * a)
    return None, "exhausted"


def blob_of(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def contents_at(ref, p):
    meta, err = get(f"/repos/{GR}/contents/{p}?ref={ref}")
    if not isinstance(meta, dict) or "sha" not in meta:
        return {"path": p, "blob": None, "why": str(err or meta)[:90]}
    return {"path": p, "blob": meta["sha"], "bytes": meta["size"], "type": meta.get("type")}


def main() -> int:
    began = datetime.now().astimezone().isoformat(timespec="seconds")
    ref, err = get(f"/repos/{GR}/git/ref/heads/{BRANCH}")
    tip = ((ref or {}).get("object") or {}).get("sha")
    print(f"[①] 镜像尖先读 {tip}  期望 {TIP_EXPECT}  相等 {tip == TIP_EXPECT}")
    assert tip == TIP_EXPECT, f"SETUP：尖不是命令里那枚 ⇒ 停，不换目标继续跑（读到 {tip}）"

    commit, _ = get(f"/repos/{GR}/git/commits/{TIP_EXPECT}")
    parents = [p["sha"] for p in commit.get("parents", [])]
    anc = get(f"/repos/{GR}/compare/{CAND}...{TIP_EXPECT}")[0] or {}
    print("[①] tree", commit["tree"]["sha"], "parents", parents)
    print("[①] compare 7c806fa...45b0a5e2 status", anc.get("status"),
          "ahead_by", anc.get("ahead_by"), "behind_by", anc.get("behind_by"))

    blobs = {p: contents_at(TIP_EXPECT, p) for p in PATHS}
    for p, v in blobs.items():
        print("  blob", p[:56], v.get("blob"), v.get("bytes"))

    # tarball 独立导出（codeload 走重定向）
    if TARBALL.exists():
        TARBALL.unlink()
    got = None
    for a in range(4):
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{GR}/tarball/{TIP_EXPECT}")
            for k, v in HDRS.items():
                req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=600) as r:
                got = r.read()
            break
        except Exception as exc:  # noqa: BLE001
            print("  TARBALL retry", a + 1, type(exc).__name__, str(exc)[:70])
            time.sleep(3 + 3 * a)
    assert got, "SETUP：tarball 取不到"
    TARBALL.write_bytes(got)
    print(f"[①] tarball {len(got):,} B sha256[:16] {hashlib.sha256(got).hexdigest()[:16]}")
    if EXPORT.exists():
        import shutil
        shutil.rmtree(EXPORT)
    EXPORT.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(got), mode="r:gz") as tf:
        roots = {n.name.split("/")[0] for n in tf.getmembers()}
        tf.extractall(EXPORT)
    inner = next(EXPORT.glob("*"))
    print("[①] 解包根", sorted(roots), "->", inner.name)

    def picked(rel):
        p = inner / rel
        return p if p.is_file() else None

    inv = {}
    for p in PATHS:
        f = picked(p)
        if f is None:
            inv[p] = {"in_export": False}
            continue
        b = f.read_bytes()
        api_blob = blobs[p].get("blob")
        inv[p] = {"in_export": True, "bytes": len(b), "export_blob_40": blob_of(b),
                  "api_blob_40": api_blob, "equal": api_blob == blob_of(b)}
        print("  核对", p[:56], "导出==提交:", inv[p]["equal"], f"{len(b):,} B")

    seam = {"symbol": "_fill_plan_generation_receipts",
            "hits_in_main": [], "count": 0}
    guard = {"symbol": "IdempotencyKey.response_json.is_(None)", "hits_in_main": [], "count": 0}
    g9 = {"symbol": "test_G9", "hits": [], "count": 0}
    mf = picked("backend/app/main.py")
    if mf:
        for i, line in enumerate(mf.read_text(encoding="utf-8").splitlines(), 1):
            if seam["symbol"] in line:
                seam["hits_in_main"].append(i)
            if guard["symbol"] in line:
                guard["hits_in_main"].append(i)
        seam["count"] = len(seam["hits_in_main"])
        guard["count"] = len(guard["hits_in_main"])
    gf = picked("backend/tests/test_qoder_ord0272_continuation.py")
    if gf:
        for i, line in enumerate(gf.read_text(encoding="utf-8").splitlines(), 1):
            if g9["symbol"] in line:
                g9["hits"].append(i)
        g9["count"] = len(g9["hits"])
    tests_present = sorted(f.name for f in (inner / "backend/tests").glob("test_qoder_ord027*"))
    print("[C] 缝出现次数", seam["count"], "守卫行", guard["hits_in_main"], "test_G9 行", g9["hits"])
    print("[C] 0272 相关门文件", tests_present)

    r3 = picked("live_checks/audit_closure_coordinates_r3.py")
    r3_check = {"expected_blob_40": R3_BLOB,
                "export_blob_40": blob_of(r3.read_bytes()) if r3 else None,
                "equal": bool(r3) and blob_of(r3.read_bytes()) == R3_BLOB,
                "bytes": r3.stat().st_size if r3 else None}
    print("[⑥] r3 尺指纹", r3_check)

    receipt = {"what": "ORD-0282 第一段：落地代 45b0a5e2 独立导出 + 那一格在不在（先量的部分）",
               "lane": "F 8ccd71d8", "began_at": began,
               "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
               "criterion_1_tree": {"branch": BRANCH, "mirror_tip_first_read": tip,
                                    "expected": TIP_EXPECT, "equal": tip == TIP_EXPECT,
                                    "commit_tree": commit["tree"]["sha"], "parents": parents,
                                    "candidate_ancestry": {"candidate": CAND, "status": anc.get("status"),
                                                           "ahead_by": anc.get("ahead_by"),
                                                           "behind_by": anc.get("behind_by")},
                                    "source": "GitHub tarball（api.github.com/repos/…/tarball/<sha>，重定向到 codeload）",
                                    "tarball_bytes": len(got),
                                    "tarball_sha256_16": hashlib.sha256(got).hexdigest()[:16],
                                    "export_dir": str(inner),
                                    "lane_worktrees_used": [],
                                    "commander_export_reused": False},
               "criterion_1b_byte_proof": inv,
               "expected_blob_checks": {
                   "main_py_landed_before_blob": {"expected": MAIN_BEFORE,
                                                  "observed": blobs["backend/app/main.py"].get("blob"),
                                                  "equal": blobs["backend/app/main.py"].get("blob") == MAIN_BEFORE},
                   "gate_file_candidate_blob": {"candidate_7c806fa": GATE_CAND_BLOB,
                                               "landed": blobs["backend/tests/test_qoder_ord0272_continuation.py"].get("blob"),
                                               "same": GATE_CAND_BLOB == blobs["backend/tests/test_qoder_ord0272_continuation.py"].get("blob")}},
               "criterion_3_landing_symbols": {"seam": seam, "guard_line": guard,
                                               "g9_cell": g9, "ord0272_test_files": tests_present},
               "criterion_6_second_observer_prereq": r3_check,
               "discipline": {"demo_reset_calls": 0, "user_dbs_touched": [],
                              "credentials_printed": 0, "refs_written": 0,
                              "lane_worktrees_used": 0}}
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("WROTE", OUT, OUT.stat().st_size, "B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
