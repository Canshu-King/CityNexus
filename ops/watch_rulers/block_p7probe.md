### SESSION=494abfd7 · C 交了 P7 候选（`db4a91c`），我做了**行为探针**（不是 grep）：三项当场过、一项**从响应里根本看不见** ⇒ 已问清证据落在哪 @02:3x

`STATUS: BEHAVIORAL-PROBE-PARTIAL | 树 `git archive db4a91c` → `v_db4a91c`；解释器 venv **3.12.14**（我第一次误用系统 3.10 → `StrEnum` ImportError，是我的错，已换回）；一次性临时库 `DATABASE_URL=sqlite:///…/probe.db`，AI off、provider 凭据清空；经**正常入口** `GET /api/v1/destinations/capability` |`

**① 先报无破损**：`--collect-only` = **1151 collected / rc=0**；四套定向跑 = **54 passed / 0 failed**。

**② 行为探针原样读数（两座未预录县）**
```
贡山县 → 200  canonical=null  resolution=unresolved  capability=UNAVAILABLE
              reason=NO_CANONICAL_IDENTITY  action=CHOOSE_ANOTHER_DESTINATION
              pending_destination_label="贡山县"（原文逐字保留）
云和县 → 同上
两次的响应键中**没有任何包含 "attempt" 的字段**（我把键名列出来才敢说这句，不是"没搜到"）
```
**当场通过的行为条件**：
- 不再造 `unresolved:<hash>`（对比我 02:2x 在部署侧实测到的 `unresolved:8fccf2bbf123e3df`）⇒ **hash 冒充身份在这条路径上消失** `REPRODUCED`
- `canonical=null` + **原文逐字保留** + 推荐动作与状态自洽 ⇒ 条件 3/5/7 的行为面成立 `REPRODUCED`

**③ 我看不清的那一项（所以不签 P7）**：**响应里看不到"问过没有/问了几次"**。代码里确实存在与 `NO_CANONICAL_IDENTITY` **不同**的 `REASON_RESOLVER_UNAVAILABLE`（`anywhere_capability.py:629/665/744`），而我这次拿到的是前者 ⇒ 无法从响应区分"问过且为空"与"配置没让问"。
⇒ **已问 C**：`ProviderAttempt[]` 落在哪（响应字段？operation/audit 行？给我 `表.列` + 那次 run 的关联键）。这正好是仲裁那句 **final outcome ≠ audit history** 的落地点：审计可以不在响应里，但**必须在**某个可复放的地方，且我的收据检查器要求它出现。
⇒ 因此 **P7 仍 false**：MATCH/AMBIGUOUS/RUNTIME_FAILURE 三类我这次都没能从行为上触发（需要 provider 真被问一次，或 C 给可按的 fixture 收据）。

**④ 顺序**：C 请补两样——(a) 一次 **LIVE_REQUEST/REPLAY** 的 MATCH 与 RUNTIME_FAILURE 收据（同一 SHA、正常入口）；(b) attempt 历史的存放位置。给了我就跑 `p7_check.py`，全绿才走五步唤醒。

status: P7 候选 db4a91c 行为探针：无破损(1151/54✓)、hash 冒充已消失✓、canonical=null+原文保留✓；但 attempt 历史在响应中不可见 ⇒ 无法区分"问过为空"与"未问"，P7 继续 false，已索要 attempt 存放位置与 MATCH/RUNTIME 行为收据
