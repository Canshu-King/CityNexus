"""ORD-0204 重钉 @13377d3（SESSION=d2305848）。

前任在 tree8(=2c2621e) 断掉前：a/c/d KILLED，(b) 因驱动锚点仍是旧字串 NOT_ANSWERED
而 anchor_hits=0 → HARNESS_INVALID。本驱动在 tree9(=13377d3) 上按内容重定锚，
四个靶 + (b) 三臂一次跑完。

判定口径沿用 harness：只有红的正是 EXPECTED_KILLER 那条断言才算 KILLED；
collected 必须与 failed+passed+skipped 对得上；每次突变后逐字节还原并自证。

用法：D:/moodle/CityNexus/.venv/Scripts/python.exe raw/d2305848_ord0204_tree9.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TREE = Path(os.environ.get("REDTEAM_TREE", str(HERE.parent / "tree9"))).resolve()
BACKEND = TREE / "backend"
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
OUT = HERE / "d2305848_ord0204_tree9.json"

CAP = BACKEND / "app" / "anywhere_capability.py"
MAIN = BACKEND / "app" / "main.py"

GATE_HARD_GAP = "tests/test_qoder_mobility_hard_gap.py"
GATE_LEG = "tests/test_qoder_provider_identity_leg.py"
GATE_REPLAN = "tests/test_qoder_mobility_replan_endpoint.py"
SUITE = [GATE_HARD_GAP, GATE_LEG, GATE_REPLAN]

KILLER_G17 = "test_g17_the_new_cell_keeps_the_pair_that_stops_it_being_a_vague_fourth_string"

A_OLD = "        hard_gaps.append(GAP_MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE)\n"
A_NEW = "        pass  # MUTANT-0204a: the named hard gap is never emitted\n"

B_OLD = '        "retryable": bool(resolution.retryable) or verdict == UNKNOWN_RETRYABLE,\n'
B_NEW = '        "retryable": bool(resolution.retryable),\n'

C_OLD = '        http_status = None\n        source_layer = "TRANSPORT"\n'
C_NEW = '        http_status = 0\n        source_layer = "TRANSPORT"\n'

D_OLD = '    reason_code = "MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE"\n'
D_NEW = '    reason_code = "MOBILITY_DATA_UNAVAILABLE"\n'

# b 臂①: 摘一条上游 retryable=True（传输失败站点，六行块全文件唯一）
UP_OLD_FULL = '''            method="provider_error",
            state="RUNTIME_FAILURE",
            reason_code=REASON_RESOLVER_UNAVAILABLE,
            retryable=True,
            resolver_attempted=True,
            resolver_status=status,
'''
UP_NEW_FULL = UP_OLD_FULL.replace("retryable=True,", "retryable=False,")

CASES = [
    {
        "key": "a",
        "file": "cap",
        "old": A_OLD,
        "new": A_NEW,
        "what": "hard_gaps.append(GAP_MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE) 不再发射（anywhere_capability.py）",
        "expected_killer": "test_a_frozen_only_mobility_axis_names_the_gap_and_stays_hydratable",
    },
    {
        "key": "b",
        "file": "cap",
        "old": B_OLD,
        "new": B_NEW,
        "what": "拆掉 or verdict == UNKNOWN_RETRYABLE 联动（改名后新字串）",
        "expected_killer": KILLER_G17,
        "note": "契约 M17 登记为预期幸存者；存活⇒与 M17 一致，不是新洞",
    },
    {
        "key": "c",
        "file": "cap",
        "old": C_OLD,
        "new": C_NEW,
        "what": "transport 分支 http_status None -> 0",
        "expected_killer": "test_g16_the_four_attribution_fields_arrive_together_or_not_at_all",
    },
    {
        "key": "d",
        "file": "main",
        "old": D_OLD,
        "new": D_NEW,
        "what": "replan 具名 reason_code 退回泛称",
        "expected_killer": "test_ord199_a_leg_whose_only_number_is_the_fixture_constant_says_so",
    },
]

B_ARMS = [
    {
        "key": "b-arm2-upstream-only",
        "mutations": [("cap", UP_OLD_FULL, UP_NEW_FULL)],
        "note": "只摘一条上游（传输失败站点）retryable=True→False；1457/1473 联动应救回 ⇒ 期望绿",
    },
    {
        "key": "b-arm3-both",
        "mutations": [("cap", UP_OLD_FULL, UP_NEW_FULL), ("cap", B_OLD, B_NEW)],
        "expected_killer": KILLER_G17,
        "note": "两处同时摘 ⇒ g17 应红（证明该不变量由这一对共同守着）",
    },
]

NODE_RE = re.compile(r"^(?:FAILED|ERROR)\s+(\S+)::(\S+)", re.M)
COUNT_RE = re.compile(r"(\d+)\s+(passed|failed|error|errors|skipped)")


def run_suite(extra_suite: list[str] | None = None) -> dict:
    env = dict(os.environ)
    for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_MODEL", "CITYNEXUS_AI_API_KEY"):
        env.pop(k, None)
    env["CITYNEXUS_DEMO_MODE"] = "true"
    env["CDSA_PORT"] = ""
    env["CITYNEXUS_AI_ENABLED"] = "false"
    env["PYTHONIOENCODING"] = "utf-8"
    suite = extra_suite or SUITE
    p = subprocess.run(
        [str(PYTHON), "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", "-rf", *suite],
        cwd=str(BACKEND), capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=1800,
    )
    out = (p.stdout or "") + (p.stderr or "")
    nodes = [f"{m.group(1)}::{m.group(2)}" for m in NODE_RE.finditer(out)]
    counts = {m.group(2): int(m.group(1)) for m in COUNT_RE.finditer(out)}
    mc = re.search(r"(\d+)\s+tests? collected", out)
    if mc:
        collected = int(mc.group(1))
    else:
        collected = sum(counts.get(k, 0) for k in ("passed", "failed", "error", "errors", "skipped"))
    return {"rc": p.returncode, "nodes": nodes, "counts": counts, "collected": collected, "tail": out[-600:]}


def apply_and_run(muts: list[tuple[str, str, str]], expected_killer: str | None = None) -> dict:
    files = {"cap": CAP, "main": MAIN}
    originals = {k: f.read_bytes() for k, f in files.items()}
    rec: dict = {}
    try:
        text_by_key = {k: b.decode("utf-8") for k, b in originals.items()}
        rec["anchor_hits"] = {m[1][:40]: text_by_key[m[0]].count(m[1]) for m in muts}
        if any(v != 1 for v in rec["anchor_hits"].values()):
            rec["verdict"] = "HARNESS_INVALID (anchor hits != 1)"
            return rec
        cur = text_by_key
        for key, old, new in muts:
            cur[key] = cur[key].replace(old, new)
        for key, text in cur.items():
            files[key].write_bytes(text.encode("utf-8"))
        res = run_suite()
        rec["observed"] = {k: res[k] for k in ("rc", "counts", "collected", "nodes")}
        rec["tail"] = res["tail"]
        if expected_killer:
            killer_red = any(expected_killer in n for n in res["nodes"])
            others = [n for n in res["nodes"] if expected_killer not in n]
            c = res["counts"]
            collected_ok = res["collected"] is not None and c.get("failed", 0) + c.get("passed", 0) + c.get("skipped", 0) + c.get("error", 0) + c.get("errors", 0) == res["collected"]
            if killer_red:
                rec["verdict"] = "KILLED" if collected_ok else "KILLED_UNVERIFIED (计数对不上)"
            elif not res["nodes"] and res["rc"] == 0:
                rec["verdict"] = "SURVIVED"
            else:
                rec["verdict"] = "NO_KILL (红的不是点名断言)"
            rec["other_failed_nodes"] = others
            rec["counts_close"] = collected_ok
        else:
            rec["verdict"] = "GREEN (期望绿臂)" if res["rc"] == 0 and not res["nodes"] else "UNEXPECTED_RED"
            rec["counts_close"] = res["collected"] is not None and res["counts"].get("passed", 0) + res["counts"].get("failed", 0) + res["counts"].get("skipped", 0) + res["counts"].get("error", 0) + res["counts"].get("errors", 0) == res["collected"]
    finally:
        for key, f in files.items():
            f.write_bytes(originals[key])
        for key, f in files.items():
            rec[f"restored_byte_exact_{key}"] = hashlib.sha256(f.read_bytes()).hexdigest() == hashlib.sha256(originals[key]).hexdigest()
        rec["sha256_prefix"] = {k: hashlib.sha256(b).hexdigest()[:16] for k, b in originals.items()}
    return rec


def main() -> int:
    files = {"cap": CAP, "main": MAIN}
    text = {k: f.read_text(encoding="utf-8") for k, f in files.items()}
    report: dict = {
        "tree": str(BACKEND.parent),
        "tip": "13377d3 (git archive export, tree9)",
        "suite": SUITE,
        "cases": [],
    }

    # 行号统一在最后重算（按内容，不按记忆）
    def line_no(src: str, needle: str, startswith: bool = False) -> int | None:
        for i, l in enumerate(src.splitlines(), 1):
            if (l.strip().startswith(needle) if startswith else needle in l):
                return i
        return None

    cap_lines = text["cap"].splitlines()
    b_upstream = None
    for i, l in enumerate(cap_lines, 1):
        if 'method="provider_error"' in l:
            chunk = "\n".join(cap_lines[i - 1:i + 5])
            if "retryable=True," in chunk and "resolver_status=status," in chunk:
                b_upstream = i
                break

    report["anchor_lines"] = {
        "a": line_no(text["cap"], "hard_gaps.append(GAP_MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE)"),
        "b": line_no(text["cap"], '"retryable": bool(resolution.retryable) or verdict == UNKNOWN_RETRYABLE,'),
        "c": line_no(text["cap"], "http_status = None", startswith=True),
        "d": line_no(text["main"], 'reason_code = "MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE"'),
        "b_upstream_block": b_upstream,
    }

    base = run_suite()
    report["baseline"] = {k: base[k] for k in ("rc", "counts", "collected", "nodes")}
    print(f"[baseline] rc={base['rc']} collected={base['collected']} counts={base['counts']}")

    for case in CASES:
        rec = apply_and_run([(case["file"], case["old"], case["new"])], case["expected_killer"])
        rec["key"] = case["key"]
        rec["what"] = case["what"]
        rec["expected_killer"] = case["expected_killer"]
        if case.get("note"):
            rec["note"] = case["note"]
        report["cases"].append(rec)
        print(f"[{case['key']}] {rec['verdict']} nodes={rec.get('observed', {}).get('nodes')}")

    for arm in B_ARMS:
        rec = apply_and_run(arm["mutations"], arm.get("expected_killer"))
        rec["key"] = arm["key"]
        rec["what"] = arm["note"]
        report["cases"].append(rec)
        print(f"[{arm['key']}] {rec['verdict']} nodes={rec.get('observed', {}).get('nodes')}")

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), "utf-8")
    print("WROTE", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
