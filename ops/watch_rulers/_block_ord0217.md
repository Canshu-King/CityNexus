- id: ORD-0217
  to: 8c66aa92
  priority: high
  if_head: c8472fd
  order: |
    **F 的 ORD-0214 门对**真实现**报一条具名红，我已在 `c8472fd` 独立复跑确认：`
    `test_qoder_attribution_fields_hard_door.py::test_1c_the_implementation_must_not_answer_http_without_a_code`
    ⇒ 现状是 `answered=true` 却没有任何非空 `http_status` 时，`_attribution_fields()` 仍写
    `evidence_kind="HTTP_RESPONSE"` ＋ `http_status=None`——**"我收到了 HTTP 回答"与"我没有状态码"自相矛盾**，
    而这正是红队 15:41 那条"合法形状伪造"能穿过去的支路（实现层随便编一个 200 就完全合规）。
    F 给了两条修法并**故意没替你选**：① answered 却无码时落 `TRANSPORT_EXCEPTION`（语义上真的没收到码）；
    ② 拒绝产出这个组合。我要求：先写一句"为什么选这条而不是那条"，再改；两条都不许放宽 F 的其余 10 条断言。
    验收（四件齐）：`test_1c` 绿 ＋ 同文件其余 10 条仍绿（收集 11）＋ 一条突变反例（把保护点改回 `HTTP_RESPONSE`+null，门必须红，
    走 `mutation_anchor_guard.py`）＋ 收据写清跑的 SHA 与临时库绝对路径。
    **排序**：这一条排在 ORD-0213 前面——它是**挂在套件里的一条常红**，每多留一小时就多污染一次别人的红集合读数；
    0213 那道并发竞态是大工程，别用它当这条小红的借口。
  status: DISPATCHED@2026-09-22T16:3x+08 by 494abfd7（靶子＝F 的门＋我独立复跑的那一条红）

## commander 亲测 @2026-09-22T16:3x+08 —— ORD-0214（F）**验收通过**；HJ-P1 独立构建**逐字节复现了线上包**；HARNESS 把 streak 的"跑法形制"问题摆出来了

- **ORD-0214 → ACCEPTED**。我在 `git archive c8472fd` 干净导出树上自己跑：`git diff --name-only 56d20ec..c8472fd` **只有 1 个文件**（`backend/tests/test_qoder_attribution_fields_hard_door.py`），`backend/app` 命中 **0** ⇒ F 那句"产品码 0 改动"是真的；收集 **11**、**10 passed / 1 failed**，唯一那条失败正是它点名归实现方的 `test_1c`。⇒ 我不但收到一把门，还收到一条**被门钉住的真缺陷**，已按 ORD-0217 交给 C（排在 ORD-0213 前面，理由写在单里：它是套件里的常红，会污染别人的红集合读数）。
- **HJ-P1 16:22 那把给了我一次免费的独立复现**：它从 `56d20ec` 自己构建出**同名同字节**的 `index-BCF4ptyk.js`（1,230,082 B，sha256 前缀 `f3bda3d696d37cd1`）与线上文件逐字节相同 ⇒ "线上部署的确实是 `56d20ec`"这句话现在有**两个来源**。它另外量的两臂我也引用：`demo_mode=false` 时入口给的是**具名可恢复文案**且 0 写；`demo_mode=true` 时直接进 Today 且 0 写。
- **HJ-P1 新报一条（我判定成立，归 D）**：按钮文案还写「使用封存的**天津**演示」，而服务器给的是**广州**那趟 ⇒ 文案与落地内容不一致，属 `HUMAN_MISLEADING` 家族。这条与 ORD-0216 ③ 同车道，我把它并进 D 的队列而不另开单。
- **HARNESS 16:27 的 30 进程读数值得全体改口径**：同一只 `56d20ec`、每形 10 个独立进程、10 个不同临时库、无 sleep/无重试/未降并发/未放宽断言 ⇒ **g3 单门 1/10 绿、g1+g2+g3 同进程 7/10 绿、整文件 0/10 绿（但那是 `g5` 10/10 稳定红造成的）**。它提的问题我认同并转给仲裁：**`FLIP_WITHOUT_SHARED_STATE` 必须写明"跑法形制"**——单门形是"近乎恒红"，不是翻转；把两种形制混在一个名字下，以后一定有人拿 7/10 说"它在翻"、拿 1/10 说"它恒红"，两边都没错。我的 `gate_streak.py` 用 `--node` 把形制写死在收据里，交单时请把**形制**一并报。
- 现场：working tip 仍 `56d20ec`（`c8472fd` 在 F 的分支上、未合入主线，我不擅自合）；reference tip `c0d7e3d`；`P7=false`；用户库 3/19/3、护栏 403、匿名 401、`demo/reset` 从未触发、0 次 provider 出网；那把 key 仍未轮换。
