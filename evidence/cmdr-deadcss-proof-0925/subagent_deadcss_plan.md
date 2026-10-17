# 死类名剥离工单（快照 f2e5081 复测版）

- 被测对象：`D:/moodle/_agent_dead_snap_1017/frontend`（git `f2e5081077629433d4e163409e8f786a5eae759f` 的冻结导出，全程只读；已核它与 `D:/moodle/_cmdr_fe_rev_1016/tip/frontend/src` 逐字节相同，而 `tip` 的 HEAD 就是这枚 revision）。
- 生成器：`_agent_dead_arms_r1.py`（甲臂）· `_agent_dead_armb_r1.py`（乙臂）· `_agent_dead_server_check_r1.py`（丙臂的树比对）· `_agent_dead_census_r1.py`（整棵快照点名）· `_agent_dead_plan_r1.py`（工单）· `_agent_dead_check_edits_r1.py`（把工单在内存里演一遍）· `_agent_dead_selftest_r1.py`（探测器自测）。
- 判据沿用 `_cmdr_deadcss_sweep_r1.py`：边界正则（禁子串）+ 连字符/下划线前缀比对 + `collect_selector_list()` 倒吃逗号 + `neg_guard()`。

## 分母（先把口径钉死，下面的 0 才是有分母的 0）

| 臂 | 看了多少 | 说明 |
|---|---|---|
| 甲 静态读者 | 157 个 `.tsx/.ts` + 1 个 `index.html` | `frontend/src` 全量，非子串、带边界 |
| 甲 宽口径 | 另 427 个 `.ts/.tsx` | `src` 之外（e2e、.storybook、docs 里的脚本）；13 枚 token 在这些里也是 0 命中 |
| 乙 动态拼装 | 141 处现场，其中 31 处真能落到 class 属性上 | 模板串前后槽、字符串相加、classList、imperative `.className=`、数组 push/join；clsx/cn/cx/classNames/twMerge 这类 helper 在产品码里计数为 0 |
| 丙 真屏 | 0 枚（本臂未跑） | 服务树与快照不同一棵，见下 |

探测器不是坏掉的零（正对照，当场咬住）：
- 甲 `v8-page` -> 边界读者 36 处，近似 25 处（活类：产品码里必有边界读者）
- 甲 `cn-access-picker` -> 边界读者 0 处，近似 6 处（禁删枚：只该有近似命中（-label / -hint），边界读者也应有）
- 甲 `cn-badge` -> 边界读者 1 处，近似 4 处（禁删枚：字面量以 cn-badge--${tone} 拼装，边界不命中但近似必命中）
- 乙 `cn-badge--error` -> 咬到 ["src/components/Badge.tsx:95 'cn-badge--'"]（Badge.tsx:95 `cn-badge--${tone}`（前槽））
- 乙 `cn-badge--anchor` -> 咬到 ["src/components/Badge.tsx:95 'cn-badge--'"]（Badge.tsx:96 classes.push 字面量 + join（前槽））
- 乙 `v8-empty-hint-SUFFIX-CONTROL` -> 咬到 ["SELFTEST/synthetic.tsx:0 '-empty-hint'"]（合成现场 `${x}-empty-hint` 必须被后槽判据咬住）

## 逐枚判语与工单（file:line 与读数同一行）

| token | 现场（本次重读） | 判语 | 甲 读者/分母 | 甲 近似 | 乙 命中/分母 | 丙 | 悬空风险 | 这一刀 | 字节 前→后 |
|---|---|---|---|---|---|---|---|---|---|
| `v8-anchor-row` | `src/styles.css:175`、`src/styles.css:185` | `ARM_C_NOT_RUN` | 0 / 157 文件 + 1 html | 0 处 | 0 / 141 | 未跑 | 否 | drop_rule_block @styles.css:175-175；drop_rule_block @styles.css:175-175；drop_rule_block @styles.css:175-175；drop_rule_block @styles.css:175-175 | `1988→1528`、`2696→2626` |
| `v8-trip-metrics` | `src/styles.css:175`、`src/styles.css:185` | `ARM_C_NOT_RUN` | 0 / 157 文件 + 1 html | 0 处 | 0 / 141 | 未跑 | 否 | drop_rule_block @styles.css:175-175；drop_rule_block @styles.css:175-175；drop_rule_block @styles.css:175-175；drop_rule_block @styles.css:175-175 | `1988→1525`、`2696→2577` |
| `v8-trip-hero-head` | `src/styles.css:175`、`src/styles.css:185` | `ARM_C_NOT_RUN` | 0 / 157 文件 + 1 html | 0 处 | 0 / 141 | 未跑 | 否 | drop_rule_block @styles.css:175-175；drop_rule_block @styles.css:185-185；drop_rule_block @styles.css:185-185；drop_rule_block @styles.css:175-175 | `1988→1908`、`2696→2601` |
| `anchor-line` | `src/styles.css:175` | `ARM_C_NOT_RUN` | 0 / 157 文件 + 1 html | 0 处 | 0 / 141 | 未跑 | 否 | drop_rule_block @styles.css:175-175 | `1988→1929` |
| `v8-live-grid` | `src/styles.css:180`、`src/styles.css:184` | `ARM_C_NOT_RUN` | 0 / 157 文件 + 1 html | 0 处 | 0 / 141 | 未跑 | 否 | drop_rule_block @styles.css:179-180；strip_branch @styles.css:184-184；drop_rule_block @styles.css:179-180；strip_branch @styles.css:184-184 | `5035→4930`、`562→547` |
| `v8-strength` | `src/styles.css:181` | `ARM_C_NOT_RUN` | 0 / 157 文件 + 1 html | 0 处 | 0 / 141 | 未跑 | 否 | drop_rule_block @styles.css:181-181；drop_rule_block @styles.css:181-181；drop_rule_block @styles.css:181-181；drop_rule_block @styles.css:181-181 | `2598→2206` |
| `v9-live-actions` | `src/styles.css:278` | `ARM_C_NOT_RUN` | 0 / 157 文件 + 1 html | 0 处 | 0 / 141 | 未跑 | 否 | drop_rule_block @styles.css:278-278；drop_rule_block @styles.css:278-278 | `248→126` |
| `v8-cta` | `src/design-tokens.css:440`、`src/design-tokens.css:514` | `ARM_C_NOT_RUN` | 0 / 157 文件 + 1 html | 0 处 | 0 / 141 | 未跑 | 否 | strip_branch @design-tokens.css:440-440；strip_branch @design-tokens.css:514-514；strip_branch @design-tokens.css:440-440；strip_branch @design-tokens.css:514-514 | `18→0`、`57→38` |
| `v8-home-language` | `src/design-tokens.css:991` | `ARM_C_NOT_RUN` | 0 / 157 文件 + 1 html | 0 处 | 0 / 141 | 未跑 | **是** | strip_last_branch_repair @design-tokens.css:990-991 | `33→14` |
| `collections-panel` | `src/cn-pulse.css:396` | `ARM_C_NOT_RUN` | 0 / 157 文件 + 1 html | 0 处 | 0 / 141 | 未跑 | 否 | strip_branch @cn-pulse.css:396-396 | `19→0` |
| `poi-import-panel` | `src/cn-pulse.css:397` | `ARM_C_NOT_RUN` | 0 / 157 文件 + 1 html | 0 处 | 0 / 141 | 未跑 | **是** | strip_last_branch_repair @cn-pulse.css:396-397 | `39→20` |
| `v8-user-meta` | `src/cn-pulse.css:510` | `ARM_C_NOT_RUN` | 0 / 157 文件 + 1 html | 0 处 | 0 / 141 | 未跑 | 否 | strip_branch @cn-pulse.css:510-510 | `14→0` |
| `v8-empty-hint` | `src/cn-pulse.css:514` | `ARM_C_NOT_RUN` | 0 / 157 文件 + 1 html | 0 处 | 0 / 141 | 未跑 | **是** | strip_last_branch_repair @cn-pulse.css:513-514 | `40→24` |

