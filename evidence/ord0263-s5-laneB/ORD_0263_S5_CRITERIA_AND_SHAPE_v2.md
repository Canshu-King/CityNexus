<!-- 勘误（v2）：本文件是 ORD_0263_S5_CRITERIA_AND_SHAPE.md（blob `d80ac353ea2f…`, 13,328 B）的更正版，v1 原文不覆盖、按已发布路径冻结留档。两处改动：
     (a) §⑤ 第 3 条——v1 写「requestJson 有四处无泛型（`:812 :829 :911 :962`）」是我自己的正则误读：`911/962` 两处其实带跨行泛型。真实的两处 `Promise<unknown>` 是 `selectPlan`(:811) 与 `captureBooking`(:828)，只被 demo 脚本 await、无 catch。
     (b) §⑦ 第三条——把「204/空体未量」换成读数：后端 1 处 204（main.py:4506），前端 1 处 DELETE（citynexus.ts:1056，走 requestJson 的空体支），v8Request 侧 15 个调用点无 DELETE ⇒ 误伤面 0（源码层计数）。-->

# ORD-0263 第五态 `ORIGIN_INVALID_RESPONSE` —— 判据 + 形状（先交这个，产码等放行）

写者：B `c01d72a3`　日期：2026-09-23　射程：源站**答了**、答的**不是这一屏的数据**（2xx + HTML 文档）。
本文只交三样：我自己的复量读数、缺陷的机械指纹、判据与形状。**没有产品代码**，除第 ⑤ 节列出的改动清单。

---

## ① 复现：我自己的两代实测（真实 HTTP，不是浏览器 mock）

面：`vite preview :4441` → 源站 `:8441`，构建自 landed tip `2b49e3ca`（含 ORD-0263），产物目录 `dist_ord0268`。
归属双向先证再信：`GET http://127.0.0.1:4441/v8/hub` 的字节 == 我磁盘上 `dist_ord0268/index.html`（两侧 sha256/16 都是 `3cb318326b13a033`）；经代理取回的 health 体里含我源站的标记 `ord0263-s5`。
被复现的现场由我造：真 uvicorn 先进面并落快照，然后**同一端口**换成一台「GET → `200 text/html`、`/api/*/health` → `200 application/json`、POST → 收下不答」的真 HTTP 服务器。
本轮 driver 与全部仪器只连 `127.0.0.1:4441 / :8441`；`4781 / 4782 / 8693 / 4185 / 8713` 不在我的地址表里（我没去量它们，也就没碰）。

| 格 | 第 1 代 `s5_state.json` | 第 2 代 `s5_second.json`（独立浏览器代、独立进程） |
|---|---|---|
| 时刻 | 2026-09-23T15:15:18.937Z | 2026-09-23T15:19:43.429Z |
| 屏幕（`innerText`，非 data 属性） | 「连接 / **网络不可用** / 这一发请求没能出去，也没有收到任何回答，所以这是网络问题。你的行程数据没有丢失，已保存的只读副本还能看。请检查网络后重试。 / 看已保存的只读副本 / 重试 / 归因详情」 | 同一句，逐字相同 |
| 产品自记的归因 | `reason=NETWORK_UNAVAILABLE` `evidence_kind=TRANSPORT` `http_status=null` `source_layer=TRANSPORT` `message_key=failure.networkUnavailable` `recovery_action=read-only-cached` `context=shell.boot.journeyRead` | 同一枚，逐字相同 |
| telemetry 原文 | `attribution_reason=NETWORK_UNAVAILABLE evidence_kind=TRANSPORT http_status=none source_layer=TRANSPORT retryable=true recovery_action=read-only-cached cached_copy_present=true` | 同上 |
| 同一瞬间同页探针 | `200 application/json`，9 ms，`thrown=false` | `200 application/json`，4 ms |
| 源站那一发读 | `200 text/html`，体首 `<!doctype html><html><head><meta c`（直连与经代理各一次） | 计数累计 `html_for_api_get=2`、`health_json=4` |
| 分类节点 | `failure-view=1 failure-reason=1 failure-read-cached=1 failure-retry=1` | 同上 |
| 本地快照 | `present=true count=1 store=journeys` | 同上 |

⇒ 红队 A1 的读数我独立复量成立（两代一字不动）。**屏幕上写「这是网络问题」的同一页、同一秒，就有一次 `200` 的探针在反证它**，而产品把这一次 200 当成了支持网络无罪的证据——方向正好相反。

