"""0262 retry 收口那一笔的 3×3 全量 A/B：候选 30092dc vs 基线 d2665e2。

形制与已验收的上一份一致（新鲜 `git archive` 导出、跑前逐文件核对导出字节==提交字节、
分母先量 `--collect-only`、每棵树一算完就落盘、每轮记墙钟）。
唯一要看的事：**only_in_candidate 应从 1 变 0**（那 1 条是设计内红的"三处 500 与阶梯不一致"格，
现在常数已收口，它该转绿；若还留着别的名字，逐条归因不遮）。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path("D:/moodle/_qoder_integration_20260919")
RUN = Path("D:/moodle/_qoder_f_run")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ROUNDS = 3
OUT = RUN / "o225_receipts" / "ord0262_retry_collapse_ab_r2.json"
RED_RE = re.compile(r"^FAILED (\S+)", re.MULTILINE)
COUNT_RE = re.compile(r"(\d+) failed")

TREES = {
    "candidate_3093eea": "3093eea",     # busy 等值收口进各自阶梯 + resident 断言改判阶梯下限
    "base_d2665e2": "d2665e25855aeb265329266831983de42321697d",   # 派单前的权威基线
}
CHECK = [
    "backend/app/main.py",
    "backend/app/catalog_hydration_operations.py",
    "backend/app/stay_generation_operations.py",
    "backend/tests/test_qoder_ord0262_narrow_contention.py",
    "contracts/openapi.yaml",
]


def git(*args: str) -> str:
    p = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert p.returncode == 0, f"git {args[:2]}: {p.stderr[:200]}"
    return p.stdout.strip()


def export(tag: str, rev: str) -> tuple[Path, dict]:
    full = git("rev-parse", rev)
    assert len(full) == 40, f"SETUP：{rev} 没解析成 40 位"
    root = RUN / f"e_262ab_{tag}"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    p = subprocess.run(f'git archive --format=tar {full} | tar -xf - -C "{root}"', shell=True,
                       cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900)
    assert p.returncode == 0, f"SETUP：解不出 {tag}：{p.stderr[:220]}"
    prov = {}
    for rel in CHECK:
        b = git("rev-parse", "--verify", "-q", f"{full}:{rel}") if subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "--verify", "-q", f"{full}:{rel}"],
            capture_output=True).returncode == 0 else ""
        if not b:
            prov[rel] = {"in_commit": False, "in_export": (root / rel).is_file()}
            continue
        size = int(git("cat-file", "-s", f"{full}:{rel}"))
        got = hashlib.sha1(b"blob %d\0" % size + (root / rel).read_bytes()).hexdigest()
        prov[rel] = {"in_commit": True, "bytes": size, "commit_sha1": b, "export_sha1": got,
                     "equal": got == b}
    bad = [k for k, v in prov.items() if v.get("in_commit") and not v.get("equal")]
    assert not bad, f"SETUP：导出字节 != 提交字节 ⇒ 量的不是那枚提交：{bad}"
    return root, {"full_sha": full, "tree": git("rev-parse", f"{full}^{{tree}}"),
                  "blob_equality": prov}


def run_pytest(cwd: Path, extra: list[str]) -> dict:
    t0 = time.time()
    p = subprocess.run([PY, "-m", "pytest", *extra], cwd=str(cwd), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=1800)
    out = p.stdout or ""
    tail = next((l for l in reversed(out.splitlines()) if "passed" in l or "error" in l), "")
    collected = re.findall(r"(\d+) tests? collected", out)
    return {"exit_code": p.returncode, "seconds": round(time.time() - t0, 1), "summary_line": tail,
            "collected": int(collected[-1]) if collected else None,
            "failed": int((COUNT_RE.search(tail).group(1)) if COUNT_RE.search(tail) else 0),
            "named_red_nodeids": sorted(set(RED_RE.findall(out)))}


def main() -> int:
    data = {"generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "command": "python -m pytest --no-header -p no:cacheprovider -q --tb=no -rf  (cwd=<export>/backend)",
            "interpreter": PY, "rounds_per_tree": ROUNDS, "trees": {}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    for tag, rev in TREES.items():
        root, prov = export(tag, rev)
        backend = root / "backend"
        collect = run_pytest(backend, ["--collect-only", "-q", "-p", "no:cacheprovider"])
        entry = {**prov, "suite_cwd": str(backend),
                 "collect": {"exit_code": collect["exit_code"],
                             "collected": collect["collected"],
                             "rc_zero": collect["exit_code"] == 0}, "rounds": []}
        print(f"[{tag}] collect={entry['collect']}", flush=True)
        for i in range(ROUNDS):
            r = run_pytest(backend, ["--no-header", "-p", "no:cacheprovider", "-q", "--tb=no", "-rf"])
            r["round"] = i + 1
            entry["rounds"].append(r)
            print(f"[{tag}] r{i + 1} {r['seconds']}s :: {r['summary_line']}", flush=True)
        entry["union_of_red_names"] = sorted({n for r in entry["rounds"] for n in r["named_red_nodeids"]})
        entry["per_round_red_counts"] = [r["failed"] for r in entry["rounds"]]
        entry["always_red_all_rounds"] = sorted(set.intersection(
            *(set(r["named_red_nodeids"]) for r in entry["rounds"])))
        data["trees"][tag] = entry
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    cand, base = list(TREES)
    cset = set(data["trees"][cand]["union_of_red_names"])
    bset = set(data["trees"][base]["union_of_red_names"])
    data["comparison"] = {"candidate_tag": cand, "baseline_tag": base,
                          "only_in_candidate": sorted(cset - bset),
                          "only_in_baseline": sorted(bset - cset),
                          "in_both_unions": len(cset & bset),
                          "collect_denominators": {t: data["trees"][t]["collect"]["collected"]
                                                   for t in TREES},
                          "expectation_under_the_ruling": "only_in_candidate 应为 0（那 1 条 FINDING_OPEN 格已收口转绿）"}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in data["comparison"].items() if k != "collect_denominators"},
                     ensure_ascii=False, indent=1))
    print(f"WROTE {OUT} ({OUT.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
