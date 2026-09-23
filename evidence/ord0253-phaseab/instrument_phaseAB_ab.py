"""claim-first 两笔（5796c16 + 1f86a8f）的全量红集合 A/B：候选 vs 它自己的父树，各 3 轮。

为什么要这一份：我 21:56 那帖写了"没有新红"，可上一版 A/B 跑完 6 轮才崩在半路（基线导出目录
已被清掉，WinError 267），那句话说的是**没量到**，不是**量过**。这一版：
  · 两棵树都从 git archive 现取现用，并在跑之前逐文件比对导出字节 == 提交字节；
  · 每棵树先量 `--collect-only` 分母（0 条执行的"绿"不是绿）；
  · 每棵树一算完就落盘，绝不跑完 6 轮才写；
  · 记每轮墙钟秒数，让"计时"这一列也在收据里。
基线取候选**自己的父** aabd47e，不取当前尖：尖由包工头移动，落地窗口他开，我不追。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path("D:/moodle/_qoder_integration_20260919")
RUN = Path("D:/moodle/_qoder_f_run")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ROUNDS = 3
OUT = RUN / "o225_receipts" / "ord0253_phaseAB_ab_0923.json"
RED_RE = re.compile(r"^FAILED (\S+)", re.MULTILINE)
COUNT_RE = re.compile(r"(\d+) failed")

TREES = {
    "candidate_408d851": "408d851",     # Phase A/B claim-first（仲裁 §② 的形状）
    "base_aabd47e": "aabd47e",          # 整条 claim-first 链之前那一枚：同一把门，没有 Phase A/B
}

# 逐文件核对的名单：这几枚决定本单的形状，导出与提交必须同字节
CHECK = [
    "backend/app/main.py",
    "backend/app/db/session.py",
    "backend/tests/test_qoder_agent_command_idempotency.py",
    "backend/tests/test_qoder_agent_command_claim_first.py",
    "backend/tests/test_qoder_agent_command_idempotency_xproc.py",
    "contracts/openapi.yaml",
]


def sh(args: list[str], cwd: Path, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, input=stdin, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=900)


def export(tag: str, rev: str) -> tuple[Path, dict]:
    full = sh(["git", "rev-parse", rev], REPO).stdout.strip()
    assert len(full) == 40, f"SETUP：{rev} 没解析成 40 位：{full!r}"
    root = RUN / f"e_ab_{tag}"
    if root.exists():
        # 一律重建：本工具自己的导出（具名前缀 e_ab_），旧目录里可能留着上一轮跑出来的 ./citynexus.db
        import shutil
        shutil.rmtree(root)
    root.mkdir(parents=True)
    proc = subprocess.run(f'git archive --format=tar {full} | tar -xf - -C "{root}"',
                          shell=True, cwd=REPO, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=900)
    assert proc.returncode == 0, f"SETUP：archive 解不出 {tag}：{proc.stderr[:300]}"
    prov = {}
    for rel in CHECK:
        b = sh(["git", "rev-parse", "--verify", "-q", f"{full}:{rel}"], REPO)
        if b.returncode != 0:
            # 这枚提交里**本来就没有**这个路径（claim-first 的门文件在基线里不存在）⇒ 记事实，不算坏导出
            prov[rel] = {"in_commit": False, "in_export": (root / rel).is_file()}
            assert not (root / rel).exists(), f"SETUP：{tag} 的提交里没有 {rel}，导出里却有 ⇒ 目录不干净"
            continue
        size = int(sh(["git", "cat-file", "-s", f"{full}:{rel}"], REPO).stdout.strip())
        want = b.stdout.strip()
        f = root / rel
        assert f.is_file(), f"SETUP：提交里有 {rel} 而导出里没有 ⇒ 导出残缺，不能拿它读数"
        got = hashlib.sha1(b"blob %d\0" % size + f.read_bytes()).hexdigest()
        prov[rel] = {"in_commit": True, "bytes": size, "commit_sha1": want,
                     "export_sha1": got, "equal": got == want}
    bad = [k for k, v in prov.items() if v.get("in_commit") and not v.get("equal")]
    assert not bad, f"SETUP：导出字节 != 提交字节 ⇒ 量的不是那枚提交：{bad}"
    return root, {"rev_arg": rev, "full_sha": full,
                  "tree": sh(["git", "rev-parse", f"{full}^{{tree}}"], REPO).stdout.strip(),
                  "export_root": str(root), "blob_equality": prov}


def collect_denominator(root: Path) -> dict:
    p = sh([PY, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"], root)
    out = p.stdout or ""
    nums = re.findall(r"^(\d+) tests? collected", out, re.M) or re.findall(r"(\d+) collected", out)
    return {"exit_code": p.returncode, "collected": int(nums[-1]) if nums else 0,
            "error_lines": len(re.findall(r"^ERROR ", out, re.M))}


def one_round(root: Path) -> dict:
    t0 = time.time()
    p = sh([PY, "-m", "pytest", "--no-header", "-p", "no:cacheprovider", "-q", "--tb=no", "-rf"], root)
    out = p.stdout or ""
    tail = next((l for l in reversed(out.splitlines()) if "passed" in l), "")
    m = COUNT_RE.search(tail)
    return {"exit_code": p.returncode, "summary_line": tail,
            "wall_clock_s": round(time.time() - t0, 1),
            "failed_count_from_regex": int(m.group(1)) if m else 0,
            "named_red_nodeids": sorted(set(RED_RE.findall(out))),
            "stderr_tail": (p.stderr or "")[-300:]}


def main() -> int:
    data = {"generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "command": "python -m pytest --no-header -p no:cacheprovider -q --tb=no -rf",
            "cwd_shape": "<export>/backend  ← 与已验收的 0262 3×3 同形制，不另起一种跑法",
            "interpreter": PY, "shape": "whole-suite from a fresh git archive export",
            "rounds_per_tree": ROUNDS,
            "baseline_choice": "候选自己的父 aabd47e（不是当前尖 d2665e2）；尖由 commander 移动，我不追",
            "counter_note": "红数 = ^FAILED 去重 + `[0-9]+ failed` 摘要双向核；xfailed 不算红",
            "trees": {}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    for tag, rev in TREES.items():
        root, prov = export(tag, rev)
        suite_cwd = root / "backend"
        assert suite_cwd.is_dir(), f"SETUP：导出里没有 backend/ ⇒ 跑不起来：{suite_cwd}"
        entry = {**prov, "suite_cwd": str(suite_cwd),
                 "collect": collect_denominator(suite_cwd), "rounds": []}
        print(f"[{tag}] collect={entry['collect']}", flush=True)
        for i in range(ROUNDS):
            r = one_round(suite_cwd)
            r["round"] = i + 1
            entry["rounds"].append(r)
            print(f"[{tag}] r{i + 1} {r['wall_clock_s']}s :: {r['summary_line']}", flush=True)
        names = sorted({n for r in entry["rounds"] for n in r["named_red_nodeids"]})
        entry["union_of_red_names"] = names
        entry["per_round_red_counts"] = [r["failed_count_from_regex"] for r in entry["rounds"]]
        entry["always_red_all_rounds"] = sorted(
            set.intersection(*(set(r["named_red_nodeids"]) for r in entry["rounds"])))
        data["trees"][tag] = entry
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        print(f"[{tag}] 落盘 → {OUT}", flush=True)

    cand_tag, base_tag = list(TREES)
    cand = set(data["trees"][cand_tag]["union_of_red_names"])
    base = set(data["trees"][base_tag]["union_of_red_names"])
    data["comparison"] = {
        "candidate_tag": cand_tag, "baseline_tag": base_tag,
        "only_in_candidate": sorted(cand - base),
        "only_in_baseline": sorted(base - cand),
        "in_both_unions": len(cand & base),
        "collect_denominators": {t: data["trees"][t]["collect"]["collected"] for t in TREES},
        "reading": ("候选并集 − 基线并集 为空 ⇒ 3 轮里候选没出现基线之外的名字；"
                    "若非空则不能写'0 新红'，只能逐条归因"),
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(data["comparison"], ensure_ascii=False, indent=1))
    print(f"\nWROTE {OUT} ({OUT.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
