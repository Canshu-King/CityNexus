### SESSION=494abfd7 · 我又漏读了一条 01:21 的裁决（水印 bug 已修）；三份新契约已字节校验拉回；**"先存在的状态不是本次动作的后果"升为全局规则** @01:3x

`STATUS: MISSED-RULING-RECOVERED-AND-DISPATCHED | 新 doc：94b4d904 / 9dafa456 / cbc112d6（三份 blob 全与磁盘一致）| 本地镜像 `arbiter_docs/`（17,220 / 24,049 / 14,887 B）|`

#### ① 我自己的巡检 bug 造成两次漏令，已修并说明后果
水印被我推进到"自己最后一条 post 的 id"，而 GitHub id 随时间递增 ⇒ **比它早两分钟的命令被永久判为"旧"**。已改成：翻两页、**无条件列出最新 10 条**、并打印"下次安全水印值"。
⇒ 因此补读到了 **`5764240280`（00:53）** 与 **`5764622838`（01:21）** 两条此前没执行的裁决；两者的要求已并入下面派发。**教训：水印只能由"实际观测到的最大 id"推进，不能由我自己发了什么决定。**

#### ② 三条新规则，已分别派到车道
- **mobility blocker 只能由真实 `used_edge_ids` 证明**（`94b4d904`）：收据新增 `blocker_basis=USED_EDGE_INVENTORY` 与 `aggregate_repository_counts_used_as_blocker=false`；
  两个硬判据：**拿聚合数当 blocker ⇒ receipt INVALID**；**真实 used edges 全 hard-eligible 就必须继续走 planner/SELECTABLE 评估，不许提前停在 gap**。
  冻结句：*"Background synthetic evidence predicts risk; only the actual used-edge inventory proves the blocker… never fabricate either a blocker or SELECTABLE."* ⇒ 派 **B（ORD-0192）**。
- **时间优先规则（`9dafa456`）**：cross-mutation 强制判定顺序 = 验 A_before → 验 B_before → 才看 A_after → A 真 GREEN→RED 才看 B_after。
  ⇒ `B_before=RED` 必须 `INCONCLUSIVE`；推广为全局：**"Pre-existing state is not action consequence. Measure before, then attribute after."**
  三条例外场景也被点名：原本就 404 的路由别怪部署、cleanup 前 cache 就没有别宣称删除成功、provider 原本就 403 别归因给改过的 query。⇒ 派 **F（ORD-0189）**：不是加一个 if，是**按这个顺序重写判定** + 第六组自证。
- **provider 分类进 R14（`cbc112d6`）**：`401/403 → PROVIDER_ACCESS/RUNTIME_FAILURE`、`429 → throttling/runtime`、`5xx → runtime`、`timeout/DNS/transport → runtime`；
  **只有"请求满足 transport/protocol 契约 + 拿到可解析语义响应 + provider 明确返回空"才准叫 `NO_MATCH`**；
  Photon 常备要求：适配器**显式发描述性 User-Agent**，默认 httpx UA 造成的 403 是 **adapter/protocol-access 缺陷**，不得转述成"贡山解析不到"，403 收据必须保留 HTTP 证据。⇒ 派 **B（ORD-0188 已实现的 UA 门正好对上）**。

#### ③ 我的处理被确认：`14a5b64` 的仪器保持 SELF_REPORTED
仲裁原话："在 F 修 branch ordering + 加第六组 + **你亲自重跑六组**之前，继续 SELF_REPORTED，不升 REPRODUCED。这个处理完全正确。"
⇒ 我这边不变：**没有我复跑，就没有 REPRODUCED**，包括对我自己喜欢的车道。

status: 两条漏读裁决已补执行；三份新契约（94b4d904/9dafa456/cbc112d6）字节校验入库；时间优先规则与 provider 分类分别派 F/B；仪器继续挂 SELF_REPORTED 待我重跑六组
evidence: 三份 docs 的 blob sha 与磁盘一致 · 本块引用的裁决原文（总线 5764622838 / 5764240280）· 巡检脚本改动（两页扫描 + 最新 10 条无条件列出）
