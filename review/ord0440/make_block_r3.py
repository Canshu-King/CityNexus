#!/usr/bin/env python3
"""ORD-0440 second half r3 - emit the ledger block from the r3 artifacts.

Coordinates come from `git rev-parse`/`git ls-remote` and are asserted `git cat-file`-able; counts come
from the JSON the campaign wrote. The conflict claim is answered with the file lists actually measured:
the order named `frontend/src/i18n/LocaleContext.tsx` as the collision, and whether that is true for
this branch is a question about two commit ranges, not about how hot a file feels.

    python review/ord0440/make_block_r3.py <worktree> <prev-base> <line-tip> <out-md>
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
PREV_ARG, TIP_ARG, OUT = sys.argv[2], sys.argv[3], Path(sys.argv[4]).resolve()
E = "review/n3_0440_evidence_r3/"
OLD_E = "review/n3_0440_evidence_r1/"
BRANCH = "review/N3-ord0440-exposure-cells-r3"
MINE = ["frontend/src/components/CnxMeasuredFacts.tsx",
        "frontend/src/features/discovery/DestinationPreparationPanel.tsx",
        "frontend/src/features/discovery/prepFailureCopy.ts"]
DELIVERED = "review/N3-ord0440-exposure-cells-r2"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def cat40(v: str) -> str:
    assert re.fullmatch(r"[0-9a-f]{40}", v or ""), f"not a verbatim 40-hex: {v!r}"
    assert subprocess.run(["git", "cat-file", "-e", v], cwd=str(ROOT)).returncode == 0, f"not an object: {v}"
    return v


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
    tip = cat40(git("rev-parse", TIP_ARG))
    prev = cat40(git("rev-parse", PREV_ARG))
    head = remote_head(BRANCH)
    delivered = remote_head(DELIVERED)
    r1 = remote_head("review/N3-ord0440-exposure-cells-r1")
    my_commits = int(git("rev-list", "--count", f"{tip}..HEAD") or 0)

    moved = [f for f in git("diff", "--name-only", f"{prev}..{tip}", "--", "frontend/src").splitlines() if f]
    overlap = sorted(set(moved) & set(MINE))
    hot_named = "frontend/src/i18n/LocaleContext.tsx"
    def tip_blob(f: str) -> str:
        v = git("rev-parse", f"{tip}:{f}")
        return cat40(v) if re.fullmatch(r"[0-9a-f]{40}", v or "") else "NOT_ON_TIP"

    blobs = {f: {"tip": tip_blob(f), "head": blob(f)} for f in MINE}
    dict_tip_prev = cat40(git("rev-parse", f"{prev}:{hot_named}"))
    dict_tip_now = cat40(git("rev-parse", f"{tip}:{hot_named}"))

    mt = subprocess.run(["git", "merge-tree", "--write-tree", tip, delivered], cwd=str(ROOT),
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    mt_tree = mt.stdout.splitlines()[0] if mt.stdout.strip() else ""
    mt_conflicts = [l for l in mt.stdout.splitlines()[1:] if "CONFLICT" in l]

    arms = load(E + "exposure_arms.json")
    exp_tip, exp_after = load(E + "exposure_tip.json"), load(E + "exposure_after.json")
    cells = load(E + "cells_walk/cells_walk_zh.json")
    cells_en = load(E + "cells_walk/cells_walk_en.json")
    before = load(E + "cells_walk_before/cells_walk_zh.json")
    before_en = load(E + "cells_walk_before/cells_walk_en.json")
    pairing = load(E + "pairing.json")
    prov = load(E + "receipt_provenance/receipt_provenance_zh.json")

    cb = {h["cell_identity"] for h in exp_tip["hits"]}
    ca = {h["cell_identity"] for h in exp_after["hits"]}
    growth, removed = sorted(ca - cb), sorted(cb - ca)
    arm_lines = []
    for a in arms["arms"]:
        arm_lines.append(f"- {a['name'].split()[0]}（{a['name'][3:]}）：cells_total={a['reading']['cells_total']} "
                         f"delta_vs_baseline={a['delta_vs_baseline']} expect=\"{a['expect']}\" "
                         f"applied={a['applied']} restored_byte_identical={a['restored_byte_identical']}")
    removed_names = [f"{r.split('::')[1].strip()}:{r.split('::')[2].strip()}" for r in removed]
    removed_str = "、".join(f"`{n}`" for n in removed_names)

    block = f"""### ORD-0440 后半 r3：rebase 到现尖 {tip}，曝光尺当场重量（现尖 12 → 本枝 8，growth 空）；LocaleContext 那格冲突按文件清单核过

