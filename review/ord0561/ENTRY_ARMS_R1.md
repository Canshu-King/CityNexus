# ORD-0561 续 · 将入口方式做成一臂：底栏点击进入 对 直接地址，口径差从此有数

代次：尖 `4d43f8bc25a1a2f4e4c752afe08851032ab6c71d`（`git ls-remote --refs origin refs/heads/mirror/integration-frontend-apple-pass1` 现读），两臂共用同一份产物：入口 `http://127.0.0.1:4892/assets/index-iZ6I1MKH.js`、1623095 字节，服务字节 sha1 与磁盘字节 sha1 逐字相同 `c1b65cc2c9bb8b4c59b554c6181b51eddb1e19fa`；私有栈 api pid 59772 / static pid 29420，库 `_r5_rch5.db`，静态口代理 CITYNEXUS_BACKEND_PORT=4891。本件写时线尖 `4d43f8bc25a1a2f4e4c752afe08851032ab6c71d`。

## 一、为什么要这一臂

上一件（`review/ord0561/REACH_INSTRUMENT_R6.md`）里我把两把尺在 `covered` 上的差归因到三条，其中两条是“入口方式不同”：`1ba48dbf` 那把是按底栏 `nav-<key>` 点击进入，我那把是按地址直达。解释不算读数，所以这一件把入口本身做成一臂，让那个差变成带名字的数。

## 二、仪表改了什么

`sweep_ink_r1.cjs` 新增 `ENTER=nav`：先落 `/v8/hub`，再点 `[data-testid="nav-<key>"]`，并 `waitForFunction(location.pathname 含该 key)` 才认这次进入——点不到或没换页就写进 `refusals` 具名报出，不默默回退到地址进入。底栏只挂 5 枚（`hub、trips、map、agent、me`），其余路由在这一臂里进 `skipped` 数组并计数（本代导航臂 0 条、地址臂 0 条）。每一趟另记 `path_walked`（当场回读 `location.pathname`）。

配对条件（不满足就拒，不对齐就不比）：两臂同尖 `4d43f8bc25a1`、同入口资产 `index-iZ6I1MKH.js`、同形 `390x844`、同档 `light`、同两臂 `zh-CN、en`、逐屏 `path_walked` 逐枚相等。

## 三、结果

每臂 10 趟（5 屏 × 2 臂），两臂全部挂载。逐类合计（点击进入 对 地址直达）：

| 类 | 点击进入 | 地址直达 |
| --- | --- | --- |
| `covered` | 37 | 37 |
| `clipped` | 4 | 4 |
| `ellipsis` | 12 | 12 |
| `no_name` | 0 | 0 |
| `glyph_name` | 35 | 35 |
| `below_floor` | 21 | 21 |

逐屏逐类同数的格子 56/60；按枚身份比（y 精确）只在一臂出现的：点击臂 6 枚、地址臂 6 枚；换成 8 px 容差再比：点击臂 3 枚、地址臂 3 枚（差的那几枚全是 `Map marker`，同物同命中方、只是列表在两次进入里各滚了一两像素，所以这是**我这把尺的身份键太严**，不是屏不同）。

并且六类的**合计枚数在两臂完全相同**（`covered 37对37、clipped 4对4、ellipsis 12对12、no_name 0对0、glyph_name 35对35、below_floor 21对21`）。⇒ 我上一件写的解释被我自己这一手证伪了一半：「入口方式不同」并不能解释 `covered` 与 `1ba48dbf` 那把的差，剩下的解释只有「选择器面宽窄」（我这把多收 `a[href]` 与 `[role=button]`）与它那趟走查时的面板状态；前者我这手能算，后者要把它那把的原始逐枚读数拿来同屏比（件里 `review/ord0561-screens/walk_r2.json` 可取）。我不改口径去凑相等，只把这条解释降级为已证伪。

### 只在一臂出现的（具枚，不集合化）

- 只在点击进入臂：`en` 类 `covered` 在 `/v8/hub`，`Map marker|SPAN|810`。
- 只在点击进入臂：`en` 类 `below_floor` 在 `/v8/hub`，`Map marker||810`。
- 只在点击进入臂：`en` 类 `covered` 在 `/v8/map`，`Map marker|CANVAS.maplibregl-canvas|523`。
- 只在点击进入臂：`zh-CN` 类 `covered` 在 `/v8/hub`，`Map marker|NAV.v8-mobile-nav|763`。
- 只在点击进入臂：`zh-CN` 类 `covered` 在 `/v8/hub`，`Map marker|path|791`。
- 只在点击进入臂：`zh-CN` 类 `below_floor` 在 `/v8/hub`，`Map marker||763`。
- 只在地址直达臂：`en` 类 `covered` 在 `/v8/hub`，`Map marker|SPAN|809`。
- 只在地址直达臂：`en` 类 `covered` 在 `/v8/hub`，`Map marker|svg|782`。
- 只在地址直达臂：`en` 类 `below_floor` 在 `/v8/hub`，`Map marker||782`。
- 只在地址直达臂：`en` 类 `below_floor` 在 `/v8/hub`，`Map marker||809`。
- 只在地址直达臂：`en` 类 `covered` 在 `/v8/map`，`Map marker|CANVAS.maplibregl-canvas|522`。
- 只在地址直达臂：`zh-CN` 类 `covered` 在 `/v8/hub`，`Map marker|svg|791`。

## 四、演示门与现场

`demo/reset` http_status=200、`prepare-scenario` http_status=200、`demo/scene` http_status=200，站点 6 段、无坐标 0 段，错 token 的重置回 http_status=403，分享授权回 http_status=201。

## 五、这一手没做的

产品字节 0 枚改动。两臂都只读屏：没点任何写侧控件、没重启服务、没动 `4783` 那枚预览口、`demo/reset` 只落我自己的库。`C4` 那族按屏逐枚的可裁表仍未交（下一手）。前端 e2e 整套没跑（`NOT_EXECUTED_BY_CMDR`）。

