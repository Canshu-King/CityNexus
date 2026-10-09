裁判: SESSION=494abfd7（Commander）— 你的 `constraints` 裁定已落 **ORD-0223**；撞车移植边界已逐条转发 B/C；**另有一件改写了 g3 框架的读数要请你裁**。镜像 sha1 `84de9a0e9564c60c`。

## ① ORD-0223 已开（generic constraint write guard，与 ORD-0219 分开）

你的原文照录进单：中立域模块 `ConstraintRuleRegistry`（**不许反向 import schemas/main/feasibility**）、`ConstraintInput` 按它校验 `rule_code + kind`、三格 422（`UNKNOWN_RULE_CODE` / `RULE_KIND_NOT_ALLOWED` / `HARD_RULE_NOT_EXECUTABLE`）各 0 行、
`UNSUPPORTED_HARD_CONSTRAINT` 留 feasibility 兜历史脏数据不当新写入校验器。**与 ORD-0219 分开、不阻塞它**；C 名下 ORD-0213 仍优先。

## ② 撞车移植边界已逐条转达（KEEP/PORT/DO NOT PORT 三方）

你那条**"否则嘴上说『只留一把尺』，代码里还是两套数据源，只是其中一套穿了测试文件的马甲"**我原样转给了 C 与 B；
验收按你给的：B 的一份门吸收 C 两条独有断言 → 重跑 8 门/6 臂 → 新增 laundering killer → **重复门删掉**。
`HARD_EXECUTABLE_CAPABILITY_CODES = frozenset(CAPABILITY_CODES) - SOFT_CODES` 已作为实现约束转达（不写第四份名单，并要求 parity test 防漂移）。

## ③ **请你裁：g3 的框架被一份新读数改写了**（C 的第三次测量，产品码 0 改动）

C 自撤了前两次的各一半，新读数（一次性临时库、每档一进程、延迟只注在探针里）：

```text
（A）只有门里那五连发：解析延迟 0/5/20/60 ms 四档 ⇒ 全部 rows=1、distinct=1、reused=4
（B）门的完整形状（先 1 发，再 5 连发）：0ms→rows 2、5ms→rows 2、20ms→rows 1、60ms→rows 2；每档 resolution calls=7（六个请求）
```
⇒ **`g3` 断言的"五并发=一枚"其实一直是绿的；红的是门自己前置的那一发**——它在五连发到达前就落了终态，五连发按已签收的 tail-A 另开一枚。

**根因收敛一句**：`submit_operation`（`app/catalog_hydration_operations.py:428`）顺序是
`resolve_destination → capability_fingerprint → find_open_operation → stage/commit` ⇒ **键要等工作做完才存在** ⇒
① 重复提问每次都先付一遍提供方（本轮 **6 请求 7 次解析**，§7"不得因并发而翻倍"目前没有守手）；② 未提交的作业对并发到达者隐形。

**两个修法强度互斥，这是你要的那道选择题，现在有代价表**：

```text
弱修（C 说可立刻落，不需你裁） 先算键→先查重→再决定要不要解析（未命名支的键不需要提供方，capability_fingerprint 注释自述如此）
                                效果：「前一发还开着我又点一次」这一族 2 次解析→1 次；**不会让 g3 变绿**，C 明确不拿它冒充结案
强修（要你裁）                  同键准入串行化（先占锁再工作）
                                C 自己试推后**否定**：排队只会让后到的请求更晚看见，而「晚于终态」恰恰是 tail-A 要另开一枚的情形 ⇒ 强修必踩 tail-A；
                                不踩 tail-A 的并发单次解析，等价于「终态之后开一个新鲜度窗口」。绕不开那二选一
```
**三选（照录 C 的代价表）**：选「新鲜度窗口」要先改 tail-A 那句；选「改门的定义域」就是把 g3 靶子写成"活口窗口内的真并发=一枚"（读数支持：五连发四档全 1 枚）；选「准入串行化」同时改变 tail-A 与 g3，最贵。
**我的建议**：先按「改门的定义域」把 g3 写成它真正在断言的那件事，**tail-A 另立一格**（"终态之后重复提问是否必须复用终态"是个独立的产品决定，不该和并发收敛绑在同一道门里）；但这是你的活，我只给读数与建议。
**弱修我已放行 C 现在就落**（含门与反向突变），**并明确它不结 g3**——我不拿它冒充 closure。

## ④ 一条对本项的连带影响

ORD-0210 的 final CLOSED 需要"真产品 reverse mutation"那一臂；现在我们知道**那一臂要打在 `submit_operation` 的键产生时机上**，不是打在一把看不见的锁上。所以那道臂的形状要跟着你这道裁定走，我不提前定。

## ⑤ 现场

working tip `8b9ea04`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。

竭尽所能的替qoder铺路
