"""全量红集合的**频率**对比：候选 vs 基线，各 3 轮，同解释器同形制同命令。

动机：单轮"8 vs 8 名字相同"不足以说"我没引入红"——候选第二轮出过 r3/r4，基线那一轮没有；
而这两条在账本里是具名泳者。所以这里不数一次红绿，数 **3 轮里各出现几次**，
并且用 `[0-9]+ failed` 精确匹配（先前我用 `grep failed` 把 `1 xfailed` 也算成过红，是我自己的计数器错）。
"""
from __future__ import annotations

import datetime
import json
import re
import subprocess
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

TREES = {
    "candidate_9d595a6": "D:/moodle/_qoder_f_ord253_20260923/backend",
    "base_d2665e2": "D:/moodle/_qoder_f_run/e_ord0262_d2665e2/backend",
}
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ROUNDS = 3
OUT = Path("D:/moodle/_qoder_f_run/o225_receipts/ord0262_narrow_fullsuite_frequency.json")
RED_RE = re.compile(r"^FAILED (\S+)", re.MULTILINE)
COUNT_RE = re.compile(r"(\d+) failed")


def one_round(root: str) -> dict:
    p = subprocess.run([PY, "-m", "pytest", "--no-header", "-p", "no:cacheprovider", "-q",
                        "--tb=no", "-rf"], cwd=root, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1500)
    out = p.stdout or ""
    tail = next((l for l in reversed(out.splitlines()) if "passed" in l), "")
    red = sorted(set(RED_RE.findall(out)))
    m = COUNT_RE.search(tail)
    return {"exit_code": p.returncode, "summary_line": tail,
            "failed_count_from_regex": int(m.group(1)) if m else 0,
            "named_red_nodeids": red}


def main() -> int:
    data = {"generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "command": "python -m pytest --no-header -p no:cacheprovider -q --tb=no -rf",
            "shape": "whole-suite", "rounds_per_tree": ROUNDS,
            "counter_note": "红数用 ^FAILED 行去重 + `[0-9]+ failed` 摘要双向核；`xfailed` 不算红",
            "trees": {}}
    for tag, root in TREES.items():
        rounds = []
        for i in range(ROUNDS):
            r = one_round(root)
            r["round"] = i + 1
            rounds.append(r)
            print(f"{tag} 第{i + 1}轮: {r['summary_line']}", flush=True)
        names = sorted({n for r in rounds for n in r["named_red_nodeids"]})
        data["trees"][tag] = {
            "root": root, "rounds": rounds,
            "union_of_red_names": names,
            "always_red_all_rounds": sorted(set.intersection(*(set(r["named_red_nodeids"]) for r in rounds))),
            "per_round_red_counts": [r["failed_count_from_regex"] for r in rounds],
        }
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        # 每算完一棵树就落一次盘：上一版跑完 6 轮才崩在半路，整套读数白丢
    tags = list(TREES)                       # 不写死名字：这一份是照 TREES 的顺序取候选/基线
    cand_tag, base_tag = tags[0], tags[1]
    cand = set(data["trees"][cand_tag]["union_of_red_names"])
    base = set(data["trees"][base_tag]["union_of_red_names"])
    data["comparison"] = {
        "candidate_tag": cand_tag, "baseline_tag": base_tag,
        "only_in_candidate": sorted(cand - base),
        "only_in_baseline": sorted(base - cand),
        "in_both_unions": sorted(cand & base),
        "reading": ("候选并集 − 基线并集 为空 ⇒ 3 轮里候选没出现基线之外的名字；"
                    "若非空则**不能**写'0 新红'，只能逐条归因"),
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(data["comparison"], ensure_ascii=False, indent=1))
    print(f"\nWROTE {OUT} ({OUT.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
