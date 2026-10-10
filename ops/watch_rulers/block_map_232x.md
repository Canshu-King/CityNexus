### SESSION=494abfd7 · 换包后的地图面：文案与穿透已实测，**但"单指能否平移"我没验成——我的观测量选错了**（maplibre 重绘而非 CSS transform）@本机钟 23:2x

`STATUS: PARTIAL-SELF-MEASUREMENT / INSTRUMENT-ERROR-NAMED | 目标 `:4782` 新包 `index-BwIS1pck.js`，390×844，有效行程 `6cbdbc65…`（北京 PLANNED，可信坐标在）| 全程只读，未动后端/护栏/用户数据 |`

**量到的（这些是真的）**
- `/v8/map` 上 `.v8-map-panel` **在**、`canvas` **在**；
- 手势提示文案实测 = **「单指拖动地图 · 双指缩放 · 想翻这一页就拖地图以外的地方」** ⇒ 旧文案「两指拖动或缩放地图」已不在生产包里；
- 该提示元素 `getComputedStyle().pointerEvents = **none**` ⇒ `4176e7b` 的"叠层不再抢走手指"确实生效（这正是旧版"手指落在字上、地图没反应"的机制）；
- `says_offline = false` ⇒ 换成有效行程后不再冒充离线（与 ① 那条 R14-S 实测连成一条完整链）。

**没量到的，我不给自己记绿**
- 我对手指平移的判据是 `.maplibregl-canvas-container` 的 CSS `transform` 变化 ⇒ **before/after 都是 `none`、`camera_moved=false`、`page_scrolled=0`**。
  **这个观测量本身是错的**：maplibre 平移是重绘画布（WebGL），不改容器 transform。所以 `camera_moved=false` **既不能证明没动、也不能证明动了** ⇒ 记 `NOT_MEASURED（instrument chose the wrong observable）`。
- 正确做法（lane D 的门已经这么读）：**读相机坐标**（它的交付里是 `lat 39.1142126 → 38.9513717`、`documentElement.scrollTop` 钉在 0），而不是读样式。
⇒ 结论：**ORD-0169 的第③ 条（恢复态地图回来）成立**（面板/画布/文案/穿透四件都在）；
   **"单指真的能平移"仍只有 lane D 的门与 HJ-P3 的真机读数可签**，我没复跑，**不签**。已回给 HJ-P3（ORD-0165 ① 就是要这个读数）。

**给全线的一句（同"没收集就没分母"一族）**：验"移动"要看**状态被改了什么**（相机 center/zoom、scrollTop、DB 行数），别抓一个"看起来会动"的代理指标（CSS transform、class 变化、元素存在）。我今晚已经第三次靠这条把自己从错误结论里拉回来（前两次：`onLine` 当主证、匿名 401 当"护栏没了"）。

status: 地图面文案+pointer-events+非假离线四项实测通过；单指平移我用错观测量、判 NOT_MEASURED 不签；ORD-0169③ 成立、物理那半留给 D 门与 HJ-P3
evidence: 本轮 evaluate 原文（hint 文案、`pointerEvents:none`、`transform before/after = none/none`）· lane D 门里的 `lat 39.1142126 → 38.9513717` 为正确观测量示例
