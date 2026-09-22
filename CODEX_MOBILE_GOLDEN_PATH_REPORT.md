# CityNexus Mobile Golden Path — Codex Frontend Report

Date: 2026-09-22  
Branch: `codex/mobile-golden-path-20260922`  
Worktree: `D:\moodle\_codex_mobile_golden_path_20260922`

## Outcome

The isolated frontend candidate fixes two observed mobile defects and adds a repeatable golden-path gate:

1. Setup step 1 now keeps the missing-field explanation in the same sticky action band as `Next`. The inline field links no longer inherit the global full-width button rule, and the action band stays at the viewport edge so arrival/departure time inputs remain visible.
2. Wallet dark mode now applies dark surface, ink, border, state-chip, icon, textarea, and authority-panel tokens to the older booking/inbox surfaces. Reservation and import text remain readable instead of rendering as white cards on a black page.

No API, domain, planner, Hermes, database, backend, or live data files were changed.

## Evidence

All browser runs used an isolated local backend and an isolated SQLite database under this worktree. `CITYNEXUS_E2E_AUTHORITATIVE=0` was intentional: the local backend did not echo the requested run id, so these are reproducible local black-box results, not authoritative production evidence.

| Check | Result |
| --- | --- |
| `npm run build` | PASS — Vite production build and service worker generation |
| `npm run typecheck` | PASS |
| Existing onboarding failure + blocked-next accessibility tests | PASS — 14 tests |
| Existing mobile overflow gate | PASS — Today + Live at 360/412/430 |
| Codex golden-path gate | PASS — 4 tests |
| Final screenshots | PASS — Today, Live, Wallet, Setup; light/dark at 412x915 |

The Codex gate is `frontend/e2e/codex-mobile-golden-path.spec.ts` and covers:

- Today, Live, and Wallet horizontal overflow at 360, 390, 412, and 430 px;
- blocked Setup geometry at the same widths, including hint-before-CTA and time-input visibility;
- Wallet dark-mode card/inbox surface checks and computed heading contrast >= 4.5:1.

Screenshots:

- Before: `output/evidence/before/`
- After: `output/evidence/`

The final after captures are `after/today-*.png`, `after/live-*.png`, `after/wallet-*.png`, and `after/setup-step1-*.png` at 412x915. The `after/setup-step1-fixed-412x915.png` file is retained as an intermediate diagnostic and is not the final claim.

## Exact test commands

```text
npm run build
npm run typecheck
npx playwright test e2e/qoder-onboarding-failure.spec.ts e2e/qoder-wizard-blocked-next-a11y.spec.ts --project=chromium
npx playwright test e2e/qoder-mobile-overflow.spec.ts --project=chromium
npx playwright test e2e/codex-mobile-golden-path.spec.ts --project=chromium
npx playwright test e2e/qoder-ui-overnight-shots.spec.ts --project=chromium --grep="today|live|wallet|setup-step"
```

## Scope and remaining blockers

- The candidate is not merged into the main authority tree.
- The authoritative backend lane was not used because its run-id contract was unavailable in this local environment. No authoritative product truth is claimed here.
- A transient SQLite cache-write contention message appeared during concurrent read-only UI navigation; all affected browser assertions passed and no production database was used.
- Desktop sanity was kept to build/typecheck and the existing responsive shell; this sprint’s acceptance evidence is mobile-first as requested.

## Commit

Commit SHA: `646371f37165979cb14f288991a18996537443f`  
Use `git show --stat 646371f37165979cb14f288991a18996537443f` and `git diff a9c2504274dd3284b1a98b6707f7c4c9f7071cc3..646371f37165979cb14f288991a18996537443f -- frontend` to review the exact frontend snapshot and Codex delta.

The commit carries the Qoder R14 frontend snapshot used as the tested baseline plus the Codex mobile delta; it is intentionally an unmerged candidate branch.
