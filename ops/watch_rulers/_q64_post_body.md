**S1-q64sweep → 号令者：Q64 尺 r2 全前端树清扫已交（量具读数，0 改产品字节）**

权威尖 generation = {{TIP}}（开单与收尾各读一次 `git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`，同一枚，件内 `tip_moved=False`）。账本镜像 blob {{LEDGER}}。

**上架（两条路径均为 CREATED，0 覆盖，只走 publish_evidence_gated_r1.py）**

- `commander/control:evidence/q64-sweep-S1/sweep_r1.json` = blob f783b12eea629d52dbe8ff00f45716d50b99e30c，publish commit 09c56540df86a4bb205d8a3795de200c3a23f08e，proof BYTE-LEVEL MATCH
- 独立回读走第二扇门：`git fetch origin refs/heads/commander/control:refs/remotes/origin/cmdcontrol` 后 `git rev-parse origin/cmdcontrol:evidence/q64-sweep-S1/sweep_r1.json` = f783b12eea629d52dbe8ff00f45716d50b99e30c，与本地 sha1-over-bytes、`git hash-object` 三处全等
- 回读收据 = `commander/control:evidence/q64-sweep-S1/readback_proof_r1.json` blob d15fd4430b74d410c32cc486601c97486bec669a，commit 38c0778c3e5e07cc3910a4031c80c1dd04397c79，`rev-parse` 回读同值，verdict READBACK_CONCORDANT（件不能自存自身 blob，故号记在旁边这件里）

**量具** 尺 = blob 608016f6a538097041554b76cfe3e9a4192f299c，本地 `git hash-object` 与 `git rev-parse origin/commander/control:evidence/cmdr-ui-exposure-r2-0059/ui_exposure_field_check_r2.py` 同值；`--selftest` = SELFTEST_PASS，夹具 8 枚中 5 红 3 净，逐条 assertion_met=True。

**方法** 尺本体逐文件调用 `--ref <generation> --path frontend/src/... --out <scratch>.json`，未 import 尺、未重写正则；尺经 `git show` 取字节，输入是尖的提交对象而非工作树。枚举 `git ls-tree -r --name-only` 的 .ts/.tsx 计 files_scanned=74，files_failed=0；`node_modules`/`dist`/`frontend/node_modules`(junction) 未扫未碰；旁证 `git archive` 导出后 find 亦 74。

**读数** files_with_hits=12，hits_total=25（UPSTREAM_READ_DIRECT 21、UPSTREAM_TEXT_VIA_HELPER_TO_DOM 1、RAW_BODY_TO_DOM 1、RAW_TEXT_INTERPOLATION 1、UPSTREAM_EXCEPTION_TO_DOM 1）。分类由我逐格读落点行得出：upstream_prose 16、local_wording 6、machine_label 3。

**两向自检** baseline_reproduced=True：`frontend/src/features/planning/PlanWithAiSheet.tsx` 仍 1 命中，规则 UPSTREAM_TEXT_VIA_HELPER_TO_DOM、行 :1016、链 serverReasonSentence → failureReason，blob 3bb6a39067a380c2f75629fd7562f0de8f5d2f2a 全等。negative_control_clean=True：具名负控 `frontend/src/lib/money.ts`（币制算术，全文无 fetch/axios/detail/body/message 痕迹）= NO_EXPOSURE_SHAPE_FOUND，命中 0。verdict=SWEEP_VALID，由这两格派生。

**上游正文进 DOM 的集中点** `frontend/src/features/inbox/JourneyInboxWorkbench.tsx:88` 一枚 throw 把 `payload.error.message` / `payload.detail` 塞进 `error.message`，供 9 枚命中同源使用，出屏在 :687、:731、:691。另 `frontend/src/app/V8Experience.tsx:169` 的 rejectionReason 逐字取 `body.detail`，渲染 :1562；`PlanComparison.tsx:95` → :260；`HotelsPanel.tsx:104` 的 `raw ||` 在未映射码时漏原话 → :229；`ProductErrorBoundary.tsx:104` 连 React 的组件栈 `info`（:105）一起进 pre；`AgentComposer.tsx:95` 与 `CopilotDock.tsx:615` 是 CopilotResponse.message（api/citynexus.ts:384、:908）设计内模型答复通道，我单列供你另行裁决。对照组：`frontend/src/features/execution/LiveRecovery.tsx:234` 虽直读上游，但过 :68 humanReplanReason 的四码白名单、:90 未映射即回本机句子 ⇒ 判 local_wording，闸门在这条路上是在的。

**给你量具的三样读数（我没改尺）**

- r2 报的行是匹配起始花括号所在行：25 枚中 16 枚的 snippet 实为 `} catch (error) {`、`} else {`、`if (!r.ok) {`，覆盖 6 文件（按尺自己的 snippet 字段实数）。所以我给每格另附按行号从尖树机器抽取的 basis 原文。
- 1 枚打在注释上：`V8Experience.tsx:320` 的 `\braw\b.*\bslice\(` 吃到 317-326 的 JSDoc 散文，永不进 DOM。
- 反向漏报：`main.tsx:1063`、`main.tsx:1064`、`main.tsx:1074`、`main.tsx:1421` 把 `agentRun.outcome`、`agentRun.failure_reason`、`step.result.error`、`item.explanation` 这些服务器列直进 DOM，r2 不响。我没把它们计进 hits_total（该数只由尺派生），单列在件的 adjacent_findings。

**边界** 0 改产品字节（交付前 `git status --porcelain frontend` 读回 0 行）、0 推权威分支、未跑 demo/reset、未碰 `*_live.db`/`*_preview.db`、未跑 vite build、未读未打印任何凭据。同检出内 `backend/app/main.py` 与 `backend/app/agent/runtime_identity.py` 的 modified 及根目录 `_ctrl_log.txt` 等未跟踪文件是别的车道既有状态，非本趟产生（R14 先说明）。

**账本块** `D:\moodle\_qoder_ledger_inbox\S1-q64sweep_0254.md`，首行 `### `，自跑 Q43 r4c = Q43_GATE_GREEN（claims checked 14，findings 0）。

**下一步归属** 16 枚 upstream_prose 是否各配闸门归裁决与实现车道；本车道为量具，未开修复。若要 r3，上面三样读数即夹具输入。
