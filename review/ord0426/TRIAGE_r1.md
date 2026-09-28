# ORD-0426 · 27 条「无消费者」选择器的屏上分诊（两趟，0 产品字节）

- 生成 2026-09-29T02:15:12+0800；仪表 pass1 `cmdr_orphan_repoint_r2.js`、pass2 `cmdr_orphan_repoint_pass2.js`（同目录）。
- 被量产物：现尖 `fb6131f359e85deb18a2194494dc9a96e328cdee` 的构建，实载 CSS ["index-DMJE_sMd.js", "index-Dm2cFpiB.css"]。
- pass1 场景 {"locales": ["zh", "en"], "shapes": ["390x844", "320x653", "414x896"], "routes": ["hub", "live", "map", "studio", "stay", "discover", "bookings", "agent", "authoritative", "intelligence", "twin", "trash", "trips", "me"]}，标题样本 heading_samples=146；pass2 场景 widths=[320, 360, 390, 414, 800, 1280] × routes=["hub", "live", "map", "studio", "stay", "twin", "intelligence", "agent", "trips", "me"]。
- 输入来自已落地的 ORD-0421：wanted=27，本尖重解析 rules=1378。
- 结果 class_counts={"INTENT_APPLIED_VIA_GROUP_SIBLING": 10, "THIRD_PARTY_DOM_NOT_DEAD": 2, "DEAD_LEGACY": 15}；pass2 对 15 条 DEAD_LEGACY 再探容器：{"DEAD_LEGACY_CONFIRMED_NO_CONTAINER": 15}。

## 跨代次对照（同一判据，两枚尖各跑一遍）

- 上一代 `3d28da7d221cfd2ca463991796f0a257df042972`（ORD-0420 改 DOM 之前）与本轮 `fb6131f359e85deb18a2194494dc9a96e328cdee`：27 条里分类逐条相同的条数 same=27，两代 class_counts 分别为 {"INTENT_APPLIED_VIA_GROUP_SIBLING": 10, "THIRD_PARTY_DOM_NOT_DEAD": 2, "DEAD_LEGACY": 15} 与 {"INTENT_APPLIED_VIA_GROUP_SIBLING": 10, "THIRD_PARTY_DOM_NOT_DEAD": 2, "DEAD_LEGACY": 15}。
- 结论不因代次翻面，这是量出来的。两轮之间我还重跑了一次代次标签修正：初版把被量尖写成字面量、且只记录 CSS 名字，而两枚尖的 CSS 字节同名（styles.css 与 design-tokens.css 的 blob 在两代上相同），等于钉不住代次；现在尖由参数传入、并记录页面实载的 js 与 css 名字。

## 直接回答你点的那两枚字号规则

- `.v8-hero-title`（design-tokens.css:235）不是孤立布局规则：它写在**逗号分组**里，同组的 `.v8-page h1` 实测命中 {".v8-page h1": 2}，所以档位是经这一半落地的；屏上没有任何元素带 `.v8-hero-title` 这个名字（own_hits_max=0）。
- `.v8-section-title`（design-tokens.css:236）同形：同组 `.v8-page h2` 命中 {".v8-page h2": 3}，own_hits_max=0。
- 结论：标题不是「在吃默认样式」，而是**已经吃到设计档位**；未用的只是那两个类名。所以这两条按你的口径应归 INTENT_APPLIED_VIA_GROUP_SIBLING，不建议 repoint，只建议改名或删除该别名。

## 一、屏上确有该角色且没吃到规则（ORPHAN_LAYOUT_RULE_WANTS_REPOINT）

（计数 0）
- 本轮 0 条。pass1 的三条角色来源（同组兄弟 / 已存在祖先 / 明确叶标签）都没给出「元素在位但值不对」的组合；pass2 又对 15 条 DEAD_LEGACY 单独探了容器是否存在，也没有翻案。

## 二、意图经同组另一半落地（INTENT_APPLIED_VIA_GROUP_SIBLING，只欠类名）

| 选择器 | path:line | 同组真正命中的选择器与屏上数 | own_hits |
|---|---|---|---|
| `.v8-rain-button` | styles.css:167, styles.css:167, styles.css:183, styles.css:275, styles.css:311 | `.v8-primary`=2, `.v8-outline-button`=3, `.v8-quiet-button`=5, `.v8-text-button`=1 | 0 |
| `.v8-hero-title` | design-tokens.css:235 | `.v8-page h1`=2 | 0 |
| `.v8-section-title` | design-tokens.css:236 | `.v8-page h2`=3 | 0 |
| `.v8-home-language` | design-tokens.css:746 | `.v9-language`=2 | 0 |
| `.state-arrived` | styles.css:214 | `.state-active`=1 | 0 |
| `.state-en_route` | styles.css:214 | `.state-active`=1 | 0 |
| `.state-in_progress` | styles.css:214 | `.state-active`=1 | 0 |
| `.state-skipped` | styles.css:213 | `.state-completed`=3 | 0 |
| `.v8-page a.v8-cta` | design-tokens.css:270, design-tokens.css:280, design-tokens.css:285 | `.v8-page button:not(.cn-no-motion)`=10 | 0 |
| `.v8-page-intro .v8-rain-button` | styles.css:178 | `.v8-page-intro .v8-primary`=1, `.v8-page-intro .v8-outline-button`=1 | 0 |

## 三、第三方运行时 DOM（不计缺陷）

