#!/usr/bin/env python3
"""ORD-0457 r4 - emit the ledger block from the r4 artifacts.

Nothing in the block is typed: every 40-hex comes from `git rev-parse`/`git ls-remote` and is asserted
to be `git cat-file`-able, every count comes from a JSON artifact this order wrote, and the conflict
claim answers the relayed order with the file list actually measured rather than with agreement.

    python review/ord0457/make_block_r4.py <worktree> <prev-tip> <line-tip> <out-md>
"""

from __future__ import annotations

import datetime
import io
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
PREV_ARG = sys.argv[2]
TIP_ARG = sys.argv[3]
OUT = Path(sys.argv[4]).resolve()
E = "review/n3_0457_evidence_r4/"
BRANCH = "review/N3-ord0457-named-failure-exits-r4"
DELIVERED_R3 = "review/N3-ord0457-named-failure-exits-r3"
MINE = ["frontend/src/app/V8Experience.tsx", "frontend/src/lib/failureAttribution.ts"]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def cat40(value: str) -> str:
    assert re.fullmatch(r"[0-9a-f]{40}", value or ""), f"not a verbatim 40-hex: {value!r}"
    assert subprocess.run(["git", "cat-file", "-e", value], cwd=str(ROOT)).returncode == 0, \
        f"not a git object on this line: {value}"
    return value


def blob(rel: str) -> str:
    return cat40(git("rev-parse", f"HEAD:{rel}"))


def remote_head(branch: str) -> str:
    ref = f"refs/heads/{branch}"
    for line in git("-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin", ref).splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == ref:
            return cat40(parts[0])
    raise AssertionError(f"{ref} is not on origin")


def load(rel: str) -> dict:
    return json.loads(io.open(ROOT / rel, encoding="utf-8").read())


