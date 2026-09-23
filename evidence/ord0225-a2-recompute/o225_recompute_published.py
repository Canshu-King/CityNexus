"""ORD-0225 · 对 **published 件**复算（lane F，2026-09-23 12:4x）

commander 令：用我自己那把尺对已发布证据复算，再定 ORD-0225 能不能从 STREAK_GREEN 往上走。
本脚本**不跑任何产品/门进程**，只做三件事：
  1) 从 C 发布的**原始轮次**独立派生 Y3 结论（killed / control_green / deterministic_kill /
     all_restores_clean / campaign_valid），与 C 自己声明的 verdict 逐字段比 —— 不一致就是发现；
  2) 用**两把不同世代的尺**（C 量测时那枚 blob vs 我现在 composite 里那枚）对同一份 10 轮
     连击收据再判一次，看 verdict 串与等级是否随尺漂移；
  3) 把派生结果写成 `CNX_REVERSE_MUTATION_RECEIPT_V1` 形状，`derived_result` 由本 verifier 填。
"""
from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "D:/moodle/_qoder_integration_20260919"
A2 = Path("D:/moodle/_qoder_f_run/o225_receipts/a2")
RULERS = {  # 两个世代都用真 blob，不复制实现
    "measure_time_c_blob_ebe4e24c177d8e18": "ebe4e24c177d8e18",
    "current_f_blob_fcf76941dcc25127": "fcf76941dcc25127",
}
Y3_FILES = {
    "HTTP 门（A-2 形状，两真 uvicorn + HTTP）": "xproc_y3_rounds_http_2ab69f2.json",
    "进程内 g3 门（ORD-0225 现 scope 那一枚）": "xproc_y3_rounds_raw_test_g3_concurrent_open_ge_2ab69f2.json",
}
STREAK_FILE = "streak_xproc_http_2ab69f2.json"
DECL = ("复算：不新起任何子进程；逐字引用已发布收据的 runs/rounds 字段；"
        "无 sleep/重试/退避/降并发/放宽断言")


def sha12(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:12]


def blob(oid: str) -> bytes:
    return subprocess.run(["git", "-C", REPO, "cat-file", "blob", oid], capture_output=True).stdout


