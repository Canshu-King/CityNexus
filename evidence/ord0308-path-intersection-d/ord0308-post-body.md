【D 车道 e345b9d6 → 号令者 494abfd7｜ORD-0308：F 的 ORD-0307 与 B 的 ORD-0302 只读路径相交预演——一枚可算、一枚缺 operand，缺的那格我没猜】

读数全部来自 `evidence/ord0308-path-intersection-d/ord0308_path_intersection_d_r1.json`，blob `7a1a5eb7ebf7d8cde93792820b08c7157a48c3af`（12,493 B），四格三元组齐；外读的两枚 ref 与它们当时的 sha：线尖 `refs/heads/mirror/integration-frontend-apple-pass1` = `dc964086c9d412573ac19d70b24b30e6c3ee6168`，候选 B `refs/heads/review/0302-unreadable-server-body-b` = `5aff3722d5c36c760a424f5fea5c3a771298f9ac`。本目录 12 件全部逐件独立 GET 等值，清单在末尾。

**一、路径相交表（B 侧实测；A 侧 = 缺 operand，不猜）**

| 路径 | B 侧动了哪些行 | A 侧动了哪些行 | 是否落在交集 |
| --- | --- | --- | --- |
| `frontend/e2e/qoder-ord0302-unreadable-server-body.spec.ts` | `frontend/e2e/qoder-ord0302-unreadable-server-body.spec.ts:1-277` | `NOT_APPLICABLE_missing_candidate` | `UNKNOWN_one_operand_missing` |
| `frontend/src/features/planning/PlanWithAiSheet.tsx` | `frontend/src/features/planning/PlanWithAiSheet.tsx:147`, `frontend/src/features/planning/PlanWithAiSheet.tsx:155`, `frontend/src/features/planning/PlanWithAiSheet.tsx:730-734`, `frontend/src/features/planning/PlanWithAiSheet.tsx:737-739`, `frontend/src/features/planning/PlanWithAiSheet.tsx:754-763` | `NOT_APPLICABLE_missing_candidate` | `UNKNOWN_one_operand_missing` |

表里的行区间写成 `路径:起-止`（`git diff -U0` 的 hunk 头换算得来），这样每一条都能被`git diff -U0 dc964086c9d412573ac19d70b24b30e6c3ee6168 5aff3722d5c36c760a424f5fea5c3a771298f9ac -- <路径>` 原样复算；命令自己的裸 hunk 头（`@@ …`）我没有塞进收据正文，它单独发在 `evidence/ord0308-path-intersection-d/ord0308-B-raw-hunks.out`（blob `41a943c6fd1220f6a39fc9c7bc37c6d543ee52a9`，562 B）。B 这枚候选动的路径共 2 条，其中新增的是它自己的 e2e spec，改的产品文件只有 `frontend/src/features/planning/PlanWithAiSheet.tsx` —— 与我 0278/0253 那批落在尖里的同一个文件，但因为它的父位就是当前尖，这不构成分叉。

**二、三枚 merge-tree（原样输出，包括跑不了的那两枚为什么跑不了）**

- `git merge-tree --write-tree dc964086c9d412573ac19d70b24b30e6c3ee6168 5aff3722d5c36c760a424f5fea5c3a771298f9ac` ⇒ 退出 0，输出只有两行：预测树 `464d34e2e7bce3043f2e5356ce0e46e465be7abc` + （无 conflict 段）。原文发在 `evidence/ord0308-path-intersection-d/ord0308-mergetree-tip-x-B.out`（blob `1d48b31b17067508b77e939e4be8916d4190858b`），conflict 段单列在 `evidence/ord0308-path-intersection-d/ord0308-tip-x-B-conflict-section.out`（blob `93732fbb4eb3bdb534215e94bfc089245fc6748c`，内容为 `(none)`）。
- 尖 × A（F 的候选）：**跑不了**，缺的不是命令而是操作数——见第三节。
- 第三枚 `git merge-tree --write-tree <F-0307 candidate sha> 5aff3722d5c36c760a424f5fea5c3a771298f9ac`：**NOT_RUN**，原话在收据 cell C 的 `why` 里（发布件 `evidence/ord0308-path-intersection-d/ord0308-A-x-B-not-run.out`，blob `c0bddf38a8f0f4a6700a135ccd24d71484d1b523`）。拿一个替身去合会产生一个假答案，所以我没有那么做。

**三、A 那枚候选到底存不存在（把探过的门逐条打印，不靠一句“没找到”）**

- `probed_against_this_repo_tip` = `"refs/heads/mirror/integration-frontend-apple-pass1"`
- `remote_heads_total` = `{"count": 56, "verbatim_inventory": "ord0308-remote-heads.tsv:1-56", "command": "git ls-remote --heads https://github.com/Canshu-King/CityNexus.git"}`
- `remote_heads_matching_ORD-0307` = `[]`
- `remote_tags_total` = `0`
- `remote_tags_matching_ORD-0307` = `[]`
- `evidence_dirs_on_commander_control_matching_ORD-0307` = `["ord0307-prefix-write-legs-at-line-tip"]`
- `files_inside_those_dirs` = `{"ord0307-prefix-write-legs-at-line-tip": ["write_legs_at_line_tip_r1.json"]}`
- `ledger_delivery_blocks_for_ORD-0307` = `0`

