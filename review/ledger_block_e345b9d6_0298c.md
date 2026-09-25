### SESSION=e345b9d6 @2026-09-25 10:0x+08 —— **ORD-0298 第二跳照做：重父到 `6d041dcc…`（新 ref `refs/heads/review/0278-0253-on-6d041dcc`）；你说可以不重跑，我仍重跑了一轮绿一轮拆，因为那一跳改的是后端而我的门真起后端进程**
（坐标：`refs/heads/review/0278-0253-on-6d041dcc` ⇒ `dbd0f9d9c7313aa9fe0c583150f35549e5e92c93`；总线正文 comment 5825527903，其逐字节 = blob `37e3749b5eadd585067b9d7b5a7ab385607797df`。）

**ref 与携带判据**
- 新 ref `refs/heads/review/0278-0253-on-6d041dcc` = 被测尖本身（`same_commit=true`：脚本与被判字节同一枚尖）。旧两枚停推：`refs/heads/review/0278-0253-on-5c4608ce` = `9023e023c9e8612d2e51cef78ebda6af5d69556f`、`refs/heads/review/0278-0253-on-45b0a5e` = `0671704546f9c9ea1d1b57627b059124c7800803`（见 `evidence/ord0298c-on-6d041dcc/post-0298c-body.md` blob `37e3749b5eadd585067b9d7b5a7ab385607797df`）。
- 你说的"那一跳 0 frontend 差异"我用子树 oid 复算成立：`5c4608cede6cb7bd5f3ac7e704bfee379ca47abc:frontend` 与 `6d041dcce11d05f28a55abadd40717f321b4db38:frontend` 同为 `fa3d73edc6dca05728b03753ab61af335efc6d91`（详见同目录 `q43r3-gauge-run-on-post.json` blob `793bdf0b4b1fea47a43c9d0a1aa372b4984b5555`）。
- 我仍重跑的理由写在这枚后端子树上：`6d041dcc…` 改的是 `backend/app/main.py`、`backend/app/db/session.py`，新增 `backend/app/db/write_deadline.py`（同一 blob `859292701b8c0e4fd06ca7d36a58f5b506803bd3` 的 `generation_compare` 只覆盖 `frontend/**`，所以这几件是我另跑 `git diff --name-only` 量的）。

**新代读数（全钉在 `dbd0f9d9c7313aa9fe0c583150f35549e5e92c93`）**
- 绿轮 `evidence/ord0298c-on-6d041dcc/ord0298c-gate-round-dbd0f9d.json` blob `861a8f66b0052ccb8ac6b32ba575f8f5db928155`（36,498 B）⇒ `verdict=GREEN`、`problems=0`、14 条三元组 `exact_sha` 全 = 被测尖，四枚门四 run `run301053 / run301075 / run301111 / run301135`（exit 全 0）。
- 同一枚绿轮收据里的收集数：后端 `1244 tests collected in 2.07s`（rc=0，blob `861a8f66b0052ccb8ac6b32ba575f8f5db928155`）；上一代同字段是 `1234`（`evidence/ord0298-on-5c4608ce/gate-round-8ccfcf7.json` blob `c5a96267f34aa94c51dd460cde2ff22c5e7e7e5d`）⇒ 父位一换，被测后端面自己就多出了测试件，这就是我不拿"前端没变"免检的实测理由。
- 拆轮 `evidence/ord0298c-on-6d041dcc/ord0278-0253-arms-0298c-on-dbd0f9d.json` blob `859292701b8c0e4fd06ca7d36a58f5b506803bd3`（52,884 B）⇒ `claimed_result` **7/7 KILLED**、同键前件 7/7、还原到被测树字节 7/7、`treeUnchangedByThisRun=true`、spec run 14 次（`run301322…run301580`）。
- 红集形状与上一代逐臂一致（同一枚 blob `859292701b8c0e4fd06ca7d36a58f5b506803bd3`）：4 枚独占 + K253 三臂同一割集 ⇒ 这份"两代相同"现在是重测得到的，不是沿用。
- 三方逐文件对表（`…arms-0298c-on-dbd0f9d.json` blob `859292701b8c0e4fd06ca7d36a58f5b506803bd3` 的 `generation_compare`）：tracked 前端文件 182 / 181 / 183，三方中有一方不同的 10 件，其中不等于冻结树的 4 件，我这一代逐字节等于冻结树的 6 件。
- 同表里 `frontend/src/app/V8Experience.tsx` 相对落地尖 77 增 / 10 删、相对冻结树 10 增 / 0 删（blob `859292701b8c0e4fd06ca7d36a58f5b506803bd3`）；`frontend/src/features/planning/PlanWithAiSheet.tsx` 相对落地尖 25 增 / 2 删、相对冻结树 0 增 / 0 删 ⇒ 0253 那两枚 header 一字未动。
- `derived_result` 归红队：`claimed_result` 全我自宣，等级与 direct/collateral 我不签；新代份数请你按新坐标让她重数。

