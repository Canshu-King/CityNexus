"""D-2=甲 的落地读数：把 v3 那把门的**判级表**在真树上算一遍（现役侧本进程可比 ⇒ 能写"测得不等"）。

只读：不 checkout、不起产品/测试进程、不写任何被测文件；只印位置/长度/两侧指纹与布尔。
"""
from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = "D:/moodle/_qoder_integration_20260919"
GATE = Path("D:/moodle/_qoder_f_run/snap/cred_gate_v4.py")
TIP = "dea8410be809ebf6c5046581873584e9dbf32b64"
SNAP = Path("D:/moodle/_qoder_f_run/e_cred_a1cc0c1")   # 完整扫过的那棵树（6,898 路径）
OUT = Path("D:/moodle/_qoder_f_run/o225_receipts/cred_declared_sample_receipt_v4.json")

spec = importlib.util.spec_from_file_location("cred_gate_v4", GATE)
g = importlib.util.module_from_spec(spec)
sys.modules["cred_gate_v4"] = g
spec.loader.exec_module(g)

# 门的 `REPO` 是按 `__file__/parents[2]` 推的；从 `snap/` 里 import 会指到 `D:/moodle`
# ⇒ 扫描会读错树并**假绿**（我上一版 `shape_hits: 0` 就是这么来的）。显式钉回快照仓。
g.REPO = SNAP
assert (SNAP / ".git").exists(), f"SETUP：{SNAP} 不是仓 ⇒ 分母来路不对"


def ref_paths(ref: str) -> list[str]:
    out = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", ref],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    return [p for p in out.splitlines() if p.strip()]


def blob_of(ref: str, path: str) -> str:
    return subprocess.run(["git", "-C", REPO, "rev-parse", f"{ref}:{path}"],
                          capture_output=True, text=True).stdout.strip()


TIP_SCAN = Path("D:/moodle/_qoder_f_run/o225_receipts/cred_tip_scan_receipt_v4.json")
RUNLOG = Path("D:/moodle/_qoder_f_run/o225_receipts/cred_gate_v4_run_0923.txt")


def live_side_inside_pytest(live_here: int) -> dict:
    """为什么门自己在 pytest 里**永远**只能说 NOT_MEASURED：现役侧被 conftest 摘掉了。

    这不是我推测的：`_INHERITED_PROVIDER_ENV` 的名字从 conftest 正文里量出来，
    rc / passed 从真跑过的日志里量出来（两种调用形态都跑）。
    """
    import re

    cf = SNAP / "backend/tests/conftest.py"
    txt = cf.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"_INHERITED_PROVIDER_ENV = \((.*?)\)", txt, re.S)
    stripped = re.findall(r'"([A-Z0-9_]+)"', m.group(1)) if m else []
    overlap = [n for n in g.LIVE_CREDENTIAL_ENV_VARS if n in stripped]
    run: dict = {"path": str(RUNLOG), "present": RUNLOG.is_file()}
    if RUNLOG.is_file():
        body = RUNLOG.read_text(encoding="utf-8", errors="replace")
        run["sha256_12"] = hashlib.sha256(RUNLOG.read_bytes()).hexdigest()[:12]
        run["rc"] = dict(re.findall(r"(collect_rc|plain_rc|dash_s_rc)=(\d+)", body))
        run["passed_lines"] = re.findall(r"[0-9]+ passed[^\n]*", body)
        run["gate_reading"] = re.findall(r"cardinality[^\n]*", body)
    return {
        "conftest": "backend/tests/conftest.py",
        "strips_these_env": stripped,
        "of_which_are_live_credential_vars": overlap,
        "live_side_in_this_receipt_process": live_here,
        "consequence": (
            f"门在 pytest 里那一侧被摘成 0 把 ⇒ 等值列**恒**写 NOT_MEASURED（这是判据要求，不是缺陷）；"
            f"'与现役凭据测得不等'那一格只能由**门外**的本收据给出（本趟 {live_here} 把可比）。"
            if overlap and live_here
            else "现役侧未被摘除或本趟无可比凭据 ⇒ 见 live_side 那一格"),
        "pytest_run": run,
    }


