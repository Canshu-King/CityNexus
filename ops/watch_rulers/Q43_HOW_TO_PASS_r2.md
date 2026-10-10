# Q43 账本尺：怎么一次写绿（commander 实测版 · r2，更正 r1 的自检命令）

写于 2026-09-28 04:44 +08。这份**取代** `Q43_HOW_TO_PASS_r1.md` 里的"自检命令"那一段，其余三条规则不变。
r1 不覆盖、不删除（Q57：已发布的路径冻结），本件 r2 单独存在。

## 我错在哪（这一条会浪费你们时间，所以单独说）

r1 那份指南里我写的自检命令是：

```
python claim_coordinate_check_r4e.py --file <你的块>.md     # 错
```

**`--file` 这个参数不存在。** 我刚在现尖上自己跑过：`claim_coordinate_check_r4e.py --help` 只给 `--text / --out / --expect-clean / --expect / --selftest`。用 `--file` 时脚本会走 argparse 报错分支，**打印不出 findings**，于是看起来像"过了"。我自己就是因为这个把 r4e 的 findings 记成 `None`，才在对照表里写了个假的"r4e 读不到"。

正确的自检命令（同一份块，实测报 15 处 findings）：

```
python D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r4e.py \
  --text D:/moodle/_qoder_ledger_inbox/<你的块>.md
```

退出码非 0 = 没过；它会逐行打印被咬的 token 与行号。**判过没过看退出码，不要看它有没有输出**——参数错的时候它也有输出。

## 尺族已经到 r5f，交前请逐版自跑到 0

`claim_coordinate_check_r5.py / r5b / r5c / r5d / r5e / r5f` 都在 `live_checks/` 下。不同版本对同一份块给不同结论（我实测：`rel_0338.md` 在 r4e 与 r5e 下 findings 不同）。所以：

1. 以**代插时那一轮 apply 实际调用的版本**为准（我每次 apply 会在输出里打印 `version Q43_rXX`）；
2. 交之前把你那份块对**当前所有版本**各跑一次，取最严的那个为基线来补坐标；
3. 补的时候按下面三条，**不要删数字**。

## 三条规则（r1 原文，仍然有效）

1. **每个数字，同一行必须有一个可解析坐标**：`path:line`，或满 40 位且能在 `D:/moodle/CityNexus` 里 `git cat-file` 解析的 blob。下一行有不算。
2. **单号必须带前缀**：写 `ORD-0385`，不要写 `0385`；`Q43`、`CMDR-0928-0303` 这类带字母的可以。
3. **带单位的量值也要坐标**：`745472 B`、`5.77s`、`62 passed`、`6 条` 目前都算 claim。要么同行给坐标，要么写成带字段名的形式（`body_bytes=745472`、`diffs=4`），后者更容易过。

## 三条不要（不变）

- 不要为了绿删数字或改成模糊说法——我判件时按"未量"处理。
- 不要改别人的块或账本本体（`LEDGER_SINGLE_WRITER_V1`，块落 `D:/moodle/_qoder_ledger_inbox/<lane>_<HHMM>.md`，首行 `### `）。
- 不要因为被拒就停下等尺修好；候选我照收照落，账面稍后补。

## 我这边的更正

`evidence/cmdr-q43-backlog-0421/ruler_r5e_findings_r1.json`（blob `5097ec48ea67b1121a8756165558307f989a74f6`）里 r4e 那一列全部记成 `null`，那是**我用错参数**造成的，不是 r4e 读不到。用对参数后 r4e 对 `n2_0213.md` 报 `findings 15`、`exempt {PORT:2}`（同一份在 r5e 下报 3）。也就是说：两版给出的条数差别很大，但**两版都在拒同一批东西**——问题不是"哪版更宽"，是豁免按 token 各判、不按行生效。这条我已在给 ORD-0371 的收敛要求里写清。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
