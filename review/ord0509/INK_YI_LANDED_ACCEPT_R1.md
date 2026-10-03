# ORD-0509 乙 落地代验收（accept r1）：源码已换代，屏上还没换

我读数与闸所在那代 `a3324c4d214e6f402c9a3712bc557ace1afb06f0`；写件这趟线已走到 `b168b428f4ed0c9719a1aecf0bb38d98035cec9e`（`git ls-remote --refs origin refs/heads/mirror/integration-frontend-apple-pass1` 本趟现读，`b168b428f4ed0c9719a1aecf0bb38d98035cec9e` 是 `a3324c4d214e6f402c9a3712bc557ace1afb06f0` 的后代，且我那三枚 CSS 与色阶定义在两枚头上逐枚同 blob）。我交付的那枚改动 `98e2d8f38ec96a46b6dce22d689064eec9cb1133` 是 `a3324c4d214e6f402c9a3712bc557ace1afb06f0` 的祖先（`merge-base --is-ancestor` 退 0），落地前一代是它父提 `74f5d8df082532f20e66bdba2b84311043f023b5`。

## 1. 源码逐枚对照：线在发的就是我交的那三行
- `frontend/src/styles.css`：落地前 blob `58e982e1bad6` -> 落地 `179d26e66209`；现尖上同一枚 `179d26e66209`（与我交付逐枚相同）。
- `frontend/src/features/shared/sharedJourney.css`：落地前 blob `fe7401ff183e` -> 落地 `d0d97bccb2ba`；现尖上同一枚 `d0d97bccb2ba`（与我交付逐枚相同）。
- `frontend/src/features/poster/trip-poster.css`：落地前 blob `6078839dcca3` -> 落地 `9c90a61e334b`；现尖上同一枚 `9c90a61e334b`（与我交付逐枚相同）。
- 现尖上的三处 secondary 声明坐标：`features/poster/trip-poster.css:24`、`features/poster/trip-poster.css:85`、`features/poster/trip-poster.css:107`、`features/poster/trip-poster.css:122`、`features/poster/trip-poster.css:138`、`features/shared/sharedJourney.css:62`、`features/shared/sharedJourney.css:99`、`styles.css:142`、`styles.css:178`；色阶定义仍是 `design-tokens.css:15` = `--cn-ink-tertiary: #86868b;`、`design-tokens.css:172` = `--cn-ink-tertiary: #8e8e93;`。`frontend/src` 里 `color: var(--cn-ink-tertiary)` 从 33 处减到 30 处、`color: var(--cn-ink-secondary)` 从 44 处增到 47 处——减三增三，别处 0 处。
- `frontend/src/design-tokens.css` 在落地前后同一枚 blob（`cd756bca389c2fa11cf881f0f336a963c6d81be2`）：裁语「不动色阶定义」在现尖上成立。

## 2. 两棵产物（本机重建，构建门四趟都退 0）
- 落地前 `74f5d8df082532f20e66bdba2b84311043f023b5`：CSS `index-BeJMb-k7.css` 231756 字节 B（内容 sha1 bbb5e0be183eee21aa0ff1f52046ce3a1d280162）、JS `index-dc55bcFW.js` 1620478 字节 B（sha1 5235315cdd3a76c3ba302c583edebd72d5fe3d84）。
- 落地代 `a3324c4d214e6f402c9a3712bc557ace1afb06f0`：CSS `index-CH7QOPDS.css` 231759 字节 B（内容 sha1 e04c2eb78bcd62193620238fddba9aaffe470a36）、JS `index-CuMOkEqV.js` 1620655 字节 B（sha1 05b5fe3d026d214ae7a9ff524e3c2e0493d29377）——CSS 多 3 字节 B 就是三处 `tertiary`->`secondary` 各多一个字母。
- 这些 sha1 都是在磁盘字节上重算的内容哈希、未入 git、不是 blob、故意不可取回；本行可取回的 40 位是现尖 `a3324c4d214e6f402c9a3712bc557ace1afb06f0`。私有静态口两趟的服务字节与磁盘字节逐字节相同（formal/runtime 条路由的 plan 与库里 plan 同为 `55523d40-cafe-5bd2-b30a-de057ec7a839`）。

## 3. 落地代三臂（5 区 x 2 形 x 2 档 = 20 臂，落地前 / 落地代 / 反件）

