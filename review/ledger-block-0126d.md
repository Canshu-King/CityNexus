### 🪞 e345b9d6（SESSION=e345b9d6）ORD-0126 补项交付：403 不再借 401 那句话（并给出服务器自己的码）＋ 屏上那趟与提交那趟同源第一次被门钉住 @2026-09-23 01:0x +08 → 提交 **`9544628`**

**报数六要素**：树 `D:/moodle/_qoder_integration_20260919`；`git log -1` = **`9544628 2026-09-23 01:09 +0800 fix(frontend): a 403 says permission, not sign-in, and the screen's journey is the one submitted (ORD-0126 follow-ups)`**；`git status --short -- frontend` 空；解释器 Node/Playwright ＋ `D:/moodle/CityNexus/.venv/Scripts/python.exe` = 3.12.14；命令 `python review/run_spec.py "e2e/qoder-a-refusal-says-what-it-is.spec.ts" 4600 --config playwright.prod-gate.config.ts` → 收集 **4 节点**（1 real-seed ＋ 3 门），执行 **exit 0 / 4 passed**（`run-run096273.log`）；回归链读数见文末；`tsc --noEmit -p tsconfig.check.json` **exit 0** 三次（`tsc-0126a/b/c.txt`）。

**③ 补的那半：403 曾经被说成"重新登录"**。`classifyReadFailure` 原来把 `401 || 403` 合成一条 `UNAUTHORIZED`，文案是「这一趟需要重新登录才能读 / 登录之后这一趟还在」——而 403 的语义是"我认得你，这一步不行"（预览链上就是 `PREVIEW_GUARDED`）。这跟"把 404 说成网络断了"是同一族缺陷：**把一个具名的 HTTP 回答改写成另一个原因**。现在拆开：
- `401` → `UNAUTHORIZED`，出口 `sign-in`（原样保留）；
- `403` → 新增原因 **`FORBIDDEN`**，出口 **`choose-journey`**，文案自己说清边界：「服务器认得你是谁，但明确拒绝了这一步（HTTP 403：PREVIEW_GUARDED）。这不是网络问题，也不是登录问题——重新登录不会改变它的回答。你可以换一趟行程，或回到选择页。」
- 顺手补了 **`server_code`** 字段（`Attribution` ＋ telemetry 多一格 `server_code=…`），因为"具名"必须能引服务器原话，不是我转述。

门 `e2e/qoder-a-refusal-says-what-it-is.spec.ts`：
- `ord0126d-a`（zh）：403 的渲染文字必须含「这一步这台服务器不允许」＋`403`＋`PREVIEW_GUARDED`；**不得**出现 401 的标题「这一趟需要重新登录才能读」，不得出现网络句；`failure-sign-in` 按钮必须 **不存在**（`toHaveCount(0)`）；出口 `failure-choose-journey` 可见且 `focus()` 后 `document.activeElement` 就是它；结构字段 `data-attribution-reason=FORBIDDEN`、`data-recovery-action=choose-journey` 必须与文字一致。
  ⚠ 我第一版在这里写错过一条断言：用 `/重新登录|网络不可用/` 禁词——而**正确文案本身**含"重新登录不会改变它的回答"，于是门在自己是对的时候红（`run-run095837.log`）。改成"禁 401 的标题＋禁登录出口"才是可判别的断言，这条我按实记。
- `ord0126d-b`：401 仍必须说「重新登录」，且**不得**塌成 403 那句——两条拒绝各留各的出口。

**④ 补的那半：屏上与提交同源，之前没人测**。提交路径确实都吃 `data.journey.id`（含 `V8Experience.tsx:1693` 传给 AI 规划面板的 `journeyId`），但这是"看起来对"，没有门钉着，下一次重构就能悄悄换成 `localStorage`。新节点 `ord0126d-c`：真实加载 Today → **把设备记住的引用换成另一枚合法 uuid**（`77777777-…`）→ 走用户真会做的动作（「AI 帮我规划」→ 输入目标 → 提交）→ 从浏览器自己的请求日志里取 `POST /api/v1/journeys/<uuid>/plans` 的 uuid。收据 `review/evidence/ui-overnight/ord0126d-id-source.json`：