注：`before/after` 的字节是**受影响的整组物理行**的长度（摘表尾支那一类会牵到相邻两行，成组给才不会看错位）；逐枚的孤立工单与合并一趟的工单都在 `_agent_dead_plan.json` 里（`entries[].per_site[]` 与 `compound_single_pass[]`）。

## 每枚 token 的原文 before/after

### `v8-anchor-row` — ARM_C_NOT_RUN

- 备注：styles.css:175 里有 5 条规则、:185(@media 680) 里有 2 条规则都只服务这枚死类；其中 175 的 `.v8-anchor-row div:not(.anchor-line){min-width:0}` 一并随本枚删除，不要单独去动 :not() 里的 anchor-line。
- 甲：边界读者 0 处（分母 157 个 .tsx/.ts + index.html）；近似命中 0 处；`src` 外宽口径 427 个文件里 0 处。
- 乙：拼装现场 141 处里命中 0 处（能落到 class 的 31 处中 0 处）。也没有同形嫌疑。
- 丙：未跑（服务树不等于快照，见下节）。
- **本次新发现的现场（旧清单上没有）**：`src/styles.css:175`

  孤立工单 `src/styles.css:175`：整组替换
  ```css
  .v8-hero-grid { display: grid; grid-template-columns: minmax(0, 1.14fr) minmax(340px, .86fr); gap: 18px; }.v8-trip-hero { padding: 28px 30px 24px; border: 1px solid #dfe4ed; border-radius: var(--cn-r-16); background: var(--v8-panel); box-shadow: 0 12px 30px #1b2d5510; }.v8-trip-hero-head { display: flex; justify-content: space-between; gap: 20px; }.v8-status-pill { display: inline-flex; align-items: center; gap: 5px; padding: var(--cn-s-6) 9px; border-radius: var(--cn-r-pill); color: var(--cn-success-text); background: var(--cn-elev-1); font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }.v8-status-pill.violet { color: var(--v8-violet); background: #f3efff; }.v8-trip-hero h2 { margin: 18px 0 8px; font-size: 24px; letter-spacing: -.03em; }.v8-trip-hero p { display: flex; align-items: center; gap: 7px; margin: 0; color: #7b8798; font-size: 12px; }.v8-trip-
  ```
  改后：
  ```css
  .v8-hero-grid { display: grid; grid-template-columns: minmax(0, 1.14fr) minmax(340px, .86fr); gap: 18px; }.v8-trip-hero { padding: 28px 30px 24px; border: 1px solid #dfe4ed; border-radius: var(--cn-r-16); background: var(--v8-panel); box-shadow: 0 12px 30px #1b2d5510; }.v8-trip-hero-head { display: flex; justify-content: space-between; gap: 20px; }.v8-status-pill { display: inline-flex; align-items: center; gap: 5px; padding: var(--cn-s-6) 9px; border-radius: var(--cn-r-pill); color: var(--cn-success-text); background: var(--cn-elev-1); font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }.v8-status-pill.violet { color: var(--v8-violet); background: #f3efff; }.v8-trip-hero h2 { margin: 18px 0 8px; font-size: 24px; letter-spacing: -.03em; }.v8-trip-hero p { display: flex; align-items: center; gap: 7px; margin: 0; color: #7b8798; font-size: 12px; }.v8-trip-
  ```
  字节 1988 → 1528；删掉的子串：`.v8-anchor-row { display: flex; align-items: center; gap: 15px; padding-top: 18p` / `.v8-anchor-row div:not(.anchor-line) { min-width: 0; }` / `.v8-anchor-row span, .v8-anchor-row small { display: block; color: #9ca5b1; font` / `.v8-anchor-row b { display: block; margin: 5px 0 var(--cn-s-2); font-size: 12px;` / `.v8-anchor-row small { font-size: 11px; letter-spacing: 0; white-space: nowrap; ` / `.v8-anchor-row { gap: 9px; }` / `.v8-anchor-row small { max-width: 110px; }`
  - 这一刀的回读：花括号 1063/1063 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

  孤立工单 `src/styles.css:185`：整组替换
  ```css
  @media (max-width: 680px) { .v8-product-shell { display: block; padding-bottom: var(--cn-nav-clearance); }.v8-sidebar { display: none; }.v8-topbar { min-height: 58px; padding: var(--cn-safe-top) 17px 0; }.v8-mobile-menu { display: block; width: auto; margin: 0; padding: 0; color: var(--v8-ink); font-size: 0; }.v8-mobile-menu:after { content: "≡"; font-size: 20px; }.v8-breadcrumb span, .v8-runtime, .v8-icon-button { display: none; }.v8-top-actions { gap: 8px; }.v8-content { padding: 27px 17px 34px; }.v8-message { margin: 13px 17px -5px; }.v8-page-intro { display: block; margin-bottom: 24px; }.v8-page-intro .v8-primary, .v8-page-intro .v8-outline-button { margin-top: 18px; }.v8-page h1 { font-size: 30px; }.v8-lede { font-size: 13px; }.v8-trip-hero { padding: 22px 19px; }.v8-trip-hero-head { display: block; }.v8-trip-hero-head .v8-quiet-button { margin-top: 15px; }.v8-trip-hero h2 { font-si
  ```
  改后：
  ```css
  @media (max-width: 680px) { .v8-product-shell { display: block; padding-bottom: var(--cn-nav-clearance); }.v8-sidebar { display: none; }.v8-topbar { min-height: 58px; padding: var(--cn-safe-top) 17px 0; }.v8-mobile-menu { display: block; width: auto; margin: 0; padding: 0; color: var(--v8-ink); font-size: 0; }.v8-mobile-menu:after { content: "≡"; font-size: 20px; }.v8-breadcrumb span, .v8-runtime, .v8-icon-button { display: none; }.v8-top-actions { gap: 8px; }.v8-content { padding: 27px 17px 34px; }.v8-message { margin: 13px 17px -5px; }.v8-page-intro { display: block; margin-bottom: 24px; }.v8-page-intro .v8-primary, .v8-page-intro .v8-outline-button { margin-top: 18px; }.v8-page h1 { font-size: 30px; }.v8-lede { font-size: 13px; }.v8-trip-hero { padding: 22px 19px; }.v8-trip-hero-head { display: block; }.v8-trip-hero-head .v8-quiet-button { margin-top: 15px; }.v8-trip-hero h2 { font-si
  ```
  字节 2696 → 2626；删掉的子串：`.v8-anchor-row { display: flex; align-items: center; gap: 15px; padding-top: 18p` / `.v8-anchor-row div:not(.anchor-line) { min-width: 0; }` / `.v8-anchor-row span, .v8-anchor-row small { display: block; color: #9ca5b1; font` / `.v8-anchor-row b { display: block; margin: 5px 0 var(--cn-s-2); font-size: 12px;` / `.v8-anchor-row small { font-size: 11px; letter-spacing: 0; white-space: nowrap; ` / `.v8-anchor-row { gap: 9px; }` / `.v8-anchor-row small { max-width: 110px; }`
  - 这一刀的回读：花括号 1063/1063 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

### `v8-trip-metrics` — ARM_C_NOT_RUN

