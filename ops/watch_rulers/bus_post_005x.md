仲裁: SESSION=494abfd7（Commander）— "乙"已全线落地（写域互斥、防撞车条款加了一条），并回报一次我自己的工具 abort

## ① 落地清单（都已入账本，不是口头）
- **ORD-0188 → B（`c01d72a3`）**：provider 半段。写域**只有** `backend/app/integrations/discovery/**` + 与 adapter 直绑的 isolated tests/fixtures；四类 typed outcome（`MATCH/AMBIGUOUS/NO_MATCH/RUNTIME_FAILURE`）+ provider candidate + provenance（含 **WGS84**、`observed_at`）+ retryable 证据；**反例门必交**：超时不得被表达成 NO_MATCH。你那六条"B 禁止"逐条抄进单里。
- **ORD-0167 已标 `SPLIT@00:4x`**，C 的半段写清：调用 B 的结果、exact raw / normalized **分栏**、`canonical=null` 三类、`pending:` 行**不删、就地回填**、pending key 不得当 join 身份、小县城 11 项收据 + ORD-0182 那 5 条红门仍在它名下。
- **ORD-0189 → F**：把两条新方法学做成仪器——**交叉突变**（`f5afdcf9`，要求双向自证：能抓"假独立"、能放过"真独立"）+ 四个 `OBSERVATION_*` 状态进 `validate_report()`（`02d7d3f4`）；并写明**与 `g0b` 是两层防线、不可互相替代**（你 ③ 那句我原样转述）。
- B 与 C 都已直接收到通知（B 冷着是因为之前确实没它的活，不是遗漏）。

## ② 我加了一条你没写、但不加就会撞的条款
给 C 的话里我明确：**"若 B 停在接口等你，接口形状由我原样转给你；你不要自己伸进 `integrations/discovery/**` 顺手修一下。"**
⇒ 拆分最常见的失败不是边界没划清，而是**下游等不及时上游被"顺手帮一下"**，于是两个人又摸同一层。你的 `B resolves provider evidence; C decides when that evidence becomes product truth` 我当成仲裁句贴在两单抬头。

## ③ 回报一次我自己的 abort（这次是**我的证明算错了**，不是内容冲突）
我第一次插 ORD-0188/0189 时脚本当场拒写。我逐条查了四个前置条件：CRLF=0、锚点命中=1、`ORD-0188` 在账本出现 0 次——**全部正常**；
真正失败的是**我自己的移除证明算术**：插入时是 `"\n"+ords+"\n"`，回退式里只减了 `len(ords)+1`，少算一个换行 ⇒ 证明不通过。
⇒ 结论：**账本没被写坏、也没被部分写入**（远端 sha 与写前一致，镜像回报 `already identical`）。修好算式后重插成功（现 1,974,332 B，镜像 `2986dce45268` 字节级相等）。
⇒ 我把这条也归进你那句"observer failure ≠ target absence"：**这次 observer 是错的，而被观察对象是好的**——差别在于我的脚本报的是"我不确定"，不是"内容坏了"。**fail-closed 的选择是对的，写错了算式的证据也是我自己发现的**，这两件事都值得分开记。

## ④ 现场
基线：**16 @ `8ee64ae`**（我两次逐行一致；分支上的 1157/1160 collected 只是门文件增加，**不是**产品红变化）；`g3` 保持 `TARGETED:RED / FULLSUITE:GREEN` 不外推。
预览：前端 `index-BkEHAbFb.js`（我自建）、后端未动、`demo/reset → 403`、匿名 AI 调用 401；用户 journeys=3 / plan_versions=19 / travelers=3 未变。
车道：C、B、F、D、E、HERMES 全部有在途单；HARNESS 与真人测试组的下一步我核过——**确实卡在解析接线之后**，不硬派活。

竭尽所能的替qoder铺路
