# CityNexus 双线交付令｜2026-10-18：先让真人完成首次出行，再继续 Revolution

> 任务性质：直接开发与真实试玩交付，不是新一轮 ORD / verifier-only pass。GPT 在 2026-10-18 03:20（UTC+08）基于 GitHub 源码与 PR 核查制定。
> 严格双线：**Codex** 只做 `design/revolution-mobile-first-v1`、PR #23、Issue #26/#24、入口 **/revolution**；**Qoder** 只做 `review/qoder31a-signed-session-2235` → `mirror/integration-frontend-apple-pass1`、PR #32 / Issue #31、入口 **/v8/hub**。
> 快照：Codex HEAD `ccdd74866046498205b667b3b11b2b1260fdb8b8`，GitHub trial-build PASS（仅 fixture smoke）；Qoder PR #32 HEAD `4dd57ff92fcd99b9ba37a3b78427a65bcfda633c`，报告独立手机 Chromium 9 passed，PR 未合并；Qoder 主产品分支仍 `f5ecd9d854000e7eaa6ca07c55bd0436d4f80c68`。每轮开工须重新 fetch，不得把快照当永远最新。

## 唯一共同验收目标

- 用户只需照图操作，无需求助 GPT、不用粘贴坐标或 OSM 链接、不用理解开发者术语。入口与使用说明匹配**用户实际打开的代码 SHA**。
- `USER_OPENABLE`：本机用户可打开真实运行实例，前端/后端/数据库同一个隔离 runId，有确切 URL 和 health、checkout SHA；与 `USER_VERIFIED`（本人亲手走通）严格区分。
- `REAL_POI`、`POCKET_WALK_GO`、`ACTIVE_JOURNEY`、`LIVE_AGENT_RUN` 分别按**同一会话**的服务端结果独立标记；历史实测可保留但不拼成一次新的通过。
- 一切外部请求按显式用户许可；绝不靠伪造地点、假 Agent 工具事件、私有推理文字、假审批、自动重试无幂等 POST 使测试变绿。

## Codex｜C0：先交用户能亲手打开的新版（优先立即做）

1. 从 PR #23 最新 HEAD 新建不影响旧现场的隔离 worktree，使用现有 `trial/try_revolution.py` 及当前代码，不覆盖旧 `:14173`、`:14176` 或任何历史 SQLite。若端口冲突，明确选一个新端口，并提供 **具体 PowerShell 一键启动指令 + URL + /api/v1/health 读数 + git SHA + 进程日志位置**。不可只给测试截图或说“准备完成”。本机 localhost 仅对实际运行这台电脑可达，停机后不得继续宣称在线。
2. 以**同一新实例** 390x844 人手逻辑实际点击：第一次打开 → 新建签名 DRAFT（记录两次 POST 201）→ 输入中文城市 → 查地名 → 地名服务失败时紧邻按钮一键选择“Photon 备用地名查询”或“应用内地图手选”，无需用户自行找地图 URL、坐标。MapLibre 瓦片不可见时不得把“地图入口出现”叫做可以选区；要给真实可用的另一条操作路，并清楚说明来源、许可和不可用原因。
3. 修订遮挡：初始视口里地点查找/下一步按钮不得被底栏覆盖；AI 未启用时只显示醒目简短状态与“继续手动探索”。每个页面一项明确主动作。写入结果模糊时沿用已有防重写逻辑，不悄悄再 POST。
4. **先交 C0 checkpoint**：能够打开的新 URL、代码 SHA、健康响应、第一页与地名降级的两张真实截屏、实际点击记录、唯一剩余障碍。不要把 agent/live provider 的进一步工作扣在这个 checkpoint 之前。

## Codex｜C1：一条连续真实路线 + Revolution 专属图文教程

1. 在一个支持真实地点的中文城市/区域（优先复用已成功的宁波、武汉来源经验，不得替用户默改城市）完成**一次连续**：城市选区 → 显式同意查询 → 两个独立真实 OSM/Photon/Overpass 来源地点 → 保存签名私人 Pocket Walk → GO → 刷新后服务端恢复相同路线/进度。不得把上一轮宁波/Wuhan 与此轮 Quanzhou 零结果拼作同一成功。
2. 当 provider 返回 0，页面给出用户可点的“改类别 / 换附近区域 / 明示换一个公开来源”动作，按钮附近写人话和来源事实；按明确许可最多一次每种查询，不循环轰击。若外部服务全部故障，可以提供独立**清楚标为 DEMO/SAMPLE 的试玩模式**供用户看清交互，但绝不纳入 LIVE_POI/GO 证据，也不让 DEMO 代替真实数据验收。
3. 必须提交 `trial/REVOLUTION_USER_ILLUSTRATED_GUIDE_CN.md` 和仓库内可见截图：**不是 Qoder 的 V8 画面**。覆盖首页/输入城市、地名失败备用入口、地图选择/兴趣、真实地点、选两站、保存、GO、刷新、行程页与 AI 工作动态、异常恢复。每一步**单屏或局部放大真实截图上直接画红框/箭头/数字**，箭头指向真按钮，图下 ≤2 句人话；原始 PNG 和标注版分存、可重复生成，屏幕禁止巨长空白/遮挡。没有 ACTIVE Run 的 AI 图必须写“暂无真实运行”，不得混用 fixture。
4. 发布**同 SHA 新实例**的简洁“用户照做卡片”：第一步打开哪个 URL，第二步点哪一颗按钮，操作到哪一步能看到真实 GO。以可见UI、真实 Network、持久结果为准，CI fixture 为补充。
5. C1 未成功时回报 `PARTIAL` + 具名一个原因、当前能到的真实最后一步，不能以 12/12 UI fixture 替代。

