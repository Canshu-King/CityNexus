"""Append ledger section 13.7 -- the 390x844 shape of the same cell, and the boundary it does not cross.

Same byte-preserving rules as r120: the block is written with the terminator already dominant in the
file, and the instrument refuses if the section it is closing is not where §13.6 left it.
"""
import io
import sys

PATH = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_GO_FROM_BLANK_REPORT.md"
text = io.open(PATH, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in text else "\n"
guard = "\u90a3\u6863\u7684\u540c\u4e00\u683c\u8fd8\u6ca1\u91cf"
if guard not in text:
    sys.exit("ABORT the §13.6 line this section closes is not in the report")
if text.count("### 13.7") > 0:
    sys.exit("ABORT section 13.7 already exists")
lines = [
    "",
    "### 13.7 390×844 同一格：按开了，六行来源对上六行存表（§13.6 第三条就此闭）",
    "",
    "先报尺的错，不报屏的错。第一次走 390×844 那档（臂 r121）印出 `STEPS_SUMMARY_PRESSED true`，可按完",
    "读回来仍是 `open=false`、行文本全空（`trial/results/20261026_gozero/bm121-tool-step-source-390.txt:21-25`）。",
    "查下去是 `tap()` 里 `click(...).catch(() => {})` 把点击的拒绝吞了 —— 尺把自己没按成这件事说成了",
    "「按过了」。修在 `9a559d6c78`：改成先用 Playwright 认容器的滚动、再把 click / scroll 的拒绝原文印成",
    "`CLICK_FAIL` / `SCROLL_FAIL`。**这条不改产品，也据此不给产品定性** —— 那一轮到底是被什么挡住，",
    "在拒绝被丢掉之后已经追不回来；能说的只有「修好尺之后的同一档按开了」。",
    "",
    "重跑（臂 r122，同一现尖栈 :14464 / :60364、又一个全新空库、同一句话术）：",
    "",
    "    STEPS_BEFORE  open=false  summary「Agent 工具时间线 · 8 步」        （bn122…390.txt:17）",
    "    STEPS_AFTER   open=true rows=8 source_rows=6 amap=6 not_recorded=0 （:20、:21）",
    "    SOURCE_HIT_PROOF 236x26@600 inViewport=true visible=true           （:22）",
    "    FINAL_CLEAN true                                                   （:23）",
    "",
    "第二行全文读回：`2 查找公开地点 完成 8 处地点 来源：高德地图 · 真供应商已核实 03:27:17 · 0.3 秒`。",
    "只读探针把同一条旅程的存表数出来对上（`bn123-step-provider-census-390.txt:4-7`）：八条 AgentRunStep，",
    "其中六条 `discover_places` 带 provider=amap 与核实状态，两条（`ask_traveler`、`save_draft_itinerary`）",
    "两者都没有。六对六、无「未记录」行 —— 因为这一轮没有那条只带 provider 不带核实状态的 `route_public_places`。",
    "",
    "边界要画住，别把「能按开」外推：r121 那一轮是十五步、来源行落在 y=1204（844 高的视口之外，要滚动",
    "才看得见）；r122 这一轮只有八步、来源行在视口内。也就是说**还没在「步数多到 summary 自己落到视口外」",
    "的形状下按成过一次**，那一格仍归 #344，不当已闭。",
    "",
    "现尖工作树的临时携带已复原，并现读回验：`E:/_cmdr_tip_113` 的 `git status --porcelain=v1` 为 0 行，",
    "`WorkspaceActions.tsx` 的 blob 从 `82a158d91bf0…`（`599ed95b76` 那枚）回到 `74019c5573ab…`",
    "（`dea0328e0b` 同代），vite 仍回 200。§13.6 第二条就此销掉。",
    "",
    "同代账（本次推上去的四笔，远端已回验 `dc7b5e6d5d`）：`95997901dd` 步骤披露的屏证与对账、",
    "`9a559d6c78` 尺不吞点击拒绝、`c35397222d` 390×844 同一格、`dc7b5e6d5d` 把提交门的自测装进发布门。",
    "",
]
block = nl.join(lines) + nl
io.open(PATH, "w", encoding="utf-8", newline="").write(text + block)
after = io.open(PATH, encoding="utf-8", newline="").read()
print("BYTES_BEFORE", len(text.encode("utf-8")), "BYTES_AFTER", len(after.encode("utf-8")))
print("PREFIX_INTACT", after.startswith(text[:4000]))
print("SECTION_137_COUNT", after.count("### 13.7"))
print("TAIL", repr(after[-32:]))
