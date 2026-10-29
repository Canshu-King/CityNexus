# 册廿三日：Agent 草案到「正式出发」之间还剩哪几道门

写给要点名裁语的人（号令者／仲裁）与下一棒施工者。每条都带现读坐标；判据不是猜的，是按出来的。

## 门一 · 地点事实（已开，屏上可看）

- 营业时间：Agent 向高德要的那句话现在真的落到地点行里，`backend/app/agent/goal_amap.py:73` 用共享的 `normalize_opening_hours` 包成 `status=VERIFIED_PROVIDER`，`trial/results/20261022_v3_human_chrome/departure-price-evidence-probe-1.txt:7` 到 `:12` 六处已定地点逐条读回 `blocks_opening=false`。
- 具体地点：仍然只由 Agent 的研究步供给；没定地点的那一项在待办里写成「让 Agent 找这一处」（`trial/results/20261022_v3_human_chrome/walk-57-log.txt:28`）。
- 转场路线：只有 Agent 真调过 `route_public_places` 的跳才不算缺，判定在 `backend/app/agent/goal_preparation.py:158`。

## 门二 · 票价：没有来源答，不是我们没问

- `departure-price-evidence-probe-1.txt:16` 现读：这座城市 72 条高德地点里营业时间已知 56 条、**票价已知 0 条**；`:17` 两样都齐的 0 条。
- 高德 `show_fields=business` 的 `cost` 只在餐馆类 POI 出现（`trial/results/20261022_v3_human_chrome/amap-business-fields-1.txt:38` 的 119.00 是人均消费），把它当门票价是造假，所以没接。
- 产品里已有的合法出路：`COST_UNKNOWN_ACCEPTED` + `USER_ACCEPTS_UNKNOWN_PRICE_NOT_INCLUDED`（`backend/app/services.py:605` 与 `:606`），且权威判据本来就读这套策略（`backend/app/services.py:771`）；通用编排那条路在 `backend/app/services.py:2315` **自动**写这个状态，前端也有对应的旅客勾选（`frontend/src/trial/mobile/MobilePlanWorkbench.tsx:304`「未核实的门票费用，稍后确认」）。
- 差别在于：草案这条路写的是 `PROVISIONAL_UNRESOLVED_FACTS`（`backend/app/agent/goal_preparation.py:221`），而 `backend/app/services.py:783` 那一支**不看** cost_unknown_mode，于是同一件旅客声明在一条路上管用、在另一条路上没用。
- 请点名（甲／乙）：甲＝让勾选也走草案这条路，把 `COST_UNKNOWN_ACCEPTED` 那套既有策略带进 `prepare-plan` 的落库（只覆盖票价，营业时间与跳仍按原规则，和 `backend/app/services.py:779` 的注释一致）；乙＝要求票价必须有来源（那就意味着再接一条来源，今晚没有任何已接来源能答它）。

## 门三 · 冻结的移动证据：这条路径在契约上就承诺"不冻"

- 选用门口现读：`backend/app/main.py:18120` 在候选的 `mobility_evidence_json` 没有 `snapshot_id` 时直接 409「STALE_RECOMPOSE_REQUIRED: PlanVersion has no frozen provider evidence」。
- 草案门的自述：`backend/app/agent/goal_preparation.py:76` 把响应里的 `mobility_frozen` 声明成字面 `False`（契约同代位置 `contracts/openapi.yaml:2708` 与 `frontend/src/generated/api.ts:3709`），也就是说**没有任何 UI 点击**能在这条路上让候选拿到快照。屏上现在如实写着「这份候选里没有冻结的步行时间。」（`frontend/src/trial/mobile/departureGaps.ts`）。
- 已有材料是真的：Agent 存下的步行跳带 provider、距离、时长、抓取时间与公开链接（`backend/app/agent/goal_amap.py:206` 到 `:211`）。适配器已写出来放在 `backend/app/agent/goal_mobility.py`（实现既有取数口 `backend/app/integrations/mobility/snapshot_capture.py:95` 要的 estimator 协议；量不到的跳抛错，让整次捕获 fail-closed，绝不用 mock 值洗成硬事实）。**没有接线**，因为接线要同时改响应契约与 `contracts/openapi.yaml`＋生成的前端类型，那是跨车道热文件的语义改动，不该由我一人替权威落。
- 附带一道要裁的语义：选用时可行性门把**每一对相邻活动**都当一跳检查，包括隔夜那对（`backend/app/replanning/feasibility.py:973` 到 `:980`，失败码 `INSUFFICIENT_TRAVEL_GAP`）。Agent 的路线工具只会步行量法，隔夜两站之间的"步行时长"在真实行程里没有意义。要么按日切段（同日才查），要么让这跳由别的模式量。这条与门三一起裁。
- 现读的分母：走通的那几趟里，同一天相邻跳数为 5（`trial/results/20261022_v3_human_chrome/research-routes-in-walked-journey-1.txt`），Agent 当时量到 4 跳；册廿三日十一分的另一趟（`trial/results/20261022_v3_human_chrome/walk-57-log.txt:28`）里待办还写着 4 段「转场路线：让 Agent 量这一段路」，说明这一趟模型没去量。