## Codex｜C2：只在 C1 稳定之后，再推进真实 Hermes AgentRun

- 不再停留在 DRAFT read-only AI 建议。通过正式 Journey 的生成、确认、授权、`ACTIVE` 条件后，尝试**一次有边界的真实模型/工具运行**，记录持久 `AgentRun`、服务端工具起止/耗时、权限请求、失败或 no-op 的真实状态；外部服务不配置则如实写 `NO_LIVE_RUN`，不把 `TEST_FIXTURE`、`Journey.created` 当 Agent 执行。
- 手机上的“AI 工作动态”必须一直有入口（含 DRAFT）、说明不能工作的原因与可执行下一步。隐藏模型私有思维链；可展示的公开摘要与真实工具事件要严格区分。**先交 C0/C1，不必等 C2 才让用户试玩**。

## Qoder｜Q0：安全合入原本 V8，不向 Revolution 冒领教程成绩

1. 基于 PR #32 `4dd57ff92f` 最新状态继续，修掉图①灰色不可点“下一步”却被作为当前步骤描红的错误：要么补拍填满必填项后可点击状态，要么先在图里引导全部必填格；教程里每个被圈的按钮都必须实际能点。图⑥ `catalog.count.zero` 为产品原始机器码，修前端中文回退后再拍真图；压缩“中止之盾”那段吓人的长文到普通用户能看懂的规则。
2. 保留 `e8a2bee...` 对已配置签名服务器匿名读/写私人 Journey 的 401 收口和 403 成员权限；不要为了旧匿名 fixture 打开 `CITYNEXUS_TRAVELER_AUTH_ALLOW_ANONYMOUS_PRIVATE` 使产品变不安全。对**涉及个人信息的相关派生读写接口**做一次有边界的同人/异人/匿名检查（不要求无穷全仓 ORD）；明确 demo 公开能力与私人能力隔离。
3. 处理已有 `91 passed, 2 baseline failed`：复核具名两项历史失败是否与本 PR 改动相关，记录真实结果；修 PR 引入的红，勿盲目改门禁让所有断言绿。保留新的真浏览器 9 臂对一人两旅程、换人、签名、Today 与 AI 动态和步骤截图的覆盖。
4. **在 review/CI/范围通过后合并 PR #32 到 `mirror/integration-frontend-apple-pass1`**，交合并后 SHA、启动命令、可进入的 V8 入口、图文教程链接；不把 Commander 账本、开发分支提交或 PR mergeable 状态冒充主产品已经交付。若受保护分支门禁阻塞，点名唯一 blocker 和具名通过方案，不 force push、不直接改真实库。
5. `Q0` 的完成不代表 Revolution `:14176/revolution` 已修复，两个产品入口分开验证。

## Qoder｜Q1：真正能继续使用的身份恢复

- 当前短时签名默认约 15 分钟失效，关闭标签/浏览器后没有可信重登录就拿不到旧行程。**下一棒单独解决这个根本体验**：会话内安全续期与可信重新认证（优先核对现有邮件 OTP/Passkey 能力；没有运营邮箱服务就采用用户明确保存且经服务端哈希验证、严格限速的一次性恢复码等可落地方案，并明确其限制）。绝不能凭 `traveler_id`、行程 UUID 或本地指针直接换新 token；不能把 bearer 长期放 localStorage。
- 在 V8 提供“继续上次行程/会话已过期/重新验证/找回行程”真实按钮和明确恢复结果；真人两浏览器场景测本人找回与 B 不可查看 A。
- Q1 不阻止 Q0 已修产品合入，但不能把短会话体验称为完整用户账户体系。

## 双线协作与报告纪律

- Qoder 给 Codex 交**契约，不移植 V8 的组件/8 张图**：`POST /travelers` 的签名会话、`GET /travelers/session`、私人 Journey owner/member 验证、签名 GET Agent 事件与运行状态、拒因区分、写入结果未知的恢复边界；Codex 决定最小适配到 Revolution，不反向降权。
- 不交错修改同名 `RevolutionQuickExplore.tsx`、`V8Experience.tsx`；两个 PR 不全仓直接 cherry-pick，功能各自先验证，再单独开融合任务。
- 每次实质 checkpoint **至多一屏文字**：实际代码 SHA、真实用户新增一步、真浏览器结果/Provider 事实、能打开的地址或启动命令、截图链接、**一个**当前 blocker。没有产品代码变化，不再更新十轮空的 ORD。
- 优先顺序：**Codex C0 → Codex C1；Qoder Q0 与 C0/C1 并行；Codex C2 与 Qoder Q1 后续**。不要要求用户替两边复制长提示词，也不要把用户尚未亲手玩的状态写成 `USER_VERIFIED`。

## 真人验收表（不能偷换证据）

| 用户可感知条件 | Codex /revolution | Qoder /v8/hub |
| --- | --- | --- |
| 同 SHA、同实例真的能打开并操作 | C0 必须 | Q0 必须 |
| 无需开发知识选择下一步，失败有实际恢复按钮 | C0/C1 必须 | Q0 必须 |
| 真实地点、两站保存、GO、刷新恢复 | C1，必须同一 session | 不冒领 Revolution 的成功 |
| 真实 AI 运行/工具工作记录 | C2 单列，没运行如实写无 | 面板状态真实，实际 Run 另验 |
| 手机截图上直接标按钮的新手教程 | **Revolution 独立一份** | V8 独立八图，继续修 |
| 浏览器重新打开后可找回自己的私有行程 | 现阶段如实标限制 | Q1 必须 |

**立刻开始实施，不接受只回“任务已收到/计划已更新”。**
