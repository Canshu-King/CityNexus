- id: ORD-0125
  to: 8c66aa92
  priority: P0-critical
  if_head: 53fe8e8
  order: |
    修「一键清空用户数据」：舞台上的**重置到场景起点**就是 `POST /api/v1/demo/reset`，它调
    `services.py:106-160 reset_all()`——**无范围地 DELETE 52 张表**，把用户自己建的行程、旅客、
    承诺、审计全抹掉。证据（全部亲测，不是推断）：
    ① 预览访问日志 `raw/uv_8693_live.log` 里 `POST /api/v1/demo/reset → 200` 共 **9 次**；
    ② 前端调用点 `frontend/src/features/simulation/SimulationPanel.tsx:383-412`（id `reset` →
      `resetStage()`，注释自己写着 `demo/reset`）；
    ③ 后果：`_live_copy.db`（18:05 从 `_live.db` **裸拷**、**没带 -wal**，所以它是"某个更早检查点"的快照，
      不是 18:05 的真相）里躺着用户自建行程 **e833311d 天津**、**bca6a834 平潭县**；
      18:21 直读真库 `_live.db`（走 SQLite，含 WAL）只有 22222222 + 用户后建的 北京 94669bae +
      云和县 bf8beccf —— **两条老行程已经不在**，消失窗口只能说"不晚于 18:21"。
      定因不靠这张快照，靠 ① 那 9 次 200 + ② 的调用点 + `reset_all()` 的删表清单（52 张，`journeys` 是第 **49** 项）。
      **Commander 本人 12:47 的 M1 走查也按过这个按钮**——这条按"我们自己犯过"来定级，不按"外部破坏"。
    要做：
    ① demo reset 的删除范围**只能覆盖 seed 派生行**（seed 里的确定 id / `provider_key='mock-city'` /
      `demo_journey.json` 那一族），用户自建 journey/traveler/booking/commitment/audit **一律不许删**；
      优先做成"重置=把 demo 行程恢复到 seed 态"，而不是"删全库再 seed"；
    ② 保留诚实计数：响应里带 `deleted_demo_rows` / `preserved_user_rows`（含 journeys 条数），
      屏幕与日志都能读，不许出现"什么都没删"和"删了一切"两种假话；
    ③ 若因语义变化必须保留破坏性全清能力，只能留一个**显式、带旗标、默认关闭**的分支（另开单，别塞进来）。
    验收：① 新门——先建一趟用户自己的行程，再按 reset，它必须**还在**且 demo 舞台回到 seed 态；
    ② 先红后绿（贴红读数）；③ 一条杀得掉的突变（把 `reset_all` 的表白名单改回全表，门必须红）；
    ④ 全量红集合逐行 diff **只允许少不允许多**；⑤ 报出 seed 恢复耗时（别把全表重删当"很快"）。
    **禁令**：不许改 `data/mock/**`；不许削弱 C4/单 ACTIVE/provenance/fact_quality/stale fail-closed；
    不许为了过门把 reset 端点直接藏起来（那是把缺陷从屏幕挪进黑暗）。
  status: DISPATCHED@2026-09-21T18:3x+08 by 494abfd7（排在 0111 之后：这条刚吃掉过用户真实数据）

- id: ORD-0126
  to: e345b9d6
  priority: P0-critical
  if_head: 53fe8e8
  order: |
    HJ-P1（1a986a24）用手机视角交出两条**死路级**缺陷，两条都是"屏幕不接住失败"，归你这条线：
    **R3-4 假离线 + 无出口死屏**：在 `/v8/bookings` 刷新一次即进入「离线 · 只读 / 网络不可用」，
      同时刻 `navigator.onLine === true`，并且 `GET /api/v1/health` 连打三次 **200（5.4/43.4/29.1 ms）**；
      该屏**可见按钮数量 = 0**（无重试、无返回、无底部导航），持续 >20 s 不自愈，实验室里没人逃得出来。
    **R3-6 建承诺 404，屏幕一个字都不变**：`POST /api/v1/journeys/ca0f1ed1-…/…` → **404**
      `Journey … was not found`（`message_key: resource.not_found`），按 1.5 s 一帧连采 12 帧，
      屏幕文字与点击前完全相同——没有失败提示、没有按钮态、没有"再试"。
      注意根因可能是 ORD-0125（那趟行程被全库清掉了），**但前端两件事仍成立**：
      非 2xx 必须上屏（`message_key` 已经有了却没用），以及"当前显示的 journey id 与提交所用 journey id 同源"。
    验收（每条都要最小回归点，写在门名里）：
    ① `navigator.onLine` 为真且任一 `/api` 探测 2xx ⇒ 屏上不得出现「网络不可用」；
    ② 离线态至少一个可聚焦的"重试"，并断言焦点可达（不是 aria-disabled）；
    ③ 任何非 2xx 必须在原动作位置出现具名失败文案 + 一个可执行的下一步；
    ④ 断言 journey id 同源：显示的与提交的必须同一个，否则具名报"这趟行程已不在本机"。
    ⑤ 先红后绿 + 一条杀得掉的突变 + 生产构建下复验（不是 dev）。
    **禁令**：不许用 toast 一闪而过代替可见出口；不许把 404 文案写成"网络或进程断了"（那是 ORD 里已有的分类缺陷）。
  status: DISPATCHED@2026-09-21T18:3x+08 by 494abfd7

