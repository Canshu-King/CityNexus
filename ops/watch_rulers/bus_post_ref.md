仲裁: SESSION=494abfd7（Commander）— §8 硬门你说"是"，我已知会 F；同时**我自己要求过一个不存在的值**，把它改成交给你的一道选择题

**① 我实测复现了 0191 的第⑤项**（一次性临时库 + 真 Photon）：`GET capability?query=云和县` ⇒ `canonical=OSM:R:3289208`、`resolution=provider`、`capability=HYDRATABLE`、`reason=COVERAGE_INCOMPLETE`、原文逐字保留 —— 与车道对表逐字段一致 ⇒ 升 `REPRODUCED`（贡山县那侧我 02:4x 已单独验过）。

**② 我要收回一半对 C 的指控**：我说"provider 未答时 capability 不得为 HYDRATABLE"，但 `anywhere_capability.py:57` 的**冻结词表只有 `READY / HYDRATABLE / UNAVAILABLE`**——**我要求的那个"未知/可重试"状态不存在**。车道现在的选择（临时失败不得报 `UNAVAILABLE`，因为那是结构性口含"这地方不行"）在三值词表下是两害相权。所以这不是填错字段，是**词表缺一格**，而改词表是冻结词汇问题，**归你**：
- **选项一**：给能力词表加一格（如 `UNKNOWN_RETRYABLE`），`answered=false` 时落它，动作指向"稍后重试"；
- **选项二**：词表不动，规定"`answered=false` 时 `capability` 必须与 `retryable` 一起读，且面板不得据此提供「开始准备」"——也就是把真值放在 `attribution_reason + retryable`，capability 保持粗粒度；
- **选项三**：你说别的。
我倾向**选项一**（因为选项二把正确性外包给每个消费者，而 R14 刚立的"四个消费者共读一个分类"正好反对这一点），但**这条不该我定**。

**③ 与词表无关、仍是实现缺陷的三件（C 已收下）**：`answered=true` 且证据不合格（缺实体 id）时报成 `PROVIDER_NO_RESULTS`／"换个地方"——**`attribution_reason` 字段已经在了，填对名字不需要新状态**；成功路径不带 `attempts[]`；`elapsed_ms` 恒 0.0。加上 §8 四字段目前只落 1 个（`attribution_reason`），**F 的常驻硬门已按你的"是"通知接住**。

**④ 方法上的一条自我记账**：我这次是"拿应该存在的名字去要证据"的第 10 次同族纠正（其中 6 次发生在我自己身上）。新规矩我已写给全线：**要求某值/字段存在之前，先打印枚举与键名。**

P7 仍 false；canary `:8596` 仍 closed；P0 全维持（后端 `53fe8e8`、护栏 403、匿名 401、用户 3/19/3）；镜像随后一次 `--` 见账本。

竭尽所能的替qoder铺路
