## commander 亲测（我自己动手做的第一个突变复现）@2026-09-22T14:0x+08 —— **E-2 的 (c) 判定我独立重跑成立；过程中抓到两个会造出假"存活"的突变错**

### 一、复现（全程在我自己的干净导出树，权威树 0 改动）
```
树    D:\moodle\_qoder_cmdr_ref_20260921\v_13377d3 = git archive 13377d3 | tar -x
解释器 D:\moodle\CityNexus\.venv 3.12.14；DEEPSEEK_API_KEY 已 unset
靶    backend/app/anywhere_capability.py:629  `        http_status = None`  →  `        http_status = 0`
      锚点用正则 ^([ \t]*)http_status = None$ 定位，**命中数 1**（唯一），突变前后 sha256[:16]
      f7b59d0835341826 → 0d76ac5cc1337000（我先断言 mut != orig 才落盘，避免写出一个空突变）
命令  python -m pytest -q --no-header -p no:cacheprovider --tb=line <三文件>
读数  点名断言变红：test_qoder_provider_identity_leg.py::test_g16_the_four_attribution_fields_arrive_together_or_not_at_all ⇒ 1 failed
      三文件套件 ⇒ **1 failed / 28 passed**（与 `d2305848` 报的 1/28 **逐数相同**）
还原  写回原始字节后 sha256[:16] = f7b59d0835341826，**byte-exact True**（也与 E-2 自报的 cap 指纹同值 ⇒ 两棵树同一内容）
```
⇒ **ORD-0204 的 (c) 判 `KILLED` 我这一侧也算复现了；E-2 的方法与还原纪律我按亲测认，不按自述认。**
其余三靶（a/d KILLED、b SURVIVED 与 M17 一致）我仍按它的读数引用，标 `SELF_REPORTED（我未复跑）`——
只有 (c) 这一格现在是我自己的证据。

### 二、过程里差点造出两次假"存活"，都记下来（这是最容易被掩盖的那类错）
1. **我先假设这棵树是 CRLF**（记忆里 `main.py/services.py/v9.py` 是 CRLF），用 `\r\n` 拼锚点 ⇒ 命中数 0，脚本断言 `anchor not unique` **中止**。
   实测本文件：**CRLF 行数 0、LF 1544**——**这个提交上是 LF**。断言救了我：否则"什么也没改 + pytest 1 passed"会被写成"(c) SURVIVED"，
   而 (c) 恰恰是 F 那道 §8 门的承重件——这条假结论会一路传到仲裁那里。
2. **我第二次按 4 空格缩进猜锚点**，真实是 **8 空格**（在 `else:` 里）⇒ 又是命中 0 中止。
   ⇒ 结论：`^([ \t]*)…$` 捕获原缩进、并且**永远断言"突变后字节必须与原字节不同"**，
   这两条我现在写进自己的驱动，也建议 E-2/HARNESS/F 的脚本一起用。
   这条与 harness 老账同源：**"0 hits" 与 "no effect" 都不是"survived"**；一次"红集合里少了一条"必须先证明我的钉子真的钉进去了。

### 三、总线更正一条（我自己写错的归因）
`5771925544` 末尾名册里我写"13:58 后新块 = HJ-P2 交付待复跑"——**错**：那个块是 **HJ-P1 `1a986a24`** 的第二块（J5/J6）。
HJ-P2 到 14:03 无交付块。已在第 53 次敲门里向仲裁当面更正；账本里那条归因本来就写对（②标的是 HJ-P1）。
