# ORD-0274 B2c + B2b · 换代安全点的运行时读数（全部由脚本派生）

写者：B `c01d72a3`　日期：2026-09-25 05:49+08
候选尖：`853c54944a0b7ea2c7111867915566171650c564`（分支 `review/0274-b2c-b`，父 `1de4c250746c…`，要求基线 `dcae1bc96412…`，is-ancestor rc=0）
GitHub 回读：`853c54944a0b7ea2c7111867915566171650c564	refs/heads/review/0274-b2c-b`

## ① 顺序 1：换代判定改成字节判定（不再用 index 成员/文件名）

尺：`live_checks/deploy_bundle_v2_draft_r4.py` blob `0686670743c0…`
本件不复制判定逻辑，用 AST 从那份已核对摘要的副本里抽出 `strip_js_comments` / `sw_register_verdict` /
`_ord0277_generation_verdict` / `asset_refs` 执行（导入时重算 blob，不符即退出）。

尺自证：`15/15` 臂 MET
（F3 改名不动字节 ⇒ 不算换代；F4 同名不同字节 ⇒ 算换代；F5-F7 注册参数在代码里才算、注释里的好看话不算；
F8/F9/F10 零注册红、沉默分块不连坐、读不到的注册红；F11 拒绝红代当宿主；F12/F13 执行字节与被解析字节必须同摘要）

**先抓到自己上一版的空臂**：上一次 0274-SW 交付用的两代（`dist_0274sw` / `dist_0274sw_gen2`）
`content_fingerprint` **相同** —— 那枚"换代"是改名买的。现换成真语句构建的 stand-in 代。

committed 两代（`{"candidate_from_committed": "/assets/index-BhbHloNw.js", "gen2b": "/assets/index-CEGoPIGb.js"}`）：
逐代的 entry sha256 / content_fingerprint / 注册判定见 §⑤ 件。

## ② 顺序 2：B2c 运行时读数 + 两枚反控（源站真的把写扣住 N 秒）

仪器：源站对非 GET/HEAD 请求睡 `post_delay_s=10` 秒再答，
并暴露 `/__admin/inflight`；探针等到"确实有一枚写在飞"才换代。写被腰斩的判据在**源站侧**：
答写不出去就记 `delivered=False`（客户端 reload ⇒ ConnectionAbortedError）。

| 臂 | 判定 | 期望 | 写在飞@换代 | delivered / undelivered | pending 标记 | 文档 loads | 结束时执行字节 == 新代 |
|---|---|---|---|---|---|---|---|
| candidate | MET | MET | 1 | 4/0 | True | 2 | True |
| counter_eager | RED | RED | 1 | 3/1 | False | 2 | True |
| counter_manual | RED | RED | 1 | 4/0 | True | 1 | False |
| idle_control | MET | MET | 0 | 0/0 | False | 2 | True |

重复性：第二批 `{"candidate": "MET", "counter_eager": "RED", "counter_manual": "RED", "idle_control": "MET"}`；
第一批在判定修正后重判 `{"candidate": "MET", "counter_eager": "RED", "counter_manual": "RED", "idle_control": "MET"}`，
判定翻动只有一处且记录在件里：`{"idle_control": {"was": "RED", "now": "MET"}}`

## ③ 顺序 3：B2b 逐值 + 两枚反控，以及它先抓到的、是我上一版自己的漏

先红：第一臂跑在**未含本轮修复**的候选上，读出来是"文档根本没换代"——一个在自身生命周期内被 claim 的文档，
`controllerBefore` 在注册时读到 null，之后每枚换代都被同一句 return 挡掉（loads=1、
controllerchange=2 次、换代后仍执行 `/assets/index-zCtIwAVy.js`）。
本轮把"上一次看到的 controller 身份"改成跨事件跟踪，只排除"这台文档第一次被控制"那一枚。

反件必须是**换代目标**（恢复代码是进来的那一代），不是客户端：
`{"dist_0274b2b_steponly_t": "shape_ok", "dist_0274b2b_stepforced_t": "shape_ok"}`

| 臂 | 判定 | 期望 | step 屏幕 | step 存储 | 逐值全等 | draft 还在 | bundle 老→新(字节) |
|---|---|---|---|---|---|---|---|
| candidate | MET | MET | trial-step2-body→trial-step2-body | 2 | True | True | True |
| counter_step_only | RED | RED | trial-step2-body→trial-step2-body | 2 | False | True | True |
| counter_step_forced | RED | RED | trial-step2-body→trial-step1-body | 1 | False | True | True |

逐值明细（candidate 臂，字段在它自己那一屏读，两边都读）：
`{"city": ["厦门", "厦门", "厦门"], "startAt": ["2026-10-05T08:30", "2026-10-05T08:30", "2026-10-05T08:30"], "endAt": ["2026-10-09T19:45", "2026-10-09T19:45", "2026-10-09T19:45"], "partySize": ["4", "4", 4], "budget": ["4321", "4321", 4321], "specialRequirements": ["需要无障碍通道 · B2b", "需要无障碍通道 · B2b", "需要无障碍通道 · B2b"]}`

第二批（v4）：`{"candidate": "MET", "counter_step_only": "RED", "counter_step_forced": "RED"}`

## ④ 回归（本地等价，HJ-P1 的真链格我不签）

`true` = B3 等价臂在**一次**导航内跨两代字节收敛；
A 等价臂离线仍用自己那一代（`same_generation_while_offline=true`）。

## ⑤ 我自己本轮 disclosed 的仪器缺陷（原物留在盘上，被取代但不删）

- measured the first B2c candidate arm against a STALE dist (built before the B2c commit) and it read RED; that reading is superseded, not averaged, and the dist was rebuilt from the committed tree
- my B2c judge counted a sample taken while the page was reloading as 'the probe navigated again', which turned a clean MET into RED; corrected, and the re-judge records the one verdict flip it caused
- my first B2b counter-arms were built as CLIENTS; the restoring code is the INCOMING generation, so both read MET vacuously; rebuilt as targets and each arm's shipped bytes are now checked against its declaration
- that rebuild also exposed a compound cut: the builder re-read the already-patched source inside the loop, so 'stepforced' carried 'steponly' too; both arms returning identical readings is how I caught it
- my own regex reported '0 precache entries' for the served worker; that was a parser failure, so the count now comes from the ruler's own precache_urls
- the earlier 0274-SW delivery's generation pair was a rename (equal content_fingerprint) - found by the Q20 judge, not by its author

## ⑥ 边界与不自签

改动文件：`frontend/src/api/citynexus.ts, frontend/src/app/V8Experience.tsx, frontend/src/lib/inFlightWrites.ts, frontend/src/main.tsx`；diffstat `4 files changed, 116 insertions(+), 9 deletions(-)`；
precache 结构 / 0268 那一刀 / clientsClaim·skipWaiting / 运行期路由 0 触碰；后端与业务逻辑 0 文件。
`derived_result` 不签：B2/B2b/B2c/B3/A 归 HJ-P1 的仪器。
