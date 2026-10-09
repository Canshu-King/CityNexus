### SESSION=494abfd7 · **ORD-0167 第一片我已复跑通过：`g19a/g19b/g19c` 三条红门当场退掉**（今晚第一次真的减少红集合，不是顺序漂移）@01:2x

`STATUS: FIRST-PRODUCT-REDUCTION-VERIFIED-BY-ME | 树 `git archive f2708dd` → `v_f2708dd`（权威树 0 写）| 3.12.14、AI off、凭据清空 | 全 targeted（P5）|`

**我量的**
```
--collect-only -q                         → 1116 tests collected（8ee64ae 上是 1101 ⇒ 新增 15 条测试）
tests/test_qoder_anywhere_capability_from_store.py
  + tests/test_qoder_pending_destination_identity.py → **19 passed / 0 failed**（1.78 s）
```
⇒ **`g19a_a / g19b_b / g19c_c` 三条从红转绿**——它们此前**稳定占据交集 14 里的 3 格**（`capability_from_store` 3 条全部来自这一族）。
⇒ 所以共享基线预期变为 **11**（14 − 3），**但我现在不改发布值**：按 P5，基线数字只在"夜间集成稳定候选"上用一次全量重算，targeted 只证明"这三条退了"。
⇒ 这次与今晚两次"红变少"的性质差别要说清：**那两次是同一 SHA 上成员轮换（假象）**；这次是**我在新 commit 上定向跑到 0 失败**、且这三条本来就在交集里 ⇒ 是真减少。

**C 这次交付的形状（我读 diff 核过的部分）**
- 新增 `pending_destination_label` 列（`db/models.py` + `db/schema.sql`）+ `db/session.py` 里 **150 行就地回填**（对齐 R10"legacy 行不删不重建"）；
- `anywhere_capability.py:134` 起 `DESTINATION_STATES = ("RESOLVED","AMBIGUOUS","NO_MATCH","RUNTIME_FAILURE")`，且 `:381/:410` 明写 **RUNTIME_FAILURE = 可读源失败、retryable、不是结构性缺失** ⇒ 与 B 的 typed outcome 语义接上（B `provider_identity.py` 四类同名）；
- 新增 775 行测试 + `review/mutate_ord167.py`（180 行突变驱动）⇒ 有 kill 面，不是只加断言；
- 契约 `openapi-anywhere-draft.yaml` +52。

**仍然欠的（所以 ORD-0191 没签）**：你 10 项必证我要逐条对上（尤其 ④"已落库 pending 行不删"、⑥"AMBIGUOUS 不静默选一个"、⑨"pending/raw 永不当 planner/catalog join 真值"、⑩重放幂等）；
以及 **B→C 是不是真用 `ProviderResolution`**（我 grep 到 `resolution.pending_destination_label`，但没确认 provider 通路是接 B 的 `PhotonIdentityProvider` 还是旧路径）——**这条决定贡山端到端能不能开跑**。

status: ORD-0167 第一片 REPRODUCED（19/19 targeted，三条红门退掉）；基线暂不改发布值（待稳定候选一次全量）；ORD-0191 未签，欠 10 项对表与"是否真接 B 通路"一条
evidence: `v_f2708dd` 上两条 pytest 原样输出 · `anywhere_capability.py:134/167/184/241/269/311/381/410` 行号 · `models.py/schema.sql/session.py/mutate_ord167.py` diff 规模
