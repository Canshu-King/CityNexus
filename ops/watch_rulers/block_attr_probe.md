### SESSION=494abfd7 · `16cc652` 我自己复测了：**具名原因确实到账了**（两种失败给出不同名字），但 R14 §8 的四字段只落了 1 个，且**"未答却 HYDRATABLE"没修** @02:5x

`STATUS: PARTIAL-FIX-VERIFIED-BY-ME | 树 `git archive 16cc652` → `v_16cc652/backend`，venv 3.12.14，一次性临时库，正常入口；两个反例：假 provider（200+合法 GeoJSON+**无可用实体 id**）与不可达 provider（拒接）|`

| 场景 | `reason_code`（冻结类） | **新增** `attribution_reason`（具名原因） | `capability` |
|---|---|---|---|
| provider 答了但证据不合格 | `NO_CANONICAL_IDENTITY` | **`PROVIDER_NO_RESULTS`** | UNAVAILABLE |
| provider 根本没答（拒接） | `DESTINATION_RESOLVER_UNAVAILABLE` | **`PROVIDER_UNREACHABLE`** | **`HYDRATABLE`** ← 缺陷未修 |

**已改善（我确认）**：响应里多了一个**放具名原因的字段**，两种失败给出**不同**名字 ⇒ 以前那种"全塞进一个冻结类"的局面打开了口子；`destination_resolution` 也仍区分 `provider_no_match` / `provider_error`。

**四处仍未成立（逐条给证据，不夸大）**
1. **未答时 `capability=HYDRATABLE`**：`answered=false`、`provider_replied=false`，身份没定，却告诉用户"可以开始准备" ⇒ 面板会邀请准备一个没定位的地点。**未修**。
2. **malformed 仍被叫成 `PROVIDER_NO_RESULTS`**：上游**答了**（200 + 一个 feature），只是**没有可用实体 id** ⇒ 语义上是"证据畸形/契约违约"，不是"没结果"。名字现在有地方放了，但**放的还是错的那个**。
3. **R14 §8 的四个字段只落了 1 个**：响应里我只看到 `attribution_reason`（我把出现的键名打出来才敢说这句）——
   `attribution_evidence_kind / attribution_http_status / attribution_source_layer` **均不存在** ⇒ 仲裁那句"屏幕、播报、telemetry、恢复动作共读一个分类"目前只有半个分类可共读。
4. **`elapsed_ms` 依旧 0.0**（拒接与真超时都是 0），成功路径也仍不带 `attempts[]`。

**P7 仍 false**（`p7_check.py` 的必填字段现在连 `evidence_kind` 都取不到）。我把这四项并成一句给 C：**"字段有名字了 ≠ 字段填对了"**；晨报第 13 项按上表写"部分改善 + 四项未成立"。

status: 16cc652 我复测——具名原因字段落地且两种失败不同名（改善）；但未答仍报 HYDRATABLE、malformed 仍名 PROVIDER_NO_RESULTS、R14 §8 四字段只存 1、elapsed/attempts 未修；P7 仍 false
