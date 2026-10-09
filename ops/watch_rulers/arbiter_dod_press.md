仲裁: SESSION=EXTERNAL

已读 **5760495709**。两处我都压，但压法不同：

## ① #4 真 provider 闭环：**要，立即升为当前产品能力主线；不要等 #18 全绿**

但不抢掉已经在修的安全 P0：R13/ORD-0125 和 g3/裸 500 继续收口；**B/F 可以并行把 #4 做成隔离的端到端闭环**，不要让“先把红数变漂亮”挡住这条任务的命根。

首个闭环不要选一个会同时被 R10 身份 bug 污染的案例。建议顺序：
1. **贡山**先做 CASE3，因为 Photon canonical identity + extent 已经实测成立；
2. **云和县**作为 CASE4，在 R10 identity 修好后再走同链，证明不是特例。

### #4 的验收不是“接口都 200”，而是这一条证据链必须完整：

`raw destination text`
→ Photon canonical identity（真实 provider id + extent + WGS84 provenance）
→ Overpass 冷发现（无 seed / 无 mock places）
→ normalized persisted catalog（每个实体带 provider/source identity）
→ DestinationCapability 从 HYDRATABLE 变成真实可规划状态
→ shared planner 生成候选
→ 候选 used places 全来自这次 provider-backed catalog
→ used mobility legs 走 hard-eligible evidence
→ candidate SELECTABLE

硬门：
- 测试前确认该 canonical destination 在 DB 中 **0 预录 places / 0 golden catalog**；
- hydration operation 必须保留 Photon/Overpass provider observations；
- catalog entity 不允许 `mock` / `seed` / `synthetic identity` 冒充 live；
- provider 超时允许 PARTIAL，但不能把缺失类别说成物理不存在；
- warm 第二次必须命中 TTL/read gate，provider call count 明显下降；
- planner 失败必须能区分 catalog insufficiency / mobility gap / temporal gap，不许再折成 generic validation；
- 产出 SELECTABLE 的话，必须逐 used-place / used-edge 回溯 provenance；
- 最终交一份机器可复跑的 cold-chain evidence，不只截屏。

**#18 可以继续红着。** #18 的修复不能成为证明 #4/#6/#7/#16 的前置借口。先证明系统真的能从一座未预录的县长出可规划目录，这比先把报告数字擦漂亮重要得多。

---

## ② 实时 Valhalla：**要开，但不要直接在当前用户正在用的主预览上全量开**

R6 的方向不变：review/demo profile 必须真实 routing，不能永远吃手写矩阵。

但 `:8693` 这台当前预览刚经历两次 reset 事故、仍有 g3 并发幂等和 SQLite 裸 500，直接把所有用户流量从 mock 切到 live Valhalla，会把“证明 #7”与“给正在用的用户扩大失败面”混在一起。没必要拿用户当 canary，软件已经够有戏剧性了。

### 正确 rollout：两阶段

**Stage V1 — 立即开 isolated/canary review profile**
- 同一代码 SHA；
- 独立 DB 或 `_live.db` 一致快照副本，禁止写活库；
- `CITYNEXUS_REAL_CITY_ENABLED=true`；
- `CITYNEXUS_LIVE_VALHALLA_URL=<live endpoint>`；
- 启动日志明确 `discovery=LIVE / routing=LIVE`；
- 禁止 silent fallback 到 mock；
- N≤20，单 request cells≤100 分块；
- 明确并发限流/退避策略；
- live failure 变成具名 mobility runtime/gap，不是假成功。

用这台 canary 完成 #4 + #7 的组合闭环：**Photon → Overpass → catalog → Valhalla → selectable plan**。

**Stage V2 — 通过 promotion gate 后再切当前手机主预览**
至少满足：
1. canary 连续 ≥10 次 live routing 生成，无 silent mock；
2. used-edge provenance 100% 指向 live/frozen hard-eligible evidence，不含 `SYNTHETIC_DEFAULT`；
3. Valhalla timeout/5xx 场景 UI 有具名恢复态；
4. 不制造新的裸 500；
5. P95 额外延迟有实测并记录；
6. live routing 开关能 fail-closed，关闭时不会把 mock 冒充 live；
7. 当前用户 Journey 在切换前做一致快照；
8. 切换后先用 probe journey 做只读/新建验证，不触发 reset。

如果当前基础设施只能有一台 preview，那就做**同机 canary scope**：只对专用 probe journey / canary session 启用 live routing，不能一键全量切所有用户。等门过了再扩大。

### 对 #7 的最终定义

**#7 只有当至少一条正常 SELECTABLE candidate 的实际 used edges 全部来自 live Valhalla（或契约允许的 hard-eligible真实 routing evidence），且没有 `SYNTHETIC_DEFAULT` / mock fallback，才算过。**

“环境变量开了”不算；“Valhalla 偶尔返回 200”也不算。必须落到一个真实候选的 used edges 上。

---

## Commander 可立即下的硬令

- **#4/#6/#16：现在并行推进，不等 #18。** 首个 provider E2E 用贡山，云和县做 R10 后的第二案例。
- **#7：现在在 canary/review profile 开 live Valhalla，不直接全量切当前用户主预览。**
- B 负责真实 provider/cold-chain 证据；F 负责契约/门；C 只在明确写域交接后落实现；E/HJ 可从用户视角复验，但不走 API 捷径。
- 主预览 promotion 只有在上述 8 条 gate 通过后执行。

这次优先级我给得很明确：**先证明“Anywhere 真的能从零长出来”，再把它安全地推广到用户正在用的那台预览。**