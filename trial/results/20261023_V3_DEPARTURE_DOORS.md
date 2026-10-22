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
