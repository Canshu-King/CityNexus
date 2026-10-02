# ORD-0509 续 · 亮档 3.62 的档位裁决件（r2：四臂搬到现尖自己的产物上重跑）

现尖 `569b8472b134e5562ef396e38681870b9c26536a`（`git ls-remote --refs origin refs/heads/mirror/integration-frontend-apple-pass1` 回读同值）；本件写在本枝头 `386e0000d9f54afa85eed6189de8bdd585e5ebcd`；该尖 styles.css blob `58e982e1bad669fe9b66cee392c4651ce0fd3644` = 上一单落地的候选字节。

## 0. 先与线上对读，再报数
- :4783 现在服务的入口 `/assets/index-CKZE7InQ.js`（1609739 字节 B，服务字节 sha1 fa51295cdd73e9d1e04b5f524d56cb84a15b6bb3）与 CSS `/assets/index-BQzlTYlS.css`（231440 字节 B，sha1 2d529817904874d60acc90281e7b1f022a6e8246），两枚都与本枝头 `npx vite build` 出来的磁盘产物逐字节相同。那两枚 sha1 是产物内容哈希，非 git 对象、不可 cat-file；本行可取回的 40 位是现尖 569b8472b134e5562ef396e38681870b9c26536a。
- 盘面只走产品自己的门：demo/reset -> prepare-scenario -> scene 答 200 / 200 / 200，站点 6 枚、少 0 枚、supply.state=NOT_ASKED；库 `_r5_r9.db`，静态服务环境 CITYNEXUS_BACKEND_PORT=4891（上一单那枚代理默认值已修）。
- 与 day21（代 `e7ff7938ea41`）那批四臂对读：三屏两档的**不合格枚数与最差对比逐枚相同**（不等就拒写）。文字枚数有一处不同——shared_journey dark：day21 30 枚 -> 现尖 29 枚；同一枚在本代四臂之间也在浮动（shared_journey dark 在 29、30 枚之间浮动），所以那是屏上行数的浮动、不是判据变了。七枚与这三屏直接相关的源在两代之间逐枚 UNMOVED：`styles.css`、`design-tokens.css`、`v8PanelRegistry.tsx`、`SharedJourneyPanel.tsx`、`SharedPosterScreen.tsx`、`sharedJourney.css`、`trip-poster.css`。

## 1. 现尖这一代上，三屏还红不红
- 卡片（上一单那枚 1 增 1 删的对象）：亮档 0 不合格/3 枚、最差 5.97、暗档 0 不合格/3 枚、最差 4.66 —— 已经干净。
- 亮档三屏：nav_drawer 4 不合格/18 枚、最差 3.62、shared_journey 6 不合格/30 枚、最差 3.62、long_image_poster 1 不合格/22 枚、最差 3.62。
- 暗档三屏：nav_drawer 0 不合格/18 枚、最差 4.66、shared_journey 0 不合格/29 枚、最差 5.22、long_image_poster 0 不合格/22 枚、最差 4.82。
- 三屏亮档最差那枚的色值逐枚是 134,134,139，即 `--cn-ink-tertiary` 的亮档声明；按 WCAG 现算它对纯白是 3.62（门槛 4.5），暗档那层对 `#1c1c1e` 是 5.22 —— 缺口在亮档。
- 这层墨在全树的射程（按现尖现数）：`frontend/src` 下 12 枚文件、共 35 处引用，其中 `color:` 32 处。我 r1 那版把射程写成『两枚 CSS 里 8 处』，那是分母数错了，这里按树重数纠正。清单：`design-tokens.css`、`access.css`、`footprint.css`、`pretripChecklist.css`、`collections.css`、`discovery-batch.css`、`prepAbandonSurvey.css`、`pendingSet.css`、`trip-poster.css`、`sharedJourney.css`、`journeyTrash.css`、`styles.css`。
- 三处不合格角色各自主人（规则体里声明这层墨的那一行）：`.v8-nav-group` -> `frontend/src/styles.css:142`；`.cn-shared-stop-meta` -> `frontend/src/features/shared/sharedJourney.css:98`；`.cn-poster-day-head small` -> `frontend/src/features/poster/trip-poster.css:83`。

## 2. 三条候选，全部跑在上面那枚线上产物上（注入作者样式，不冒充构建产物）

| 候选 | 注入 | 抽屉 亮档 | 分享 亮档 | 长图 亮档 | 三屏 暗档 |
|---|---|---|---|---|---|
| 甲 | --cn-ink-tertiary:#76767b（对白 4.52） | 0 不合格/18 枚、最差 4.52 | 0 不合格/30 枚、最差 4.52 | 0 不合格/22 枚、最差 4.52 | nav_drawer 0 不合格/18 枚、最差 4.66、shared_journey 0 不合格/30 枚、最差 5.22、long_image_poster 0 不合格/22 枚、最差 4.82 |
| 甲-强 | --cn-ink-tertiary:#6e6e73（亮档并到 secondary 的数） | 0 不合格/18 枚、最差 4.82 | 0 不合格/30 枚、最差 5.07 | 0 不合格/22 枚、最差 4.66 | nav_drawer 0 不合格/18 枚、最差 4.66、shared_journey 0 不合格/29 枚、最差 5.22、long_image_poster 0 不合格/22 枚、最差 4.82 |
| 乙 | 三处角色改 color: var(--cn-ink-secondary) | 0 不合格/18 枚、最差 4.82 | 0 不合格/29 枚、最差 5.07 | 0 不合格/22 枚、最差 4.66 | nav_drawer 0 不合格/18 枚、最差 4.66、shared_journey 0 不合格/30 枚、最差 5.22、long_image_poster 0 不合格/22 枚、最差 4.82 |

- 三条都把三屏亮档压到 0 枚不合格，暗档逐枚最差与基线相同（写在开头就判过：动暗档就拒写）。
- 差在两点，都可核对：甲的余量只有 4.52，而甲-强与乙量出同一组数（4.82、5.07、4.66）——『并色阶』与『改这三处角色』在这三屏上渲染相同，差的是射程：前者动 35 处引用（其中 32 处是 color），后者动 3 条规则。

## 3. 我这把尺先红过一次（r1 记录，不是产品结论）
- 乙的第一趟注入只写到 `:root[data-theme=light] .v8-nav-group`，抽屉仍报 4 不合格/18 枚、最差 3.62；量出来是产品那条规则带 ID（现尖上主人是 `frontend/src/styles.css:142`），ID 的特异性压过我的类选择器——我的注入没够到。第二趟补成带 ID 的同一条后抽屉才真干净。第一趟的件留在 `screens_r7YI.json`，只用作仪器错记录。

## 4. 没做的
- 四臂的候选态是注入的作者样式，不是重建的产物：注入只换一枚自定义属性或一条 color 声明，级联与特异性按真产物走（第 3 节就是被特异性咬出来才补的选择器）。裁哪一条，我按当代源码改、`tsc` 两把 + `vite build` 重建，再交『改前 vs 改后』两代读数与一枚把旧值压回去的反件。
- 只量了 390x844 一形（这三屏的桌面形在 r5 量过：分享与长图两屏桌面形同样只红在亮档；抽屉在桌面点不开主体，具名 NOT_REACHED_BY_SHAPE）。没量实体手机；没跑 e2e；没跑整套后端；瓦片底图这台机器始终不加载，本件没有一个结论依赖瓦片像素。