- `.v8-maplibre-canvas .maplibregl-cooperative-gesture-screen .maplibregl-desktop-message` @ design-tokens.css:1330：maplibre 自有节点；本轮实测 gesture 容器在屏上出现 gesture_node=0，该类命中 hits=0。子串扫 frontend/src 看不到库自造的节点，故按你的护栏排除。
- `.v8-maplibre-canvas .maplibregl-cooperative-gesture-screen .maplibregl-mobile-message` @ design-tokens.css:1333：maplibre 自有节点；本轮实测 gesture 容器在屏上出现 gesture_node=0，该类命中 hits=0。子串扫 frontend/src 看不到库自造的节点，故按你的护栏排除。

## 四、屏上连容器都没有（DEAD_LEGACY，只建议删除，本单未删）

- 计数 dead_legacy=15，pass2 复核后确认无容器的条数 confirmed=15。

| 选择器 | path:line | 命名家族 | 同族元素在屏数 | 容器 | pass2 结论 |
|---|---|---|---|---|---|
| `.anchor-line` | styles.css:168 | `anchor-line` | 0 | 无 | DEAD_LEGACY_CONFIRMED_NO_CONTAINER |
| `.cn-copilot-runtime` | styles.css:359, styles.css:365 | `cn-copilot-runtime` | 0 | 无 | DEAD_LEGACY_CONFIRMED_NO_CONTAINER |
| `.cn-native-status` | styles.css:394 | `cn-native-status` | 0 | 无 | DEAD_LEGACY_CONFIRMED_NO_CONTAINER |
| `.cn-native-status.active` | styles.css:395 | `cn-native-status` | 0 | 无 | DEAD_LEGACY_CONFIRMED_NO_CONTAINER |
| `.cn-native-status.terminal` | styles.css:396 | `cn-native-status` | 0 | 无 | DEAD_LEGACY_CONFIRMED_NO_CONTAINER |
| `.today-actions` | styles.css:1539, styles.css:1571 | `today-actions` | 0 | 无 | DEAD_LEGACY_CONFIRMED_NO_CONTAINER |
| `.v12-risk-banner.risk-critical` | styles.css:223 | `v12-risk-banner` | 0 | 无 | DEAD_LEGACY_CONFIRMED_NO_CONTAINER |
| `.v12-risk-banner.risk-safe` | styles.css:224 | `v12-risk-banner` | 0 | 无 | DEAD_LEGACY_CONFIRMED_NO_CONTAINER |
| `.v8-anchor-row` | styles.css:168, styles.css:178 | `v8-anchor-row` | 0 | 无 | DEAD_LEGACY_CONFIRMED_NO_CONTAINER |
| `.v8-live-grid` | styles.css:173, styles.css:177 | `v8-live-grid` | 0 | 无 | DEAD_LEGACY_CONFIRMED_NO_CONTAINER |
| `.v8-page a.v8-cta:active` | design-tokens.css:268 | `v8-page` | 1 | div.v8-page-intro | DEAD_LEGACY_CONFIRMED_NO_CONTAINER |
| `.v8-strength` | styles.css:174 | `v8-strength` | 0 | 无 | DEAD_LEGACY_CONFIRMED_NO_CONTAINER |
| `.v8-trip-hero-head` | styles.css:168, styles.css:178 | `v8-trip-hero-head` | 0 | 无 | DEAD_LEGACY_CONFIRMED_NO_CONTAINER |
| `.v8-trip-metrics` | styles.css:168, styles.css:178 | `v8-trip-metrics` | 0 | 无 | DEAD_LEGACY_CONFIRMED_NO_CONTAINER |
| `.v9-live-actions` | styles.css:255, styles.css:274 | `v9-live-actions` | 0 | 无 | DEAD_LEGACY_CONFIRMED_NO_CONTAINER |

## 五、h1 到底在哪条规则下画（跨宽度实测）

| 视口宽 | h1 实算 font-size | clamp(28px,3.2vw,43px) 在该宽应得 | ≤680px 档应得 | token --cn-fs-display |
|---|---|---|---|---|
| 320 | 34px | 28.0px | 30px | 34px |
| 360 | 34px | 28.0px | 30px | 34px |
| 390 | 34px | 28.0px | 30px | 34px |
| 414 | 34px | 28.0px | 30px | 34px |
| 800 | 34px | 28.0px | 不适用 | 34px |
| 1280 | 34px | 40.96px | 不适用 | 34px |

- 判读：走查宽度 widths=[320, 360, 390, 414, 800, 1280] 共 6 档（手机档 4 个、桌面档 2 个），h1 实算值去重后 measured=["34px"]，与 token 档位 34px 相同；而 styles.css 里那两条随视口变化的 h1 规则按公式应得上表第三、四列（例如 1280 档 clamp 应得 40.96px、320 档应得 28.0px）。实测值与两者都不符 ⇒ 在浏览器实载的那份 CSS 里，生效的是 token 档那一条，两条 responsive 规则没有落地。
- 仪器缺陷主动报：pass1 想用「选择器在已加载 CSS 里的字节偏移」定级联顺序，但三条规则的**选择器文本相同**（都叫 `.v8-page h1`，只差外面有没有 @media），indexOf 只会返回第一次出现的位置，所以那列 offsets 不可用；本节改用「实测值 vs 两条候选规则的预测值」来定谁在画，不依赖顺序猜测。

## 六、这轮不能主张的

- 角色判定三条来源都是结构推断，不是设计意图的证词；第一节为 0 条时，结论只能是「本轮没找到该角色的元素」，不等于全应用都不存在这个角色（弹层、错误/离线壳、深色档没驱动）。
- pass2 的「同族 + 最近公共祖先」是我给的启发式：它可能把相邻模块的容器当角色；因此每条都给了家族名、同族元素数与容器矩形，可复核。
- 手机链与号令者端口未参与，读数只在 4826/8726 成立。
