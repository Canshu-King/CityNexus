# Revolution R57｜Codex 即刻施工：旅客硬约束真正进入 Agent 规划与可行性门

- **负责人**：Codex；独立分支 `codex/r57-travel-hard-constraints-20261027`
- **基线**：`22f1fe174ddebf6afa2daaccb84b2beea7caccfd`（PR #56 当前完整成果），**不是** Qoder 的 rescue 工作树。
- **与集成线的关系**：PR #56 保持冻结，交 Qoder 正常合入；R57 是它之后的 *stacked* 后端增量。不得直接推 `rescue/v3-final-departure-20261022`、改 Qoder 的 `frontend/`、课堂 BAT/本机现有测试数据库、强推或 stash 他人的 dirty 文件。后续 PR 只提交 R57 新增产品差异，Qoder 负责最终合并及真实 Chrome。
- **目标一句话**：用户说“坐轮椅、不能走台阶、每段步行/推行≤500米、Day2已有不能更改的预约；只改Day1下午，其他保持原样”，Agent 不再只把约束写进 notes 后许诺“500米内可达”，而能保存**有明确作用域的机器硬约束**，主动查证路线/设施，给实际可选方案，并在证据不足时明确 UNKNOWN、指出缺口、继续寻找替代方案；最终正式 Plan 不能无证放行，也不能因一个未知值让 Agent 整体罢工。

## 为什么现在做（GitHub 已有真实用户证据）

1. `trial/results/20261027_WHEELCHAIR_PARTIAL_DRAFT.md`：同一苏州 Journey 390px 真 Chrome，Agent 成功将 Day1 下午改为室内参观+坐着休息，Day2 JSON SHA 完全不动，**但四个槽 Place ID 都为 null，500m/无台阶只在 notes，opening/cost/travel UNKNOWN**。界面标题“≤500米内可达，距离未核实”把要求与已证实事实混在一起。不要把这次已形成的草案冒充已可执行无障碍行程。
2. `backend/app/agent/goal_draft_patch.py:493-542` 中 `replace_draft_slots` schema 只有 title/time_of_day/place_id/notes 和特例 start_not_before；缺普通结构化 mobility/capability 修改路径。
3. `backend/app/replanning/feasibility.py` **已有** HARD `STEP_FREE_REQUIRED`、`AVOID_STAIRS`、`MAX_WALKING_PER_LEG_M` 与可信来源的 UNKNOWN/CONFLICT 判定；`backend/app/agent/goal_route_freeze.py:_walking_cap_m` **已有**步行 cap 提取和 transit 备选，但未证所有 Agent 草案/按半天修改的硬条件能持久化到这些执行门。优先复用，禁止再造一套平行规则。
4. `trial/results/20261026_COUPLE_LATE_START_UI.md`：真实旧 task consent 与刷新 UI 的“本次不同意”互相打架；这是 Qoder UI 主责，Codex 必须保证后端**显式撤销 model/online consent 不会发起 Agent 或 Provider**，并交代现有后端契约，不能代改 UI 或声称已修刷新问题。

## P0 第一刀：结构化约束传递，不靠自然语言备注猜执行事实

- 在现有 `JourneyIntent.capabilities_json` / GoalTask draft artifact / 对应 Constraint / feasibility 输入的**单一权威路径**上，把“轮椅/无台阶”和“每段≤500m”变成明确的 `STEP_FREE_REQUIRED`/`AVOID_STAIRS`、`MAX_WALKING_PER_LEG_M: max_m=500` 等已实现词汇，保留 USER_DECLARED 来源、强硬程度、用户语言、作用域、修改版本/时间。哪个表示层作为 canonical 由现有实现决定，但只写 notes 不算交付。不要从“轻松少走”“多走一点也可以”擅自推断出精确500米。
- 必须区分「旅客的要求」与「供应商核实的事实」。user says ≤500m 是约束，**不是路线已经通过500m**。结构化值应能被正式 prepare/freeze/selection 的 writer 读取、用于硬条件判定。存在已经保存的明确约束时，第二轮 Agent 只修改 Day1 下午，必须保留约束和 Day2 原始预约/slot、时间与身份，除非本人明确授权变更。
- 优先做可小范围交付的真实 API/领域代码，不预先全面重构 Agent prompt；如需要更改 `backend/app/main.py` 或跨 Qoder UI 的合同，先在 Issue #47 发一段字段与错误码契约。向后兼容旧客户端（未声明轮椅/行走 cap 的旅程不得突然全拒）。

## P0 第二刀：查证与可执行门，Agent 应主动找出路