## ② 机械指纹（不必改尺就能跑的红）

用 HARNESS 冻结尺（`ord0263_verifier.py`，blob `ed8a61dc79d87cc2acf18ef93ecca7caf89b4b83`）已有的两个派生量：

```text
answered(S5)  == True                       # 尺 :47-50：status 是 int 且 thrown is false —— 源站确实答了
classified_label(S5) startswith "NETWORK_UNREACHABLE"   # 我的 capture :109-131 从产品归因派生 = NETWORK_UNREACHABLE_WITH_SNAPSHOT
⇒ 指纹 = 「answered 为真」且「标签属于 NETWORK_UNREACHABLE 家族」同时成立 = 当前为 RED（缺陷的机械形状，与文案无关）
```

## ③ 成因：三处字节的合谋（都在 landed tip 上，逐行读得）

1. `app/V8Experience.tsx:189` `const body = await response.json().catch(() => null);` —— 2xx 的 HTML 体解析失败被咽成 `null`，`:190 if (!response.ok)` 不成立，`:197 return body as T` 把 **HTTP 事实整个丢掉**。（尺 `ord0263_verifier.py:48` 那句注释仍写 "the fact `:198` throws away"：0263 落地后行号漂了 1 位，真实返回行是 `:197`。**在此报告，不动尺**。）
2. 下游对 `null` 取属性 → `TypeError` → `boot()` `:637 classifyReadFailure(error)` → `lib/failureAttribution.ts:152 if (error instanceof TypeError)` → `NETWORK_UNAVAILABLE / TRANSPORT / null`。**`:150` 的注释写着「这是唯一允许说网络不可用的分支」，而它这次拿到的证据其实是「源站答了 200」。**
3. `:638-641`：`if (attribution.evidence_kind === "TRANSPORT")` 才去探健康，且 `:641 if (!fact.ok)` 才覆写 —— 探针 2xx 时谎话被**保留**。这是红队第二点，我复量到的是同一个 `:641`。
4. 第二条通道形状不同、也更安静：`api/citynexus.ts:652 text = await response.text()`，`:656 JSON.parse` 失败时 `:658 body = text`（**一整段 HTML 字符串**），`response.ok` 成立 → `:668 return body as T` 原样交出。它不抛、不分类、不上屏，把文档当数据交给调用方。同一事实的两种失败形状，判据必须两条都钉。

## ④ 判据（第五格 V5 + 前四格的双向控）

命名建议 `ORIGIN_INVALID_RESPONSE`（名字归仲裁裁）。词表**沿用 HARNESS 冻结的三张**，我不新增自己的表。

| 编号 | 判据（一句话一个事实） | 红在何处（killer，必须是产品侧单变量） |
|---|---|---|
| **V5-a 事实不得丢** | `S5_origin_answered_html` 里 `attribution.evidence_kind == "HTTP_RESPONSE"` 且 `attribution.http_status == 200`（实测那一发的状态，不是写死的常数） | 只把 `catch(() => null)` 改成抛错但错误里不带 status → `http_status=null` → RED |
| **V5-b 不得落进那两个 reason** | `attribution.reason != "NETWORK_UNAVAILABLE"` 且 `message_key != "failure.noAnswer"`（NO_REPLY 家族同禁）→ 即 §② 那枚指纹必须消失 | 把新分支加在 `failureAttribution.ts:152` 的 TypeError 分支**之后** → 永远走不到 → RED |
| **V5-c 屏幕上是一句真话** | `NETWORK_WORDS` 命中数 **=0**；`SERVICE_WORDS` 命中 ≥1（服务器答了 / 答得不合用）；`snapshot_present=true` 时 `SNAPSHOT_WORDS` 命中 ≥1；句子必须把实测的 `HTTP 200` 与 `text/html` 说出来 | 只改分类不改 copyFor → 落 `default` 分支「这一次没读到」，NETWORK_WORDS=0 但 SERVICE_WORDS=0 → RED（这条专防"换个词继续含糊"） |
| **V5-d 两条通道同判** | 同一格跑两腿：腿一 = 有 journey id 的 boot 读（`v8Request`）；腿二 = 走 `requestJson` 的一读（当前返回 HTML 字符串）。腿二要么给出同一具名 reason，要么**明确不产生"读取成功"态** | 只修 `v8Request` → 腿二仍把文档当数据 → RED |
| **V5-e 探针不得用来掩盖** | 健康探针 `200` 时，归因仍是 `HTTP_RESPONSE` 家族，且 `recovery_action` 与两扇门（`failure-retry` / `failure-read-cached`）计数 ≥1 | 改成"探针 200 就覆写成 UNKNOWN_FAILURE" → `evidence_kind=HEALTH_PROBE` → RED |