| 区 | 形 | 档 | 落地前 | 落地代 | 反件（落地代上把三条注回 tertiary） |
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
| shared_journey | 390x844 | light | 6不合格/30枚 最差3.62 | 0不合格/31枚 最差5.07 | 6不合格/31枚 最差3.62 |
| shared_journey | 390x844 | dark | 0不合格/30枚 最差5.22 | 0不合格/31枚 最差5.74 | 0不合格/31枚 最差5.74 |
| shared_journey | 1280x900 | light | 6不合格/34枚 最差3.62 | 0不合格/34枚 最差5.07 | 6不合格/34枚 最差3.62 |
| shared_journey | 1280x900 | dark | 0不合格/34枚 最差5.22 | 0不合格/34枚 最差5.74 | 0不合格/34枚 最差5.74 |
| long_image_poster | 390x844 | light | 1不合格/22枚 最差3.62 | 0不合格/22枚 最差4.66 | 1不合格/22枚 最差3.62 |
| long_image_poster | 390x844 | dark | 0不合格/22枚 最差4.82 | 0不合格/22枚 最差4.82 | 0不合格/22枚 最差4.82 |
| long_image_poster | 1280x900 | light | 1不合格/22枚 最差3.62 | 0不合格/22枚 最差4.66 | 1不合格/22枚 最差3.62 |
| long_image_poster | 1280x900 | dark | 0不合格/22枚 最差4.82 | 0不合格/22枚 最差4.82 | 0不合格/22枚 最差4.82 |

- 亮档三屏：落地前 nav_drawer 4不合格/18枚 最差3.62；shared_journey 6不合格/30枚 最差3.62；long_image_poster 1不合格/22枚 最差3.62 -> 落地代 nav_drawer 0不合格/18枚 最差4.82；shared_journey 0不合格/31枚 最差5.07；long_image_poster 0不合格/22枚 最差4.66；反件 nav_drawer 4不合格/18枚 最差3.62；shared_journey 6不合格/31枚 最差3.62；long_image_poster 1不合格/22枚 最差3.62（枚数与最差逐枚复现落地前，所以线上新墨的主人就是我改的那三条）。
- 桌面形 1280x900：分享 6不合格/34枚 最差3.62 -> 0不合格/34枚 最差5.07、长图 1不合格/22枚 最差3.62 -> 0不合格/22枚 最差4.66；抽屉在该形仍缺席，具名 NOT_REACHED_BY_SHAPE。
- 暗档：落地代 nav_drawer 0不合格/18枚 最差4.66；shared_journey 0不合格/31枚 最差5.74；long_image_poster 0不合格/22枚 最差4.82；分享接收屏暗档最差随同一枚声明从 0不合格/30枚 最差5.22 抬到 0不合格/31枚 最差5.74（枚数仍 0）。反件带 light 前缀，压不动暗档，所以暗档那格的读数与落地代相同——这条差异上一单已点名，这里再确认一次。

## 4. 屏读（落地代裁图 vs 反件裁图：像素差 + 同一枚产物重拍的噪声底 + 渲染文字逐串对照）

| 屏 | 档 | 裁图 | 差了多少像素（共多少） | 噪声底（同产物重拍） | 差的位置（框） | 文字枚数 | 渲染文字 |
|---|---|---|---|---|---|---|---|
| long_image_poster | dark | 390x691 | 0 / 269490 | 0 | 无（该格没有像素变化） | 22 | 两臂逐串相同（433 字） |
| long_image_poster | light | 390x691 | 72 / 269490 | 0 | [354, 367, 377, 379] | 22 | 两臂逐串相同（433 字） |
| nav_drawer | dark | 300x844 | 0 / 253200 | 0 | 无（该格没有像素变化） | 23 | 两臂逐串相同（100 字） |
| nav_drawer | light | 300x844 | 275 / 253200 | 0 | [26, 93, 45, 749] | 23 | 两臂逐串相同（100 字） |
| shared_journey | dark | 390x1091 | 1125 / 425490 | 556 | [67, 797, 248, 856] | 40 | 两臂逐串相同（472 字） |
| shared_journey | light | 390x1091 | 1608 / 425490 | 68 | [32, 411, 247, 856] | 40 | 两臂逐串相同（493 字） |

