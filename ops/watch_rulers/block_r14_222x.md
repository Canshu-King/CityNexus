### SESSION=494abfd7 · **R14「因果归因真值」正式立项**（仲裁 `5761941748` ③，由我 22:1x 提的统一口径升为常设规则）——四条在跑的单改挂 R14 验收 @本机钟 22:2x

`STATUS: R14-BROADCAST | 仲裁原文：Issue#1 comment 5761941748（22:15，我 22:25 拉全）| 冻结句见下 | 本块是转录+归属，不新增判据 |`

**R14 冻结句**：
> **产品已经拿到了能区分真实原因的证据，却在另一层把它改写成了一个更方便的假原因。**

⇒ 从此**不再按"一个红测试一个 bug"数人头，也不再按"一个 catch 一个文案"修界面**（仲裁原话：前者把同一个环境根因拆成九个鬼，后者让同一种假原因在下一页重新投胎）。
这正好解释我今天量到的三件事：① 我 21:0x 报的"5 类端点各自 500"其实是一个缺兜底的根因；② F 的 24/17/14 三个数不是吵架，是树与过滤口径不同；③ ORD-0169 不是前端补丁，是 R14 的一条 gate。

**R14 的 8 条必备门 → 归属（谁交哪条）**
| # | 门 | 归属单 | owner |
|---|---|---|---|
| 1 | 1600 CNY 全链不变 | ORD-0158 | C `8c66aa92` |
| 2 | missing/uncertain budget 不得变 0 | ORD-0158 | C |
| 3 | DB lock 有具名 runtime class | ORD-0112 | C |
| 4 | valid empty reset 不得 500（`200/204 + deleted_demo_rows=0`） | ORD-0125 | C |
| 5 | stale journey 404 ⇒ 清失效 id + recovery + **地图/正常 shell 恢复** | ORD-0169 | D `e345b9d6` |
| 6 | 真 transport failure 仍是 OFFLINE，**不许因修 404 被误判成 JOURNEY_NOT_FOUND** | ORD-0169 | D |
| 7 | server 5xx 是 SERVER/RUNTIME，不是 OFFLINE | ORD-0169 | D |
| 8 | banner + `aria-live` + telemetry + recovery action **同一个 machine reason** | ORD-0169 / ORD-0130 族 | D（F 出门） |

**六条必杀突变**（谁的红字要写进交付）：`404→OFFLINE`、`真 transport failure→JOURNEY_NOT_FOUND`、`unknown budget→0`、`empty reset→500`、`具名 DB contention→无结构 500`、`UI 宽 catch 绕过 structured reason`。
⇒ 与我 22:2x 退回 F 的那条**同一味药**：我实测把"缺证据当可达"装进 `evaluate_accessibility_requirement`，因为 `d5/d6` 本来就红，**杀没杀看不出来** ⇒ R14 之后统一要求：**突变必须让一条原本绿的门变红**，并给 `文件:行 + 绿 nodeid + 变红原文`。

**仲裁还替我堵了一个我差点踩的坑**（关于我那条 404→离线的读数）：
`navigator.onLine=true` 本身**不是**可靠的全局联网证明；但**同源请求真返回 HTTP 404** 已足以否定"这个请求没有网络响应"，再加 `/demo/scene → 200` 才把"全局不可用"这块 banner 证成过宽。
⇒ 我 21:56 那条结论成立，但**证成方式要按这个次序写**（onLine 只是旁证，404+200 才是主证）。已按此更正我给 D 的口径。

**当前冻结（照抄仲裁 ⑤，各单验收以此为准）**
```
Test baseline@366cba6 = 17          Network-isolation remediation = ORD-0170 ⇒ 量 17 -> N
Pending identity = ORD-0167         Hermes owner = 9baacb24
Stale journey false-offline = ORD-0169 under R14-S/P
Causal attribution invariant = R14  Preview backend unchanged（:8693 仍 53fe8e8）
:4782 PREVIEW_GUARDED remains       Codex = read-only black-box verifier
```
另：`docs/test_execution_truth_policy.md` 已因我补的 archive 例外更新 → 新 commit **`54a4bcaa2d98b7e8e77724b43ae4d221bb5de47a`**；
**lane C/F 不再需要为"拉不到契约文档"停工**（两份都可达，我已字节校验并落到 `_qoder_cmdr_ref_20260921/arbiter_docs/`）。
还有一句对我自己的：仲裁明确"不要为了让 9 条一起绿去放宽业务断言——这次修的是 test environment isolation，不是降低 product truth gate"，这句我转给 F 并已在其 ORD-0170 里成文。

status: R14 立项转录 + 8 门 6 突变归属表 + 我那条 404 读数的证成次序更正
evidence: 总线 `5761941748`（22:15）· 本地 `live_checks/set17.txt`、`tree_f156` 突变试验、`arbiter_docs/` 两份契约
