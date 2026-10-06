仲裁: SESSION=494abfd7（Commander）— 权威树合进了 B 的 typed outcomes（我复跑无破损）；canary 报出**今夜第一个可能的真 HYDRATABLE**，但**我没能复现运行时那一格——它已经停了**，所以那一格按你的协议留在 SELF_REPORTED

## ① 合并面（我复跑）
- tip `306f153` → **`520cf29`**（merge `agent/b-ord188-20260922`）
- `git archive 520cf29` 上跑 `provider_identity + pending_destination_identity + provider_identity_leg`：**49 passed / 0 failed**
- ⇒ 这是**新增证据层**进树，产品消费面仍未接线 ⇒ **`520cf29` 不改变 P7=false**

## ② canary：坐标真、测试真、**链未验**
- `git cat-file -t`：`53a21fc` / `e3f416f` / `08786c1` / `44e4ea7` 全部 commit ⇒ 可 checkout（我今夜反复要的东西，这次到位）
- `git archive 53a21fc` 上四套合跑：**53 passed / 0 failed**，`g19a/g19b/g19c` 三绿 ⇒ **测试面 REPRODUCED**
- 但它报的运行时链（`贡山县` ⇒ provider canonical `OSM:R:2729765` / `HYDRATABLE` ⇒ 202 durable ⇒ 6 live 行 ⇒ planner 422 ⇒ 逐边收据 ⇒ `MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE`）我去连 `:8596` 得到 **connection refused** ⇒ **运行时不升档**，已让车道重起 canary（自有端口+自有备份库，并确认不挂用户 preview/隧道/SW scope）并交 14 项逐边收据，**我自己 GET 一遍才升**
⇒ 你 ③ 那句我现在体会很深：**正因为这条最有新闻价值，它最不能用"跑过 39 个测试"来代替链**。

## ③ 我按你的协议做了两格拆分（晨报第 3/8/9 项）
`REPRODUCED(坐标/测试面)` 与 `SELF_REPORTED(运行时可见链)` 分列；第 5 项继续保持两格：
- 手机可见：`unresolved:8fccf2bbf123e3df` + `CHOOSE_ANOTHER_DESTINATION`（后端仍 `53fe8e8`，我对部署侧直接 GET）
- 树内已改：`canonical=null` + 独立 `pending_destination_label` 列（我在 `f2708dd` 复跑 19/19）

## ④ P0 与工具
- P0 全维持：主预览后端未动、`demo/reset → 403 PREVIEW_GUARDED`、匿名 `401`、用户 `3/19/3` + places 北京8/演示8 未变；canary 停机期间不存在"用户可达 canary"风险面，重启时我再量端口与库路径。
- 账本仍是 LF、锚点=1；镜像 `19b2e7223d14` 字节级相等；`ORD_0192_REPRODUCTION_PROTOCOL.md` 已按你 `cab91a25` 落本地并作为唯一验收口径（我不另发明一套）。
- 车道状态：C 在做 0197 行为收据（v2 口径）、B 重启 canary、D 已收 0193、F 已收仪器（我七组复跑）+ 待 R14 行为门承接；**Harness 与 P1–P4 继续睡**。

竭尽所能的替qoder铺路
