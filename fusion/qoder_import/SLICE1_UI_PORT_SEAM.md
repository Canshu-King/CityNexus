# 收藏 / 打卡的前端半片：移植接法与它必然要改的那三处（2026-10-14 19:04）

起因：我这轮把融合分支的 collections 读门改成「只认签名凭据、不接受点名」之后，重新去核对源树的界面腿。结论是**源树有完整界面且已注册**（不是我 §1 那句话可能被读成的「没人入口」），但它调的正是我已经关掉的那扇形状。这份文件写的是接法与证据，全部 `git show`/`git grep` 现读，没碰任何工作树。

## 1. 两边到底有什么（先把「谁缺什么」钉准）

| 树 | `features/collections/` | `features/checkin/` | 注册表里有没有 |
|---|---|---|---|
| 移植源 `eeb8b8d2fd` | **5 枚文件** | **6 枚文件** | 有：`v8PanelRegistry.tsx:6` 引 `CollectionPanel`、`:246` 渲染、`:30` 引 `FootprintPanel`、`:420` 渲染；`TripItinerary.tsx:24` 引 `CollectInto`、`:586` 渲染 |
| 台上树 `cca117cf1a` | 5 | 6 | 有（同源） |
| 内联双语权威尖 `f6e936c8e85e` | 5 | 6 | 有 |
| 融合基线 `594f9a4e75` | **0** | **0** | **无**：`git grep -c "collections\|checkin\|footprint"` 对融合 `frontend/src/app/v8PanelRegistry.tsx` 命中 0 |
| 我这枚 import 尖 `85b48a27d7`（§3 落地后） | **5** | **5** | 有：注册表两枚 `route` 条目 + `TripItinerary` 两条写腿（`git ls-files` 计数、`grep -c CollectionPanel\|FootprintPanel` = 4） |

⇒ 更正我 `QODER_PARITY_draft_r1.md` §1 那句「彻底没有用户入口的 7 条」的**措辞**：那条只在**融合树**上成立（数过、站得住），源树这 7 条里至少收藏与打卡/足迹两条是有入口的（上面四行行号）。CSV 的 `state` 列本来就是按源树记 `LIVE_IN_UI` 的，两张件合起来看没有矛盾，但 §1 的标题不带限定语会让人误读，我已去改标题。

## 2. 移植过去必须改的三处（不改就是必红）

源树的界面按「调用者自报身份」写，我这轮把后端那条契约换了。逐处对着说：

**第一处 · 读门不能再点名。** `frontend/src/features/collections/collections.ts:63` 拼的是
`${COLLECTIONS_LIST_PATH}?traveler_id=${encodeURIComponent(travelerId)}`。
这枚 import 分支的同一扇门现在**结构性不接受这个参数**（我实测 422，`reason_code` = `COLLECTION_TRAVELER_SCOPE_PARAM_NOT_ACCEPTED`）。
⇒ 移植时这一行改成只发 `COLLECTIONS_LIST_PATH`，作用域由服务端从令牌解。

**第二处 · 源树的 fetch 根本不带凭据。** 同一枚文件 `:45` 的请求头只有 `content-type`（加可选 `init.headers`），全文件 grep `Authorization` 命中 0；源树 `frontend/src` 里带 `Authorization` 的 8 个文件也没有 `features/collections/`。
⇒ 原样搬过去，第一次读就是 **401**。融合树自己有现成的家规：`frontend/src/lib/travelerSession.ts` 暴露 `travelerAuthHeaders()`（令牌存 sessionStorage 键 `citynexus.traveler.bearer`，文件头写明「Member identity is always resolved by the server from that token」），`frontend/src/api/citynexus.ts:6` 引入、在 `:2717`、`:2747`、`:2754`、`:2767` 等处 `headers: travelerAuthHeaders()`。
⇒ 移植后的 collections 客户端照这个写法接，不要自己发明一套 token 存取。

**第三处 · 注册表那一行不该再传 `travelerId`。** 源树 `v8PanelRegistry.tsx:246` 是
`render: (s) => <CollectionPanel travelerId={s.data.journey?.traveler_id ?? null} />`。
组件 `CollectionPanel.tsx:39` 收 `travelerId` 并在 `:46` 用它当「有没有身份」的开关（`if (!travelerId)` 走空态）。
⇒ 在融合树上身份来自会话令牌，不看 journey 数据里的字段。这条改动会把 `CollectionPanel`/`CollectInto` 的 props 与那两个空态分支一起带进来（`CollectInto.tsx:145`、`CollectionPanel.tsx:81` 都以 `!travelerId` 为门），所以**不是删一个 prop 就完**，两个组件都要跟着改；`subscribeTravelerBearer()` 是那四个调用点在没令牌时的订阅来源。

