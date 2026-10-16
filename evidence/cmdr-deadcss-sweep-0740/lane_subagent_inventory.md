# 死 CSS 类名清点 v1（_cmdr_deadcss_audit_r1）

只读清点。仓库：`D:/moodle/_cmdr_fe_rev_1016/tip/frontend/src`，分支未动过。输出：本 md + `_cmdr_deadcss_audit_r1.tsv` + `_cmdr_deadcss_audit_r1_evidence.json`。

## 总数

| 项 | 数 |
|---|---|
| .css 文件（src 下） | 29 |
| 样式规则块 | 1808 |
| 选择器里的 class token（去重） | 847 |
| LIVE（>=1 产品读者） | 808 |
| DEAD（0 读者） | 0 |
| TEST-ONLY（产品 0，e2e 有） | 0 |
| UNPROVEN（排不掉动态拼装） | 39 |
| 非 LIVE 且声明里有浅底字面量 | 4 |
| 非 LIVE 且声明里有深字字面量 | 8 |

读者扫描跑的语料：`frontend/src/**.ts` + `**.tsx`（157 枚）+ `frontend/index.html`，注释先剥掉（剥掉 645168 字符），所以「只在注释里被提到」不算读者；边界用 `(?<![-_A-Za-z0-9])token(?![-_A-Za-z0-9])`，因此 `is-active` 不算 `active` 的读者。第二层 `frontend/e2e/**`（215 枚），第三层 contracts/backend/data/public/demo（498 枚，只用于动态拼装的证据），第四层 `dist/assets/*.js`（3 枚，只为认出依赖库注入的类名）。

## 15 枚声明最多的 DEAD token

| token | 声明数 | 声明位置 (file:line) | 浅底字面量 | 深字字面量 | e2e |
|---|---|---|---|---|---|

完整 39 行在 tsv 里（DEAD 0 + TEST-ONLY 0 + UNPROVEN 39）。

## 全部 DEAD（0 枚，按声明数降序）


## TEST-ONLY（0 枚：产品不挂，e2e 在指）


## UNPROVEN（39 枚：排不掉动态拼装，别按 DEAD 处理）

