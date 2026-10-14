# Revolution first-user UI rescue — 2026-10-15

## Why this exists
A real user's 2026-10-15 screenshots showed: "连城，从这里开始。" forced into a one-character-wide column, the "换一个地区" button spanning most of the content width, all of the R107/R108 BootstrapDiscoveryPanel internal provenance/debug paragraphs shown at once, massive blue V8-width buttons, bilingual developer copy, and no obvious way to advance.

The user should not have to read raw protocol diagnostics or type WGS84 coordinates just to find a local place. This is an observed product regression, not a lack of user training.

## What was actually changed in GitHub
- `frontend/src/trial/RevolutionFirstLook.tsx`: new `RevolutionGuide` and collapsed native discovery details. Original signed discovery and GO MODE remain mounted/functional.
- `frontend/src/trial/RevolutionGuide.tsx`: 3 actionable choices that explicitly reveal/focus existing (NOT fake) native controls:
  (1) choose a public map search center; (2) select an interest and authorize one external search; (3) select two actual returned candidates and save GO walk. No programmatic granting of location, model, payment, provider or member permission.
- `frontend/src/trial/RevolutionUsability.css`: scoped fixes to the collapsed heading and giant buttons, 3-step layout, readable forms, smaller type, mobile behavior, accessible high-contrast controls. No Qoder/mainline CSS changes.
- `frontend/src/features/discovery/BootstrapDiscoveryPanel.tsx`: essential city picker, consent and POI search text localized; diagnostic service readiness, optional shared-walk import and coordinate fallback folded into disclosure widgets; meaningful Chinese message explains the reason for a disabled search button. All actual search data, provider identity, provenance and authorization remain in the DOM and unchanged.

**This PR/commit intentionally does NOT claim "the AI independently planned an outing."** The `HERMES_COMPAT_ENDPOINT` status still means configured, not that model returned tool_calls or a signed AgentRun completed. Actual Agent can be enabled separately via `--agent` only, as documented in `trial/REVOLUTION_AGENT_WB2API_CONNECT.md`.

## Human update (existing detached trial checkout)
Stop the old launcher if necessary. The old detached worktree may have local npm lockfile repairs; do not reset or hard-clean its working tree.

```powershell
cd D:\moodle\CityNexus-Revolution-Trial
git fetch origin
git restore --source origin/trial/revolution-first-look-20261014 -- frontend/src/trial/RevolutionFirstLook.tsx frontend/src/trial/RevolutionGuide.tsx frontend/src/trial/RevolutionUsability.css frontend/src/features/discovery/BootstrapDiscoveryPanel.tsx
```

Then `Ctrl+Shift+R` in `http://127.0.0.1:14173/revolution`, or restart Vite if necessary. Existing `--agent` setting, local `WB2API_KEY`, Nominatim contact and `frontend/package-lock.json` are untouched by this command.

**If the previous local `revolution_ui_fix.py` was already applied**, save local source changes first. The direct GitHub implementation supersedes that offline patch; do not apply both.

## Follow-on Codex acceptance (small and concrete)
Do this only on the trial branch; no R110, Qoder fusion, broad regression archive or restart of the Agent implementation:
1. Refresh these exact files, use the same isolated backend and `--agent`; capture desktop 1440px + mobile 390x844 screenshots.
2. `cd frontend; npm run typecheck:all; npm run build`. Backend smoke only if UI route requests fail. Resolve actual TypeScript/runtime mismatches. **These tests were NOT executed during the remote GitHub editing turn.**
3. In browser, confirm header renders horizontally, only 3 understandable actions appear initially and diagnostic/import/coordinates sections are collapsed.
4. Starting a **fresh signed** DRAFT Journey, user clicks "选一个地方", chooses a real public center with explicit geocoder/map consents; then "找好玩的" to select category, confirm city label, opt into external POI search, and see real provider results or truthfully surfaced service error; then selects two sourced places and saves GO.
5. Make sure `/v8/hub` remains intact and R108 Pocket Walk data/PlanVersion/member private boundaries haven't changed. Return any actual unblocker as one minimal PR/commit.
6. Verify `/agent/runtime-status` says `HERMES_COMPAT_ENDPOINT` after --agent, but DO NOT declare AI Agent success without tool-call trace and durable signed AgentRun.
7. Stop treating large retrospective verifier counts as a substitute for a human completing this exact flow.

## Evidence grade
`GITHUB_CODE_WRITTEN + STATIC_STRUCTURAL_CHECK`: JSX <details> openings/closings match; application imports refer to committed paths; all essential consent/identity gates remain in the product source. **Not yet `TYPECHECK_PASS`, `PLAYWRIGHT_PASS`, or `REAL_USER_PASS`**.
