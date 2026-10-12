# revolution-archive —— revolution lab 独有资产的归档区

主人 2026-10-12 令：把 revolution lab 全量吸收，一根不少，融会贯通。执行件是权威尖上的`docs/REVOLUTION_ABSORPTION_FIVE_YEAR_PLAN.md`。本目录就是那份计划里 2026Q4 第0季那一格（正文第 49 行）落下来的东西：族B 八枚 prep 枝的 `evidence/gpt-assist/` 评审产物并入 `docs/revolution-archive/gpt-assist/`。纯搬运，零产品码。

写这份文档与拼这棵树的代：权威尖 `3bf57cc0e15ee4defc833e3a3c7463d0be0d2f60`（`git -C D:/moodle/CityNexus ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1` 现取，本地 tracking 不算尖）。

## 一、搬运规矩（三条都可复算，不需要信我的措辞）

1. **一字节不改。** 本目录每一枚归档文件在树里挂的就是它在来源枝上那枚 blob 本身，blob id 逐枚相同（下表 blob 列）。git 的 blob id 由内容算出，所以这条等式本身就是保真的证明；拼树全程走 `git mktree`／`git commit-tree`，没有检出、没有覆写、没有换行符转换。
2. **只换路径。** `evidence/gpt-assist/<轮次目录>/<文件>` 换成 `docs/revolution-archive/gpt-assist/<轮次目录>/<文件>`，轮次目录原样保留：一轮一档，谁也不盖谁。
3. **该没动的都没动。** 产品码 0 行；`docs/REVOLUTION_ABSORPTION_MANIFEST.tsv` 一个字节没改（吸收代由号令者点，车道不自封）；八枚来源枝一字未改、未删、未 rebase；本目录之外的任何在飞文件没碰。

## 二、这一批纸是什么

八枚枝是 R6 到 R7.5 那条外部评审线：它们共同的本族叉口是 `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`（逐枚把该枝尖与现尖 `3bf57cc0e15ee4defc833e3a3c7463d0be0d2f60` 走 `git merge-base`，八次同值），在那之上每枚只往 `evidence/gpt-assist/` 放东西。对账表把这八行记在第 32、33、34、35、36、37、38、39 行，八行的 prod 列现读全为 0，也就是这八枚枝对现尖的独有产品码是零——所以本目录里没有一行代码，只有纸。

合计 28 个文件、1414 行、65763 字节。五类东西：轮次前言与交接纸、外部审计判语、给对方的执行契约与任务书、证据契约与取证记录、以及从未落地的补丁意向与 RED 草稿与诊断探针。

它们值得留的理由不是"码"，是"当年怎么判的"：五年计划第五年要把 revolution 这个词消解进主线语汇，靠的就是这套判定原文与那份身份契约的措辞。

## 三、为什么现尖上没有它（四条同时成立，说明这是设计不是丢件）

| 判据 | 现读 | 复算命令 |
|---|---|---|
| 权威尖上 `evidence/gpt-assist/` 这个路径下有几个文件 | 0 个 | `git ls-tree -r --name-only 3bf57cc0e15e -- evidence/gpt-assist` 回 0 行 |
| 八枚枝里有几枚是权威尖的先祖 | 0 枚 | 逐枚 `git merge-base --is-ancestor <枝尖> 3bf57cc0e15e`，八次全为否 |
| 28 枚 blob 在权威尖全部 blob 里命中几个 | 0 个（内容级去重，不靠文件名） | `git ls-tree -r --format=%(objectname) 3bf57cc0e15e` 取 8912 枚 blob 与本轮 28 枚取交集 |
| 来源枝自己怎么声明（逐字取自那一枚，行号是现读的） | 写下就声明这是协调枝 | `evidence/gpt-assist/20260923/R6_H11_R61_PREP.md` 第 3 行：「This branch is **coordination/evidence only**. It is based on the repository's current default branch and is **not** the Revolution Lab R6 product source.」；`evidence/gpt-assist/20260923/proposed_test_r61_explicit_role_boundary.py` 第 3 与第 4 行（该行原文到此处断行）：「# PROPOSED R6.1 RED TESTS ONLY.」「# Store under evidence on this coordination branch. Copy into the exact R6.1」 |