- 甲：边界读者 0 处（分母 157 个 .tsx/.ts + index.html）；近似命中 0 处；`src` 外宽口径 427 个文件里 0 处。
- 乙：拼装现场 141 处里命中 0 处（能落到 class 的 31 处中 0 处）。也没有同形嫌疑。
- 丙：未跑（服务树不等于快照，见下节）。
- **本次新发现的现场（旧清单上没有）**：`src/styles.css:185`

  孤立工单 `src/styles.css:175`：整组替换
  ```css
  .v8-hero-grid { display: grid; grid-template-columns: minmax(0, 1.14fr) minmax(340px, .86fr); gap: 18px; }.v8-trip-hero { padding: 28px 30px 24px; border: 1px solid #dfe4ed; border-radius: var(--cn-r-16); background: var(--v8-panel); box-shadow: 0 12px 30px #1b2d5510; }.v8-trip-hero-head { display: flex; justify-content: space-between; gap: 20px; }.v8-status-pill { display: inline-flex; align-items: center; gap: 5px; padding: var(--cn-s-6) 9px; border-radius: var(--cn-r-pill); color: var(--cn-success-text); background: var(--cn-elev-1); font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }.v8-status-pill.violet { color: var(--v8-violet); background: #f3efff; }.v8-trip-hero h2 { margin: 18px 0 8px; font-size: 24px; letter-spacing: -.03em; }.v8-trip-hero p { display: flex; align-items: center; gap: 7px; margin: 0; color: #7b8798; font-size: 12px; }.v8-trip-
  ```
  改后：
  ```css
  .v8-hero-grid { display: grid; grid-template-columns: minmax(0, 1.14fr) minmax(340px, .86fr); gap: 18px; }.v8-trip-hero { padding: 28px 30px 24px; border: 1px solid #dfe4ed; border-radius: var(--cn-r-16); background: var(--v8-panel); box-shadow: 0 12px 30px #1b2d5510; }.v8-trip-hero-head { display: flex; justify-content: space-between; gap: 20px; }.v8-status-pill { display: inline-flex; align-items: center; gap: 5px; padding: var(--cn-s-6) 9px; border-radius: var(--cn-r-pill); color: var(--cn-success-text); background: var(--cn-elev-1); font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }.v8-status-pill.violet { color: var(--v8-violet); background: #f3efff; }.v8-trip-hero h2 { margin: 18px 0 8px; font-size: 24px; letter-spacing: -.03em; }.v8-trip-hero p { display: flex; align-items: center; gap: 7px; margin: 0; color: #7b8798; font-size: 12px; }.v8-trip-
  ```
  字节 1988 → 1525；删掉的子串：`.v8-trip-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12` / `.v8-trip-metrics span, .v8-trip-metrics small { display: block; color: #95a0af; ` / `.v8-trip-metrics strong { display: block; margin: var(--cn-s-6) 0 var(--cn-s-4);` / `.v8-trip-metrics strong.green { color: var(--v8-green); }` / `.v8-trip-metrics { gap: 8px; }` / `.v8-trip-metrics strong { font-size: 15px; }` / `.v8-trip-metrics small { line-height: 1.35; }`
  - 这一刀的回读：花括号 1063/1063 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

  孤立工单 `src/styles.css:185`：整组替换
  ```css
  @media (max-width: 680px) { .v8-product-shell { display: block; padding-bottom: var(--cn-nav-clearance); }.v8-sidebar { display: none; }.v8-topbar { min-height: 58px; padding: var(--cn-safe-top) 17px 0; }.v8-mobile-menu { display: block; width: auto; margin: 0; padding: 0; color: var(--v8-ink); font-size: 0; }.v8-mobile-menu:after { content: "≡"; font-size: 20px; }.v8-breadcrumb span, .v8-runtime, .v8-icon-button { display: none; }.v8-top-actions { gap: 8px; }.v8-content { padding: 27px 17px 34px; }.v8-message { margin: 13px 17px -5px; }.v8-page-intro { display: block; margin-bottom: 24px; }.v8-page-intro .v8-primary, .v8-page-intro .v8-outline-button { margin-top: 18px; }.v8-page h1 { font-size: 30px; }.v8-lede { font-size: 13px; }.v8-trip-hero { padding: 22px 19px; }.v8-trip-hero-head { display: block; }.v8-trip-hero-head .v8-quiet-button { margin-top: 15px; }.v8-trip-hero h2 { font-si
  ```
  改后：
  ```css
  @media (max-width: 680px) { .v8-product-shell { display: block; padding-bottom: var(--cn-nav-clearance); }.v8-sidebar { display: none; }.v8-topbar { min-height: 58px; padding: var(--cn-safe-top) 17px 0; }.v8-mobile-menu { display: block; width: auto; margin: 0; padding: 0; color: var(--v8-ink); font-size: 0; }.v8-mobile-menu:after { content: "≡"; font-size: 20px; }.v8-breadcrumb span, .v8-runtime, .v8-icon-button { display: none; }.v8-top-actions { gap: 8px; }.v8-content { padding: 27px 17px 34px; }.v8-message { margin: 13px 17px -5px; }.v8-page-intro { display: block; margin-bottom: 24px; }.v8-page-intro .v8-primary, .v8-page-intro .v8-outline-button { margin-top: 18px; }.v8-page h1 { font-size: 30px; }.v8-lede { font-size: 13px; }.v8-trip-hero { padding: 22px 19px; }.v8-trip-hero-head { display: block; }.v8-trip-hero-head .v8-quiet-button { margin-top: 15px; }.v8-trip-hero h2 { font-si
  ```
  字节 2696 → 2577；删掉的子串：`.v8-trip-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12` / `.v8-trip-metrics span, .v8-trip-metrics small { display: block; color: #95a0af; ` / `.v8-trip-metrics strong { display: block; margin: var(--cn-s-6) 0 var(--cn-s-4);` / `.v8-trip-metrics strong.green { color: var(--v8-green); }` / `.v8-trip-metrics { gap: 8px; }` / `.v8-trip-metrics strong { font-size: 15px; }` / `.v8-trip-metrics small { line-height: 1.35; }`
  - 这一刀的回读：花括号 1063/1063 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

### `v8-trip-hero-head` — ARM_C_NOT_RUN

