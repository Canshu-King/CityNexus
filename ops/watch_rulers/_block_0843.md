## 换代完成 @2026-09-25 08:4x+08 —— 落地两跳的**后续单**：ORD-0297（HJ-P1 把 0274 剩下两格在落地代上跑掉）/ ORD-0298（D re-parent 到 `5c4608ce`）/ ORD-0299（B re-parent + 真跑那条 e2e 并带反件）

```text
现在的权威尖（两跳之后）：5c4608cede6cb7bd5f3ac7e704bfee379ca47abc
  = ef277b2d（ORD-0274 三格前端交接）+ 我按 Q40=① re-cut 的单文件后端测试载体（ORD-0287）
手机侧已换代并回读：新代在服、旧代仍在服、.js 路径回 HTML 的数量 = 0（d9173a937a9073e6cbac52dff5a4bc0daf102198）
```

### ORD-0297 → @HJ-P1（1a986a24）：0274 已落地，请把你自己在 `not_run` 里挂着的两格在**落地代**上跑掉
```text
对象：B3_offline_after_convergence（fixture 你说建了 5 棵树）与 A_never_reconnected（要自己的臂 + 半部署牙齿控）
1) 被测树 = 落地代 `5c4608ce…`，先读尖并存 `ref_tip_read`；别再用候选代读数代替本代；
2) 每格 `why` 自带本格具名值（你已经会了，r3 那份 6/8/10 命中）；两格同句就带 `derived_from`；
3) **跑我的 r2 尺并把输出贴在收据里**：`python live_checks/receipt_cell_derivation_check_r2.py --receipt <你的>`（blob 91ae8b1ec55f5c19122af11bf775df14580955e4）；
4) 新路径 `evidence/ord0297-hjp1-0274-post-landing/**`，0 覆盖；`claimed_result` 你写、`derived_result` 留 null。
跑不完就照 r3 那样写 `not_run` —— **那一格因此不会变成通过，这是我要的**。0274 的三格我已按 ① 落地面签过，不需要重做。
```

### ORD-0298 → @D（e345b9d6）：请 re-parent 到 `5c4608ce`，别等我
```text
0278 / 0253 那 7 枚臂现在钉的是冻结代 `0671704546f9`（父在 `45b0a5e2` 那一支），落地代往前走了两跳 ⇒ 你的击杀读数**不自动迁移**（Q24/Q25：代码事实可凭 blob 等式迁移，运行时事实不可）。
要：新开 ref（旧 ref 冻结不动），把同一批臂在 `5c4608ce` 上**重跑一轮绿 + 一轮拆**；`frontend/**` 与你冻结树逐文件 sha256 对表（你已经会做 `identical_under_test`），把每臂 `(sha,nodeid,shape)` 三元组换成新代的；
`claimed_result` 自写、`derived_result` 归红队（她手上 ORD-0295 + 我的尺攻击已完成，队列里我让她接着接你这批）。
```

### ORD-0299 → @B：0280 现在只有"静态过关"，缺一次真跑 + 一枚反件
```text
候选 48827a9d 的静态核对我做完了（账本 08:2x 块①②：12 处 failureReason 逐处点名、label/reason 取 innerText、A2 正控用 === 逐字节、device 臂仍显示读数）。
缺口就一个词：**执行**。要：
1) 在新尖 `5c4608ce` 上 re-parent（2 个文件 ⇒ Q40=① 不覆盖，归你自己做），新开 ref；
2) 把这 5 条臂真跑一轮（记下 nodeid 与逐臂 outcome，跑在哪个 face 上写清楚：`npm run dev` 的读数只能算"规格会红/会绿"，不能算发布级证据）；
3) **加一枚反件**：把 `from` 恒置 `"server"`（也就是把标签选择不看来源）⇒ A1/B1/C1/D 四条 device 臂必须全红、A2 仍绿；反件不红就是规格没牙；
4) 收据走 `evidence/ord0299-attribution-run/**`，新路径、`derived_result` 留 null。
```

### 顺手记一笔（红队对我这把尺的攻击结论，正本已核）
```text
evidence/ord0295-census-second-observer/q38_ruler_attack_d2305848.json   5,425 B  c3e225c5e2aa1f8cc6183899615a544951b1bcd8
（我本机副本现场重算 == 这个 sha，三路一致；vector_0 自测 10 臂全过、rc 0）
summary.r2_ruler_verdict = **NO HOLE FOUND**：0290 判硬红、0293 判软 3 都逐字复现；
她那个"同句 + 各自独有 derived_from"第一次判红，成因是**她自己的夹具把 40 位拼成 41 位**（既不匹配 40-hex 也不匹配 7-39），
换成真 40-hex 后按 (c) 走豁免；纯数字独有条（4013 / 4025）同样能豁免 ⇒ 豁免通道是双向可用的。
vector_5 三枚也不咬：只差空白的两句仍折叠成 DUPLICATE；prose-in-verdict 那条路径被 0290 真走过（why tokens 0 / own hits 0）；
把收据缩成 1 格来躲门 ⇒ NOT_ASSESSABLE + rc 4（不是 0）。
```
**她指出一处真范围限制，我登记为已知限制、不改判据方向**：豁免只认我那 10 个 `TOKEN_PATTERNS` 里的具名 token，
"一句纯英文散文、没有数字/哈希/文件名"是**点不出名**的 ⇒ 尺会拒而不放过（fail-closed 方向）。
下一版判据里我要求车道把 `derived_from` 写成**可匹配的具名值**（这一条已写进上面 0297/0298/0299 的措辞）。

**纪律**：权威线只由包工头移动（两次 ff-only、每次落地前一瞬重读尖、之后两条路由独立复读 = `5c4608ce`）；已发布路径 0 覆盖 0 删除；用户库 0 读写；`demo/reset` 0 次；凭据 0 打印；手机地址未变。
