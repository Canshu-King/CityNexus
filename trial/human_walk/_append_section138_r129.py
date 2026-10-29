"""Append ledger section 13.8 -- the long-page reachability reading, and the negative control that came with it.

Byte rules as in r120/r126: keep the file's own terminator, refuse if the section being closed is not
where it was left, refuse if 13.8 already exists.
"""
import io
import sys

PATH = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_GO_FROM_BLANK_REPORT.md"
text = io.open(PATH, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in text else "\n"
if "\u90a3\u4e00\u5f62\u72b6\u4ecd\u672a\u6d4b" not in text and "\u6ca1\u5728\u300c\u6b65\u6570\u591a\u5230" not in text:
    sys.exit("ABORT the §13.7 boundary line this section closes is not in the report")
if text.count("### 13.8") > 0:
    sys.exit("ABORT section 13.8 already exists")
lines = [
    "",
    "### 13.8 长页面那一格：summary 一开始在视口外，滚一下仍按得开（附一枚现成的负对照）",
    "",
    "#344 当时欠的那句话不是「能不能按开」，而是「页面长到 summary 自己落到 844 视口之外时还能不能按开」。",
    "这一格不必等模型再跑长一轮 —— 旅客本来就会把上面那条事件时间线展开。臂 bo128 就照这个动作走：先按",
    "`.rev-workspace-timeline summary`（`bo128-tool-step-source-390.txt:17`、`:18`，HIT true、按开了），再去够",
    "下面那条步骤时间线的 summary。够之前现读几何（`:20`）：",
    "",
    "    LONG_PAGE_GEOMETRY  viewport=844  summary top=924 bottom=968 h=44  head top=0 bottom=65  open=false",
    "",
    "也就是说 summary 整条都在视口外（924 > 844），上方 sticky 头占 0–65。接着按：`HIT steps-summary true`",
    "（`:21`，滚动后中心命中测试落在它自己身上）、按完 `STEPS_AFTER open=true rows=8`（`:23`）——",
    "**滚一下按得到，且没有哪个键被页头接走**。于是 §13.7 画的那条边界就地闭掉，r121 那回「按不动」",
    "也彻底不当成产品读数：它的成因已由这一枚正面读数替掉。",
    "",
    "随行的负对照要单独记一笔，因为它比预想的有用。bo128 跑之前，`E:/_cmdr_tip_113` 已经把携带的那枚",
    "文件还原回原生代（代次票 `bo128-generation-ticket.txt:1-3`：尖 `dea0328e0b…`、dirty 0 行、",
    "`WorkspaceActions.tsx` 的 blob `74019c5573ab…`）。于是这一轮屏上 `source_rows=0`、`SOURCE_HIT_PROOF null`",
    "（`:16`、`:25`）—— 不是尺坏了，是那一代本来就没有来源行。这条负对照把「`599ed95b76` 带来的行」和",
    "「面板本来就印着某些字段」分开：同一个选择器、同一条旅客路径、同一个栈，有那枚 blob 就有六行，",
    "没有那枚 blob 就一行都没有。",
    "",
    "顺手把尺的另一格钉住：bo128 里 `VERDICT DISCLOSURE_MISSING_ON_SCREEN rows=8` 看着像红，其实是上面",
    "那句「那一代没有披露行」。读这类臂必须先认代次，否则负对照会被当成回归 —— 这条已在票里写明，",
    "以后同形制的臂一律随一张代次票落盘。",
    "",
]
block = nl.join(lines) + nl
io.open(PATH, "w", encoding="utf-8", newline="").write(text + block)
after = io.open(PATH, encoding="utf-8", newline="").read()
print("BYTES_BEFORE", len(text.encode("utf-8")), "BYTES_AFTER", len(after.encode("utf-8")))
print("PREFIX_INTACT", after.startswith(text[:4000]))
print("SECTION_138_COUNT", after.count("### 13.8"))
print("TAIL", repr(after[-30:]))