```text
journeyOnScreen          3e3158ef-923a-43af-ae97-b6e6d6d9c3e0
storedReferenceAfterLoad 77777777-7777-4777-8777-777777777777
submittedRequests        ["POST 3e3158ef-923a-43af-ae97-b6e6d6d9c3e0"]   ← 提交的是屏上那趟
```

两次失败尝试也记在门注释里（不藏）：先用 `hub-stay-retry`，它在"已有住宿选项"的 seed 行程上**根本不渲染**；再退而求其次想靠只读导航触发请求，而加载完成后没有任何路径会去重读 storage——**没有请求就没有比较**，所以换成 AI 面板这条真有 POST 的路径。

**突变（两条都杀）**：`killAB1-403-wears-the-401-sentence`（把 401/403 合回去，anchor 317 B、bytes_changed **−141**）→ `ord0126d-a` **KILLED**，变红原文引的就是那句错话：`a 403 did not say what a 403 says: "身份 这一趟需要重新登录才能读 …登录之后这一趟还在。 重新登录 …"`；`killAB2-sheet-submits-the-stored-journey`（面板改成从 storage 取 id，anchor 63 B、bytes_changed **＋63**）→ `ord0126d-c` **KILLED**，原文 `the screen shows journey e0be4f58-… but the traveller's action submitted ["77777777-…"]`。两把都 `anchor_hits=1`、`on_disk=True`、跑完 `restored OK`。

**门禁**：新 spec **4/4**（`run-run096273.log`）；回归链七张（refusal / failure-has-an-exit / onboarding-failure / ai-sheet-blocked / demo-entry-addresses / raw-enums / surface-readings）**29 passed / exit 0**（`run-run096748.log`；逐 spec 节点数已核对：3/3/2/4/6/5/5，没有哪张被静默跳过）。

**可读坐标（我自己发的，同一把发布器 v3）**：`https://github.com/Canshu-King/CityNexus/tree/commander/control/evidence/ord0126d` — **7 个文件全 201 ＋ BYTE-LEVEL MATCH**，独立回读 `remote entries=7 disagreements=0 on-disk-but-not-published=[]`（`review/readback-0126d.txt`）：patch `9544628__9544628.patch` 21,458 B blob **`1ab182c48078e38b`**；source+parent blob **`2f816650ca0640a5`**；changed-files blob **`c48f4363e50f143e`**；`mutation-receipts.json` blob **`4c47ad40a5b26785`**；403 可见文字收据 blob **`51c116324f0a2e16`**；屏上/提交对照收据 blob **`fdb9b6bb9e59c784`**；`MANIFEST.txt` blob **`07277667981a69cd`**。

**现场**：产品分支仍 0 次 push；未碰 `:4781/:4782/:8693` 与 `_live.db`；`demo/reset` 0 次；provider 出网 0 次；账本只追加本块。

status: ORD-0126 **补项 DONE@2026-09-23T01:0x+08 by e345b9d6**（提交 `9544628`）——③ 的 403 半格与 ④ 的同源断言都补上了，各带一条能杀的门；(b) 存储支撑那格早已由 ORD-0178 交付。至此 **ORD-0126 五格全闭**。
evidence: `frontend/src/lib/failureAttribution.ts`（FORBIDDEN/server_code/拆分支）、`frontend/e2e/qoder-a-refusal-says-what-it-is.spec.ts`、`review/evidence/ui-overnight/ord0126d-403.json`、`ord0126d-id-source.json`、`review/ord0126-kill.txt`、`review/ord0126-chain.txt`、`review/add-ord0126-mutants.py`、`review/run-run095837.log`（我自己那条禁词断言写错的一手证据）、`run-run096273.log`。
