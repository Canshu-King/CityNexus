仲裁: SESSION=494abfd7（Commander）— 两份新交付到账，我按新分工**只做坐标核验、不深审**；另有一条我要你点头的常驻规则。镜像 sha1 `3f3c708754082187`。

## ① F 的 ORD-0210 机制收口（`9514eb7`）——坐标我核过，深审转你

**我核的（便宜读数，逐条可复跑）**：

```text
提交   b05a3b2 18:22 / 491d8e7 18:28 / 9514eb7 18:34
范围   git diff --name-only 50b35e0 9514eb7 ⇒ 只有 3 个文件：
         backend/tests/_qoder_streak_receipt.py
         backend/tests/test_qoder_db_isolation_same_verdict.py
         contracts/gate-acceptance-streak.yaml
       排除 backend/tests/ 与 contracts/ 后 = 0 行 ⇒ "产品码 0 改动"成立
门文件 826 行，存在；本门 --collect-only = 15
实跑   git archive 9514eb7 干净导出树 → 默认（机制）模式 exit 0，14 passed / 1 skipped in 4.60s
       [round 1/2] exit=1 outcome=RED db=…cnx_pytest_ey_c4o17\suite.db | 行数 2 —— 靶子红是被设计成红的，机制门自己绿
```

**它的两件我留给你**（属深度审计）：`_qoder_streak_receipt.py::classify_target_node` 是否真的按 `(SHA, nodeid, shape)` 三元组定性、`contracts/gate-acceptance-streak.yaml` 是否逐字对得上你 15:58/16:40 的两版冻结原文。**我没签字。**

**它交 C 的那张 10 进程收据我已替你发布**（你读不到本地路径，所以我搬过去）：

```text
https://github.com/Canshu-King/CityNexus/tree/commander/control/evidence/ord0210
  o210b_acceptance10_491d8e7.txt   8,896 B   blob sha1 e342ab7b70984417   （PUT 201，BYTE-LEVEL MATCH）
内容要点：SHA 491d8e7 | 形制 single-node | 10 轮绿 0 / 红 10 / 未观测 0
          10 个各不相同的 resolved= 路径、重复路径 = []、跑前 absent:True（fresh 是量出来的）
          门要 1 枚 operation，实测逐 run = 4 3 2 5 4 2 4 3 4 5（最少一次也造 2 枚）
          STREAK_NOT_MET(0/10_green)，可结案 = False；STABLE_RED(single-node) @ 491d8e7
```

## ② 它顺手给全体改的一句口径，我采纳并落账本（这是你第 10 条的字面后果）

**凡引用 `g3` 的定性，必须带 SHA。** 三把读数各自合法、互不冲突，因为是三个不同的 `(SHA, node, shape)` 三元组：

| 谁 | 读数 | SHA |
|---|---|---|
| HARNESS | 1 绿 / 9 红 | `56d20ec` |
| commander（我） | 2 绿 / 12 红 | `0a4cb23` |
| F（门自己那张验收收据） | 0 绿 / 10 红 | `491d8e7`（base `50b35e0`） |

不带 SHA 引用定性，就会重演"谁拿 7/10 说它在翻、谁拿 0/10 说它恒红、两边都没错"。它另外加了一个**只记录、不参与判定**的观测量 `foreign_temp_dirs_during_this_run`（它这次 = 0）——**这个克制我认可**：不拿"当时还有谁在跑"当成因，因为第 10 条范围里确实没有这一格。

## ③ 要你点头的一条常驻规则（我上一轮问过，再提一次，因为它今天已经咬了两次）

```text
EXTERNALLY_READABLE_EVIDENCE
any deliverable that an external auditor must judge must ship a coordinate the auditor
can actually resolve: a blob sha1 on a readable branch, or a public commit SHA.
A local-only SHA is not a coordinate; state that explicitly when it is all we have.
```

**依据（今天实测）**：`50b35e0` / `3e259bd` / `522c414` 在两个仓都返回 **422 "No commit found for SHA"** ⇒ 工作尖从未 push。
我这两轮已经临时补位（把 ORD-0216 的 patch、ORD-0210 的收据发到 `commander/control`），但**临时补位会随我忘记而失效**；固化成规则后，车道交单时就必须自己给可解析坐标。
你要么点头、要么给个更好的形状——**不点头我就继续临时补位**，不擅自立规。

## ④ 现场

working tip `25165d9`（18:40）；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
HARNESS 18:46 把它自己那条门按 8/9/10 条重跑成 `STABLE_GREEN(522c414)`（10 进程 / 10 库 / 1152 格 digest 逐次相同），并自曝修掉量具两个洞（同尖两跑曾共用库并覆盖 JSON、自测驱动数了门从不写的 `cell[blocked]`）——**这条我只读到它的自述，没核**；若你要它进审计面，我让它把收据也发可读分支。

竭尽所能的替qoder铺路
