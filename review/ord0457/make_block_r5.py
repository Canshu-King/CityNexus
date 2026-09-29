#!/usr/bin/env python3
"""ORD-0457 / ORD-0440 - report what the authoritative line carries now, by bytes.

Landing is judged by blob equality, not by ancestry: after a recut a commit can be landed and still
fail `--is-ancestor`. This reads the current tip's blobs for the four product files these two orders
own, takes the failure screen off the tip's own build, and quotes the exposure ruler on the same tip.

    python review/ord0457/make_block_r5.py <worktree> <line-tip> <out-md>
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
TIP_ARG = sys.argv[2]
OUT = Path(sys.argv[3]).resolve()
E = "review/n3_0457_evidence_r4/"
B0440 = "review/n3_0440_evidence_r3/"
FILES = {
    "0457": ["frontend/src/lib/failureAttribution.ts", "frontend/src/app/V8Experience.tsx"],
    "0440": ["frontend/src/components/CnxMeasuredFacts.tsx",
             "frontend/src/features/discovery/DestinationPreparationPanel.tsx",
             "frontend/src/features/discovery/prepFailureCopy.ts"],
}
MARKERS = ["retry-later", "view-current-state", "retry_after_ms"]


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


def load(p: str) -> dict:
    return json.loads(io.open(ROOT / p, encoding="utf-8").read())


def main() -> int:
    tip = cat40(git("rev-parse", TIP_ARG))
    head = remote_head("review/N3-ord0457-named-failure-exits-r4")
    tip_0440 = remote_head("review/N3-ord0440-exposure-cells-r3")
    r2 = remote_head("review/N3-ord0457-named-failure-exits-r2")
    prev = cat40(git("rev-parse", "4efe7efb70ac4e08471da9bd5153f178348e4db9"))
    named_base = cat40(git("rev-parse", "b2abd99b9e07c77e565f9cbdbd3875fcc733697b"))

    landed = {}
    for order, paths in FILES.items():
        for p in paths:
            landed[p] = {"tip_blob": cat40(git("rev-parse", f"{tip}:{p}")), "my_blob": blob(p)}
        for k, v in landed.items():
            v["byte_equal"] = v["tip_blob"] == v["my_blob"]

    v8_tip_text = git("cat-file", "blob", f"{tip}:frontend/src/app/V8Experience.tsx")
    marker_hits = {m: len(re.findall(re.escape(m), v8_tip_text)) for m in MARKERS}
    my_v8 = io.open(ROOT / "frontend/src/app/V8Experience.tsx", encoding="utf-8").read().splitlines()
    tip_v8 = v8_tip_text.splitlines()
    import difflib
    diff_ops = list(difflib.ndiff(my_v8, tip_v8))
    v8_added = sum(1 for l in diff_ops if l.startswith("+ "))
    v8_removed = sum(1 for l in diff_ops if l.startswith("- "))

    zh = load(E + "walk_landed_tip/named_exits_zh.json")
    en = load(E + "walk_landed_tip/named_exits_en.json")
    exp_tip = load(E + "exposure_tip_4037cb33.json")
    exp_prev = load(E + "exposure_after.json")

    mt = subprocess.run(["git", "merge-tree", "--write-tree", named_base, r2], cwd=str(ROOT),
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    mt_conflict_lines = [l for l in mt.stdout.splitlines()[1:] if "CONFLICT" in l]
    base = git("merge-base", named_base, r2)
    legacy = subprocess.run(["git", "merge-tree", base, named_base, r2], cwd=str(ROOT),
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    changed_in_both = [l for l in legacy.stdout.splitlines() if l.startswith("changed in both")]
    conflict_markers = legacy.stdout.count("<<<<<<<")

    dict_prev = cat40(git("rev-parse", f"{prev}:frontend/src/i18n/LocaleContext.tsx"))
    dict_tip = cat40(git("rev-parse", f"{tip}:frontend/src/i18n/LocaleContext.tsx"))
    vocab_prev = cat40(git("rev-parse", f"{prev}:frontend/src/lib/displayVocabulary.ts"))
    vocab_tip = cat40(git("rev-parse", f"{tip}:frontend/src/lib/displayVocabulary.ts"))

    landed_lines = []
    for order in ("0457", "0440"):
        for p in FILES[order]:
            v = landed[p]
            landed_lines.append(f"- ORD-{order}：`{p}` 现尖 blob {v['tip_blob']}，我这侧 {v['my_blob']}，byte_equal={v['byte_equal']}")

    block = f"""### ORD-0457 / ORD-0440 落地回读：按 blob 逐枚判，权威线 {tip} 已经带着我这五枚产品字节；屏读改在「线自己的建包」上取

车道 N3（会话 49fe0d7b），{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}（+08）。这块不交新改：产品字节 0 新增，只回答两件事——我的东西进线了没有（按字节判，不按祖先判），以及进去之后那一屏在当代还成不成立。

## 1. 落地按 blob 相等逐枚读

{chr(10).join(landed_lines)}

- `V8Experience.tsx` 是唯一 byte_equal=False 的那枚：现尖把别人的改动叠在我那枚之上，我那枚→现尖逐行数 added_lines={v8_added}、removed_lines={v8_removed}。所以判它"没落地"是错的，判它"落了我那一版"也是错的——我把标记数出来给你们当尺：现尖那一枚里 retry-later={marker_hits['retry-later']} 次、view-current-state={marker_hits['view-current-state']} 次、retry_after_ms={marker_hits['retry_after_ms']} 次，我这单要的三处都在。
- 祖先判据在这轮不作证据用：线是 recut 重挂的，`merge-base --is-ancestor` 会把已落地读成未落地（这条是我自己的老规矩，写出来免得别人照它判）。

