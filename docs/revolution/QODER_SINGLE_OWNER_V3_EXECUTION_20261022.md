# CityNexus Revolution V3｜Qoder 全面接管执行令（2026-10-22）

**执行负责人：Qoder；原 Codex 会话暂停写代码。** 这是用户对当前 CityNexus Revolution V3 剩余产品任务的明确决定，取代 Issue #42 中原先的「Codex UI / Qoder 后端」双线同时施工分工。所有当前 V3 前端、后端、Agent 工具、Guardian/多人、集成、体验改版、演示验收与交付，由 Qoder 统一完成。历史 commits、现成真实功能、签名权限、两条 PR 保留；不宣称用户 Windows 本地 Qoder 已被 GitHub 评论自动启动。

## A. 唯一主线与分支规矩

- **开发/集成唯一落点：** `rescue/v3-final-departure-20261022`；其起点 `0f61745b9c469efa5a8363dc193e597b98642814`，已经包含 Codex 真正最后产品提交 `3c5cdd02e176a3f19fa5b4118063eb1230d658be` 及恢复 taskbook。
- **目标合入分支：** `design/revolution-mobile-first-v1`（Codex PR #23 产品线）。Qoder 在 rescue 分支提交，后续单独开 PR 以此为 base；不向 PR #23 强推、不 force push，不直接更改 repo default branch。
- **能力来源：** `reform/qoder-capability-adapters-1018`（Qoder PR #35，核验 HEAD `33436585634dd71714b6058920f9bf1b5100aeee`）。只做**按具体文件/契约依赖的窄移植**，保留 Qoder 原工作树和 PR；停止在 PR #35 的文案、量具、零前端读者 API 上长期消耗迭代。
- **Codex 暂停：** PR #23 保持 OPEN/DRAFT，只作历史产品与 PR base；Codex 故障会话不再同时施工。恢复后也先从 rescue 的真实代码与任务书读取，不与 Qoder 抢写热文件。
- 本任务书优先级高于 Issue #42 历史分工。若 Qoder 手上已有未提交文件先 `git status` 保护，另开独立 worktree，不 `reset --hard`、不清理数据库、不覆盖密钥、不中断已运行的正常服务。

## B. 继续哪里，不能误报什么

**已真实交付，可直接复用，不准倒退到静态 demo：**

1. `docs/revolution/v3-design/` **41 原始设计条目**：10 个 PNG、10 个 HTML、17 JPG、目录、中文交互规范等；都是设计参考，不是假实时数据。
2. `/revolution` 新版「探索 / 我的旅程 / 我的」、跨空间唯一 Agent 输入、同 Journey + GoalTask 持续对话、真实来源媒体、地图/日程联动、A/B/C 备选、局部改日程并刷新保留。
3. **首份签名候选已打通**：`POST /journeys/{jid}/agent/goal-tasks/{tid}/prepare-plan` 在真实签名广州任务 HTTP201，保存 3 slot 的 `PlanVersion CANDIDATE`，保持日期/时间/来源 metadata，页面 reload 后恢复。最后产品报告：`trial/results/20261020_V3_DRAFT_PREPARATION.md` 与 `20261020_DRAFT_PREPARATION_LIVE.json`，候选 `54d2cfca-ad1f-4dd5-a198-128c21a1294c`。
4. **现实阻塞**：目前候选 `selectable=false`、费用 `PARTIAL_UNKNOWN`、未映射 Place、没有足够转场事实；`selected=false` / `activated=false`，未完成 ACTIVE、Guardian/collective 的真实连续使用，`USER_VERIFIED=PENDING`。
5. **时间事实**：历史实测广州行程的时段是 2026-10-20，已过期。新的正式出发测试必须使用未来日期的新鲜 Journey，不得将旧回执宣称成 10 月 22 日可出发证明。
6. Qoder 后端分支已有 `place_source_lead`、`place_media_routes`、`plan_from_slots`、`plan_evidence`、`departure_commit`、`collective_consent`、`plan_delta` 等模块，但与 Codex 产品线未整体集成。`plan_from_slots` 在原上游对空 `active_plan_version_id` 的 `expected_revision` 曾有无解缺口；当前 **task-aware prepare-plan 已独立解决首趟候选**，不要为合并而抹掉它。