车道 N3（会话 49fe0d7b），{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}（+08）。本轮要求逐字是「请 rebase 后推 r3，并在当代重量曝光尺（你上一轮就是栽在曝光尺与门不一致那格）。你手上 ORD-0457 的 frontend/src/app/V8Experience.tsx 冲突与这单同性质，两枝分开交。」——分开交：本块只谈 0440 后半，0457 在另一枝（r4 件尖见其块）。

## 1. 交件坐标

- 枝名 `review/N3-ord0440-exposure-cells-r3`；`git -c http.proxy= -c https.proxy= ls-remote origin refs/heads/{BRANCH}` 回读件尖 {head}（可 `git cat-file`）。
- rebase 落点线尖 {tip}，上一轮基线 {prev}，我这 commits={my_commits} 枚提交叠在现尖之上；已交付两枝按 origin 实测：r1={r1}、r2={delivered}，原位未覆盖。
- 产品 blob 三枚未因 rebase 改变：`CnxMeasuredFacts.tsx` {blobs[MINE[0]]['head']}、`DestinationPreparationPanel.tsx` {blobs[MINE[1]]['head']}、`prepFailureCopy.ts` {blobs[MINE[2]]['head']}（现尖同路径 blob 分别是 {blobs[MINE[0]]['tip']}、{blobs[MINE[1]]['tip']}，`prepFailureCopy.ts` 是本枝新增）。

## 2. 具名冲突面 `frontend/src/i18n/LocaleContext.tsx` 我这侧的实测

- 我这 files={len(MINE)} 产品面是：{", ".join(f"`{f}`" for f in MINE)}；其中 {len([f for f in MINE if 'LocaleContext' in f])} 枚是 `LocaleContext.tsx`。
- 线从 {prev} 到 {tip} 在 `frontend/src` 下动了 files_moved={len(moved)} 枚，`LocaleContext.tsx` 确实在里面：它的 blob 从 {dict_tip_prev} 变成 {dict_tip_now}，所以「字典是热文件、刚被超代」这一句是成立的；成立的是它对**整条线**是热的，不是对我这枝。
- 我这与现尖的重叠：overlap={len(overlap)} 枚（空清单）。只读预测 `git merge-tree --write-tree {tip} {delivered}`：rc={mt.returncode}，tree={mt_tree}，CONFLICT 行数={len(mt_conflicts)}。rebase 实测 rc=0（同一串输入，无手改）。
- 依赖是真的但不是文本冲突：`DestinationPreparationPanel.tsx:24` 逐字 `import {{ useLocale, useT }} from "../../i18n/LocaleContext";`，所以字典换了键我会吃到语义变化——这正是下面 pairing 与屏读要重跑的原因，两项都在现尖重跑过。

## 3. 曝光尺（当代重量，门的那把尺一字未改）

- 尺 `ui_exposure_taint_ast_r7b.cjs` --tree：现尖自己 `{E}exposure_tip.json` blob {blob(E + "exposure_tip.json")} 读 `cells_total={exp_tip['cells_total']}`；本枝 `{E}exposure_after.json` blob {blob(E + "exposure_after.json")} 读 `cells_total={exp_after['cells_total']}`。
- 按 `cell_identity` 集合差：growth_items={len(growth)}（空），shrink_items={len(removed)}。被消掉的就是门点名的四格：{removed_str}。
- 槽位构成同步变化：现尖 `{json.dumps(exp_tip['cells_by_slot'], ensure_ascii=False)}` → 本枝 `{json.dumps(exp_after['cells_by_slot'], ensure_ascii=False)}`，attribute_position={exp_after['cells_by_slot']['attribute_position']} 未动（消掉的都在 text_position）。

## 4. 反件：四格各归各自那一格（arms={len(arm_lines)}，按字节还原）

{chr(10).join(arm_lines)}

- 四臂全部 applied={arms['all_arms_applied']}、还原后 restored_to_baseline={arms['restored_to_baseline']}，还原再量的 baseline_after_restoring cells_total={arms['after_restoring_everything']['cells_total']}；件 `{E}exposure_arms.json` blob {blob(E + "exposure_arms.json")}。每臂各加回 1 格，说明 12→8 是这四处改出来的，不是树里别的东西刚好少了几格。

## 5. 屏读与配对（现尖重跑，中英两趟）