## 门三 · 已在这一棒接上（册廿三日廿一点十六分之后）

第 1 棒落地：`backend/app/agent/goal_route_freeze.py` 把「这份候选当天真正会走的相邻两站」列出来，能用上的高德回执就复用（`REUSED_PROVIDER_RECEIPT`），没有的就用同一个客户端、同一个回执写入器当场再量一次（`MEASURED_NOW`），任何一跳量不到就整批不冻（`ROUTE_UNAVAILABLE`＋fail-closed）。冻结走的是产品既有的那台机器 `backend/app/integrations/mobility/snapshot_capture.py:95`，不新建第二套路线真相。

屏上真实点击读数：`trial/results/20261022_v3_human_chrome/walk-61-log.txt:31` 是「当天的转场还没有向高德核实过。」，同一处按钮点下去之后 `walk-61-log.txt:32` 变成「转场已核实 3/3 · 已冻结进这版方案」。库里回读 `trial/results/20261022_v3_human_chrome/route-freeze-readback-1.txt`：`:2` 候选已有 snapshot id 且 `STALE False`（同一条判据在接上之前恒说"没有冻结证据"），`:3` 三条事实 degraded False、来源 amap_walking、`fact_quality=LIVE_PROVIDER_CAPTURE`、`time_basis=PROVIDER_CAPTURED_AT`，`:8` 四张高德回执都是 http 200 的真测距（663 m、4133 m、1333 m、3385 m）。冻结成功后那几行「转场路线」的待办会一起消失，身份/营业/票价的缺口留着——钉在 `backend/tests/test_goal_route_freeze.py`。

仍然没有骗人的地方：选用按钮还是 0（`walk-61-log.txt:34`），因为服务端权威还指着票价与那处没有身份的地点；几何也没有（研究步存下来的回执本就裁掉了 geometry，两点连线不是道路，不补）。

## 门三之前 · 一条当时的实测事实（保留，说明为什么必须接）

只读取器把刚保存的三份草案候选逐条过产品自己的判据（`backend/app/services.py:573` 起的 `_plan_staleness` 与 `plan_authority_blocker`），现读结果：三份全都 `stale=True`，原因是
`STALE_RECOMPOSE_REQUIRED: no frozen provider evidence`（这句话在 `backend/app/services.py:584`），
`mobility_snapshot=None`，`blocker=UNRESOLVED_ACTIVITY_FACTS`，`active_plan_version_id` 为 None。

这条读数是修屏上句子的依据：草案候选从写下那一刻起就没有冻结证据，因此它不是"过期"，把屏上那句改成
「地点信息有更新，请重新生成方案。」会把真人支到错误的门上——让人去重新生成一份同样没有证据的候选。
屏上现在按载荷本身说话：只有真带着 `mobility_snapshot_id` 又标记为过期的方案才说"重新生成"，其余说清缺哪几项、并补一句「这份候选里没有冻结的步行时间。」
（`frontend/src/trial/mobile/MobilePlanWorkbench.tsx` 与 `frontend/src/trial/mobile/departureGaps.ts`）。

同一件事也说明门三与门二其实是同一道门的两半：证据齐了才谈得上"过期"，而证据的来源（Agent 量过的跳、可核的票价）现在一个都没有接线。

## 屏上现在能做到哪一步（三趟真机走查的同代读数）

| 步骤 | 屏上文字 | 出处 |
| --- | --- | --- |
| 一句诉求 → 草案 | 「已保存 6 项正式安排。下方可以查看日程和出发待办。」 | `trial/results/20261022_v3_human_chrome/walk-57-log.txt:27` |
| 出发待办 | 每行写「缺什么 · 找谁要」 | `trial/results/20261022_v3_human_chrome/walk-57-log.txt:28` |
| 方案屏 | 「这版方案还缺：票价、转场路线。出发待办逐处写着找谁要。」 | `trial/results/20261022_v3_human_chrome/walk-57-log.txt:30` |
| 选用按钮 | 一次都没出现（SELECT_BUTTONS 0） | `trial/results/20261022_v3_human_chrome/walk-55-log.txt:34`、`walk-57-log.txt:31` |