**控制轮已经跑了（未修树上机械派生，`q263_s5_criteria_control.json`）**：词表从尺里 import（blob `ed8a61dc…`，跑前跑后回验 `ruler unchanged after: True`），我没复制一个字面量。

```text
generation_1: V5a=RED V5b=RED V5c=RED V5d=NOT_MEASURED V5e=RED
generation_2: V5a=RED V5b=RED V5c=RED V5d=NOT_MEASURED V5e=RED      # 两代逐条同判
S1..S4（修前 capture，尺自己的 judge_all）: S1_live=GREEN V1_origin_error_5xx=GREEN V2_no_answer=GREEN V3_distinctness=GREEN
反向哨兵 S3 必须保持：classified_label=NETWORK_UNREACHABLE_WITH_SNAPSHOT 且 origin_answer.thrown=true
```

⇒ 前四格今天不背第五格（它们在修前就已全绿），而 V5 的四条可判项在无修树上恒红 —— 判据有牙齿，不是我写的愿望。

**前四格不得回归（双向控，逐格点名，同一次跑内产出）**
- S1 live：`classified_label=LIVE`、`today-heading=1`、NETWORK_WORDS=0；
- S2 origin 500 + 快照：SERVICE_WORDS=1、SNAPSHOT_WORDS=1、NETWORK_WORDS=0（尺 V1 原样）；
- S3 静默 + 快照：**必须仍是** `NETWORK_UNREACHABLE_WITH_SNAPSHOT` 且 `evidence_kind=TRANSPORT`、LOADING_WORDS=0（尺 V2 原样）。这一格是第五态的反向哨兵——若第五态把「没答」也吸进新态，S3 就红，说明我修过了界；
- S4 探针说话：`SERVER_ERROR` via `HEALTH_PROBE`；
- V3 distinctness 扩到三句互不相同：S2 ≠ S3 ≠ S5（任两句逐字相同即 RED）。当前实测 S3 是「等了 12 秒，这台服务器一个字也没回答…」，S5 是「这一发请求没能出去…」，S2 是「服务暂时不可用…」——三句已不同，但 S5 那句**说的是假话**，所以 V3 扩了也不等于 S5 绿。
- **killer 的 killer（正控）**：把 `:190` 的 `catch(() => null)` 原样放回去 → V5 五判据全红、S1..S4 全绿。这才证明 V5 只测第五态，不顺手重判别人的格。

## ⑤ 形状（我打算怎么改，等你放行）

零新增文件；`AttributionReason` +1 枚，`EvidenceKind` **不动**（`HTTP_RESPONSE` 已够用，这正是最低验收那句"保住 HTTP_RESPONSE"）。

