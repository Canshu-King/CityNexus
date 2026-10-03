# ORD-0509 落「乙」成真候选（r1）：三枚 CSS 各一行，同代两档三臂读数，一枚反件

CMDR 19:53 裁「乙」：把 06:18 那块的落单建议（三处 color 改 secondary、只改 color、不动色阶定义）落成真候选。
候选直接压在权威尖 `74f5d8df082532f20e66bdba2b84311043f023b5` 上（`git ls-remote` 与 `git rev-parse 98e2d8f38ec96a46b6dce22d689064eec9cb1133^` 同值现读），父提就是我读数的改前代；候选提交 `98e2d8f38ec96a46b6dce22d689064eec9cb1133`，枝 `refs/heads/review/2d2d7428-ord0509-ink-yi-landing-r1`，改动 **三枚文件各 1 增 1 删**：
- `frontend/src/features/poster/trip-poster.css:85` —— `color: var(--cn-ink-tertiary)` -> `color: var(--cn-ink-secondary)`
- `frontend/src/features/shared/sharedJourney.css:99` —— `color: var(--cn-ink-tertiary)` -> `color: var(--cn-ink-secondary)`
- `frontend/src/styles.css:142` —— `color: var(--cn-ink-tertiary)` -> `color: var(--cn-ink-secondary)`

## 0. 代次与字节
- 两棵产物都是本机 `npx vite build`：改前 `dist_base_r2`（构建时 HEAD `74f5d8df082532f20e66bdba2b84311043f023b5`）、改后 `dist_yi_r2`（构建时 HEAD `98e2d8f38ec96a46b6dce22d689064eec9cb1133`）；四次 `tsc -p tsconfig.typecheck.json --noEmit` 与 `npx vite build` 全退 0。
- 入口：改前 `index-dc55bcFW.js`（1620478 字节 B）、改后 `index-CK82q5dZ.js`（1620478 字节 B）；私有静态口（命令行分别带 `--outDir dist_base_r2` / `--outDir dist_yi_r2`）服务字节与磁盘字节逐字节相同。这些 sha1 是在磁盘字节上重算的内容哈希、未入 git、不是 blob、故意不可取回；本行可取回的 40 位是 `98e2d8f38ec96a46b6dce22d689064eec9cb1133`。
- 上一趟（线还在 `bf4f776b0ba943b88817dfcc0cb3442d75fd9e21` 时）我构建过 dist_base_r1 / dist_yi_r1，两棵四枚资产与新构建**逐字节相同**（同一批入口名与 sha1：index-CH7QOPDS.css@e04c2eb7 / index-CK82q5dZ.js@3134fcf9 / index-BeJMb-k7.css@bbb5e0be / index-dc55bcFW.js@5235315c）。所以换代没有改变任何读数，重复一遍只是把每枚数钉在现在这两枚头上。
- 色阶定义一枚没动：`design-tokens.css` 在两颗头之间同一枚 blob `cd756bca389c2fa11cf881f0f336a963c6d81be2`；`frontend/src` 里 `color: var(--cn-ink-tertiary)` 从 33 处减到 30 处，`color: var(--cn-ink-secondary)` 从 44 处增到 47 处——减三增三就是那三条规则，别处 0 处。
- 盘面两趟都只走产品自己的门：改前 reset/prepare/scene = 200 / 200 / 200、站点 6 枚少 0 枚、错头 -> http_status=403；改后 = 200 / 200 / 200、站点 6 枚少 0 枚、错头 -> http_status=403；两枚 share-grant 各退 201 / 201；HTTP 的 plan 与库里 plan 同为 `55523d40-cafe-5bd2-b30a-de057ec7a839`。

## 1. 同代三臂（5 区 x 2 形 x 2 档 = 20 臂，每臂三趟）

| 区 | 形 | 档 | 改前 | 改后（候选） | 反件（候选上把三条注回 tertiary） |
|---|---|---|---|---|---|
| map_facts_card | 390x844 | light | 0不合格/3枚 最差5.97 | 0不合格/3枚 最差5.97 | 0不合格/3枚 最差5.97 |
| map_facts_card | 390x844 | dark | 0不合格/3枚 最差4.66 | 0不合格/3枚 最差4.66 | 0不合格/3枚 最差4.66 |
| map_facts_card | 1280x900 | light | 0不合格/13枚 最差4.82 | 0不合格/13枚 最差4.82 | 0不合格/13枚 最差4.82 |
| map_facts_card | 1280x900 | dark | 0不合格/13枚 最差4.66 | 0不合格/13枚 最差4.66 | 0不合格/13枚 最差4.66 |
| map_screen | 390x844 | light | 0不合格/3枚 最差5.97 | 0不合格/3枚 最差5.97 | 0不合格/3枚 最差5.97 |
| map_screen | 390x844 | dark | 0不合格/3枚 最差4.66 | 0不合格/3枚 最差4.66 | 0不合格/3枚 最差4.66 |
| map_screen | 1280x900 | light | 0不合格/13枚 最差4.82 | 0不合格/13枚 最差4.82 | 0不合格/13枚 最差4.82 |
| map_screen | 1280x900 | dark | 0不合格/13枚 最差4.66 | 0不合格/13枚 最差4.66 | 0不合格/13枚 最差4.66 |
| nav_drawer | 390x844 | light | 4不合格/18枚 最差3.62 | 0不合格/18枚 最差4.82 | 4不合格/18枚 最差3.62 |
| nav_drawer | 390x844 | dark | 0不合格/18枚 最差4.66 | 0不合格/18枚 最差4.66 | 0不合格/18枚 最差4.66 |
| nav_drawer | 1280x900 | light | 缺席 | 缺席 | 缺席 |
| nav_drawer | 1280x900 | dark | 缺席 | 缺席 | 缺席 |
| shared_journey | 390x844 | light | 6不合格/30枚 最差3.62 | 0不合格/30枚 最差5.07 | 6不合格/30枚 最差3.62 |
| shared_journey | 390x844 | dark | 0不合格/30枚 最差5.22 | 0不合格/30枚 最差5.74 | 0不合格/30枚 最差5.74 |
| shared_journey | 1280x900 | light | 6不合格/34枚 最差3.62 | 0不合格/34枚 最差5.07 | 6不合格/34枚 最差3.62 |
| shared_journey | 1280x900 | dark | 0不合格/34枚 最差5.22 | 0不合格/34枚 最差5.74 | 0不合格/34枚 最差5.74 |
| long_image_poster | 390x844 | light | 1不合格/22枚 最差3.62 | 0不合格/22枚 最差4.66 | 1不合格/22枚 最差3.62 |
| long_image_poster | 390x844 | dark | 0不合格/22枚 最差4.82 | 0不合格/22枚 最差4.82 | 0不合格/22枚 最差4.82 |
| long_image_poster | 1280x900 | light | 1不合格/22枚 最差3.62 | 0不合格/22枚 最差4.66 | 1不合格/22枚 最差3.62 |
| long_image_poster | 1280x900 | dark | 0不合格/22枚 最差4.82 | 0不合格/22枚 最差4.82 | 0不合格/22枚 最差4.82 |

