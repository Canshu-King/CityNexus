"""红队 ORD-0227 三臂：砸 B 的新门 test_two_hard_constraints_each_name_their_own_blocker（tree19 = dea1251）。

臂 1 同候选双冲突：place-tech-art 的 luggage 也改 false ⇒ 一个候选同时与两把冲突。
     预期：产品会点两个名字；B 的门对"只因 STROLLER 冲突却报了 LUGGAGE 名"的断言会红 ⇒ 门误报。
臂 2 三把 HARD：confirm STROLLER + LARGE_LUGGAGE + STEP_FREE_REQUIRED ⇒ 看行为与门的反应。
臂 3 子串诱惑：让冲突地点的 **id** 含另一把的码串 ⇒ 响应点名时带出 ⇒ 门按子串判会误红。
用法：D:/moodle/CityNexus/.venv/Scripts/python.exe raw/d2305848_b0227_arms.py <arm>
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
sys.path.insert(0, r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
from mutation_anchor_guard import temporary_guarded_replace  # noqa: E402

TREE = Path(os.environ.get("REDTEAM_TREE", str(HERE.parent / "tree19"))).resolve()
BACKEND = TREE / "backend"
FIX = TREE / "data" / "mock" / "places.json"
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
GATE = "tests/test_qoder_demo_accessibility_evidence.py"
NEW_NODE = "test_two_hard_constraints_each_name_their_own_blocker"

NODE_RE = re.compile(r"^(?:FAILED|ERROR)\s+(\S+)::(\S+)", re.M)
COUNT_RE = re.compile(r"(\d+)\s+(passed|failed|error|errors|skipped)")


def run_gates() -> dict:
    env = dict(os.environ)
    for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_MODEL", "CITYNEXUS_AI_API_KEY"):
        env.pop(k, None)
    env.update({"CITYNEXUS_DEMO_MODE": "true", "CITYNEXUS_AI_ENABLED": "false", "PYTHONIOENCODING": "utf-8"})
    p = subprocess.run([str(PY), "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", "-rf", GATE],
                       cwd=str(BACKEND), capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=900)
    out = (p.stdout or "") + (p.stderr or "")
    nodes = [f"{m.group(1)}::{m.group(2)}" for m in NODE_RE.finditer(out)]
    counts = {m.group(2): int(m.group(1)) for m in COUNT_RE.finditer(out)}
    mc = re.search(r"(\d+)\s+tests? collected", out)
    return {"rc": p.returncode, "nodes": nodes, "counts": counts,
            "collected": int(mc.group(1)) if mc else sum(counts.values())}


def main() -> int:
    arm = sys.argv[1]
    orig = FIX.read_bytes()
    sha0 = hashlib.sha256(orig).hexdigest()[:16]
    rep: dict = {"tree": str(TREE), "arm": arm, "fixture_sha0": sha0, "cases": []}
    print("fixture sha256[:16]:", sha0)

    A1_OLD = b'"accessibility": {"stroller_accessible": false, "luggage_accessible": true}'
    A1_NEW = b'"accessibility": {"stroller_accessible": false, "luggage_accessible": false}'
    A3_OLD = b'"id": "place-tech-art"'
    A3_NEW = b'"id": "place-tech-art-LUGGAGE_ACCESS_UNAVAILABLE"'

    if arm == "1":
        try:
            with temporary_guarded_replace(FIX, A1_OLD, A1_NEW) as g:
                res = run_gates()
                rep["cases"].append({"key": "A1_same_candidate_both_conflicts",
                                     "receipt": {"anchor_hits": g.anchor_hits, "bytes_changed": g.bytes_changed},
                                     "observed": res,
                                     "new_node_red": any(NEW_NODE in n for n in res["nodes"]),
                                     "other_red": [n for n in res["nodes"] if NEW_NODE not in n]})
        finally:
            pass
        rep["cases"][-1]["restored_exact"] = hashlib.sha256(FIX.read_bytes()).hexdigest()[:16] == sha0
        print("A1:", json.dumps(rep["cases"][-1], ensure_ascii=False)[:600])

    elif arm == "3":
        try:
            with temporary_guarded_replace(FIX, A3_OLD, A3_NEW) as g:
                res = run_gates()
                rep["cases"].append({"key": "A3_substring_temptation",
                                     "receipt": {"anchor_hits": g.anchor_hits, "bytes_changed": g.bytes_changed},
                                     "observed": res,
                                     "new_node_red": any(NEW_NODE in n for n in res["nodes"]),
                                     "other_red": [n for n in res["nodes"] if NEW_NODE not in n]})
        finally:
            pass
        rep["cases"][-1]["restored_exact"] = hashlib.sha256(FIX.read_bytes()).hexdigest()[:16] == sha0
        print("A3:", json.dumps(rep["cases"][-1], ensure_ascii=False)[:600])
    else:
        print("arm 2 is driven separately (needs the product API, not a fixture mutation)")
        return 2

    out = HERE / f"d2305848_b0227_arm{arm}.json"
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
