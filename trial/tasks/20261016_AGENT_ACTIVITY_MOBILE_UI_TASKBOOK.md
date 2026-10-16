# CityNexus Revolution · Mobile Agent Activity UI (Hermes Runtime Transparency)

**Date:** 2026-10-16  
**Parent:** `trial/tasks/20261016_REVOLUTION_MOBILE_FIRST_V1_EXECUTION.md`  
**Branch:** `design/revolution-mobile-first-v1`  
**Owners:** Codex implements end-to-end; Qoder can identify reuse points, cannot concurrently rewrite the same branch.  
**Priority:** P1 immediately after fixing mobile shell and basic user navigation; this is core UX, not optional observability/developer-console garnish.

## Why this is a product feature

The traveler must always be able to tell what CityNexus is doing: receiving intent, waiting for a model, searching real venues, consulting route or venue evidence, making a recommendation, waiting for permission, failing, recovering or being idle. An inexplicable spinner (or generic "AI configured") is unacceptable. The user specifically wants a modern **mobile Agent UI resembling DSH's conversation/trajectory dual view**, with **tool cards and an activity log**.

This is **not** a request to dump private model chain-of-thought or full tool arguments. Show **audited, user-safe decision summaries** and actual tool events. Do not generate fake reasoning sentences or inferred tool progress; do not disguise a read-only model category suggestion as a durable AgentRun.

## Repo archaeology: actual EXISTING capabilities (read before writing a framework)

**Current frontend**:
- `frontend/src/features/agent/AgentRunRail.tsx`: already has pending/active/done/approval/failed visible rail.
- `frontend/src/features/agent/CopilotDock.tsx`:
  - `NativeMissionTimeline` currently fetches `getNativeHermesTimeline(journeyId,runId)`, opens `EventSource(run.events_url)`, attaches named lifecycle/tool event listeners, deduplicates by event key and polls `getNativeHermesRun` for terminal status.
  - Already renders real `run.started / tool.started / tool.completed / tool.failed / approval.required / proposal.created / run.completed / run.failed / run.stopped` and offers existing governed stop + approval behavior. Also includes mission_plan steps. Avoid rebuilding this event model.
  - Review privacy risk of caching native timeline by just `journeyId+runId` in `localStorage`; in the signed multi-traveler trial, never replay member A's data into member B after bearer switch. Avoid storing private inputs/outputs locally. Treat server events as authority.
- `frontend/src/api/citynexus.ts`: `AgentRun`, `AgentRunStep`, `AgentMission` (`reasoning_summary`), `NativeRuntimeEvent`, `AgentFeedEntry`, `getNativeHermesRun`, `getNativeHermesTimeline`, `stopNativeHermesRun`, `getAgentFeed`, `getAgentRun`, `runAgentCommand`.
- `frontend/src/trial/RevolutionFirstLook.tsx`: NEW 3-tab Explore/Trips/Me shell; DRAFT `RevolutionQuickExplore`, ACTIVE real `LiveRecovery`. Do not pretend the ACTIVE agent comes from the DRAFT guide.
- `trial/agent_preview_app.py`: `POST /trial-ai-discovery` is a one-request **read-only Hermes-compatible structured category suggestion** on a signed DRAFT. This can have authentic local phase labels (user clicked / request sent / pending / response) but **NO persistent AgentRun**.

**Current backend**:
- `backend/app/agent/runtime_events.py`: canonical Hermes normalization with allowlisted lifecycle/tool events and bounded result metadata. Explicitly drops `reasoning.available`, `reasoning.delta`, `message.delta` and free-form tool/model prose to protect private chain-of-thought and credentials. **Do not undo this protection**.
- `backend/app/agent/mission.py`: `AgentMission.reasoning_summary` is intended as a **user-safe decision summary**, separate from raw private chain-of-thought. Surface it only if it is actually returned for the same authorized Mission/Run.
- `backend/app/agent/gateway.py`: mission tool gateway and approval semantics remain the authority. **No approval via visual-only state changes.**

