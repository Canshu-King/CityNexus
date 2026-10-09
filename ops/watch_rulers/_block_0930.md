## 落地 @2026-09-25 09:2x+08 —— **权威线第三跳：`5c4608ce` → `6d041dcc`（ORD-0296 / 0281 的后端半）**；红队那两处 Q43 漏洞也修了（r3 自测 12/12）

### ① 我凭什么落它（每一条都是现场量，不是"车道说"）
```text
候选：refs/heads/review/0296-write-deadline-f tip `6d041dcce11d05f28a55abadd40717f321b4db38`，parent = 当时的尖 `5c4608cede6cb7bd5f3ac7e704bfee379ca47abc`
5 个文件：`backend/app/core/config.py` `backend/app/db/session.py` `backend/app/db/write_deadline.py`(新) `backend/app/main.py` `backend/tests/test_qoder_ord0296_write_deadline.py`(新 361 行)
我自己跑（`git archive 6d041dcc backend data contracts tools` -> `D:/moodle/_qoder_snap_0296`，venv 3.12.14 = `D:/moodle/CityNexus/.venv/Scripts/python.exe`）：
   `--collect-only` = **10 tests collected**；删库重跑 3 轮 = **10 passed / 10 passed / 10 passed**
   默认值：`CITYNEXUS_WRITE_BUSY_TIMEOUT_MS = 30000`（config.py:95）、`CITYNEXUS_WRITE_DEADLINE_MS = 45000`（config.py:96）
   **反方向（Q36=① 的那一半）**：`CITYNEXUS_WRITE_DEADLINE_MS=10000` ⇒ 启动即具名拒绝
     `app.db.write_deadline.WriteDeadlineConfigurationError: DEADLINE_NOT_ABOVE_BUSY_TIMEOUT`，逐档打 `delta_ms=-20000 / effective_busy_timeout_ms=10000 / reachable=False`
   点名回归（范围声明）：`tests/test_qoder_ord0287_k8_carrier.py` 2 passed；`tests/test_contract.py` 4 passed
它的反突变（我机械复算，不抄它的结论）：`evidence/ord0296-write-deadline-f/mutation_campaign_r1.json`
   **10/10 臂**每臂满足：3 轮 rc≠0 且每轮红它点名的那个节点、`before_blob_40 != after_blob_40`（变异真落盘，这条是我今晚自己踩过的坑）、`restored_byte_exact`、`py_compile_ok`、`carriers_removed>=1`、意外红 0、车道把 `derived_result` 留 null
   全局：survivors = []、control_rounds_green = true、unexpected_red_total = 0 ⇒ 我的派生 = **KILLED_ALL_ARMS_AND_CLEAN_AB**
   派生件：`evidence/ord0296-write-deadline-f/commander_derivation_r1.json` 5,477 B blob `382d6b502030c6c3045499adb8e4b65101219111`
A/B 全量（它交、我逐节点比对）：基线 **10 红 / 1208 绿**，候选两轮 **10 红 / 1218 绿**；
   **候选红节点集合 == 基线红节点集合**（新增 0、消失 0）⇒ 这是"无新红"的名字级证明，不是"数字差不多"
```

### ② 落地动作与手机面的实话
```text
`live_checks/land_authoritative_ref.py 6d041dcc… 期望基 5c4608ce…`：落地前一瞬读回尖 = `5c4608ce…` ✓，PATCH force=false -> http 200，读回尖 = `6d041dcc…` ✓（父 = `5c4608ce…`，tree `5e9b6decb7f7`）
**手机不需要第二次换代**：这次落地 `git diff --name-only 5c4608ce 6d041dcc -- frontend` = **0 个文件**（5 个文件全在 backend）⇒ 包不变，换了指纹也不会改变手机上那一份
**但后端面要说清**：手机上那个预览后端**还是重启前的旧代码**——这一跳改的是服务端写路径（写期限 + 具名拒绝），**没重启就不在手机上生效**。
   我不在 09:3x 去重启它（用户 10:00 要看手机，链路现在是健康的：08:37 换代 + 09:0x 逐字节回读）；
   ⇒ 状态记为 **REPRODUCED(tree+pytest) / NOT-DEPLOYED(preview backend)**，下一班要看到手机上也吃到它，就得挑一个不赶时间的窗口重启那一台。
```

### ③ 我这一跳给车道添的成本（不藏）
尖从 `5c4608ce` 前进到 `6d041dcc` ⇒ **@D 的 ORD-0298、@HJ-P1 的 ORD-0297、@B 的 ORD-0299（`review/0280-attribution-label-r2` 仍没推上线：外读 422，分支表里只有旧 `48827a9d`）都要把候选 re-parent 到新尖再交**。
按 **Q40=①**：只有"单文件 + 我能逐字节证明"的那种我替你做；0280 是 2 个文件（含新 e2e 规格）、0298/0297 是多臂重跑，**都还得你们自己切**。我落地前后都会把尖号贴在总线上，不让你们猜。

### ④ 另一件已完成的（红队替我抓出来的）
`claim_coordinate_check_r3.py` blob `e653e597c2e6fd74a5f8d3be65fe60e017b03017`：全角 `＝` 归一化 + 新增 F3（任何裸数字申报旁必须有 durable 坐标）；
差分证明：她的两枚逃逸输入 r2 都是 `claims 0 / NOT_APPLICABLE`，r3 分别 `claims 2 / RED` 与 `claims 1 / RED`；自测 **12 臂全过**（`6791e409162551e4d67792335c938729a8894741`）。
我拿它量自己今晚的账本文字：`claims 36 / findings 7` ⇒ **已发布历史不回改**（与"路径冻结/不造 5 MB 假 diff"冲突），从下一块起按 r3 写。

**纪律**：本节 4 次 PUT（r3 尺 + 它的自测 + 我对自己的量 + ORD-0296 派生件）全 BYTE-LEVEL MATCH、0 覆盖 0 删除；用户库 0 读写；`demo/reset` 0；凭据 0 打印；权威线由包工头单独移动（本次 1 跳，落地前后各读一次尖）。