- `.today-actions` — 10 条声明：src/design-tokens.css:902,903; src/styles.css:1644,1650,1659,1663,1668,1669,1670,1676
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['today-acti', 'o', 'n', 's']），子串 grep 'acti' 在产品里有 85 文件：src/api/citynexus.ts:16, src/api/citynexus.ts:38
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：actions(22), today(6)
- `.v8-anchor-row` — 7 条声明：src/styles.css:175,185
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['v8-anchor-', 'r', 'o', 'w']），子串 grep 'anchor' 在产品里有 16 文件：src/app/V8Experience.tsx:1278, src/app/V8Experience.tsx:1282
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：anchor(16), row(70)
- `.v8-trip-metrics` — 7 条声明：src/styles.css:175,185
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['v8-trip-metr', 'i', 'c', 's']），子串 grep 'metr' 在产品里有 12 文件：src/api/citynexus.ts:619, src/api/citynexus.ts:635
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：metrics(1), trip(54)
- `.cn-no-motion` — 5 条声明：src/design-tokens.css:437,440,460,477,486
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['cn-no-mot', 'i', 'o', 'n']），子串 grep 'mot' 在产品里有 5 文件：src/components/v8/MapPanel.tsx:675, src/components/v8/MapPanel.tsx:973
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：motion(4)
- `.v8-cta` — 4 条声明：src/design-tokens.css:437,440,510,513
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['v8-', 'c', 't', 'a']），产品里有 'v8-'：49 文件，src/app/V8Experience.tsx:993, src/app/V8Experience.tsx:998
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：cta(8)
- `.v8-strength` — 4 条声明：src/styles.css:181
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['v8-stren', 'g', 't', 'h']），子串 grep 'stren' 在产品里有 5 文件：src/api/citynexus.ts:537, src/features/trip/SpendPanel.tsx:191
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：strength(5)
- `.v9-live-actions` — 4 条声明：src/styles.css:261,262,280
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['v9-live-acti', 'o', 'n', 's']），子串 grep 'acti' 在产品里有 85 文件：src/api/citynexus.ts:16, src/api/citynexus.ts:38
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：actions(22), live(35)
- `.v8-trip-hero-head` — 3 条声明：src/styles.css:175,185
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['v8-trip-hero-h', 'e', 'a', 'd']），子串 grep 'hero' 在产品里有 4 文件：src/app/V8Experience.tsx:2839, src/app/V8Experience.tsx:3239
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：head(61), hero(4), trip(54)
- `.anchor-line` — 2 条声明：src/styles.css:175
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['anchor-l', 'i', 'n', 'e']），子串 grep 'anchor' 在产品里有 16 文件：src/app/V8Experience.tsx:1278, src/app/V8Experience.tsx:1282
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：anchor(16), line(61)
- `.cn-access-picker` — 2 条声明：src/features/access/access.css:40,52
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['cn-access-pic', 'k', 'e', 'r']），产品里有 'cn-access-pic'：1 文件，src/features/access/AccessPanel.tsx:539, src/features/access/AccessPanel.tsx:579
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：access(13), picker(5)
- `.cn-badge--error` — 2 条声明：src/components/badge.css:53,93
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/components/Badge.tsx:95 的 `cn-badge--${tone}` 能吃下这枚 token（拼出的截=['error']），产品里有 'error'：44 文件，src/api/citynexus.ts:204, src/api/citynexus.ts:212
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：badge(7), error(44)
- `.cn-badge--info` — 2 条声明：src/components/badge.css:77,117
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/components/Badge.tsx:95 的 `cn-badge--${tone}` 能吃下这枚 token（拼出的截=['info']），产品里有 'info'：5 文件，src/components/Badge.tsx:8, src/components/Badge.tsx:32
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：badge(7), info(5)
- `.cn-badge--neutral` — 2 条声明：src/components/badge.css:85,125
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/components/Badge.tsx:95 的 `cn-badge--${tone}` 能吃下这枚 token（拼出的截=['neutral']），产品里有 'neutral'：4 文件，src/app/V8Experience.tsx:4631, src/components/Badge.tsx:8
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：badge(7), neutral(4)
- `.cn-badge--success` — 2 条声明：src/components/badge.css:69,109
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/components/Badge.tsx:95 的 `cn-badge--${tone}` 能吃下这枚 token（拼出的截=['success']），产品里有 'success'：9 文件，src/components/Badge.tsx:8, src/components/Badge.tsx:54
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：badge(7), success(9)
- `.cn-badge--warning` — 2 条声明：src/components/badge.css:61,101
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/components/Badge.tsx:95 的 `cn-badge--${tone}` 能吃下这枚 token（拼出的截=['warning']），产品里有 'warning'：9 文件，src/components/Badge.tsx:8, src/components/Badge.tsx:31
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：badge(7), warning(9)
- `.v8-live-grid` — 2 条声明：src/styles.css:180,184
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['v8-live-g', 'r', 'i', 'd']），子串 grep 'live' 在产品里有 35 文件：src/api/citynexus.ts:1009, src/api/citynexus.ts:1028
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：grid(11), live(35)
- `.cn-badge--solid` — 1 条声明：src/components/badge.css:41
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/components/Badge.tsx:95 的 `cn-badge--${tone}` 能吃下这枚 token（拼出的截=['solid']），产品里有 'solid'：3 文件，src/app/V8Experience.tsx:2125, src/components/Badge.tsx:11
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：badge(7), solid(3)
- `.cn-badge--tinted` — 1 条声明：src/components/badge.css:47
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/components/Badge.tsx:95 的 `cn-badge--${tone}` 能吃下这枚 token（拼出的截=['tinted']），产品里有 'tinted'：6 文件，src/components/Badge.tsx:11, src/features/agent/CopilotDock.tsx:449
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：badge(7), tinted(6)
- `.cn-hero-stagger` — 1 条声明：src/design-tokens.css:591
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['cn-hero-stag', 'g', 'e', 'r']），子串 grep 'hero' 在产品里有 4 文件：src/app/V8Experience.tsx:2839, src/app/V8Experience.tsx:3239
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：hero(4), stagger(0)
- `.cn-spend-unpriced` — 1 条声明：src/features/trip/spend.css:25
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['cn-spend-unpri', 'c', 'e', 'd']），子串 grep 'spend' 在产品里有 5 文件：src/app/V8Experience.tsx:2386, src/app/V8Experience.tsx:2393
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：spend(5), unpriced(3)
- `.cnx-select__empty` — 1 条声明：src/components/cnx-select.css:211
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['cnx-select__em', 'p', 't', 'y']），子串 grep 'cnx' 在产品里有 20 文件：src/app/V8Experience.tsx:3050, src/app/V8Experience.tsx:3051
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：cnx(20), empty(41), select(31)
- `.collections-panel` — 1 条声明：src/cn-pulse.css:395
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['collections-pa', 'n', 'e', 'l']），子串 grep 'collections' 在产品里有 8 文件：src/app/v8PanelRegistry.tsx:6, src/app/v8PanelRegistry.tsx:239
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：collections(8), panel(28)
- `.hub-party-size` — 1 条声明：src/cn-pulse.css:509
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['hub-party-s', 'i', 'z', 'e']），子串 grep 'hub' 在产品里有 11 文件：src/app/V8Experience.tsx:73, src/app/V8Experience.tsx:371
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：hub(11), party(7), size(22)
- `.maplibregl-cooperative-gesture-screen` — 1 条声明：src/design-tokens.css:1598
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['maplibregl-cooperative-gesture-scr', 'e', 'e', 'n']），子串 grep 'gesture' 在产品里有 2 文件：src/components/v8/MapPanel.tsx:890, src/components/v8/MapPanel.tsx:1159
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：cooperative(0), gesture(2), maplibregl(2), screen(30)
- `.maplibregl-desktop-message` — 1 条声明：src/design-tokens.css:1598
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['maplibregl-desktop-mess', 'a', 'g', 'e']），子串 grep 'desktop' 在产品里有 2 文件：src/app/V8Experience.tsx:96, src/app/V8Experience.tsx:507
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：desktop(2), maplibregl(2), message(30)
- `.maplibregl-mobile-message` — 1 条声明：src/design-tokens.css:1598
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['maplibregl-mobile-mess', 'a', 'g', 'e']），子串 grep 'maplibregl' 在产品里有 2 文件：src/components/JourneyMap.tsx:2, src/components/JourneyMap.tsx:111
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：maplibregl(2), message(30), mobile(6)
- `.poi-import-panel` — 1 条声明：src/cn-pulse.css:395
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['poi-import-pa', 'n', 'e', 'l']），产品里有 'poi-import-pa'：1 文件，src/features/poiimport/PoiImportPanel.tsx:441
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：import(130), panel(28), poi(19)
- `.risk-critical` — 1 条声明：src/styles.css:229
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['risk-criti', 'c', 'a', 'l']），子串 grep 'criti' 在产品里有 4 文件：src/api/citynexus.ts:82, src/api/citynexus.ts:848
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：critical(4), risk(12)
- `.risk-safe` — 1 条声明：src/styles.css:230
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['risk-s', 'a', 'f', 'e']），子串 grep 'risk' 在产品里有 12 文件：src/api/citynexus.ts:229, src/api/citynexus.ts:234
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：risk(12), safe(9)
- `.state-active` — 1 条声明：src/styles.css:220
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['state-act', 'i', 'v', 'e']），e2e里有 'state-act'：2 文件，e2e/qoder-bulangong-0557-pretrip-empty-r1.spec.ts:141, e2e/qoder-ord0407-empty-state-actions.spec.ts:40
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：active(41), state(63)
- `.state-arrived` — 1 条声明：src/styles.css:220
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['state-arri', 'v', 'e', 'd']），子串 grep 'arri' 在产品里有 21 文件：src/api/v12Authoritative.ts:90, src/app/V8Experience.tsx:144
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：arrived(5), state(63)
- `.state-completed` — 1 条声明：src/styles.css:219
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['state-comple', 't', 'e', 'd']），子串 grep 'comple' 在产品里有 14 文件：src/api/citynexus.ts:158, src/api/citynexus.ts:190
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：completed(9), state(63)
- `.state-en_route` — 1 条声明：src/styles.css:220
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['state-en_ro', 'u', 't', 'e']），子串 grep 'state' 在产品里有 63 文件：src/api/citynexus.ts:218, src/api/citynexus.ts:270
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：route(26), state(63)
- `.state-in_progress` — 1 条声明：src/styles.css:220
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['state-in_progr', 'e', 's', 's']），子串 grep 'progr' 在产品里有 13 文件：src/demo/goldenScenario.ts:59, src/features/agent/AgentComposer.tsx:291
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：progress(13), state(63)
- `.state-skipped` — 1 条声明：src/styles.css:219
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['state-skip', 'p', 'e', 'd']），子串 grep 'skip' 在产品里有 9 文件：src/api/v12Authoritative.ts:90, src/app/V8Experience.tsx:4766
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：skipped(7), state(63)
- `.v8-empty-hint` — 1 条声明：src/cn-pulse.css:518
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['v8-empty-h', 'i', 'n', 't']），子串 grep 'empty' 在产品里有 41 文件：src/api/citynexus.ts:695, src/api/citynexus.ts:698
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：empty(41), hint(10)
- `.v8-hero-title` — 1 条声明：src/design-tokens.css:294
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['v8-hero-ti', 't', 'l', 'e']），子串 grep 'hero' 在产品里有 4 文件：src/app/V8Experience.tsx:2839, src/app/V8Experience.tsx:3239
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：hero(4), title(79)
- `.v8-home-language` — 1 条声明：src/design-tokens.css:985
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['v8-home-langu', 'a', 'g', 'e']），子串 grep 'home' 在产品里有 4 文件：src/app/V8Experience.tsx:503, src/components/ProductErrorBoundary.tsx:44
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：home(4), language(7)
- `.v8-user-meta` — 1 条声明：src/cn-pulse.css:509
  - 为什么排不掉：模板字符串拼出来的可能性排不掉：src/features/agent/CopilotDock.tsx:844 的 `cn-copilot-dock ${expanded ? "open" : "colla` 能吃下这枚 token（拼出的截=['v8-user-m', 'e', 't', 'a']），子串 grep 'user' 在产品里有 14 文件：src/api/citynexus.ts:139, src/api/citynexus.ts:585
  - 我跑的子串 grep（token 拆成的词片 -> 产品源码里命中的文件数）：meta(19), user(14)