结论：一句话到"正式候选方案"已经是真人可走通的；**候选到出发**这两道门（票价策略与冻结证据）需要上面甲／乙的点名，加上一次跨契约的施工。我不把这两道门说成已开，也不靠改断言让屏上出现按钮。


## 第 1、2 棒施工后：同一趟真人旅行已经走到 ACTIVE（2026-10-23 05:10 现场读数）

产品 SHA：`17857bb115af8b7330ae7cb5a61744967ba9e07b`（第 2 棒＋两处链形缺陷）与
`1b87caf27a2035fbdc43323e6206b35958c35bd7`（来源状态与契约文件）。隔离栈 r9：后端 60196、前端 14396、
独立库 `citynexus_v3_human11_1022.db`；走查日志 `trial/results/20261022_v3_human_chrome/walk-62-log.txt`，
逐帧截图前缀 `walk62-*.png`，屏幕之外的持久化回读
`trial/results/20261022_v3_human_chrome/walk62-departure-readback-1.txt`。

真人从首页输入一句话开始，屏幕逐字读到的（不是接口造出来的）：

| 门 | 屏上文字 | 出处 |
| --- | --- | --- |
| 保存候选 | 「已保存 4 项正式安排。下方可以查看日程和出发待办。」 | walk-62-log.txt:28 |
| 转场核实前 | 「当天的转场还没有向高德核实过。」＋按钮「核实并冻结今天的转场」 | walk-62-log.txt:31 |
| 转场核实后 | 「转场已核实 3/3（其中 1 段是跨夜衔接） · 已冻结进这版方案」 | walk-62-log.txt:32 |
| 票价未知 | 「还没有来源给过确定的费用；另有 4 处门票没有来源，预算里没有把它们算作 0 元，实际花费可能超出预算。」 | walk-62-log.txt:34 |
| 本人确认后 | 「按你的确认保存：这 4 处门票仍未核实，没有已核实的费用，出发前请自己留意现场票价。」 | walk-62-log.txt:36 |
| 选用 | 按钮「选用这份方案」第一次真的出现并被点下（SELECT_BUTTONS=1 VISIBLE=true） | walk-62-log.txt:39 |
| 选用后 | 「可以确认出发」「方案 1 已选用」＋按钮「确认方案，开始行程」 | walk-62-log.txt:41 |
| 出发后 | 「旅程已开始」，刷新后仍是「旅程已开始 · 方案 1 正在使用」 | walk-62-log.txt:44、:46 |

库里同一代读回来的（只读探针，不改一个字节）：journey `014bc3ff-86c4-4254-a343-e4046d06c3f1` 状态
ACTIVE、active_plan `87211ad3-3194-46c5-b9ed-92b250effc1f`；这版方案 snapshot
`63410f5c-8241-4ecf-910d-84d143d0a0eb`，authority_state `COST_UNKNOWN_ACCEPTED` 配
`USER_ACCEPTS_UNKNOWN_PRICE_NOT_INCLUDED`，cost_summary 里 unknown_count 四、
unknown_cost_included=False、total_is_not_free=True、known_subtotal 零；三条冻结事实全部
`LIVE_PROVIDER_CAPTURE` ＋ `PROVIDER_CAPTURED_AT`（20、44、230 分钟）；高德 ProviderCall 共十二条
（district 一、search 八、walking 三）；幂等键 goal.prepare／goal.freeze-routes／goal.price-accept 各一；
审计 goal.draft.prepared、goal.routes.frozen、goal.price.unknown.accepted、plan.selected、
plan.committed_by_traveler、journey.started 各一。

那 230 分钟值得说清楚：它是高德对「前一天最后一站→第二天第一站」给的**真实步行回执**，不是编的数；
正因为跨夜不会有人这样走，屏上才单独标「其中 1 段是跨夜衔接」，而不是把它混进当天转场。
下一步该给它多模式来源（地铁／打车），这是 P1 第 1 项，不是把这条事实藏起来。

## 还没开、也没说成开了的门

- 营业时间按出发日期核实（第 3 棒）：这次四站的营业事实仍未核实，屏上「出发待办」逐行写着找谁要；
  这版方案能选用的原因不是营业已确定，而是它的四站都绑到了正式地点行、且已核实的部分不为未知背书。