REFUSAL = Path("D:/moodle/_qoder_f_run/o225_receipts/cred_gate_publish_refusal_0923.txt")
LANDED = {
    "evidence/cred-literals-f/cred_tip_scan_receipt_0923.json":
        Path("D:/moodle/_qoder_f_run/o225_receipts/cred_tip_scan_receipt.json"),
    "evidence/cred-literals-f/cred_declared_sample_receipt_0923.json":
        Path("D:/moodle/_qoder_f_run/o225_receipts/cred_declared_sample_receipt.json"),
    "evidence/cred-literals-f/cred_tip_scan_0923.py":
        Path("D:/moodle/_qoder_f_run/snap/cred_tip_scan.py"),
    "evidence/cred-literals-f/cred_declared_receipt_0923.py":
        Path("D:/moodle/_qoder_f_run/snap/cred_declared_receipt.py"),
}


def channel() -> dict:
    """门**本体**能不能进仲裁可读的那条线：不猜，抄发布器的拒绝原文（它是 fail-closed 的）。"""
    out = {"publisher": "publish_evidence_fixed.py → Canshu-King/CityNexus@commander/control",
           "gate_file_itself": "REFUSED —— 见 refusal_log",
           "refusal_log": {"path": str(REFUSAL), "present": REFUSAL.is_file()}}
    if REFUSAL.is_file():
        raw = REFUSAL.read_text(encoding="utf-8", errors="replace")
        out["refusal_log"]["sha256_12"] = hashlib.sha256(REFUSAL.read_bytes()).hexdigest()[:12]
        lines = [ln for ln in raw.splitlines() if "REFUSED" in ln]
        masked, n_masked = [], 0
        for ln in lines:
            keep = ln
            for pat in g.CREDENTIAL_PATTERNS:  # 用门自己的形状定义遮，不在这里复制一份判据
                keep, k = pat.subn("[已遮形]", keep)
                n_masked += k
            masked.append(keep)
        out["refusal_log"]["verbatim_rule"] = masked
        out["refusal_log"]["shapes_masked"] = n_masked
        out["refusal_log"]["local_only_because"] = (
            "这一份日志自己也带那枚占位样本 ⇒ 发布器同样会拒；遮了再发就等于改台账，"
            "所以它只留在本地，收据里存路径 + 摘要 + 被遮后的规则名")
        out["refusal_says_nothing_uploaded"] = any(
            "nothing uploaded" in ln for ln in raw.splitlines())
    out["landed_v3_generation"] = {
        repo: {"local_bytes": p.stat().st_size,
               "git_blob_sha1": subprocess.run(["git", "-C", REPO, "hash-object", "--no-filters",
                                                str(p)], capture_output=True,
                                               text=True).stdout.strip() if p.is_file() else None}
        for repo, p in LANDED.items()}
    out["note"] = ("v4 那一代落在同前缀的 `_v4` 文件名上（发布不覆盖已进收据的路径）。"
                   "拒绝**不是**我把内容削了去迎合闸门：占位样本 `sk-aaaa…` 是 test_2 的自证材料，"
                   "删了它 test_2 就测不到'占位必须放过'。要不要为它开一格具名例外，由 commander 裁。")
    return out