- 甲：边界读者 0 处（分母 157 个 .tsx/.ts + index.html）；近似命中 0 处；`src` 外宽口径 427 个文件里 0 处。
- 乙：拼装现场 141 处里命中 0 处（能落到 class 的 31 处中 0 处）。也没有同形嫌疑。
- 丙：未跑（服务树不等于快照，见下节）。
- **本次新发现的现场（旧清单上没有）**：`src/styles.css:185`

  孤立工单 `src/styles.css:175`：整组替换
  ```css
  .v8-hero-grid { display: grid; grid-template-columns: minmax(0, 1.14fr) minmax(340px, .86fr); gap: 18px; }.v8-trip-hero { padding: 28px 30px 24px; border: 1px solid #dfe4ed; border-radius: var(--cn-r-16); background: var(--v8-panel); box-shadow: 0 12px 30px #1b2d5510; }.v8-trip-hero-head { display: flex; justify-content: space-between; gap: 20px; }.v8-status-pill { display: inline-flex; align-items: center; gap: 5px; padding: var(--cn-s-6) 9px; border-radius: var(--cn-r-pill); color: var(--cn-success-text); background: var(--cn-elev-1); font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }.v8-status-pill.violet { color: var(--v8-violet); background: #f3efff; }.v8-trip-hero h2 { margin: 18px 0 8px; font-size: 24px; letter-spacing: -.03em; }.v8-trip-hero p { display: flex; align-items: center; gap: 7px; margin: 0; color: #7b8798; font-size: 12px; }.v8-trip-
  ```
  改后：
  ```css
  .v8-hero-grid { display: grid; grid-template-columns: minmax(0, 1.14fr) minmax(340px, .86fr); gap: 18px; }.v8-trip-hero { padding: 28px 30px 24px; border: 1px solid #dfe4ed; border-radius: var(--cn-r-16); background: var(--v8-panel); box-shadow: 0 12px 30px #1b2d5510; }.v8-status-pill { display: inline-flex; align-items: center; gap: 5px; padding: var(--cn-s-6) 9px; border-radius: var(--cn-r-pill); color: var(--cn-success-text); background: var(--cn-elev-1); font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }.v8-status-pill.violet { color: var(--v8-violet); background: #f3efff; }.v8-trip-hero h2 { margin: 18px 0 8px; font-size: 24px; letter-spacing: -.03em; }.v8-trip-hero p { display: flex; align-items: center; gap: 7px; margin: 0; color: #7b8798; font-size: 12px; }.v8-trip-hero p svg { width: 14px; height: 14px; color: var(--v8-indigo); }.v8-trip-hero 
  ```
  字节 1988 → 1908；删掉的子串：`.v8-trip-hero-head { display: flex; justify-content: space-between; gap: 20px; }` / `.v8-trip-hero-head { display: block; }` / `.v8-trip-hero-head .v8-quiet-button { margin-top: 15px; }`
  - 这一刀的回读：花括号 1067/1067 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

  孤立工单 `src/styles.css:185`：整组替换
  ```css
  @media (max-width: 680px) { .v8-product-shell { display: block; padding-bottom: var(--cn-nav-clearance); }.v8-sidebar { display: none; }.v8-topbar { min-height: 58px; padding: var(--cn-safe-top) 17px 0; }.v8-mobile-menu { display: block; width: auto; margin: 0; padding: 0; color: var(--v8-ink); font-size: 0; }.v8-mobile-menu:after { content: "≡"; font-size: 20px; }.v8-breadcrumb span, .v8-runtime, .v8-icon-button { display: none; }.v8-top-actions { gap: 8px; }.v8-content { padding: 27px 17px 34px; }.v8-message { margin: 13px 17px -5px; }.v8-page-intro { display: block; margin-bottom: 24px; }.v8-page-intro .v8-primary, .v8-page-intro .v8-outline-button { margin-top: 18px; }.v8-page h1 { font-size: 30px; }.v8-lede { font-size: 13px; }.v8-trip-hero { padding: 22px 19px; }.v8-trip-hero-head { display: block; }.v8-trip-hero-head .v8-quiet-button { margin-top: 15px; }.v8-trip-hero h2 { font-si
  ```
  改后：
  ```css
  @media (max-width: 680px) { .v8-product-shell { display: block; padding-bottom: var(--cn-nav-clearance); }.v8-sidebar { display: none; }.v8-topbar { min-height: 58px; padding: var(--cn-safe-top) 17px 0; }.v8-mobile-menu { display: block; width: auto; margin: 0; padding: 0; color: var(--v8-ink); font-size: 0; }.v8-mobile-menu:after { content: "≡"; font-size: 20px; }.v8-breadcrumb span, .v8-runtime, .v8-icon-button { display: none; }.v8-top-actions { gap: 8px; }.v8-content { padding: 27px 17px 34px; }.v8-message { margin: 13px 17px -5px; }.v8-page-intro { display: block; margin-bottom: 24px; }.v8-page-intro .v8-primary, .v8-page-intro .v8-outline-button { margin-top: 18px; }.v8-page h1 { font-size: 30px; }.v8-lede { font-size: 13px; }.v8-trip-hero { padding: 22px 19px; }.v8-trip-hero h2 { font-size: 21px; }.v8-trip-metrics { gap: 8px; }.v8-trip-metrics strong { font-size: 15px; }.v8-trip-m
  ```
  字节 2696 → 2601；删掉的子串：`.v8-trip-hero-head { display: flex; justify-content: space-between; gap: 20px; }` / `.v8-trip-hero-head { display: block; }` / `.v8-trip-hero-head .v8-quiet-button { margin-top: 15px; }`
  - 这一刀的回读：花括号 1067/1067 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

### `anchor-line` — ARM_C_NOT_RUN

- 备注：只摘 175 末尾那条独立规则 `.anchor-line { flex:1; height:1px; background:#dfe3ea; }`。175 上另一处 anchor-line 出现在 `.v8-anchor-row div:not(.anchor-line)` 的 :not() 里 —— neg_guard 形状，本枚不许据它删规则（删了会把 min-width:0 扩大到所有 div）；那条规则只能作为 v8-anchor-row 的一部分被带走。
- 甲：边界读者 0 处（分母 157 个 .tsx/.ts + index.html）；近似命中 0 处；`src` 外宽口径 427 个文件里 0 处。
- 乙：拼装现场 141 处里命中 0 处（能落到 class 的 31 处中 0 处）。也没有同形嫌疑。
- 丙：未跑（服务树不等于快照，见下节）。
- **本次新发现的现场（旧清单上没有）**：`src/styles.css:175`
- neg_guard 不动的形状：`.v8-anchor-row div:not(.anchor-line)`（该 token 只在 :not() 里出现）

  孤立工单 `src/styles.css:175`：整组替换
  ```css
  .v8-hero-grid { display: grid; grid-template-columns: minmax(0, 1.14fr) minmax(340px, .86fr); gap: 18px; }.v8-trip-hero { padding: 28px 30px 24px; border: 1px solid #dfe4ed; border-radius: var(--cn-r-16); background: var(--v8-panel); box-shadow: 0 12px 30px #1b2d5510; }.v8-trip-hero-head { display: flex; justify-content: space-between; gap: 20px; }.v8-status-pill { display: inline-flex; align-items: center; gap: 5px; padding: var(--cn-s-6) 9px; border-radius: var(--cn-r-pill); color: var(--cn-success-text); background: var(--cn-elev-1); font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }.v8-status-pill.violet { color: var(--v8-violet); background: #f3efff; }.v8-trip-hero h2 { margin: 18px 0 8px; font-size: 24px; letter-spacing: -.03em; }.v8-trip-hero p { display: flex; align-items: center; gap: 7px; margin: 0; color: #7b8798; font-size: 12px; }.v8-trip-
  ```
  改后：
  ```css
  .v8-hero-grid { display: grid; grid-template-columns: minmax(0, 1.14fr) minmax(340px, .86fr); gap: 18px; }.v8-trip-hero { padding: 28px 30px 24px; border: 1px solid #dfe4ed; border-radius: var(--cn-r-16); background: var(--v8-panel); box-shadow: 0 12px 30px #1b2d5510; }.v8-trip-hero-head { display: flex; justify-content: space-between; gap: 20px; }.v8-status-pill { display: inline-flex; align-items: center; gap: 5px; padding: var(--cn-s-6) 9px; border-radius: var(--cn-r-pill); color: var(--cn-success-text); background: var(--cn-elev-1); font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }.v8-status-pill.violet { color: var(--v8-violet); background: #f3efff; }.v8-trip-hero h2 { margin: 18px 0 8px; font-size: 24px; letter-spacing: -.03em; }.v8-trip-hero p { display: flex; align-items: center; gap: 7px; margin: 0; color: #7b8798; font-size: 12px; }.v8-trip-
  ```
  字节 1988 → 1929；删掉的子串：`.anchor-line { flex: 1; height: 1px; background: #dfe3ea; }`
  - 这一刀的回读：花括号 1069/1069 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

### `v8-live-grid` — ARM_C_NOT_RUN

