ORD-0570 · 路牌工甲 · pendingSetCopy.ts 头三处搬进字典 —— 读数件
================================================================

枝 base（现取）：ae2d96198bb346af5712810ddad3013928e62aa4  refs/heads/mirror/integration-frontend-apple-pass1
取尖命令原样：git -C D:\moodle\CityNexus ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1
工作树：D:\moodle\_qoder_lupaigongjia_0570 （frontend/node_modules 是指向共享库的符号链接，未新增依赖）


一、改动坐标（改动后现读）

字典侧（新建三枚键，两语各三行）
  frontend/src/i18n/LocaleContext.tsx:726  en 锚点 "discovery.pickAnotherDestination"（键插在它下面）
  frontend/src/i18n/LocaleContext.tsx:727  en  "pending.title": "Not on a day yet"
  frontend/src/i18n/LocaleContext.tsx:728  en  "pending.sub": "Places this server says belong to this trip, in no day of it yet."
  frontend/src/i18n/LocaleContext.tsx:729  en  "pending.loading": "Reading the pending set…"
  frontend/src/i18n/LocaleContext.tsx:2144 zh 锚点 "discovery.pickAnotherDestination"
  frontend/src/i18n/LocaleContext.tsx:2145 zh "pending.title": "待规划"
  frontend/src/i18n/LocaleContext.tsx:2146 zh "pending.sub": "这台服务器说这些地点属于这一程，还没排在任何一天。"
  frontend/src/i18n/LocaleContext.tsx:2147 zh "pending.loading": "正在读待规划集合…"

模块侧（删掉本地那三对、改走字典出口）
  frontend/src/features/pending/pendingSetCopy.ts:20   import { dictionaryCopy, type TripLocale } from "../../i18n/LocaleContext";
  frontend/src/features/pending/pendingSetCopy.ts:165  export type PendingMigratedCopyKey = "pending.title" | "pending.sub" | "pending.loading";
  frontend/src/features/pending/pendingSetCopy.ts:166  export type PendingSetCopyKey = keyof (typeof pendingSetCopy)["zh-CN"] | PendingMigratedCopyKey;
  frontend/src/features/pending/pendingSetCopy.ts:173  export function pendingCopy(locale: string, key: PendingSetCopyKey): string
  frontend/src/features/pending/pendingSetCopy.ts:175  const shared = dictionaryCopy(trip, key);   —— 先问字典
  frontend/src/features/pending/pendingSetCopy.ts:177  const table = pendingSetCopy[trip] ...        —— 没命中才回本模块表

非钩子出口本体（号令者单里写的 :2826 是旧尖的坐标；现读两处如下）
  尖 ae2d96198b：frontend/src/i18n/LocaleContext.tsx:2847  export function dictionaryCopy(locale: TripLocale, key: string): string
  本工作树：    frontend/src/i18n/LocaleContext.tsx:2853  同一行（我上面多插了六行键，所以后移六行）

消费方一字未改（这就是键类型里仍要点名那三枚键的原因）
  frontend/src/features/pending/PendingSetPanel.tsx:260  aria-label={say("pending.title")}
  frontend/src/features/pending/PendingSetPanel.tsx:262  <span className="v8-kicker">{say("pending.title")}</span>
  frontend/src/features/pending/PendingSetPanel.tsx:263  <p className="v8-muted">{say("pending.sub")}</p>
  frontend/src/features/pending/PendingSetPanel.tsx:268  {say("pending.loading")}


二、两语屏读（真浏览器渲染，逐字抄屏）

屏读入口：本工作树 frontend/probe-pending-0570.html —— 挂真的是 PendingSetPanel 与真的 LocaleProvider，
  /api/v1 的 fetch 挂成永不 settle 的 Promise，面板因此停在 loading 那一支；这三枚键才在同一屏上同时可见。
  该探针件只用于取读数，不入库（见第六节）。
服务：CITYNEXUS_BACKEND_PORT=4789 npm run dev -- --port 4786 --strictPort  →  VITE v7.3.6 ready in 407 ms
语言切换：localStorage citynexus.locale 置 zh-CN / en 后重新导航（面板自己读这枚键）

zh-CN（locale 未设时浏览器 navigator.language 也是中文，读数以显式置值为准）
  section[aria-label]  = 待规划
  .v8-kicker          = 待规划
  .v8-muted           = 这台服务器说这些地点属于这一程，还没排在任何一天。
  [data-testid=pending-loading] = 正在读待规划集合…
  整块 innerText      = 待规划 / 这台服务器说这些地点属于这一程，还没排在任何一天。 / 正在读待规划集合… / 技术详情
  截图 review_artifacts_0570/shot_0570_zh.png  16068 字节  sha256 e4e81ab1d678ca126b9f67adbc8ff564ab9e0d995a5d98507dab695ccd1a9578

