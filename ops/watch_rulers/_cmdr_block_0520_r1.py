import io, os, time

LIVE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
STAMP = time.strftime("%H%M")
OUT = os.path.join(r"D:\moodle\_qoder_ledger_inbox", "6efab655_" + STAMP + ".md")

TIP = "d107131c6f6e65d9f207f6bf1b563d1cc8877f89"
AB = "78ea16b8f2085d9bf90682d0cbd7e65bc38bed0c"
RB = "fa0276edc214c0534a963a61b92d2438daf40834"

body = u"""### 6efab655 · 号令者实例 A · ORD-0520 屏侧那格收口：入口点得到，但确认键被正文盖住（两臂同形），开 ORD-0575 派给已有那一族的车道

**一、栈与代次（沿用本日夜那把私有栈，全部现读）**

- 被读的那一代：现尖 `@@TIP@@` 的构建产物，入口件 `index-BW2_ds1t.js`，服务字节与磁盘字节同一枚 1623134 字节（对拍读数在件 blob `@@RB@@` 的 `entry_asset` 段）。
- 分母：私有副本库里 142 程、45 程有排程；本轮读的是其中一枚 24 段、状态 ACTIVE 的行程（id 在件内，不在本块里贴带连字符的 id）。

**二、我欠了很久的那格，现在的实测（中文臂与英文臂各一遍）**

- 入口只在一屏有：`/v8/trips` 两枚命中，`/v8/hub`、`/v8/live`、`/v8/me` 三屏各零枚（逐屏读数在件 blob `@@AB@@`，7316 字节）。
- 那两枚不是同一个东西：第一枚是展开用的 `summary.cn-abort__summary`（中心 cy 454 像素，中文臂；英文臂 488 像素），命中测试落在它自己身上，点得开；点开之后屏上画出完整说明段 `p.cn-abort__explains` 全文 114 字、渲染成 6 行、`scrollHeight` 不超 `clientHeight`（不是裁切，见下节我撤回的那条）。
- 第二枚才是提交键 `button.v8-quiet-button`（那一枚的形制在 `frontend/src/features/abort/JourneyAbortPanel.tsx:185`），文字同为「中止这趟行程」，盒位宽 96 像素、高 44 像素，左上角落在 x 251、y 525 像素（同一枚键在英文臂同形，中心 cy 613 像素；`frontend/src/features/abort/JourneyAbortPanel.tsx:185`）。
- **缺陷就在这枚**：它中心那一点的 `document.elementFromPoint` 回的是 `p.v8-lede`（正文那句「逐日安排。已确认的预订会被标记为受保护。」，那句的形制在 `frontend/src/features/trip/TripItinerary.tsx:393`）。两枚都是 `position: static`、`z-index: auto`、`pointer-events: auto`，正文盒与按钮盒的重叠面积 2058 平方像素、按钮自身面积 4224 平方像素，也就是按钮被盖住约一半面积（三个数同一件：blob `@@AB@@`）。
- 我按中心点没有去点它（那程还在），所以「按不动」是从命中测试与重叠面积判出来的，不是从一次失败的点击判出来的。
- 一条给车道的取件口径：这三枚证据件（blob `@@AB@@`、`@@RB@@` 与仪器合订件）在 `refs/heads/commander/control` 那条线上；本机要先 `git fetch origin +refs/heads/commander/control:refs/remotes/origin/commander/control` 才 `git cat-file` 得动（我本轮 fetch 过，三枚都回 blob）。

**三、自报一条我自己差点报错的**

- 第一遍读数里那句说明看起来像半截句（结尾停在「这台服务」），那是我的尺把每条可见文字截到九十字符造成的，不是产品裁切；我当场用不截断的重读验了：全文 114 字、末字是「…只能新开一趟。」、渲染 6 行、无裁切（同一件 blob `@@AB@@`）。这条不立案。

**四、派单**

- **ORD-0575 → 车道 1ba48dbf**（它名下已有 ORD-0561 那一族「按钮被正文盖」的修法，本枚是同一缺陷类的新一枚，不另开枝族）：`/v8/trips` 上 `details` 展开后的提交键 `button.v8-quiet-button` 与 `p.v8-lede` 盒重叠，中心命中被正文拿走。修法要在**布局**上解（谁该在谁下面），不许用 `pointer-events: none` 把正文打哑来骗过尺。
- 验收要件（我会自己重跑）：中文臂与英文臂各测一次，提交键中心的 `elementFromPoint` 必须回它自己或它的后代；重叠面积必须为零；展开后说明段仍逐字可见（正对照，不许靠隐藏正文换取重叠归零）；页面异常零枚。
- 反件至少两枚：把提交键挪回原位（撤销修法）与把 `p.v8-lede` 的盒撑大，两枚都必须让那把尺报红。

**五、没改善的部分（具名）**

- ORD-0575 本轮零字节落地（`frontend/src/features/abort/JourneyAbortPanel.tsx:185` 一字未动），用户此刻在屏上仍点不动那枚提交键；我只把「点不到」从一句推测变成两臂可重跑的几何读数。
- 闭合查找尺接进落地门：`NOT_IN_GATE_YET_BY_CMDR`。
- 我没有真的完成一次中止（零次写请求），所以「中止成功后那一屏说什么」仍是 `NOT_REACHED_BY_CMDR`。
"""

body = body.replace("@@TIP@@", TIP).replace("@@RB@@", RB).replace("@@AB@@", AB)
assert "@@" not in body
closing = io.open(os.path.join(LIVE, "CLOSING_LINE.txt"), encoding="utf-8", newline="").read().strip()
text = body.rstrip() + "\n\n" + closing + "\n"
io.open(OUT, "w", encoding="utf-8", newline="").write(text)
print("wrote", OUT, len(text.encode("utf-8")), "B")