- 备注：styles.css:184(@media 960) 里它是 5 支选择器表中的一支，只摘这一支，其余 4 支（.v8-hero-grid/.v8-studio-layout/.v8-stay-layout/.v8-intelligence-grid）字节不动。
- 甲：边界读者 0 处（分母 157 个 .tsx/.ts + index.html）；近似命中 0 处；`src` 外宽口径 427 个文件里 0 处。
- 乙：拼装现场 141 处里命中 0 处（能落到 class 的 31 处中 0 处）。也没有同形嫌疑。
- 丙：未跑（服务树不等于快照，见下节）。
- **本次新发现的现场（旧清单上没有）**：`src/styles.css:184`

  孤立工单 `src/styles.css:180`：整组替换
  ```css
  .v8-evidence-label { align-self: center; padding: 8px var(--cn-s-10); border: 1px solid var(--cn-rule); border-radius: var(--cn-r-8); color: var(--cn-success-text); background: var(--cn-elev-1); font-size: 10px; font-weight: 800; letter-spacing: .08em; }.v8-stay-layout { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(330px, .95fr); gap: 18px; }.v8-stay-list { display: grid; gap: 12px; }.v8-stay-card { display: flex; gap: 16px; padding: 13px; border: 1px solid var(--v8-line); border-radius: var(--cn-r-12); background: var(--cn-elev-1); cursor: pointer; }.v8-stay-card.selected { border-color: #8490e9; box-shadow: 0 0 0 2px #e8eaff; }.v8-stay-card-body { min-width: 0; flex: 1; padding: 5px 5px 3px 0; }.v8-stay-card-title { display: flex; align-items: start; justify-content: space-between; gap: var(--cn-s-10); }.v8-stay-card-title > div { display: flex; align-items: center; g
  ```
  改后：
  ```css
  .v8-evidence-label { align-self: center; padding: 8px var(--cn-s-10); border: 1px solid var(--cn-rule); border-radius: var(--cn-r-8); color: var(--cn-success-text); background: var(--cn-elev-1); font-size: 10px; font-weight: 800; letter-spacing: .08em; }.v8-stay-layout { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(330px, .95fr); gap: 18px; }.v8-stay-list { display: grid; gap: 12px; }.v8-stay-card { display: flex; gap: 16px; padding: 13px; border: 1px solid var(--v8-line); border-radius: var(--cn-r-12); background: var(--cn-elev-1); cursor: pointer; }.v8-stay-card.selected { border-color: #8490e9; box-shadow: 0 0 0 2px #e8eaff; }.v8-stay-card-body { min-width: 0; flex: 1; padding: 5px 5px 3px 0; }.v8-stay-card-title { display: flex; align-items: start; justify-content: space-between; gap: var(--cn-s-10); }.v8-stay-card-title > div { display: flex; align-items: center; g
  ```
  字节 5035 → 4930；删掉的子串：`\n.v8-live-grid { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(` / `.v8-live-grid, `
  - 这一刀的回读：花括号 1069/1069 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

  孤立工单 `src/styles.css:184`：整组替换
  ```css
  @media (max-width: 960px) { .v8-sidebar { --sb-width: 205px; }.v8-content { padding: 32px 26px 70px; }.v8-topbar { padding: 0 26px; }.v8-message { margin-left: 26px; margin-right: 26px; }.v8-hero-grid, .v8-studio-layout, .v8-stay-layout, .v8-live-grid, .v8-intelligence-grid { grid-template-columns: 1fr; }.v8-map-panel { min-height: 260px; }.v8-stay-detail { grid-row: 1; }.v8-stay-list { grid-row: 2; }.v8-intel-facts { grid-template-columns: repeat(3, 1fr); }.v8-twin-grid { grid-template-columns: repeat(2, 1fr); }.v8-boundary-card { grid-column: 1 / -1; } }
  ```
  改后：
  ```css
  @media (max-width: 960px) { .v8-sidebar { --sb-width: 205px; }.v8-content { padding: 32px 26px 70px; }.v8-topbar { padding: 0 26px; }.v8-message { margin-left: 26px; margin-right: 26px; }.v8-hero-grid, .v8-studio-layout, .v8-stay-layout, .v8-intelligence-grid { grid-template-columns: 1fr; }.v8-map-panel { min-height: 260px; }.v8-stay-detail { grid-row: 1; }.v8-stay-list { grid-row: 2; }.v8-intel-facts { grid-template-columns: repeat(3, 1fr); }.v8-twin-grid { grid-template-columns: repeat(2, 1fr); }.v8-boundary-card { grid-column: 1 / -1; } }
  ```
  字节 562 → 547；删掉的子串：`\n.v8-live-grid { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(` / `.v8-live-grid, `
  - 这一刀的回读：花括号 1069/1069 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

### `v8-strength` — ARM_C_NOT_RUN

- 甲：边界读者 0 处（分母 157 个 .tsx/.ts + index.html）；近似命中 0 处；`src` 外宽口径 427 个文件里 0 处。
- 乙：拼装现场 141 处里命中 0 处（能落到 class 的 31 处中 0 处）。也没有同形嫌疑。
- 丙：未跑（服务树不等于快照，见下节）。

  孤立工单 `src/styles.css:181`：整组替换
  ```css
  .v8-intelligence-grid { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(280px, .7fr); gap: 18px; }.v8-intel-hero { min-height: 280px; padding: 28px; border-radius: var(--cn-r-12); color: #fff; background: #172945; }.v8-intel-hero h2 { max-width: 550px; margin: 25px 0 12px; font-size: 28px; letter-spacing: -.04em; line-height: 1.1; }.v8-intel-hero p { max-width: 600px; color: #b9c7dc; font-size: 13px; line-height: 1.65; }.v8-chain { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 28px; color: #e3ebf8; font-size: 11px; font-weight: 700; }.v8-chain span { padding: 7px 9px; border: 1px solid #526b94; border-radius: var(--cn-r-4); background: #233b60; }.v8-chain b { color: #8fa7d3; }.v8-intel-facts { display: grid; gap: 12px; }.v8-intel-facts > div { padding: 19px; border: 1px solid var(--v8-line); border-radius: var(--cn-r-12); background: var(--cn-el
  ```
  改后：
  ```css
  .v8-intelligence-grid { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(280px, .7fr); gap: 18px; }.v8-intel-hero { min-height: 280px; padding: 28px; border-radius: var(--cn-r-12); color: #fff; background: #172945; }.v8-intel-hero h2 { max-width: 550px; margin: 25px 0 12px; font-size: 28px; letter-spacing: -.04em; line-height: 1.1; }.v8-intel-hero p { max-width: 600px; color: #b9c7dc; font-size: 13px; line-height: 1.65; }.v8-chain { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 28px; color: #e3ebf8; font-size: 11px; font-weight: 700; }.v8-chain span { padding: 7px 9px; border: 1px solid #526b94; border-radius: var(--cn-r-4); background: #233b60; }.v8-chain b { color: #8fa7d3; }.v8-intel-facts { display: grid; gap: 12px; }.v8-intel-facts > div { padding: 19px; border: 1px solid var(--v8-line); border-radius: var(--cn-r-12); background: var(--cn-el
  ```
  字节 2598 → 2206；删掉的子串：`.v8-strength { display: flex; align-items: center; gap: 8px; height: 6px; margin` / `.v8-strength span { display: block; height: 6px; border-radius: var(--cn-r-pill)` / `.v8-strength.learned span { background: var(--v8-violet); }` / `.v8-strength b { margin-left: auto; color: #68758a; font-size: 10px; }`
  - 这一刀的回读：花括号 1066/1066 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

### `v9-live-actions` — ARM_C_NOT_RUN

- 备注：278 那行 @media 里两条规则都只服务它（.v9-live-actions 与 .v9-live-actions button）；摘完该 @media 仍剩 .v9-wallet-layout 与 .v9-offline，不能连 @media 一起删。
- 甲：边界读者 0 处（分母 157 个 .tsx/.ts + index.html）；近似命中 0 处；`src` 外宽口径 427 个文件里 0 处。
- 乙：拼装现场 141 处里命中 0 处（能落到 class 的 31 处中 0 处）。也没有同形嫌疑。
- 丙：未跑（服务树不等于快照，见下节）。

  孤立工单 `src/styles.css:278`：整组替换
  ```css
  @media (max-width: 680px) { .v9-live-actions { align-items: stretch; flex-direction: column; }.v9-live-actions button { margin-top: 8px !important; }.v9-wallet-layout { grid-template-columns: 1fr; }.v9-offline { margin-top: 20px; padding: 22px; } }
  ```
  改后：
  ```css
  @media (max-width: 680px) {.v9-wallet-layout { grid-template-columns: 1fr; }.v9-offline { margin-top: 20px; padding: 22px; } }
  ```
  字节 248 → 126；删掉的子串：` .v9-live-actions { align-items: stretch; flex-direction: column; }` / `.v9-live-actions button { margin-top: 8px !important; }`
  - 这一刀的回读：花括号 1068/1068 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

