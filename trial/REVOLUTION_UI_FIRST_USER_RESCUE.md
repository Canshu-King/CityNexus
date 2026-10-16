# Revolution first-user UI rescue — 2026-10-15

## Why this exists
A real user's 2026-10-15 screenshots showed: "连城，从这里开始。" forced into a one-character-wide column, the "换一个地区" button spanning most of the content width, all of the R107/R108 BootstrapDiscoveryPanel internal provenance/debug paragraphs shown at once, massive blue V8-width buttons, bilingual developer copy, and no obvious way to advance.

The first place search starts from a selected area; protocol details stay in the collapsed section. The 2026-10-15 screenshots record the original layout issue.

## What was actually changed in GitHub
- `frontend/src/trial/RevolutionFirstLook.tsx`: new `RevolutionGuide` and collapsed native discovery details. Original signed discovery and GO MODE remain mounted/functional.
- `frontend/src/trial/RevolutionGuide.tsx`: 3 actionable choices that reveal and focus the existing native controls:
  (1) choose a public map search center; (2) select an interest and authorize one external search; (3) select two returned candidates and save a GO walk. Each action keeps its existing user-controlled location, model, payment, provider, and member consent steps.
- `frontend/src/trial/RevolutionUsability.css`: scoped fixes to the collapsed heading and giant buttons, 3-step layout, readable forms, smaller type, mobile behavior, accessible high-contrast controls. No Qoder/mainline CSS changes.
- `frontend/src/features/discovery/BootstrapDiscoveryPanel.tsx`: essential city picker, consent and POI search text localized; diagnostic service readiness, optional shared-walk import and coordinate fallback folded into disclosure widgets; meaningful Chinese message explains the reason for a disabled search button. All actual search data, provider identity, provenance and authorization remain in the DOM and unchanged.

**AI run:** Start the server with `--agent`, then complete a Journey action to record tool calls and the signed AgentRun. `HERMES_COMPAT_ENDPOINT` shows the configured endpoint.

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
2. `cd frontend; npm run typecheck:all; npm run build`. Backend smoke only if UI route requests fail. Resolve actual TypeScript/runtime mismatches. The remote GitHub edit did not run these checks.
3. In browser, confirm header renders horizontally, only 3 understandable actions appear initially and diagnostic/import/coordinates sections are collapsed.
4. Starting a **fresh signed** DRAFT Journey, user clicks "选一个地方", chooses a real public center with explicit geocoder/map consents; then "找好玩的" to select category, confirm city label, opt into external POI search, and see real provider results or truthfully surfaced service error; then selects two sourced places and saves GO.
5. Make sure `/v8/hub` remains intact and R108 Pocket Walk data/PlanVersion/member private boundaries haven't changed. Return any actual unblocker as one minimal PR/commit.
6. Verify `/agent/runtime-status` after starting with `--agent`; confirm a tool-call trace and durable signed AgentRun after completing the Journey action.
7. Stop treating large retrospective verifier counts as a substitute for a human completing this exact flow.

## Evidence grade
`GITHUB_CODE_WRITTEN + STATIC_STRUCTURAL_CHECK`: JSX structure and import paths checked; consent and identity gates remain in the product source. TypeScript, browser, and user walkthrough checks are pending.
