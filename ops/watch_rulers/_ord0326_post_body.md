**S1-q64sweep → ORD-0326 第一刀已落候选分支（一条共享服务器原因通道，tsc 0 / spec 4 绿 / 3 枚突变全被抓）；但本令的归属与账本冲突，先报这条**

**① 碰撞检查结果与本令不一致 —— 需要一句话裁定**。账本里 03:34 的号令者 dispatch 原文（读自 `origin/cmdcontrol:CITYNEXUS_AGENT_CONTROL.md`）：**ORD-0323（`ProductErrorBoundary.tsx:104-105` 组件栈进 `<pre>`、`JourneyInboxWorkbench.tsx:88` 把服务器正文塞进 `Error.message`）照旧归 @B，基线 `9a669c8b`**。而 04:05 的本令写"那 8 格 `JourneyInboxWorkbench.tsx` 是你的主场"。本令第 1 步自己定的规矩是"两车道同一文件不并存、B 动过的让给 B"，所以我按规矩**让出 inbox 的 cells=9 与 `ProductErrorBoundary.tsx`，一字节未改**。另两处归属也对不上：`PlanWithAiSheet.tsx` 在账本里是 **@F** 动过码的那枚（不是 B），`PlanComparison.tsx` 账本里没有任何归属记录 —— 这两枚本令点给 B，我照令也让了。现读 `git ls-remote --heads` 共 85 条，**没有 B 的候选分支**，即 B 是"已认领、未推码"。如果 04:05 的意思真是把 `:88` 改派给 S1，请明说撤掉 B 的 ORD-0323，否则 B 一推码就与我撞。

**② 已落的码**（`agent/S1-q64sweep-candidates` = commit b32c0d6516fe60539d6485e95b8fa4534e1ad56d，`ls-remote` 回验同值；权威线 0 推）：新增 `frontend/src/lib/serverReason.ts`（唯一读上游句子的地方：只读已解析信封的具名字段，即 backend/app/main.py:492 那个 `{"error":{…}}`；`request_id` 取信封里的 `trace_id`；六种允许字段之外不产出自由文本；**`cause.message` 一律不读**，多行的堆栈形状直接判"服务器没给句子"）+ `frontend/src/components/ServerReasonDetail.tsx`（唯一允许那句上屏的槽位：`<details>` 技术详情 + `data-attribution` 归属标签，正是 Q67=① 的形状；主文案只拿 `serverReasonHeadline`，永远拿不到那句）。三枚 call site 改为复用同一条：`frontend/src/features/stay/HotelsPanel.tsx`、`frontend/src/features/agent/AgentComposer.tsx`、`frontend/src/features/agent/CopilotDock.tsx` —— 原先这四处各写各的 `cause.message` / `body?.detail ??`，正是要求①禁止的形状。

**③ 验收读数**：`tsc -p tsconfig.typecheck.json --noEmit` exit=0；`e2e/server-reason-ord0326.spec.ts:26` 双向断言 4 passed，用不带 webServer 的 `playwright.logic.config.ts:1` 跑 —— 因为 `frontend/playwright.config.ts:18` 那行会绑 `127.0.0.1:8000`，而 `:8000` 是 NOT AVAILABLE 的决定、`reuseExistingServer:true` 又意味着答我的可能不是我的后端。断言打在 `serverReasonScreenTexts`（组件只排版它、自己不加字）上，理由是我量到的跑具限制：Playwright 的 transform 把 JSX 改写成 `react-dom/server` 拒绝的 `{__pw_type,type,props,key}` 节点形状 —— 我用一行 JSX 模块复现过，不是我的组件问题。

**④ 突变检查**（一条永不红的断言不算证据）：`A_sentence_into_main_copy`、`B_request_id_dropped_from_machine_line`、`C_multiline_guard_removed` 三枚各打红预期的那一条（三次都是 `1 failed / 3 passed`），还原后工作树 clean、`4 passed`。

**⑤ r4 改前改后（AST 尺 blob eb262f59e54d5142ad0e8041704e751eac473ace，已取代 r3）**：我触碰的三枚文件 `4 → 3`。`HotelsPanel.tsx` 1→0；另三枚汇点没消失而是换了规则 —— `AgentComposer.tsx:191`、`CopilotDock.tsx:458`、`CopilotDock.tsx:782` 从 `UPSTREAM_EXCEPTION_TO_DOM` 变 `UPSTREAM_TEXT_VIA_HELPER_TO_DOM`，因为通道入口 `reasonFromThrown(cause)` 必须碰 `.body`，而 r4 按文件量、看不见跨文件的消毒。**给 S4 的一条**：r4 目前没有"跨文件 sanitizer"的识别，而把 `serverReasonHeadline` 加进白名单恰是 r4 自己文档警告过的认名陷阱 —— 这一格怎么解请 S4 定，我不替尺编规则。原始异常正文进主文案这件事，在这三枚汇点上确实没了。

**⑥ 我没做也没装成做了的**：`frontend/src/app/V8Experience.tsx`（r4 报 `:1282`、`:1385`、`:1562`）。该文件 `setMessage` 有 15 个写手，又是账本记过"两边都改过、手工并档"的那一枚，要做对得先定 `message` 的状态形状，比我在本窗口能验的更长 —— **整块留着没开半截**。另外 `V8Experience.tsx:1282` 我核过是**尺的假阳性**（那里是本机写的失败页文案 `copy.body`，r4 吃的是字段名 `body`），我不照它改产品。完整 e2e 未跑（需 `:8000` 与 dev server）。

**⑦ 代次与交付件**：generation=0f8b925facabc9df57bab600b86d999dd515bf94；我的基线 65df31df96cfb8a954f5feb36484710a883e1597 是其祖先，且 `frontend/src` tree 两枚尖相同（1a657259f26028ff17b5cdc65c0aab9553bf4ecc，changed_frontend_files=0）⇒ 候选可直接并不踩别人。件 `commander/control:evidence/ord0326-server-reason-S1/channel_r1.json` = blob baa3f4f902997f3f1a54873628e12fe558969ac1（commit 300fd61ea0012e27e26ee6ea0d7207ec1856e0d3，`rev-parse` 与本地 `hash-object` 全等），含 `generation`、逐格 `cite`、"我跑的命令"。

**⑧ 一处自纠**：写本块时我又手打错一枚 40 位（基线尾号），被自己的 `_hex_preflight.py` 拦住才改回 —— 结论是**坐标一律程序产出、不许手抄**，这条我会带进后面的件里。

**边界** 0 推权威线、未 demo/reset、未碰 `*_live.db`/`*_preview.db`、未在共享树跑 `vite build`；工作树在 `D:/moodle/_qoder_ord0326_S1`，`node_modules` 是指向共享树的 junction（只读用，收尾先摘链），共享检出 `git status --porcelain frontend` 仍 0 行；未读未打印任何凭据。**账本块** `D:\moodle\_qoder_ledger_inbox\S1-q64sweep_0450.md`（首行 `### `，自跑 `_hex_preflight.py` offenders=0 与 Q43 r4c = GREEN findings 0）。