- 在既有来源 Place / route freeze / feasibility 上让每一条**实际使用**的活动和步行/地铁转场关联已采集 provider 事实。步行距离用明确 `walking_distance_m` 或可信的行走分段；**不得拿 TRANSIT 总里程当步行距离**，不得按起终点直线自称步行可达；无台阶须供应商/明确可查来源的无障碍证据，不能因为地图有线就推断轮椅通行。
- 两种合法结果：① 数据确实核实 max walking ≤500m、无台阶且所需地点可达，正式候选按权威 feasibility 通过；② 有一段超限或无障碍未知，则阻止**声称已核实可执行**的正式方案，返回机器 `constraint_code + affected_place_or_edge + evidence_state + next_action`，但仍保留 DRAFT、已研究事实和可继续的工具权限；允许 Agent 建议更近地点、调整访问顺序或继续查证，不许“缺来源→停工”。
- 如果当前高德/OSM 来源不含站内电梯、门宽、坡度等属性，就如实标 `UNKNOWN/NEEDS_EVIDENCE`，不为了把测试变绿而编无障碍字段、取消硬约束、降低限制或者给用户代买车票。公开来源快照允许复用但必须明确采集时间与 provider provenance。
- 提供最小安全的只读结果字段示例给 Qoder 消费：**requested constraint / measured result / confidence or provenance / exact unknown / user action**；保密字段不出投影。不要写纯概念设计稿，先在后端跑通一个 API 片。

## P1 第三刀：模型同意的服务端硬门（紧随第一刀，别抢 Qoder 前端）

- 给 `resume_goal_task` / run / tool gateway 添/补负例：**显式** `model_consent=false` 不开始新 AgentRun、`online_research_consent=false` 不启动在线 Provider（已有记录读取/离线操作可以继续）；反复请求/刷新不应靠旧同意自动越过一次明确撤销。对于「UI里取消但没有发到服务器」明确写**客户端未发撤销，服务端不可得知**；不要宣称后端已经修好了 Qoder 的 reload checkbox。
- 不建议在不通知 Qoder 的情况下把所有旧客户端 API 默认改成拒绝，以免已有 GO 流程倒退；如果必须引入每次发送显式 consent 的版本化字段/nonce，先给 Qoder最小向后兼容的 API 契约与一项可迁移调用示例，再实现。
- 相关安全基线：Journey 成员 401/403/200，不因无障碍事实可公开读取而放宽私人行程 ACL。特殊需要和身体状况属于敏感信息，只在授权 Journey 内保存/投影，日志与公共城市目录不得泄漏。

## 验收门：必须有真实产品增量，不得只做 verifier-only 循环

**第一笔 push 先改可运行领域代码 + 回归**：从已签名用户自然语言约束（不要预置“已验证500米”假事实）存入 canonical 机器值 →同任务读取/刷新/同半天 patch 不丢→正式评估能看到该要求。附具体 PRODUCT_SHA、旧→新 API JSON 投影（脱敏）、一条明确未核实的可操作原因。再做来源路段/无台阶验证闭环。

聚焦测试至少覆盖：
- 含 500m 的 HARD 与“少走路”的 SOFT/未知，550m 正确拒绝，源明确 450m 但 step-free 缺证仍不能宣称无障碍达标；
- TRANSIT 的 walking_distance_m 缺失不把总行程距离当步行，GCJ02 未转换不得伪 WGS84；
- 外部来源缺失、过期、冲突、伪造 Place/其他 Journey 事实拒绝冒名，重复提交幂等；
- Day1 下午 patch 后 Day2 预约字节一致，已签名成员权限与明确拒绝 model/online consent 的工具调用次数保持 0；
- 一个来源确实可证的正例（可以是标注 TEST_FIXTURE 的集成测试）及一个真实 provider **可用才运行**的窄证据。不要以合成正例充当真实供应商认证。

在独立隔离 SQLite、最小化外部请求上运行聚焦回归与 GitHub CI。不能改断言来“全绿”，不能往正式 DB 填测试地点。原有 PR #56 北京/杭州/苏州 READY、苏州同 run 四站签名完成的事实保持，不因新增规则回退非无障碍用户 GO；本轮不重复收费模型/高德调用造成功。

完成后先 push 独立 Codex R57 分支、开**窄范围新 PR**（PR #56 合并前可 stacked base 到其分支，合并后再按最新 rescue 评估），附 `PRODUCT_SHA / TESTS / AUTH_CONSENT / CONSTRAINT_INPUT_TO_GATE / REAL_VS_FIXTURE / PENDING_QODER_UI`。交 Qoder 做唯一前端 UI/Chrome/实物设备验收。**首件应是用户约束能落入机器执行门，不是又多一份报告。**
