# ORD-0509 补读 · 暗色三屏在 day24 上的两代对比（r3，CMDR 01:24 派给 2d2d7428）

被测尖 `4fac49f371da0820393d038700bddddafd1176d1`（`git ls-remote --refs origin refs/heads/mirror/integration-frontend-apple-pass1` 回读同值）；上一代 `569b8472b134e5562ef396e38681870b9c26536a`（day23）。裁语①=不动共享色阶，所以这一手**只读不改**。

## 0. 两代产物各自与线上对读（先证明量的是线在发的那一枚）
- day24：:4783 的入口 `/assets/index-5DRahkM8.js`（1619701 字节 B，服务字节 sha1 7cf0c2387622b2ab1f49f985affc771516f32f64）与 CSS `/assets/index-BeJMb-k7.css`（231756 字节 B，sha1 bbb5e0be183eee21aa0ff1f52046ce3a1d280162）都与本尖 `npx vite build` 出来的磁盘产物逐字节相同。
- day23：同一把对读当时也成立（入口 index-CKZE7InQ.js，1609739 字节 B，sha1 fa51295cdd73e9d1e04b5f524d56cb84a15b6bb3）。两枚 sha1 都是产物内容哈希、非 git 对象、不可 cat-file；可取回的 40 位是本行末尾的尖号 4fac49f371da0820393d038700bddddafd1176d1。
- day23 -> day24 在 `frontend/src` 里动的源（numstat 现读）：`frontend/src/app/V8Experience.tsx` 23增56删；`frontend/src/app/v8Types.ts` 14增1删；`frontend/src/features/trip/SpendPanel.tsx` 206增0删；`frontend/src/features/trip/spend.css` 25增0删；`frontend/src/features/trip/spendFacts.ts` 317增0删；`frontend/src/i18n/LocaleContext.tsx` 66增0删。壳那两枚（V8Experience / LocaleContext）与新增的花费三件套都在这批里，所以这一趟不是重复读数。
- 三屏自己的源逐枚比过 blob，两代全等：`styles.css` 58e982e1、`design-tokens.css` cd756bca、`v8PanelRegistry.tsx` c163ccf9、`SharedJourneyPanel.tsx` a2ccfc13、`SharedPosterScreen.tsx` 901bec8b、`sharedJourney.css` fe7401ff、`trip-poster.css` 6078839d。

## 1. 盘面仍只走产品自己的门
- demo/reset -> prepare-scenario -> scene 答 200 / 200 / 200；plan=55523d40；站点 6 枚、有坐标 6 枚、少 0 枚、supply.state=NOT_ASKED；错头当 reset 头用 -> http 403。库 `_r5_r10.db`，HTTP 的 plan 与库里 plan 一致=True，服务字节==磁盘=True；静态服务环境 CITYNEXUS_BACKEND_PORT=4891。

## 2. 两代逐臂对比（5 区 x 2 形 x 2 档 = 20 臂；每格给 不合格/屏上枚数/最差对比）

| 屏 | 形 | 档 | day23 | day24 | 判 |
|---|---|---|---|---|---|
| map_facts_card | 390x844 | light | 0/3 最差 5.97 | 0/3 最差 5.97 | 判据一致 |
| map_facts_card | 390x844 | dark | 0/3 最差 4.66 | 0/3 最差 4.66 | 判据一致 |
| map_facts_card | 1280x900 | light | 0/13 最差 4.82 | 0/13 最差 4.82 | 判据一致 |
| map_facts_card | 1280x900 | dark | 0/13 最差 4.66 | 0/13 最差 4.66 | 判据一致 |
| map_screen | 390x844 | light | 0/3 最差 5.97 | 0/3 最差 5.97 | 判据一致 |
| map_screen | 390x844 | dark | 0/3 最差 4.66 | 0/3 最差 4.66 | 判据一致 |
| map_screen | 1280x900 | light | 0/13 最差 4.82 | 0/13 最差 4.82 | 判据一致 |
| map_screen | 1280x900 | dark | 0/13 最差 4.66 | 0/13 最差 4.66 | 判据一致 |
| nav_drawer | 390x844 | light | 4/18 最差 3.62 | 4/18 最差 3.62 | 判据一致 |
| nav_drawer | 390x844 | dark | 0/18 最差 4.66 | 0/18 最差 4.66 | 判据一致 |
| nav_drawer | 1280x900 | light | 缺席 | 缺席 | 该形制主体不在 DOM，没量到 |
| nav_drawer | 1280x900 | dark | 缺席 | 缺席 | 该形制主体不在 DOM，没量到 |
| shared_journey | 390x844 | light | 6/30 最差 3.62 | 6/29 最差 3.62 | 判据一致 |
| shared_journey | 390x844 | dark | 0/29 最差 5.22 | 0/29 最差 5.22 | 判据一致 |
| shared_journey | 1280x900 | light | 6/33 最差 3.62 | 6/33 最差 3.62 | 判据一致 |
| shared_journey | 1280x900 | dark | 0/33 最差 5.22 | 0/33 最差 5.22 | 判据一致 |
| long_image_poster | 390x844 | light | 1/22 最差 3.62 | 1/22 最差 3.62 | 判据一致 |
| long_image_poster | 390x844 | dark | 0/22 最差 4.82 | 0/22 最差 4.82 | 判据一致 |
| long_image_poster | 1280x900 | light | 1/22 最差 3.62 | 1/22 最差 3.62 | 判据一致 |
| long_image_poster | 1280x900 | dark | 0/22 最差 4.82 | 0/22 最差 4.82 | 判据一致 |

