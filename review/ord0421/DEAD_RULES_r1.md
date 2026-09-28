# ORD-0421 CSS 死规则普查 · 读数（0 产品字节）

- 生成时间 2026-09-29T01:02:12+0800，仪表 `cmdr_css_census_r3.js`（本目录）。
- 被量产物：现尖 `8a7665be2061a2f38aa2227f81c57003ca4caacb` 的 frontend 构建，浏览器实载 CSS = ["index-D_Fr6K4L.css"]。
- 场景：{"locales": ["zh", "en"], "shapes": ["390x844", "320x653", "414x896"], "routes": ["hub", "live", "map", "studio", "stay", "discover", "bookings", "agent", "authoritative", "intelligence", "twin", "trash", "trips", "me"], "drawer_open_swept": true}，扫过 sweep 次数 = 168。
- 规则总数 rules_parsed = 1378，去重后唯一选择器 unique_selectors = 1065。
- 全场景 0 命中的选择器 zero_exact = 715，分类分布 class_counts = {"DEAD_RULE_TARGET_PRESENT": 2, "DEAD_RULE_NO_CONSUMER": 27, "NOT_SURE_NOT_IN_LOADED_CSS": 94, "STATEFUL_NOT_DEAD": 23, "NOT_SURE_LEAF_NOT_FOUND": 309, "NOT_SURE_CONTEXT_NOT_MOUNTED": 260}。

## 一、判成真缺陷（上下文在屏上、叶子也在其内，完整选择器仍 0 命中）

这一类的判据不是「没命中」，而是三条同时成立：祖先上下文 querySelectorAll 命中 > 0、在该上下文内部再查叶子命中 > 0、完整选择器命中 = 0。也就是选择器写的结构关系在 DOM 里不存在。

| # | 选择器 | path:line | 上下文 | 上下文命中 | 叶在其内 | 其中非直接子级 | 屏上实际（摘） | 用户会看见什么差别 |
|---|---|---|---|---|---|---|---|---|
| 1 | `#v8-nav-drawer > button` | styles.css:331 | `#v8-nav-drawer` | 1 | 15 | 15 | button.active「今天」 display=block align-items=normal gap=normal | 用户会看见的差别：排版方式（display）现在实际是 block，规则写的是 flex；对齐（align-items）现在实际是 normal，规则写的是 center；间隙（gap）现在实际是 normal，规则写的是 12px。 |
| 2 | `#v8-nav-drawer > button.active` | styles.css:337, styles.css:338 | `#v8-nav-drawer` | 1 | 1 | 1 | button.active「今天」 color=rgb(255, 255, 255) background=rgb(66, 89, 216) none repeat scroll 0% 0% / auto padding-box border-box | 用户会看见的差别：字色（color）现在实际是 rgb(255, 255, 255)，规则写的是 var(--v8-ink)；底色（background）现在实际是 rgb(66, 89, 216) none repeat scroll 0% 0% / auto padding-box border-box，规则写的是 #f1f3ff。 |

## 二、叶子类名/id 在 frontend/src 里一次都没出现（无消费者）

判据是对 `frontend/src` 下所有 `.ts/.tsx/.js/.jsx/.html` 做一次子串扫描（CSS 自身排除）。子串匹配偏保守：只要该名字在任何一处出现就不算缺。运行时拼出来的类名仍可能被骗过去，所以这一类只作候选、不称铁证。

