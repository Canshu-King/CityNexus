# ORD-0509 落单建议件（r5）：亮档 3.62 那三处，我建议落「乙」——并给出三代产物的复核读数

CMDR 02:45 记在我名下那一手：把「甲 / 甲-强 / 乙，要落哪条请另发一令」里我推荐的那条写成一行的落单建议交上去。
本件只做两件事：把那一行写清楚（第 3 节），以及为它补上现尖自己那代产物上的读数（第 1、2 节）。
**我这一手产品字节 0 枚**：只加本件这一枚文件，`frontend/src` 里 0 枚改动，等您的令。

## 0. 先证代次（我量的是哪一枚，线上在发哪一枚）
- 写件这趟 `git ls-remote --refs origin refs/heads/mirror/integration-frontend-apple-pass1` 现读的现尖是 `6a06a0bb93ffb7e9462b24b611f4ce214ea04f55`；我的构建、闸与全部读数取在它直接的上代 `25d1b2e69bfffd39157d3bcc804b20be9d89e2b4`（本件提交所在的树）。两代之间 `frontend/src` 一枚都没动。
- 两代同源：三屏相关的 7 枚源在两代之间逐枚 blob 相同（现读），三条规则的坐标在两代上 `git grep` 各取一次也逐枚相同——所以本件引用的行号对现尖有效，而读数属于 `25d1b2e69bfffd39157d3bcc804b20be9d89e2b4` 那一代。
- 再往前两代：`06ad00b0267c2bef08d4cdcbae2e5a206ded8666`（day25）、`4fac49f371da0820393d038700bddddafd1176d1`（day24）。
- 我从 `25d1b2e69bfffd39157d3bcc804b20be9d89e2b4` 这代跑两把构建门：`tsc -p tsconfig.typecheck.json --noEmit` 退 0、`npx vite build` 退 0；产物入口 `index-DeyXt9ON.js`、1620478 字节 B，我这台私有静态口（:4892，命令行带 `--outDir dist_day26`）回读的服务字节与磁盘字节逐字节相同（同一枚 sha1 5235315cdd3a76c3ba302c583edebd72d5fe3d84）；契约尺现读 formal 175 条 / runtime 175 条，HTTP 的 plan 与库内 plan 同为 55523d40-cafe-5bd2-b30a-de057ec7a839。
- :4783 此刻仍在发的是上一代（day25）那枚入口 `index-DeyXt9ON.js`（1620076 字节 B、sha1 04a7ba87c345e824e321d2751626bc18e14e0d5e，与本车道 `dist_day25` 磁盘产物逐字节相同）；它这次发的 CSS `index-BeJMb-k7.css`（sha1 bbb5e0be183eee21aa0ff1f52046ce3a1d280162）与本趟现尖产物里同名那枚**逐字节相同**。所以下面的对比是：基线读数在两代产物上各取一次，候选读数也在两代上各取一次。
- day25 -> 现尖之间 `frontend/src` 只动了 3 枚：`PlanRankingPanel.tsx`、`journeyTrash.ts`、`displayVocabulary.ts`；这 3 枚都不是那三屏的主人，也不是我要改的那三条规则所在文件（`styles.css`、`sharedJourney.css`、`trip-poster.css`）。
- 那三屏相关的 7 枚源在 day24 -> 现尖之间逐枚 blob 相同（UNMOVED）：`styles.css`、`design-tokens.css`、`v8PanelRegistry.tsx`、`SharedJourneyPanel.tsx`、`sharedJourney.css`、`SharedPosterScreen.tsx`、`trip-poster.css`。
- 盘面只走产品自己的门：reset -> prepare-scenario -> scene 答 200 / 200 / 200；站点 6 枚、有坐标 6 枚、少 0 枚；supply.state=NOT_ASKED；错头当 reset 头用 -> http 403；库 `_r5_r12.db`。

## 1. 基线：三屏在两代产物上的读数（390x844，同一把仪表，两臂 REFUSALS 皆空）

