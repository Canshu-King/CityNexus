# Revolution R39 — Grounded Journey Launch Result

## Closure

- **Outcome:** `LAUNCH_ORIGIN_UNKNOWN`
- **Fresh Journey:** `476d78b2-5106-42c5-8597-a35003013c36`
- **Machine receipt:** [r39-grounded-journey-launch-v1.json](backend/output/r39-grounded-journey-launch-v1.json)
- **Source head before live:** `b39e3ef999792f34329e0ac57dd4cdb442c562d5`
- **Authority:** `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`

The bounded closure created a fresh NARA Journey with a selected provider-backed plan and no shared location. No fresh foreground observation, temporally valid selected stay, or coordinate-bearing arrival anchor was present for the first target. The projection therefore returned `UNKNOWN_ORIGIN`; it did not select a city centre, hotel, first mobility fact, or arbitrary nearest edge. The exact launch edge stayed unavailable and `must_leave_by` remained `null` with `NO_TRAVEL_EDGE`.

## Readiness and continuity

The readiness refresh returned `READY_WITH_UNCERTAINTY`. The offline snapshot contains the launch origin, launch edge, leave-by value, and capture/freshness fields; this closure records the first two as `null` because the source was not grounded. The active plan id was unchanged before and after the refresh.

The persisted action ledger remained empty: zero `Event`, `AgentRun`, `ReplanProposal`, and accepted-mutation rows; zero location observations; zero notification rows. No execution activity state or plan truth was mutated by launch projection or readiness refresh.

## Implemented contract

- Strict launch-source precedence for previous activity, fresh advisory location, temporally covering selected stay, coordinate-bearing arrival anchor, then unknown.
- Exact origin-key → target-Place matching across frozen `MobilityFact`, plan evidence, and `JourneyLeg`; no aggregate or nearest-edge fallback.
- Next Move uses a `LAUNCH_EDGE` route only when the activity edge is absent; readiness computes a leave-by time only from an explicit exact duration plus a 10-minute safety buffer.
- Offline readiness carries launch source, edge, provider/provenance, capture/expiry, and freshness semantics.
- UI copy names the ordinary start point when one exists and does not expose internal origin enums.

## Verification

- Focused backend suite: **53 passed, 4 warnings**.
- Frontend TypeScript: **passed** (`tsc -p tsconfig.check.json --noEmit`).
- Focused Playwright: **3 passed** (`r35-live-guardian-status.spec.ts`); five selected legacy/live cases stopped at their own reset/auth preconditions (`RESET_TOKEN_REQUIRED` or journey setup `422`), before exercising R39 UI assertions.
- R33–R38 live closures were not rerun.

\n
