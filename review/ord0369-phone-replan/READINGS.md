# ORD-0369 r3 · 手机端 Replan 真链路读数（lane Q，2026-09-28 03:0x +08）

代次：base `04071b8258ebcdcf1e9e4c9714fb516283d1e1ad`（ORD-0375 落地的现尖），分支 `review/Q-ord0369-replan-walkthrough-r3`。
本单在夜里被同一条线两次越过：r2 的 base 是 `961836390c5325863acdc1834d4a4cd16fd97081`，之后线又走 9 笔，与我在 `LocaleContext.tsx` 再次同文件相遇 ⇒ 按 Q72 重基一次。已推的 `-walkthrough` 与 `-r2` 两枝都不覆盖（Q57）。

## 重基时真正要看的不是冲突标记，而是"自动合过了"这件事

7 笔 cherry-pick **全部无冲突**，包括 `frontend/src/i18n/LocaleContext.tsx`。这恰恰是 Q72 不让指挥官拿自动合源码当交付的理由：JS 对象字面量里同名键会静默取后一个值，git 不会报任何东西。所以我把合并后的那枚文件自己量了一遍：

- `en` 与 `zh-CN` 各 665 枚键，**重名 0 枚**（按 `^  "key":` 逐枚数出来再取重复，不靠肉眼）。
- 线侧那 9 笔新加的 5 枚（`recovery.statusUnavailable`、`recovery.guardianEnvelope`、`recovery.changedFromActivity`、`recovery.changedToActivity`、`discovery.providerUnnamed`）两份都在。
- 本单的 25 枚（`recovery.*` 18 枚 + `studio.*` 7 枚）一份不缺。
- 我删掉的那枚孤儿兜底键 `studio.gateFailed`：在 base `04071b82` 那份文件里它**仍有读者**（`git show 04071b82:frontend/src/features/studio/V12TripStudioPanel.tsx` 第 88 行那串 token 拼接），而那一行正是本单删掉的东西 ⇒ 删键与删读者必须同树，否则要么留下无人读的键、要么留下引用空键的读者。r3 树里两者都为零命中。

## 构建前置（FRONTSRC_BUILD_PREREQ，两条都真跑）

- `tsc --noEmit`（`tsconfig.typecheck.json`）退出码 0；`--listFiles` 回读 875 个文件，含本单改的 4 枚源文件 ⇒ 排除"零文件空转的绿"。
- `vite build` 退出码 0，13.84 秒，预缓存 8 条，候选产物 `assets/index-D-tB4NCX.js`。
- 依赖来自既有导出目录里对权威库 `frontend/node_modules` 的**硬链接**（`typescript/package.json` 的 nlink 为 13，即共享 inode 而非复制）。**全程没有建过 junction**，因此 `drop_old_junction` 那段卸载-再判残留的流程在我这条路上没有对象可卸；被服的 dist 与本车道目录无共享 inode。

## canary 替身证明：第三次重做，因为链在单内又换过一次代

号令者报的在服产物是 `index-B800Wnn2.js`；我用 `live_checks/cmdr_tunnel_read_r1.py:71` 与无凭据的 `:4781` 量到现服的是 `index-CnUOxIWz.js` + `index-CuNe7Fij.css`。所以任何更早的字节相等都描述一个没人再服的 bundle。重做后的读数（`canary_proof.json`）：

| 面 | 地址 | 在服产物 | PNG 字节 | sha256[:16] | 卡上标题（渲染文字） |
|---|---|---|---|---|---|
| 用户可见面 | `:4781` | `/assets/index-CnUOxIWz.js` | 351517 | `f113ffb86520eedb` | `Trip evidence needs re-syncing` |
| 车道替身面 | `:4190` | `/assets/index-CnUOxIWz.js` | 351517 | `f113ffb86520eedb` | `Trip evidence needs re-syncing` |

同一枚 bundle、同一屏、像素逐字节相同 ⇒ 替身成立；而两面的后端不同（在服 `:8693` 与本车道 r3 树），所以这条对照同时说明：这一屏的差异不来自后端代码版本。图在 `face_user_4781_served-generation.png` 与 `face_lane_canary_same_generation.png`。

**顺带量到一件必须说的事**：用户手机此刻那张卡**仍然是英文的** `Trip evidence needs re-syncing`。本单的修复在 r3 候选产物里已经生效（同屏中文，见 `candidate_studio_trial.png` 与下方原文），但它还没上线——落地与上线是两格，这一格只有你动。

## 链路实际终点（与 r1/r2 同，换代没让它变好）

