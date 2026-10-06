### SESSION=494abfd7 · **基线要改：当前 tip `8ee64ae` = 16（两次独立跑逐行一致），不是所有人还在引用的 17**；且 `g3` 在两种上下文里结论相反 @00:3x

`STATUS: BASELINE-REMEASURED-ON-CURRENT-TIP | 树 `git archive 8ee64ae` → `_qoder_cmdr_ref_20260921/tree_r14`（权威树 0 写）| 解释器 3.12.14、AI off、凭据清空 | run1 `--tb=line`、run2 额外 `-p no:randomly` |`

#### ① 数字
| 跑法 | 结果 |
|---|---|
| run1（全量，默认随机序） | **16 failed / 1070 passed / 15 skipped in 148.87 s** |
| run2（全量，`-p no:randomly`） | **16 failed / 1070 passed / 15 skipped in 130.70 s** |
| 两次 FAILED 集合逐行 diff | **完全相同 → 稳定核 16，本次 0 个 swimmer** |
分布：`discovery_truth 4 / capability_from_store 3 / catalog_hydration 2 / provider_truth 2 / matrix_truth 2 / provider_independence 1 / lock_duration 1 / gates 1`。

#### ② 与 17 的差**不是修好了**（这点必须写死，否则又变成"消失的红=绿"）
17(`366cba6`) → 16(`8ee64ae`) 之间只有**前端四笔 + `366cba6` 收集修复**，后端产品码没动，所以后端红不可能少一条。逐条对：
- 从全量里消失：`gates::g3_five_concurrent_hydrations…`、`catalog_hydration::test_abandon_reports_a_request_not_a_death`
- 新出现：`catalog_hydration::test_a_job_stopped_before_its_worker_starts_still_closes_itself`
⇒ 即 `catalog_hydration` 那**一族三兄弟里恒有两红、但哪两条会换人**（顺序/时序敏感，与 F 今晚"批次里消失的红一律不记绿"同一条）；
⇒ **`g3` 更要注意**：我单独跑那三个文件时它**是红的**（`3 failed, 26 passed`，红的正是 g3/g5/g9b），全量里却绿 ⇒
   按仲裁 `54a4bcaa/65f1934f` 的口径，**这条只能报 `TARGETED=RED / FULLSUITE=GREEN`，两边都不许外推成"修好"或"没修"**。
   ORD-0131（g3 的主人）请在**同一棵 SHA** 上各跑一次并把两行并排交，我要的是这个矛盾本身。

#### ③ 因此共享分母改成（全线引用这一句）
```
BASELINE@8ee64ae (no boundary, full suite) = 16 red   [两次逐行一致]
  stable: discovery_truth 4 · capability_from_store 3 · provider_truth 2 · matrix_truth 2 · catalog_hydration 2* · provider_independence 1 · lock_duration 1 · gates 1
  *catalog_hydration 三兄弟里恒 2 红、成员可轮换 ⇒ 引用时点名成员，别只报 2
  g3 状态 = TARGETED:RED / FULLSUITE:GREEN（矛盾未消，禁止外推）
带边界稳定核 = 13（F 的 ORD-0170 口径，tip 较旧；F 下一轮请在 `8ee64ae` 上重给 16→N）
```
⇒ **旧口径"17/13 成对"从今天起改为"16（无边界）/ 13（带边界，待 F 在新 tip 重钉）"**；
  仲裁 5763777551 ④ 里"tip 仍 `d26933c`"我已在 `5763806333` 更正，本轮再把数字一并更正，避免它按 17 出后续裁定。

#### ④ 本轮另外两条我自己量到的现场（已落单，不占别人算力）
- **ORD-0187（新，已派 C）**：`GET /health` 在预览那台返回 **200 + `<!doctype html>`**（SPA 兜底吞了裸路径），而 `frontend/src/generated/api.ts:7` **确实声明了 `/health`** ⇒ 按契约探活的客户端会**假绿**（状态码对、载荷是 HTML）。要的不是补端点，是 **`/api/**` 未匹配必须具名 404 JSON，永不回 200+HTML**；突变：兜底改回吞一切 ⇒ 该门必红。
- **安全边界仍守住（好消息，别再扩大面）**：匿名 `POST /api/v1/agent/commands` 与匿名 `POST …/plans/generate` 都是 **401**（代理先拦），所以"公网无鉴权 AI 端点"当前**不成立**；但 `ai:"enabled"` + 线上那把 key 仍是可撤销前状态 ⇒ 我已明确要求 C **不要在这台新增免鉴权 AI 路由**，代理护栏我继续不拆。

status: 基线更正为 16@8ee64ae（两次一致，0 swimmer）+ g3 的 TARGETED/FULL 矛盾禁止外推 + catalog_hydration 三兄弟成员可轮换；另落 ORD-0187（/health 假绿）与安全边界实测
evidence: `live_checks/fullsuite_8ee64ae_r1.txt`、`_r2.txt`、`red_8ee_r1.txt`、`red_8ee_r2.txt`、三文件定向跑 `3 failed, 26 passed`、`/health` 与 `/api/v1/health` 两条原样响应、两次匿名 POST 401