| # | 选择器 | path:line | 缺的名字 | 规则要设 |
|---|---|---|---|---|
| 1 | `.anchor-line` | styles.css:168 | .anchor-line | flex: 1, height: 1px, background: #dfe3ea |
| 2 | `.cn-copilot-runtime` | styles.css:359, styles.css:365 | .cn-copilot-runtime | display: flex, align-items: center, gap: 10px |
| 3 | `.cn-native-status` | styles.css:394 | .cn-native-status | flex: none, padding: 4px 6px, border-radius: 5px, color: #53627b |
| 4 | `.cn-native-status.active` | styles.css:395 | .cn-native-status | color: #4c579d, background: #e9eaff |
| 5 | `.cn-native-status.terminal` | styles.css:396 | .cn-native-status | color: #4c7d63, background: #e6f3eb |
| 6 | `.state-arrived` | styles.css:214 | .state-arrived | color: #3f6f92 |
| 7 | `.state-en_route` | styles.css:214 | .state-en_route | color: #3f6f92 |
| 8 | `.state-in_progress` | styles.css:214 | .state-in_progress | color: #3f6f92 |
| 9 | `.state-skipped` | styles.css:213 | .state-skipped | color: #5d7c69 |
| 10 | `.today-actions` | styles.css:1539, styles.css:1571 | .today-actions | display: grid, grid-template-columns: repeat(3, minmax(0, 1fr)), gap: 10px, margin: 16px 0 4px |
| 11 | `.v12-risk-banner.risk-critical` | styles.css:223 | .risk-critical | background: #fff7f5 |
| 12 | `.v12-risk-banner.risk-safe` | styles.css:224 | .risk-safe | background: #f5fbf7 |
| 13 | `.v8-anchor-row` | styles.css:168, styles.css:178 | .v8-anchor-row | display: flex, align-items: center, gap: 15px |
| 14 | `.v8-hero-title` | design-tokens.css:235 | .v8-hero-title | font-size: var(--cn-fs-display), font-weight: 700, line-height: var(--cn-lh-tight), letter-spacing: -0.02em |
| 15 | `.v8-live-grid` | styles.css:173, styles.css:177 | .v8-live-grid | display: grid, grid-template-columns: minmax(0, 1.3fr) minmax(280px, .7fr), gap: 18px |
| 16 | `.v8-maplibre-canvas .maplibregl-cooperative-gesture-screen .maplibregl-desktop-message` | design-tokens.css:1330 | .maplibregl-desktop-message | padding: var(--cn-s-8) var(--cn-s-12), border: 1px solid var(--cn-hairline), border-radius: var(--cn-r-control), background: var(--cn-surface) |
| 17 | `.v8-maplibre-canvas .maplibregl-cooperative-gesture-screen .maplibregl-mobile-message` | design-tokens.css:1333 | .maplibregl-mobile-message | padding: var(--cn-s-8) var(--cn-s-12), border: 1px solid var(--cn-hairline), border-radius: var(--cn-r-control), background: var(--cn-surface) |
| 18 | `.v8-page a.v8-cta:active` | design-tokens.css:268 | .v8-cta | transform: scale(0.985) |
| 19 | `.v8-rain-button` | styles.css:167, styles.css:167, styles.css:183, styles.css:275, styles.css:311 | .v8-rain-button | display: inline-flex, align-items: center, justify-content: center, gap: 8px |
| 20 | `.v8-section-title` | design-tokens.css:236 | .v8-section-title | font-size: var(--cn-fs-title), font-weight: 700, line-height: var(--cn-lh-tight), letter-spacing: -0.015em |
| 21 | `.v8-strength` | styles.css:174 | .v8-strength | display: flex, align-items: center, gap: 8px, height: 6px |
| 22 | `.v8-trip-hero-head` | styles.css:168, styles.css:178 | .v8-trip-hero-head | display: flex, justify-content: space-between, gap: 20px |
| 23 | `.v8-trip-metrics` | styles.css:168, styles.css:178 | .v8-trip-metrics | display: grid, grid-template-columns: repeat(3, 1fr), gap: 12px, padding: 16px 0 |
| 24 | `.v9-live-actions` | styles.css:255, styles.css:274 | .v9-live-actions | display: flex, align-items: center, gap: 8px |
| 25 | `.v8-home-language` | design-tokens.css:746 | .v8-home-language |  |
| 26 | `.v8-page a.v8-cta` | design-tokens.css:270, design-tokens.css:280, design-tokens.css:285 | .v8-cta |  |
| 27 | `.v8-page-intro .v8-rain-button` | styles.css:178 | .v8-rain-button |  |

## 三、STATEFUL_NOT_DEAD（不算死规则，仪表看不见状态）