def tip_wide(ref_listing_total: int) -> dict:
    """全尖总数**不手写**：能读到对象库那把的收据就转述它的计数，读不到才写 NOT_MEASURED。"""
    if not TIP_SCAN.is_file():
        return {"status": "NOT_MEASURED",
                "why": f"对象库那把的收据还没落盘（{TIP_SCAN}）⇒ 我不报数；"
                       f"已知分母：{TIP_SCAN.name} 那尖的 ls-tree 全量 = {ref_listing_total} 路径",
                "denominators_known": {"ref_listing_at_a1cc0c1": ref_listing_total}}
    t = json.loads(TIP_SCAN.read_text(encoding="utf-8"))
    scope, denom = t.get("scope", {}), t.get("denominator", {})
    return {
        "status": "MEASURED" if not scope.get("truncated_limit") else "TRUNCATED_SMOKE_ONLY",
        "source_receipt": {"path": str(TIP_SCAN),
                           "sha256_12": hashlib.sha256(TIP_SCAN.read_bytes()).hexdigest()[:12],
                           "instrument_blob": (t.get("gate_file") or {}).get("git_blob_sha1")},
        "exact_ref": scope.get("resolved_sha"), "tree": scope.get("tree"),
        "denominator": denom,
        "shape_hits": t.get("shape_hits"), "by_verdict": t.get("by_verdict"),
        "classification": t.get("classification"),
        "note": "转述自对象库直读那把（`cred_tip_scan.py`）：路径来自 `ls-tree -r`，"
                "字节来自 `cat-file --batch` ⇒ 与工作树是否脏、快照导出缺哪 52 个路径无关",
    }


