仲裁: SESSION=494abfd7（Commander）— 基线已经不再是一个数字（两个独立来源交集同为 14）；今晚第一个 REPRODUCED 已升档；**有一个夜里会真遇到的岔口请你先定，免得我到时猜**

## ① 基线合流完成（这条是你 ⑤"别拿计数当进步"的落地）
同一 SHA `8ee64ae`、各自建库、各自干净导出：
- 我三次全量：16 / 16 / **14** → 三遍交集 **14**
- lane F 两遍全量：17 / **14** → 两遍交集 **14**
⇒ **两个独立来源的交集相同 = 14，合并区间 14–17**；具名轮换成员只有 3 个，全在 `catalog_hydration` 一族。
⇒ 我们前几轮"16 还是 17"的争执就此定性：**不是谁读数错，是"报单值"这个说法错**。车道原话我引用进账本："真值是这个集合。"
⇒ 契约里已落成 `baseline-is-a-set-not-a-number`（含 worked example）+ `p5-targeted-only-until-the-stable-candidate`，我核过门文件行为与说法一致。

## ② 今晚第一个 `REPRODUCED`（三档标注真的在跑，不是口号）
lane F 交 ORD-0194 时**只给自己标 SELF_REPORTED**，写明"我不替任何一项写 REPRODUCED，那是你的标记"。我在 `2176774` 上 targeted 复跑：
`1163 collected` · 收集门文件 **9 passed** · 新立 `test_7`（负断言必须先在**真键清单**上算缺什么）绿 · 新立 `test_8`（**守卫必须单实现**，包装里出现锚点判定逻辑即红）绿。
⇒ 已升 `REPRODUCED`。**它的交叉突变仪器（`14a5b64`）我没复跑，继续挂 SELF_REPORTED**，明早的表里会照实写。
⇒ 顺带：`test_8` 也约束我——我的 `ledger_anchor_guard.py` 保持唯一实现，巡检脚本只调用不复制。这正好是我今晚两次"两份东西各修一半"担忧的机器版解法。

## ③ 请你先定这个岔口（我拒绝在夜里自己猜）
贡山 13 步链跑到第 11–12 步时，最可能撞的是**用于 SELECTABLE 的 mobility 证据是否 hard-eligible**：
现网事实是我们只有一个可达 router（Valhalla）、`cells≤100`、且**实时路由默认关**（要 `CITYNEXUS_LIVE_VALHALLA_URL` 才开），而用户主预览仍走 mock 冻结矩阵。
⇒ 岔口：若解析 + 目录都真、**唯独 used-edge 证据只能到 `EXPLICIT_FROZEN_FIXTURE`/`SYNTHETIC_DEFAULT`**，明早的里程碑算不算达成？
我的建议（等你一字）：
- **A（我倾向）**：算达成"**HYDRATABLE + 具名 gap**"这一档——链在 12 步**如实停在 `MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE`**，**不造 SELECTABLE**；主线记为"解析与目录真通、路由证据是确切缺口"。
- **B**：夜里在 **canary/自有库**上打开实时 Valhalla，把最后一步也跑真（代价：多一个变量、慢，而且违反"P0 不把主预览切实时"——只在自有 canary 上做可以合规）。
⇒ 若你选 A，我就把"SELECTABLE"从今晚必达改成**明早目标**，并把力气放在 B→C 交接与云和第二例；若你选 B，我只在自有端口/自有库做，**主预览一行不动**，且把 P95 额外延迟记进晨报。

## ④ 现场（P0 仍守住，01:0x 实测）
`POST /api/v1/demo/reset`（带凭据）→ **403 PREVIEW_GUARDED**；匿名隧道 → 401 / 1.4 s（链活、鉴权在前）；`GET /` → 200；
用户库只读 `journeys=3 / plan_versions=19 / travelers=3 / places 北京8+演示8` **未变**；后端未动，前端 `index-BkEHAbFb.js`；账本镜像 `2bfbff977bc7` 字节级相等（2,024,553 B）。
车道：B 与 C 在 ORD-0191/0192 主线上、D 在收尾+ORD-0193、F 待我复跑交叉突变、HERMES 并行（ORD-0190 欠清单重出）。

竭尽所能的替qoder铺路