| 屏 | 档 | day25（`dist_day25`） | 现尖（`dist_day26`） |
|---|---|---|---|
| nav_drawer | light | 4 不合格/18 枚、最差 3.62 | 4 不合格/18 枚、最差 3.62 |
| nav_drawer | dark | 0 不合格/18 枚、最差 4.66 | 0 不合格/18 枚、最差 4.66 |
| shared_journey | light | 6 不合格/30 枚、最差 3.62 | 6 不合格/30 枚、最差 3.62 |
| shared_journey | dark | 0 不合格/29 枚、最差 5.22 | 0 不合格/30 枚、最差 5.22 |
| long_image_poster | light | 1 不合格/22 枚、最差 3.62 | 1 不合格/22 枚、最差 3.62 |
| long_image_poster | dark | 0 不合格/22 枚、最差 4.82 | 0 不合格/22 枚、最差 4.82 |
| map_facts_card | light | 0 不合格/3 枚、最差 5.97 | 0 不合格/3 枚、最差 5.97 |
| map_facts_card | dark | 0 不合格/3 枚、最差 4.66 | 0 不合格/3 枚、最差 4.66 |

- 两代之间：三屏亮档不合格枚数与最差对比逐枚相同（4、6、1 vs 4、6、1）；暗档两代都 0 枚不合格。
- 屏上文字枚数（分母）：抽屉 18 vs 18、长图 22 vs 22、分享接收 30（亮）/29（暗）vs 30（亮）/30（暗）（前两者两代逐枚相同；只有分享接收那格在 29/30 之间浮动）。day24 是 29（亮）/29（暗），而同一代四臂之间这枚本来就在 29/30 浮动（day24 的 20 臂对比件已具名记过）——行数浮动不是判据，三屏的不合格枚数与最差对比三代逐枚相同。
- 1280x900 那形照旧：分享屏与长图屏同样只红在亮档（现尖 6 不合格/34 枚、最差 3.62 / 1 不合格/22 枚、最差 3.62），抽屉在那形点不开主体，具名 NOT_REACHED_BY_SHAPE。
- 最差那枚的色值三代相同：`--cn-ink-tertiary` 的亮档声明（对白底 WCAG 现算 3.62，门槛 4.5）。

## 2. 候选读数：乙（只改这三条规则的 color）在两代产物上各跑一次

| 屏 | 档 | 基线（现尖） | 注入乙（现尖） | 注入乙（day25 产物） |
|---|---|---|---|---|
| nav_drawer | light | 4 不合格/18 枚、最差 3.62 | 0 不合格/18 枚、最差 4.82 | 0 不合格/18 枚、最差 4.82 |
| nav_drawer | dark | 0 不合格/18 枚、最差 4.66 | 0 不合格/18 枚、最差 4.66 | 0 不合格/18 枚、最差 4.66 |
| shared_journey | light | 6 不合格/30 枚、最差 3.62 | 0 不合格/30 枚、最差 5.07 | 0 不合格/29 枚、最差 5.07 |
| shared_journey | dark | 0 不合格/30 枚、最差 5.22 | 0 不合格/30 枚、最差 5.22 | 0 不合格/29 枚、最差 5.22 |
| long_image_poster | light | 1 不合格/22 枚、最差 3.62 | 0 不合格/22 枚、最差 4.66 | 0 不合格/22 枚、最差 4.66 |
| long_image_poster | dark | 0 不合格/22 枚、最差 4.82 | 0 不合格/22 枚、最差 4.82 | 0 不合格/22 枚、最差 4.82 |

- 两代注入读数逐枚相同，且暗档在乙下逐枚与基线相同（4.66、5.22、4.82 -> 4.66、5.22、4.82）。
- 形制：注入的是作者样式（`addStyleTag`，带 `:root[data-theme="light"]` 前缀与 ID 特异性），不是重建的产物；上一单 r1 那趟因为漏了 ID 选择器被特异性压住，那 4 不合格/18 枚 只记仪器错，本轮没重犯（两臂都过）。
- 甲（`--cn-ink-tertiary: #76767b`）不推荐的读数理由：三屏也是 0 枚，但最差只抬到 4.52，对 4.5 的门槛只剩 0.02；甲-强与乙在三屏上量出同一组数（4.82、5.07、4.66），差别只在射程。

