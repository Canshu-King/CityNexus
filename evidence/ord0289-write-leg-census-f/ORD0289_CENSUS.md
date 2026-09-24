# ORD-0289 · 写腿普查：换口径（AST）在两代各数一遍，并与两份既有读数逐条对表

lane F `8ccd71d8` · 2026-09-25T07:26:00+08:00

## 口径（先声明，便于别人复算）

```text
工具 = TypeScript 编译器 API（node + 仓库里的 typescript 包）解析 AST，不用正则定调用点：
  · 站点 = 被调对象是标识符 fetch 或成员 X.fetch 的 CallExpression；
  · method = 第二个实参对象里的 method，只认字符串字面量或同文件字符串常量；解析不出记 unresolved，不猜；
  · signal / timer 只看**同一个调用表达式**（AbortSignal.timeout / setTimeout 回调里 .abort），不借 700 字符窗口；
  · .d.ts 与 node_modules 排除；两代各一份，导出后先与 GitHub 递归树逐名对表（71/69 件全等，tree 未截断）。
```

## 表 2：按代汇总

```text
[landed_45b0a5e2]  提交 45b0a5e28…  文件 71 个 .ts/.tsx（与 GitHub 递归树逐名相等 = True）
   AST 站点 39｜写腿 14｜写腿带 signal 2｜写腿带计时器 0   ← 判据点名的承重三项
   其余分桶：选项里没有 method 的读腿 17｜完全无第二实参 8｜选项是变量(method 未知) 2｜分桶相加=总数 True
   同一批文件用有界正则 (?<![\w$])fetch\( 数 = 50（包工头申报的 fetch 数就是这样复现的：落地代 40、前一代 39）
   正则 + 700 字符窗口数写腿 = 17（他申报 17 的同一形状）

[earlier_dcae1bc9]  提交 dcae1bc96…  文件 69 个 .ts/.tsx（与 GitHub 递归树逐名相等 = True）
   AST 站点 38｜写腿 14｜写腿带 signal 2｜写腿带计时器 0   ← 判据点名的承重三项
   其余分桶：选项里没有 method 的读腿 16｜完全无第二实参 8｜选项是变量(method 未知) 2｜分桶相加=总数 True
   同一批文件用有界正则 (?<![\w$])fetch\( 数 = 49（包工头申报的 fetch 数就是这样复现的：落地代 40、前一代 39）
   正则 + 700 字符窗口数写腿 = 17（他申报 17 的同一形状）

```

## 表 3：与两份既有读数逐条归因（谁的数都不默认对，包括我的）