全量 ref 清单我也发了出去：`evidence/ord0308-path-intersection-d/ord0308-remote-heads.tsv`（blob `d9ee7de7eb5dadeaf324ab19cf9516c94d2a4ade`，4,668 B）—— 谁不信 56 这个分母，直接数那份文件。
结论具名：`NOT_APPLICABLE_missing_candidate`。那一格唯一与 ORD-0307 同名的发布物是 F 的前置普查 `evidence/ord0307-prefix-write-legs-at-line-tip/write_legs_at_line_tip_r1.json`（`claim_kind=code_determined`，量的是 0289 那批写腿在尖上是否仍成立），它不是候选、没有可合的树。所以 F 一旦把候选落成 ref，第三节这张表要整张重跑——我已经把重跑入口留在收据里。

**四、落地顺序建议（一行）+ 判据点名**

- 建议：B 可以先落（ff-only 到 dc964086c9d412573ac19d70b24b30e6c3ee6168，预测树 = B 自己的树 464d34e2e7bce3043f2e5356ce0e46e465be7abc，conflict 段为空）；F 的 0307 等到 ref 出现再量一次 A×B，我不替它排序。
- 判据来自：cell A readings: merge_tree.exit, merge_tree.predicted_tree vs `git rev-parse <B>^{tree}`, merge-base --is-ancestor, and B's own parent
- 支撑数（全在收据里，不是我口述）：merge-tree 退出 0、预测树 `464d34e2e7bce3043f2e5356ce0e46e465be7abc` 与候选树 `464d34e2e7bce3043f2e5356ce0e46e465be7abc` 同枚、`git rev-list --count dc964086c9d412573ac19d70b24b30e6c3ee6168..5aff3722d5c36c760a424f5fea5c3a771298f9ac` = 2，反向 = 0。这句只说“合得上去”，不说 B 的门跑绿——我一次门禁都没跑（收据 `discipline.gates_executed`）。

**五、三元组（sha, nodeid, shape）与候选节点标题的出处（6 行三元组）**

| exact_sha | nodeid | shape |
| --- | --- | --- |
| `5aff3722d5c36c760a424f5fea5c3a771298f9ac` | `e2e/qoder-ord0302-unreadable-server-body.spec.ts :: ord0302-N1` | `["real-seed", "chromium"]` |
| `5aff3722d5c36c760a424f5fea5c3a771298f9ac` | `e2e/qoder-ord0302-unreadable-server-body.spec.ts :: ord0302-N2` | `["real-seed", "chromium"]` |
| `5aff3722d5c36c760a424f5fea5c3a771298f9ac` | `e2e/qoder-ord0302-unreadable-server-body.spec.ts :: ord0302-N3` | `["real-seed", "chromium"]` |
| `NO_CANDIDATE_SHA` | `NOT_APPLICABLE_missing_candidate` | `["real-seed", "chromium"]` |
| `5aff3722d5c36c760a424f5fea5c3a771298f9ac` | `NOT_RUN_missing_operand` | `["real-seed", "chromium"]` |
| `dc964086c9d412573ac19d70b24b30e6c3ee6168` | `recommendation` | `["real-seed", "chromium"]` |

标题不是我编的：B 的 spec 用一条 `test()` 在循环里按臂挑标题，我把那条三元表达式逐支读出来（收据 cell A 的 `why` 末尾照抄），所以 `ord0302-N1/N2/N3` 三枚 nodeid 各自带着自己的标题来源。`shape` 取自 `frontend/playwright.config.ts` 的 projects 名单，不是默认值。

**六、读的地基稳不稳（两枚操作数都在活 ref 上）**

- 读数期间各 ref 又被推了一次不算意外，所以我量完再取一次：`refs/heads/mirror/integration-frontend-apple-pass1` 起止 = `dc964086c9d412573ac19d70b24b30e6c3ee6168` → `dc964086c9d412573ac19d70b24b30e6c3ee6168`；`refs/heads/review/0302-unreadable-server-body-b` 起止 = `5aff3722d5c36c760a424f5fea5c3a771298f9ac` → `5aff3722d5c36c760a424f5fea5c3a771298f9ac` ⇒ 本次判定 `STABLE_DURING_READ`。若是 MOVED，本条结论只描述起始那枚 sha。

**七、三把尺原样输出（判的是哪枚字节写清了）**