### Important security audit BEFORE transport reuse
- The old V8 `NativeMissionTimeline` uses `EventSource(url)` with no custom Authorization header (EventSource cannot set one). Verify how `events_url` is scoped and authenticated before embedding it into signed, multi-member mobile trial. A convenient event URL must never leak other members' tool facts.
- Do not trust `run_id` or `trace_id` pulled from localStorage or an unbound global 'latest'. Run must be authorized to the current signed member and Journey. If no current-run-list contract exists, add a **narrow signed read-only server projection** returning allowed `run_id / mission_id / status / safe summary / events`, or bind a newly initiated run to the UI via server response. Never guess one from timestamp alone.
- SSE reconnection: support bounded retry and authenticated history reconciliation by event sequence or event_id; avoid duplicate/reordered events and infinite polling. On 401/403 drop cached private data and close the stream. On offline show last VERIFIED server event and "连接中断，等待恢复", not "AI still thinking" indefinitely.

## OSS references (look and borrow ideas, not an entire engine)

1. **DSHA** `https://github.com/SingalongDan/dsha`, especially `dsh-web-vs-android.md` and `dsh-android-app-design.md`: *conversation/trajectory two-view navigation*, mobile drawer, queued/injected prompts shown only while busy, per-tool fold, execution duration, and permissions attached to actions. **AGPL-3.0 repo**: for closed/other-licensed CityNexus use inspiration rather than copying sources/assets without license review.
2. **Rish** `https://github.com/ZSeven-W/rish-app` MIT, specifically `apps/mobile/src/components/{agentActivityProjection.ts,toolActivityProjection.ts,MessageList.tsx,StructuredContent.tsx,ApprovalComposer.tsx,RuntimeEvidenceSheet.tsx}`: sequence-aware tool-call-to-result matching, error/denial semantics, safe runtime evidence, actionable approve/refuse UI. It explicitly states **no stable installable release**; use patterns, not proof of mature runtime.
3. **Soodok DSH Mobile** `https://github.com/Soodok/Deepseek-Harness-Local-Android` MIT: Android shell around DSH engine/WebUI, notification and background run status reference, but **not** a React PWA UI library; don't embed Android Node runtime into CityNexus.
4. **OpenHands Mobile** `https://github.com/OpenHands/openhands-mobile` MIT: phone conversation layout and REST-history-plus-WebSocket reconnection; presently early MVP and not a full mature tool-control console.
5. **assistant-ui** `https://github.com/assistant-ui/assistant-ui` MIT: frontend tool-call card lifecycle `running/complete/error/requires-action`, inline result, user approval, typed rendering. Do not replace the whole CityNexus React app to show existing events. Note that standalone `assistant-ui/tool-ui` repository is archived since 2026-09-26: borrow concepts from active `assistant-ui` instead.
6. **AG-UI protocol / CopilotKit** `https://github.com/ag-ui-protocol/ag-ui`, `https://github.com/CopilotKit/CopilotKit` MIT: future protocol adapter options; map your **existing** event contract to `RUN_STARTED/TOOL_CALL_START/TOOL_CALL_RESULT/RUN_FINISHED` only in an optional adapter. Do not alter Gateway/AgentRun to conform just for a pretty screen.
7. **Open WebUI** `https://github.com/open-webui/open-webui`: review known user complaints about invisible tool-call progress as a negative UX example, not a copy/paste dependency.

## UI: concrete first visual slice

On mobile `/revolution`, when a REAL run exists, put a **small persistent, dismissible-by-collapse but not destructive** active-work chip near the bottom ABOVE `RevolutionMobileNav`:

> 🟢 CityNexus 正在处理 · 核查附近地点 · 已用 18 秒  
> [查看工作过程]

Only the currently observed tool/event and real elapsed time appear. No imaginary percent complete and no indefinite "思考中".

When opened, show a **mobile bottom sheet / full-height narrow drawer**, separate from chat composer keyboard, three information levels:

**L0 (always visible):** user-safe current phase (preparing / querying exact provider / checking evidence / waiting approval / done / error / offline), last real update time, stop/retry/approval CTA if actually supported.

**L1 (tap to expand):** vertical timeline (last 3 expanded, older events folded):
- ✅ 已理解你的需求: based on real `semantic.interpreted` event
- ✅ 已调用地点搜索: based on real `tool.completed` with known tool name/source
- 🔄 正在核实地点信息: **only** if a current started tool event is still unmatched and server run is active
- ⏳ 等待你确认方案: based on `approval.required` with current authorized pending approval
- ⚠️ 当前服务超时 / 可重试: exact backend failure; never infer success
- ✅ 已生成建议: `proposal.created` without asserting accepted/apply plan