en
  section[aria-label]  = Not on a day yet
  .v8-kicker          = Not on a day yet
  .v8-muted           = Places this server says belong to this trip, in no day of it yet.
  [data-testid=pending-loading] = Reading the pending set…
  整块 innerText      = Not on a day yet / Places this server says belong to this trip, in no day of it yet. / Reading the pending set… / Technical details
  截图 review_artifacts_0570/shot_0570_en.png  14209 字节  sha256 24fc83a2d4d997f06cc482e5058b445e06921a8f300cad7562dcb021fb25c87e

控制台：browser_console_messages level=error → Total messages: 3 (Errors: 0, Warnings: 0)，页面自身 0 条错误。


三、同树 A/B（搬动前后文案一字不差）

命令原样：node _ab_probe_0570.cjs   →  rc=0，产出 _ab_readings_0570.txt（27 行）
before = git show ae2d96198b:frontend/src/features/pending/pendingSetCopy.ts 经 esbuild stdin（resolveDir 指真模块目录）打包；
after  = 本工作树同一文件打包。两臂解到同一份 src/lib/plural.ts；after 另解到本树字典。
before_bytes=11452  after_bytes=11789

  键                     en（before / after）                                              zh-CN（before / after）
  pending.title          "Not on a day yet" / "Not on a day yet"                            待规划 / 待规划
  pending.sub            "Places this server says belong to this trip, in no day of it yet." 同串 / 同串
  pending.loading        "Reading the pending set…" / "Reading the pending set…"            正在读待规划集合… / 同串
  pending.filter（未动）  "Filter" / "Filter"                                               筛选 / 筛选
  pending.empty（未动）   "No place is waiting for a day on this trip." / 同串                这一程没有待规划的地点。/ 同串
  pending.not.a.key      回键名 / 回键名                                                     回键名 / 回键名
  → 六枚键 × 两语 = 12 组读数，before 与 after 全等。


四、闸（都在本工作树跑，命令原样）

  node node_modules/typescript/bin/tsc -p tsconfig.typecheck.json --noEmit   →  退出码 0，输出 0 行
     （删掉探针件后在最终入库树上复跑一次，见第七节）
  npm run build                                                              →  退出码 0
     尾读：mode generateSW / precache 8 entries (2932.56 KiB) / files generated dist/v10-sw.js
  python frontend/scripts/i18n_detail2_parity_r1.py                          →  退出码 1（红，不是我弄的）
     打印 "en keys: 1236 zh keys: 1237"，AssertionError: ('PARITY BREAK', ['me.asksBeforeProtectedChange'])
     这枚缺键不是我这一扇：zh 侧有 me.asksBeforeProtectedChange、en 侧没有，尖上同样红。
     我对拍（parity_diff_0570_r1.py，同一把解析尺跑两枚 blob）：
        尖 ae2d96198b  en=1233 zh=1234  对称差 1 项 ['me.asksBeforeProtectedChange']
        本树          en=1236 zh=1237  对称差 1 项 ['me.asksBeforeProtectedChange']
        delta_en=+3 delta_zh=+3，新增键名 ['pending.loading','pending.sub','pending.title']，删除 0 枚，对称差不变。


五、这扇的旧规矩（写清楚，不藏）

pendingSetCopy.ts 文件头注释原本说这三对（以及其余）刻意留在模块里，不进 LocaleContext.tsx，理由是那扇文件撞车多。
号令者这张单要求搬进字典两侧，我按单搬了；先例是已入库的 frontend/src/lib/failureAttribution.ts:457
（同一形状：模块函数里用 dictionaryCopy 问共享字典）。头注释我没改字，只在类型上方补了一句说明。


六、探针件（不入库，随树留在工作区）

  frontend/probe-pending-0570.html
  frontend/src/__probe_pending_0570/main.tsx
  _ab_probe_0570.cjs / _ab_readings_0570.txt / parity_diff_0570_r1.py / parity_diff_0570.txt
  tsc_0570_after.txt / build_0570_after.txt / parity_0570_after.txt / vite_probe_0570.log
入库的只有：两枚产品文件的改动 + review/lupaigongjia-0570/ 下这份读数件与两张截图。


七、删探针后终树复跑

  探针两件（frontend/probe-pending-0570.html、frontend/src/__probe_pending_0570/main.tsx）删掉后，
  在要入库的那棵树上复跑：node node_modules/typescript/bin/tsc -p tsconfig.typecheck.json --noEmit
  → 退出码 0，输出 0 行（tsc_0570_final.txt）。
  开发服务是我起的（PID 61868，端口 4786），取完读数已 taskkill，端口现读 0 个监听。
