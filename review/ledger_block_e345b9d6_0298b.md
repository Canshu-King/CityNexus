### SESSION=e345b9d6 @2026-09-25 09:4x+08 —— **ORD-0298 的落地时补记（两件事：红队 derived 已到 + 权威线又动了两跳，用 tree-oid 判，不改上一块任何判据）**
（总线正文 = comment 5825303735。上一块 `@2026-09-25 09:39+08` 的读数被测尖仍是 `8ccfcf7a5c3f7f45026a9df53670d780bdc155d5`；候选 ref `refs/heads/review/0278-0253-on-5c4608ce` ⇒ 外读尖 `195a0f24c38c71979bc88e3a26cb23a3b4a7cd0d`，其与 `8ccfcf7a5…` 之间 `frontend/**` 移动 0 件。）

**① 红队 @E d2305848 的 derived 已落在我的证据目录里**（她写的，不是我转述）：`evidence/ord0298-on-5c4608ce/verifier_derivation_d2305848.json` blob `472bf8481c35e4fdc033fbc53aec601b64e8ccb9`（5,420 B，`CNX_VERIFIER_DERIVATION_V1`，at 09:42+08）。她那份里的可判读数（F1 形式，坐标 = 上面那枚 blob）：
- `DERIVED_KILLED = 7`（她的 `derived_result` 原文 "7/7 KILLED on tested_tree 8ccfcf7; every kill derived from raw round fields; zero claims taken"，在同一枚 blob `472bf8481c35e4fdc033fbc53aec601b64e8ccb9` 里）
- `MUTATION_LANDED_CHECKS = 7`（她按你新加的口径另核 `digest_before_mutant != digest_mutated` ⇒ 7/7，见同一 blob 的 `mechanical_derivation.per_arm_checks_common_to_all_7`）
- `INDEPENDENT_KILLS = 5`（她本代重算，不从 `0671704546f9c9ea1d1b57627b059124c7800803` 沿用：4 枚 K278 sole-carrier + 1 枚 K253 compound cut-set，同一 blob `472bf8481c35e4fdc033fbc53aec601b64e8ccb9`）
⇒ 这批现在是 **claimed 7 / derived 7 / 独立击杀 5** 三个数并存，各归各的出具人（我签 claimed，她签 derived，等级仍归她与仲裁）。

**② 权威线又前进了两跳**（`git ls-remote refs/heads/mirror/integration-frontend-apple-pass1` 现读 `90d29a172e186aab6e6cb138ab4583ccf93bfa68`），判据用 `frontend` 子树 tree-oid，不数文件：
```text
5c4608cede6cb7bd5f3ac7e704bfee379ca47abc  frontend tree = fa3d73edc6dca05728b03753ab61af335efc6d91
6d041dcce11d05f28a55abadd40717f321b4db38  frontend tree = fa3d73edc6dca05728b03753ab61af335efc6d91  （同一枚 ⇒ ORD-0296 对前端零影响）
90d29a172e186aab6e6cb138ab4583ccf93bfa68  frontend tree = 663b4516bd8d79eecb1ebc7991dd7d3a45fb90c0  （变了）
8ccfcf7a5c3f7f45026a9df53670d780bdc155d5  frontend tree = c9623f46cace7a9c069ad9c36bfa395f9ffa790a  （我的被测尖）
```
⇒ 按红队与我同样认的这条携载规则（子树 oid 不变才谈得上不重跑）：**上面那 7/7 不能读成 `90d29a17` 的当代读数**。旁证两处：`git show 90d29a17…:frontend/src/features/planning/PlanWithAiSheet.tsx` 相对 `6d041dcc…` numstat **71/16**；`git show 90d29a17…:frontend/src/api/journeyContinuation.ts` 里我那条整行锚点（`body: JSON.stringify({ candidate_count: 3, mission_id: args.missionId }),`）**0 命中**（同一锚点在被测尖 1 命中）⇒ 0278/0253 现在确实不在权威线上。合流只读预测：`git merge-tree --write-tree 90d29a17… 195a0f24…` ⇒ rc=0、tree `2fb5d599e83c0ab8a155d7225a5022e41f75227b`（我 0 次移动任何 ref）。

**要我做第二轮 re-parent 到 `90d29a17`（重跑一轮绿 + 一轮拆，≈25 分钟，端口带已含守卫）请落字**；上一单你点名的是 `5c4608ce`，我不擅自换基座，换了就按 Q24 重跑，不给新尖贴旧读数。目录现状：`evidence/ord0298-on-5c4608ce/` 共 **8 件** = 我 7 件 + 红队 1 件，全部独立 GET 逐字节回读过；`demo/reset` 0 次、`_live/_preview` 0 读写、凭据 0 打印、权威线 0 次移动。
