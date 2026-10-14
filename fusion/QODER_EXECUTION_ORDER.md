# QODER — Unified Fusion Implementation Order (2026-10-14)

Read `fusion/UNIFIED_FUSION_CHARTER.md` first. **Your job changes:** no further ORD batches unrelated to fusion until a unified application visibly ships. Work on your dedicated `fusion/qoder-import-20261014` branch, not `commander/control` or `mirror/integration-frontend-apple-pass1`.

## First actions
1. Fetch exact source refs from charter; verify initial canonical branch SHA; make new isolated worktree from dedicated fusion branch. Keep original worktrees untouched.
2. Inspect full source tree with `git diff --name-status`, `git ls-tree -r`, directory/API/route inspections. Compare `mirror/integration-frontend-apple-pass1` to the fusion baseline using three-way/semantic classification, not GitHub's truncated 300-file compare. Make a **feature parity matrix**, not one row per technical commit. Include source/target/test paths, user entry, API & schema impact, migration decision, owner, state.
3. Freeze demonstration-like user-visible Qoder capabilities: Today, Map, Copilot, Wallet, Me, setup/wizard, trips, check-in, collections, POI import, stays, estimate/budget, posters/sharing/calendar, pending/inbox, offline PWA. Confirm existence in source, do not invent if only dormant files.
4. Identify overlapping modules (`backend/app/main.py`, `services.py`, `core/config.py`, `db/models.py`, `db/session.py`, `schemas.py`, `agent/gateway.py`, `frontend/src/main.tsx`, `V8Experience.tsx`, `LiveRecovery.tsx`, `src/api/citynexus.ts`, OpenAPI types, Workbox SW). **NEVER** wholesale copy these over Revolution; use small reviewable integration commits.
5. Implement vertical slice restoration in descending end-user value, with routes + API + schema + UI + one affected test together. For Qoder-only files, transplant with attribution after checking dependencies. Make Qoder UX the home/shell candidate if source tests show it is stronger, but retain Revolution new routes/cards and contracts. No unilateral UI shell overwrite.
6. Pair with Codex through PR review: publish PR into canonical marked 'Qoder capability import'; do not merge without cross-review/integration owner. List exact effects and missing paths, distinguish product additions from evidence-only.
7. Prove one **Qoder-specific** complete phone-size walkthrough on fused source; also ensure R107/R108 discovery/GO still appears and still works after Qoder imports.

## Top risks assigned to Qoder
- Old Qoder R77 contract regressions (8 failed, 18 passed at 2026-10-13 checkpoint; not a claim latest full suite fails): metadata search, unknown costs, route fact and service helpers. Repair real causes on fusion branch if reappearing, but never block importing unrelated vertical slices on eight archival regressions.
- Preserve Qoder PWA, entry routes, actual Chinese UI, map and error handling while adding Revolution.
- Guard old SQLite migration/data compatibility. No destructive migration or test reset of actual Journey.
- Separate demo/simulation from live sources; no estimated opening/cost being given canonical hard authority.

## Deliverables
- `fusion/QODER_PARITY.md` with precise gaps + implemented rows
- `fusion/QODER_RESULT.md` containing SHA, affected tests, link to normal UI routes, new vs old user actions, remaining blockers
- Reviewable feature commits + PR and one saved 390x844 Chromium route walkthrough against **one fused backend**
- No expanding unrelated ORD/evidence bureaucracy. Invest 80% in feature code and integration; keep evidence proportional.