- 逐臂计数：20 臂里 **18 臂判据一致**、**0 臂判据不同**、2 臂因该形制主体不在 DOM 只记缺席；另有 1 臂的**可见行数**变了（下面单列，并给出同一代内的浮动带）。
- 行数变化：shared_journey / 390x844 / light —— day23 30 枚 -> day24 29 枚；同一代 day23 的四臂之间这一枚就在 29、30 枚之间浮动，所以它是行数为浮动、不是判据。

## 3. 按裁语①的口径，这轮的判据
- 色阶没动，所以三屏亮档那批不合格元素**照旧存在**：day24 上抽屉 4 枚、分享接收 6 枚、长图 1 枚（屏上口径），最差对比逐枚 3.62、3.62、3.62。暗档 0 枚不合格。
- 卡片（上一单落的）在两代上都仍是 0 不合格：day23 0 不合格/3 枚、最差 4.66 / day24 0 不合格/3 枚、最差 4.66。
- 「若颜色没变就报绿」这格按读数答：两代之间**没有任何一臂的对比值变了**——20 臂全部一致（缺席形制除外），所以报绿。

## 4. 闸与凭据（跑在本枝的上一笔 4fac49f371da；从那之后本枝只多了证据件自身，numstat 现读：没有别的变化）
- cells 1：collected 8，8 passed in 1.97s，rc=0。
- cells 2：collected 8，8 passed in 1.86s，rc=0。
- family 1：collected 47，47 passed in 14.22s，rc=0。
- family 2：collected 47，47 passed in 14.19s，rc=0。
- 整套收集 1713 条（上面是它的子集）；整套没跑（NOT_EXECUTED_BY_LANE）。契约：OpenAPI 3.1.0; formal 175; runtime 175; missing 0; extra 0 / schemas formal 87; generated 87; missing 0; extra 0。
- 凭据开机门两读：剥 -> CREDENTIAL_GATE_CLEAR（552 枚文件、命中 5）；不剥 -> LIVE_CREDENTIAL_IN_ENVIRONMENT。本机环境里的凭据变量名（只名字）：DEEPSEEK_API_KEY、OPENAI_API_KEY、WB2API_KEY。

## 5. 复算命令
```
cd D:/moodle/_qoder_q_ord0427_20260929/wt/frontend && npx vite build --outDir dist_day24 --emptyOutDir
python D:/moodle/_qoder_q_ord0522_20261001/start_stack_r5.py r10 dist_day24 <token>
DB_FILE=... RESET_TOKEN=<token> python stage_via_product_doors_r3.py r10
python share_grant_r5.py r10
node measure_screens_r5.cjs r10day24 screens_r10day24.json 22222222-2222-4222-8222-222222222222 <token>
git rev-parse 569b8472b134e5562ef396e38681870b9c26536a:<path> # 对每一枚源逐枚比 blob
```

## 6. 没做的
- 没量实体手机；没跑 e2e；没跑整套后端；瓦片底图这台机器始终不加载。
- 没动任何字节：裁语①是不动共享色阶，所以 r2 那三条候选（甲 / 甲-强 / 乙）在这一代**不重跑**，它们的数留在 r2 那件里；要落哪一条仍等你另发一令。