现尖登记的 13859 个路径里，`evidence/gpt-assist` 下面一个都没有（就是上表第一条判据）。这些评审产物从写下那一刻就不打算进产品线——RED 草稿要等独立评审点头才复制进当轮的 worktree，而那条 worktree 长在族A 的累积线上，不在这八枚枝上。所以"现尖没有"是当初的规矩。第0季的令要求一根不少，于是纸收进主线看得见的位置，码仍然一行不动。

## 四、逐枚清单（八节，一节一枚来源枝）

### 4.1 refs/heads/gpt/revolution-r6-h11-r61-prep-20260923

- 枝尖 `187263c67a5348d565adfc5ad8f01877fb56267d`｜本族叉口 `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`｜叉口之上 4 笔提交｜是不是权威尖的先祖：否｜这一档 3 个文件、214 行
- 源路径前缀 `evidence/gpt-assist/20260923/`；归档路径前缀 `docs/revolution-archive/gpt-assist/20260923/`（表里只写文件名，两枚前缀一一对换）

| 文件 | 行数 | 字节 | blob（源与归档同一枚） | 引入它的提交 | 这一枚是什么 | 现尖为什么没有它 |
|---|---|---|---|---|---|---|
| R61_MINIMAL_PATCH.diff | 32 | 1325 | `221e3f5097c3d471497c5ae7287f832f73242419` | `187263c67a5348d565adfc5ad8f01877fb56267d` | R6.1 的最小补丁草图：往 services.py 的错误词表加一枚 PLACE_ROLE_NOT_VISIT_ELIGIBLE | 意向补丁：纸上的 diff，采纳动作发生在族A 那条累积线 |
| R6_H11_R61_PREP.md | 51 | 3050 | `e5894dc3b9c074bccb7d592aeb0ff915a555fbc9` | `38a7114982de86321c77f6bff46f2fccda3bc1af` | R6 到 H11 到 R6.1 的交接前言；冻结的 R6 实验候选写在其正文里，并声明本枝只做协调与证据 | 协调纸：它第一段就写 coordination/evidence only，从没走产品线的门 |
| proposed_test_r61_explicit_role_boundary.py | 131 | 4689 | `7dd420b48fe2454a6b53d1031ae028eb099370e6` | `af7ad2e22391523fb5e226c73b80a43a6809710d` | 三组 R6.1 的 RED 草稿：住宿角色越界要拒、零持久化、拒绝必须早于 mobility 采集 | RED 草稿：正文自述要等独立 H11 点头才复制进 R6.1 worktree |

### 4.2 refs/heads/gpt/revolution-r61-h12-r62-prep-20260923

- 枝尖 `9fd3d221214901ba372924d60a8e9e0bfd859938`｜本族叉口 `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`｜叉口之上 6 笔提交｜是不是权威尖的先祖：否｜这一档 5 个文件、83 行
- 源路径前缀 `evidence/gpt-assist/20260923-r61/`；归档路径前缀 `docs/revolution-archive/gpt-assist/20260923-r61/`（表里只写文件名，两枚前缀一一对换）

| 文件 | 行数 | 字节 | blob（源与归档同一枚） | 引入它的提交 | 这一枚是什么 | 现尖为什么没有它 |
|---|---|---|---|---|---|---|
| CODEX_NEXT_TASK.md | 10 | 1804 | `c6abf15a67b2213997f2a0d9374ddabb53294d95` | `c05fb7d4aa3cd1778e7fa04e9c29998bc7398c4e` | 给 Codex 的下一格任务书：冻结实验源、请 H12 独立跨测、把该走的臂逐条列全 | 任务书：评审侧指令，产品线不收录指令 |
| H12_HANDOFF.md | 8 | 689 | `f83a71553963e2a8a6ee8ee6ebb7b2321e91987f` | `9fd3d221214901ba372924d60a8e9e0bfd859938` | 交给独立 Harness H12 的交接：目标那一枚逐字给出，并声明 H11 只是 R6 的上下文、不是 R6.1 的证明 | 交接纸：写给另一个评审者的话，本就不为进线 |
| R61_EXTERNAL_AUDIT.md | 29 | 2493 | `31395874f3cd0c12b7971e32f025890289359264` | `9cddc6428010eb9a4140235947a61dbd4fe55d11` | R6.1 的外部审计判语：RED 检查点上三枚缺陷复现得出，终态报通过数与前端类型检查 | 审计原文：评审判语，主线收的是被审的码 |
| R62_STALE_COMPATIBILITY_MINIMAL.diff | 9 | 320 | `712766624dd40f7cc3b76e72d990c2db9d3900cd` | `4bc966564c0669b2055fae4026cf09c4aa1fbcb9` | 四行的最小补丁意向：过期 cost_minor 从 setdefault 改成直写 | 意向补丁：等 RED 先被证方才采纳，纸本身从不落地 |
| proposed_test_r62_cost_truth_edges.py | 27 | 1136 | `8440f22dc7231d3e0db586817f45b4288b5316de` | `03557c2409defddaeb500b31e8c6c59297324f65` | R6.2 成本真相边界 RED 草稿：四种已核实零成本状态必须仍算已知免费 | RED 草稿：协调枝上待采纳的草稿，未随任何 merge 进线 |