| 选择器 | path:line | 为什么不算 |
|---|---|---|
| `.v8-page button:not(.cn-no-motion):active` | design-tokens.css:266 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `#v8-nav-drawer > button:hover` | styles.css:337 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `.cn-copilot-stop:hover` | styles.css:423 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `.family-chip:disabled` | styles.css:66 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `.plan-ai-field textarea::placeholder` | styles.css:852 | 伪元素：querySelectorAll 永远看不见 ::before/::after |
| `.trial-field input::placeholder` | design-tokens.css:1140 | 伪元素：querySelectorAll 永远看不见 ::before/::after |
| `.trial-field textarea::placeholder` | design-tokens.css:1141 | 伪元素：querySelectorAll 永远看不见 ::before/::after |
| `.trial-steps li span:last-child` | styles.css:485 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `.trial-steps li:not(.active) span:last-child` | design-tokens.css:1109 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `.v12-trip-studio .v8-activity:active` | styles.css:1751 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `.v8-day-card:hover` | styles.css:170 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `.v8-mode-option:disabled` | styles.css:293 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `.v8-nav button:hover` | styles.css:145, design-tokens.css:741 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `.v8-page :focus-visible` | design-tokens.css:277 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `.v8-page .v8-card:hover` | design-tokens.css:273 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `.v8-primary-button:disabled` | styles.css:695 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `.v9-evidence-summary::-webkit-details-marker` | styles.css:324 | 伪元素：querySelectorAll 永远看不见 ::before/::after |
| `::view-transition-new(root)` | styles.css:351, styles.css:447 | 伪元素：querySelectorAll 永远看不见 ::before/::after |
| `::view-transition-old(root)` | styles.css:350, styles.css:447 | 伪元素：querySelectorAll 永远看不见 ::before/::after |
| `:focus-visible` | design-tokens.css:796 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `.v8-product-shell :focus-visible` | design-tokens.css:797 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `.v8-product-shell button:focus-visible` | styles.css:287, design-tokens.css:798 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |
| `.v8-product-shell textarea:focus-visible` | styles.css:287, design-tokens.css:800 | 状态式或结构性伪类：需要指针悬停、键盘聚焦、表单值或兄弟位次 |

## 四、NOT_SURE（点名缺哪一个读数，不计数）

- `NOT_SURE_LEAF_NOT_FOUND`：309 条。去组合符后叶子也没在走过的屏幕里出现，同缺上面那个状态读数。
- `NOT_SURE_CONTEXT_NOT_MOUNTED`：260 条。它们要的上下文在走过的 14 屏 × 2 语言 × 3 形状里一次都没挂载，缺的是能挂载它的那个状态：弹层/抽屉内特定分组/错误提示/离线壳/深色档。
- `NOT_SURE_NOT_IN_LOADED_CSS`：94 条。这些选择器不在浏览器实载的 CSS 字节里（被 tree-shake/未 import/写错文件），本单的 DOM 探针判不了它们。

## 五、正对照（仪表必须能抓到已知的那三条，否则普查不可信）

- 号令者亲测的抽屉一族被本仪表抓到 2 条：`#v8-nav-drawer > button` @ styles.css:331; `#v8-nav-drawer > button.active` @ styles.css:337, styles.css:338。
  - `#v8-nav-drawer > button`：用户会看见的差别：排版方式（display）现在实际是 block，规则写的是 flex；对齐（align-items）现在实际是 normal，规则写的是 center；间隙（gap）现在实际是 normal，规则写的是 12px。
  - `#v8-nav-drawer > button.active`：用户会看见的差别：字色（color）现在实际是 rgb(255, 255, 255)，规则写的是 var(--v8-ink)；底色（background）现在实际是 rgb(66, 89, 216) none repeat scroll 0% 0% / auto padding-box border-box，规则写的是 #f1f3ff。

## 六、这轮不能主张的

- 手机链（:4781 / :4782 / :8693）与号令者的 :4805 我都没连，也没重起；读数只在我自起的端口上成立。
- 弹层、错误提示、离线壳、深色档这些状态本轮没有驱动，落在第四节里；把它们的挂载条件补进扫屏后，第三/四节里的一部分会挪进第一节或彻底消失，那不是本轮的结论。
- 「用户会看见什么差别」是把规则值与元素计算值做差得到的句子，不是设计判断；值相同的那些我写成死重量，不等于可以删——删除是另一个单的事。
