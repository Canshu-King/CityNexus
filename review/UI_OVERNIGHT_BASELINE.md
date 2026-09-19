# UI_OVERNIGHT_BASELINE — 移动验收网在 `00dfd62` 上的红/绿名单（修订版 v2）

ORD-0009 限制 (3) 的交付物：先把回归网立起来，再动生产代码。

> **v2 修订说明**：v1 曾报"Wallet 主 CTA 在 412×915 被底部导航遮住 44px"。**该条撤回** —— 它是
> 我探针自身的缺陷造成的假阳性（见下文"量具的三次自错"）。v2 的数字来自修好探针后的运行。

- 树：`D:\moodle\_qoder_ui_overnight_20260920` @ `agent/ui-overnight-20260920`，基线 commit `00dfd62`
- 量具：`frontend/e2e/_qoderMobileScan.ts` + `frontend/e2e/qoder-mobile-ui-overnight.spec.ts`
- **现有门未被改动**：`e2e/qoder-mobile-overflow.spec.ts` 一个字节没动（仲裁已签的门，重构它是风险不是收益）
- 证据全在 `review/`，不进生产目录；原始数据 `review/evidence/ui-overnight/geometry-{seeded,setup}.json`

## 运行方式与出处

authoritative 模式，本 run 自己起两个进程，不复用邻居的 `:8000`：

```
suite=current-product authoritative=true
python=D:/moodle/CityNexus/.venv/Scripts/python.exe
frontend=:4240 backend=:8140
db=sqlite:///D:/moodle/_qoder_ui_overnight_20260920/review/evidence/_uibase06.db
ai=disabled reuseExistingServer=false workers=1 retries=0
```

| 命令 | collected | 结果 |
|---|---|---|
| `qoder-mobile-overflow.spec.ts`（现有门，冒烟验证 harness） | 1 test + 1 seed project | **2 passed** (21.1s) |
| `qoder-mobile-ui-overnight.spec.ts`（新门，最终基线） | 2 tests + 1 seed project | **2 failed / 1 passed(seed)**，`PW_EXIT=1` (29.7s) |

新门覆盖 **12 个测量点 = 3 视口（360×800 / 390×844 / 412×915）× 4 界面（Today / Live / Wallet / Journey 创建）**。

## 红/绿名单（v2，可信）

| 检查项 | 红 | 绿 | 备注 |
|---|---|---|---|
| 横向溢出（右边界 + 左边界，`+1px` 容差同现有门） | **0** | 12/12 | 三档口径均无溢出。我原本担心的"390/412 无针对性处理"没有以溢出形式出现 |
| fixed/sticky chrome 互相重叠 | **0** | 12/12 | — |
| 主控件触控 <44px | **9 例** | 3/12 点干净 | 全部在 Today，三档视口数字完全相同 → 常量问题不是视口问题 |
| 文案截断 | **4 例** | 8/12 点干净 | 全部在 Journey 创建的步骤指示器 |
| 主 CTA 被 chrome 遮住 | **0** | 12/12 | v1 的 1 例已撤回 |
| 找不到可见主 CTA | 0 | 12/12 | 修选择器后 |

### 红项 (a)：Today 三个次级操作只有 30px 高（×3 视口 = 9 例）

```
[data-testid="hub-plan-with-ai"]  "Plan my trip with AI"   117 x 30
button.v8-quiet-button            "Try another city"       119 x 30
button.v8-quiet-button            "Open Trip Studio"       127 x 30
```
根因：`.v8-quiet-button` 只有 `padding: 5px 0`，无 `min-height`（`styles.css:162`）；
`styles.css:260` 在 680px 下的 44px 抬升清单只列了 nav / mode-chips / compare / page-intro，**漏了它**。

### 红项 (b)：Journey 创建步骤标签被 ellipsis 截断

```
setup@360x800  "Destination & dates"         96 > 88
setup@360x800  "Travellers & preferences"   116 > 88
setup@390x844  "Travellers & preferences"   116 > 98
setup@412x915  "Travellers & preferences"   116 > 105
```
根因：`.trial-steps li { flex: 1 }` + `.trial-steps li span:last-child { white-space: nowrap; text-overflow: ellipsis }`
（`styles.css:447-460`）。三个标签挤在一行，**"Travellers & preferences" 在三档口径下全部被截** —— 必然发生，不是边缘情况。

## 量具的三次自错（记录以免有人重走，也因为我差点把"没测"报成"测过"）

1. **Live 找不到 CTA**：最初写 `.v8-live-main .v8-compare-button`。Pass-8 裁决 #3 刻意把 Live 的两个全宽按钮降级成
   `.cn-live-toolbar` 里的文字按钮，`.v8-compare-button` 实际住在 `.cn-live-secondary > .v8-mode-chooser`。
   选择器按真实结构改好后 Live 解析到 `.v8-compare-button`，高 44px，真绿。