```text
A) 包工头 40/17/2/0（落地代）vs 我 39/14/2/0：
   站点差 1 处，具名：features/planning/PlanWithAiSheet.tsx:300 —— 那是注释 `/** fetch() rejects a cancelled re…` 里的字面量，
     不是调用点；除它以外两代每一处 (file,line) 都能对上（逐文件不等只有这一个文件：正则 8 / AST 7）。
   写腿差 3 处，全部是**窗口越界**（700 字符里捞到了同文件另一发的 method），逐处：
     features/inbox/JourneyInboxWorkbench.tsx:82  —— 该处 AST 站点里 method=null，它的第二个实参是 ['non-literal-expr']；同文件里真正带 POST 的行在 []
     features/recovery/V14RecoveryTruthPanel.tsx:55  —— 该处 AST 站点里 method=null，它的第二个实参是 ['absent']；同文件里真正带 POST 的行在 [69]
     features/stay/HotelsPanel.tsx:54  —— 该处 AST 站点里 method=null，它的第二个实参是 ['absent']；同文件里真正带 POST 的行在 [63, 64, 87]
   ⇒ 他那 17 里含 3 处读腿误判为写；承重两项不受影响（signal 2、timer 0 两口径同数），他自己也写了『17 偏宽』。

B) HJ-P3 33/13/2/0（前一代 dcae1bc9）vs 我 38/14/2/0：
   我把可能的范围口径逐个试了（全部/排除 test+mock/只 features/排除 app+i18n/只看带选项/只数裸 fetch/排除 components），
   没有任何一桶凑出 33 且 13（见 ord0289_hypotheses.json）；目录组合穷举（≤3 个前缀）也无精确命中 ⇒ 他们那两个数是
   另一棵树切片或另一份口径下的读数，我不指错、也不拿我的数覆盖它。
   能对齐的是承重那两项：写腿带 signal = 2、写腿带计时器 = 0 —— 四种口径 × 两代 × 三方人数，全一致。

C) 我自己口径的限界（先自己说）：落地代有 2 处第二实参是变量，method 无法从字面量判定：
     features/inbox/JourneyInboxWorkbench.tsx:82   lib/readDeadline.ts:44
   ⇒ 我的『写腿 14』是**下界**，若这两发都是写则上界 16；其中 readDeadline.ts 正是 ORD-0281 要动的文件，
   改之前请把那两处读一遍再定，不要按 14 直接下结论。

```

## 表 1：逐处清单（file:line，method，signal，timer）

```text
--- landed_45b0a5e2（39 处）---
  api/candidateRejections.ts:37    method=—     (absent            ) signal=False timer=—                  opts=object-literal
  api/travelerPreferences.ts:23    method=—     (absent            ) signal=False timer=—                  opts=object-literal
  api/useContinuationState.ts:22    method=—     (absent            ) signal=True  timer=—                  opts=object-literal
  api/v10Execution.ts:26    method=—     (absent            ) signal=False timer=—                  opts=absent
  api/v10Execution.ts:32    method=—     (absent            ) signal=False timer=—                  opts=absent
  api/v12Authoritative.ts:21    method=—     (absent            ) signal=False timer=—                  opts=object-literal
  app/V8Experience.tsx:243   method=—     (absent            ) signal=True  timer=—                  opts=object-literal
  features/discovery/RealCityDiscoveryPanel.tsx:59    method=—     (absent            ) signal=False timer=—                  opts=object-literal
  features/execution/LiveRecovery.tsx:112   method=—     (absent            ) signal=False timer=—                  opts=absent
  features/execution/LiveRecovery.tsx:151   method=—     (absent            ) signal=False timer=—                  opts=absent
  features/execution/LiveRecovery.tsx:225   method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/inbox/JourneyInboxWorkbench.tsx:82    method=—     (absent            ) signal=False timer=—                  opts=non-literal-expr
  features/notifications/PushCapabilityCard.tsx:36    method=—     (absent            ) signal=False timer=—                  opts=absent
  features/notifications/PushCapabilityCard.tsx:56    method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/planning/PlanComparison.tsx:88    method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/planning/PlanWithAiSheet.tsx:374   method=—     (absent            ) signal=True  timer=—                  opts=object-literal
  features/planning/PlanWithAiSheet.tsx:402   method=—     (absent            ) signal=False timer=—                  opts=object-literal
  features/planning/PlanWithAiSheet.tsx:434   method=—     (absent            ) signal=True  timer=—                  opts=object-literal
  features/planning/PlanWithAiSheet.tsx:492   method=POST  (literal           ) signal=True  timer=—                  opts=object-literal
  features/planning/PlanWithAiSheet.tsx:534   method=—     (absent            ) signal=True  timer=—                  opts=object-literal
  features/planning/PlanWithAiSheet.tsx:561   method=—     (absent            ) signal=True  timer=—                  opts=object-literal
  features/planning/PlanWithAiSheet.tsx:605   method=POST  (literal           ) signal=True  timer=—                  opts=object-literal
  features/recovery/RecoveryRequiredPanel.tsx:26    method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/recovery/V14PreventivePanel.tsx:79    method=—     (absent            ) signal=False timer=—                  opts=absent
  features/recovery/V14RecoveryTruthPanel.tsx:55    method=—     (absent            ) signal=False timer=—                  opts=absent
  features/recovery/V14RecoveryTruthPanel.tsx:69    method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/simulation/simulationAdapter.ts:229   method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/simulation/simulationAdapter.ts:296   method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/simulation/simulationAdapter.ts:335   method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/simulation/simulationAdapter.ts:376   method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/simulation/simulationAdapter.ts:433   method=—     (absent            ) signal=False timer=—                  opts=object-literal
  features/simulation/simulationAdapter.ts:480   method=—     (absent            ) signal=False timer=—                  opts=object-literal
  features/stay/HotelsPanel.tsx:54    method=—     (absent            ) signal=False timer=—                  opts=absent
  features/stay/HotelsPanel.tsx:63    method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/stay/HotelsPanel.tsx:64    method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/stay/HotelsPanel.tsx:87    method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  lib/readDeadline.ts:44    method=—     (absent            ) signal=False timer=—                  opts=non-literal-expr
  lib/readDeadline.ts:59    method=—     (absent            ) signal=True  timer=—                  opts=object-literal
  lib/sceneClock.ts:116   method=—     (absent            ) signal=True  timer=—                  opts=object-literal
--- earlier_dcae1bc9（38 处）---
  api/candidateRejections.ts:37    method=—     (absent            ) signal=False timer=—                  opts=object-literal
  api/travelerPreferences.ts:23    method=—     (absent            ) signal=False timer=—                  opts=object-literal
  api/v10Execution.ts:26    method=—     (absent            ) signal=False timer=—                  opts=absent
  api/v10Execution.ts:32    method=—     (absent            ) signal=False timer=—                  opts=absent
  api/v12Authoritative.ts:21    method=—     (absent            ) signal=False timer=—                  opts=object-literal
  app/V8Experience.tsx:242   method=—     (absent            ) signal=True  timer=—                  opts=object-literal
  features/discovery/RealCityDiscoveryPanel.tsx:59    method=—     (absent            ) signal=False timer=—                  opts=object-literal
  features/execution/LiveRecovery.tsx:112   method=—     (absent            ) signal=False timer=—                  opts=absent
  features/execution/LiveRecovery.tsx:151   method=—     (absent            ) signal=False timer=—                  opts=absent
  features/execution/LiveRecovery.tsx:225   method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/inbox/JourneyInboxWorkbench.tsx:82    method=—     (absent            ) signal=False timer=—                  opts=non-literal-expr
  features/notifications/PushCapabilityCard.tsx:36    method=—     (absent            ) signal=False timer=—                  opts=absent
  features/notifications/PushCapabilityCard.tsx:56    method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/planning/PlanComparison.tsx:88    method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/planning/PlanWithAiSheet.tsx:373   method=—     (absent            ) signal=True  timer=—                  opts=object-literal
  features/planning/PlanWithAiSheet.tsx:401   method=—     (absent            ) signal=False timer=—                  opts=object-literal
  features/planning/PlanWithAiSheet.tsx:433   method=—     (absent            ) signal=True  timer=—                  opts=object-literal
  features/planning/PlanWithAiSheet.tsx:491   method=POST  (literal           ) signal=True  timer=—                  opts=object-literal
  features/planning/PlanWithAiSheet.tsx:527   method=—     (absent            ) signal=True  timer=—                  opts=object-literal
  features/planning/PlanWithAiSheet.tsx:554   method=—     (absent            ) signal=True  timer=—                  opts=object-literal
  features/planning/PlanWithAiSheet.tsx:598   method=POST  (literal           ) signal=True  timer=—                  opts=object-literal
  features/recovery/RecoveryRequiredPanel.tsx:26    method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/recovery/V14PreventivePanel.tsx:79    method=—     (absent            ) signal=False timer=—                  opts=absent
  features/recovery/V14RecoveryTruthPanel.tsx:55    method=—     (absent            ) signal=False timer=—                  opts=absent
  features/recovery/V14RecoveryTruthPanel.tsx:69    method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/simulation/simulationAdapter.ts:229   method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/simulation/simulationAdapter.ts:296   method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/simulation/simulationAdapter.ts:335   method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/simulation/simulationAdapter.ts:376   method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/simulation/simulationAdapter.ts:433   method=—     (absent            ) signal=False timer=—                  opts=object-literal
  features/simulation/simulationAdapter.ts:480   method=—     (absent            ) signal=False timer=—                  opts=object-literal
  features/stay/HotelsPanel.tsx:54    method=—     (absent            ) signal=False timer=—                  opts=absent
  features/stay/HotelsPanel.tsx:63    method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/stay/HotelsPanel.tsx:64    method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  features/stay/HotelsPanel.tsx:87    method=POST  (literal           ) signal=False timer=—                  opts=object-literal
  lib/readDeadline.ts:44    method=—     (absent            ) signal=False timer=—                  opts=non-literal-expr
  lib/readDeadline.ts:59    method=—     (absent            ) signal=True  timer=—                  opts=object-literal
  lib/sceneClock.ts:116   method=—     (absent            ) signal=True  timer=—                  opts=object-literal
```

## 交给 ORD-0280/0281 的清单基础（只交清单，不改码）

```text
写腿逐处（落地代，AST 判定）：
  带signal  features/planning/PlanWithAiSheet.tsx:492  (POST)
  带signal  features/planning/PlanWithAiSheet.tsx:605  (POST)
  裸发     features/execution/LiveRecovery.tsx:225  (POST)
  裸发     features/notifications/PushCapabilityCard.tsx:56  (POST)
  裸发     features/planning/PlanComparison.tsx:88  (POST)
  裸发     features/recovery/RecoveryRequiredPanel.tsx:26  (POST)
  裸发     features/recovery/V14RecoveryTruthPanel.tsx:69  (POST)
  裸发     features/simulation/simulationAdapter.ts:229  (POST)
  裸发     features/simulation/simulationAdapter.ts:296  (POST)
  裸发     features/simulation/simulationAdapter.ts:335  (POST)
  裸发     features/simulation/simulationAdapter.ts:376  (POST)
  裸发     features/stay/HotelsPanel.tsx:63  (POST)
  裸发     features/stay/HotelsPanel.tsx:64  (POST)
  裸发     features/stay/HotelsPanel.tsx:87  (POST)
其中带 signal 的只有 2 处（PlanWithAiSheet.tsx:492 / :605），带计时器的 0 处 ⇒ 『写腿没有期限』这句在落地代仍然成立；
两代文件级差：只有 api/useContinuationState.ts 从 0 → 1（GitHub compare 的 frontend/src 改动 6 件里，其余 5 件站点数未变）；
本件产码 0 处：没有任何产品字节被我改动（普查只读导出树）。
```

```text
复跑：node o289_ast_census.js <导出>/frontend/src <out.json> <repo>/frontend/node_modules/typescript/lib
     python o289_export_two_gens.py（先读尖、tarball 导出、与递归树逐名对表）
     python o289_analyze.py / o289_attribute.py / o289_hypotheses.py（口径对比与归因）
```