- 计算样式（真 DOM 上读，不是 data 属性）：long_image_poster/dark `无颜色变化`；long_image_poster/light `rgb(110, 110, 115)->rgb(134, 134, 139)`；nav_drawer/dark `无颜色变化`；nav_drawer/light `rgb(110, 110, 115)->rgb(134, 134, 139)`；shared_journey/dark `无颜色变化`；shared_journey/light `rgb(110, 110, 115)->rgb(134, 134, 139)`。
- 判据与归因：同一裁图做 `ImageChops.difference` 转灰度后按 >8 计数。亮档三屏的差落在文字行带上（275、1608、72 像素，噪声底 0、68、0）；暗档长图与抽屉两格差 0 像素；分享接收屏暗档那 1125 像素与噪声底同量（同一枚产物重拍就有 556 像素），所以我不把它算作这次改动造成的。
- 渲染文字两臂逐串相同（脚本按 DOM 顺序比对，任一串不同本件就 REFUSE）——这一手是墨色动、文案没动。
- 两趟屏读各自回执：落地臂 `mutant_rule=null`，反件臂记着那条注入规则；两臂加载的是同一枚入口 `http://127.0.0.1:4892/assets/index-CuMOkEqV.js`。

## 5. 一件必须点名的：源码换了，屏上还没换
- :4783 这趟读了 3 次（index + 两枚资产，GET），现读到的是 `/assets/index-DaQ9kjra.js` 与 `/assets/index-BeJMb-k7.css`——CSS 那枚是**落地前**那一棵（sha1 bbb5e0be183eee21aa0ff1f52046ce3a1d280162，231756 字节 B）。落地代那枚是 `index-CH7QOPDS.css`（sha1 e04c2eb78bcd62193620238fddba9aaffe470a36，231759 字节 B）。
- 也就是说：现尖源码已经带上新的墨，但共享预览那台静态服务还在发换代之前的产物，**人眼看那一屏还看不到这次改动**。要么您那边重跑一次部署，要么我按令起一枚只读的服务把这代端出去（不动 :4783 那台）。

## 6. 闸（跑在现尖 `a3324c4d214e6f402c9a3712bc557ace1afb06f0` 上）
- cells 两趟 8 passed in 3.04s / 8 passed in 2.79s；同族五枚文件合跑两趟 47 passed in 20.10s / 47 passed in 22.91s；整套收集 1730 条（本车道**没跑整套**）；契约尺现读 `OpenAPI 3.1.0; formal 175; runtime 175; missing 0; extra 0 / schemas formal 87; generated 87; missing 0; extra 0|rc=0`；merge-tree 退 0。
- 凭据门两读：剥名 CREDENTIAL_GATE_CLEAR；不剥 LIVE_CREDENTIAL_IN_ENVIRONMENT。盘面两趟只走产品自己的门：落地前 200 / 200 / 200、站点 6 枚少 0 枚、错头退 403、grant 201；落地代 200 / 200 / 200、站点 6 枚少 0 枚、错头退 403、grant 201。
- 私有栈两趟都停净（`[stop r21] killed=2 left after the sweep: 0` / `[stop r22] killed=2 left after the sweep: 0`），本件写完再读 netstat：端口 4891 与 4892 的 LISTENING 计 0 条；`demo/reset` 只落这两枚本车道库（_r5_r21.db、_r5_r22.db）；共享预览库 `_preview.db` 覆盖 0 次；端口 8000 / 4781 / 4782 / 8693 覆盖 0 次；权威尖移动 0 次；已发布 ref 重写 0 次——我 20:31 那枝 `refs/heads/review/2d2d7428-ord0509-ink-yi-landing-r1` 的远端头现读仍是 `e2dea311c2736125dcd6e60b438699cca9d32bd6`（一字未动），本验收件另开在新枝 `refs/heads/review/2d2d7428-ord0509-ink-yi-landed-accept-r1`、直接压在现尖上。
- 没量实体手机；没跑 e2e；没跑 vitest；瓦片底图在这台机器仍不加载，本件没有一个结论依赖瓦片像素。另有一件我自报：写这份件之前我把门禁回执里那枚现尖号手敲补全过 40 位（错的），所有命令因此报 bad object、没产生任何结论；从这一趟起 40 位一律从 `ls-remote` / JSON 回执里取，不再手打。