### `v8-cta` — ARM_C_NOT_RUN

- 备注：旧清单只点了 :514 一处，本次重读发现 :440 还有一处（同一族 hover/press 过渡的多行选择器表）。只摘 514 的话，440 那条声明还在，token 归不了零。
- 甲：边界读者 0 处（分母 157 个 .tsx/.ts + index.html）；近似命中 0 处；`src` 外宽口径 427 个文件里 0 处。
- 乙：拼装现场 141 处里命中 0 处（能落到 class 的 31 处中 0 处）。也没有同形嫌疑。
- 丙：未跑（服务树不等于快照，见下节）。
- **本次新发现的现场（旧清单上没有）**：`src/design-tokens.css:440`

  孤立工单 `src/design-tokens.css:440`：整组删掉
  ```css
  .v8-page a.v8-cta,
  ```
  字节 18 → 0；删掉的子串：`.v8-page a.v8-cta,\n` / `.v8-page a.v8-cta, `
  - 这一刀的回读：花括号 217/217 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

  孤立工单 `src/design-tokens.css:514`：整组替换
  ```css
    .v8-page button, .v8-page a.v8-cta, .v8-page .v8-card {
  ```
  改后：
  ```css
    .v8-page button, .v8-page .v8-card {
  ```
  字节 57 → 38；删掉的子串：`.v8-page a.v8-cta,\n` / `.v8-page a.v8-cta, `
  - 这一刀的回读：花括号 217/217 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

### `v8-home-language` — ARM_C_NOT_RUN

