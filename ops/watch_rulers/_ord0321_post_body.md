**S1-q64sweep → ORD-0321 已交：16 格逐格判"手机上真能撞到吗" = 14 可达 / 2 UNKNOWN / 0 构造性够不到；另补你 03:07 点名的 `ruler_delta` 版件**

先报一条你我都得知道的：**权威尖在这单中途移动了**。我开工读到 30de4ebe409f49c5e25f4758cb2e5f4e90764a4f，收尾再读是 9a669c8bec863fadf31d5158f4a1be66aec49f23。件里 `generation` 仍 pin 我实测那枚、`tip_moved=True`、`authoritative_tip_now` 记新尖。按任务书我在新尖重读了基准那一格：尺 r3 仍 1 命中、规则 UPSTREAM_TEXT_VIA_HELPER_TO_DOM、链 `serverReasonSentence`(:159)→`failureReason`，但渲染行从 `:1016` 变成 **`:1046`** —— 两尖之间 `git diff --stat -- frontend/src` 只有 `frontend/src/features/planning/PlanWithAiSheet.tsx` 动了（blob 3bb6a39067a380c2f75629fd7562f0de8f5d2f2a → fc4d6111dc013008b610a240aab096deebe2436f，+57 −6）。我引用的其余每个文件都做了两尖 `rev-parse` 比对，全部 SAME，所以本表 16 个 cite 除上面那一枚仍指原行。

**判据与结论**：cells=16，`REACHABLE_ON_PHONE`=14、`UNKNOWN`=2、`CODED_BUT_UNREACHABLE`=0，`live_observed_any=false`。我答的是"手机点击到服务器原话之间的链路在代码里是否闭合"，不是"我在手机上看见了" —— 你 03:10 写明 `:8000` 仍 NOT AVAILABLE 且手机不换代（Q61），本会话没有活面，我也不拿 `vite build` 造一个（那会同时踩 `frontend/node_modules` 这个 junction）。

**0 格构造性够不到的原因**：底栏虽只有 5 键（routes/v8Routes.ts:21），但 app/V8Experience.tsx:424 把两张路由表并成 `drawerRoutes`，:1440 的汉堡在 styles.css:178 的 `@media (max-width: 680px)` 下显形、:1839 逐条渲染 ⇒ 桌面键手机全能走。更近的入口本来就在底栏：app/V8Experience.tsx:1959 住宿 tab 挂 HotelsPanel、app/V8Experience.tsx:1962 预订 tab 挂 JourneyInboxWorkbench、:1573 Today 未选方案时即 PlanComparison、:1777 CopilotDock 无条件挂（窄屏布局 styles.css:429、:752）。

**钉住全部判定的一条服务器事实**（读自 `git show <tip>:backend/app/main.py`，只读）：信封 main.py:483-492 是 `{"error":{code,message,message_key,trace_id,details}}`，而 main.py:570 把 HTTPException 的 detail 原样放进 `error.message` ⇒ 前端读 `body.error.message` 的分支拿到的就是原话。顺带纠正我自己一处口径：**服务器从不发顶层 `detail` 键**，所以先试 `body?.detail` 的几处（features/stay/HotelsPanel.tsx:93、features/execution/LiveRecovery.tsx:238、features/planning/PlanComparison.tsx:96）实际取的是第二候选 `error.message` —— 正文照样进屏，只是取 message；这不改任何一格 verdict，只改判据叙述。500 不在此通道（无 JSON 体，前端 features/inbox/JourneyInboxWorkbench.tsx:82 自己抛，屏上是浏览器解析话术），故我的 REACHABLE 全以 4xx/具名 5xx 为前置。最普遍的是 main.py:640 的 `require(...)`：六个 inbox handler 开头都调它，行程 id 一失效就答 `Journey <uuid> was not found`，而 :317 与 :336 两格是挂载即自动发请求（features/inbox/JourneyInboxWorkbench.tsx:345、:349）⇒ 打开预订页就能看到那句原话。

**两枚 UNKNOWN 缺的步**：components/ProductErrorBoundary.tsx:104 —— 确实挂在根上（main.tsx:1668）且崩了就渲染 `:104`/`:105`（连组件栈），缺"旅客自己能撞出来的崩溃"，没活面证不到崩得了；features/inbox/JourneyInboxWorkbench.tsx:386 —— 要先有 decodedText，而扫描器只挂在抽屉那条 bookings 路由（app/V8Experience.tsx:1729），Trips 的预订 tab 里没有它，且手机摄像头解码本会话没跑过。

**上架（新路径，0 覆盖，均 decision=CREATED、proof=BYTE-LEVEL MATCH，且我用 fetch+`rev-parse` 第二扇门独立回读全等）**

- ORD-0321：`commander/control:evidence/ord0321-reachability-S1/reachability_r1.json` = blob 6fd9068e806394f597275efef1c1c4cdeff8ed42，commit a4d2a783c455dc3ff77ff8729ca35a956f709542
- 你 03:07 点名的 `ruler_previous` + 字面 `ruler_delta`：`commander/control:evidence/q64-sweep-S1/sweep_r3.json` = blob 4d69a646a9f20384be419df83e784473951f3c66，commit fabbc539dd2387c1a3ec435db6f3c5a7219dc12d。`ruler_delta` 是 (only_in_r3 ∪ only_in_r2) 两空集长度派生 = 0，不是我手填；`sweep_r1.json` = f783b12eea629d52dbe8ff00f45716d50b99e30c 与 `sweep_r2.json` = 33576c7390ec431ba0fad5d6dd73a76a99fe59e0 一律不动。
- 你的复核件我从架上读了：`evidence/cmdr-s1-verify-0306/verify_r1.json` = 2799ec3d3be2b058edde839bfeba96c947e6332d，总数与我一致（74 / 25 / 12）。

**边界** 0 改产品字节（交付前 `git status --porcelain frontend` 读回 0 行）、0 推权威分支、未 import 尺、未 vite build、未进 `frontend/node_modules`、未 demo/reset、未碰 `*_live.db`/`*_preview.db`、未读未打印任何凭据。**账本块** `D:\moodle\_qoder_ledger_inbox\S1-q64sweep_0331.md`（首行 `### `，自跑 Q43 r4c = Q43_GATE_GREEN，findings 0）。**下一步归属**：把 14 枚 REACHABLE 从"链路闭合"升成"手机上看见了"要活手机面，归 P3 与 `:8000` 恢复；两枚 UNKNOWN 的缺口我在件里各自写明缺哪一步。本车道零产品修复。
