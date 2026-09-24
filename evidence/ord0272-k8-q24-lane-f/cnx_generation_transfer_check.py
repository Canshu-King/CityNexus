#!/usr/bin/env python3
"""Q24 合流：跨代引用只能**逐格**按被引文件的 blob 两侧值判，缺任一侧就是不可转移。

规则来源：仲裁 Q24 = ①，常设规则 `GENERATION_TRANSFER_BY_CITED_BLOB_EQUALITY_V1`
（账本 @2026-09-25T04:0x+08 §②）。要点：判断单位是观察格而不是整单；每个格只许声明
"实际跑过的那一代"的结果；要引用旧代证据，该格依赖的**每一个**被引文件必须在两代里
40 位 blob 完全一致，且收据要记下 `cited_blob_at_each_generation` 两侧值；
任一不一致 / 缺任一代 / 证不了同一内容 ⇒ `NOT_TRANSFERABLE_GENERATION`，且**只重跑该格**。

用法
----
  python cnx_generation_transfer_check.py --tree <仓库或工作树> --gen-a <sha> --gen-b <sha> \
         --files backend/app/main.py,backend/tests/... [--json 输出]

  python cnx_generation_transfer_check.py --tree <仓库> --selftest
      # 三向自测，全部用真对象：同代相等 / 同代不等 / 只有一代有该文件

只读：本脚本只跑 `git rev-parse` / `git cat-file -s`，不写树、不 checkout、不动 ref。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TRANSFERABLE = "TRANSFERABLE_BY_CITED_BLOB_EQUALITY"
NOT = "NOT_TRANSFERABLE_GENERATION"


def git(tree: Path, *args: str) -> str | None:
    p = subprocess.run(["git", "-C", str(tree), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.stdout.strip() if p.returncode == 0 else None


def blob_at(tree: Path, rev: str, path: str) -> dict:
    """一枚 (代, 路径) 的 blob：取不到就写明取不到，绝不用空值蒙过判定。"""

    sha = git(tree, "rev-parse", "--verify", "-q", f"{rev}:{path}")
    out = {"path": path, "blob_sha1_40": sha or None}
    if sha:
        size = git(tree, "cat-file", "-s", sha)
        out["bytes"] = int(size) if size and size.isdigit() else None
        out["resolved"] = True
    else:
        out["bytes"] = None
        out["resolved"] = False
        out["why_missing"] = f"这一代 {rev[:9]} 里取不到 {path}（blob 不存在或未提交）"
    return out


def judge(path: str, gen_a: str, gen_b: str, tree: Path) -> dict:
    a, b = blob_at(tree, gen_a, path), blob_at(tree, gen_b, path)
    if not a["resolved"] or not b["resolved"]:
        verdict, why = NOT, "缺任一代的 blob 读数 ⇒ 按 Q24 直接判不可转移，不当成未填放行"
    elif a["blob_sha1_40"] == b["blob_sha1_40"]:
        verdict, why = TRANSFERABLE, "两代 40 位逐位相等"
    else:
        verdict, why = NOT, (f"两代内容不同（{a['blob_sha1_40'][:9]} vs {b['blob_sha1_40'][:9]}）"
                             "⇒ 该格必须在目标代重跑，只重跑这一格")
    return {"file": path, "generation_a": gen_a, "generation_b": gen_b,
            "blob_a": a, "blob_b": b,
            "cited_blob_at_each_generation": {gen_a: a["blob_sha1_40"], gen_b: b["blob_sha1_40"]},
            "generation_transfer": verdict, "reason": why}


def check(tree: Path, gen_a: str, gen_b: str, files: list[str]) -> dict:
    rows = [judge(f, gen_a, gen_b, tree) for f in files]
    return {"rule": "GENERATION_TRANSFER_BY_CITED_BLOB_EQUALITY_V1（仲裁 Q24 = ①）",
            "unit": "观察格（cell），不是整张任务单",
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "tree": str(tree), "gen_a": gen_a, "gen_b": gen_b,
            "gen_a_head_of": git(tree, "rev-parse", "--short", gen_a),
            "gen_b_head_of": git(tree, "rev-parse", "--short", gen_b),
            "files": rows,
            "summary": {
                "total": len(rows),
                "transferable": sum(1 for r in rows if r["generation_transfer"] == TRANSFERABLE),
                "not_transferable": sum(1 for r in rows if r["generation_transfer"] == NOT),
                "missing_a_side": sum(1 for r in rows
                                      if not r["blob_a"]["resolved"]
                                      or not r["blob_b"]["resolved"])},
            "read_only_declaration": "只跑 git rev-parse / git cat-file -s；不写树、不 checkout、不动 ref"}


def selftest(tree: Path) -> int:
    """三向都用真对象：相等 / 不等 / 只有一代有。任何一向判错就 FAIL。"""
    A, B, OLD = "dcae1bc964125c3a975916f6bf667794cc19622a", \
        "7c806fab58e872060cb5811ff96c770b40dad165", "c79e2b4f4efe414dba22a071a7136ae10b5c84aa"
    cases = [
        ("相等（本代未改的文件）", "backend/app/schemas.py", A, B, TRANSFERABLE),
        ("不等（K8 刚改过的文件）", "backend/app/main.py", A, B, NOT),
        ("只有一代有该文件（上一代还没有这扇门）", "backend/tests/test_qoder_ord0272_continuation.py",
         OLD, B, NOT),
    ]
    ok = True
    for name, path, ga, gb, want in cases:
        r = judge(path, ga, gb, tree)
        vals = [r["blob_a"]["blob_sha1_40"] or "—", r["blob_b"]["blob_sha1_40"] or "—"]
        good = r["generation_transfer"] == want
        ok = ok and good
        print(f"[selftest] {name}\n    {path}\n    两侧 blob = {vals[0][:12]}… vs {vals[1][:12]}…"
              f"\n    判定 = {r['generation_transfer']}（期望 {want}）-> {'对' if good else '错'}")
    print("SELFTEST_PASS" if ok else "SELFTEST_FAIL")
    return 0 if ok else 5


def main() -> int:
    ap = argparse.ArgumentParser(description="Q24 跨代引用检查（逐格、按被引文件 blob 两侧值）")
    ap.add_argument("--tree", required=True)
    ap.add_argument("--gen-a", default=None)
    ap.add_argument("--gen-b", default=None)
    ap.add_argument("--files", default="")
    ap.add_argument("--json", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    tree = Path(a.tree)
    if a.selftest:
        return selftest(tree)
    if not (a.gen_a and a.gen_b and a.files):
        print("用法：--gen-a/--gen-b/--files 都要给（或用 --selftest）")
        return 2
    out = check(tree, a.gen_a, a.gen_b, [f.strip() for f in a.files.split(",") if f.strip()])
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8",
                                newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
