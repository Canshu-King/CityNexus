# 交付件：QODER_GO_FROM_BLANK_AND_AGENT_VISIBILITY 三刀（2026-10-27 01:08 本地 / 17:08Z 起算的同一夜）

权威枝 `rescue/v3-final-departure-20261022`，本件对应尖 **3ad2f482ff5868c396371ed6d1fa8e5d83c059bb**
（本地与 `git ls-remote` 逐字相同；这枚是把远端新增的 19 笔——含 PR #56 `4dfeac260b` 与 CI 门禁 `575318cbf1`——
经 `git merge-tree --write-tree` 只读预测零冲突之后 merge 进来的合并代；没有 force-push，没有 rebase 已发布枝）。
合并代上门禁三条腿本地重放全绿：后端聚焦选择集 **213 passed**、`npx tsc -p tsconfig.check.json --noEmit` RC=0、
`npm run build` RC=0（收据 `trial/results/20261026_gozero/ci-gate-merged-r72.txt`；§66 记了 Actions 上为何没有这一代的运行）。
其后又落了两枚产品刀：`e5fdc2734e`（§64，已保存过的草案卡仍允许「按以上时间重新准备方案」，并在重存时换新幂等键）、
`d1b016040e`/`739b4162e8`（W 臂派生器与 §65 读数）。明细在 `trial/results/20261026_GO_FROM_BLANK_REPORT.md` §47–§66。

## 1. PRODUCT_SHA（本夜落线的产品字节，逐笔可取回）

| 提交 | 改的文件 | 那一格 |
| --- | --- | --- |
| `ab2ca5913a` | `backend/app/planning/travel_brief.py` + 新测试 | 已接受方案的站要能上图（第二臂 + 署名/CRS 分家） |
| `f2f65020b9` | `frontend/src/trial/mobile/MissionCockpit.tsx` | 日程与计划点跨两套 place-id 命名空间对齐 |
| `0188ebd5f4` | `frontend/src/trial/mobile/MobilePlanWorkbench.tsx:70` `:376` | 选用门拒绝那一屏，原因句下面给可按的一枚 |
| `c160a9cea3` | `frontend/src/trial/mobile/DraftDepartureCard.tsx:141` | `PLACE_NOT_IN_GOAL_TASK_SCOPE` 不再谎称「可以重试」 |
| `89dbbe22c1` | （撤回）| 我自己基于 500 字截断造的冗余分支，已撤 |
| `12609ae5e3` | `frontend/src/trial/mobile/DraftDepartureCard.tsx:343` 前 | 只有拒绝句、没有可挪行时那一块里一颗键都不剩 → 补「重新核实这几段」 |

同代回归：`npx tsc -p tsconfig.check.json --noEmit` RC=0；`e2e/revolution-draft-preparation.spec.ts`
3 passed (13.9s)；后端聚焦 **86 passed**（47+39），宽面 129 条里 15 枚红经父代对照臂证明早于本刀（§58）。

## 2. USER_CLICK_PATH（真实 Chrome，无假 DOM、无 API 代按、无 localStorage 预置）

冷首屏 → 输入那句两天两人步行 1 公里的话 → 「继续规划」→「对话」→ ⚙ 勾两项许可 → 发送 →
研究 → 「跳过/回答」→ 草案卡 → 「保存为正式候选方案」→「票价没有来源，我接受先不计入预算」→
「核实并冻结今天的转场」→「刷新方案」→「选用这份方案」→ **「确认方案，开始行程」**
（`HIT start-fallback-… true`，走的是中心命中测试）→ 出发。

## 3. 同号收据（journey / task / candidate / plan / ACTIVE 同一趟）

| 形状 | journey_id | task_id | plan_version_id | 出发读数 |
| --- | --- | --- | --- | --- |
| 390×844 | `5180b857-e1d2-47fb-b31c-f5b86023247a` | `214f5e61-8f82-4c4d-bd8d-ef503d125ee6` | `10cf2ebb-8837-456e-8e42-e3acf259a426` | `departure/commit 200` → `start 200`，屏上「行程执行中」 |
| 430×932 | `a87c821b-8eec-418b-8ccf-0888d5581cdd` | `8ac475d1-d48f-4fa0-958d-ce7d952ec4b0` | （同屏 `5 项/8 项` 见收据） | `start 200` 同上 |
| 漂移腿 390 | `0ff63e58-53d5-41a7-812c-5920c16d031a` | `f495676e-c976-4b85-a7ef-a1bf91f2e587` | `ccd05664-e21a-483d-b4f7-226094e9424f` | 出发门被我自己那一改挡住（见第 6 项） |

