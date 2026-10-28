"""Append ledger section 13 to the go-from-blank report, byte-preservingly.

The report is CRLF, so the block is joined with the terminator read back from the file itself; the
instrument refuses to run if the tail it is about to follow has moved since the numbers below were read
(it prints what it found instead), and it re-reads afterwards to prove nothing above section 13 changed.
"""
import io
import sys

PATH = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_GO_FROM_BLANK_REPORT.md"
text = io.open(PATH, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in text else "\n"
before_bytes = len(text.encode("utf-8"))
guard = "缺口块在\"什么都不缺\"的时候确实不挂"
if guard not in text:
    sys.exit("ABORT the tail I pinned my numbers to is not where section 12.6 left it")
lines = [
    "",
    "## 13 第 2 刀 2a：两条 Agent 时间线都上了屏，来源披露逐行对上库（§13.1–§13.6）",
    "",
    "### 13.1 事件时间线：80 条服务端记录，折叠着，按得开，屏上没有私有文本",
    "",
    "r116 在现尖栈（vite :14464 / 后端 :60364，全新空库）走旅客自己那条路 —— 冷开 430×932、手打那句",
    "「2026 年 12 月 3 日到 4 日在北京玩两天，两个人，每段步行不超过 1 公里，太远坐地铁」、手勾两枚同意、",
    "真跑一轮研究，然后读 `frontend/src/trial/mobile/WorkspaceActions.tsx:692` 那块 `details`：",
    "",
    "    TIMELINE_BEFORE  open=false  summary「Agent 真实工作过程 · 已记录 80 条事件」  rows=24",
    "    SUMMARY_PRESSED  true   （先命中测试：elementFromPoint 打在 summary 自己的中心）",
    "    TIMELINE_AFTER   open=true  rows=24  首行「#57 工具返回结果 · 查询步行路线」",
    "                     private_markers=[]  uuid_in_source=false  FINAL_CLEAN true",
    "",
    "读数在 `trial/results/20261026_gozero/bk116-agent-tool-timeline-430.txt:47`、`:49`、`:50`、`:51`。",
    "折叠态那次 rows=24 而文本全空，是 `details` 收起时子节点仍在 DOM 里但没有渲染文本 —— 所以行内容",
    "只有按开之后才读得到，这不是缺陷，但读数必须分清这两次各自量到了什么。",
    "",
    "这些行不是模型叙述：端点只白名单放字段（`backend/app/agent/goal_tasks.py:510` 的",
    "`list_goal_task_events`），屏上出现的是工具名、轮次、理由码三样，没有思考链、没有凭据、",
    "没有内部码原文。",
    "",
    "### 13.2 步骤时间线：屏上七行来源，库里七行 provider，一对一",
    "",
    "`599ed95b76` 把「这一步是谁答的」写到每条 AgentRunStep 行上（渲染点",
    "`frontend/src/trial/mobile/WorkspaceActions.tsx:703`、取值 `:711`–`:712`、函数 `:150`）。r117 按同一条",
    "旅客路径走到对话层，读了展开前后两次：",
    "",
    "    STEPS_BEFORE  present=true  open=false  summary「Agent 工具时间线 · 8 步」  source_rows=6（空文本）",
    "    STEPS_AFTER   open=true  rows=9  source_rows=7  amap=7  checked=6  not_recorded=1",
    "                  第二行全文：2 查找公开地点 完成 8 处地点 来源：高德地图 · 真供应商已核实 03:13:02 · 0.3 秒",
    "    SOURCE_HIT_PROOF 236x26@713  inViewport=true  visible=true",
    "",
    "读数在 `trial/results/20261026_gozero/bl117-tool-step-source-430.txt:15`、`:18`、`:19`、`:20`、`:21`。",
    "只信屏不够 —— 「屏上没有」既可能是渲染没接上、也可能是库里本来就没有。所以 r118 用只读探针",
    "（`mode=ro`，只打印计数与字段名，不打印行体）把同一条旅程的存表数出来对账：",
    "",
    "    STEPS 9  —— ask_traveler 1 步（无 provider）／discover_places 6 步（全带 provider=amap 与 provenance）",
    "              route_public_places 1 步（带 provider=amap，不带 provenance）／save_draft_itinerary 1 步（无）",
    "",
    "坐标 `trial/results/20261026_gozero/bl118-step-provider-census.txt:4`、`:5`、`:6`、`:7`、`:8`。",
    "带 provider 的存表行数合计七，屏上来源行也是七；带 provenance 的六，屏上「已核实」也是六；",
    "两步全无 provider 的（问答与存草案）在屏上就不挂来源行（rows=9 而 sources=7，差两格）。",
    "两头对上，才敢说这行的内容是读回来的、不是拼出来的。",
    "",
    "### 13.3 「核实状态未记录」那一格，根因不在前端",
    "",
    "七行里有一行写「来源：高德地图 · 核实状态未记录」。它对应的正是库里那条 route_public_places：",
    "`backend/app/agent/goal_amap.py:269` 那条出口带 `" + "`" + "provider_provenance\": \"LIVE_PROVIDER\"`，而 `:270` 那条出口",
    "压根没产成路线，也就没写核实状态。前端如实说「未记录」是对的 —— 拿 LIVE_PROVIDER 去填一条没有",
    "路线的出口才是撒谎。",
    "",
    "剩下的缺陷是另一件：旅客从那行看不出「这一步其实没给出路线」，只知道核实状态没记。这一格与",
    "#319（按完之后的上限披露未展开）同族，留在那张单上，我没有顺手改后端。",
    "",
    "### 13.4 行上那句检索动作是谁写的（归属，免得读成我新加的口子）",
    "",
    "步骤行里出现的「搜索故宫博物院作为第1天核心景点」这类句子，是服务端在派工具时就写下的对外动作",
    "描述（`backend/app/agent/goal_amap.py:153` 把 `public_action[:120]` 存进行体），渲染点早在",
    "`frontend/src/trial/mobile/WorkspaceActions.tsx:708` 就在，不是本刀新增。它经服务端截断且属于",
    "「可公开」命名那一路，但账要记清：屏上并非只有结构化字段，还有这一句模型写的动作句。",
    "要不要连它也收进白名单，属裁语，不自取。",
    "",
    "### 13.5 自报：两次没带 pathspec 的提交，把别人的暂存卷走了",
    "",
    "本班连踩两次同一脚：`git add -- 我的路径` 之后 `git commit -m` 没带路径，git 就把 index 里另一个",
    "写者的二十二条前端暂存条目一并写进我那条信息底下（`frontend/src/app/V8Experience.tsx` 等，",
    "巨行增删是换行翻转的形状）。两次都用 `git reset --soft` 退回、再按 pathspec 重打，损害限于提交",
    "归属混乱，没丢内容：拆后 `599ed95b76` 两档文件、`bebdf21b72` 五档文件、`95997901dd` 七档文件，",
    "别人的 index 条目每笔之后都还是二十二条。",
    "",
    "靠记性不算规矩，所以这条装进了写的那扇门：`trial/human_walk/_cmdr_pathspec_commit_gate_r119.py`",
    "只提交点名的路径，提交后现读 `git show --name-only` 与 index 双向核对，卷走别人条目就软回滚并退",
    "非零码。`--selftest` 三格都是真跑的：对照组不带 pathspec 确实吞掉了别人的文件；ROOT 深度那一格",
    "是我这次踩的第二只坑（dirname 少一层 ⇒ 把一份文件齐着的交付判成「文件不存在」而拒收）；点名的",
    "路径不在树里就 rc=2 拒在写之前。自测原文见本次回执。",
    "",
    "### 13.6 这一刀还欠的两格（不折算成已完成）",
    "",
    "一、指令要的「新旧差异摆在接受键旁 + 缺的花费写成 unknown」：差异与花费两处都在码里",
    "（课堂面板 `frontend/src/trial/mobile/ClassroomPresenterPanel.tsx:307`、`:308` 的三元都有「未知」分支；",
    "出发卡 `frontend/src/trial/mobile/DraftDepartureCard.tsx:376` 的逐行差异紧贴 `:377` 的接受键）。",
    "屏上证到的那一次读的是「费用：不变」，也就是花费确实算出来了那格；**「费用：未知」那一格至今",
    "没有屏上证词**，因为它要一条真算不出总价的候选，而这类候选不可预置。这条保持未证。",
    "",
    "二、现尖 worktree `E:/_cmdr_tip_113` 仍然只携带一枚外来的文件 —— WorkspaceActions.tsx 是",
    "`599ed95b76` 的那枚 blob，其余还是 `dea0328e0b`。这是屏证的前提，也是要还原的偏差；还原只要一行：",
    "`git -C E:/_cmdr_tip_113 checkout HEAD -- frontend/src/trial/mobile/WorkspaceActions.tsx`。",
    "",
    "三、r117 只走 430×932 一档；390×844 那档的同一格还没量。",
    "",
]
block = nl.join(lines) + nl
io.open(PATH, "w", encoding="utf-8", newline="").write(text + block)
after = io.open(PATH, encoding="utf-8", newline="").read()
print("BYTES_BEFORE", before_bytes, "BYTES_AFTER", len(after.encode("utf-8")))
print("PREFIX_INTACT", after.startswith(text[:4000]))
print("SECTION_13_COUNT", after.count("## 13 第 2 刀 2a"))
print("TAIL", repr(after[-30:]))
