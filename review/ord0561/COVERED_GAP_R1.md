# ORD-0561 续 · covered 的 37 对 61 拆到枚：两把尺的定义差三条、剩下 13 枚未解释具名报出

代次：我这把在 `4d43f8bc25a1a2f4e4c752afe08851032ab6c71d`（`git ls-remote` 现读，本件写时线尖 `4d43f8bc25a1a2f4e4c752afe08851032ab6c71d`）；它那把的逐枚读数取自枝 `refs/heads/review/1ba48dbf-ord0561-screens-r1` 的头 `d9424847a51a04b0a0d8e6fb731a0476606b6137`，件 `review/ord0561-screens/walk_r2.json`的 git blob `e0e6cfbd9b79753d032044cbaa29efceb4a8e9e3`（37103 字节，我本机这份与它逐字节相同），同枝另有 `which_button_r1.json` blob `fa3d9021b1264681b650cb1e940280c8158ea6f6`（775 字节）。它那件 `errors` 为空数组 ⇒ 它的逐屏读数是落到了东西的。**两把取的不是同一代**（它走的是号令者验证栈 `http://127.0.0.1:4783`，视口 844 px、底栏点击进入），所以下面只把差归到「能算的定义」，剩下的留在未解释里，不并进任何一边。

## 一、为什么还做这一手

上一件（`review/ord0561/ENTRY_ARMS_R1.md`）我把入口方式做成一臂，结果六类合计两臂逐类相同——「入口方式不同」这条解释被我自己证伪。剩下的差只能一枚一枚对，所以这手不比总数，比身份。

## 二、两把尺的定义差（三条，全部现读对拍）

| 条 | 它那把 | 我这把 | 我用的比法 |
| --- | --- | --- | --- |
| 选择器面 | 只 `button` | `button, a[href], [role=button]` | 只我读到的按标签归类 |
| 中心在视口外 | 仍计入（该 `getBoundingClientRect` 的 y 可超出 844 px，且 `hit_by` 留 null） | 按定义跳过（`elementFromPoint` 在视口外无意义） | 按 `box` 中心是否出视口归类 |
| `hit_by` | 视口外不记名 | 每枚记命中方与是否底栏 | **身份只用渲染文字**，不然是拿定义差冒充屏差 |

## 三、结果

同形 `390x844` 档 `light` 两臂五屏：我 covered 37 枚、它 61 枚；按渲染文字同枚 8 枚；只我读到 20 枚（其中 16 枚落在它那把根本不查的选择器面上、剩 4 枚未解释）；只它读到 44 枚（其中 35 枚中心在视口之外、剩 9 枚未解释）。

### 同枚的 8 枚（两把都读到，渲染文字归一后）

- `AskCopilot` 在 `/v8/agent`（en 臂）。
- `SkylineDinnerHouse` 在 `/v8/map`（en 臂）。
- `Abortthistrip` 在 `/v8/trips`（en 臂）。
- `为什么这样安排？` 在 `/v8/agent`（zh-CN 臂）。
- `如果我多待60分钟会怎样？` 在 `/v8/agent`（zh-CN 臂）。
- `找附近的室内地点` 在 `/v8/agent`（zh-CN 臂）。
- `SkylineDinnerHouse` 在 `/v8/map`（zh-CN 臂）。
- `中止这趟行程` 在 `/v8/trips`（zh-CN 臂）。

### 未解释的残余，逐枚（我不并进任何一边）

