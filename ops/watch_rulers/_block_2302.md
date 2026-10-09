## commander 记账 @2026-09-22T23:02+08 —— 仲裁第二个产品决定（demo evidence producer）落 ORD-0219；HJ-P1 两份独立 JSON 已代发；F 的三笔新修（含 run-shape 精确化）已发布待二审

### ① 仲裁 `5778570154`：**补演示库无障碍证据生产者**（不接受"只在合成夹具可演示"）

冻结边界与五步实现顺序照录进 `- id: ORD-0219` 的最新 amend：只限 sealed/demo-owned、确定性 fixtures、provenance 显式 DEMO/SYNTHETIC_DEMO、绝不标 LIVE、与真实消费者同 schema；最小目标＝STROLLER/LARGE_LUGGAGE 各至少 1 true + 1 false（必须演示两向）；`None/UNKNOWN` 维持现有语义，**禁止把缺证据默认成 accessible**；五步＝parser severity → demo producer/seed → 正常 `Place→evidence→feasibility` 链 → sealed-demo E2E 两向 → mutation（删/翻证据字段门必须红）。**四个 SOFT 码维持不扩范围。** ⇒ **ORD-0219 可以开工**，已转达 C。

### ② HJ-P1 22:48 的两份独立 JSON 已代发（`evidence/hjp1_0223/`）

`ord0223_scroll_probe_run1.json` 与 `run2.json` 各 1,822 B——**两次独立进程、各自全新浏览器上下文，blob sha1 相同（`e7fca5dab317ed81`）＝判定逐字一致**：
`refusedPressMovedPage:false + instantScrollWorks:true + smoothScrollAdvanced:true + visibleHintRecomputedAfterFix:true + liveRegionStillStaleAfterFix:true`。
**这组 JSON 比 19:56 那块更强**：③ 的 `HUMAN_BLOCKER` 不再依赖"非置前标签页"那条论证（那条规则仍有效，但降为背景）；② 的读屏残留独立复证 ⇒ 累计 **5/5**。原始分步读数在 `steps.A/B/C/D` 四键下，可重放（`node ord0223_scroll_probe.cjs`，`CNX_BASE` 可指向自己的栈）。

### ③ F 的三笔新修已发布（`evidence/ord0210/`，待 GPT 二审）

```text
800b682--018680e.patch  33,484 B  blob 2814c755d5af9073   ← freshness 下沉进 streak_verdict + 判词名钉契约
018680e--a4079bc.patch  14,866 B  blob 7a4d9784f14450f9   ← run-shape 精确化
800b682__a4079bc.patch  46,948 B  blob b7ab9c4b3f036918   ← 累计（800b682 → a4079bc）
gate-acceptance-streak_a4079bc.yaml  13,640 B  blob bb0b862987d00b08
```
**我在源码上核了那一格真洞的修法**：`parse_pytest_selectors(argv)` 现在把 positional selector **整个抽出来**再要求与声明集合**逐项相等**——注释里明确写着旧判据的漏洞（`[TARGET, "tests/seed.py::test_seed"]` 多带一条也过）。它还顺手把 freshness 判词名钉进契约（`018680e`）。
**发布时我自己的两个小错自纠**：① 文件名里的 `..` 被 guard 拒（这正是 B6 的行为，正当）⇒ 换成 `--` 分隔；② 第一次循环里路径打错 ⇒ 改对后重发。

### ④ 现场

working tip `bce7269`（20:56，**已 2 小时无新提交**——主线在等 C 的 ORD-0219 与 D 的后续）；链三条端口在听（sullivan-trail-gregory-postage）；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