2. **触控与截断只判首屏**：原实现对两者都做"滚动出视口就跳过"。但 `rect.height` 与 `scrollWidth/clientWidth`
   与滚动位置无关，这个过滤让 Live 首屏之下的模式芯片与 compare 按钮**完全没被量过**（表现为 `small=0`，看着像绿）。
   去掉过滤后 Live 仍是 0 —— 那才是绿。
3. **遮挡判定读的是未滚动的矩形**（造成 v1 的假阳性）：`page.evaluate` 里同步调 `scrollIntoView` 后立刻读
   `getBoundingClientRect()`，滚动尚未提交。诊断字段直接抓到证据：
   `scroller=html scrollTop 0->0（可滚 1031px）ctaTop 859->859` —— 一次都没滚。
   改为显式 `window.scrollTo` + 等两帧 + 回读，并新增 `scrollBlocked` 自诊断：滚不动时报"页面拒绝滚动"，
   **不再报遮挡**。修后 12/12 点 `navCover=0`，Wallet 那条撤回。

## 结构性结论（本轮最高价值的一条）

`V8Experience.tsx:818` 是 `if (setupOpen) return <JourneyTrialSetup …/>` —— **Journey 创建整屏渲染在
`.v8-product-shell` 之外**。它因此同时丢掉四样东西：

| 丢掉的东西 | 定义位置 | 后果 |
|---|---|---|
| `--v8-*` 全部变量 | `styles.css:125`（壳层内） | 只能走 fallback，主按钮变青色 `#0f766e` |
| Apple 调色板 + 暗色重绑 | `design-tokens.css:118`（壳层内） | 首进门面完全不跟手系主题 |
| 左右留白 | `.v8-content { padding: 38px 46px }`（壳层内） | **内容贴屏幕边**，eyebrow 文案首词被切 |
| 文字颜色 | `body` 从未设 `color`，只有 `.v8-product-shell{color:var(--v8-ink)}` | 暗色下表单标签**暗底暗字不可读** |

所以限制 (1) 的 token 上提不是可选重构，而是修好 Journey 创建的**前置条件**。

## 限制 (1) 批次：token 上提 —— 已做，门未变红

改动（`review/patches/step3-token-hoist.patch`，2 文件 / +28 −6）：
- `styles.css:125` 的 `--v8-*` 字面量默认值 `.v8-product-shell` → `:root`
- `design-tokens.css:118` 的 Apple 重绑 `.v8-product-shell` → `:root`（壳层规则只留字体与抗锯齿）
- 在 `:root` 上真正定义此前从未定义的 `--v8-accent: var(--cn-accent)` 与 `--v8-surface: var(--cn-surface)`
- `styles.css:592` 吸底栏渐变的 `var(--v8-surface, #0b1f24)` → `var(--v8-canvas)`（它要的是页面底色不是遮罩）

**陷阱已避开**：`styles.css:125` 与 `design-tokens.css:118` 原本用同一个选择器，后者靠加载顺序赢。
若只搬绑定不搬字面量，壳层内更具体的 `.v8-product-shell` 字面量会赢回去 → 全应用退回旧配色。两处必须同时上提。

改完立刻跑三道门（`review/gates-after-tokenhoist.log`）：

| 门 | 结果 |
|---|---|
| `qoder-contrast-audit.spec.ts`（Today/Live 明+暗、对比 + focus 3:1，mobile + desktop） | **4 passed** ✅ 未变红 |
| `qoder-mobile-overflow.spec.ts` | **1 passed** ✅ 未变红 |
| `qoder-mobile-ui-overnight.spec.ts` | 红名单与基线**逐字相同** → 无几何回归 |

→ 按限制 (1) 不回退。

目视复核（`review/evidence/verifyhoist/setup-step1-{light,dark}-412x915.png` 对比
`review/evidence/before/setup-step1-*.png`）：
- 明色：Next 按钮由青变 Apple 蓝；按钮上方那条近黑横带消失；步骤"1"徽标变蓝
- 暗色：`Create a trip` 标题从**暗底暗字不可读**变白字可读；Next 由青底深字变蓝底白字
- 暗色下表单标签与输入框仍是亮的（`body` 无 `color` + UA 默认白底输入框）—— 改动前就存在，是下一批的目标

## 下一步

4. 限制 (2)：`viewport-fit=cover` 与真实 safe-area 留白同批
5. 红项 (a)(b) + 上面表格里的第 3、4 行（留白与 `body` 文字色）+ trial 暗色泄漏
