- id: ORD-0134
  to: e345b9d6
  priority: P0-critical
  if_head: 53fe8e8
  order: |
    只读侦察线 ORD-0130 交回了**两个机制级答案**（文件：`D:\moodle\_qoder_cmdr_ref_20260921\live_checks\donor\`
    下 `UI_DONOR_SCOUT_REPORT.md` + `UI_DONOR_PORT_MATRIX.md`，12 行矩阵、每个 blocker 3 个候选），
    正是你手上那两个还没收口的真机缺陷的成因。**注意：这是"借结构重写"级的思路，不是搬代码**
    （`clawnify/OpenTripPlanner` license=null ⇒ 只准看；`stvlynn/OpenTrip` 是 Apache-2.0 可借结构）。
    **① AI/规划面板手指滑不动（ORD-0090 残①）**
    - 成因已定位（**行号我自己核过**）：`.plan-ai-sheet` 用 `max-height: 92vh`（`frontend/src/styles.css:691`，
      规则从 `:689` 开），量的是**布局视口**；手机浏览器工具栏出现/收起时布局视口不变，
      **可见视口**才变 ⇒ 底部那一排动作被键盘/工具栏挤到看不见也摸不到。
    - donor 的做法（OpenTrip `shared/ui/drawer/drawer.tsx` + `shared/lib/visual-viewport.ts`）：
      把 overlay **钉在 visual viewport** 上（`--vv-*` CSS 变量 + `visualViewport` 事件），
      面板内部只有**一个** `min-h-0 flex-1 overflow-auto` 滚动区，header/footer `flex-none`。
      他们注释里写明原因和 WebKit 忽略 `interactive-widget=resizes-content` 有关——这条我们已经吃过一次。
    - 要做：面板高度改用 visual viewport 派生的自定义属性（带 `100dvh` 兜底），
      把"只有一个滚动区"写成结构而不是补丁；门：360/390/412 三档下**最后两个动作按钮必须可点击**
      （命中测试要读真实 `elementFromPoint`/pointer 可达，不接受 `aria-disabled` 假绿）。
    **② 地图手势（滑不动 / 一用力滑到旁边的 trips）**
    - 成因已定位（**行号我自己核过**）：`frontend/src/components/v8/MapPanel.tsx:252` 设了
      `cooperativeGestures: true` ⇒ 手机上**单指平移直接无效**，用户"用力滑"就滑到了外层容器（面板抢手势）。
    - donor 的做法：单指平移保留；覆盖层 `pointer-events-none` + 控件单独 `pointer-events-auto`；
      marker 点击 `stopPropagation()`；拖拽所有权用**显式 allowlist/denylist**（`BOARD_PAN_BLOCK`）而不是整块 `touch-none`；
      外加 dnd 的 **8px 起点容差 + 只有握把可拖**（`Serkanbyx/travel-planner`：`PointerSensor{distance:8}`、
      grip-only `touch-none`），但**它 `max-h-[calc(100vh-400px)]` 在 360/390 会塌**，这一条别学。
    - 要做：去掉 cooperative 模式（或给出"单指即可平移"的产品答案），手势所有权变成**可测试的显式规则**；
      门：真机口径（390×844 + hasTouch）拖地图 ⇒ 地图平移、页面不滚；拖列表 ⇒ 列表滚、地图不动。
    验收：① 两条各自先红后绿（把上面的行号读数当红基线）；② 各一条杀得掉的突变
      （把 `--vv-*` 换回 `92vh` / 把 `cooperativeGestures` 打开必须判红）；
    ③ **在生产构建 + 手机视口下复验**（不是 dev server，不是桌面宽度）；④ 全量前端 typecheck + build 绿；
    ⑤ **别重做已经做完的**（我自己核过，不是转述）：`PlanWithAiSheet.tsx:38-54` 已把厦门硬编码例子改成
      "用服务器返回的本城地名造例子，少于两个就不给例子"；`:555-566` 已删掉位置性 `slice(0,8)`，
      卡片现在只发 `{candidate_count: 3}`、**不发 `place_ids`**。我把这个请求体原样在公网打了一遍：
      **201 / 3 个候选 / selectable=True / 活动 8·8·7 / 1.41 s** ⇒ ORD-0104 ① 与 ORD-0107 ① 在 `53fe8e8`
      **代码已完成**，你剩下的是手机上走通并截图（与 ORD-0129 同批复验）+ 本单 ①② 两件事，**不要再动阶梅**。
  status: DISPATCHED@2026-09-21T18:5x+08 by 494abfd7
