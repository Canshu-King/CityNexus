# Current active work order: CityNexus Revolution V3 | Qoder sole owner | 2026-10-22

**Branch scope: rescue/v3-final-departure-20261022. Qoder is the sole implementation owner for this branch, not Codex.**

The old AGENTS.md message named Codex as owner and Qoder as a non-editing reviewer. That message belonged to the historical Mobile-First V1 phase and has been superseded by the user's explicit 2026-10-22 instructions. Keep the historical taskbooks as provenance; do not follow their outdated ownership instructions on this branch.

## Read before editing

- Current user priority: trial/tasks/20261022_QODER_CHROME_USE_HUMAN_FIRST_ACCEPTANCE.md
- Full handover and all V3 responsibilities: docs/revolution/QODER_SINGLE_OWNER_V3_EXECUTION_20261022.md
- Recent real reports: trial/results/20261022_V3_AGENT_HALFDAY_PRESS.md and trial/results/20261022_V3_REAL_CITY_BEIJING_PRESS.md
- Verified original design reference: docs/revolution/v3-design/
- GitHub task owner: Issue #42; product PR: #43 (rescue -> design/revolution-mobile-first-v1).
- Original Codex product PR #23 and original Qoder adapter PR #35 are preserved; do not force push or merge either whole branch.

## CRITICAL: browser-first implementation, not green-test-first

The user specifically requests that Qoder control **real Chrome** through **chrome-use** and act like a human using the CityNexus app.

1. **Use the chrome-use CLI from Qoder's terminal for real-browser tasks when installed; start with chrome-use skills get core, and check chrome-use status.** Connect an isolated project Chrome session/profile, not the user's personal tabs or financial/password pages. Consult installed CLI version and official documentation before choosing flags. If chrome-use is unavailable in this Qoder installation, use Qoder's supported real-Chrome Browser Agent (/browser) / Computer Use, and name the fallback and why. Never pretend it is connected until a real screenshot and click are recorded.
2. Open the actual app entry, inspect the screen like a first-time traveller, click/scroll/type and observe the result. No direct API calls, artificial localStorage seeding, pre-built success data, tests or DOM injection as substitutes for a user's click; setup of an isolated signed test environment is permitted and must be explicitly disclosed.
3. Work in cycles: real visible blocker -> before screenshot -> fix product code -> use real Chrome again -> after screenshot -> push. Automated backend/Playwright checks remain supplemental regression gates, never the only result.
4. Test one future-dated natural language goal on **the same Journey** from Agent conversation through grounded research, A/B/C, natural-language half-day change, reload, formal departure and ACTIVE. An unrelated mock-city successful start does NOT prove this flow. Respect genuine provider failures and keep UNKNOWN distinct from verified.
5. Require a human-readable browser walkthrough and a simple <10-step user tutorial. Keep USER_VERIFIED=PENDING until the user personally operates a real phone.

## Product intent and non-negotiable correctness

- Keep a modern mobile app: Explore / My Trip / Me, exactly one obvious Agent entry, visible live task/tool progress, usable images, interactive map and user-controlled itinerary. Put raw engine names, audit details and advanced tools in expandable diagnostics rather than the main screen.
- Preserve authenticated Journey/task/member identity, signed transitions, revision/idempotency, provider permissions, PlanVersion authority and genuine Guardian receipts. No fake AgentRun or thought trace. No mock provider fact advertised as live. No suggestion/hotel recommendation masquerading as confirmed purchase/booking; no physical arrival without authenticated evidence.
- Group consent in original V3 reference: with three required authorised members, two approvals do not change shared PlanVersion; each person consents under their own principal, and a full set still goes through the actual plan feasibility/authority writer. Resolve the practical ACL/consent-eligibility issue without handing everyone unrestricted plan-write permission.
- Frontend React 19 / Vite 7 includes lucide-react and MapLibre. Avoid blind incompatible dependency installs, global CSS battles, or rebuilds from static HTML. Check mobile 390x844 and 430x932, keyboard, back navigation, and desktop view in actual Chrome.
- Protect existing real SQLite, trial/.runtime, keys, live accounts and running services; test on separate canary DB and appropriate local credentials. Do not repeat unauthorized paid provider usage or send invitations/purchases. No destructive reset/force push.
- Do not fabricate current readiness: current #43 has browser-proven plan SELECTED/ACTIVE on offline catalogue and actual Agent discussion, but the entire live-source Agent-to-ACTIVE one-Journey flow remains unverified. Human manual half-day edit != Agent local replan.
- Incremental **working product** commits go to rescue branch and PR #43. Attach before/after browser screenshots, same journey/task IDs (redacted if sensitive), API response evidence with tokens redacted, source provenance and genuine blockers in Issue #42.

**Never substitute numerous green backend tests, more R-series paperwork, or cosmetic copy cleanups for a usable travel app.**
