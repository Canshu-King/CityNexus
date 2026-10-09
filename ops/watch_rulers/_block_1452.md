### CMDR-1452 · Q47=②① 盖章（不切 index，等射程表→改文案→只换一次）＋ ORD-0298d 我独立派生 7/7 ＋ ORD-0303 派给 F ＋ 我第二笔误更正

**Q47 的回字与对位**（总线盖章 `issuecomment-5828091963`；提问在 `issuecomment-5827977086`）：仲裁 14:3x 在窗口回 **②①**。第①问（换代窗口）→ **②** = 先等 HJ-P3 的 ORD-0301 射程表 ⇒ B 依表改文案 ⇒ 落地 ⇒ **只换一次**代 ⇒ 所以现在**不切** `dist/index.html`。第②问（ORD-0272 闭单前置）→ **①**，那一问我只给了"我倾向要（按 Q24）"一种读法 ⇒ 我记作**要重跑**，据此派 ORD-0303；若仲裁本意不同，回一个 ✗ 我立刻撤这单。
可复算判读点：`grep -aoE 'assets/index-[A-Za-z0-9_-]+\.js' D:/moodle/_qoder_preview_20260920/dist/index.html` 在 14:40:41 打出的仍是 `assets/index-xKIGmoBz.js`（08:36 那一代）；同刻带 Basic 走 tunnel 拿到成功响应（凭据只从 `run/preview_auth.txt` 取用，不落字）。

**ORD-0298d 的机械复核（我自己的读数，不抄车道正文）**：D 的新候选 `refs/heads/review/0278-0253-on-90d29a17` = `dc964086c9d412573ac19d70b24b30e6c3ee6168`（`tested_tree == tooling_commit`），臂收据 `457313365eda53e9634ddf522839fe3714d0e86d`，绿轮 gate `211c67f88b4360c63c1e4ed1c6284f36b3f354fd`。
```text
仪器  evidence/ord0298d-cmdr-derivation/derive_arms_commander_r2.py   blob 799f9b43690bb88b4a7f1722bf1ee3f4df742ca6   7,532 B
派生  evidence/ord0298d-cmdr-derivation/commander_derivation_r1.json  blob 14794d2c78c7099b3797c0bf5587e8f89262cdc1   5,130 B
结果  七臂 KILLED 由我逐条派生（十一枚布尔全过，`failing_checks` 全空），red sizes [1, 3]，claims agree True，rc 0
控制  同仪器喂回 ORD-0292 的三枚 blob 与冻结尖 06717045… ⇒ 仍 arms 7 / killed 7 / agree True（⇒ 参数化改写没动判据：正本 `derive_ord0292_commander_r1.py` 一字未改，新文件 `derive_arms_commander_r2.py` 的十一枚 checks 与它逐字相同）
还欠  `verifier_comparison.present = False`：红队签的是上一代 `dbd0f9d9…`，`dc964086…` 这代还没有 verifier 的 `derived_result`（B-1）⇒ 已点名红队；拿到我就 ff-only 落 ORD-0278 / ORD-0253
```

**ORD-0303 → F**：在 `90d29a172e186aab6e6cb138ab4583ccf93bfa68` 上重跑 ORD-0272 的九格 + K8 那一臂；先外读尖、每格 `(sha,nodeid,shape)` 与 runId、`derived_result` 留 null、两把尺原样输出随件发布、旧代次件不改。

**我第二笔误更正（链条要留全，别只留结论）**：早上我记"F 欠 `evidence/ord0289-ast-census/write_legs_f.json`"——**是对的**；14:02 我看见另一个目录里有类似件，就宣布"我路径猜错了、F 早就交了"并在 `### CMDR-1404` 作废了早上那笔——**那笔"更正"才是假的**。F 真交那枚是在 14:20（blob `2a2343c67417223f7e447ce1f53a87d3a3b02ea6`，落笔提交 `2d326839fe71`）。⇒ 我的错法：**从"别处有类似东西"推出"你要的那件早已存在"**；唯一合法的存在证明是按那个确切路径取回并重算 blob。这条已升进 `EVIDENCE_INTEGRITY_GATE_V1` 的第①查（Artifact：path + blob + size 一致）。

**常设口径 `EVIDENCE_INTEGRITY_GATE_V1`（源自仲裁 11:19 那轮，我采纳为验收门槛，即刻生效）**：① Artifact：path/blob/size 三者一致，按路径取回重算；② Claim：申报计数 = 观测计数，且写明 scope 与时间戳；③ Validator：每枚布尔 gate 带 positive / negative / mutation 三向；④ Identifier：判据、收据、换代规则里只允许完整 40 位 blob，短前缀只能当显示并标明是显示。
