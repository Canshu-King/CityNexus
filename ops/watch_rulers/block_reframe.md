### SESSION=494abfd7 · 我自己验了 0191 的第⑤项（真 provider ⇒ `OSM:R:3289208` + HYDRATABLE）；并**更正我对"未答却 HYDRATABLE"的定性**：那是**词表只有三个状态**导致的被迫选择，不是代码写错 @02:5x

`STATUS: ITEM-5-VERIFIED + MY-DEFECT-CLAIM-REFRAMED | 树 `v_16cc652/backend`（venv 3.12.14、一次性临时库、`CITYNEXUS_ANYWHERE_RESOLVER=photon`）|`

**① 第⑤项我自己打了一遍（原样）**
```
GET /api/v1/destinations/capability?query=云和县
→ canonical=OSM:R:3289208   resolution=provider   capability=HYDRATABLE
  reason=COVERAGE_INCOMPLETE  retryable=false   pending_destination_label="云和县"
```
⇒ 与车道 0191 对表里第⑤项**逐字段一致** ⇒ 该项升 `REPRODUCED`（贡山县那侧我 02:4x 已单独验过）。
⇒ 顺带确认：**"provider 答了但没带可用身份"与"provider 答了且带身份"两条路径共存**（前者仍报 `PROVIDER_NO_RESULTS`，见 ②）。

**② 更正我自己：我要求的是一个不存在的值**
`anywhere_capability.py:57` 的**冻结能力词表只有三个值**：`("READY", "HYDRATABLE", "UNAVAILABLE")`。
⇒ 我之前写"未答时 capability 不得为 HYDRATABLE"，**隐含假设存在第四个（未知/可重试）状态——它不存在**。车道的做法（第⑧项：临时失败**不得**报 `UNAVAILABLE`，因为那是"结构性不可用"）在现有词表下是**两害相权**：`UNAVAILABLE` 会说谎"这地方不行"，`HYDRATABLE` 会说谎"现在就能准备"。
⇒ 所以这不是"填错字段"，而是**词表缺一格**——而改词表属于**冻结词汇**（R1 面），**不归我判、也不归车道判**。已把它作为选择题上交仲裁（见总线）。
⇒ **保留的部分仍然是缺陷**（与词表无关）：`answered=true` 且拿到 feature 但**无可用实体 id** 时报 `PROVIDER_NO_RESULTS`／`NO_CANONICAL_IDENTITY`——这是把**契约违约**说成**世界没有这个地方**，`attribution_reason` 字段已经存在，填对名字不需要新状态。
⇒ 还有一条不变：**成功路径不带 attempts、attempt `elapsed_ms=0.0`**、§8 四字段只落 1 个 —— 这三件是纯实现问题。

**③ 一句话给全线（我自己又用了一次"应该存在"的名字）**：要求某个值/字段存在之前，**先把枚举与键名打印出来**。这是我今夜第 10 次同族纠正——第 6 次发生在我自己身上。

status: 0191 第⑤项由我实测复现（云和县→OSM:R:3289208/HYDRATABLE）升 REPRODUCED；"未答报 HYDRATABLE"更正为**冻结词表缺格**上交仲裁（不再要求车道私改）；malformed 归因、attempts 缺失、elapsed=0、§8 三字段仍为实现问题待修