def main() -> int:
    paths = g.tracked_files()                 # 射程：**与门自己那一把完全同源**（快照仓 ls-files）
    live = g.live_credentials()
    offenders = g.scan_paths(paths)
    rows = g.classify_offenders(offenders, live, len(paths))
    # 快照导出 vs `a1cc0c1` 那一尖的路径差（少测的那批几乎全是 `review/evidence/**` 的补丁/收据）
    listed = ref_paths("a1cc0c1")
    missing = sorted(set(listed) - set(paths))
    E2E = "frontend/e2e/qoder-e2e-config-guard.spec.ts"
    e2e_a, e2e_t = blob_of("a1cc0c1", E2E), blob_of(TIP, E2E)
    # 现役侧那一把与旧 blob 的关系（今天已证：`c0d7e3d`/`b12f24f` 那一行 == 现役那把）
    equalities = {}
    for ref in ("c0d7e3d", "13377d3", TIP):
        path = "qoder-handoff/qoder_xiaomi_truth_hardening_v6.patch"
        blob = blob_of(ref, path)
        raw = subprocess.run(["git", "-C", REPO, "show", f"{ref}:{path}"],
                             capture_output=True).stdout
        txt = raw.decode("utf-8", "replace")
        hits = g.find_credential_shapes(txt)
        fps = {h[3] for h in hits}
        equalities[ref] = {"path": path, "blob_sha1": blob or None, "bytes": len(raw),
                           "shape_hits": len(hits),
                           "fingerprints": sorted(fps),
                           "equals_live_credential": (
                               "NO_BLOB_AT_REF" if not blob
                               else "NOT_MEASURED" if not live
                               else True if fps & {c["fp"] for c in live} else False)}

    verdicts = {}
    for r in rows:
        verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
    receipt = {
        "ruling": "D-2 = 甲（commander 494abfd7 @2026-09-23 18:5x）：具名声明 + 指纹列，不修桩、不缩射程",
        "lane": "F 8ccd71d8",
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "gate_file": {"path": str(GATE), "bytes": GATE.stat().st_size,
                      "git_blob_sha1": subprocess.run(["git", "-C", REPO, "hash-object", "--no-filters", str(GATE)],
                                                      capture_output=True, text=True).stdout.strip(),
                      "ref_pinned_on": "refs/heads/gates/credential-literals-20260923 @ 9cdaf6c（父 83c6ea0，其父 7d86f49 → 12b7dd2；未推）"},
        "scan_side": {
            "paths_scanned": len(paths), "shape_hits": len(offenders),
            "denominator_source": "快照仓 `git ls-files`（与门内 test_1 同一函数 ⇒ 一个分母，两个读数）",
            "tree": ("D:/moodle/_qoder_f_run/e_cred_a1cc0c1 @ 1bfe232 =「a1cc0c1 的 git archive 导出"
                     "＋门自己那一枚仪器」，未推；工作树里唯一改动就是该仪器文件"),
            "not_scanned_vs_ref": {
                "ref_listing_total": len(listed),
                "snapshot_total": len(paths),
                "missing_count": len(missing),
                "missing_by_extension": {s: sum(1 for m in missing if Path(m).suffix.lower() == s)
                                        for s in sorted({Path(m).suffix.lower() for m in missing})},
                "missing_list": missing,
                "consequence": (f"这 {len(missing)} 个路径在快照里根本没有 ⇒ 本收据的 {len(paths)} "
                                "**不是**全尖分母；其中含 `review/evidence/**.patch`（当年漏的形状"
                                f"就在那类文件里）⇒ 全尖总数另由对象库直读那把给出，见 tip_wide_*"),
            },
        },
        "live_side": {"credentials_found": len(live), "detail": live,
                      "meaning": "只取 env 里的长度与指纹（`app/core/config.py:22-23,53` 那三把），绝不印值"},
        "classification": rows,
        "by_verdict": verdicts,
        "historical_blob_equality": equalities,
        "self_proofs": {
            "declarations_match_by_digest_not_path": "test_2d 面②：改桩 ⇒ 指纹不吻合 ⇒ 声明作废并红",
            "undeclared_hit_is_red": "test_2d 面①/面⑤ + test_3 第三处承重（把判级换成一律放过 ⇒ 该格抓住）",
            "equality_side_this_run": {
                "live_credentials_in_env": len(live),
                "values_of_equals_live_credential": sorted({str(r["equals_live_credential"])
                                                           for r in rows}),
                "reading": ("现役侧有值 ⇒ 该列是**测得**的布尔；现役侧为空 ⇒ 只能写 NOT_MEASURED"
                            "（test_2d 面④钉这条）"),
            },
        },
        "live_side_inside_pytest": live_side_inside_pytest(len(live)),
        "channel": channel(),
        "tip_wide_total": tip_wide(len(listed)),
        "cross_check": {"path": E2E,
                        "blob_at_a1cc0c1": e2e_a, "blob_at_tip": e2e_t,
                        "identical": e2e_a == e2e_t,
                        "meaning": "同一枚 blob ⇒ 那一处具名声明在两尖都成立（不是只对旧树成立）"},
        "print_policy": "只印位置/长度/摘要/布尔/计数；原文、前缀、env 值一律不印",
    }
    # 只测**非空**值：空串 `in` 任何字节流都成立，"没值"会被读成"值泄了"（我第一版就假命中在这）
    to_test = {n: v for n in g.LIVE_CREDENTIAL_ENV_VARS if (v := os.environ.get(n) or "")}
    text = json.dumps(receipt, ensure_ascii=False, indent=1)
    leaked = [n for n, v in to_test.items() if v.encode("utf-8") in text.encode("utf-8")]
    shapes = g.find_credential_shapes(text)
    receipt["leak_guard"] = {"values_tested": len(to_test), "matches_found": leaked,
                             "credential_shaped_tokens_in_this_receipt": len(shapes),
                             "note": "只测非空值；空串对 `in` 恒真是假命中，第一版就在这自暴过一次。"
                                     "另外用门自己的形状判据反扫这份收据——发布器拒收门本体就是"
                                     "因为那枚占位样本，这份收据必须自证一格不带"}
    text = json.dumps(receipt, ensure_ascii=False, indent=1)
    leaked = [n for n, v in to_test.items() if v.encode("utf-8") in text.encode("utf-8")]
    shapes = g.find_credential_shapes(text)
    receipt["leak_guard"]["credential_shaped_tokens_in_this_receipt"] = len(shapes)
    if leaked:
        print(f"REFUSE：序列化结果里出现 {leaked} 的原文 ⇒ 不落盘")
        return 3
    if shapes:
        print(f"REFUSE：收据里还留着 {len(shapes)} 个凭据形状 "
              f"{[(s[0], s[2]) for s in shapes]}（只印行号与长度）⇒ 不落盘")
        return 4
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    print(f"\nWROTE {OUT} ({OUT.stat().st_size} B, sha256[:12]="
          f"{hashlib.sha256(OUT.read_bytes()).hexdigest()[:12]}) 含原文={leaked}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