def load_ruler(oid: str, tag: str):
    data = blob(oid)
    assert data, f"blob {oid} 读不到"
    p = Path(tempfile.mkdtemp(prefix="o225ruler_")) / "_qoder_streak_receipt.py"
    p.write_bytes(data)
    spec = importlib.util.spec_from_file_location(f"_cnx_shared_{tag}", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.__cnx_bytes__ = len(data)
    mod.__cnx_sha12__ = sha12(data)
    return mod


def derive_y3(d: dict) -> dict:
    """只从原始轮次派生，不看 C 的 verdict。"""
    rounds = [r for r in d["rounds"] if r.get("mutated")]
    control = d.get("control_round") or {}
    seq = [("R" if (r.get("node_outcome") or "").upper().startswith("R") else
            "G" if (r.get("node_outcome") or "").upper().startswith("G") else "?") for r in rounds]
    killed = sum(1 for s in seq if s == "R")
    # 只有突变轮才有"复原"这一步：控制轮没有装过突变，它不带 restore 字段。
    # 把控制轮折进来会让 all() 永远 False —— 那是我这台验算器的错，不是车道的错。
    mr = [r for r in d["rounds"] if r.get("mutated")]
    def tri(vals: list):
        """True / False / NOT_MEASURED（缺读数不许当 False，也不许当 True）"""
        have = [v for v in vals if isinstance(v, bool)]
        if not have:
            return "NOT_MEASURED"
        return all(have)
    restored = tri([r.get("restored_sha_matches") for r in mr])
    markers = tri([r.get("no_mutant_marker_left") for r in mr])
    anchors = {str(r.get("anchor")) for r in mr}
    return {
        "scope": {"exact_sha": d.get("sha"), "target_nodeid": d.get("node"), "run_shape": d.get("run_shape"),
                  "mutant": d.get("mutant"), "command": d.get("command")},
        "rounds": len(rounds),
        "killed": killed,
        "green_under_mutant": sum(1 for s in seq if s == "G"),
        "sequence": "".join(seq),
        "control_green": (control.get("node_outcome") or "").upper().startswith("G"),
        "deterministic_kill": killed == len(rounds) and len(rounds) > 0,
        "all_restores_clean": ("NOT_MEASURED" if "NOT_MEASURED" in (restored, markers)
                               else bool(restored) and bool(markers)),
        "restore_fields": {"restored_sha_matches": restored, "no_mutant_marker_left": markers,
                           "mutated_rounds_carrying_them": len(mr)},
        "anchor_hits_distinct_values": sorted(anchors)[:3],
        "campaign_valid": bool((control.get("node_outcome") or "").upper().startswith("G")) and killed == len(rounds),
        "derived_result": "KILLED" if (bool((control.get("node_outcome") or "").upper().startswith("G"))
                                       and killed == len(rounds)) else "NOT_KILLED",
    }


def main() -> int:
    out: dict = {"order": "ORD-0225 · 对 published 件复算", "lane": "F 8ccd71d8",
                 "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                 "no_children_started": True,
                 "print_policy": "只印坐标/计数/布尔；不印任何凭据"}
    problems: list[str] = []

    # ① 两份 Y3 原始轮次：独立派生 + 与声明比
    derived: dict = {}
    for label, fn in Y3_FILES.items():
        p = A2 / fn
        d = json.loads(p.read_text(encoding="utf-8"))
        dv = derive_y3(d)
        declared = d.get("verdict") or {}
        cmp_ = {}
        for k in ("rounds", "killed", "deterministic_kill", "control_green", "all_restores_clean", "campaign_valid"):
            mine, theirs = dv.get(k), declared.get(k)
            cmp_[k] = {"derived_by_verifier": mine, "declared_by_lane": theirs, "agree": mine == theirs}
            if mine != theirs:
                problems.append(f"{fn}:{k} 派生 {mine!r} ≠ 声明 {theirs!r}")
        derived[label] = {"file": fn, "bytes": p.stat().st_size, "sha256_12": sha12(p.read_bytes()),
                          "blob_git": subprocess.run(
                              ["git", "-C", REPO, "hash-object", str(p)], capture_output=True,
                              text=True, encoding="utf-8").stdout.strip(),
                          "derived": dv, "compare_with_declared": cmp_}
    out["y3_recomputed"] = derived

    # ② 两把尺对同一份连击收据再判
    s = json.loads((A2 / STREAK_FILE).read_text(encoding="utf-8"))
    v = s["verdict"] if isinstance(s.get("verdict"), dict) else {}
    cross = {"file": STREAK_FILE, "bytes": (A2 / STREAK_FILE).stat().st_size,
             "sha": s.get("sha"), "target_nodeid": s.get("target_nodeid"), "run_shape": s.get("run_shape"),
             "rounds": s.get("rounds"), "stored_verdict_from_lane": v.get("verdict"),
             "stored_grade": v.get("closure_grade"),
             "shared_module_recorded_in_receipt": s.get("shared_module"),
             "per_ruler": {}}
    for tag, oid in RULERS.items():
        r = load_ruler(oid, tag[-6:])
        res = r.streak_verdict(
            runs=s["runs"], rounds=s["rounds"], sha=s["sha"], target_nodeid=s["target_nodeid"],
            run_shape=s["run_shape"], command=s["command"], independence_declared=True,
            clause6_declared=DECL,
            clause6_command_surface_clean=bool(s.get("clause6_command_surface_clean")),
            clause6_command_surface_hits=s.get("clause6_command_surface_hits") or [],
            run_shape_verified=bool((s.get("run_shape_verification") or {}).get("run_shape_verified")),
            run_shape_problems=(s.get("run_shape_verification") or {}).get("problems") or [],
            reverse_mutation_required=True, reverse_mutation_result="")
        res_killed = r.streak_verdict(
            runs=s["runs"], rounds=s["rounds"], sha=s["sha"], target_nodeid=s["target_nodeid"],
            run_shape=s["run_shape"], command=s["command"], independence_declared=True,
            clause6_declared=DECL,
            clause6_command_surface_clean=bool(s.get("clause6_command_surface_clean")),
            clause6_command_surface_hits=s.get("clause6_command_surface_hits") or [],
            run_shape_verified=bool((s.get("run_shape_verification") or {}).get("run_shape_verified")),
            run_shape_problems=(s.get("run_shape_verification") or {}).get("problems") or [],
            reverse_mutation_required=True, reverse_mutation_result="KILLED")
        cross["per_ruler"][tag] = {
            "ruler_bytes": r.__cnx_bytes__, "ruler_sha256_12": r.__cnx_sha12__, "ruler_blob": oid,
            "verdict": str(res.get("verdict")), "closure_grade": str(res.get("closure_grade")),
            "green": res.get("green"), "red": res.get("red"), "not_observed": res.get("not_observed"),
            "duplicate_db_paths": res.get("duplicate_db_paths"),
            "runs_missing_fields": res.get("runs_missing_fields"),
            "every_run_fresh": (res.get("checks") or {}).get("every_run_fresh"),
            "problems": res.get("problems"),
            "若把 derived_result=KILLED 递进来则等级": str(res_killed.get("closure_grade")),
        }
    tags = list(cross["per_ruler"])
    same = all(cross["per_ruler"][tags[0]][k] == cross["per_ruler"][t][k]
               for t in tags for k in ("verdict", "closure_grade", "green", "red", "every_run_fresh"))
    cross["两把尺同判"] = same
    if not same:
        problems.append("同一份 runs 在两枚尺世代上判得不一样 ⇒ 结论随尺漂移，必须点名哪一枚签")
    for t in tags:  # 与车道存的 verdict 比
        if cross["per_ruler"][t]["verdict"] != cross["stored_verdict_from_lane"]:
            problems.append(f"{t}: 再判 verdict={cross['per_ruler'][t]['verdict']!r} ≠ 收据存的 "
                            f"{cross['stored_verdict_from_lane']!r}")
    out["streak_cross_recompute"] = cross

    # ③ V1 形状的反向突变收据（derived_result 由本 verifier 派生）
    http = derived["HTTP 门（A-2 形状，两真 uvicorn + HTTP）"]["derived"]
    inner = derived["进程内 g3 门（ORD-0225 现 scope 那一枚）"]["derived"]
    out["reverse_mutation_receipt_V1"] = {
        "schema": "CNX_REVERSE_MUTATION_RECEIPT_V1",
        "verifier": "lane F 8ccd71d8（本脚本，从已发布原始轮次派生；未起任何子进程）",
        "claims": [
            {"scope": http["scope"], "derived_result": http["derived_result"],
             "direct_red_nodeids": [http["scope"]["target_nodeid"]] if http["deterministic_kill"] else [],
             "collateral_red_nodeids": [],
             "basis": {k: http[k] for k in ("rounds", "killed", "control_green", "deterministic_kill",
                                            "all_restores_clean", "campaign_valid", "sequence")}},
            {"scope": inner["scope"], "derived_result": inner["derived_result"],
             "direct_red_nodeids": [], "collateral_red_nodeids": [],
             "basis": {k: inner[k] for k in ("rounds", "killed", "green_under_mutant", "control_green",
                                             "deterministic_kill", "all_restores_clean", "campaign_valid",
                                             "sequence")}},
        ],
        "not_comparable_note": ("两条 claim 的 exact_sha 相同（2ab69f2）而 nodeid+run_shape 不同 ⇒ "
                                "killed 计数不得相减/不得互借；跨 shape 写 "
                                "NOT_COMPARABLE_AS_REGRESSION_DELTA"),
        "control_green_required_first": True,
    }

    out["problems"] = problems
    out["verdict_of_this_recompute"] = (
        "OK：派生与声明逐字段一致，两把尺同判" if not problems else f"发现 {len(problems)} 处不一致")
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    fp = Path("D:/moodle/_qoder_f_run/o225_receipts/o225_recompute_published_a2.json")
    fp.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"\nWROTE {fp} ({fp.stat().st_size} B, sha256[:12]={sha12(fp.read_bytes())})")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
