"""把 A/B 里那条"候选独有红"分诊一遍：它是系统性回归，还是只在一轮里出现的批次敏感泳者？

判法不用我自己的嘴：同一枚 nodeid 在两棵树各跑 N 轮（聚焦跑，库各自新建），
再和 A/B 里的逐轮读数并排——**只有"候选每轮都红、基线每轮都不红"才叫回归**。
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path("D:/moodle/_qoder_integration_20260919")
RUN = Path("D:/moodle/_qoder_f_run")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
NODEID = ("tests/test_qoder_ord224_g3_generation_measurement.py::"
          "test_shape_a_terminal_job_then_five_requests_is_two_generations_not_one")
ROUNDS = 3
TREES = {"candidate_3093eea": "3093eea773c79fa00744fe72d1f2c43b4d0bd75e",
         "base_d2665e2": "d2665e25855aeb265329266831983de42321697d"}
OUT = RUN / "o225_receipts" / "ord0262_swimmer_triage.json"
AB = RUN / "o225_receipts" / "ord0262_retry_collapse_ab_r2.json"

rows = {}
for tag, full in TREES.items():
    root = RUN / f"e_triage_{tag}"
    if root.exists():
        import shutil
        shutil.rmtree(root)
    root.mkdir(parents=True)
    subprocess.run(f'git archive --format=tar {full} | tar -xf - -C "{root}"', shell=True,
                   cwd=REPO, check=True, capture_output=True)
    backend = root / "backend"
    runs = []
    for i in range(ROUNDS):
        t0 = time.time()
        p = subprocess.run([PY, "-m", "pytest", NODEID, "-q", "--no-header",
                            "-p", "no:cacheprovider", "--tb=line"], cwd=str(backend),
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=600)
        out = p.stdout or ""
        tail = next((l for l in reversed(out.splitlines()) if "passed" in l or "failed" in l), "")
        runs.append({"round": i + 1, "exit_code": p.returncode, "seconds": round(time.time() - t0, 1),
                     "summary": tail[:120], "red": "failed" in tail and "1 failed" in tail})
        print(f"[{tag}] r{i + 1} {'RED' if runs[-1]['red'] else 'GREEN'} :: {tail[:70]}", flush=True)
    rows[tag] = {"full_sha": full, "rounds": runs, "red_rounds": sum(1 for r in runs if r["red"])}

ab = json.loads(AB.read_text(encoding="utf-8")) if AB.is_file() else {}
cand_rounds = ab.get("trees", {}).get("candidate_3093eea", {}).get("per_round_red_counts", [])
base_rounds = ab.get("trees", {}).get("base_d2665e2", {}).get("per_round_red_counts", [])
cand_union = ab.get("trees", {}).get("candidate_3093eea", {}).get("union_of_red_names", [])
cand_always = ab.get("trees", {}).get("candidate_3093eea", {}).get("always_red_all_rounds", [])
verdict = ("REGRESSION：候选聚焦跑每轮都红且基线每轮都不红"
           if rows["candidate_3093eea"]["red_rounds"] == ROUNDS and rows["base_d2665e2"]["red_rounds"] == 0
           else "BATCH_SENSITIVE / NOT_A_REGRESSION：聚焦轮里不是候选恒红 ⇒ 它不满足'系统性回归'的形状"
           )
data = {"what": "A/B 那条候选独有红的分诊（聚焦 N 轮 × 两棵树，与全量逐轮读数并排）",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "nodeid": NODEID, "focused_rounds": ROUNDS, "trees": rows,
        "whole_suite_context": {"candidate_per_round_red": cand_rounds, "baseline_per_round_red": base_rounds,
                                "candidate_union_size": len(cand_union),
                                "candidate_always_red_size": len(cand_always),
                                "note": "全量里它只在候选的 3 轮中出现 1 轮 ⇒ union 9 > always 8"},
        "command": f"{PY} -m pytest {NODEID} -q --no-header -p no:cacheprovider --tb=line",
        "verdict": verdict,
        "rule": "只有『候选每轮都红且基线每轮都不红』才允许叫回归（ORD-0168 三分类：具名门/批次敏感/回归）"}
OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\n" + verdict)
print(f"WROTE {OUT} ({OUT.stat().st_size} B)")