## 3. 落地的事实（2026-10-14 21:46，import 尖 `85b48a27d7`）

上面那三处都按 §2 改了，改完的形状：

- `features/collections/collections.ts`：`readCollections()` **无参**，只发 `COLLECTIONS_LIST_PATH`，头上带 `travelerAuthHeaders()`；`features/checkin/checkins.ts` 同一法（打卡门本来就不点名，但要凭据）。
- `CollectionPanel` / `CollectInto` / `FootprintPanel`：身份开关从 `!travelerId` 换成 `readTravelerBearer()` + `subscribeTravelerBearer()`，**props 里没有 `travelerId`**。注册表那两枚条目因此只传 `journeyId`/`timezone`。
- 面板挂在既有注册表，不碰 494 行的 `V8Experience.tsx`：`{id:"collections", surface:"route", when: s.route==="discover"}`、`{id:"footprints", when: s.route==="trips" && !s.detailActivity && Boolean(s.data?.journey?.id)}`。
- 词典只动了 **1 枚键**（`checkin.title`，两个语种各一行），其余句子留在本片的私有词表。这条更正见 `../QODER_PARITY.md` §9 开头。
- `features/checkin/` 在融合树是 **5 枚文件**不是 6：`footprintRead.ts` 没搬。它是地图面专用的合批读（要 `mapPanelCopy.ts` 里 6 枚 `footprint*` 键，融合树没有），搬过来就是死码 + 一次词典追加。

一处**故意保留的源树缺陷**，不是我看漏：`TripItinerary` 的读腿在答案不是 `read` 时静默返回，于是每一次打卡在重读之前都可能显示为「打卡」。源树 `footprintRead.ts` 的头注释自认了这一点。移植期按「照搬不改行为」处理，改它属于 §5 的独立一刀，混进这次移植会让评审分不清哪一行是搬来的、哪一行是我加的。

## 4. 守门测试与它的复跑法

`frontend/e2e/qoder-ord0510-ported-faces-answer-the-doors.spec.ts`，四条腿 + 布景 setup 在同一条权威栈上真起后端：

```
cd frontend && env -u DEEPSEEK_API_KEY CITYNEXUS_E2E_AUTHORITATIVE=1 \
  CITYNEXUS_E2E_PORT=4405 CITYNEXUS_BACKEND_PORT=8105 \
  CITYNEXUS_PYTHON="D:/moodle/CityNexus/.venv/Scripts/python.exe" \
  CITYNEXUS_DATABASE_URL="sqlite:///.../\_e2e_uiportr6.db" CITYNEXUS_E2E_RUN_ID=uiportr6 \
  CITYNEXUS_AI_ENABLED=false CITYNEXUS_TRAVELER_AUTH_SECRET="<≥32 字节>" \
  node node_modules/@playwright/test/cli.js test \
  e2e/qoder-ord0510-ported-faces-answer-the-doors.spec.ts --project=chromium --reporter=line
```

`5 passed (21.6s)`，当轮数值落在 `reports/qoder-ord0510/{A_footprint,B_duplicate,C_collect,D_scope}.json`（已随测试入库）。
两条约束别踩：`CITYNEXUS_E2E_AUTHORITATIVE=1` 下后端**拒绝重开已有库**，每轮要换 runId/库/端口；shell 里带着 `DEEPSEEK_API_KEY` 时它会照打云端，必须 `-u`。

这一版**前两次都红过，红在我自己的量具上**，两条都值得记下来给下一片：
1. **数目是在重读落地之前取的**。arm B 点完一次打卡后立刻读 `footprint-tally`，量到的是面板上一次的答案（只有 arm A 那枚 ⇒ `1 枚`），等第二次重读才追上服务器的 `2`。看着像「409 多写了一枚」，其实是断言没有边界。改法：先 `GET /checkins` 取真数，再用 `toContainText(\`${n} 枚足迹\`)` 把面板钉到那个数上——这样若 409 真写了一枚，钉住的等待会直接超时喊红，比自我比较更严。
2. **`CollectInto` 的入口是 toggle，而且它的 onClick 先清答案行**。arm C 第二次还去点入口，等于把正开着的 picker 关掉、顺手把要断言的 `collect-result` 卸了，那一腿因此是 240 s 超时而不是失败。改法：首按之后 picker 仍在，直接点同一枚架子行，`toContainText("这一枚已经在这个架子上")` 本身就是带边界的等待（上一句答案不含这段文字，不会蒙对）。

