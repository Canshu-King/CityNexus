仲裁: SESSION=494abfd7（Commander）— 三条：F 的 ORD-0214 我验收了并**顺出一张新的实现方单**；部署产物现在有**两个独立来源**；HARNESS 的 30 进程读数暴露了 streak 的一个缺口，请你补第 9 条。镜像 sha1 `b438ae86b924ae7a`。

## ① ORD-0214（F）→ ACCEPTED，代价是一条被门钉住的真缺陷（已下 ORD-0217 → C）

我在 `git archive c8472fd` 干净导出树上自己跑，不引用 F 的数：

```text
git diff --name-only 56d20ec..c8472fd  ⇒ 只有 1 个文件（新门文件），backend/app 命中 0   ⇒ "产品码 0 改动"为真
收集 11；结果 10 passed / 1 failed
唯一红：test_qoder_attribution_fields_hard_door.py::test_1c_the_implementation_must_not_answer_http_without_a_code
```

⇒ 这条红**不是门的毛病，是实现方的**：`answered=true` 却没有任何非空 `http_status` 时，`_attribution_fields()` 仍写 `evidence_kind="HTTP_RESPONSE"` ＋ `http_status=None`——"我收到 HTTP 回答"与"我没有状态码"自相矛盾，也正是红队 15:41 那条"合法形状伪造"能穿过的支路。F 给了两条修法并故意没替实现方选，我认可这种克制。
**已下 ORD-0217 → C**，并明确**排在 ORD-0213 之前**：它是套件里的常红，每多留一小时就多污染一次别人的红集合读数；0213 是大工程，不能当这条小红的挡箭牌。验收四件：`test_1c` 绿＋其余 10 条不放宽＋一条突变反例（改回 `HTTP_RESPONSE`+null 必须红）＋收据写 SHA 与临时库绝对路径。

## ② "线上部署的就是 `56d20ec`"现在有第二个来源

HJ-P1 16:22 自己从 `56d20ec` 构建出**同名同字节**的 `index-BCF4ptyk.js`（1,230,082 B，sha256 前缀 `f3bda3d696d37cd1`），与线上文件逐字节相同；它另外两臂的读数我也引用：`demo_mode=false` ⇒ 入口给具名可恢复文案、0 写；`demo_mode=true` ⇒ 直接进 Today、0 写。它同时报了一条我判定成立的新缺陷：**按钮写「使用封存的天津演示」而服务器给的是广州那趟** ⇒ 已不改正文地追加为 ORD-0216 第④件（要求：要么文案改成城市无关，要么入口显式选中天津；**不许把文案改成"广州"蒙过**）。

## ③ streak 的缺口：请补第 9 条（跑法形制），否则同一个 g3 会同时被叫"恒红"和"在翻"

HARNESS 16:27 在同一只 `56d20ec`、每形 10 个独立进程、10 个不同临时库、无 sleep/无重试/未降并发/未放宽断言下量到：

```text
单门形            g3  1/10 绿
带前序门同进程形   g1+g2+g3  7/10 绿
整文件形          0/10 绿（但那是 g5 10/10 稳定红造成的，不是 g3）
```

⇒ 我 14 次那把（12 红 / 2 绿）是**单门形**，所以严格说它是"近乎恒红"，不是"翻转"。建议冻结：

```text
GATE_ACCEPTANCE_STREAK (amendment)
9. the receipt must name its run shape: single-node | node-with-preceding-doors-in-one-process | whole-file
10. FLIP_WITHOUT_SHARED_STATE is only valid for a shape whose runs actually flip;
    a shape that is red 10/10 is STABLE_RED(<shape>) — naming it a flip hides the mechanism
```

我的 `gate_streak.py` 已经把 `--node` 写进收据（形制天然显式），交单车道必须把形制一并报。另外 `g5` 现在是 **10/10 稳定红**（C 早前自报"G5 AI no-op 不在我收口清单"），这条要不要现在给它立单，你说一句我就立——我不替你把队列加宽。

## ④ 现场

working tip 仍 `56d20ec`（`c8472fd` 在 F 的分支上，**我没合、也不打算让车道自己合**）；reference tip `c0d7e3d`；`P7=false`；`:8693` 未重启（`53fe8e8`）；用户库 3/19/3、护栏 403、匿名 401、`demo/reset` 从未触发、0 次 provider 出网；canary 全部验完即停；那把 key 仍未轮换（只有用户能做）。车道响应：F/HJ-P1/HARNESS 已交新块，C 已收到 ORD-0217 定位，D 收到 ORD-0216 第④件，B 在跑，HERMES 与 HJ-P2 两次点名后我继续盯。

竭尽所能的替qoder铺路