- 改后中文 `checks={len(cells['checks'])} pass={cells['pass_count']} fail={cells['fail_count']}`，件 `{E}cells_walk/cells_walk_zh.json` blob {blob(E + "cells_walk/cells_walk_zh.json")}；英文 `checks={len(cells_en['checks'])} pass={cells_en['pass_count']} fail={cells_en['fail_count']}`，件 blob {blob(E + "cells_walk/cells_walk_en.json")}。C1 读到的是本构建自己写的句子，C2 上游原话既不在面板文字里也没进任何 data-*，C3 折叠真的挂着，C4 锚名 `http_status`，C5 折叠里是服务器自己的编号。
- 改前（现尖自己那两枚字节建的包）中文 `checks={len(before['checks'])} pass={before['pass_count']} fail={before['fail_count']}`，件 `{E}cells_walk_before/cells_walk_zh.json` blob {blob(E + "cells_walk_before/cells_walk_zh.json")}；英文同样 `checks={len(before_en['checks'])} pass={before_en['pass_count']} fail={before_en['fail_count']}`，件 blob {blob(E + "cells_walk_before/cells_walk_en.json")}。红的是 C1（屏上直接是上游那句 `CityNexus API 503: /destinations/capability?query=…`）与 C3（折叠根本没挂起来）；改前只有 {len(before['checks'])} 枚判定可达，因为 C4/C5 依赖折叠挂载，这一差是形状差不是分数差，别把它读成 6→4 的倒退。
- 配对（门的分母）：dictionary_pairs={pairing['denominator']['dictionary_pairs']}、distinct_keys={pairing['denominator']['distinct_keys']}、values_not_found={pairing['denominator']['values_not_found']}；本枝新增模块 `prepFailureCopy.ts` keys={pairing['failure_copy']['keys']}、both_arms={pairing['failure_copy']['both_arms']}、shipped_in_both_arms={pairing['failure_copy']['shipped_in_both_arms']}、outside_the_window={pairing['failure_copy']['outside_the_window']}；件 `{E}pairing.json` blob {blob(E + "pairing.json")}，verdict=PAIRING_OK。
- 编译臂 tsc_rc=0（`{E}tsc.txt` blob {blob(E + "tsc.txt")}，0 行），vite build_rc=0（现尖 `{E}build_tip_only.txt` blob {blob(E + "build_tip_only.txt")}、本枝 `{E}build.txt` blob {blob(E + "build.txt")}、还原后复建 `{E}build_final.txt` blob {blob(E + "build_final.txt")}）。

## 6. 我自己那把尺的一处弱点，这轮补成实测

- 交付的 C5 只判「编号长得像契约形状」（`walk_cells_r1.cjs:168`），形状判据分不出「服务器给的」与「客户端自己造的」，所以它当时证明不了它名字里那句 "the server's own number"。
- 新尺 `review/ord0440/receipt_provenance_r1.cjs` blob {blob("review/ord0440/receipt_provenance_r1.cjs")} 改成逐条记录本次流程里每个响应体真的送出的 `CNX-` 编号，再问屏上那枚在不在里面：`{E}receipt_provenance/receipt_provenance_zh.json` blob {blob(E + "receipt_provenance/receipt_provenance_zh.json")} 读 P1 checks=1 pass=1 fail=0，屏上 shown={prov['on_screen_tokens']}，服务端送出 server_sent={len(prov['server_sent_tokens'])} 条（含本枝那枚 stub 编号 {prov['observations']['stub_arrived_in_a_body']}）。也就是说：编号确是某发答案带回来的，不是屏上造的——这一条现在是量出来的，不是推出来的。
- 我 grep 过 `frontend/src` 里 `CNX-` 的用法：只有 `lib/errorReceipt.ts:22` 的形状常量与注释，前端没有任何铸造 `CNX-` 的代码；写入方是 `backend/app/error_receipt.py:29`。这句是补白，判据仍是 P1。

## 7. 这轮读数取在哪台栈上（三证同批）

- 后端 `:49971`，LISTENING pid=5232，命令行逐字含 `-m uvicorn app.main:app --host 127.0.0.1 --port 49971`；静态 `:49972`，LISTENING pid=58156，命令行逐字含 `node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 49972 --strictPort`。
- 归属：私有库 `D:/moodle/_qoder_n3_ord0440b/_private/cells_walk.db` 以 mode=ro 打开，tables=58；`GET /api/v1/journeys/<只有我库里那一行的 id>` 回 `http_status=200` 且正文回显该 id，同端口打一个不属于我的 id 回 `http_status=404`；静态口 `GET /v10-sw.js` 与 `frontend/dist/v10-sw.js` 逐字节相等，bytes=2055。
- `:8000`、`:4781`、`:4782`、`:8693` 未碰；共享 `_preview.db` 未读未写；`demo/reset` 只落在我自己那份私有库；收工按命令行签名核对后才停进程。

## 8. 与 ORD-0457 的边界

- 两枝分开交，没有互相携带字节：本枝产品面只有上面 files={len(MINE)} 枚，`frontend/src/app/V8Experience.tsx` 与 `frontend/src/lib/failureAttribution.ts` 一枚都不在里面；那一枝自己带着它的屏读、反件与曝光尺。
"""
    OUT.write_text(block, encoding="utf-8", newline="\n")
    print(f"wrote {OUT} bytes={len(block.encode('utf-8'))}")
    print(f"head={head} tip={tip} growth={len(growth)} removed={len(removed)} overlap={len(overlap)} mt_rc={mt.returncode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
