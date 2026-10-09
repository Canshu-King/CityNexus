## 亲测 @2026-09-25 09:2x+08 —— 两件事我亲自量完了：**Q43 尺 r3（红队找出两个真洞，修完双向验死）** 和 **F 的 ORD-0296 后端半（10 条绿 3 轮 + 双向门真的咬）**

### ① Q43 尺被红队攻出两个真洞，r3 已修（两把尺之间做差分，不是嘴上说"修好了"）
```text
她的攻击件：`evidence/ord0295-census-second-observer/q43_ruler_attack_d2305848.json`（5,425 B，blob `c3e225c5e2aa1f8cc6183899615a544951b1bcd8`）
B1 全角等号 `DEFAULT_WRITE_DEADLINE_MS ＝10000`：r2 ⇒ `claims checked 0 / NO_CLAIM_FOUND_NOT_APPLICABLE`（**看不见**）
   同一输入 r3 ⇒ `claims checked 2 / Q43_GATE_RED`，命中码 `CONSTANT_VALUE_CLAIM_WITHOUT_COORDINATE` + `BARE_NUMBER_WITHOUT_COORDINATE`
B3 换词转述 "the lane said the deadline is 10000 …"：r2 ⇒ 0 claims（**词表追不上改写**）
   同一输入 r3 ⇒ 1 claim / `BARE_NUMBER_WITHOUT_COORDINATE`
r3 的做法：扫描前把全角 `＝`(U+FF1D) 归一化成 `=`；**新增 F3：任何裸数字申报（≥3 位，或"数字 + 单位/量词"）只要 200 字符窗口里没有 durable 坐标就判**——不再依赖固定词表
自测：`evidence/q43-claim-coordinate-gate/selftest_r3_20260925_0921.txt` blob `6791e409162551e4d67792335c938729a8894741` ⇒ **12 臂全过**（run 12 / passed 12 / failed []）
尺本体：`claim_coordinate_check_r3.py` blob `e653e597c2e6fd74a5f8d3be65fe60e017b03017`（11,765 B）
```
**同时把最不舒服的一条摆出来**：r3 拿去做在我自己 09:1x 那块已发布的账本文字上 ⇒ `claims checked 25 / findings 13 [BARE_NUMBER_WITHOUT_COORDINATE]`（`945edee78b97d68533a69279acd7a63cab9295e0`，2,634 B）。
⇒ F3 比 F1/F2 严得多，**已发布的历史文本我不回改**（改它会造出 5 MB 假 diff，也和"已发布路径冻结"冲突）；从下一块起我按 r3 写：每个数字旁边放坐标。红队若愿意，请继续攻 r3——它现在最该被攻。

### ② ORD-0296（F：0281 的后端半）我亲测过：绿、绿、绿，而且双向门真的咬
```text
候选：refs/heads/review/ord0296-write-deadline-f tip `6d041dcce11d05f28a55abadd40717f321b4db38`，parent = 现落地代 `5c4608cede6cb7bd5f3ac7e704bfee379ca47abc`（它自己就重切好了，不用我 re-cut）
5 个文件：`backend/app/core/config.py`(+10) `app/db/session.py`(+7) `app/db/write_deadline.py`(新 234) `app/main.py`(+181) `tests/test_qoder_ord0296_write_deadline.py`(新 361)
干净导出 git archive 到 `D:/moodle/_qoder_snap_0296`，解释器 `D:/moodle/CityNexus/.venv/Scripts/python.exe` = 3.12.14
--collect-only：**10 tests collected**（先报分母再谈绿）
默认值 `CITYNEXUS_WRITE_DEADLINE_MS = 45000` vs `CITYNEXUS_WRITE_BUSY_TIMEOUT_MS = 30000`（config.py:95/96）：
   3 轮删库重跑：10 passed / 10 passed / 10 passed（每轮 ≤1.7 s）
**双向门的反方向**（这正是 Q36=① 要的那一半）：`CITYNEXUS_WRITE_DEADLINE_MS=10000` ⇒ 启动即拒
   `app.db.write_deadline.WriteDeadlineConfigurationError: DEADLINE_NOT_ABOVE_BUSY_TIMEOUT:
    write_deadline_ms must be strictly above write_busy_timeout_ms=30000 for every scenario in
    ['agent.commands','plans.generate']`，并把每档的 `delta_ms=-20000 / effective_busy_timeout_ms=10000 / reachable=False / verdict` 打出来
   ⇒ 形状要说清：它是**具名拒绝**（fail-fast 在门口），不是"某条断言变红"。我量的是"拒绝发生且带具名码"，**没**把它写成 test-red。
顺带回归（不跑全量，说清范围）：`tests/test_qoder_ord0287_k8_carrier.py` 2 passed；`tests/test_contract.py` 4 passed（OpenAPI 奇偶门没被我这次改动搞红）
**没做的**：全量 1232 条后端套件（时间不够，我不说"全绿"）；F 自己的交付收据我还没看到 ⇒ 我不签 CLOSED，只记 `VERIFIED_BY_COMMANDER / 等 F 的 claimed_result 与击杀收据`
```

### ③ 队列与手机
`review/0280-attribution-label-r2`（B 的 0299 修订候选，尖 `549ac8f1b20bc04e70eadbd238ade737eefbff01`）**仍未推上线**（外读 422，分支表里只有旧的 `48827a9d6402aaabffc5ff47b1540407fafed620`）；09:30 前推上来我就按 **Q44=①** 落它并评估第二次换代（09:40 之后不动手机面）。D 的 ORD-0298、HJ-P1 的 0297 也还没回。
手机：仍是我 08:37 换的那一代（`5c4608ce…`），09:0x 逐字节回读为证（`62f07fe62934750b57c1ef6a7a227c7c33c91e30`）。
**纪律**：权威线本节未动；本节 3 次 PUT 全 BYTE-LEVEL MATCH、0 覆盖 0 删除；用户库 0 读写；`demo/reset` 0；凭据 0 打印。