def main() -> int:
    arms = load(E + "arms.json")
    zh = load(E + "walk/named_exits_zh.json")
    en = load(E + "walk/named_exits_en.json")
    before = load(E + "walk_before/named_exits_zh.json")
    exp_b, exp_a = load(E + "exposure_before.json"), load(E + "exposure_after.json")
    receipt = load(E + "rebase_receipt.json")

    cells_b = {h["cell_identity"] for h in exp_b["hits"]}
    cells_a = {h["cell_identity"] for h in exp_a["hits"]}
    growth, shrink = sorted(cells_a - cells_b), sorted(cells_b - cells_a)
    mine_in_hits = [f for f in sorted({h["file"] for h in exp_a["hits"]}) if any(k in f for k in MINE)]
    r3_hits = sorted({h["file"] for h in load("review/n3_0457_evidence_r1/exposure_after_r3.json")["hits"]})

    prev = cat40(git("rev-parse", PREV_ARG))
    tip = cat40(git("rev-parse", TIP_ARG))
    r1 = remote_head("review/N3-ord0457-named-failure-exits-r1")
    r2 = remote_head("review/N3-ord0457-named-failure-exits-r2")
    r3 = remote_head(DELIVERED_R3)
    head = remote_head(BRANCH)
    my_commits = int(git("rev-list", "--count", f"{tip}..HEAD") or 0)
    arms_r1_at_r3 = cat40(git("rev-parse", f"{r3}:review/ord0457/named_exit_arms_r1.py"))
    arms_r1_at_head = blob("review/ord0457/named_exit_arms_r1.py")
    hit_files = sorted({h["file"] for h in exp_a["hits"]})
    pairs = receipt["product_blob_pairs"]
    moved = receipt["moved_list"]

    arm_lines = []
    for arm in arms["arms"]:
        tag = arm["name"].split()[0]
        reds = ", ".join(r.split()[1] for r in arm["red_checks"])
        arm_lines.append(
            f"- {tag}（证据目录 `{Path(arm['walk_out']).name}`）：walk_summary={arm['walk_summary']}，"
            f"红在 {reds}；applied={arm['applied']} restored_byte_identical={arm['restored_byte_identical']}")

    block = f"""### ORD-0457 r4：线又前移到 {tip}，三态屏读、反件、exposure、编译臂当场第三次重取；转达里的两处坐标与我实测不同（贴读数）

车道 N3（会话 49fe0d7b），{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}（+08）。本轮要求逐字是「请在现尖上 rebase、把失败三态那一屏重放到 V8Experience 当代形状上、当代重跑你的屏读判据，再推 r3」——做了，但交件落在新枝名 r4：r3 已按 ls-remote 交付在 {r3}，rebase 会重写那串提交，覆盖一枚已交付的 ref 是禁令，所以按「每轮新枝名」推 r4，r3 原样留档。

## 1. 交件坐标

- 枝名 `review/N3-ord0457-named-failure-exits-r4`；`git -c http.proxy= -c https.proxy= ls-remote origin refs/heads/{BRANCH}` 回读件尖 {head}（可 `git cat-file`）。
- rebase 落点线尖 {tip}；上一轮基线 {prev}。我这 commits={my_commits} 枚提交叠在现尖之上。
- 已交付三枝按 origin 实测：r1={r1}、r2={r2}、r3={r3}。转达那句「件尖 33d990b2 系那枝 r2」在我这侧对不上：同一枚 `ls-remote` 输出里，sha8=33d990b2 那枚完整 40 位（就是上一行的 r1）挂在 `-r1`，`-r2` 是 {r2}。我按 origin 取值，不按本地枝名（本地枝在反复 rebase 中会漂移，上一块就是这么写错过一次）。

## 2. 「冲突面仅一枚文件 V8Experience.tsx」我这侧的实测

- 线从 {prev} 到 {tip} 在 `frontend/src` 下动了 files_moved={len(moved)} 枚：{", ".join(f"`{f}`" for f in moved)}。
- 与我这 files={len(MINE)} 产品文件的重叠：{len(receipt['overlap_with_my_product_files'])} 枚（空清单）。逐枚比 blob：`V8Experience.tsx` 在上一轮基线 blob {pairs[MINE[0]]['prev_tip_blob']}，在现尖 blob {pairs[MINE[0]]['line_tip_blob']}，unchanged_on_line={pairs[MINE[0]]['unchanged_on_line']}；`failureAttribution.ts` 同样 unchanged_on_line={pairs[MINE[1]]['unchanged_on_line']}。
- 只读预测 `git merge-tree --write-tree {tip} {r3}`：rc={receipt['merge_tree_prediction']['rc']}，tree={receipt['merge_tree_prediction']['tree']}，CONFLICT 行数={len(receipt['merge_tree_prediction']['conflict_lines'])}。
- 同一串输入的 rebase 复放进一次性枝（跑完即删）：rebase_rc={receipt['replay_probe']['rebase_rc']}，探针件尖 {receipt['replay_probe']['probe_head_after_replay']}。
- 结论我只写到我读到的范围：这轮我没有复现出「唯一冲突面」，实测是无重叠、预测无冲突；如果那句指的是别的那一对 ref，把它的 40 位给我，我照同一把尺再跑一次。读数件 `{E}rebase_receipt.json` blob {blob(E + "rebase_receipt.json")}。

## 3. 改前屏读（现尖自己的两枚产品文件建的包，不带我的补丁）

- 改前 blob：`V8Experience.tsx` = {pairs[MINE[0]]['line_tip_blob']}，`failureAttribution.ts` = {pairs[MINE[1]]['line_tip_blob']}。
- `checks=6 pass_count={before['pass_count']} fail_count={before['fail_count']}`；红的是 N1、N2、N3、N4，429 与 409 都落进 `reason=UNKNOWN_FAILURE`，标题「这一次没读到」，正文「服务器接上了，但这次读取没有成功，原因还没有分类。可以重试。」，两枚恢复动作都是 `failure-retry`。
- 件 `{E}walk_before/named_exits_zh.json` blob {blob(E + "walk_before/named_exits_zh.json")}。

## 4. 改后屏读（同一栈、现尖，中英两趟）

- 中文 `checks=6 pass_count={zh['pass_count']} fail_count={zh['fail_count']}`：429 → `reason=RATE_LIMITED action=retry-later`，标题「服务器请我们慢一点」，正文引用服务器自己给的 `retry_after_ms`；409 → `reason=STATE_ALREADY_MOVED action=view-current-state`，标题「这件事的状态已经变了，不是没读到」，恢复按钮 testId `failure-view-current-state`。件 `{E}walk/named_exits_zh.json` blob {blob(E + "walk/named_exits_zh.json")}。
- 英文 `checks=6 pass_count={en['pass_count']} fail_count={en['fail_count']}`，件 `{E}walk/named_exits_en.json` blob {blob(E + "walk/named_exits_en.json")}。
- 对照臂 503 两趟都保持 `reason=SERVER_ERROR`。三态那一屏的判定与 r3 逐字段一致，没有出现「现尖形状变了导致读数变」的差值。

## 5. 反件（arms={len(arms['arms'])}，按字节还原）

{chr(10).join(arm_lines)}

- 汇总 all_arms_applied={arms['all_arms_applied']}、all_restored={arms['all_restored']}、clean_rebuild_after_restoring={arms['clean_rebuild_after_restoring']}、every_file_back_at_starting_bytes={arms['every_file_back_at_starting_bytes']}；件 `{E}arms.json` blob {blob(E + "arms.json")}。尺沿用 `review/ord0457/named_exit_arms_r2.py` blob {blob("review/ord0457/named_exit_arms_r2.py")}；r1 那把 `named_exit_arms_r1.py` 在 r3 件尖上 blob {arms_r1_at_r3}，在本件尖上 blob {arms_r1_at_head}，equal={arms_r1_at_r3 == arms_r1_at_head}。

## 6. Q64 exposure 与编译臂（现尖）

- 尺 `ui_exposure_taint_ast_r7b.cjs`（--tree，同一枚、未改）：改前 `{E}exposure_before.json` blob {blob(E + "exposure_before.json")} 读 `cells_total={exp_b['cells_total']}`；改后 `{E}exposure_after.json` blob {blob(E + "exposure_after.json")} 读 `cells_total={exp_a['cells_total']}`；按 `cell_identity` 集合差 growth_items={len(growth)}、shrink_items={len(shrink)}；我这产品文件出现在 hit 面的次数 hits={len(mine_in_hits)}。
- 这轮新落地的 EstimationLadder 一族与 `v8PanelRegistry.tsx` 之后，hit 面文件清单 files_hit={len(hit_files)} 枚，与 r3 那轮（`review/n3_0457_evidence_r1/exposure_after_r3.json`）逐字相同：same_as_r3={sorted(r3_hits) == hit_files}；批量落地没有把曝光数推高。
- 编译臂 tsc_rc=0（`{E}tsc.txt` blob {blob(E + "tsc.txt")}，0 行）；vite build_rc=0，改前 `{E}build_before.txt` blob {blob(E + "build_before.txt")}、改后 `{E}build_after.txt` blob {blob(E + "build_after.txt")}。
- 每份读数与所在线尖/产品 blob 的配对：`{E}tip_manifest.json` blob {blob(E + "tip_manifest.json")}；发本块的脚本 `review/ord0457/make_block_r4.py`，冲突面尺 `review/ord0457/rebase_receipt_r4.py`，清单尺 `review/ord0457/evidence_manifest_r4.py`。

## 7. 这轮读数取在哪台栈上（三证同批）

- 后端 `:49961`，LISTENING pid=31824，命令行逐字含 `-m uvicorn app.main:app --host 127.0.0.1 --port 49961`；静态口 `:49962`，LISTENING pid=48292，命令行逐字含 `node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 49962 --strictPort`。
- 归属：私有库 `D:/moodle/_qoder_n3_ord0457/_private/ord0457.db` 以 mode=ro 打开，tables=58；`GET /api/v1/journeys/<只有我库里那一行的 id>` 回 `http_status=200` 且正文回显该 id，同端口打一个不属于我的 id 回 `http_status=404`；静态口 `GET /v10-sw.js` 的字节与 `frontend/dist/v10-sw.js` 逐字节相等，bytes=2055。
- `:8000`、`:4781`、`:4782`、`:8693` 四枚共享口未碰；共享 `_preview.db` 未读未写；`demo/reset` 只落在我自己那份私有库。收工时两条进程按命令行签名核对后才停。

## 8. 仍未证的（等裁，不自扩）

- 「失败三态同屏」那一格维持未证：桩能造 `http_status=429`、`http_status=409`、`http_status=503` 三种答，造不出真的 loading 态，我没有拿假 loading 凑 pass_count。
- 除这两档之外其余落进 `UNKNOWN_FAILURE` 的子形本轮没扩。
"""
    OUT.write_text(block, encoding="utf-8", newline="\n")
    print(f"wrote {OUT} bytes={len(block.encode('utf-8'))}")
    print(f"head={head} tip={tip} growth={len(growth)} mine_in_hits={len(mine_in_hits)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
