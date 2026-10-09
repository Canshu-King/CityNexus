### SESSION=494abfd7 · 我自己造了"provider 答了但不给身份"的反例 ⇒ **抓到第二条归因错误**：它被报成 `PROVIDER_NO_RESULTS`（"没找到"），而真相是"拿到了却不能用作身份" @02:4x

`STATUS: MALFORMED-RECEIPT-NEGATIVE-RESULT | 树 `v_db4a91c/backend`，venv 3.12.14，一次性临时库；我在 `127.0.0.1:8731` 起了一个假 provider：**HTTP 200 + 合法 GeoJSON + 一个看起来正常的县 feature，但没有任何可用实体 id**；脚本留在 `v_db4a91c/backend/_cmdr_probe_malformed.py`（车道可直接复放）|`

**产品实际返回（原样）**
```
canonical_destination_id = null                      ← 好：没有 hash 凑身份（这条守住了）
destination_resolution   = provider_no_match
reason_code              = NO_CANONICAL_IDENTITY
recommended_action       = CHOOSE_ANOTHER_DESTINATION
provider_status = [{status:"OK", answered:true, provider_replied:true,
                    reason:"PROVIDER_NO_RESULTS", attempts:[{http_status:200, elapsed_ms:0.0}]}]
pending_destination_label = "贡山县"（原文保留）
```
**两点对错**
1. ✅ **没有伪造身份**：宁可 `canonical=null` 也没 hash 一个 ⇒ 我原来担心的"凑一个身份"没有发生。
2. ❌ **归因错位（这是新缺陷）**：provider **确实答了**（`answered=true`、200、有 feature），只是那份证据**不合格**（无实体 id）。系统却报 `PROVIDER_NO_RESULTS`（"这座城不存在"的味道）并让用户"换个写法/另选一个地方"。
   ⇒ 真实类别是 **畸形/不可用的 provider 证据（契约违约）**，不是**结构性无身份**。用户被告知"你输入的地方没结果"，而事实是"我们的上游给了个我们没法用的东西"。
   ⇒ 这正是 R14 要禁的那一步：**把采集/契约失败写成结构性缺失**——方向与我 02:4x 抓到的 `HYDRATABLE-while-unanswered` 相反，但同源。
   ⇒ 最小修法：`answered=true` 且候选非空却缺 `source_entity_id`/合法几何 ⇒ 具名 `PROVIDER_EVIDENCE_MALFORMED`（或等价），动作不得是"换个地方"，应是可重试/等待上游；配门：同一反例断言 `reason_code != NO_CANONICAL_IDENTITY`。
3. 附带：`elapsed_ms=0.0` 第三次出现 ⇒ 计时确实没接。

**P7 判定更新（诚实）**：条件"缺 source id 时不得 hash 身份"**PASS**；但"必须具名 malformed"**FAIL**（被并入 NO_MATCH 类）。
⇒ **P7 仍 false**。C 现在要修三件 + 交一件：
   ① `HYDRATABLE` 不得出现在 provider 未答时；② 上述 malformed 归因；③ 成功路径补 `attempts[]` + `elapsed_ms` 接上；④ 同键重放幂等收据。

status: 我用假 provider 反例复现"答了但无身份"⇒ 产品未伪造身份(PASS)但把它报成 PROVIDER_NO_RESULTS(FAIL，归因错位)；elapsed_ms 三次为 0；P7 仍 false，C 待修三件交一件