- 备注：旧清单的 982 行现在在 991（同文件前面多出 9 行注释/规则）。v10.css:49 的那句提及在 /* */ 注释里（记录的是 05:2x 那手死码清理），不是声明，不动。
- 甲：边界读者 0 处（分母 157 个 .tsx/.ts + index.html）；近似命中 0 处；`src` 外宽口径 427 个文件里 0 处。
- 乙：拼装现场 141 处里命中 0 处（能落到 class 的 31 处中 0 处）。也没有同形嫌疑。
- 丙：未跑（服务树不等于快照，见下节）。
- 只读不动的提及：`src/v10.css:49`
- **本次新发现的现场（旧清单上没有）**：`src/design-tokens.css:991`

  孤立工单 `src/design-tokens.css:991`：整组替换
  ```css
  .v9-language,
  .v8-home-language {
  ```
  改后：
  ```css
  .v9-language {
  ```
  字节 33 → 14；删掉的子串：`,\n.v8-home-language `
  - 悬空补修（已并入工单）：L990 表尾支 '.v8-home-language' 摘掉后 ',' 会悬在 { 前：删逗号、把 { 提到 '.v9-language' 的行尾
  - 这一刀的回读：花括号 217/217 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

### `collections-panel` — ARM_C_NOT_RUN

- 甲：边界读者 0 处（分母 157 个 .tsx/.ts + index.html）；近似命中 0 处；`src` 外宽口径 427 个文件里 0 处。
- 乙：拼装现场 141 处里命中 0 处（能落到 class 的 31 处中 0 处）。同形但喂给 id / aria-controls / data-testid 的 3 处不算读者：`src/components/CnxSelect.tsx:262`(free-string(不进类名))、`src/components/CnxSelect.tsx:275`(non-class-attr:id)、`src/components/CnxSelect.tsx:276`(free-string(不进类名))
- 丙：未跑（服务树不等于快照，见下节）。

  孤立工单 `src/cn-pulse.css:396`：整组删掉
  ```css
  .collections-panel,
  ```
  字节 19 → 0；删掉的子串：`.collections-panel,\n`
  - 这一刀的回读：花括号 72/72 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

### `poi-import-panel` — ARM_C_NOT_RUN

- 备注：它是 .plan-ranking/.collections-panel/.poi-import-panel 这张表的表尾支（带着 {）：摘它必须把 { 提到上一支行尾，否则 `.plan-ranking,\n{` 是非法选择器表。与 collections-panel 同批做时，最终这一张表只剩 `.plan-ranking {`。
- 甲：边界读者 0 处（分母 157 个 .tsx/.ts + index.html）；近似命中 0 处；`src` 外宽口径 427 个文件里 0 处。
- 乙：拼装现场 141 处里命中 0 处（能落到 class 的 31 处中 0 处）。同形但喂给 id / aria-controls / data-testid 的 3 处不算读者：`src/components/CnxSelect.tsx:262`(free-string(不进类名))、`src/components/CnxSelect.tsx:275`(non-class-attr:id)、`src/components/CnxSelect.tsx:276`(free-string(不进类名))
- 丙：未跑（服务树不等于快照，见下节）。

  孤立工单 `src/cn-pulse.css:397`：整组替换
  ```css
  .collections-panel,
  .poi-import-panel {
  ```
  改后：
  ```css
  .collections-panel {
  ```
  字节 39 → 20；删掉的子串：`,\n.poi-import-panel `
  - 悬空补修（已并入工单）：L396 表尾支 '.poi-import-panel' 摘掉后 ',' 会悬在 { 前：删逗号、把 { 提到 '.collections-panel' 的行尾
  - 这一刀的回读：花括号 72/72 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

### `v8-user-meta` — ARM_C_NOT_RUN

- 甲：边界读者 0 处（分母 157 个 .tsx/.ts + index.html）；近似命中 0 处；`src` 外宽口径 427 个文件里 0 处。
- 乙：拼装现场 141 处里命中 0 处（能落到 class 的 31 处中 0 处）。也没有同形嫌疑。
- 丙：未跑（服务树不等于快照，见下节）。

  孤立工单 `src/cn-pulse.css:510`：整组删掉
  ```css
  .v8-user-meta,
  ```
  字节 14 → 0；删掉的子串：`.v8-user-meta,\n`
  - 这一刀的回读：花括号 72/72 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

### `v8-empty-hint` — ARM_C_NOT_RUN

- 备注：同样是表尾支（带 {），最小修法是把 { 提到 .cn-pending-empty-next 行尾。注意这张表从 509 一直排到 514，中间夹着一行空行和一段中文注释 —— 只按"倒吃逗号"往前收会漏掉 513/514，判成"整块只剩死类"从而多删。
- 甲：边界读者 0 处（分母 157 个 .tsx/.ts + index.html）；近似命中 0 处；`src` 外宽口径 427 个文件里 0 处。
- 乙：拼装现场 141 处里命中 0 处（能落到 class 的 31 处中 0 处）。也没有同形嫌疑。
- 丙：未跑（服务树不等于快照，见下节）。

  孤立工单 `src/cn-pulse.css:514`：整组替换
  ```css
  .cn-pending-empty-next,
  .v8-empty-hint {
  ```
  改后：
  ```css
  .cn-pending-empty-next {
  ```
  字节 40 → 24；删掉的子串：`,\n.v8-empty-hint `
  - 悬空补修（已并入工单）：L513 表尾支 '.v8-empty-hint' 摘掉后 ',' 会悬在 { 前：删逗号、把 { 提到 '.cn-pending-empty-next' 的行尾
  - 这一刀的回读：花括号 72/72 OK；字节对账 OK；活 token 账 无违例；区间重叠 0 处。

## 合并一趟落地（同一物理行/同一张表只改一次；`compound_single_pass`）

### `src/cn-pulse.css`（这一趟管：`collections-panel`、`poi-import-panel`、`v8-user-meta`、`v8-empty-hint`）— 门禁 **PASS**

- 行数 655 → 651；字节 28248 → 28178；删掉 72 字节、补写回 2 字节；花括号 72/72；活 token 账 无违例；区间重叠 0 处；新文本 X,, 无。

| 老行号 | 新行号 | 动作 | 前→后字节 |
|---|---|---|---|
| [395, 397] | [395, 395] | replace | 54→15 |
| [510, 510] | [508, 507] | delete | 14→0 |
| [513, 514] | [510, 510] | replace | 40→24 |

```css
.plan-ranking,
.collections-panel,
.poi-import-panel {
```
改成：
```css
.plan-ranking {
```

```css
.v8-user-meta,
```

```css
.cn-pending-empty-next,
.v8-empty-hint {
```
改成：
```css
.cn-pending-empty-next {
```

### `src/design-tokens.css`（这一趟管：`v8-cta`、`v8-home-language`）— 门禁 **PASS**

- 行数 1618 → 1616；字节 72209 → 72152；删掉 58 字节、补写回 1 字节；花括号 217/217；活 token 账 无违例；区间重叠 0 处；新文本 X,, 无。

| 老行号 | 新行号 | 动作 | 前→后字节 |
|---|---|---|---|
| [440, 440] | [440, 439] | delete | 18→0 |
| [514, 514] | [513, 513] | replace | 57→38 |
| [990, 991] | [989, 989] | replace | 33→14 |

```css
.v8-page a.v8-cta,
```

```css
  .v8-page button, .v8-page a.v8-cta, .v8-page .v8-card {
```
改成：
```css
  .v8-page button, .v8-page .v8-card {
```

```css
.v9-language,
.v8-home-language {
```
改成：
```css
.v9-language {
```

### `src/styles.css`（这一趟管：`v8-anchor-row`、`v8-trip-metrics`、`v8-trip-hero-head`、`anchor-line`、`v8-live-grid`、`v8-strength`、`v9-live-actions`）— 门禁 **PASS**

- 行数 1929 → 1928；字节 122839 → 120859；删掉 1980 字节、补写回 0 字节；花括号 1045/1045；活 token 账 无违例；区间重叠 0 处；新文本 X,, 无。

| 老行号 | 新行号 | 动作 | 前→后字节 |
|---|---|---|---|
| [175, 175] | [175, 175] | replace | 1988→926 |
| [179, 181] | [179, 180] | replace | 7634→7137 |
| [184, 185] | [183, 184] | replace | 3259→2960 |
| [278, 278] | [277, 277] | replace | 248→126 |

```css
.v8-hero-grid { display: grid; grid-template-columns: minmax(0, 1.14fr) minmax(340px, .86fr); gap: 18px; }.v8-trip-hero { padding: 28px 30px 24px; border: 1px solid #dfe4ed; border-radius: var(--cn-r-16); background: var(--v8-panel); box-shadow: 0 12px 30px #1b2d5510; }.v8-trip-hero-head { display: flex; justify-content: space-between; gap: 20px; }.v8-status-pill { display: inline-flex; align-items: center; gap: 5px; padding: var(--cn-s-6) 9px; border-radius: var(--cn-r-pill); color: var(--cn-success-text); background: var(--cn-elev-1); font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }.v8-status-pill.violet { color: var(--v8-violet); background: #f3efff; }.v8-trip-hero h2 { margin: 18px 0 8px; font-size: 24px; letter-spacing: -.03em; }.v8-trip-hero p { display: flex; align-items: center; gap: 7px; margin: 0; color: #7b8798; font-size: 12px; }.v8-trip-hero p svg { width: 14px; height: 14px; color: var(--v8-indigo); }.v8-trip-hero p span { color: #c0c7d1; }.v8-trip-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 28px; padding: 16px 0; border-top: 1px solid #edf0f4; border-bottom: 1px solid #edf0f4; }.v8-trip-
```
改成：
```css
.v8-hero-grid { display: grid; grid-template-columns: minmax(0, 1.14fr) minmax(340px, .86fr); gap: 18px; }.v8-trip-hero { padding: 28px 30px 24px; border: 1px solid #dfe4ed; border-radius: var(--cn-r-16); background: var(--v8-panel); box-shadow: 0 12px 30px #1b2d5510; }.v8-status-pill { display: inline-flex; align-items: center; gap: 5px; padding: var(--cn-s-6) 9px; border-radius: var(--cn-r-pill); color: var(--cn-success-text); background: var(--cn-elev-1); font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }.v8-status-pill.violet { color: var(--v8-violet); background: #f3efff; }.v8-trip-hero h2 { margin: 18px 0 8px; font-size: 24px; letter-spacing: -.03em; }.v8-trip-hero p { display: flex; align-items: center; gap: 7px; margin: 0; color: #7b8798; font-size: 12px; }.v8-trip-hero p svg { width: 14px; height: 14px; color: var(--v8-indigo); }.v8-trip-hero p span { color: #c0c7d1; }
```

```css
.v8-evidence-label { align-self: center; padding: 8px var(--cn-s-10); border: 1px solid var(--cn-rule); border-radius: var(--cn-r-8); color: var(--cn-success-text); background: var(--cn-elev-1); font-size: 10px; font-weight: 800; letter-spacing: .08em; }.v8-stay-layout { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(330px, .95fr); gap: 18px; }.v8-stay-list { display: grid; gap: 12px; }.v8-stay-card { display: flex; gap: 16px; padding: 13px; border: 1px solid var(--v8-line); border-radius: var(--cn-r-12); background: var(--cn-elev-1); cursor: pointer; }.v8-stay-card.selected { border-color: #8490e9; box-shadow: 0 0 0 2px #e8eaff; }.v8-stay-card-body { min-width: 0; flex: 1; padding: 5px 5px 3px 0; }.v8-stay-card-title { display: flex; align-items: start; justify-content: space-between; gap: var(--cn-s-10); }.v8-stay-card-title > div { display: flex; align-items: center; gap: 8px; }.v8-rank { color: #a0a9b6; font-size: 10px; font-weight: 800; }.v8-stay-card h3 { margin: 0; font-size: 15px; letter-spacing: -.02em; }.v8-stay-card p { margin: 8px 0 15px; color: #818c9d; font-size: 11px; }.v8-selected-label { padding: var(--cn-s-4) 7px; border-radius: var(--cn-r-4); colo
```
改成：
```css
.v8-evidence-label { align-self: center; padding: 8px var(--cn-s-10); border: 1px solid var(--cn-rule); border-radius: var(--cn-r-8); color: var(--cn-success-text); background: var(--cn-elev-1); font-size: 10px; font-weight: 800; letter-spacing: .08em; }.v8-stay-layout { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(330px, .95fr); gap: 18px; }.v8-stay-list { display: grid; gap: 12px; }.v8-stay-card { display: flex; gap: 16px; padding: 13px; border: 1px solid var(--v8-line); border-radius: var(--cn-r-12); background: var(--cn-elev-1); cursor: pointer; }.v8-stay-card.selected { border-color: #8490e9; box-shadow: 0 0 0 2px #e8eaff; }.v8-stay-card-body { min-width: 0; flex: 1; padding: 5px 5px 3px 0; }.v8-stay-card-title { display: flex; align-items: start; justify-content: space-between; gap: var(--cn-s-10); }.v8-stay-card-title > div { display: flex; align-items: center; gap: 8px; }.v8-rank { color: #a0a9b6; font-size: 10px; font-weight: 800; }.v8-stay-card h3 { margin: 0; font-size: 15px; letter-spacing: -.02em; }.v8-stay-card p { margin: 8px 0 15px; color: #818c9d; font-size: 11px; }.v8-selected-label { padding: var(--cn-s-4) 7px; border-radius: var(--cn-r-4); colo
```

```css
@media (max-width: 960px) { .v8-sidebar { --sb-width: 205px; }.v8-content { padding: 32px 26px 70px; }.v8-topbar { padding: 0 26px; }.v8-message { margin-left: 26px; margin-right: 26px; }.v8-hero-grid, .v8-studio-layout, .v8-stay-layout, .v8-live-grid, .v8-intelligence-grid { grid-template-columns: 1fr; }.v8-map-panel { min-height: 260px; }.v8-stay-detail { grid-row: 1; }.v8-stay-list { grid-row: 2; }.v8-intel-facts { grid-template-columns: repeat(3, 1fr); }.v8-twin-grid { grid-template-columns: repeat(2, 1fr); }.v8-boundary-card { grid-column: 1 / -1; } }
@media (max-width: 680px) { .v8-product-shell { display: block; padding-bottom: var(--cn-nav-clearance); }.v8-sidebar { display: none; }.v8-topbar { min-height: 58px; padding: var(--cn-safe-top) 17px 0; }.v8-mobile-menu { display: block; width: auto; margin: 0; padding: 0; color: var(--v8-ink); font-size: 0; }.v8-mobile-menu:after { content: "≡"; font-size: 20px; }.v8-breadcrumb span, .v8-runtime, .v8-icon-button { display: none; }.v8-top-actions { gap: 8px; }.v8-content { padding: 27px 17px 34px; }.v8-message { margin: 13px 17px -5px; }.v8-page-intro { display: block; margin-bottom: 24px; }.v8-page-intro .v8-primary, .v8-page-in
```
改成：
```css
@media (max-width: 960px) { .v8-sidebar { --sb-width: 205px; }.v8-content { padding: 32px 26px 70px; }.v8-topbar { padding: 0 26px; }.v8-message { margin-left: 26px; margin-right: 26px; }.v8-hero-grid, .v8-studio-layout, .v8-stay-layout, .v8-intelligence-grid { grid-template-columns: 1fr; }.v8-map-panel { min-height: 260px; }.v8-stay-detail { grid-row: 1; }.v8-stay-list { grid-row: 2; }.v8-intel-facts { grid-template-columns: repeat(3, 1fr); }.v8-twin-grid { grid-template-columns: repeat(2, 1fr); }.v8-boundary-card { grid-column: 1 / -1; } }
@media (max-width: 680px) { .v8-product-shell { display: block; padding-bottom: var(--cn-nav-clearance); }.v8-sidebar { display: none; }.v8-topbar { min-height: 58px; padding: var(--cn-safe-top) 17px 0; }.v8-mobile-menu { display: block; width: auto; margin: 0; padding: 0; color: var(--v8-ink); font-size: 0; }.v8-mobile-menu:after { content: "≡"; font-size: 20px; }.v8-breadcrumb span, .v8-runtime, .v8-icon-button { display: none; }.v8-top-actions { gap: 8px; }.v8-content { padding: 27px 17px 34px; }.v8-message { margin: 13px 17px -5px; }.v8-page-intro { display: block; margin-bottom: 24px; }.v8-page-intro .v8-primary, .v8-page-intro .v8-outline
```

```css
@media (max-width: 680px) { .v9-live-actions { align-items: stretch; flex-direction: column; }.v9-live-actions button { margin-top: 8px !important; }.v9-wallet-layout { grid-template-columns: 1fr; }.v9-offline { margin-top: 20px; padding: 22px; } }
```
改成：
```css
@media (max-width: 680px) {.v9-wallet-layout { grid-template-columns: 1fr; }.v9-offline { margin-top: 20px; padding: 22px; } }
```

## 够不着 / 没能核的地方

1. **丙臂（真屏命中）没有跑，也不能拿来当证据。** 已读 `_cmdr_deadcss_dom_probe_r1.cjs`，它需要：跑着的应用、Playwright（`D:/moodle/CityNexus/frontend/node_modules/playwright`）+ channel chrome、以及一枚写死的 DEAD 清单（现写的是 `v8-rain-button`/`cn-copilot-runtime`/`cn-native-status`，与本题无关）。8121 上确实是 Vite dev server（pid 52108），但逐字节比了 187 个文件后：184 相等，`src/design-tokens.css` **不等** —— 服务版 1644 行、快照 1618 行，多出 08:31 那手 `.trip-stop.disrupted` 暗档配对（diff 已存 `_agent_dead_served_design_tokens.css`）。差的这枚正是本工单要改的三个文件之一，所以按规矩不用丙臂；也没重启/停止/改配任何进程。
2. 那次树比对里另有两处**不是树不同**的对不上，已查明是取数方式而非内容：`src/components/ProductErrorBoundary.tsx` 要 `?raw` 时 Vite 回了转译后的模块（没拿到原文，故该文件未核，且它不在本题现场）；`index.html` 差的是 Vite 注入的 `/@vite/client` 与 react-refresh 两段 script 以及 `main.tsx?t=…` 的时间戳，正文一致。
3. **行号会漂**：`_agent_dead_plan.json` 里每一处 `line` 都是本次在快照上重读的当前行号；逐枚孤立工单只保证“在这一枚还没被改过的文件上”成立。真要落地请一次改完一整个文件（用 `compound_single_pass`），或者每改一枚就重读一次行号。旧 DRY run 报的 982/514 那批号，本快照上已经分别是 991/440+514。
4. **`:not()` 那一处不在本工单的删除许可里**：`styles.css:175` 的 `.v8-anchor-row div:not(.anchor-line){min-width:0}` —— `anchor-line` 只出现在 :not() 内，按 `neg_guard()` 本枚不许据它删；它是作为 `v8-anchor-row` 的一部分被带走的。如果有人只把 :not() 里的类名摘掉，那条 `min-width:0` 会扩大到 `.v8-anchor-row` 里的所有 div —— 那是改行为，不是清死码。
5. **注释里的提及不算声明，也没动**：`src/v10.css:49` 提到 `.v8-home-language`，它在 `/* */` 里（那段是 05:2x 死码清理的记录）。整棵快照这 13 枚 token 的边界命中只有 CSS 侧这些处：产品码 `.tsx/.ts` + `index.html` 里 0 处，`src` 之外的 427 个 `.ts/.tsx`（e2e、.storybook、docs 脚本）里也 0 处 —— 全量点名见 `_agent_dead_census.json`（文本文件 770 个，另有 176 个非文本/坏码跳过）。
6. 顺带发现（不属于本题，没动）：`src/styles.css:1648` 有一处**本来就空的** `@media (max-width: 480px) { …注释… }`，声明体里只剩注释。那是另一族死码，本工单的"形状检查"对它作了基线豁免（`_agent_dead_check_edits_r1.py` 只对"这一刀新造的毛病"报警）。
7. 排除项按交办原样保留，未复测：
   - cn-no-motion / :not(.cn-no-motion) 全族 —— 等价改法是去掉 :not()，动的是所有按钮，要产品裁语
   - cn-badge--* —— Badge.tsx:95 `cn-badge--${tone}` 运行时拼装（本次乙臂正对照当场咬住）
   - cn-access-picker —— 甲臂边界 0 读者、6 处近似都是 -label/-hint（勘误已定为禁删）

## 三臂过关统计

- 本次处理的 token：13 枚（`cn-no-motion` 族与 `cn-badge--*`、`cn-access-picker` 按交办排除，不在其中）。
- 甲乙两臂全过：**13 枚**；甲臂不过（其实还活着）：0 枚；乙臂不过（可被拼出来）：0 枚。
- 三臂全过：**0 枚** —— 因为丙臂没法跑，所有判语都是 `ARM_C_NOT_RUN`，不是 `DEAD_PROVEN`。
- 悬空风险为 true 的：`v8-home-language`、`poi-import-panel`、`v8-empty-hint`（都是“表尾支带着 `{`”那三类，最小修法已写进工单，未落笔）。