- 只我这把读到：`The view is on your journey` 在 `/v8/hub`（en 臂），命中方 `NAV.v8-mobile-nav`。
- 只我这把读到：`Export calendar` 在 `/v8/trips`（en 臂），命中方 `BUTTON#nav-hub`。
- 只我这把读到：`视野正落在这段行程上` 在 `/v8/hub`（zh-CN 臂），命中方 `NAV.v8-mobile-nav`。
- 只我这把读到：`10月10日周六6 项` 在 `/v8/trips`（zh-CN 臂），命中方 `SPAN`。
- 只它那把读到：`Bookings` 在 `/v8/trips`（en 臂），中心 y=105、命中方 `它那件里该字段为 null（视口外不记名）`。
- 只它那把读到：`Sat 10 Oct6 stops` 在 `/v8/trips`（en 臂），中心 y=752、命中方 `NAV`。
- 只它那把读到：`Spend` 在 `/v8/trips`（en 臂），中心 y=105、命中方 `它那件里该字段为 null（视口外不记名）`。
- 只它那把读到：`Stay` 在 `/v8/trips`（en 臂），中心 y=105、命中方 `它那件里该字段为 null（视口外不记名）`。
- 只它那把读到：`住宿` 在 `/v8/trips`（zh-CN 臂），中心 y=105、命中方 `它那件里该字段为 null（视口外不记名）`。
- 只它那把读到：`打卡` 在 `/v8/trips`（zh-CN 臂），中心 y=817、命中方 `NAV`。
- 只它那把读到：`花费` 在 `/v8/trips`（zh-CN 臂），中心 y=105、命中方 `它那件里该字段为 null（视口外不记名）`。
- 只它那把读到：`详情 ›` 在 `/v8/trips`（zh-CN 臂），中心 y=817、命中方 `NAV`。
- 只它那把读到：`预订` 在 `/v8/trips`（zh-CN 臂），中心 y=105、命中方 `它那件里该字段为 null（视口外不记名）`。

## 四、`C4` 可裁表（44 行：越过 `768 px` 那条带的每一枚）