### 4.3 refs/heads/gpt/revolution-r62-r63-prep-20260923

- 枝尖 `1c3a2d019921dbfd2df00ec67085998615780b2e`｜本族叉口 `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`｜叉口之上 4 笔提交｜是不是权威尖的先祖：否｜这一档 3 个文件、298 行
- 源路径前缀 `evidence/gpt-assist/20260923-r62/`；归档路径前缀 `docs/revolution-archive/gpt-assist/20260923-r62/`（表里只写文件名，两枚前缀一一对换）

| 文件 | 行数 | 字节 | blob（源与归档同一枚） | 引入它的提交 | 这一枚是什么 | 现尖为什么没有它 |
|---|---|---|---|---|---|---|
| R62_R63_PREP.md | 56 | 3465 | `7022b343e8670086f19fa5ecbca19014c379f7e4` | `fec637f42a1d193ec0d604e353bd90c5294fc0ab` | R6.2 到 R6.3 的前言：冻结候选、改前 RED 检查点、父代三枚坐标逐枚写全 | 协调纸：轮次前言，产品线不产轮次叙事 |
| proposed_test_r63_anchor_commitment_cost_truth.py | 170 | 6366 | `b2ef64dc18f917e3c58c51a74b8a80b7f6688738` | `3a5e6ac1420cdca62b6340c3b42e0877cabfe6a6` | 这一批里最长的一枚：证 C4 锚点的钱来自 Commitment，而不是 Place 兜底或字面零 | RED 草稿：正文自述要等 R6.3 冻结后才搬进 worktree |
| proposed_test_r63_template_budget_fit_truth.py | 72 | 2583 | `11240128fa63b1a563f8f903e5e59a191edc4b8f` | `1c3a2d019921dbfd2df00ec67085998615780b2e` | 模板候选的 budget_fit 要由候选自身成本与旅程预算推出，不许继承夹具里冻着的分数 | RED 草稿：同上，草稿阶段就停在证据区 |

### 4.4 refs/heads/gpt/revolution-r7-r71-prep-20260923

- 枝尖 `03f8d0e3f0025e6a5c088e87d3ce7d12bc608f4d`｜本族叉口 `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`｜叉口之上 4 笔提交｜是不是权威尖的先祖：否｜这一档 3 个文件、192 行
- 源路径前缀 `evidence/gpt-assist/20260923-r7/`；归档路径前缀 `docs/revolution-archive/gpt-assist/20260923-r7/`（表里只写文件名，两枚前缀一一对换）

| 文件 | 行数 | 字节 | blob（源与归档同一枚） | 引入它的提交 | 这一枚是什么 | 现尖为什么没有它 |
|---|---|---|---|---|---|---|
| CODEX_R71_TASK.md | 39 | 1456 | `54f2c64f0eab791a2828f869b9cbb2c1927d8e5e` | `9720ccc64cc93d3ce2c575f1bb7c94ae843cc582` | R7.1 的执行契约：第一道门就要求 PRE/POST 自取 HEAD、分支与工作树状态 | 任务书：给评审对方的规矩，不是产品行为 |
| R7_R71_PREP.md | 60 | 3291 | `5184d8c2c78eaa62c08e47a6af9a4ca4abeb8928` | `f143ac17c1625180b94a2b091e776d5acb3729ee` | R7 到 R7.1 的前言：R6.3 冻结检查点、贡山实况注水源、以及解析到的那枚供应商身份 | 协调纸：轮次前言 |
| r71_catalogue_eligibility_ledger.py | 93 | 3293 | `8372e2c6f0011e5bdcda098152e2dcc9c7c36dc6` | `03f8d0e3f0025e6a5c088e87d3ce7d12bc608f4d` | 目录资格台账：数一个目的地里有几枚供应商 Place 真能进 AUTO 模板（角色、营业、成本三道门） | 诊断件：只数事实不改事实，产品线不收计数控件 |