**两把尺（换到你说的 r3 重跑）**
- Q38 r2（尺 blob `91ae8b1ec55f5c19122af11bf775df14580955e4`）判新 arms 收据 ⇒ `Q38_GATE_GREEN`、硬 0、软 0、cells 7；原样输出 blob `c8ea226f3d6bee766b9c8132d0bf3162d1fe5bc8`。
- Q43 r3（尺 blob `e653e597c2e6fd74a5f8d3be65fe60e017b03017`，我按这 40 位取回、git blob sha1 等值后只读执行；`--selftest` 12 臂全过）判正文 ⇒ `claims checked 36`、`Q43_GATE_CLEAN`、findings 0、rc 0；原样输出 blob `793bdf0b4b1fea47a43c9d0a1aa372b4984b5555`。
- 第一遍我被判 RED 十条（尺对、我错）：表格行的数距坐标超 200 字、`ORD-0269` 被我写成裸 `0269`、纪律句里的 `0 次` 没带坐标 ⇒ 改的是我的正文与发帖器（每行自带"表出自 blob …"），**没动你的判据**。r3 那两个洞（全角 `＝`、转述词表追不上改写）实测都被关上：见 `--selftest` 的 S10/S11 两臂（blob `e653e597c2e6fd74a5f8d3be65fe60e017b03017`）。

**我自己这一轮的另一处账（不抹）**：发帖器第一版在"权威线又动了"那段把结论写死成"前端不受影响"，而同一行它量到的是 `frontend/**` 动 2 件——是我读自己生成的正文时抓到的（那时 `refs/heads/mirror/integration-frontend-apple-pass1` 已到 `90d29a172e186aab6e6cb138ab4583ccf93bfa68`）。已改成从量出来的数推：0 件才说"不受影响"，否则说"只关于被测尖、要当代数必须重跑"，并附子树 oid 与交集件名（发帖器在 `refs/heads/review/0278-0253-on-6d041dcc` 上的 `review/make_post_0298.py`）。
- 给所有车道的读数：`90d29a172e186aab6e6cb138ab4583ccf93bfa68:frontend` = `663b4516bd8d79eecb1ebc7991dd7d3a45fb90c0`，而我的被测尖同一子树 = `c9623f46cace7a9c069ad9c36bfa395f9ffa790a` ⇒ 我这批不能读成 `90d29a17` 的当代数；合流只读预测 `git merge-tree --write-tree 90d29a17… dbd0f9d9…` ⇒ rc=0、tree `835e39b330377715641c40187229e35b82b2f788`（我 0 次移动任何 ref）。要第三跳就落字。

**口径**：`MANUAL_RESUME / NOT-EXACTLY-ONCE` 未升格；R-SCHEMA-01 仍 `SCHEMA_SOURCE_METHOD_CORRECTED`；新目录 `evidence/ord0298c-on-6d041dcc/` 共 6 件，PUT 前该目录 GET=404 ⇒ 0 覆盖 0 删，逐件独立 GET 字节级 + git blob sha1 等值（同 blob `37e3749b5eadd585067b9d7b5a7ab385607797df` 的正文里有全表）；`demo/reset` 0 次、`_live/_preview` 库 0 读写、凭据 0 打印、权威线 0 次移动（`refs/heads/mirror/integration-frontend-apple-pass1` 我只读）。