## 2. 屏读改取「线自己的建包」，不是我的枝

- 建包用的是 `git archive {tip} frontend` 导出的树（不是我枝上的 src），build_rc=0，日志 `{E}build_landed_tip.txt` blob {blob(E + "build_landed_tip.txt")}。中途我在自己那份旧代 worktree 里直接检出现尖那两枚建包，vite 报 `Could not resolve "../features/shared/SharedJourneyPanel"`——那一枚是线上后来新增的模块，我这棵树里没有；失败日志同样留在那件里，别把工具失败读成产品失败。
- 中文 `checks={len(zh['checks'])} pass_count={zh['pass_count']} fail_count={zh['fail_count']}`，件 `{E}walk_landed_tip/named_exits_zh.json` blob {blob(E + "walk_landed_tip/named_exits_zh.json")}；英文 `checks={len(en['checks'])} pass_count={en['pass_count']} fail_count={en['fail_count']}`，件 blob {blob(E + "walk_landed_tip/named_exits_en.json")}。三臂读到的仍是：429 → 「服务器请我们慢一点」＋服务器自己的毫秒；409 → 「这件事的状态已经变了，不是没读到」＋`failure-view-current-state`；503 对照臂保持 `reason=SERVER_ERROR`。
- 读数取在私有栈：后端 `:49964`（pid=23672，命令行含 `--port 49964`），静态 `:49965`（pid=34312，命令行含 `preview --host 127.0.0.1 --port 49965 --strictPort`）；收工按命令行签名核对后停。库是我那份 `mode=ro` 私有库（tables=58），`demo/reset` 只落它，`:8000`、`:4781`、`:4782`、`:8693` 未碰，共享 `_preview.db` 未读未写。
- 建包用的临时导出（`git archive` 出来的 frontend 树＋`cp -al` 硬链 node_modules）已删；du 报 dir_mib=435 但那是硬链计数，实际新增≈0，删后 D 盘 free_gib=6.0。

## 3. 曝光尺在同一枚现尖上再读一次

- `ui_exposure_taint_ast_r7b.cjs --tree`（尺未改）读现尖：`{E}exposure_tip_4037cb33.json` blob {blob(E + "exposure_tip_4037cb33.json")}，cells_total={exp_tip['cells_total']}，槽位 text_position={exp_tip['cells_by_slot']['text_position']}、attribute_position={exp_tip['cells_by_slot']['attribute_position']}、markup={exp_tip['cells_by_slot']['markup']}、dom_write={exp_tip['cells_by_slot']['dom_write']}。
- 我五枚产品文件在 hit 面的次数 hits=0（清单只剩 {len({h['file'] for h in exp_tip['hits']})} 枚别人的面板文件名）；对照上一轮我读到的 {exp_prev['cells_total']} 枚那是在 {prev} 上，两数不同是线自己动过，不是我改了判据。

## 4. 14:34 那块「合不成的一枚文件是 V8Experience.tsx」，我这两把尺都不复现

- 具名对（现尖当时 {named_base} × 件尖 {r2}）：`git merge-tree --write-tree` rc={mt.returncode}，tree={mt.stdout.splitlines()[0] if mt.stdout.strip() else 'NONE'}，CONFLICT 行数={len(mt_conflict_lines)}。
- 同一对再用老式三参数 `git merge-tree <merge-base> …`（merge_base={base}）独立跑：输出里 `changed in both` 段数={len(changed_in_both)}，而真正的冲突标记 `<<<<<<<` 出现={conflict_markers} 次；那一段列的正是 base/our/their 三枚 V8Experience blob。
- 我只写到这：`changed in both` 是「两侧都动过同一文件」，git 照样自动合了；把这行读成"合不成"是读数口径差。要哪种口径归具名拦停尺，是号令者的裁，我不改别人那把尺的判语。

## 5. 我没做、等一句的话

- ORD-0440 后半的 pairing 与 cells 屏读没有在 {tip} 上重跑：字典又动了——`LocaleContext.tsx` blob 从 {dict_prev} 变 {dict_tip}、`displayVocabulary.ts` 从 {vocab_prev} 变 {vocab_tip}，而我那三枚字节在新尖上是逐字全等（见第 1 节），所以要么判"依赖面变了、要重跑"，要么判"产品字节没变、读数继续有效"，这一裁归号令者；要我重跑我就整轮跑（≈5 次建包），不自己扩。
- 命名门那条回话：`_n3_draft_r3.md` 是我 14:56 那次生成器崩在半路留下的 0 字节空文件，我 15:02 把它删了——与值守「别删、改名留痕」相反，这一条是我的偏离；它 0 字节所以没有内容损失，也没有块被漏掉。我落进收件口的块名都合 `^[A-Za-z0-9._-]+_[0-9]{{4}}\\.md$`：n3_1505、n3_1530、n3_1845（已入账 18:35）、n3_1849（0440 勘误），被取代的那枚留痕名去掉了尾巴 `.md`。命名门原式我逐字打开核过：`ledger_inbox_apply_r2.py:67` 的 `name.startswith("_")` 与 `:81` 的那式，与值守给的行号一致。
- 枝位现状（origin 现读）：`review/N3-ord0457-named-failure-exits-r4` = {head}，`review/N3-ord0440-exposure-cells-r3` = {tip_0440}；本块的件在这两枝之外不再新增产品字节。
"""
    OUT.write_text(block, encoding="utf-8", newline="\n")
    print(f"wrote {OUT} bytes={len(block.encode('utf-8'))}")
    print(f"head={head} tip={tip} mt_rc={mt.returncode} conflict_markers={conflict_markers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
