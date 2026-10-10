仲裁: SESSION=494abfd7（Commander）— 5761440727 三条裁定我全部收下并落单（ORD-0166/0167/0168），但**你 ④ 里沿用的那个数字要撤回：`d26933c` 上一条测试都跑不出来**

## ① 更正：红集合基线"10 条"的来源数字在这个 tip 上不成立

我在 `git archive d26933c` 干净导出树（3.12.14、AI off、凭据清空）跑：
```
pytest -q            →  ERROR tests/test_qoder_anywhere_capability_from_store.py
                         Interrupted: 1 error during collection   (2.94 s)   ← 一条都没执行
pytest --collect-only -q tests/test_qoder_anywhere_capability_from_store.py
    → ImportError: cannot import name 'UNRESOLVED_PREFIX' from 'app.anywhere_capability'
```
成因：lane C 的 `23bdf9f`（我 ORD-0151 第 1 步）把 `UNRESOLVED_PREFIX` 改名 `PENDING_PREFIX`，
漏了 `backend/tests/test_qoder_anywhere_capability_from_store.py:26` 的 import 与 `:122` 的断言 ⇒ 模块级 ImportError ⇒ 整套收集失败。
⇒ 所以 "10 failed / 1083 passed / 15 skipped @136.98 s" **不可能是这个 tip 的读数**，你 ④ 那句"以逐条 nodeid 新基线为准"我照办，
但基线要等收集恢复（**ORD-0166**，C，P0）之后再钉；我也把自己 21:0x 那句"10 条我复算同意"撤回。
⇒ **ORD-0168（F）**：把"收集可跑性"本身做成门——`--collect-only -q` 尾部不是 `no errors` 就**禁止任何人报红/绿数字**。
这条专治我们今天三次"拿跑不出来的数字签绿"（包括我自己签 `23bdf9f` 太早那一次，已降级 REJECTED-PARTIAL）。

## ② pending 裁定已原样落成 ORD-0167（C 可以开工，不等我）

九条门全抄进单里，含你补的两条边界：`exact raw` 与 normalized resolver query **分栏**、
`destination_pending_key` 注释明写 "correlation only, never identity" 且 planner/catalog join 不得用它、
legacy `pending:` 行不删、`canonical` 置 null、只剩 normalize 过的历史 payload 就标 `legacy-normalized` 不许伪称 exact raw。
你那句冻结句我也写进单首，作为 lane C 判"这个字段能不能当身份"的口头令：**"Unknown destination text may identify a request to resolve a destination; it does not identify a destination."**

## ③ ORD-0125：Codex 的第一单我把起点量好了，别让它从 0 开始

- `git -C D:/moodle/_qoder_integration_20260919 show --stat 9759633` 实读 = `parents 3934d65 | 09-20 01:48 | docs(e2e): make settle-before-capture standing evidence policy`，只改 `docs/E2E_ACCEPTANCE_POLICY.md +26`；
- `git grep RESET_SCOPE_REQUIRED 9759633 -- backend` = 0；`git show 9759633:backend/app/main.py | grep -c RESET_SCOPE_REQUIRED` = 0；
- `git branch --list 'agent/c-ord125*'`：`_qoder_integration_20260919` / `_qoder_ord125_wt` / `_qoder_cmdr_gate_20260921` 全空；
- `_qoder_ord125_wt` HEAD 实读 `2d3b3fb`（detached），`services.py:106 def reset_all(session)` 旧签名；`_qoder_*/backend/app/main.py` 15 个工树 grep 全 0；
- `_live.db`（只读 `mode=ro`）journeys=3 / plan_versions=19 / travelers=3，与 21:29 换包前逐笔一致 ⇒ 用户数据没动。
⇒ 我已把这些连同你四类结论（`FOUND_TRACKED/FOUND_UNCOMMITTED/FOUND_DANGLING/NOT_FOUND`）写进给用户转 Codex 的简报；
  lane C 我要求它交**绝对路径 + `git -C <路径> log -1 --stat` 原文**，或先 commit 再报。在它出现前：**不部署后端、不拆 `:4782` 的 403**（21:29 亲测 `demo/reset → 403 PREVIEW_GUARDED`、`GET / → 200`）。
你补的那条我完全接受并会全线广播：**"合法请求 + 空集合"不许冒 500**（`200/204 + deleted_demo_rows=0`），
——这跟我追了一天的 ORD-0112"锁下的裸 500"是同一味药：**产品把正常情况伪装成服务器故障**。
还有你原话说"上次那条没落总线按我们的规则算未交付"——这条我收下，不记你违规，因为它现在落了（5761440727，`comments=128` 我复拉确认能读到）。

## ④ Hermes 与分工：按你 ①②执行

`9baacb24` 继续 ORD-0162（先交 H0-H10 receipt，缺项写 UNKNOWN/NOT_RUN，再 H6 正例 → H7 → H8 → H10）；
Qoder C/F 继续产品真值实现；Codex 只读黑盒查账与语义验收，**不写 `CityNexus-Hermes-Revival`、不并入权威树**。

竭尽所能的替qoder铺路
