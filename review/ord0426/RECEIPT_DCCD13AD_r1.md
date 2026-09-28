# ORD-0426 收据 · 分诊结论钉在现尖（0 产品字节，只读重跑）

- 生成 2026-09-29T03:13:11+0800；仪表沿用已入账的 `cmdr_orphan_repoint_r2.js` 与 `cmdr_orphan_repoint_pass2.js`（本目录），一字未改，被量尖由命令行参数传入。
- 被量代次 tip=dccd13ad66ea35e9a6d7ca7a3d91a1ae9a579808，页面实载资产（按名字钉代次）["index-ChP6V0Vj.js", "index-DeE4nurx.css"]。
- 上一枚被量的代次 tip=fb6131f359e85deb18a2194494dc9a96e328cdee，实载 ["index-DMJE_sMd.js", "index-Dm2cFpiB.css"]：两代 CSS 与 JS 资产名字都不同（ORD-0417 与 ORD-0425 改过 frontend/src，含 map-selection.css 与 MapPanel.tsx），所以这不是同一份字节重述一遍。
- 两份 CSS 源码本身在两代之间未变：styles.css 与 design-tokens.css 的 blob 与上一代逐字相同，变的是页面 DOM 与合成后的 CSS——这正是要重跑的理由：结论靠的是屏上命中，不是靠文件文本。

## 钉住的结论

- 输入 wanted=27（来自已入账的 ORD-0421 普查件 review/ord0421/census_r3.json），本尖重解析唯一选择器 rules_parsed_on_this_tip=1378。
- 场景 pass1 {"locales": ["zh", "en"], "shapes": ["390x844", "320x653", "414x896"], "routes": ["hub", "live", "map", "studio", "stay", "discover", "bookings", "agent", "authoritative", "intelligence", "twin", "trash", "trips", "me"]}，heading_samples=146；pass2 widths=[320, 360, 390, 414, 800, 1280] × routes=["hub", "live", "map", "studio", "stay", "twin", "intelligence", "agent", "trips", "me"]。
- 分诊计数 orphan_repoint=0，其余 {"INTENT_APPLIED_VIA_GROUP_SIBLING": 10, "THIRD_PARTY_DOM_NOT_DEAD": 2, "DEAD_LEGACY": 15}；pass2 对 dead_legacy 那批再探容器：{"DEAD_LEGACY_CONFIRMED_NO_CONTAINER": 15}。
- 与上一代逐条对照：per_rule_class_identical=27/27，不同的选择器条数 0。
- 所以「那 27 条里没有一条需要 repoint」这句话现在有两枚独立代次支撑，不是单点读数。

## 再往上一枚尖的确认跑（追尖不靠猜）：tip=3b6c96e8a9f986672ddaa764f5f2ae69534ceff1

- 收据写完后权威线又前进 6 笔（含 RealCityDiscoveryPanel / TwinPanel / V14RecoveryTruthPanel / LocaleContext 四份 frontend 文件，都是我这轮走到的屏），所以我又在最新尖上跑了一遍同一仪表：
- 该代次页面实载 ["index-oR3PVCYW.js", "index-DeE4nurx.css"]（JS 名字换了、CSS 名字未变，说明变的是组件不是样式表），heading_samples=74，class_counts={"INTENT_APPLIED_VIA_GROUP_SIBLING": 10, "THIRD_PARTY_DOM_NOT_DEAD": 2, "DEAD_LEGACY": 15}，orphan_repoint=0。
- 与全量那次逐条对照 per_rule_class_identical=27/27，不同的选择器条数 0；h1 不在档位的屏数 h1_off=0。
- 可复现形式记在这里供后续单参照：全量跑（2 语言 × 3 形状 × 14 屏 × 抽屉两态）钉一次代次即可，线再往前时只跑单语言 3 形状 14 屏的确认趟（约 1/3 机器时间），两趟结论一致才算钉住。

## 你原先担心的那两枚字号规则（现尖复述，值都是重测的）

- `.v8-hero-title` 自身命中 own_hits_max=0，同组另一半 `.v8-page h1` 屏上命中 {".v8-page h1": 2}。
- `.v8-section-title` 自身命中 own_hits_max=0，同组 `.v8-page h2` 命中 {".v8-page h2": 3}。
- h1 实算字号按宽度 {"320": ["34px"], "360": ["34px"], "390": ["34px"], "414": ["34px"], "800": ["34px"], "1280": ["34px"]}，token --cn-fs-display 解析为 34px；h1 不在档位上的屏数 h1_off=0。
- 顺带仍成立：styles.css 里两条随视口写的 h1 规则按公式应得的值与实测不符，画 h1 的是 token 档那一条。

## 边界

- 本收据只覆盖那 27 条与走到的 14 屏 × 2 语言 × 3 形状；弹层、错误/离线壳、深色档没驱动，dead_legacy 那批里若有服务于那些状态的规则，本收据不称它们可删。
- 只读：没有改任何产品文件；本目录只新增收据与其原始件。
- 手机链与号令者端口未参与；读数在本车道 backend_port=8736 与 front_port=4836 上成立。
