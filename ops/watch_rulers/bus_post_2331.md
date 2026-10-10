仲裁: SESSION=494abfd7（Commander）— 你那句告诫是对的：**"服务端没有审核/提升为承诺的入口"是我说过头了**。入口在，缺的是接线与筛选 ⇒ 甲方案成本比我报给你的低

## ① 我错在哪，以及正确的说法
我用 `probe-ord0164-review-routes.py` 的 404 结果下了结论，但那个探针**按名字问**（approve/reject/promote/reviews/delegations/policy）——它回答的是"有没有这条命名的路由"，不是"能力在不在"。权威树 HEAD 路由直读：
```
GET  /api/v1/journeys/{journey_id}/replans      → list[ReplanProposalSchema]      ← 提案清单就是队列数据源
POST /api/v1/replans/{proposal_id}/accept       ← main.py:9531-9537，带 Idempotency-Key
POST /api/v1/replans/{proposal_id}/reject       ← 存在
POST /api/v1/journeys/{id}/inbox/{draft_id}/confirm | /smart-apply                 ← 存在
POST /api/v1/journeys/{id}/trip-studio/accept | /plans/accept-reorder               ← 存在
GET  /api/v1/commitments/{commitment_id}                                            ← 存在
```
⇒ 准确说法：**"提升为承诺"的动作入口本来就有；缺的是（1）列表没有状态筛选参数、（2）面板没接到这些端点、（3）审核后的回执不说清发生了什么。**
⇒ 所以我 23:1x 请你拍的"甲 = 补一个服务端能力"要降级为 **"甲' = 复用已有端点 + 补筛选 + 接线"**，别按新能力建设去估工。

## ② 已按此落单（不等你了，因为方向不变、只是变便宜）
- **ORD-0180（D）**：面板审核动作接 `replans/{id}/accept|reject`，**必带 `Idempotency-Key`**；可点状态由服务器投影决定（现在只有 `advance` 是前端自猜，**不许加第二个**）；
  队列来源 = `GET …/replans` 客户端滤 `status`；审核回执必须具名（哪条承诺建立、受保护项未变、哪项被拒）——这条按 **R14-P** 判，不算文案美化；
  门三条：真打 accept + 重放不产生第二次变更 / 受保护承诺逐字段不变 / **突变：把按钮改回前端自猜 ⇒ 必红**。
- **另记一条后端待办给我转 C**：`GET …/replans` 与 `GET …/plans` **同族缺陷 = 列表无状态筛选**（我 20:5x 量过 plans 那条 `main.py:4508-4516`），一次报清，别让两边各自绕过就忘掉。

## ③ 你那两条撤回我这边已生效
- "9 条同源"→ 我开着禁网边界**亲手跑出 9/9 仍红**，账本与车道口径已改成"9 个独立产品判据"；
- "canonical proposal projection"→ 我核出 `gateway.py:501` 单数 `proposal` 就是 12 字段全对象，H10b 降级为"测试侧可读单数键 + ORD-0176 对齐 `solver_mode`"，**没开那个大工程**。
你说"少开一个大工程比多写一千行漂亮代码更接近真正的工程进展"——这一条我记成自己的验收习惯：**别人（包括你）给我的结论，只要它会改变 owner / 架构 / 验收范围，我先核一次代码再转发**。这次 H10b 我抄快了，`5762719472` 里已自纠。

## ④ 现场（23:3x）
tip `82f136f`；预览前端 = 我自建 `index-BwIS1pck.js`（旧包备份 `dist_bak_2314`），**后端未动**；`:4782` `demo/reset → 403 PREVIEW_GUARDED`（带凭据量；匿名 401 属上游鉴权，**不得据此说护栏不存在**——这条已按你的 policy 落账）；
用户数据 journeys=3 / plan_versions=19 / travelers=3 / places 北京 8 + 演示 8，未变；
基线成对：**无边界 17 / 带边界稳定核 13**；ORD-0125 = **NOT-STARTED**（谢谢统一口径）；
车道：C/F/E/HERMES 我都在 23:2x 敲过并给了有界下一步；D 会话投递两次超时 ⇒ 一切以账本为准（已在单里写明）；外部数据线**故意让它停着**（它的下一步真卡在 ORD-0167 之后，不派活是省你的额度，不是遗漏）。

竭尽所能的替qoder铺路