### 4.5 refs/heads/gpt/revolution-r71-r72-prep-20260923

- 枝尖 `d1a05785839ad08649c65d48080fd70dbd9446aa`｜本族叉口 `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`｜叉口之上 6 笔提交｜是不是权威尖的先祖：否｜这一档 5 个文件、264 行
- 源路径前缀 `evidence/gpt-assist/20260923-r71/`；归档路径前缀 `docs/revolution-archive/gpt-assist/20260923-r71/`（表里只写文件名，两枚前缀一一对换）

| 文件 | 行数 | 字节 | blob（源与归档同一枚） | 引入它的提交 | 这一枚是什么 | 现尖为什么没有它 |
|---|---|---|---|---|---|---|
| CODEX_R72_TASK.md | 48 | 1981 | `43a99627c9d204b3f89ae3d39be0465186508923` | `bd86685e53a52a8e8a708077e1853be203a1a6d0` | R7.2 是取证轮：明令不许为了让 Mission A 变绿就削弱真相门或改动冻结的产品检查点 | 任务书：评审侧约束 |
| R71_EXTERNAL_AUDIT.md | 45 | 2769 | `145bffb6071f9eb3eb275690db91c87d8c377e87` | `2659604a1039472ad10b8af6c2db0425d1d7ac19` | R7.1 的外部审计判语 FACT_EVIDENCE_INSUFFICIENT：贡山有供应商 Place 却无一合格，Mission A 仍 OPEN | 审计原文：判语，主线收被审的码 |
| R72_ACQUISITION_FRONTIER.json | 26 | 640 | `8aab38dcff62ffb653af0d9e4d83a46fa5b64513` | `6c8e96b3b7685b0d7ab5c8d9a0c29bea01d79758` | 当时手里已握的外部 id 清单（overpass 节点那批），也就是取证的边界在哪 | 取证记录：只记那一刻手里有什么，不进产品事实表 |
| R72_EVIDENCE_CONTRACT.md | 12 | 775 | `7e043144ce596bcbde5276fae91c7a74d3463b85` | `4d938a57e41b2496085a6e7c8afbc96e67f43bec` | 证据契约：产品实现与诊断工具分开绑基线，一条 live 臂该记哪些字段逐项列出 | 契约原文：评审侧的收件规矩 |
| r72_exact_osm_fact_probe.py | 133 | 5102 | `f01feb24bd00697c28751242093367406a85df8c` | `d1a05785839ad08649c65d48080fd70dbd9446aa` | 精确对象 OSM 事实探针；文件头自述 Diagnostic only，既不生成 Place 行也不提升事实 | 诊断件：自述不产产品事实 |

### 4.6 refs/heads/gpt/revolution-r72-r73-prep-20260923

- 枝尖 `c7c5ccbb7d093a43558a94cdc4072586a2de6a5e`｜本族叉口 `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`｜叉口之上 5 笔提交｜是不是权威尖的先祖：否｜这一档 4 个文件、178 行
- 源路径前缀 `evidence/gpt-assist/20260923-r72/`；归档路径前缀 `docs/revolution-archive/gpt-assist/20260923-r72/`（表里只写文件名，两枚前缀一一对换）

| 文件 | 行数 | 字节 | blob（源与归档同一枚） | 引入它的提交 | 这一枚是什么 | 现尖为什么没有它 |
|---|---|---|---|---|---|---|
| CODEX_R73_TASK.md | 23 | 1598 | `a97a363fafe4da2ed621267fb7eb1a45fd4e1d7b` | `00ef4ba408c30bdb439eebf8bc4528e020d0fb4f` | R7.3 任务书：RED 先行，并保留那枚反控——云合 对唯一供应商主名 遂昌县 必须 NO_MATCH | 任务书：评审侧指令 |
| R72_R73_PREP.md | 23 | 1685 | `0262abd13d9c11e9b49866f627bf98898fc663e6` | `9306a47982ec4968321c55f7ba4990ca61484500` | R7.2 交付包的审计：JSON 全部按 UTF-8 解析、清单条数与实有对齐、JUnit 的过败数逐枚点回 | 审计原文：对包的判语 |
| R73_IDENTITY_CONTRACT.md | 20 | 861 | `cb539de6a4eefb5d434a7b55b31c38615937727b` | `e1fcf7cb6fdec7728e45f2c581a11c27efd9c71e` | 身份真相契约：什么算足够证据、什么不算——一枚供应商候选永远不构成身份 | 契约原文：判定标准本身不在主线代码里 |
| r73_provider_candidate_capture.py | 112 | 4196 | `8d423101bd79079763daca30b7613c83f9939fc8` | `c7c5ccbb7d093a43558a94cdc4072586a2de6a5e` | 把 Overpass 成功响应里的完整候选抓下来，供身份契约复核用 | 诊断件：取证捕获器，不落产品行 |

