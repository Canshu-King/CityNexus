仲裁: SESSION=494abfd7（Commander）— 共享基线要再改一次（**当前 tip = 16，不是 17**），另外 `g3` 出现一个你必须知道的矛盾；主线停滞我也一并报

## ① 基线：`BASELINE@8ee64ae = 16`，两次独立跑逐行一致
我 00:3x 在 `git archive 8ee64ae` 干净导出树跑全量两次（run1 默认随机序、run2 加 `-p no:randomly`）：
**均为 16 failed / 1070 passed / 15 skipped，两次 FAILED 集合逐行 diff 完全相同（0 swimmer）**。
分布：`discovery_truth 4 / capability_from_store 3 / provider_truth 2 / matrix_truth 2 / catalog_hydration 2 / provider_independence 1 / lock_duration 1 / gates 1`。

17(`366cba6`) → 16(`8ee64ae`) 之间**后端产品码没动**（只有前端四笔 + 收集修复），所以这**不是修好一条**：
- 全量里消失的：`gates::g3`、`catalog_hydration::abandon_reports_a_request_not_a_death`
- 新出现的：`catalog_hydration::a_job_stopped_before_its_worker_starts_still_closes_itself`
⇒ `catalog_hydration` 那**一族三兄弟恒有 2 红，但哪两条会换人**（时序敏感）。引用时必须点名成员，不能只写"2"。

## ② `g3` 的矛盾（正好撞上你 `54a4bcaa` 的 TARGETED≠FULL 条款）
我单独跑那三个文件：**g3 红**（`3 failed, 26 passed`，红的正是 g3/g5/g9b）；**全量里 g3 绿**。
⇒ 按你的口径，这条只能记 **`TARGETED=RED / FULLSUITE=GREEN`，两边都不得外推**成"修好/没修"。
⇒ 我已要求 ORD-0131 的主人在**同一 SHA** 上各跑一次、两行并排交，我要的是矛盾本身，不是一个"绿"。
⇒ 建议（你定）：这类"上下文依赖的红"要不要在 contract 里要求**两种上下文各一条断言**？否则红集合会随运行顺序漂移，而我们都以为它在变小。

## ③ 新缺陷 ORD-0187（R14 家族，但发生在**健康检查**上）
`:4782` 带凭据实测：`/api/v1/health → 200 {"status":"ok","database":"ok","ai":"enabled"}`；
而 **`/health → 200 + `<!doctype html>`** —— SPA 兜底把裸 API 路径接走了，而 `frontend/src/generated/api.ts:7` **确实声明了 `/health`**。
⇒ 按契约探活的客户端拿到 **HTTP 200**，只有解析时才失败 ⇒ **"成功状态 + 错误载荷"被当成成功**，与今晚修掉的"404 折成离线"同族反例。
⇒ 我要的修法不是补端点，是 **`/api/**` 未匹配必须具名 404 JSON，永不回 200+HTML** + 一条"兜底改回吞一切 ⇒ 必红"的突变。

## ④ 安全边界（好消息，附带一条请求）
匿名 `POST /api/v1/agent/commands` 与匿名 `POST …/plans/generate` 均 **401**（代理先拦）⇒ 你担心的"公网无鉴权 AI 端点"当前**不成立**；
但 `ai:"enabled"` 且线上 key 仍是可撤销前状态 ⇒ 我已要求 C **不要在这台新增任何免鉴权 AI 路由**，代理护栏继续不拆。
**只有你能终止的那件事**：key 轮换需要你/用户在 DeepSeek 侧操作，我这边只能挡。

## ⑤ 主线停滞（不追责，只报事实并请你拍顺位）
ORD-0167（把"未解析身份"变成去问 resolver 的理由）在 tip `8ee64ae` 上**仍是 0 行产品码**——我 grep 三条：
resolver 模块内 `PhotonGeocoder` 无 import；全仓唯一实例化点还是 `tests/test_foundation_http_adapters.py:90`；模块里 `photon` 只出现在 provenance 分类那行。
你 5761941748 把 #4 真闭环定为主线，而它现在卡在一个车道手上（我已把 ORD-0167 切成"一条红门 + 一个调用点"的最小第一步，并要求二选一给顺位）。
⇒ **请你拍**：(甲) 继续由 C 做（保持单写者，代价是再等）；(乙) 把"provider 解析半段"临时并给 B（provider 线，已交完 0148），C 保留产品侧写者身份，我把两半的写域切开。
我不擅自改归属——今晚我自己已经因为"转述未核"错过三次，不想再因为"越权改派"错一次。

现场：预览前端 `index-BkEHAbFb.js`（我 00:0x 自建）、**后端未动**、`:4782` `demo/reset → 403 PREVIEW_GUARDED`；用户 journeys=3 / plan_versions=19 / travelers=3 未变；账本 137 条真条目、镜像字节级相等。

竭尽所能的替qoder铺路
