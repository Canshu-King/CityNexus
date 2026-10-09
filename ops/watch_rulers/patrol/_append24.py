import io
txt = r"""
- 值守拍 06:37 +08（42d1a6fa）**用共享仪表时撞出一个真缺陷，复现到行后交给它的主人，S3 已被叫醒在查**。
  - 触发：我想用 S3 的状态板（`ledger_state_board_r1.py`）回答"哪些单还开着、哪条车道停着"，跑出来 **退出码非 0、`selftest_passed: false`**。
  - 复现（不改她的代码，直接 `import` 她的 `Board`）：ORD-0032 的 `_status_source_line` 竟然是一段**描述这把尺自己的散文**——"三判两向 selftest（`ledger_state_board_r1.py --selftest` 退出码 0）：a 真单逐字，抽 ORD-0032 报 `REJECTED`…"。两个成因叠加：
    ① 状态词在"讲尺子的说明段"里被匹配到（`prose≠structure` 这次咬的是自测说明）；
    ② 来源行**被截断后**再拿去做逐字比对（串尾带 `...(+66)`），而判据是 `src in text` ⇒ 长行必然假红。我实测：该行前 60 字符 `in text` = True，整串 `in text` = False。
  - 我**先排除再下结论**：不是 CRLF（账本 `\r\n` 计数 0、裸 `\n` 51,556、`split("\n")` 后以 `\r` 结尾的行 0）。帖里也写清了我没测的部分（其余 101 枚有状态的单是否也来自散文；29 枚 `NOT_IN_LEDGER` 的口径我只认可其如实性、未逐枚核）。
  - 投递：总线 `issuecomment-5840577695`（回读 `matches: True`，尾行逐字取自 `CLOSING_LINE.txt`）+ 给 S3 一行定位（她 `cold`，所以这一发不会挂我的回合——**发前先查 runtimeState**，这条是 F 冻结 2h20m 换来的）。06:36:42 回验：`a17ae861 idle=1.2m`、最后一条是 `[tool_use Bash]` ⇒ **她醒了并在动手查**。
  - 同拍车队：idle>20 分钟从 5 降到 **3**（S4 06:31 交完 `S4-ast-taint_0632.md`、F 42.9m 等回话、HJ-P3 128m 等验收）。D/B/号令者/S1/S2 全在写。`quota_dead=0/6`。
  - 判据留一条给下一拍：**状态板在 S3 修好之前只能当线索，不能当依据**（它自己的自测是红的）。我要判断"谁欠活"仍然用 `pending_check`（点名+块头时间+idle）这一把。
"""
with io.open("PATROL_LOG.md","a",encoding="utf-8",newline="\n") as f: f.write(txt)
print("ok")
