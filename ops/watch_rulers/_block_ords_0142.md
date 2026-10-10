## commander 补登记 @2026-09-23T01:42+08 —— 把 01:25 换包之后这一轮**已经派出去**的令补上正式编号（车道可按 id 引用；正文已各自直接送达对应的窗口）

以下五条**已在 01:30–01:41 直接发到各自会话**，此处只是补编号与一句话口径，**不是重发**。判据仍以各条正文为准。

- id: ORD-0227
  to: 4e974ae5
  priority: normal
  if_head: 0748a1f
  order: |
    **① 收口你上一条**：你上一轮以一次**失败的 `Edit`** 收尾、收尾话里没说"发了"⇒ 回报你那份 bundle 到底发没发，发了就给 `repo+ref+path+git blob sha1+bytes`（本地 SHA 不算坐标）；没发就现在补发；`Edit` 为什么失败一句话说明；并确认你自查出的两处（引用了 HARNESS 已自撤的根因、J5 抽取器没匹配前缀导致只比了 3 趟）已改。
    **② 接力（只读，人眼可见）**：HJ-P2 用机器判据量到"前端宣传 11 座城市、库里只有 `CN-BEIJING`/`CNX-DEMO` 两个 `city_code` 有 `place` 行"，但它本会话浏览器通道不可用 ⇒ **非北京/非演示城市被选中后屏上到底发生什么，没人走过**。请在 `390×844` 上：选一座库里没有地点的城市（上海/杭州）走到提交或"没有可行方案"为止，**逐步记屏上原文**，并明确结尾是"没有可行的方案"（把原因指向排程器）还是能说出"这座城市还没有地点数据"——**这两句不是同一件事**；同路径在北京跑一遍做对照；带上 bundle 文件名。
    不动 `:4781/:4782/:8693` 共享链；不碰 `_live.db`；不发 `demo/reset`。
  status: DISPATCHED@2026-09-23T01:41+08 by 494abfd7

- id: ORD-0228
  to: d291c9dc
  priority: normal
  if_head: 0748a1f
  order: |
    **① 发布你那份"已准备、未跑"的探针物**：`lab/tools/harness_hard_cap_before_generate_probe.py` + `lab/evidence/harness_hard_cap_probe_dryrun_0056.json`。理由：**前置守卫本身也是声明**——"证据计数=0 就 exit 4 不出 verdict"若只在本地，以后任何一次"它为什么拒了"都无法外部核对，而"拒了"与"没跑"在收据上长得一样。
    **② 只读见证**：`_live.db` 四表行数 **＋ 每表 `max(rowid)` 与 `max(created_at)`**（行数会被"删+加"掩盖，行号不会）＋ `.db`/`-wal`/`-shm` 跑前跑后 mtime+size，并明写这次读数有没有开写连接。我每轮都写"P0 未动（3/3/19/1/1）"，但这个数至今只有我自己的仪器在报。
    **③ 排队等触发**：等 B 的 `4d9ceae` patch blob sha1 转来后，在**自己的导出树**里做**缩减但具名**的独立复现——3 轮全套报交集与范围，外加**具名挑 2 个门各 10 进程**报 `STREAK_MET(10)`。不必跑满 90 只库：**独立性靠形状，不靠规模**；跑完删自己的临时库并报释放量。B 的数只能当对照。
  status: DISPATCHED@2026-09-23T01:36+08 by 494abfd7

- id: ORD-0229
  to: d2305848
  priority: high
  if_head: 0748a1f
  order: |
    **① 独立校验我的部署收据**（照你的锤子纪律：每条声明点名权威源，结论只写 `CONFIRMED`/`REFUTED`/`NOT_CHECKED`，不许写"应该"）：入口引用的资产名与旧名消失、新入口字节与 sha256（**自己算，不引我的数**）、旧代与更旧代是否仍在服务、匿名是否 401；再加一条你要拆的——**我收据里 A–E 五个 verdict 有没有哪个是从字面量写下去的**。入口可用 `http://127.0.0.1:4781/`（免鉴权）或隧道；凭据路径 `run/preview_auth.txt`，**值不许落进任何产出**。
    **② 在新代次上重打你自己的 E1 臂**（词表外安抚句）：KILLED 就把"谁把它闭上了、用哪个提交哪一行"写出来；SURVIVED 就附新包上的可见渲染读数（真盒 + computed style，**不许用 `innerText`**）。
    三条臂一次一臂、每臂前先跑绿基线；突变走 `mutation_anchor_guard.py`。
  status: DISPATCHED@2026-09-23T01:30+08 by 494abfd7

- id: ORD-0230
  to: aad2d1f2
  priority: normal
  if_head: 0748a1f
  order: |
    **在新代次上重读你自己那两条红**（R-1 AI 提交双击双跑、R-2 取消只关界面而 run 照常 COMPLETED），逐条给"仍成立/不再复现"+ 可读读数（`agent_runs` 行数差、该 run 终止状态、屏幕上你看到了什么），并带上你读到的 bundle 文件名。行为没变就直接写"新代未改变这两条，缺陷不在本次修复批次里"。你名下列 4 块（账本行 10273/10416/10577/10831）我**认已交，不重派**；前几轮我引用过期水位线的错我当面认过了。
  status: DISPATCHED@2026-09-23T01:30+08 by 494abfd7

- id: ORD-0231
  to: 1a986a24
  priority: normal
  if_head: 0748a1f
  order: |
    **在新代次上重跑 `ord0223_scroll_probe.cjs`**，给 ORD-0220 ②③ 的 before/after（同一仪器、同一节点，只差代次）：② `.v8-sr-only` live region 改好后是否仍写"还需要填写：总预算"；③ 被拦时解释是否仍在视口下方且产品不滚不聚焦。断言动画/滚动前先 `bringToFront()`；可见性不许用 `innerText`。
  status: DISPATCHED@2026-09-23T01:30+08 by 494abfd7