## C. Qoder 全权施工顺序（按照真实用户行为而非模块数量）

### P0. 能打开、能操作、能看到 Agent 在工作

首先在 rescue 的真实客户端和后端做一次最短实测：单用户输入旅行愿望（未来日期），Agent 询问或研究 →真实 source POI/照片/地图 →三种方案 →在同一 task 改某半天 →刷新恢复。首页、主导航、Agent 对话、地图、日程不得要求用户学习工具名。工具过程来自持久化真实 Run/Step，失败可继续、有部分成果，不得假动画与假成功。保留深层调试折叠入口，不占据普通旅行者主屏。

**尽早交首个代码提交**：即使这一段暂时只能修复一个用户可点的断点，也先 push。不要等完成全十屏或撰写长报告才上传。

### P1. 从已保存的 CANDIDATE 真的走到正式选用

当前关键用户入口：「我的旅程 → 准备出发」以及同一任务 `prepared_plan_id`。

- 复用已签名的 `prepare-plan`，不在前端重建另一套手动选地点/生成行程。
- 为源 ID `amap:...` / Photon / Nominatim 等接**服务器拥有的身份映射**：在原 Journey 城市、原 task scope 和 provider/external_id/来源证据下查找 canonical Place。不可凭名称猜测、不可编造 Place UUID；未知时保留原 ID 与理由，Agent 主动尝试被授权的来源工具，不让全任务罢工。
- 动态补齐营业、门票/成本、照片/许可和真实转场路线，正确处理 GCJ02/WGS84；来源时间、unknown/estimate/verified 要保持显式区分。未报价格 ≠ 免费；酒店建议 ≠ 预订。
- 将“待处理 3 项 / 哪一项缺什么”变成用户**可点的解决动作**；已取得事实时直接更新原同一 Journey 的候选/必要的正式版本与读取视图。所有正式写入受服务端原本可行性、权限与版本条件约束，不用 UI 层强行跳过。
- 当服务端真实可选：签名本人选用 / `departure/commit`（按对应代码实际已注册的路由，避免重复套门）→ `SELECTED` → `start` → `ACTIVE`。重试必须幂等，刷新后读回同一版本。不满足则诚实 `BLOCKED` 并交代下一次用户点击能完成的事。
- 独立验证首趟无 active plan、同 task revision 变化、两次点击幂等、已有方案基准改变、他人无权限、跨城误匹配、数据不足四种情形。复用 Codex 当前兼容的 DB 及 auth，不造新登录阻碍。

### P2. 旅行中、Guardian、多人决策接通真实界面

- ACTIVE 首屏下一站/地图导航/可确认执行位置，维持每位成员自己的身份和权限；没有真实 GPS 证明时不标记物理到场。
- Agent Guardian 使用真实 provider observation 或**明确标注的模拟事件**，给出影响到的 slot、来源、时间、预算差与可选替代。没有 material change 则显示正常状态，不能为了显示动作反复触发假闭馆/天气。
- 多人共享场景：创建 proposal → 每位有授权的本人分别表态，2/3 尚不更新 active PlanVersion，满足服务器真正规则时 3/3 才可应用。拒绝/退出成员的边界按现有 domain 合同，不让一个账号替别人同意。
- 图和数据统一使用同一 Journey/PlanVersion/GoalTask；Guardian 改变经确认后才反映在共享行程，刷新回读保持一致。

### P3. 十屏 UI 质量和真人试玩