## 逃逸口（非 LIVE 声明里的字面浅底/深字）

- `.today-actions` [UNPROVEN] 浅底 0 条：
- 深字 2 条：src/styles.css:1668 深字 hex=#1c7a4a; src/styles.css:1669 深字 hex=#b45309
- `.v8-strength` [UNPROVEN] 浅底 1 条：
    - src/styles.css:181 浅底 hex = #e9ebf1 (L=0.831)
- 深字 1 条：src/styles.css:181 深字 hex=#68758a
- `.anchor-line` [UNPROVEN] 浅底 1 条：
    - src/styles.css:175 浅底 hex = #dfe3ea (L=0.766)
- 深字 0 条：-
- `.risk-critical` [UNPROVEN] 浅底 1 条：
    - src/styles.css:229 浅底 hex = #fff7f5 (L=0.944)
- 深字 0 条：-
- `.risk-safe` [UNPROVEN] 浅底 1 条：
    - src/styles.css:230 浅底 hex = #f5fbf7 (L=0.951)
- 深字 0 条：-
- `.state-active` [UNPROVEN] 浅底 0 条：
- 深字 1 条：src/styles.css:220 深字 hex=#3f6f92
- `.state-arrived` [UNPROVEN] 浅底 0 条：
- 深字 1 条：src/styles.css:220 深字 hex=#3f6f92
- `.state-completed` [UNPROVEN] 浅底 0 条：
- 深字 1 条：src/styles.css:219 深字 hex=#5d7c69
- `.state-en_route` [UNPROVEN] 浅底 0 条：
- 深字 1 条：src/styles.css:220 深字 hex=#3f6f92
- `.state-in_progress` [UNPROVEN] 浅底 0 条：
- 深字 1 条：src/styles.css:220 深字 hex=#3f6f92
- `.state-skipped` [UNPROVEN] 浅底 0 条：
- 深字 1 条：src/styles.css:219 深字 hex=#5d7c69

## 判据与坑

- 判「在用」= 该 token 作为独立词出现在产品源码（含 `className="a b c"` 的空格分词、`classList.add("x")`、模板字符串里的字面量）。
- 判「排不掉动态拼装」= 源码里有 `className={\`前缀-${x}-后缀\`}` 这类带字面锚的模式能吃下这枚 token，且拼出来的那截在产品/e2e/数据里查得到；或者存在整槽来自变量的 className（`className={\`base ${x.status}\`}`，共 13 处裸槽，涉及 ${aiPreflightClass(aiState)}, ${compact ? "compact" : ""}, ${copy.tone}, ${costKnown ? band.key : "unknown"}, ${item.id === now?.id ? "current" : ""}, ${item.role}, ${job.terminal ? "terminal" : "running"}, ${passed ? "passed" : "blocked"}）而该 token 又是契约/数据里的字面取值。
- `:not(.x)` 里的 x 是行为开关（即使 DOM 上从不挂，删了也会让 :not 恒真），这类单列：共 1 枚只出现在 :not() 里。
- 亮度用 r2 那套 sRGB 相对亮度：浅底 >0.72，深字 <0.22。