- 刷新后的**凭证过期与重新登录找回**：本轮只做到「同一登录状态下刷新保留」，P1 那条真入口仍未通过。
- `journeys` 表根本没有同行人数这一列（探针读到 no such column: party_size），所以「同行决策」那块牌子
  底下要挂什么，仍然等甲／乙点名，不能靠前端猜。
- 契约文件 `contracts/openapi.yaml` 现在收了 accept-unknown-price 这道门；同一份文件里 prepare-plan 与
  freeze-routes 两段还没写上新字段（unrouted_count、known_subtotal_minor、overnight、spans_night），
  这条对表尺 `tests/test_contract.py::test_openapi_runtime_method_parity_includes_v7_surface` 在本枝
  仍因 `_IncludedRouter` 红着（backend/tests/test_contract.py:73），我没为了让它绿而改断言。

## 第 3 棒之后：上面四条里有一条动了，两条没动，一条是我自己写坏的（2026-10-23 05:55 现场读数）

第一条（营业时间按出发日期核实）已开：`backend/app/agent/goal_opening_date.py` 把来源原句按子句读，
对着旅客真正到的那一天和到站那一刻给四档结论，屏上逐行写「来源写这天开放（来源写的时段 08:30—16:30）」
或「来源说这天闭馆；来源另写「以官方通知为准」 来源原文：…」，待办里跟着给可点的出口
（「让 Agent 换一天或换一处」／「让 Agent 挪个时间」／「让 Agent 向来源再要这一项」）。
现场两趟同一批地点、只差出发日：周一那趟（walk-63）故宫按来源判闭馆、并列出待办；周四那趟（walk-65）
六处全部 OPEN、当天是否开放这一类待办 0 条。逐格读数与两侧对拍表在
`trial/results/20261022_v3_human_chrome/opening-reader-ab-1.txt`，屏上原文行号在
`walk-63-log.txt:30` 与 `walk-65-log.txt:29`。产品代 `fea251f323ec90d81cfbde47908140267a9fa567`。

第四条（契约）里"我自己写坏的"那一半也修了：accept-unknown-price 当时被带上了多一层 `/api/v1` 前缀、
并且把 schema 内联进去，而这份文档的形制是相对 `servers: http://localhost:8000/api/v1` 写路径、用
`#/components/schemas` 引 schema——那样一条永远对不上真路由。`f57b6ab6f829a2ac2b16daeee9878fbcb2367468`
把三扇门重写成同形制，并补上 `unrouted_count`、`known_subtotal_minor`、`opening_checks`、`overnight`、
`spans_night` 与 OpeningCheck／RouteEdge／FreezeRoutesResult／UnknownPrice 三组模型；改后实测：
三扇门各自只文档化运行时真提供的那一个 POST，文档里存在而运行时没有的键为 0。
`test_contract.py:73` 那枚 `_IncludedRouter` 的红照旧不动，它是仓库里既有的事，不在这笔的授权面里。

没动的两条还是没动：真机由主人亲手点（USER_VERIFIED 仍 PENDING）；「同行决策」牌子底下依旧没有门
（`journeys` 表仍无同行人数这一列）。这两条要的是裁语与手，不是我再写一层代码。

## 补一笔：第五扇门（问 Agent 这一按）现在是真的了（walk-72，2026-10-23 07:29 现场读数）

上面"这一版还需要把待办逐项补完才能选用"那一步，屏上给了两枚出口：票价确认、以及「和 Agent 补齐出发资料」。
后者原先只发一句通用话术（要 Agent 复述清单并"先不要改行程"），量到 walk-66 才发现它按下去什么都不发生；
现在它按服务端的缺口逐条发问，并且明说要旅客自己再按一次「发送 ↑」（对话框要旅客本人的模型同意才发，
不能由按钮代签）。读数与逐条行号在 `20261022_V3_CHROME_USE_HUMAN_WALKTHROUGH.md` 第二十节。

顺带两笔与这道门直接相关的修正：Agent 那一轮的超时天花板从 90 秒提到 180 秒（同一句问话四次只答一次，
其中一次实际用了 106 秒）；答不上来时对话框现在会写「Agent 上一轮没有答完，这次的服务暂时不可用」，
不再用消失的那行状态把失败显示成"还在想"。

walk-72 里这趟最终走到「旅程已开始」，刷新后仍是 ACTIVE；库里对账在
`20261022_v3_human_chrome/departure-loop-readback-1.txt`。要说清楚：这次让选用门打开的是 Agent 在按按钮
**之前**完成的地点绑定与 5/5 冻结，按钮那一句答回来之后草案没有再改版——所以这一按被证成"问得出、答得上"，
没有被我说成"是它补齐的"。