- 按原十张设计的**功能与信息架构**，把探索、Agent 工作中、地图、地点、方案、日程、出发、在途、Guardian、多人方案统一成现代移动 UI；可借用原 PNG/HTML 布局，不把原静态 HTML 当最终运行代码。
- 390×844、430×932 实际 Chrome 手动点击、回退、键盘弹出、导航恢复、错误重试；1366/1566 桌面正常无整页溢出。优先人能看懂的入口、图片、地图、可操作按钮；确认文字不冗长，不能单靠更短的字典取代有用功能。
- 提供有入口的试玩/图文操作说明。若原本的 `http://127.0.0.1:14332/revolution` 只在本机可访问，不要将其说成公网可用；无需让用户每次自己启动复杂后端。

### P4. 产品线集成与收尾

- rescue 完成每个可用里程碑就提交 GitHub，并在 Issue #42 报 `PRODUCT_SHA`、`UI_VISIBLE_ACTION`、`REAL_HTTP`、`PROVIDER_EVIDENCE`、`BLOCKED_REASON`、`NEXT_CLICK`。
- 创建 PR：`rescue/v3-final-departure-20261022` → `design/revolution-mobile-first-v1`，以产品实际 diff 为验收对象；不要将 Qoder 的 PR #35 整枝数百文件混合到 PR #23，必要能力由窄移植提供。
- 保持默认主分支、用户数据库、授权、API keys 与已经真实可用的能力不变。无明确授权不要部署生产、更改收费服务或替用户预订/支付。

## D. 最小验收矩阵（不是「绿了就结束」）

| 操作 | 产品验收 | 证据不能偷换 |
| --- | --- | --- |
| 一句话开始 | 有真实 Journey/task、Agent 可连续对话 | 不只播 mock 过程 |
| 查地点照片地图 | 按真实 ID + 授权来源展现至少有效结果或明示失败 | 不拿 V3 原始示意图当新真实 POI |
| 三方案/改半天 | 草案仅改受影响 slots，刷新一致 | 不能复制 fixture 的预置结构冒充实时模型 |
| 准备出发 | 已有 Agent 草案产 CANDIDATE，待办可点且逐渐减少 | UNKNOWN 不改写为 verified |
| 正式选用/开始 | 合法 provider 条件允许则 `SELECTED` / `ACTIVE`；否则清楚可复现 BLOCKED | 不越过 PlanVersion / authority gate |
| Guardian/多人 | 真实或显式夹具，2/3 尚未生效、3/3 必要条件符合时生效 | 不让同账号代签，不伪造事件 |
| 真机体验 | 有真人操作时标记 `USER_VERIFIED`，否则继续 `PENDING` | Playwright/Chrome CSS 视口不算真机 |

## E. Qoder Windows 本地接管步骤

1. 在现有 repo 的干净或受保护工作树运行 `git status`、`git fetch origin`；不要碰有未保存修改的 Qoder 原分支。
2. 单独 worktree 到 `rescue/v3-final-departure-20261022` 的远端 HEAD（若分支本地未建立，创建 tracking branch；若已存在直接使用）；确认包含本执行令和此前的 `REVOLUTION_V3_RECOVERY_RELAY_20261022.md`。
3. 首先只看最新产品与相关文件：`trial/results/20261020_V3_DRAFT_PREPARATION.md`、`frontend/src/trial/mobile/DraftDepartureCard.tsx`、`MobilePlanWorkbench.tsx`、GoalTask 的 `prepare-plan` 注册/实现、Qoder 已有位置身份/冻结/出发/成员 API。把依赖与功能逐个接入当前 V3，禁止整仓重写。
4. 只在 rescue 分支提交变更，首个可用切片立即 push；后续按上一段里程碑继续。
5. 文案/计数/类型测试只是辅助手段，**每棒必须有一段真实用户点击路径和后端回执**；没 provider 就诚实留未完成，不为了造通过去修改阈值。

**新模型或者新会话只需要本文件，不需要加载旧会话全部记录。** 这条接力在本地 Qoder 被用户真正启动/恢复时才执行；GitHub 推送不会自动驱动 Windows 客户端。
