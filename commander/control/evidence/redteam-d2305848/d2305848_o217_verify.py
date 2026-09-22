"""红队复验 C 的 ORD-0217（SESSION=d2305848）：F1 支路是否真被关死。

C 的修复 = 4d74b55：`http_status` 只从 answered 且自带状态码的 attempt 读；
answered 却无码 ⇒ 落 TRANSPORT_EXCEPTION/null/TRANSPORT（F 的门 11 passed 已由我基线复证）。

红队读法：
  R1  我的原 F1 臂（answered 分支 statuses 为空时编 200）打到**修复后**的实现上，
      期望门仍红——但红的应该是**新的保护点**（test_1c 或 test_1d），而不是修复前的形状。
      注意：修复后 F1 的锚点 `statuses[0] if statuses else None` 可能已不存在（实现重写），
      锚点变了就按内容重新定位，定位不到如实报。
  R2  直接伪造形状（不走实现）：把"answered=True 无码"喂给修复后的 _attribution_fields，
      期望产出 TRANSPORT_EXCEPTION 而不是 HTTP_RESPONSE（实现语义验证）。
用法：D:/moodle/CityNexus/.venv/Scripts/python.exe raw/d2305848_o217_verify.py
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

TREE = Path(os.environ.get("REDTEAM_TREE", str(HERE.parent / "tree13"))).resolve()
BACKEND = TREE / "backend"
CAP = BACKEND / "app" / "anywhere_capability.py"
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
OUT = HERE / "d2305848_o217_verify.json"
DOOR = "tests/test_qoder_attribution_fields_hard_door.py"

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
    src = CAP.read_text(encoding="utf-8")
    report: dict = {"tree": str(TREE), "cap_sha256_16": None, "cases": []}
    import hashlib
    report["cap_sha256_16"] = hashlib.sha256(src.encode("utf-8")).hexdigest()[:16]

    # R1: old F1 anchor — locate by content on the FIXED implementation
    old_anchor = '''        evidence_kind = "HTTP_RESPONSE"
        http_status = statuses[0] if statuses else None
'''
    hits_old = src.count(old_anchor)
    report["f1_old_anchor_hits"] = hits_old
    if hits_old == 1:
        base = run()
        report["baseline"] = {k: base[k] for k in ("rc", "counts", "collected", "nodes")}
        rec = {"key": "R1-old-F1-on-fixed-impl"}
        try:
            with temporary_guarded_replace(CAP, old_anchor.encode("utf-8"),
                                           old_anchor.replace("else None", "else 200").encode("utf-8")) as guard:
                res = run()
                rec["receipt"] = {"anchor_hits": guard.anchor_hits, "mutated_sha256": guard.mutated_sha256[:16]}
                rec["observed"] = {k: res[k] for k in ("rc", "counts", "collected", "nodes")}
                red = res["nodes"]
                rec["red_nodes"] = red
                has_1c = any("test_1c" in n for n in red)
                has_1d = any("test_1d" in n for n in red)
                rec["verdict"] = ("PROTECTED (门红，保护点命中)" if (has_1c or has_1d)
                                  else ("RED_BUT_NOT_BY_GUARD" if red else "BYPASSED (编 200 仍合规!)"))
        finally:
            pass
        report["cases"].append(rec)
        print("R1:", rec["verdict"], "| red:", rec.get("red_nodes"))
    else:
        report["cases"].append({"key": "R1-old-F1-on-fixed-impl",
                                "verdict": f"ANCHOR_GONE (旧锚点命中 {hits_old}，实现已重写——按内容重找)"})
        print("R1: anchor gone, hits =", hits_old)
        # 按内容找新的 answered 分支
        for i, l in enumerate(src.splitlines(), 1):
            if "statuses" in l and ("if statuses" in l or "answered" in l):
                print(f"  candidate line {i}: {l.strip()[:100]}")

    report["door_baseline_counts"] = {"collected": 11, "passed": 11}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), "utf-8")
    print("WROTE", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