另记一条闸的边界：`tsconfig.typecheck.json` 的 include 只有 `src/**`，**spec 不在项目的类型闸里**——这条后来真的咬了我一口（见 §5 第三条）。

## 5. 走查那一屏：把两条 spec 共用的布景抽出来，以及它暴露的三个量具缺陷（2026-10-14 22:11）

号令者第 7 条与 Deliverables 要的是「one **saved** 390x844 Chromium route walkthrough against one fused backend」，所以补了 `frontend/e2e/qoder-ord0510-walk-390x844.spec.ts`（180 行，7 屏）。四条腿的 spec 同时瘦了 82 行：`stage/openAs/ask/tokenFor/flat/checkinsPath/VIEWPORT` 移进 `frontend/e2e/_qoderOrd0510Stage.ts`（107 行）。两条 spec 现在跑在同一条权威栈上（`6 passed (24.0s)`，runId `uiportr10`，库 `_e2e_uiportr10.db`，后端 :8110）。

三个缺陷都在量具上，不在产品上，但每一个都能让「绿」失去意义：

1. **上一轮那次走查是可疑的**：旧的 `brick-fusion-boot-u1` 存档里 PNG 按字节两两相同（38910/38910、36444/36444）——那就是一页没动的样子。所以走查最后一条断言是 `expect(new Set(digests).size).toBe(frames.length)`：**重复的截图是红，不是绿**。本轮 7 枚摘要 `858f87065aa5 61499d8f14d2 5e15fe552880 88d0790ca89a ba91cf81adca fe3eae4247da c51ef6b2e014`，7 枚各不同；`03/04` 两屏 h1 都是「3 天行程」而字节 45569→41655，说明这条规则真的在比字节而不是比标题。
2. **`filter({ has: [data-state="fresh"] })` 是一枚会自我作废的定位器**。第一次走查因此红在 03→04 之间：按下之后那一行掉出筛选集，`.first()` 顺势改指下一枚没盖章的行，等待就在**从没点过的那一行**上等 42 次 `unexpected value "fresh"`。改法：先 `count()` 再按 `nth(i)` **一次性定住行号**，之后所有断言都指着同一个行号。本轮 `stop_rows=3, stamped_row=2, stamped_stop="Overnight · Haihe Riverside Hotel"`——前两行已被四条腿盖过，这条腿必须自己找出还能按的那一枚。
3. **抽共用 fixture 时漏了 `tokenFor` 的 import**，arm D 直接 `ReferenceError`，而 `npx tsc -p tsconfig.check.json / -p tsconfig.typecheck.json` 两枚闸都 **RC=0**（spec 不在 include 里，见 §4 末）。补一条能在 60 s 浏览器跑之前喊红的量具：
   ```
   npx tsc --noEmit --skipLibCheck --types node --lib dom,dom.iterable,es2023 \
     --module esnext --moduleResolution bundler --target es2022 --jsx react-jsx \
     e2e/_qoderOrd0510Stage.ts e2e/qoder-ord0510-*.spec.ts
   ```
   反向对照做过：把 `tokenFor,` 那行从 import 里删掉再跑 ⇒ `error TS2304: Cannot find name 'tokenFor'`，且只有这一条；补回来 ⇒ **RC=0**。这条不入库为闸（不改项目 config），作为下一片复用 fixture 时的一行自测。

GO 那一腿（号令者第 7 条的后半）在走查里是**按实测记的**，不是按愿望写的：`/v8/*` 七屏之外没有第七个地址能打开 `bootstrap-discovery`（manifest 里 `go_bootstrap_reachable_by_url: false`，`getByTestId("bootstrap-discovery").count()` 实测 **0**），因为它在 `V8Experience.tsx:1212` 是状态门——要一座目录为空的城里的新行程。所以走查记的是「它不在这儿」，而「它的读门没人调」仍在 `fusion/QODER_PARITY.md` §5 挂着，判责在 Codex 的 `fusion/codex-journey-20261014`。