**L2 (opt-in '运行记录'):** chronological sanitized tool cards: public provider (if recorded), tool name mapped to natural Chinese, start/end timestamps, duration, safe outcome, approved/pending/blocked. Show only allowlisted fields, never raw tool arguments, HTML, raw model reasoning tokens, credentials, private addresses, or other member's data.

For "思考过程", show **"工作思路 / 判断依据"** from the server's real `mission.reasoning_summary` and verified plan/evidence links where available. If absent: display "暂时没有可公开的判断说明". **No synthetic chain-of-thought**, no fabricated 'I searched...' messages.

### DRAFT vs ACTIVE truth

- `DRAFT` model-only `suggestTrialDiscovery()`: can display UI lifecycle like "已向 AI 提交你的想法 → 等待回复 → 已收到兴趣建议/失败". Label **"AI 兴趣建议（未创建正式执行任务）"**. Never say "调用地图工具" when the model only emitted `propose_public_discovery` schema. Provider POI searches are independent user-triggered operations, not AgentRun steps.
- `ACTIVE` persisted AgentRun from original Journey Operator: show REAL run status/actual tools/approval with server history, guarded by signed member context. Do not display demo-only fake events in live runtime.

### Button and permission truth

- Approve / refuse / stop must call **original authenticated governed** Gateway/approval endpoints, never fake an action in React state.
- If unknown / unauthorized / stale approval: do not display active approval button; offer review in original Authoritative/Recovery center instead.
- Navigating Explore ↔ Trips ↔ Me must not generate new AgentRun, user consent, tool calls, paid model requests, or reset backend progress.

## Implementation stages (Codex, exact deliverables)

**A0: Audit + first working strip (fast, code-first).** `trial/mobile/AgentWorkStatus.tsx` or `frontend/src/trial/mobile/AgentWorkStatus.tsx`, read-only presentation backed by true current run events. Add to mobile ACTIVE Journey in Trips. If no run exists, render "AI 当前没有执行中的任务" without spinning; distinguish configured-only. Reuse `NativeMissionTimeline` event projection instead of copy/pasting SSE client code.

**A1: True details sheet.** Extract shared `useAuthorizedAgentTimeline` hook from V8 `NativeMissionTimeline` rather than creating a second incompatible SSE/event dedup engine. Move RunRail/ToolCard to source-filtered mobile view; a light CSS drawer fallback must work even if modal sheet library is unavailable.

**A2: Human-readable trace/approval.** Show mission summary, non-sensitive tool metadata, failed/blocked/approved, explicit server-run-to-member binding. Implement real pause/stop and approval only if current endpoints authenticate current member.

**A3: Regression + phone acceptance.**
- 390×844 and 430×932 touch: collapsed strip, expanded sheet, scroll, close, keyboard, safe-area over bottom tab bar.
- Actual signed two-member backend: member B gets **403/empty** for member A's run history, stale events from member A disappear immediately on bearer switch.
- SSE same event reconnect and replay show exactly one tool row; out-of-order events sorted by sequence, no fabricated "complete".
- Run start after navigating away and back: persisted same run; no new POST triggered. Offline reconnect + 401/403 user-friendly recovery.
- Pending approval cannot be bypassed by a UI button; failed runtime is visibly failed, not fake "thinking".
- Model-only DRAFT call must NEVER appear as persisted AgentRun, even if same model/provider was used.
- Capture actual phone viewport video/screenshot of **real signed run**, not only fixtures. Evidence grade FULL_OPERATOR / MODEL_TOOL / UI_FIXTURE and live-provider labels must remain independent.

## Completion and Codex handoff

Write `trial/results/20261016_AGENT_ACTIVITY_MOBILE_RESULT.md` with first line:
`VISIBLE_VERIFIED_RUN = YES/NO/PARTIAL` then hard evidence: run_id (safe/truncated), displayed event types/sequence, tool statuses, approvals, SSE reconnect, signed member isolation, actual screenshots, model/provider proof separately.

PR base remains `fix/revolution-first-human-e2e-20261015` via existing **draft PR #23**. Coordinate with current Issue #21; do not open another "revolution" branch or conflate feature with Qoder mainline integration. Do not let a plan displace implementation.

**Do not claim this feature is already live. This document is a precise build task for Codex; present repositories are references, not imported dependencies.**
