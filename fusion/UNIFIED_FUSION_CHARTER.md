# CityNexus Unified Fusion — 2026-10-14

**Objective: ONE deployable CityNexus product, not two branches or two demonstrations.**

The last classroom demonstration showed an old experience despite real Revolution progress. This is a product-delivery failure. Stop optimizing for proof counts and deliver integrated user capabilities in the normal phone UI.

## Immutable source snapshot (verify remote refs before implementation)
- Revolution product: `gpt/revolution-r33-open-world-journey-adaptation` @ `a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9`.
- Qoder **product tree**: `mirror/integration-frontend-apple-pass1` @ `eeb8b8d2fd06d90963cf3cb91f6b06feef595df8`.
- Qoder commander/control is **not** the application product tree: @ `0c64074cf9347be5e74337332ee40799d3359ddd`.
- Old fusion experiment `codex/revolution-qoder-integration-20261010` @ `db6dea9bc30ea907b021befa56da628e5dcc7d43`; inspect/reuse selective fixes, not a complete target.
- Codex R108 work: `codex/revolution-r63-planned-parallel-journey` @ `c6396086022abbead5e19df5559b3673c09f4c87`. Revolution GPT branch also includes later **unrun** R108 reviewer fixes; do not overwrite them.
- Both primary product histories are **diverged**. 1219 Revolution-only and 1781 Qoder-only commits relative to each other's tips in GitHub compare on this snapshot; counts are not conflicts or proof of distinct features.

## Branches and owners
Canonical assembly/QA branch: `fusion/citynexus-unified-20261014`. It is forked from Revolution at the snapshot above because it already contains R108 Pocket Walk and its reviewer fixes. This is a starting point, **not a declaration that Revolution wins all conflicts**.

- Qoder: `fusion/qoder-import-20261014` from exact canonical branch SHA, owns Qoder product-feature transplantation, backend compatibility, and Qoder UI features. One assigned implementer owns integration commits at a time.
- Codex: `fusion/codex-journey-20261014` from same exact canonical branch SHA, owns Revolution end-to-end Journey/Agent/mobile integration and bridge to imported Qoder functionality.
- Integration release owner: assemble both by reviewed PR or explicit cherry-pick into canonical, resolve overlaps explicitly, validate on same SHA. Avoid simultaneous writes to `fusion/citynexus-unified-20261014`.
- Leave `commander/control`, `mirror/integration-frontend-apple-pass1`, `gpt/revolution-r33-open-world-journey-adaptation`, and Codex original work branch unchanged.

## Strict meaning of FULL
Full fusion is a **parity + product** target:
1. Every existing user-reachable, legitimate feature in either source has an inventory row: source path, backend endpoints, schema, frontend entry, chosen implementation, status, proof or named exclusion with approval.
2. All features kept must work through one frontend, one API runtime, one database schema/migration chain, one identity/session model, and consistent authority.
3. No disappearance of Qoder: Today, Trips, Map, Copilot, Wallet, Me, wizard, day plan, collections, POI import, check-in, stays, costs, posters, sharing, notifications, error/empty states, and offline/PWA. Inventory confirms exact user-visible entrypoints and code; do not infer from folder names.
4. No disappearance of Revolution: operator/Guardian/Agent, recovery/approval, collective journeys, real-city discovery, saved private Pocket Walk, two-stop GO and consented navigation. R109 is **taskbook only**, not accepted code until implemented/tested.
5. Consent, user-vs-provider provenance, TEST vs LIVE, signed member-private boundaries, exact PlanVersion/mutation authority, and no fake physical arrival remain enforced after fusion.
6. One actual HTTPS phone deployment on the fused SHA and a **human-operated** walkthrough; automated 390×844 Chromium is required but insufficient.
7. Proof includes baseline-to-fusion parity and truly new, user-accessible entrypoints. A green internal test with the old demo UI does not count.

## Execution order — product over paperwork
**Phase 0: one compact inventory and baseline build.** Record exact source SHAs, extract git diff/tree lists WITHOUT truncation, identify Qoder-only and Revolution-only user features, API/schema overlaps, frontend routes, migrations, service worker, environment, external providers, startup/deploy path. Do not interpret GitHub compare's first 300 files as a complete diff. Run minimal initial typecheck/build and one small signed smoke on both. Output a single editable `fusion/FEATURE_PARITY.csv` (or markdown matrix) with owner/status and first real blockers. Set timebox; do not perform an exhaustive historical verifier campaign.

**Phase 1: foundation convergence.** Decide canonical routes, V8Experience and member auth; build a single `backend/app/main.py` entry with imported endpoints, no blind 1MB overwrite; schema migrations and idempotency; OpenAPI client/type generation; settings defaults; deterministic boundary checks. Production defaults fail closed. For overlapping code use semantic 3-way merge and test the changed behaviors, never whichever file is longer/newer.

**Phase 2: Qoder capability return.** Migrate complete Qoder-only frontend/backend vertical slices (not one screen without API), maintaining routes and normal user navigation. Bring Qoder quality work that changes actual experiences. Keep import commits named by feature. No unauthenticated bypass, no fake data as live.

**Phase 3: Revolution capability visibility.** Wire real-city discovery and R107/R108 Pocket Walk to the SAME ordinary mobile home/trip flow, accessible with user login, no hidden test-only route. Make one unified Journey Operator with explicit user authorization and background model-status truth. Preserve group/private split and no-continuation-on-foreign-member fences. Existing AI fallback MUST NOT be passed off as autonomous external model judgment.

**Phase 4: single product acceptance.** Backend affected-slice suites, frontend `npm run typecheck:all`, `npm run build`, Python app/tests compile, lint/diff, two fresh authoritative signed A/B Playwright journeys in 390x844 and 430x932 against one new isolated backend and no reused server:
(A) Qoder normal create/edit/day/view/check-in/stay/cost/calendar/poster/whatever source inventory proves user-reachable;
(B) Revolution manual-city consent -> public candidates (label controlled fixture honestly) -> saved private Pocket Walk -> GO start -> separate external map consent -> user-reported progression -> reload; second member sees no private data;
(C) bounded operator/Guardian event -> proposal -> authorization -> continued watch, with `LAB_FIXTURE` if provider cannot provide a real event. AI unavailable must show actionable degraded state, not success. No route/arrival claims from map launch.
Verify same build contains and links all tested paths. Add missing tests per observed regression only.

**Phase 5: phone and release.** Deploy pinned fusion SHA to a separate HTTPS staging origin; phone opens it directly and can reload after backgrounding, no stale service worker/app shell, API 2xx, authenticated read/write, external navigation and return, source-grade copy, no private content leakage, Chinese text usable in mobile; also prove original Qoder journey flow remains reachable. Capture device/os/browser/build SHA, manual action/outcome and redacted server trace. On failure rollback to frozen previous deployment by immutable bundle/SHA. Only then choose whether to replace main release. Never auto-deploy to existing Qoder demo.

## Non-negotiable stop conditions
Stop **release only**, not development, when an unmigrated feature disappears, unsigned cross-member read/write succeeds, TEST is called LIVE, unknown opening/cost gets hard-selection authority, stale approvals mutate Journey, re-save wipes GO unexpectedly, or actual phone cannot operate the normal flow. Keep blockers specific, assign owner and implement a fix. No fake green, no repeat-until-lucky provider strike, no six-week proof loop.

## Definition of 'good progress'
Every integration batch must show a new capability in the **one fused product** or restore one feature from the other branch, with its user route and server operation, a focused test, and exact SHA. Merge receipt with 0 user-visible delta does not count. No fresh numbered Revolution round as substitute for merging.