收据文件：`trial/results/20261026_gozero/go-active-390-r57.txt`、`go-active-430-r57.txt`、
`drift-check-390-r62.txt`、`plan-open-hand-390-r53.txt`、`go-active-390-r55.txt`、`drift-check-390-r61.txt`。
令牌一律不落文件（bearer 只在浏览器 sessionStorage，屏证里没有 Authorization 串）。

## 4. 截图（本件提交时一并入库）

390：`390-g7-started-fallback.png`、`390-g8-map-preview.png`、`390-g8-map-loaded.png`、`390-g8-map-reloaded.png`
430：`430-g7-started-fallback.png`、`430-g8-map-preview.png`、`430-g8-map-loaded.png`、`430-g8-map-reloaded.png`、`430-r54-plan-blocked.png`
另 `390-r53-no-workbench.png`（身份丢失那一屏）已在库。

## 5. 真实工具调用状态与供应商来源

`/map-places` 现读响应（收据 `RELOAD_MAP_READS`）：`candidates:5`（390）/`candidates:8`（430），
每枚 `origin:"PLAN_ACTIVITY"`、`coordinate_system:"WGS84"`、`region_status:"MATCHED"`、
`selection_state:"READY_FOR_NATIVE_PLAN"`；`GCJ02` 在两枚收据里命中 0 次 ⇒ 没有原始高德坐标被画上 OSM。
署名分家：高德来源的点写 `© 高德地图（AMAP）` 且给「在高德地图打开 ↗」，OSM 来源给「查看地点来源 ↗」；
两档 `MAP_AMAP_LINKS` 与活动数一致（5/8）。

## 6. 失败与刷新路径（实测，不是设计意图）

- 刷新：两档都在 reload 后读到同样的 `N 处 / N 计划标 / N 列表项`（`RELOAD_*`）。
- 出发门拒绝：`departure/commit 422 … INSUFFICIENT_TRAVEL_GAP:real-place-00d9e27c…|real-place-62c2e606…`
  —— 成因是我把晚餐结束时间 20:00→20:30；屏上句点名该挪哪一边（`departureGaps.ts:346-348`），
  而我的臂没照做，改成把拒绝句发回 Agent，所以这一格只证到"门说得清"，未证到"旅客能自救回来"。
- 身份：关浏览器后 `TRIPS 行程` 给「这台设备上还留着「北京」这趟行程，这次打开没有登录到它，所以读不到进度」，
  旁边只有「课堂演示：进入示例行程开始探索 →」，没有"回到这趟行程"的门（#332，待裁）。
- 模型方差型阻塞：`prepare-plan 422 PLACE_NOT_IN_GOAL_TASK_SCOPE`（O 臂 13 拍）与 `409 prepare-plan`（H 臂）
  都真实出现过，新句已落线但**该屏未再见** ⇒ 标 NOT-STARTED。

## 7. KNOWN_BLOCKERS（照原样挂着，不粉饰）

1. `rev-plan-open-place-explore`（`0188ebd5f4`）与范围拒绝新句（`c160a9cea3`）的屏证 —— 要等各自阻塞形状
   在真机再现；不能预置。
2. 430 与 390 的 ACTIVE 读数取自「尖 + 三枚他人未提交的 `frontend/src/app/*`」工作树，同代性带此保留
   （§59），闭法见 #339。
3. 平板 `USER_VERIFIED=PENDING`：要主人真机走一遍，我不代按。
4. 课堂随机城市池仍 0/3；冻结公交事实 `route_geometry=[]` 那格未变。
5. 「和 Agent 补齐出发资料」之后，被拒的方案没有"应用这一版"的可达键（#336 的分辨仍未跑成）。
6. 15 枚后端红（`test_sol_concurrency_and_remap` 9／`test_qoder_live_replans_endpoint` 5／
   `test_dsh_list_replans_bound` 1）经同代对照臂证明早于本刀存在（§58），归属待裁。
