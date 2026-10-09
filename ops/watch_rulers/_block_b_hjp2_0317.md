## commander 验收 @2026-09-23T03:17+08 —— B 修好门误红并把 422 具名落地；aad2d1f2 交回**等待计数器的正证**、撤回兴趣观察、并挖出一条 **`TRUTH_DEFECT`：向导收了兴趣/节奏却一个字节都不发**（新开 ORD-0238）

### ① B `c01d72a3`：门误红已修 ＋ 泛化 422 具名**不需要 `main.py`**

**新尖 `318a034`**（`git log -1`：`318a034 Wed Sep 23 03:05:20 2026 +0800 feat(plans): a no-candidate refusal names which rules broke which candidate`，parent `dea1251`，2 files +153/−59，未 push）。

**臂 1（它的门误红）四项验收逐条**：
```text
① 臂 1 形状 ⇒ 绿：判据换成 assert (NAMED_BLOCKER[code] in text) == bool(expected[plan_id][code])，
   并加"同一地点撞两把"子例；改的是【它自己的一次性库】，回读证明改动落地、fixture 未动
② 多报 expected 之外的名字 ⇒ 红：M11/M12 各只杀这一条
③ 新形状【自己的】杀手：M13/M14（同地点双冲突时【少报】任一把）各只杀这一条，其余 12 条全绿
④ 旧形状不回退：13 条全绿，两条单码门语义未动
```
**臂 2（新缺口）定位结论：不需要 `main.py`** —— 句子与 `details` 都由 `app/services.py:1739-1755` 的 `CatalogShortfall` 组装（类 `:555-561` 带 `.reason_code/.details`）；`main.py:4571-4593` 只转发属性、`:546-561` 渲染 ⇒ 具名放 services 侧即可，**句子一字未改（ORD-0101）**。before/after 都可复放（`arm2_refusal_naming_before_after.txt`）：
```text
BEFORE(dea1251) details = 5 个计数键；整份响应里 STEP_FREE_REQUIRED 出现 = False
AFTER (318a034) details = 那 5 项 + candidate_rejections；STEP_FREE_REQUIRED = True；
                条数 3 == day_sequences_available；无一条无名
```
新门 `test_a_refusal_with_no_surviving_candidate_names_which_rules_broke_them`（第三把用 API 直写 ⇒ 同时钉住"直写的约束也具名"）；杀手 **M15 删键 / M16 键在但永远空表**。
**臂 3 只记形状**：判据是子串；不可达依据复测（两名字互不为子串、16 个演示地点 id 中 0 个含任一名、唯一通道是 `place_id` 文本）⇒ 写"形状＋不可达依据"，**不写"已安全"**；真闭环要改成判结构化 `failures` 列表（下次裁定）。
**复跑**：13 门全绿；**17 臂全 KILLED**；`nodes_without_a_killing_arm=[]`；连击 **13 节点 × 10 进程 × 130 只不同库全 `STREAK_MET(10)`**（跑完删自己 130 只、**释放 107.2 MB**）；全套两次 **9 failed / 1172 passed**（collected 1197）⇒ **引入 0 条新红**。
**合流**：我那条裁定它未动——ORD-0234 已由 C 在主线落地（`1ea6250 …has one owner again`，正是 `else None`）；`318a034` × 主线 `b8ef632` 整树合流 **28 passed**（它 13 ＋ C 15），文本冲突只剩注释。
**坐标**（`commander/control` ＋ `evidence/b-ord0219-demo-evidence/`，7 件 PUT 201 ＋ BYTE-LEVEL MATCH；15 臂收据首吃 409＝分支被推进，重试即成）：报告 v3 `db520e24c7c774f4`｜累积 patch `7524843155f7d635`｜`318a034.patch` `5c3cbdfcdff68236`｜13 节点审计表 `a05db0125f4a0f69`｜15 臂收据 `ecc9c2a432d19e1d`｜连击读回 `868c982562640555`｜臂 2 before/after `bc45fe7d76a1361c`。SOFT 四码、`tags_json`、前端渲染面、`main.py` 全未碰。

### ② aad2d1f2 `aad2d1f2`：等待计数器**正面证明**（它换了个不需可见性的量法）

- **"置前重跑"它做不到**：`select_page(bringToFront:true)` 被接受，但文档仍 `hidden`、`innerWidth×innerHeight = 0×0`、截图被拒（工具原话 "Open the in-app Browser before retrying"）。**它没有去动共用的面板**（对）。
- **但它拿到正证**：同一次提交内埋两个钟——**它自己的 1 秒采样被节流成 2 秒**，而屏上 `data-elapsed-seconds` 在这 10 秒里从 **27 走到 37 ＝ 1:1 跟随墙钟**（被量的那趟 `dea051f3`，19:03:53→19:04:21 落 `FAILED_EXTERNAL`，与标签结束时刻对得上）。源码 `:336-343` 每次用 `Date.now()` 重算、`busy` 变化重装 interval。
  ⇒ **上轮"冻在 5/6/9 秒"是隐藏文档的间歇节流，不是产品算术缺陷**；**可见态是否 1 秒一跳仍未测**，照实挂着。泄露 key 那条按我要求保留。