- 舞台「请求重规划」→ `POST .../replans` HTTP 422，`error.message` 为裸 `MOBILITY_DATA_UNAVAILABLE`，`details.gaps` 单条 `FACT_PRESENT_BUT_NOT_HARD_ELIGIBLE`；发射器 `backend/app/main.py:5513`。⇒ 外部条件，产品码改不了事实，只改说法。
- 工作室「预览影响」→ HTTP 200 且 `can_accept` 为假：这一版 5 个活动全是受保护锚点（`frontend/src/features/studio/V12TripStudioPanel.tsx:54`、`:59`）。
- 因此实时屏无 proposal、`live-accept` 不在屏上；接受腿的产品码只有既有门 `frontend/e2e/golden.spec.ts:55` 在 fixture 后端上覆盖。

## 修后同一格的渲染原文（r3 候选面，逐字）

- 舞台：「重算这一版需要能当作硬依据的路线证据。服务器说这些路程 1 段的证据在档，但达不到可硬用的标准（它给的码：MOBILITY_DATA_UNAVAILABLE，证据状态 FACT_PRESENT_BUT_NOT_HARD_ELIGIBLE）。所以它没有算出任何替代方案，你现在的方案没有变化——这一步要接上真实的路线数据源才会通。」
- 工作室：「这次改动不能被接受的原因：新的顺序挪动了受保护的承诺 / 这一版在新顺序上没有冻结的路线证据 / 冻结证据在能被使用之前就已经过期 / 新顺序里有 4 段路程拿不到实时路线数据」，末行「冻结证据 v12-stay-ad07a1aeb7f6eac534b8c64b4b745f13 · 成本变化 -¥24.00 · 时间变化 495 分钟」；原 token 与 4 对段号只出现在「技术详情」折叠里。
- 证据过期卡：「这趟行程的出行证据需要重新同步」「服务器针对这一版列出了 1 条拒绝，原文在技术详情里。」「服务器拒绝了这次生成（HTTP 422，具名 VALIDATION_ERROR）。没有任何方案被改动。」该态下不再挂载一枚必然 404 的确认按钮，改说「这趟行程现在没有等待确认的恢复决定…选定一份通过校验的方案后这条提醒才会消失。」

## 门禁（r3 代次，19 条同一次跑）

`frontend/e2e/qoder-ord0369-replan-walkthrough.spec.ts` 13 条（A1-A4 卡 / B1-B4 工作室 / C1 舞台 / E1-E4 AI 归属），
外加两条**别人的已验收门**做回归：`qoder-model-words-are-labelled.spec.ts` 3 条（ORD-0240）、`qoder-ord0373-name-hit-scope.spec.ts` 3 条（ORD-0373）。
报告 `gate-report-r3-with-regressions.json`：`expected 19 / unexpected 0 / skipped 0 / flaky 0`，用时 35868.7 毫秒。
没有 mock 产物、没有 skip、没有改任何现有断言换绿；`skipped 0` 写在报告 `stats` 里可复算。

## 合并树本身的编译读数（给落地门的编译臂，不是我这枝的）

你 03:2x 要的是 rebase 后的编译证据；我这一枝对现尖的产品码差异为零，所以更有用的读数是**你实际会落的那棵树**能不能编译。做法：`git merge-tree --write-tree 090c048f220a3089506f565929ceda1511315a09 ae9f2d8db3832d86563255fcaed065d0f421ab0d` 退出码 0、零冲突，产出树 `0d82103f981989c5fa0a6aff0dc7c3d9214a9bbc`；把这棵树的 `frontend/src` 与 `frontend/e2e` 取进既有硬链接导出目录（**没有建链接**：中途一次 `ln -s` 我事后量到它是真目录、`st_file_attributes` 为 0x10 而非 reparse 的 0x400，依赖本体 `typescript/package.json` 的 nlink 仍为 13、子项 399 枚未受损），然后：

- `tsc --noEmit` 退出码 0，见 `review/ord0369-phone-replan/MERGED_BUILD_EVIDENCE.txt:4`（同件第 5 行记 stdout 为 0 字节，即干净跑的形状）。
- `vite build` 退出码 0，用时 9.73 秒，见 `review/ord0369-phone-replan/MERGED_BUILD_EVIDENCE.txt:10`；预缓存 8 条，见 `review/ord0369-phone-replan/MERGED_BUILD_EVIDENCE.txt:11`。
- 对照：我这枝自己那棵树的构建是 13.84 秒、预缓存 8 条（本文第 18 行），产物名同为 `index-D-tB4NCX.js`。
- 跑完已把导出目录从 git 工作树重新同步回本枝源码（195 个文件、`tsc` 再跑退出码 0），工作树 `git status --porcelain` 为 0 行。
