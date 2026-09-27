# ORD-0369 r2 · 手机端 Replan 真链路读数（lane Q，2026-09-28 02:4x +08）

代次：base `961836390c5325863acdc1834d4a4cd16fd97081`（退回重应用后的权威尖），分支 `review/Q-ord0369-replan-walkthrough-r2`。
第一版（base `4ef864cfa49b805e3d41b7f079f5fb4184ccec3d`）按 Q72 退回自基，已推的 `review/Q-ord0369-replan-walkthrough` 不覆盖（Q57）。

## 重基时撞上的两件事（机械 rebase 抓不到，所以单独记）

1. **AI 那批 cherry-pick 干净通过，因此是错的。** 我的来源映射键在 `READY` 上，而 ORD-0359 已经把这个 token 改名成 `CONFIGURED_UNVERIFIED`，理由写在 `backend/app/agent/ai_availability.py:36-44`：「a key exists」不等于"能用"。若把 `CONFIGURED_UNVERIFIED` 读成"模型写过这句"，就是在 0359 关掉的那个洞之上再开一层。现在只有 `PROVIDER_REFUSED`（唯一说明提供方真被触达并答过话的状态）保留模型归属；`DISABLED_BY_OPS`/`NOT_CONFIGURED` 判 no_model；其余（含状态缺席）保持既有标签。新增 E4 臂把 `CONFIGURED_UNVERIFIED → not_stated` 钉住。
2. **唯一真冲突就是 0370 动过的那一行。** 它已经把裸 `"pending"` 换成 `t("studio.snapshotPending")`（en `frontend/src/i18n/LocaleContext.tsx:683`、zh `frontend/src/i18n/LocaleContext.tsx:1437`）。解法保留它的取词，把我这单的钱位/时长格式化接在其上，不是盖掉。

顺手补一个我自己开的洞：替换 token 行之后 `studio.gateFailed` 在全树（ts/tsx/py/cjs）无任何读者，已从两份字典删除；原因清单补了领句「这次改动不能被接受的原因：」，并在 B2 臂里断言——断言即"这个键真被读到"的证明，比 grep 强。

## 面与构建前置（FRONTSRC_BUILD_PREREQ）

- `tsc --noEmit`（`tsconfig.typecheck.json`，`include: src/**/*.ts(x)`）rc=0；`--listFiles` 回读 875 个文件，含我改的 4 个源文件（不是 0 文件空转的绿）。
- `vite build` rc=0，10.36 秒，precache 8 条，产物 `assets/index-DUX9Q9Ho.js`。
- 两者都跑在既有导出目录（`node_modules` 为硬链接件），**没有新建任何 junction**。

## canary 替身证明（重做到当前在服的那一代）

预览链在本单中途又换过一次代：号令者 01:13 记的是 `index-BEEP22s_.js`，我 02:3x 用 `live_checks/cmdr_tunnel_read_r1.py` 量到在服的是 `index-B800Wnn2.js` + `index-240iHFm5.css`。所以旧的字节相等只描述一个没人再服的 bundle，我重做了：

- 把在服根目录 `index.html` 与本车道副本逐字节比对：同一 sha256 前 16 位 `9545404149b578a4`（副本是 `shutil.copy2` 真复制，不是链接进被服目录）。
- 同一屏（`/v8/authoritative`，390×844）在两个面上各截一张：用户可见面 `:4782` 与车道替身面 `:4189`（同一代 bundle + 本单车道后端 + 本次新做的 `Connection.backup()` 私有库）。两张 PNG **字节相同**：`351517` B、sha256 前 16 位 `f113ffb86520eedb`，读数在 `canary_proof_r2.json`，图在 `face_user_4782_deployed-generation.png` 与 `face_lane_canary_same_generation.png`。
- 值 `f113ffb86520eedb` 与第一版同一屏同值，说明这一屏在这次换代前后像素未变。

## 链路实际终点（与第一版同，未因换代而变好）

- 舞台「请求重规划」→ `POST .../replans` HTTP 422，`error.message` 为裸 `MOBILITY_DATA_UNAVAILABLE`，`details.gaps` 一条 `FACT_PRESENT_BUT_NOT_HARD_ELIGIBLE`。发射器 `backend/app/main.py:5513`。⇒ 外部条件。
- 工作室「预览影响」→ HTTP 200 且 `can_accept` 为假：这一版 5 个活动全是受保护锚点。
- 因此实时屏无 proposal，`live-accept` 不在屏上。接受腿的产品码仍由既有门 `frontend/e2e/golden.spec.ts:55` 在 fixture 后端上覆盖，不算本单新交的证。

## 修后同格的渲染原文（r2 候选面，逐字）

- 舞台：「重算这一版需要能当作硬依据的路线证据。服务器说这些路程 1 段的证据在档，但达不到可硬用的标准（它给的码：MOBILITY_DATA_UNAVAILABLE，证据状态 FACT_PRESENT_BUT_NOT_HARD_ELIGIBLE）。所以它没有算出任何替代方案，你现在的方案没有变化——这一步要接上真实的路线数据源才会通。」
- 工作室：「这次改动不能被接受的原因：新的顺序挪动了受保护的承诺 / 这一版在新顺序上没有冻结的路线证据 / 冻结证据在能被使用之前就已经过期 / 新顺序里有 4 段路程拿不到实时路线数据」＋「冻结证据 v12-stay-ad07a1aeb7f6eac534b8c64b4b745f13 · 成本变化 -¥24.00 · 时间变化 495 分钟」，原 token 与段号只在「技术详情」折叠里。图 `r2_candidate_studio_trial.png`、`r2_candidate_stage_refusal.png`。
- AI 面（开关关着）：预检「这台服务的 AI 开关处于关闭状态，这是运营侧的设置，不是你的操作结果。开关本身不代表某次失败的原因。」；提交后回执「服务器拒绝了这次生成（HTTP 422，具名 VALIDATION_ERROR）。没有任何方案被改动。」

## 门禁（新代次重跑）

`frontend/e2e/qoder-ord0369-replan-walkthrough.spec.ts` 13 条（A1-A4 卡、B1-B4 工作室、C1 舞台、E1-E4 AI 归属），
与 ORD-0240 那 3 条已验收臂同栈同一次跑：`gate-report-r2-with-ord0240.json`，`stats` = expected 16 / unexpected 0 / skipped 0 / flaky 0，29870.2 毫秒。
只跑本单 13 条那一次：`gate-report-r2.json`，expected 13 / unexpected 0 / skipped 0，32373.2 毫秒。
`ord0240-1..3` 三条状态全为 expected ⇒ 那条已验收的门一字未动仍然绿。
