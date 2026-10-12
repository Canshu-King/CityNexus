# Revolution R38 — Departure Readiness & Just-in-Time Briefing

## Result

- **Outcome:** `READINESS_READY_WITH_UNCERTAINTY`
- **Fresh Journey:** `1f20ebaa-b95d-4956-85eb-6306e2027642`
- **Target:** `依水園` on provider-backed Place `real-place-22cf72809897ff4c7f312fcf` (`overpass`)
- **Source head before refresh:** `293dc434fc593fa74469d9f875c77ea1f84c9fa2`
- **Machine receipt:** [backend/output/r38-departure-readiness-v1.json](backend/output/r38-departure-readiness-v1.json)

One bounded readiness refresh ran on the fresh Journey. The selected plan had two provider-backed mobility facts, but no fact matched the current pre-trip target edge, so `must_leave_by` stayed `null` with `NO_TRAVEL_EDGE`. The refresh did not infer a travel duration from aggregate route evidence.

The target venue had no fresh Guardian venue observation in this bounded refresh (`UNKNOWN`), foreground location was not requested, and there was no reservation or protected C3/C4 commitment bound to this target. The readiness answer therefore remained usable but qualified:

> Mostly ready · some live information is unavailable.

The target was far outside the 60-minute briefing window, so no NotificationEvent was created. The stable notification/fingerprint path is implemented for the eligible windows and reuses the existing `notify()` channel.

## Authority and continuity

- Readiness is a read-only projection. The refresh created no Event, AgentRun, ReplanProposal, RecoveryEpoch, plan mutation, booking change, or execution-truth transition.
- Unrelated C3/C4 commitments no longer attach to the current next activity; reservation selection is bound to the target commitment and a nearby departure window.
- Aggregate mobility evidence cannot produce `must_leave_by`; only an exact current-to-next edge with explicit minutes can do so.
- `OfflineJourneySnapshot` now carries captured readiness, target, recommendation, venue last-known state, route evidence, freshness semantics, and capture time.
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` remained set.

## Verification

- Departure-readiness plus R37/R36/R35 focused backend suite: **58 passed**
- Frontend TypeScript check: **passed**
- Guardian/Next Move Playwright suite: **3 passed**

## Scope limit

No browser location or trusted device attestation was needed or fabricated. The receipt records the unavailable presence and the explicit absence reason for `must_leave_by`.
