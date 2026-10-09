## commander 恢复 @2026-09-22T18:30+08 —— 预览链第二次重建成功（**新隧道地址已换，请用户用新的**）；崩溃后第一轮回收完成；三张新单已下

### ① 预览链（用户手机此刻可以连了）

```text
新地址   https://brochure-humor-twisted-broadcast.trycloudflare.com     ← 请用这个，旧的三个都死了
链条     cloudflared -> :4782 (auth_proxy) -> :4781 (vite preview) -> :8693 (uvicorn, _live.db, demo_mode=true, ai=enabled)
bundle   assets/index-BCF4ptyk.js（= 56d20ec 构建；上一代 index-CnfHH2K_.js 并存可达）
端到端   鉴权 /api/v1/health -> 200 {status:ok, database:ok, ai:enabled}
         鉴权 /              -> 200  bundle = assets/index-BCF4ptyk.js
         匿名 /api/v1/demo/scene -> 401（护栏在位）
         匿名 /              -> 401
         鉴权 POST /api/v1/demo/reset -> 403（R13 护栏在位）
死链     fonts-facilities-hotel-installing（16:48 建）、buyer-festivals-jeans-photographers（16:50 建）
         —— 两条都被崩溃带走，已写进 tunnel_url.txt.dead_1830 / .dead_1648，不要再连
```

**为什么这次是我做**：`no D/B/E/F lane may operate :4781/:4782/:8693 or the preview proxy` 是仲裁的既有裁定 ⇒ 这几条端口**只有我能碰**，不是我不肯派。8693 在我动手前已由别的进程拉起（health 200），我只补了 4781/4782/隧道。

### ② 崩溃后第一轮回收（三份真交付，我只做派单，不替它们复跑）

| 交付 | 谁 | 结论 | 我下的单 |
|---|---|---|---|
| ORD-0218 g5 诊断 | HARNESS 18:14 | 三形制全 `STABLE_RED`；链定死**缺在发射层**（`runtime.py:318/:636` 构造点不带 outcome、`:589` 只在成功路径写散文、skip/no-op 不写） | **ORD-0219 → B** |
| ORD-0216 双向门 | 红队 18:07 | 拆对臂 KILLED（对照成立）＋**语义反转臂 SURVIVED**（门只钉子串同现，caveat 说了什么没断言） | **ORD-0220 ①→ D** |
| ORD-0217 复验 | 红队 18:07 | C 选 ① 是**真修复**（门 11/11、三形状探针正确、反向突变红在 `test_1d`） | 无（已 ACCEPTED） |
| HJ-P1 自我更正 | 18:07 | 自撤"挂在屏上"半句（`innerText` 把 `.v8-sr-only` 算进去，它本轮第三次栽同一量具）⇒ 改判 `HUMAN_ACCESSIBILITY`；**另报一条更重的 `HUMAN_BLOCKER`**：被拦时解释在视口下方 377 px、产品不滚动 ⇒ 体验是"按了没反应" | **ORD-0220 ②③→ D** |
| HJ-P3 水位线 | 18:0x | 它 15:2x 那块完好；我 17:5x 唤醒消息引用了 14:24 旧水位线 ⇒ **以它 16:3x 为准**，我的排程文案错 | 记在这里 |

### ③ 按用户 17:4x 新口径的分工变更

用户明确：**"尽量把检查和审计任务给 GPT 完成，而不是你来做；你主要是检查其他会话有没有活干，没活干就去下发任务。"**
⇒ 从现在起：**深度审计（跨文件一致性、门是否真空、突变是否真杀）优先转 GPT**；我只保留"派单 + 巡逻 + 最便宜的现场读数"。
**已照此执行的第一件**：D 的 `50b35e0`（ORD-0216）我**不做深度审计**，整单转 GPT 审（要 diff、两条门的反例、以及"改完当场消失"在第 2/3 步各是什么读数）；我只确认了该 SHA 在 working tip 上。

### ④ 现场冻结

working tip `50b35e0`（16:41，D 的 ORD-0216）；reference tip `c0d7e3d`；`P7=false`；用户库（只读）journeys 3 / travelers 3 / plan_versions 19 / commitments 1 / bookings 1 —— 两次崩溃+重启后逐项未变；`demo/reset` 从未触发；0 次 provider 出网；那把 key 仍未轮换（只有用户能做）。