1. `lib/failureAttribution.ts`：新增具名错误 `OriginResponseUnusableError { status, content_type, body_kind }`（该模块本来就是"事实→结论"的唯一所有者，且已导出类型/错误；两条通道都 import 它）。`classifyReadFailure` 里加一支，**位置在 `isReadDeadlineMissed` 之前**（两者都是"有事实"，不能被 TypeError 吞）：识别到它 → `make("ORIGIN_INVALID_RESPONSE", "HTTP_RESPONSE", err.status, "RUNTIME", true, "retry", "failure.originInvalidResponse")`。`recovery_action` 交给既有的 `withCachedCopyFact` 决定门，**新态要进它的 `mayOffer` 允许集（`failureAttribution.ts:199`）**（否则有快照也不给门，就是 S5 屏幕上少一只把手）。
2. `app/V8Experience.tsx` `v8Request`：在 `:190` 那个 `if (!response.ok)` 块之后、`:197 return body as T` 之前插 `if (body === null) throw new OriginResponseUnusableError(response.status, response.headers.get("content-type"), ...)`。非 2xx 路径与 `V8Rejection` 一行不动。
3. `api/citynexus.ts` `requestJson`：`body` 是字符串且响应不是 JSON 口径时抛同一个错误。**误伤面我量了（54 个调用点，正则口径），并且先更正自己的一次误读**：第一版我记成「`:812 :829 :911 :962` 四处无泛型」——`911/962` 两处其实带跨行写的泛型（`Promise<{…}>`），是我的正则吃掉了换行，不是产品没有类型。真实的两处 `Promise<unknown>` 是 `selectPlan`（`:811`）与 `captureBooking`（`:828`），它们只被 `demo/goldenScenario.ts:37 / :42` 以 `await` 调用且**没有 catch** ⇒ 新抛错会打断那支 demo 脚本（不在用户屏幕上，但会让脚本报红）。产码时必须二选一：给那两处补具名 catch，或把新抛错限定在 GET/HEAD 通道（与 §⑤ 第 1 条同一个自限口径）。
4. `copyFor` 新增 `failure.originInvalidResponse` 两分支（有快照 / 无快照），kicker 用「服务器」，句中带实测 `HTTP {status}` 与 `text/html`，**全文不得出现"网络"二字**（由 NETWORK_WORDS 反查）。
5. `boot()` 的 `:638` 不改：新态 `evidence_kind=HTTP_RESPONSE`，天然不会被探针覆写 —— 这个"不用改"正是 V5-e 要断言的事。
6. 仪器：`q263_capture.py` 的 `cells` 增 `S5_origin_answered_html`（字段形状与 S2/S3 相同，另带 `content_type` 与那一发读的 `status/body_kind`），并把 `classified_label` 的打印规则加一行 `reason ORIGIN_INVALID_RESPONSE (+/- copy) -> ORIGIN_ANSWERED_BUT_NOT_USABLE[_WITH_SNAPSHOT]`。尺那一格 `judge_v5_*` 与 `ARBS` 第四枚标签归 HARNESS 写——尺不是我的，我只交 capture 与判据。

## ⑥ A3 判定：写腿永挂时屏幕**没有**说同样的谎 ⇒ 不并本单

现场（同面、同一条源站，POST 收下不答）：`POST /api/v1/travelers` 发出后 **0 条响应**（源站计数 `post_hanging=1`），10 次采样覆盖 0→10.2 秒。屏幕全程只报「正在登记出行人」+「已等待 N 秒」（秒数真实递增）+「第一次搜索一座城市实测要两分钟左右…这里只有真实秒数，没有编出来的数字」；「停止等待」第 0 秒就在，我在 8.2 秒按了它，屏幕答「已停止等待 / 已停止等待，行程还没有创建。」全程 **0 条归因记录、0 个 `failure-view`**，`ever_blamed_network_or_origin = false`（44 句不同文案里 NETWORK/SERVICE/OFFLINE 命中 0）。

⇒ A3 与第五态**不同族**：那里缺的是"期限"，不是"归因"。`lib/readDeadline.ts:43-44` 对非 GET/HEAD 直接 `return fetch(input, init)`（我 0263 的具名自限：写腿的期限牵动幂等，不由本单答），所以挂起的写腿只能靠人自己按「停止等待」——这属 ORD-0262 家族。我不并单、不扩面。
仪器自报：`hit_test=NONE`（滚动页中心点取不到节点，我没先 `scrollIntoView`），该字段不作数；门的可用性由点下去之后**渲染出来的**「已停止等待」证明。

## ⑦ 还欠的格子（不假装闭合）

- 「生产现场也会返回 200 + HTML」是我在自己的部署层造出来的，**不是**从 `:4781 / :8693` 量到的（那两台我不能碰）⇒ 现场形态是推断，事实链只到我这两代。
- V5-d 的腿二（`requestJson`）今天只有源码形状，现场"向导里某读 200+HTML 时屏幕说什么"我没量到。
- 空体面我量了源码一侧：后端只有 **1 处** `status_code=204`（`app/main.py:4506`，`DELETE /journeys/{id}/constraints/{constraint_id}`），前端只有 **1 处** `method: "DELETE"`（`api/citynexus.ts:1056`）⇒ 它经 `requestJson`，204 的空体走 `body = null` 那一支，**"字符串才抛"的判定不会命中它**；`v8Request` 侧 15 个调用点（`grep -c "v8Request<"` = 16，其中 1 处是它自己的声明行）里没有 DELETE ⇒ `body === null` 抛错的 204 误伤面 = 0。口径要说白：这是源码层的计数，不是逐端点的运行时探针。
- 新态的英文臂（en-GB）文案未拟 ⇒ 交给 copyFor 表同一次改动，判据里只钉中文臂（与 0263 落地时一致）。
