# ORD-0369 · 手机端 Replan 真链路走查读数（lane Q，2026-09-28 +08）

视口 390×844 / deviceScaleFactor 3 / hasTouch / locale zh-CN，Playwright 1.63.0 驱动的 Chromium。
**这是设备模拟的手机视口，不是用户真机**（`REPRODUCED(simulated)`）；真机那一格只有用户本人能签。

## 四个面（每格读数具名到面，不混用）

| 面 | 地址 | 服务的是什么 | 用途 |
|---|---|---|---|
| 用户可见面 | `127.0.0.1:4782` → `:4781` | 权威尖 `4ef864cf` 的在服 bundle，后端 `:8693` | 只读走查（不写用户的库） |
| 车道 canary | `127.0.0.1:4187` → `:8711` | 同一份 dist 的**复制**、同一枚后端代码树、`Connection.backup()` 私有库 | 可写走查 |
| 候选面 | `127.0.0.1:4188` → `:8711` | 本分支构建出的新 bundle | 修后复走 |
| 门禁面 | `127.0.0.1:4206` → `:8711` | `npm run dev`（vite dev） | 9 条 e2e 门 |

canary 与用户可见面的"证据过期卡"截图**逐字节相同**（sha256 前 16 位 `f113ffb86520eedb`，
`before_user-surface_authoritative-4782.png`）——同一份在服 bundle、同一套后端代码，所以 canary 是
用户那一屏的忠实替身，不是另一套东西。这条对照是刻意做的：canary 只能替身，不能凭想象替身。

## 走查结论：这条链在手机上今天走不完，断在哪一格都有原文

1. 首屏 → 「使用封存的演示行程」 → 今天（`GET /experience` 等 11 条，全 GET，0 POST）。通。
2. 今天 → 「查看实时行程」 → 实时行程。通；屏上「当前没有需要你决定的调整。」（服务器 `GET /replans` 确实回空列表）。
3. **「提出一次改动」这一格，手机上只有两条路，两条都被拒**：
   - 教学舞台「请求重规划」→ `POST /api/v1/journeys/<id>/replans` = **HTTP 422**，
     `error.message` 是裸 token `MOBILITY_DATA_UNAVAILABLE`，`message_key` 停在泛用的 `request.invalid`，
     `details.gaps` 一条，`evidence_state` = `FACT_PRESENT_BUT_NOT_HARD_ELIGIBLE`。
     发射器：`backend/app/main.py:5513`（逐段）与 `backend/app/integrations/mobility/runtime.py:29` 的注释。
     ⇒ **外部条件**：这台部署没有可当硬依据的实时路线数据。产品码改不了这个事实，能改的是屏上怎么说（见下）。
   - 工作室（调整权威行程）→ 真指针拖动能改草稿（`无草稿变更` → `草稿与活跃方案不同`），
     「预览影响」= **HTTP 200** 且 `can_accept=false`，`deterministic_gate.failures` 7 条：
     `PROTECTED_ACTIVITY_REORDER`、`FROZEN_ROUTE_EVIDENCE_MISSING`、`STALE_FROZEN_EVIDENCE`、
     `MOBILITY_DATA_UNAVAILABLE:<段>|<段>` ×4。⇒ 「接受编辑」永久不可点，因为这一版 5 个活动全是受保护锚点。
4. 「接受」这一格：因为上面没有任何 proposal，`live-accept` 在屏上不存在（实测 `acceptPresent: false`）。
   **接受腿在演示部署上没有真链路可走**；它的产品码由 `e2e/golden.spec.ts:55` 那条既有门在 fixture 后端上覆盖，
   不是本单新造的证。

## 途中每一个断点的分级与本批做了什么

| # | 断点 | 分级 | 本批 |
|---|---|---|---|
| 1 | 证据过期卡整张硬编码英文（标题/详情/两枚按钮/回执句） | 产品码 | `f8e569a19c2a3f0a1850b799e2fe4f13c67d161c` |
| 2 | 该卡把 `body.error.message` 当主句上屏（实测 `No feasible plan candidates satisfy the journey constraints`） | 产品码 | 同上 |
| 3 | 该卡 `catch` 把任何异常都说成"检查你的连接" | 产品码 | 同上（走 `lib/failureAttribution.classifyReadFailure`） |
| 4 | 「Acknowledge warning」在只有 staleness 时必然 **HTTP 404** `no open recovery to acknowledge` | 产品码（屏上表达） | 同上：该态不挂载这枚按钮，改说"选定一份通过校验的方案后才会消失" |
| 5 | 工作室把 7 条 token + 4 对段号 UUID 拼成一行当解释 | 产品码 | `007e5aff28143fb8a528e13312fa3b629c43dee1` |
| 6 | 成本写成 `cost Δ -2400`（最小单位当钱）、时长 `495 min` 英文 | 产品码 | 同上（`formatV8Money` → `-¥24.00`、`495 分钟`） |
| 7 | 5/5 全受保护 ⇒ 草稿永远不可能被接受，而屏上事先一个字都没说 | 产品码 | 同上（动手前就说明，数字与同屏 meta 自洽） |
| 8 | 行只有 PointerSensor，键盘按 dnd-kit 自己写的提示去操作时无效；`cursor: auto` 看不出可拖 | 产品码 | 同上（补 `KeyboardSensor` + `cursor: grab`） |
| 9 | 禁用的「接受编辑」与能点的长得一样（`.v8-primary` 无 `:disabled` 规则，实测 opacity 1） | 产品码 | 同上（这一条是门 B4 先判红、我再补的） |
| 10 | 舞台 422 的句子诚实但不可读（只转述裸 token） | 产品码（可读性） | `958e4405315085a7ebe4f82be2b5efb7a4488e81` |
| — | 没有实时路线数据源 ⇒ 改动算不出来 | **外部条件，未修** | 见"没改善的部分" |

## 修后同一格的渲染原文（候选面，逐字）

- 舞台请求重规划被拒：
  「重算这一版需要能当作硬依据的路线证据。服务器说这些路程 1 段的证据在档，但达不到可硬用的标准（它给的码：
  MOBILITY_DATA_UNAVAILABLE，证据状态 FACT_PRESENT_BUT_NOT_HARD_ELIGIBLE）。所以它没有算出任何替代方案，
  你现在的方案没有变化——这一步要接上真实的路线数据源才会通。」
- 工作室试算被拒（原来是一行 token）：
  「新的顺序挪动了受保护的承诺 / 这一版在新顺序上没有冻结的路线证据 / 冻结证据在能被使用之前就已经过期 /
  新顺序里有 4 段路程拿不到实时路线数据」＋「技术详情」折叠里保留服务器原话与 4 对段号。
- 证据过期卡：「这趟行程的出行证据需要重新同步」「服务器针对这一版列出了 1 条拒绝，原文在技术详情里。」
  「服务器拒绝了这次生成（HTTP 422，具名 VALIDATION_ERROR）。没有任何方案被改动。」

## 门禁

`frontend/e2e/qoder-ord0369-replan-walkthrough.spec.ts`（9 条），
`frontend/playwright.ord0369-Q.config.ts`，跑在 `:4206` dev + `:8711` 私有后端上。
JSON 报告在本目录 `playwright-report-9-passed.json`，`stats`：`expected 9 / unexpected 0 / skipped 0 / flaky 0`，
`duration 27962.727` 毫秒。首轮曾 **2 红**：B4 咬到真缺口（`.v8-primary` 没有 `:disabled`），
B3 是我正则把负号放进货币符号里——产品那侧本来就是对的，改的是断言的形状，没有放宽判据。