### 4.7 refs/heads/gpt/revolution-r73-r74-prep-20260924

- 枝尖 `d4bdbcbc84abf82caf3322ea87b9df9683d78d8c`｜本族叉口 `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`｜叉口之上 5 笔提交｜是不是权威尖的先祖：否｜这一档 4 个文件、132 行
- 源路径前缀 `evidence/gpt-assist/20260924-r73/`；归档路径前缀 `docs/revolution-archive/gpt-assist/20260924-r73/`（表里只写文件名，两枚前缀一一对换）

| 文件 | 行数 | 字节 | blob（源与归档同一枚） | 引入它的提交 | 这一枚是什么 | 现尖为什么没有它 |
|---|---|---|---|---|---|---|
| CODEX_R74_TASK.md | 23 | 1290 | `78ee88140bbf7236a3818ae7143d5c62a5f398e5` | `987e7ea6096c7bf11763a97fda5aa148822f719f` | R7.4 精确实体任务：云合 保持 NO_MATCH，贡山独龙族怒族自治县 要 RESOLVED，异 id 一律 fail closed | 任务书：评审侧指令 |
| R73_R74_PREP.md | 30 | 2024 | `50b103698aa4cb01f76dc5ff0eef4f70934bce8c` | `68c567f963ec5129c9cb432c04332dcd42e697a4` | R7.3 终态包审计：从基线起产品 diff 只动一处，反向补丁能把旧 blob 复原 | 审计原文：对包的判语 |
| R74_IDENTITY_CORROBORATION_CONTRACT.md | 17 | 884 | `87811430e931e318127cce1e9c720d8633b63058` | `777e52d9591fcd7153dbf90c8edf15c7e6d9d48e` | 佐证契约：唯一 Photon 候选可以触发对同一 OSM 对象的精确读，但后续读不许换成别的实体 | 契约原文：判定标准 |
| r74_nominatim_exact_identity_probe.py | 62 | 3018 | `fcc5d7285858d3a6509da7579757e531f6a0fb17` | `d4bdbcbc84abf82caf3322ea87b9df9683d78d8c` | Nominatim 精确读名证据探针，白名单只放 name 家族那几枚字段 | 诊断件：白名单探针，不写产品状态 |

### 4.8 refs/heads/gpt/revolution-r74-r75-breakthrough-20260924

- 枝尖 `eb165b9737b5ede483a252b2a2e09ac08c669973`｜本族叉口 `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`｜叉口之上 2 笔提交｜是不是权威尖的先祖：否｜这一档 1 个文件、53 行
- 源路径前缀 `evidence/gpt-assist/20260924-r74/`；归档路径前缀 `docs/revolution-archive/gpt-assist/20260924-r74/`（表里只写文件名，两枚前缀一一对换）

| 文件 | 行数 | 字节 | blob（源与归档同一枚） | 引入它的提交 | 这一枚是什么 | 现尖为什么没有它 |
|---|---|---|---|---|---|---|
| R74_R75_BREAKTHROUGH_PREP.md | 53 | 2980 | `f1b7f2cc98fcf70d915713867f3c7cfc48a65498` | `eb165b9737b5ede483a252b2a2e09ac08c669973` | R7.4 到 R7.5 的转向：R7.4 是有用的检查点而不是 Mission A 成功，并把下一轮指向一份临时真行程 | 协调纸：轮次前言 |

## 五、复算入口

把本目录任意一枚文件与它在来源枝上的原件对拍，一条命令就够：

```
git -C D:/moodle/CityNexus cat-file blob <上表的 blob>
```

同一条命令对来源枝上的 `evidence/gpt-assist/...` 与归档里的 `docs/revolution-archive/gpt-assist/...`取回的字节逐枚相同——因为树里挂的是同一枚 blob，而不是我重写的另一枚。

