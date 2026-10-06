## 补 @2026-09-25 06:2x+08 —— ORD-0286 判据正文（派 @红队，排在 ORD-0285 之后）：D 的 0278 + 0253 客户端候选需要机械 `derived_result`，我才动权威线

### ORD-0286 · 验 D 的候选 `review/0278-0253-on-45b0a5e`
```text
被验对象（外读坐标，我已核过一次尖号）：
  refs/heads/review/0278-0253-on-45b0a5e  尖 f86d24e976d9b4309f4005b6af5bd31f97ea7524
  起点 = 权威尖 45b0a5e281cae9c37715173afd3ac5778f309ca7（D 自陈 --is-ancestor True、领先 11 笔）
  旧代 review/0278-on-0269-rebased @ e7cf57986b5afd8137ba6f8255f337d19f41f19c 原样保留（无 force-push），
  两代读数各归各的坐标，**不许互相折算**。

判据（缺一格就不签级；我拿到你的 derived_result 才走 ff-only 落地）：
 1)  ancestry：自己读，不引 D 的结论。`git merge-base --is-ancestor 45b0a5e2 <tip>` + 领先笔数 +
     `git diff --name-only 45b0a5e2 <tip>` 的文件清单逐件带 blob（frontend/ 相对起点改 7 件是 D 自陈，你重算）。
 2)  树来源：GitHub tarball / `git archive <tip>` 干净导出，先读镜像尖；不许用 D 的工作树。
 3)  跑它自己的门：D 为 0278 与 0253 客户端各自声明的门节点，你在候选树上**实跑**，给每格
     (nodeid, 实测, rc)；一次性库 `_*.db` 带 run id、fresh-or-no-run、AI 显式 false。
 4)  反突变：D 若主张某条判据"有牙齿"，你按 B-1 只签 `derived_result`，
     每份收据内嵌 (sha, nodeid, shape) 三元组 + 同键前件；一臂红三条≠三份证据。
 5)  **0278 与 0253 必须分开签**（D 已按号令分开交付：各自 commit、各自门节点）；
     合在一起签级我会退回，因为一次红分不清是谁欠的。
 6)  落地前我把你的收据读回并钉进尺（`audit_closure_coordinates` 下一版）；旧发布路径 0 覆盖 0 删除。
 7)  发布 `evidence/ord0286-0278-0253-derivation/`；账本块 + 总线一条。
成本估计 30~45 分钟（两棵门的实跑是主要开销）。**排在 ORD-0285 之后，别并行。**
```

### 与另外两单的边界（防互吞，HJ-P3 0281 定形里那句我照抄进令）
`0274` = 换代与在飞写收敛；`0280` = 归因真实性（标签不许冒充）；`0281` = 写腿有没有期限 + 中止之后怎么算。三单共用"中止 ≠ 没发生"这句屏上事实，修复点不同文件，**谁也不许拿自己的绿替别人交卷**。
