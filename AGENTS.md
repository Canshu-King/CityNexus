# Active work order: Revolution Mobile-First V1

**Scope of this AGENTS.md: `design/revolution-mobile-first-v1` only.**

The user repeatedly tried the Revolution Lab on desktop and phone and reported that it looks like a developer test console rather than a mainstream mobile travel app: giant full-width buttons, scrolling walls of text, map/consent dead ends, technical statuses and an AI system invisible to the user. They explicitly ordered immediate construction, not another planning loop.

**Codex is the implementation owner. Do the coding.**

Read the binding taskbook:
`trial/tasks/20261016_REVOLUTION_MOBILE_FIRST_V1_EXECUTION.md`.

**Additional product mandate (Issue #24):** Real mobile Agent work transparency, not a decorative "thinking" spinner. Read `trial/tasks/20261016_AGENT_ACTIVITY_MOBILE_UI_TASKBOOK.md`. GPT has already committed `frontend/src/trial/mobile/AgentWorkStatus.tsx` plus CSS, mounted on the ACTIVE Journey Trips screen and backed by signed `GET /journeys/:id/operator`. Continue it into real, run-bound Hermes tool events by extracting the existing `NativeMissionTimeline` SSE projection from `CopilotDock.tsx`; DO NOT introduce a duplicate Agent backend. Preserve authority, no fake AgentRun, no raw model chain-of-thought and no other member's timeline.

- GitHub repo: `Canshu-King/CityNexus`. This branch was created from the completed first-human failure rescue branch `fix/revolution-first-human-e2e-20261015`, whose PR #20 is still open. **Target the fix branch as the base of the new design PR, not commander/control and not the stale default branch.**
- New code already on this branch: `RevolutionMobileNav.tsx`, `RevolutionMobileV1.css`, revised `RevolutionFirstLook.tsx`, and signed server Pocket Walk state propagation in `RevolutionQuickExplore.tsx`. Verify the real build and browser behavior immediately, fix issues and complete actual mobile screens.
- Priority = product surface: attractive, cohesive, mobile-friendly Explore / Trip / Me + natural language AI entry / sourceful place cards / walk. Fix real bugs before writing extra plans or verifier reports. Get 390x844 and 430x932 real browser screenshots.
- The full frontend React 19/Vite 7 stack has `lucide-react` and MapLibre installed. Do not blindly install Ant Design Mobile v5: its React 19 compatibility instructions require a special render adapter. Run an isolated proof first; React Modal Sheet also requires Motion and touch/StrictMode verification.
- One clear primary action per screen, natural Chinese, zero global changes to Qoder styles, no `!important` proliferation. Fix the existing global CSS conflicts incrementally, keeping this trial isolated.
- Treat `HERMES_COMPAT_ENDPOINT` as CONFIGURED, not successful AgentRun. Keep authenticated Journey, per-member pocket walk, provider consent, UNKNOWN/LIVE/TEST provenance and self-report-vs-GPS boundaries unaltered.
- Do not mutate user `trial/.runtime`, real SQLite, local npm lockfile fixes, keys, wallet, payment or Qoder deployment. For tests, create an isolated signed test backend and fixture DB. Avoid repeated paid/real provider calls.
- Bring back accurate results: typecheck/build, Playwright desktop + mobile, touch/tabs/keyboard, signed server Pocket Walk restore, provider-down fallback. All unverified evidence stays NOT_VERIFIED.
- Commit and push incremental **working product** code. Open/maintain the design PR targeting `fix/revolution-first-human-e2e-20261015`. First line of outcome `trial/results/20261016_MOBILE_FIRST_V1_RESULT.md` must say whether a real human can use it, and precisely which step remains blocked.
- Qoder is a non-editing integration reviewer this round. Specific shared components can be recommended, but both agents must not concurrently rewrite the same branch.

**Stop treating test counts, architecture docs and R-series cycles as a substitute for a functioning travel app.**
