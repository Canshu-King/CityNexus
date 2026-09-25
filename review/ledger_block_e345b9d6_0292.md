### SESSION=e345b9d6 @2026-09-25 08:0x+08 —— **ORD-0292 交：七枚反突变臂在冻结尖 `067170454…` 上重跑完，逐臂带三元组＋同键前件＋每轮还原回验；不签级**
（总线正文 = comment 5824352738。这一段**没有任何产品改动**，`frontend/**` 一个字节都没动；只有两枚 `review/**` 脚本在工具 ref 上。）

**冻结**：`refs/heads/review/0278-0253-on-45b0a5e` ⇒ 外读回验行 `0671704546f9c9ea1d1b57627b059124c7800803	refs/heads/review/0278-0253-on-45b0a5e`（`git ls-remote` 原样）。**这一段之后我不再推它**；后续任何新东西另开 ref。我本地那枚同名标签停在 `f86d24e9…`（GitHub 已是 `0671704…`），两尖之间 `git diff --name-only f86d24e9… 0671704…` = 2 件且全在 `review/**`、`-- frontend` 命中 0 件 ⇒ 被测字节一致，落地请按 GitHub 那枚尖取。
**工具 ref（新开的）**：`refs/heads/review/0292-arm-receipt-tooling` ⇒ 外读尖 `a031308cfae7e920dc3438daf1d8fdac905ca12e`；收据点名的跑臂工具尖 = `73b22fb6a8d59e6179acf517bac8b911c638c519`，`git merge-base --is-ancestor 73b22fb6a… a031308cf…` ⇒ True（此后这枚 ref 只会继续装 `review/**` 文本，祖先链恒可达）。臂只改 `frontend/**`，故跑臂前双向量过：`git diff --name-only 0671704… HEAD -- frontend` = **0 件**、`git status --porcelain -- frontend` = **0 行**、三枚被改文件与工作树对 `0671704…` 的 object store 逐件 sha256 等值 **3/3**。

**绿轮（同代，不沿用上一代）**：`ord0292-gate-round-0671704.json` ⇒ `verdict=GREEN`、`problems=0`、三元组 **14 条且 `exact_sha` 全 = 冻结尖**（脚本坐在 `c893f860…`，两尖 `frontend/` 差 0 件；生成器现在把三元组钉在被测树而不是"脚本所在commit"，且这个差是量出来的、非空即中止）。四枚门四条 run：`run292457 / run292486 / run292519 / run292542`。收集数重测：Playwright `Total: 15 tests in 5 files` ⇒ 判据节点 **14**（rc=0）；后端 `1232 tests collected in 2.43s` ⇒ **1232**（rc=0，解释器 `.venv` 3.12.14）。冻结尖相对落地尖 `45b0a5e28…`：descendant=True、领先 **13** 笔；落地分组 **17 件 = 主线 7（`frontend/**`）+ 车道脚手架 10（`review/**`）**。

**七枚臂**：`arms-0292c-0671704.json` ⇒ `claimed_result` **KILLED 7/7**（自宣；`derived_result`、direct/collateral、等级全归红队，我不签级）。每臂三件新东西都齐了：
① 逐臂 `(exact_sha, nodeid, run_shape)`，`nodeid` 与绿轮逐字同形（`sha :: e2e/<spec> :: <标题>`），`run_shape` 里 cwd = 该 `nodeid` 的 root、端口、run 号、当场新建的 `_run<id>.db` 全部点到能点开；
② 同键前件：`0671704… :: <spec> :: <owner>` 这一枚键在绿轮里读到的就是 `ok`，且本批自己的 baseline run 读 GREEN —— 7/7 成立，"击杀"只能读成**这一代这一枚节点**的红；
③ 每轮还原回验：`before == after == 冻结树 blob` 的 sha256 三点摘要逐臂内嵌（不再只跟"我自己开工前的工作树"比），`restored_to_tested_tree_bytes` **7/7**，`treeUnchangedByThisRun=True`，14 次 spec run（`run293792…run294113`）。
归属读数（只描述我量到的，不裁决）：**4 枚独占红**（K278 那四枚各只红自己 owner）；**3 枚连带**（K253 那三枚都同时红 `0253` 三节点，`exclusiveToOwner=false`）。

**我自己这一轮的三处账（都具名，没抹）**：
1. 首跑 `0292-on-0671704` 把 `nodeid_root`/`cwd` 写成了反斜杠形式（`D:\moodle\…\frontend`），与绿轮的 `D:/moodle/…/frontend` 不同形 ⇒ 所谓"同键"只是形似；重跑 `0292b`。
2. `0292b` 的 run_shape 拼出 `_runrun293816.db` 这个**不存在的文件名**（runner 的 id 已含 `run`）⇒ 改成从 run_id 派生库名并**去盘上找它**，找不到就把那一判读成 `INVALID_STACK`（既不是击杀也不是存活）；第三次 `0292c` 才是发布的那一枚，14 组 (db, log) 名逐个 `os.path.exists` 过。
3. 发帖器 `short()` 第一版把 `ord0278` 切成 `d0278`，另一次删空行把 `return 4` 和下一句粘成了 SyntaxError ⇒ 两处都是**回读产出**抓到的，已补双向自测（必须留 `0278-` 前缀；非 `ord…` 标题原样返回）。

**新路径外读**：`commander/control` @ `evidence/ord0292-on-frozen-0671704/` ⇒ `gate-round-0671704.json` blob `0160e8db0295e600b44a5e5ff021d5da507bc7d2`（36,615 B）、`arms-0292c-0671704.json` blob `cb9270671adc323ff2816d406739e04518b9d05f`（35,661 B），逐件 PUT 后独立 GET **BYTE-LEVEL MATCH**（远端字节 == 本地字节 == git blob sha1）。发布前先证新目录：该路径 GET=404、`evidence/` 顶层 144 项里 `ord0292*` 命中 **0** ⇒ 0 覆盖 0 删。上一代那枚 `evidence/ord0278-0253-on-landed-f86d24e/` 与 06:0x 的 `…-d702d13/` 原样在架。
本地留痕（未发布、不进任何判据）：`ord0278-0253-arms-0292-on-0671704.json`（① 那枚错的分隔号）、`…-0292b-on-0671704.json`（② 那枚错库名）；v1/v2/v3 三枚旧臂收据也原样留着，各归各的坐标。

**口径与队列**：`MANUAL_RESUME / NOT-EXACTLY-ONCE` 未升格（ORD-0272 未全落地）；R-SCHEMA-01 仍 `SCHEMA_SOURCE_METHOD_CORRECTED`（行全经产品 API 造，判据只看渲染文字/HTTP/线格式，无 DDL 重放、无直调 `ensure_schema()`）。按你给的顺序：0292 已交 ⇒ **等 0280 落地才轮到我 re-parent**；ORD-0288 产码继续按住（与 B 同一枚文件）；ORD-0266 `db6ac1d` 仍 DELIVERED/NOT-LANDED 等窗口。纪律读数：`demo/reset` 0 次、`_live/_preview` 库 0 写、凭据 0 打印、权威线 0 次移动。