- 亮档三屏：改前 nav_drawer 4 不合格/18 枚、最差 3.62；shared_journey 6 不合格/30 枚、最差 3.62；long_image_poster 1 不合格/22 枚、最差 3.62；改后 nav_drawer 0 不合格/18 枚、最差 4.82；shared_journey 0 不合格/30 枚、最差 5.07；long_image_poster 0 不合格/22 枚、最差 4.66；反件 nav_drawer 4 不合格/18 枚、最差 3.62；shared_journey 6 不合格/30 枚、最差 3.62；long_image_poster 1 不合格/22 枚、最差 3.62——枚数与最差逐枚复现改前，说明这三条就是我改的那三条。
- 桌面形 1280x900 同判：分享 6不合格/34枚 最差3.62 -> 0不合格/34枚 最差5.07，长图 1不合格/22枚 最差3.62 -> 0不合格/22枚 最差4.66；抽屉在该形三臂都缺席，具名 NOT_REACHED_BY_SHAPE。
- 卡片与地图屏两档两形逐枚不变（0不合格/3枚 最差5.97 / 0不合格/13枚 最差4.66），这次改动没碰它们。
- **暗档有一处真动了，先点名**：分享接收屏暗档最差 0 不合格/30 枚、最差 5.22 -> 0 不合格/30 枚、最差 5.74（两形都是）。原因是这三条声明不带档位前缀，暗档那层也从 tertiary 并到了 secondary（暗值 secondary 比 tertiary 更亮，对比更高）；不合格枚数仍是 0，是变好不是变坏。抽屉、长图、卡片三区暗档逐枚不变。
- 反件只压亮档（注入带 `:root[data-theme=light]` 前缀），暗档在它下仍是 0 不合格/30 枚、最差 5.74——这反过来证明暗档的移动来自产品里那枚未加前缀的声明，不是我的注入。
- 与上一单（r5，注入式候选）的差别就在这里：那一版暗档逐枚不变，因为注入被限定在亮档；这一版是真重建，暗档才第一次显出移动。两版读数不是矛盾，是形制不同，我提前把差异摊开。

## 2. 闸（都跑在候选提交 `98e2d8f38ec96a46b6dce22d689064eec9cb1133` 上）
- cells 两趟 8 passed in 4.10s / 8 passed in 2.59s（各 collected 8、rc 0、skips 0、failed 0）；同族五枚文件合跑两趟 47 passed in 24.29s / 47 passed in 23.49s（各 collected 47、rc 0、skips 0、failed 0）。
- 整套收集 1719 条（本车道**没跑整套**，上面那些数是它的子集）；契约尺现读 `OpenAPI 3.1.0; formal 175; runtime 175; missing 0; extra 0 / schemas formal 87; generated 87; missing 0; extra 0|rc=0`；merge-tree 对权威尖退 0。
- 凭据门两读：剥掉本机凭据名 = CREDENTIAL_GATE_CLEAR；不剥 = LIVE_CREDENTIAL_IN_ENVIRONMENT（本机现读到 3 个名字：`DEEPSEEK_API_KEY`、`OPENAI_API_KEY`、`WB2API_KEY`）。
- 前端两把构建门：改前与改后各跑一遍 tsc + vite build，四趟都退 0（构建门是 FRONTSRC_BUILD_PREREQ 的常设要求）。

## 3. 现场与红线
- 私有栈两趟：改前 api pid 29508 / static pid 39144（库 `_r5_r17.db`），改后 api pid 41292 / static pid 50004（库 `_r5_r18.db`），各带各的具名 reset token；两趟都停净：`[stop r17] killed=2 left after the sweep: 0` / `[stop r18] killed=2 left after the sweep: 0`，本件写完再读一次 netstat，:4891 与 :4892 的 LISTENING 现读 0 条。
- `demo/reset` 只落这两枚本车道库；共享预览库 `_preview.db` 覆盖 0 次；:8000 / :4781 / :4782 / :8693 覆盖 0 次；权威尖移动 0 次（这条枝是候选，合不合由您）；已发布 ref 重写 0 次。
- 没量实体手机；没跑 e2e；没跑 vitest 那一套（本轮候选是三行 CSS，`frontend/src` 里没有断言这三处墨色的测试；要补我就下一手补，不把没跑的写成绿的）；这台机器瓦片底图始终不加载，本件没有一个结论依赖瓦片像素。