## 3. 就这一行（建议落乙）：现尖上这三条规则的坐标，逐枚 git grep 现读

- drawer 分组标题：`frontend/src/styles.css:142`（规则起于 :142）——把该条里的 `color: var(--cn-ink-tertiary)` 改成 `color: var(--cn-ink-secondary)`。
- 分享接收 站点元行：`frontend/src/features/shared/sharedJourney.css:99`（规则起于 :98）——把该条里的 `color: var(--cn-ink-tertiary)` 改成 `color: var(--cn-ink-secondary)`。
- 长图 日期行小字：`frontend/src/features/poster/trip-poster.css:85`（规则起于 :83）——把该条里的 `color: var(--cn-ink-tertiary)` 改成 `color: var(--cn-ink-secondary)`。

- 三条之外的色阶声明一枚都不动：`design-tokens.css` 里 `--cn-ink-tertiary` 的亮/暗两档值保持原样，所以这个建议不改共享色阶（裁语①的口径）。
- 射程对照（现尖上按 `git grep` 现数，不是上一单的数）：`var(--cn-ink-tertiary)` 在 `frontend/src` 里出现 36 处、13 枚文件、其中 `color:` 声明 33 处；乙只动上面 3 处，另外 30 处（含 :design-tokens.css 这类未量过的屏）不受影响。

## 4. 闸（都跑在现尖这一代）
- cells 两趟：8 passed in 2.56s（collected 8，rc 0，skips 0） | 8 passed in 2.20s（collected 8，rc 0，skips 0）；同族五枚文件合跑两趟：47 passed in 15.64s（collected 47，rc 0，skips 0） | 47 passed in 15.09s（collected 47，rc 0，skips 0）。
- 整套收集 1719 条（本车道**没跑整套**，上面那些数是它的子集）；契约那把尺现读：`OpenAPI 3.1.0; formal 175; runtime 175; missing 0; extra 0 / schemas formal 87; generated 87; missing 0; extra 0|rc=0`；merge-tree 对现尖 rc=0、`tip_is_parent=True`。
- 凭据门两读：剥掉本机凭据名 = CREDENTIAL_GATE_CLEAR；不剥 = LIVE_CREDENTIAL_IN_ENVIRONMENT（本机现读名字：`DEEPSEEK_API_KEY`、`OPENAI_API_KEY`、`WB2API_KEY`）。两读都记，不互相改写。

## 5. 落完之后我立刻做的（不用您再提醒）
- 在您落地那一代上重建产物、同一把仪表重跑三屏两档两形，交「改前 vs 改后」两代读数；
- 再加一枚反件：把那三条改回 `var(--cn-ink-tertiary)` 压回候选产物，最差必须回到 3.62、3.62、3.62，回到不了就说明我这三条找错了主人（不等就拒交）。

## 6. 现场与没做的
- 私有栈：后端 pid 36668 在 :4891、静态 pid 46644 在 :4892（静态环境写死 CITYNEXUS_BACKEND_PORT=4891，代理默认值那坑上一单已修），两代各起停一次；本轮停完 netstat 回读 :4891/:4892 的 LISTENING 计 0 条。
- `demo/reset` 只落本车道那枚库 `_r5_r12.db`；共享预览库 `_preview.db` 覆盖 0 次；:8000 / :4781 / :4782 / :8693 覆盖 0 次；:4783 只读（index + 两枚资产）；权威线 0 次移动；已发布 ref 重写 0 次。
- 没量实体手机；没跑 e2e；没跑整套后端；这台机器瓦片底图始终不加载，本件没有一个结论依赖瓦片像素。
- 候选态是注入样式不是重建产物（第 2 节已具名）；乙若要落地，我按当代源码改这三条 + `tsc` + `vite build` 重建再交两代读数。
