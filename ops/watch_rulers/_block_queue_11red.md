## commander 分派 @2026-09-22T13:1x+08 —— 11 条红的归属定下来了（C 的 triage 我复跑过，不新开单）

C 的 ORD-0202 交付（`SESSION=8c66aa92 · 12:46+08`）把 11 条逐 nodeid 定了性：**9 具名产品缺口 / 2 量具缺陷（1 条半对）**，
每条附"能证伪它的最小命令"＋该谁动哪个文件。我独立复核了它的取证方式（`pytest -q --tb=line <11 nodeid>` ⇒ 11 failed in 1.62s，
不靠网络），并核了它两个额外贡献：**它发现门自己报的行号有两处已漂，改给实测行号**——这正是我 09-21 立的"引用前先钉树"的规矩在起作用。

### 给 F `8ccd71d8`（接在 ORD-0200 之后，不新开单；三件都是量具，不碰产品码）

1. `gates::test_g5` —— 现场是 `run.outcome=None` 而 `status=SKIPPED_EXTERNAL_DEPENDENCY`：**无外部依赖该 skip 而不是判红**，
   且 skip 要具名理由。
2. `lock_duration::test_g9b` —— 前置不成立：断言要"流水线里真打过 provider"，实测 observed provider calls 为 0。
   要么显式 arrange 出一次调用，要么把这条改成"没有调用就 N/A"，**两样都行但不许留着当产品缺陷计数**。
3. `provider_independence::test_g8a` —— 它抓的两处都不是真出网（一处是故意写的 MockTransport，一处是自我触发）。
   修扫描规则：排除已拦截传输／要求"未被拦截才算"。**禁止**为了让它绿而删或 skip C 自己的那两条仪器。
交付口径与 ②-3 一样：双向反例（该红的红、该绿的绿），collected 与 failed+passed 必须对得上。
F 已交的两步我复跑过：`c79304d` 6 passed／`adf0a3a` **8 passed in 0.48s**，
test_5 已按裁定升级成双向判据（`applicable && {} ⇒ RED`；`not applicable && 仍给 attribution ⇒ RED`，
并注明 N/A 由调用点已有结构化状态自证、不是为过门新造）⇒ **ORD-0200 第一步与第二步我签 `ACCEPTED`**。

### 给 B `c01d72a3`（接在 ORD-0201 之后；按"不需要外网"排序，先做前四条）

| # | nodeid | 缺口 | 你的落点（C 给的实测行号） |
|---|---|---|---|
| 1 | `provider_truth::g11` | 6 种形状塌成 5 个码：5xx 与"结构非法"同落 `PROVIDER_BAD_RESPONSE` | `provider_identity.py` 给 5xx 一个自己的码 |
| 2 | `matrix_truth::g13d` | 嵌套形状带 `radius_m`、顶层形状丢距离 | `valhalla_http.py:187` 顶层分支同样带上 |
| 3 | `discovery_truth::g16b` | 写了 `expires_at` 没人读 ⇒ 同一天第二次外呼（242.9 s 冷／238.3 s 热的机制） | `real_city.py` 命中前先判活 |
| 4 | `discovery_truth::g17a` | 调用方要 12 km，查询被静默缩成 `around:5000` | `real_city.py:737` 要么分圈要么具名回答"只覆盖 5 km" |
| 5 | `discovery_truth::g18b` | 6 类目里 `booking/mobility/nightlife` 落默认集合（与 g18a 同根另一格） | `real_city.py` 类目分支表：逐类目给 tag 或给 MISSING |
| 6 | `matrix_truth::g14b` | 20 节点一次性发出去（>100 cells 风险） | `runtime.py:232` 分片；B/C 边界由你在下一次落账时点明 |
| 7 | `provider_truth::g10` | 规范化目录里"可查坐标"这一格根本没有承载字段 | `real_city.py` 给 node 类补中心点（`out center` 语义）并放进投影 |

**不要**顺手改 `real_city.py:1279` 的 `"NOT_ANSWERED"`——那是 provider 证据轴的取值、不是能力格，我核过并且已写死不许动（理由见上一块）。
每修一条就在自己的一次性副本上跑对应 nodeid，交付只写：改前红／改后绿／collected／动过的文件行号。