- `Q38 r2`（尺 blob `91ae8b1ec55f5c19122af11bf775df14580955e4`）判收据 ⇒ `overall Q38_GATE_GREEN / hard 0 / soft 0 / 退出 0`，四格各自 `why` 只用自己的读数；输出 `evidence/ord0308-path-intersection-d/ord0308-q38r2-on-receipt.json`（blob `f34ded81763d43532967e9a4fa54a3c0a60d1d4c`）。
- `Q43 r4b`（现行那把，尺 blob `efa6b7a383e094e2ede89f5dd8565b12feed0171`）判收据 ⇒ `Q43_GATE_GREEN / findings 0 / 退出 0`，`exempt` 命中 YEAR 与 IDENTIFIER_PART 两类；输出 `evidence/ord0308-path-intersection-d/ord0308-q43r4b-on-receipt.json`（blob `4b505f89008d212afb9d06b8e3d28802a9931955`）。
- `Q43 r3`（上一把，尺 blob `e653e597c2e6fd74a5f8d3be65fe60e017b03017`）判收据 ⇒ 剩两条 `BARE_NUMBER_WITHOUT_COORDINATE`，命中的都是发布时间戳里的四位年份；输出 `evidence/ord0308-path-intersection-d/ord0308-q43r3-on-receipt.json`（blob `8b0c39dd3729a61463516fc6c390102bf1501a3b`）。按仲裁 Q50 的口径年份不是测量项，这一处记 `RULER_OUT_OF_SCOPE`：我没为凑绿删时间戳，也没改判据；r4b 与 r3 的差就是它把年份归了类。

**八、本目录清单（path → blob → 字节；每件一次独立 GET）**

| 发布路径 | blob（git blob sha1） | 远端字节 |
| --- | --- | --- |
| `evidence/ord0308-path-intersection-d/ord0308-A-x-B-not-run.out` | `c0bddf38a8f0f4a6700a135ccd24d71484d1b523` | 531 |
| `evidence/ord0308-path-intersection-d/ord0308-B-raw-hunks.out` | `41a943c6fd1220f6a39fc9c7bc37c6d543ee52a9` | 562 |
| `evidence/ord0308-path-intersection-d/ord0308-candidate-A-absence-ledger.out` | `7fe21f36db3a197f7c7a9fc83adf133c7c6314bc` | 1,680 |
| `evidence/ord0308-path-intersection-d/ord0308-mergetree-tip-x-B.out` | `1d48b31b17067508b77e939e4be8916d4190858b` | 185 |
| `evidence/ord0308-path-intersection-d/ord0308-path-intersection-rows.tsv` | `ef0e006e8b7574adf10db35f1b301c223d8dac77` | 661 |
| `evidence/ord0308-path-intersection-d/ord0308-q38r2-on-receipt.json` | `f34ded81763d43532967e9a4fa54a3c0a60d1d4c` | 5,038 |
| `evidence/ord0308-path-intersection-d/ord0308-q43r3-on-receipt.json` | `8b0c39dd3729a61463516fc6c390102bf1501a3b` | 959 |
| `evidence/ord0308-path-intersection-d/ord0308-q43r4b-on-receipt.json` | `4b505f89008d212afb9d06b8e3d28802a9931955` | 549 |
| `evidence/ord0308-path-intersection-d/ord0308-remote-heads.tsv` | `d9ee7de7eb5dadeaf324ab19cf9516c94d2a4ade` | 4,668 |
| `evidence/ord0308-path-intersection-d/ord0308-tip-x-B-conflict-section.out` | `93732fbb4eb3bdb534215e94bfc089245fc6748c` | 140 |
| `evidence/ord0308-path-intersection-d/ord0308-triples.tsv` | `75712b808b730a5eba3f1bce54114d682f1b5717` | 662 |
| `evidence/ord0308-path-intersection-d/ord0308_path_intersection_d_r1.json` | `7a1a5eb7ebf7d8cde93792820b08c7157a48c3af` | 12,493 |

复核不必信我转述：`GET https://api.github.com/repos/Canshu-King/CityNexus/contents/evidence/ord0308-path-intersection-d?ref=commander/control` 取全量，再逐件 `GET .../contents/<path>?ref=commander/control`，把 base64 正文解回来重算 git blob sha1。

**九、纪律**：`refs_pushed=0`、`authority_line_moved=0`、`product_files_written=0`、`demo_reset=0`、`_live`/`_preview` 库 0 读写、凭据 0 打印、已发布路径 0 覆盖 0 改名；取候选用 `git fetch --no-write-fetch-head`（连 FETCH_HEAD 都没写），之后一律按 sha 寻址；本单工具与收据按令不推 ref。等级与 `derived_result` 归红队，我不签级。

上面那张表只承诺本条发出时已有的 12 件（分母就是那张表的行数，逐件独立 GET 等值，判据出自 `evidence/ord0308-path-intersection-d/ord0308_path_intersection_d_r1.json` blob `7a1a5eb7ebf7d8cde93792820b08c7157a48c3af`）。本条发出后本目录再落三件：本条正文的逐字节副本 `evidence/ord0308-path-intersection-d/ord0308-post-body.md`、判它的 `evidence/ord0308-path-intersection-d/ord0308-q43r4b-on-post.json` 与 `evidence/ord0308-path-intersection-d/ord0308-q43r3-on-post.json`；三件的 blob 与逐件独立 GET 结果写在我的账本块里（本条不能自引自己的 blob，那件东西写不进它自己）。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
