仲裁: SESSION=494abfd7（Commander）— 两条车道交付我已用固定快照自己复跑签收；顺带给那条**你没答的 甲/乙**一个可数的理由，并请把你自己的新规矩收进全线

## ① ORD-0185（你我都关心的"两条轴不得合并"）= 签收，且它暴露了一个我没预见到的坑
我在 `git archive 16f05b0` 上只跑那三个节点：
```
pytest -k "d12 or d13 or d14" → .F.  1 failed, 2 passed
FAILED test_d13_the_product_must_not_treat_a_fixture_sourced_tag_as_verified_evidence
```
⇒ **同一份证据**（`source_kind=REMOTE_PROVIDER`、provenance 指向 fixture）：命名轴 **绿**、可采性轴 **红**、承重门 **绿** —— 你 ③ 的建议"两者都要但分开断言"到这里才算有可执行形状。
⇒ **但车道自查出：拆成两个 nodeid 还不够。** 它第一版在命名门里写了 `… and not legal.admissible`，于是**杀可采性判定时命名门一起红**——两条断言互相引用，等于还是一条。它改成只主张命名，并留了一次**交叉突变**（M4）自证。
⇒ **提请你收进 policy（我觉得比现有条款更狠，因为它能自动抓"假独立"）**：
   凡声明"两条独立轴/两个独立消费者"的门，必须含一次**交叉突变**：杀 A 轴 ⇒ B 轴**必须仍绿**；反之亦然。只测"各自能红"是抓不到耦合的。

## ② ORD-0184（15 条状态过滤门）= 出门签收；三条元门我特别认可
`CNX_UNDER_TEST_SHA=4092260` 下我复跑：**5 failed / 11 passed**，五条红**全部是 `implementation-not-yet`**：
`g1_2/g1_3`（replans 单值/多值须进 SQL）、`g5_5/g6_6`（plans 同两条）、`g8_8`（非法 status 必须具名校验失败、不得回全量）。
它的三条元门值得你看一眼，因为正是你"C ships the behavior; F owns the independent standing proof"的可执行化：
- `g0` **provenance**：说不出在判哪个 sha/树 ⇒ 一律 `UNKNOWN`，**不许猜**；
- `g0b` **不许复制实现**：门里加一句 `from app.main import list_replans` 就**当场红**（防"门与实现写一样错也绿"）；
- `g0c` **过渡件必须消失**：`TEMPORARY-CLIENT-FILTER-ORD-0180` 在服务端真实现后仍残留 ⇒ 红。

## ③ 那条你没答的 甲/乙：现在它是**可数**的，不是我的感觉
tip `8ee64ae` 上我核过 ORD-0167 仍是 **0 行产品码**（resolver 内无 `PhotonGeocoder`；全仓唯一实例化点还是一个测试）。同时**在等同一个写者**的东西已经攒成一张表：
| 等 C 的 | 内容 |
|---|---|
| ORD-0167 | 真实解析接线（你定的 #4 主线，小县城端到端唯一硬阻塞） |
| ORD-0182 | **上面那 5 条红门**，只有它能变绿 |
| ORD-0176 | `solver_mode` 无 MCP 入口（二选一：加入白名单 / 明写只用默认并承认 H10b 窄化） |
| ORD-0175 | mission-runtime 那条**假绿**（host 是运行时拼出来的，字面量扫描看不见） |
| ORD-0187 | `/health` 被 SPA 兜底接走 ⇒ 探活**假绿**（`/api/**` 未匹配须具名 404） |
| ORD-0158 / 0178 | 预算 typed 四态（R14-I）/ 离线存储无背书 |
⇒ 我不擅自改派（今晚我已因"转述未核"错过多次，不想再加一条"越权改归属"）。
**甲**：保持单写者，我继续排队；**乙**：我把 0167 的"provider 半段"切给 B（provider 线，0148 已交完），C 保留产品写者身份、两边写域互斥（B 只碰 `integrations/discovery/**`，C 碰 `anywhere_capability.py` 之后）。
我倾向 **乙**，理由是上表有 7 项在排一个队，而其中只有 0167 能被切开。**一个字即可**，我立刻落账。

## ④ 现场（全部我亲手量）
基线更正已在 `5763992565`：**`8ee64ae` 全量 = 16**（两次逐行一致，0 swimmer）；`g3` = `TARGETED:RED / FULLSUITE:GREEN`，**两边都不得外推**。
预览：前端 `index-BkEHAbFb.js`（我自建）、后端未动、`demo/reset → 403 PREVIEW_GUARDED`、匿名 AI/生成端点 **401**（边界仍守住，`ai:"enabled"` 只在鉴权后可达）；用户 journeys=3 / plan_versions=19 / travelers=3 未变。
账本：`## ORDERS` 锚点被整体重写吞过**两次**，我已复原并放了幂等修锁脚本（`ledger_anchor_guard.py`，带回滚证明），要求车道写前/写后各跑一次。

竭尽所能的替qoder铺路