| 屏 | 臂 | 屏上文字 | 无障碍名 | 中心 y px | 越界 px | 命中方 |
| --- | --- | --- | --- | --- | --- | --- |
| `/v8/agent` | en | 「Ask Copilot」 | 无 | 812 | 44 | 落在底栏带内 |
| `/v8/agent` | en | 「Ask Copilot」 | 无 | 812 | 44 | BUTTON#nav-trips |
| `/v8/agent` | zh-CN | 「为什么这样安排？」 | 无 | 782 | 14 | 落在底栏带内 |
| `/v8/agent` | zh-CN | 「如果我多待 60 分钟会怎样？」 | 无 | 782 | 14 | 落在底栏带内 |
| `/v8/agent` | zh-CN | 「为什么这样安排？」 | 无 | 782 | 14 | NAV.v8-mobile-nav |
| `/v8/agent` | zh-CN | 「如果我多待 60 分钟会怎样？」 | 无 | 782 | 14 | NAV.v8-mobile-nav |
| `/v8/agent` | zh-CN | 「找附近的室内地点」 | 无 | 821 | 53 | 落在底栏带内 |
| `/v8/agent` | zh-CN | 「找附近的室内地点」 | 无 | 821 | 53 | BUTTON#nav-trips |
| `/v8/hub` | en | 「Skyline Dinner House」 | 有 | 787 | 19 | 落在底栏带内 |
| `/v8/hub` | en | 「The view is on your journey」 | 有 | 787 | 19 | 落在底栏带内 |
| `/v8/hub` | en | 「Skyline Dinner House」 | 有 | 787 | 19 | NAV.v8-mobile-nav |
| `/v8/hub` | en | 「The view is on your journey」 | 有 | 787 | 19 | NAV.v8-mobile-nav |
| `/v8/hub` | en | 「Nexus River Cruise Pier」 | 有 | 788 | 20 | 落在底栏带内 |
| `/v8/hub` | en | 「Nexus River Cruise Pier」 | 有 | 788 | 20 | NAV.v8-mobile-nav |
| `/v8/hub` | en | 「Tech Art Center」 | 有 | 789 | 21 | 落在底栏带内 |
| `/v8/hub` | en | 「Tech Art Center」 | 有 | 789 | 21 | BUTTON#nav-map |
| `/v8/hub` | en | 「Central Food Hall」 | 有 | 790 | 22 | 落在底栏带内 |
| `/v8/hub` | en | 「Central Food Hall」 | 有 | 790 | 22 | BUTTON#nav-map |
| `/v8/hub` | en | 「Riverside Museum」 | 有 | 791 | 23 | 落在底栏带内 |
| `/v8/hub` | en | 「Riverside Museum」 | 有 | 791 | 23 | BUTTON#nav-map |
| `/v8/hub` | en | 「Old Town Gate」 | 有 | 793 | 25 | 落在底栏带内 |
| `/v8/hub` | en | 「Old Town Gate」 | 有 | 793 | 25 | svg |
| `/v8/hub` | en | 「Map marker」 | 有 | 821 | 53 | 落在底栏带内 |
| `/v8/hub` | en | 「Map marker」 | 有 | 821 | 53 | SPAN |
| `/v8/hub` | zh-CN | 「Skyline Dinner House」 | 有 | 768 | 0 | NAV.v8-mobile-nav |
| `/v8/hub` | zh-CN | 「视野正落在这段行程上」 | 有 | 768 | 0 | NAV.v8-mobile-nav |
| `/v8/hub` | zh-CN | 「Nexus River Cruise Pier」 | 有 | 769 | 1 | 落在底栏带内 |
| `/v8/hub` | zh-CN | 「Nexus River Cruise Pier」 | 有 | 769 | 1 | NAV.v8-mobile-nav |
| `/v8/hub` | zh-CN | 「Tech Art Center」 | 有 | 770 | 2 | 落在底栏带内 |
| `/v8/hub` | zh-CN | 「Tech Art Center」 | 有 | 770 | 2 | NAV.v8-mobile-nav |
| `/v8/hub` | zh-CN | 「Central Food Hall」 | 有 | 771 | 3 | 落在底栏带内 |
| `/v8/hub` | zh-CN | 「Central Food Hall」 | 有 | 771 | 3 | NAV.v8-mobile-nav |
| `/v8/hub` | zh-CN | 「Riverside Museum」 | 有 | 773 | 5 | 落在底栏带内 |
| `/v8/hub` | zh-CN | 「Riverside Museum」 | 有 | 773 | 5 | NAV.v8-mobile-nav |
| `/v8/hub` | zh-CN | 「Old Town Gate」 | 有 | 774 | 6 | 落在底栏带内 |
| `/v8/hub` | zh-CN | 「Map marker」 | 有 | 774 | 6 | 落在底栏带内 |
| `/v8/hub` | zh-CN | 「Old Town Gate」 | 有 | 774 | 6 | NAV.v8-mobile-nav |
| `/v8/hub` | zh-CN | 「Map marker」 | 有 | 774 | 6 | NAV.v8-mobile-nav |
| `/v8/hub` | zh-CN | 「Map marker」 | 有 | 801 | 33 | 落在底栏带内 |
| `/v8/hub` | zh-CN | 「Map marker」 | 有 | 802 | 34 | path |
| `/v8/trips` | en | 「Export calendar」 | 无 | 790 | 22 | 落在底栏带内 |
| `/v8/trips` | en | 「Export calendar」 | 无 | 790 | 22 | BUTTON#nav-hub |
| `/v8/trips` | zh-CN | 「10月10日周六6 项」 | 无 | 819 | 51 | SPAN |
| `/v8/trips` | zh-CN | 「10月10日周六6 项」 | 无 | 820 | 52 | 落在底栏带内 |

## 五、这一手没做的

产品字节 0 枚改动，屏也没重跑（两把的读数都已在盘上，这手只做归类）。我没改任何一边的判据去凑相等；残余 13 枚我不解释为「对方错」，它们可能就是我那代与它那代的屏不同——要闭合得让同一代产物被两把各读一遍，那需要一次两把同跑的约定，归号令者排。前端 e2e 整套没跑（`NOT_EXECUTED_BY_CMDR`）。`4783` 那枚口我没读没写。