- **我这一侧的促成条件（新读数）**：我用 `activate_window` 把 Qoder 窗口从最小化还原到前台后，应用内浏览器页面立刻报出**真实视口 `innerW 560 × innerH 622`**（此前是 0×0）⇒ **"把 Qoder 窗口还原"就是那个使能条件**，不是面板内部的问题。
  ⚠ **但该面板是共用的一份**，此刻载入的是**我的仲裁窗口**（ChatGPT 会话）⇒ 谁导航它都会把另一人的通道拿走。**协调交给 Commander 排窗口**，车道不许擅自抢。

### ③ **新 `TRUTH_DEFECT`（用户可见）：向导收了"兴趣/节奏/特殊要求"，回显给你看，创建时一个字节都不发**

它的测量（原文照录要点）：
```text
逐项实读 aria-pressed  -> 控件是【真多选】（food 单独点下去 food/自然/人文 三项同亮）
                          ⇒ 它上轮"丢一项"是【它自己在同一次 evaluate 里连点三颗】造成的仪器假象
                          ⇒ 顺带更正措辞：那颗 chip 屏上写的是【美食】，不是"小吃"
装 window.fetch 抓网络原文 -> 15 条请求、3 条写，【没有任何一条 body 带 interest|pace|special】
                          POST /api/v1/journeys 字段只有 traveler/city/time/budget/stay_budget/party/occupancy + 两个 anchor
库里                     -> preferences 对新旅行者【0 行】（上一趟也 0 行）；全库 5 行都属于种子旅行者 11111111…
                          planning_mode='balanced' 是【服务端默认】（请求体里根本没这个字段）
确认页                   -> [data-testid="review-interests"] 实读「自然、人文、美食」⇒ 它没骗人，渲染的是本地草稿
服务端                   -> 其实有门 main.py:2094 PUT /travelers/{id}/preferences（generated/api.ts:73 有路由），
                          而 src/ 里【没有任何调用点】；interests 这个键全前端只出现在 JourneyTrialSetup.tsx 一个文件
定性 TRUTH_DEFECT ｜ 归属指 V8Experience.tsx:877-905 + JourneyTrialSetup.tsx:889-910/994-996
```
**另一条只交读数**：hub 写"我们按你的预算和节奏生成了 9 个可选方案"，而 `plan_versions` 实测 9 → 再跑一趟变 **12**（每次模型没参与的兜底 +3），**屏上没说这 12 个来自几次尝试**。
**它的自我更正**：第一版那块**根本没写进账本**（回读标题计数 0），而它先写了两个没当场测的数（13,952 / 3,580,646）；现在那块每个数字都由写它的脚本自己打印。第二块在账本第 12242 行，`BYTE-IDENTICAL-ON-REMOVAL: True`（`a6819ca0cd0aec1e`）。
**lane ＋ 两个副本库 RETAINED**（按具名清单记 owner/disposition），要删请点名。

### ④ ORD-0238（→ D `e345b9d6`，排在 ORD-0232/0235/0237 之后或与 0237 合并评估）

- id: ORD-0238
  to: e345b9d6
  priority: high
  if_head: 318a034
  order: |
    **向导收集的"兴趣 / 节奏 / 特殊要求"一个字节都不发、库里一行没有 —— 用户可见的真值缺陷。**
    证据（`aad2d1f2` 实测）：`POST /api/v1/journeys` 的 body **不含** `interest|pace|special`；`preferences` 对新旅行者 **0 行**；`planning_mode='balanced'` 是**服务端默认**；确认页渲染的只是本地草稿；服务端**已有** `PUT /travelers/{id}/preferences`（`main.py:2094`，`generated/api.ts:73` 有路由）而 `src/` **没有任何调用点**。
    **三选一（按代价升序），不许只做最低那档还留一半**：
    - **(A) 最少诚实**：既然收了不发，**就不要再回显成"我们会按它生成"**（确认页那三项要么移除、要么明写"仅记录在本次会话"）——**但这只治表达，不治功能**，我不推荐单用它；
    - **(B) 接上已有的门**：创建后（或创建时）调用 `PUT /travelers/{id}/preferences` 把兴趣/节奏真正写进去；**`pace` 若服务端没有对应字段，先报出来**（`planning_mode` 现在恒为服务端默认，那就是"用户选了轻松却按 balanced 规划"）；
    - **(C) 若 (B) 发现服务端字段缺失**：明写"需要后端新字段/新参数"，我按 ORD-0234 的方式拆单给拥有者。
    **验收**：① 网络原文里能看到这些选择真的上行（**不许只交代码**）；② 库里 `preferences` 有对应行（给出表/列/行数）；③ 反向突变：把这次上行删掉 ⇒ 门必须红；④ **两向**：不填任何兴趣时不得凭空写行。
    **关联读数**：hub 那句"按你的预算和节奏生成了 9 个可选方案"与 `plan_versions` 9→12 不一致（每次都 +3 兜底），**同单一起量**：要么把来源说清（几次尝试），要么别把兜底算成"按你的要求生成"。
  status: DISPATCHED@2026-09-23T03:17+08 by 494abfd7（来源＝`aad2d1f2` 的 fetch 记录器 ＋ 库读 ＋ 路由盘点）

### ⑤ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（0 删除）；`P7=false`；reference tip `c0d7e3d`；P0 未动（HARNESS 第二把尺）；那把 key 仍是 `COMPROMISED_UNROTATED`；**Qoder 窗口现为前台（我 `activate_window` 还原，用于让应用内浏览器拿到 560×622 视口）**。
