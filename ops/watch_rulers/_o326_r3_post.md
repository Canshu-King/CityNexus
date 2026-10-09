**S1-q64sweep → ORD-0326 按新范围重交：开枝 0f8b925f、8 枚文件、r5 28→21（派给我的 8 枚汇点全清，只剩指定槽 1 枚）；但新范围与 B 已交付的两枚文件重叠，需要你逐文件二选一**

**你要的两项**：开枝 sha = 0f8b925facabc9df57bab600b86d999dd515bf94（`merge-base --is-ancestor` 已验是我枝祖先）；候选 `agent/S1-q64sweep-candidates-r2` = commit 919f09a70a0a140cd0a19a8abeb90f340dfa9f11（`ls-remote` 回验同值）。**本车道碰过 8 枚**：`frontend/src/lib/serverReason.ts`、`frontend/src/components/ServerReasonDetail.tsx`、`frontend/src/features/inbox/JourneyInboxWorkbench.tsx`、`frontend/src/features/agent/AgentComposer.tsx`、`frontend/src/features/agent/CopilotDock.tsx`、`frontend/src/components/ProductErrorBoundary.tsx`、`frontend/e2e/server-reason-ord0326.spec.ts`、`frontend/playwright.logic.config.ts`。

**让出的逐文件回退、没 reset 整枝**：`frontend/src/features/stay/HotelsPanel.tsx` 在第一枝 b32c0d6516fe60539d6485e95b8fa4534e1ad56d 上被我改过，本枝相对开枝 diff 为 0 行；`frontend/src/app/V8Experience.tsx`、`PlanWithAiSheet.tsx`、`PlanComparison.tsx` 一字未动（件里 `yielded_files_confirmed_untouched` 逐枚记布尔）。

**r5 读数（`--tree` + `git archive <sha> frontend/src`，尺 blob ff98091cf3accb0d836ae25ba49820170b92d932、自测 20/20）**：开枝代次 28 枚 / 17 文件 → 我的枝 21 枚 / 16 文件。移除的 8 枚全在你新派给我的格上：`JourneyInboxWorkbench.tsx:687`、`:691`、`:731`、`AgentComposer.tsx:185`、`CopilotDock.tsx:450`、`:770`、`ProductErrorBoundary.tsx:104`、`:105`；新增只有 `ServerReasonDetail.tsx:29`（Q67=① 的指定槽）。提交树与工作树两次读数一致。

**改法**：`JourneyInboxWorkbench.tsx:88` 不再把服务器句子重铸进 `Error.message`，改抛 `InboxApiFailure(status, envelope)`；八个 catch 站点统一调 `noteFailure()`，屏幕只拿设备兜底句、原话交给 `<ServerReasonDetail>`；两枚挂载即自动发的读（`:345`、`:349`）同样在通道上。`ProductErrorBoundary.tsx` 按你条件：栈面不是被打开而是**关掉** —— `componentDidCatch` 只送 `console.error`，state 不再存 `info`。

**要你裁的**：`JourneyInboxWorkbench.tsx` 与 `ProductErrorBoundary.tsx` 正是 B 在 04:50 已交付的两枚（`review/0323-two-exposure-cells-b` = e302e4c433712284a23c1c0ab11147fe105e1e22）。同尺同模式量 B 的枝：28→26，移除五枚但**留三枚仍被旗**（`JourneyInboxWorkbench.tsx:703`、`:707`、`:747`：thrower 闭了，三个出屏口仍吃 `error.message`）。我这版 28→21。**两版不能 git 合并，请逐文件二选一**；倾向保我这版的理由是可复算（同模式下派给我的格全清、只剩指定槽）。

**三车道交集（按各枝自己的 merge-base 算）**：S1 8 / B 3 / D 6；**S1∩B = 上述两枚**；**S1∩D = 空**；**B∩D = 空**。（提醒：不能对现尖 `c1bea4c2…` 直接比 —— D 的 ORD-0325 已落进现尖、B 开枝在两代之外，那样算会得出假表。）

**其余验收**：`tsc -p tsconfig.typecheck.json --noEmit` exit=0；spec 4 passed，用不启动任何服务的 `playwright.logic.config.ts`（仓库配置会绑 `127.0.0.1:8000`，那是 NOT AVAILABLE 的决定，且 `reuseExistingServer:true` 会让别人的后端替我作证）；三枚突变各打红预期一条。**回执件** `commander/control:evidence/ord0326-server-reason-S1/channel_r3.json` = blob 94de764e50019d8c76c7cb09fadf68e534cdab64（commit 8fd0153953caad392a3e93e57013deb918fca351，`rev-parse` 与本地 `hash-object` 全等）；旧件 `channel_r1.json` = baa3f4f902997f3f1a54873628e12fe558969ac1、`channel_r2.json` = 86fc78a7540535ee2898d7129449428fbe6bb7ad 不动。**账本块** `D:\moodle\_qoder_ledger_inbox\S1-q64sweep_0524.md`（首行 `### `，自跑 `_hex_preflight.py` offenders=0、Q43 r4c GREEN）。

**边界** 0 推权威线、0 改共享检出（`git status --porcelain frontend` 读回 0 行）、未 demo/reset、未 vite build、未碰 `*_live.db`/`*_preview.db`、未读未打印任何凭据；工作树的 `node_modules` 只读 junction，收尾摘除并回验共享树完好。**仍无人认领的 r5 旗**：`V8Experience.tsx` 4 枚（`:1314`、`:1385`、`:1562`、`:2536`）、`DestinationPreparationPanel.tsx` 3 枚、`main.tsx` 2 枚、`ActivityDetail.tsx:206`、`RecoveryRequiredPanel.tsx:166`、`SimulationPanel.tsx:934`、`AgentRunRail.tsx:18`、`V12TripStudioPanel.tsx:106`、`V14RecoveryTruthPanel.tsx:162`、`RealCityDiscoveryPanel.tsx:150`。
