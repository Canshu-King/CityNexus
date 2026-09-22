"""红队复验 F 的 ORD-0214（SESSION=d2305848）：test_1d 是否真杀我原 F1 臂。

原 F1 臂 = tree10 上 `statuses[0] if statuses else None` → `else 200`（合法形状伪造）。
F 的新门声称 test_1d（产出码必须能在输入 attempts 找到出处）咬住它。
独立复验：同一突变打到 tree12 的实现上，预期 test_1d 红。

用法：D:/moodle/CityNexus/.venv/Scripts/python.exe raw/d2305848_o214_verify.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
from mutation_anchor_guard import temporary_guarded_replace  # noqa: E402

TREE = Path(os.environ.get("REDTEAM_TREE", str(HERE.parent / "tree12"))).resolve()
BACKEND = TREE / "backend"
CAP = BACKEND / "app" / "anywhere_capability.py"
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
OUT = HERE / "d2305848_o214_verify.json"
DOOR = "tests/test_qoder_attribution_fields_hard_door.py"

F1_OLD = '''        evidence_kind = "HTTP_RESPONSE"
        http_status = statuses[0] if statuses else None
'''
F1_NEW = '''        evidence_kind = "HTTP_RESPONSE"
        http_status = statuses[0] if statuses else 200
'''

NODE_RE = re.compile(r"^(?:FAILED|ERROR)\s+(\S+)::(\S+)", re.M)
COUNT_RE = re.compile(r"(\d+)\s+(passed|failed|error|errors|skipped)")


def run() -> dict:
    env = dict(os.environ)
    for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_MODEL", "CITYNEXUS_AI_API_KEY"):
        env.pop(k, None)
    env.update({"CITYNEXUS_DEMO_MODE": "true", "CITYNEXUS_AI_ENABLED": "false", "PYTHONIOENCODING": "utf-8"})
    p = subprocess.run(
        [str(PYTHON), "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", "-rf", DOOR],
        cwd=str(BACKEND), capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env, timeout=600,
    )
    out = (p.stdout or "") + (p.stderr or "")
    nodes = [f"{m.group(1)}::{m.group(2)}" for m in NODE_RE.finditer(out)]
    counts = {m.group(2): int(m.group(1)) for m in COUNT_RE.finditer(out)}
    mc = re.search(r"(\d+)\s+tests? collected", out)
    collected = int(mc.group(1)) if mc else sum(counts.values())
    return {"rc": p.returncode, "nodes": nodes, "counts": counts, "collected": collected}


def main() -> int:
    report = {"tree": str(TREE), "door_sha": None, "cases": []}
    src = CAP.read_text(encoding="utf-8")
    F1_hits = src.count(F1_OLD)
    report["f1_anchor_hits_at_tip"] = F1_hits
    report["f1_line"] = next((i for i, l in enumerate(src.splitlines(), 1) if "statuses[0] if statuses else" in l), None)
    report["door_sha"] = None

    base = run()
    report["baseline"] = {k: base[k] for k in ("rc", "counts", "collected", "nodes")}
    print(f"[baseline] rc={base['rc']} counts={base['counts']}")

    rec = {"key": "F1-replay-on-tree12"}
    try:
        with temporary_guarded_replace(CAP, F1_OLD.encode("utf-8"), F1_NEW.encode("utf-8")) as guard:
            rec["receipt"] = {"anchor_hits": guard.anchor_hits, "bytes_changed": guard.bytes_changed,
                              "mutated_sha256": guard.mutated_sha256[:16]}
            res = run()
            rec["observed"] = {k: res[k] for k in ("rc", "counts", "collected", "nodes")}
            c = res["counts"]
            rec["counts_close"] = c.get("passed", 0) + c.get("failed", 0) == res["collected"]
            # 判定：我的原 F1 臂必须红，且红的必须含 test_1d（F 声称的杀手）
            rec["killer_present"] = any("test_1d_a_reported_status_must_be_one_the_attempts_actually_carried" in n for n in res["nodes"])
            if res["nodes"] and rec["killer_present"]:
                rec["verdict"] = "CONFIRMED (test_1d 咬住原 F1 臂)"
            elif res["nodes"]:
                rec["verdict"] = "RED_BUT_WRONG_KILLER (红的是别的断言)"
            else:
                rec["verdict"] = "STILL_BYPASSED (test_1d 没咬住)"
    finally:
        pass
    report["cases"].append(rec)
    print("F1-replay:", rec["verdict"], "| red:", rec.get("observed", {}).get("nodes"))

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), "utf-8")
    print("WROTE", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