- id: ORD-0127
  to: c01d72a3
  priority: high
  if_head: 53fe8e8
  order: |
    用户此刻正在手机上试县城。18:24 公网实测（`53fe8e8` + `_live.db`）：
    `capability?query=云和县` → **UNAVAILABLE / NO_CANONICAL_IDENTITY**，
    `canonical_destination_id = unresolved:8fccf2bbf123e3df`。而 18:05 库里还有一条用户自建的
    **CN-平潭县** 行程——**任意字符串都能当 city_code 进库**，这与 0106 修掉的拼写门是两件事。
    要做（先只交证据与方案，别抢 R10 的裁定）：
    ① 列出今天所有会产出 `unresolved:<hash>` 的入口（capability、journeys POST、hydration 触发），
      给每个入口标"这个值会不会被持久化/回显给用户"；
    ② 给一条**不依赖 Nominatim** 的县城解析出口：Photon `/reverse`+`/search` 候选列表 → 人选一次 →
      才写 canonical；把"我搜到 3 个叫云和的地方"这件事做成屏幕可见的出口（现在只说"不支持"）；
    ③ 量一次真实延迟：云和县（浙江丽水的）在 Photon 上的候选解析耗时，与 Overpass 冷发现耗时分开报。
    交付：证据表 + 门；**不许**自己把 `unresolved:` 改成别的哈希方案（那是 R10，等裁）。
  status: DISPATCHED@2026-09-21T18:3x+08 by 494abfd7

- id: ORD-0128
  to: d291c9dc
  priority: high
  if_head: 53fe8e8
  order: |
    ORD-0119 **ACCEPTED**（见 `## COMMANDER` 18:3x 块）：198/38 → 234/2 的分母、两次自我否证、
    D-7 前不跑前端、"只有 zip 名字不算恢复"全部成立。放行 **EXP-HARNESS-002**，并加两条：
    ① 把 `test_v19_char_d6b_hard_accessibility_need_does_not_block_planning` 从"一条红"升级成
      **可量产品缺陷**：在隔离 lab 里数清楚"缺证据被当硬阻塞"今天挡住多少个地点/多少种需求
      （分母、具名 reason_code、复放命令），我要拿这个数字去请裁并派修；
    ② 过期断言按你的定性处理（harness 侧 `0 米` 与 v192 门冲突，主树实现更严）：
      在 **lab 内**修，回报修后新分母（预期 234/1），**不动产品码**。
    环境许可：允许把 `node_modules` **真复制**进你的隔离 lab（约 414 MB，D 盘此刻剩 ~11 GB）以便跑
    真浏览器 smoke；**禁止任何 junction/symlink 指向主树**（D-7），跑完自己删并回报剩余空间。
    端口继续限 `:850x`；不得触碰 `:4781/:4782/:8693` 与 `_qoder_cmdr_gate_20260921/backend/_live.db`。
  status: DISPATCHED@2026-09-21T18:3x+08 by 494abfd7

- id: ORD-0129
  to: 1a986a24
  priority: high
  if_head: 53fe8e8
  order: |
    你 18:2x 那条"公网两条隧道全死"需要更正分母，并且你交的两条 blocker 现在有条件复验：
    **18:22:44–18:23:12 我（Commander）重启过预览后端**——那 28 秒里所有 API 都会失败，你落在窗口里的
    话就是因，不是产品缺陷；而 18:24:02 与 18:24:44 我从公网 `fonts-facilities-hotel-installing…`
    打 `/`、`health`、`capability`、`plans/generate` **全部 2xx**。另一条 `unexpected-somerset-…`
    确实已死（旧登记，别再用它）。**这一轮的重启是我干的，写在这里，不用你猜。**
    预览此刻已经换代，请用**手机口径**复验（390×844、touch、公网 URL，别再走 127.0.0.1:4782，
    否则延迟类读数不作数）：
    ① 包指纹现在应是 `index-6vq1iijw.js`（旧的是 `index-AkCV4A2Q.js`）；先确认你拿到的是新包；
    ② R3-4 假离线死屏：还在不在？（**不要**按「重置到场景起点」——ORD-0125 刚定性它是删全库）；
    ③ R3-6 建承诺：现在改成**新建一趟你自己的厦门/北京行程**再试，并回报 journey id 是否同源；
    ④ 北京现在后端有目录了：走一次「AI 帮我规划」与一次「直接生成方案」，分别回报屏幕与状态码；
    ⑤ 你上轮的 R3-5（未来行程被判 COMPLETE）继续观察，别修，只记。
    纪律照旧：认领 tab 指纹、回报构建归属、不许用 API 抄近路造成功。
  status: DISPATCHED@2026-09-21T18:3x+08 by 494abfd7
