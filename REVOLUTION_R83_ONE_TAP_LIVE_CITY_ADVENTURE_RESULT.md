# CityNexus Revolution R83 — One Tap Live City Adventure Result

## Status

**PARTIAL — the full user-action chain passed with a controlled `TEST_PROVIDER`; no real Overpass discovery or field journey is claimed.** The taskbook's requested direct action is now covered from active Journey through selection, outbound map release, the private stop, return map release, and a self-reported head-back. This run is not evidence that an actual venue is open, that a person traveled, or that the return was physically completed.

## Git and run identity

- Branch: `codex/revolution-r63-planned-parallel-journey`, tracking the Revolution remote branch `gpt/revolution-r33-open-world-journey-adaptation`.
- R83 review/taskbook remote commits: `e3d15bffa0107cfad7fa47c49f03b6ba15e3ae9b` and `8e65b6e74d0aa509633f94898c42e2220210d61e`.
- Codex R83 integration commit: `8d9c72de734105cfdcf0d41a8a0df6c0e5f479f4`.
- Authoritative E2E run: `r83-r67-20261009-135000`; isolated SQLite: `backend/_r83-r67-20261009-135000.db`; frontend/backend ports `43451` / `43452`; AI disabled; no server reuse.
- The E2E setup reset the seeded demo Journey `22222222-2222-4222-8222-222222222222` and added a collaborator. It did **not** create a new product Journey, and the database contained 16 pre-existing demo Places before the selected OSM test Place. The test does verify that the discovered candidate itself is absent from the catalog before explicit selection.

## User-visible flow covered

The existing normal active Journey entry presents “Explore real nearby places” without first submitting the local catalog scout. The browser test opens the separate OpenStreetMap consent, verifies cancel produces zero fixture calls, then confirms once. One foreground location observation is used for discovery. The local controlled fixture returns one named candidate with source identity `overpass:node/987654321`, OSM source link, and unknown opening/accessibility/price/route evidence.

The candidate is absent from `/places` before selection. After the signed member selects it, one OSM-provenance Place is materialized and the personal side quest becomes `READY`. The test then covers `EN_ROUTE → ARRIVED → COMPLETED`, outbound walking navigation to the exact WGS84 private-stop destination, return navigation to the then-current shared rendezvous, and a saved `RETURN_STARTED_REPORTED` status. Both Google Maps URLs are intercepted by the test; each contains only the destination and neither includes an origin. No map service or physical movement was verified.

The collaborator's browser does not receive the candidate name or scout receipt and sees only the coarse planned/private-stop status. The Journey's active PlanVersion remains `55523d40-cafe-5bd2-b30a-de057ec7a839`; the shared plan rows remain unchanged.

## Provider and database evidence

- The final isolated run made **one** HTTP request to the local Overpass-shaped test server, explicitly configured as `CITYNEXUS_R67_TEST_PROVIDER=fixture`. The consent-cancel path added zero requests. The fixture's cumulative counter was five after five successful controlled invocations; only one belongs to the final run/database above.
- Persisted scout receipt: provider key `overpass`, status `SELECTED`, one candidate, one recorded local fixture attempt, selected Place `real-place-a13c5747525462dc72de0a32`. The OSM key and OSM URL are fixture values, not a verified public OSM record.
- Exact foreground locations in this isolated database: **2**, both simulated by Playwright at `(5.123456, 10.654321)` with 8 m accuracy. The first was used by discovery; the second was captured when the explicit head-back action requested a fresh group route. These are test coordinates, not user GPS evidence.
- `member_side_quests=1` (final state `COMPLETED`); `member_side_quest_return_reports=1` (`RETURN_STARTED_REPORTED`); `member_live_moment_scout_receipts=1`; `places=17` (16 seeded plus the one selected Place); `plan_versions=1`.
- `agent_runs=0`; `guardian_runs=1` (`NO_ACTION`, startup baseline); `bookings=0`; `transactions=0`.
- `provider_calls=1` and `route_acquisition_operations=1`: this is the post-head-back `mock-mobility` route-to-rendezvous refresh. It ended `UNAVAILABLE` / `ROUTE_UNAVAILABLE` because the synthetic test origin had no mobility fact (`MobilitySnapshotCaptureError` / `KeyError`). It is not an Overpass call and did not change the PlanVersion.
- The run's route result and exact test coordinates make the distinction between a destination pin and an actual route ETA explicit; no travel time or commitment fit was established.

## Checks

- `backend/.venv/Scripts/python.exe -m pytest tests/test_r82_buddy_execution.py -q --tb=short` — **5 passed**.
- `backend/.venv/Scripts/python.exe -m pytest tests/test_r64_member_side_quest.py -k r83_live_osm_scout -q --tb=short` — **7 passed, 52 deselected**.
- Controlled authoritative Playwright R67 scenario, including the `real-seed` setup — **2 passed (16.8s)**.
- `npm run typecheck:all` — passed.
- `npm run build` — passed; Vite emitted its existing large-chunk advisory.
- `backend/.venv/Scripts/python.exe -m compileall -q backend/app` — passed.
- `git diff --check` — passed before commit.

## Not verified / acceptance boundary

- A real Overpass request was **not run**. The only location available to this isolated test was deliberately synthetic Playwright geolocation; sending it to a public provider would create false real-world evidence and disclose fabricated coordinates. The controlled fixture therefore remains `TEST_PROVIDER`, not `LIVE_PROVIDER`.
- The E2E run uses the fixed seeded demo Journey rather than a newly product-created Journey, and retains the city's seeded catalog. It proves the selected live-result row is materialized only after selection, but does not prove the complete flow in a zero-venue city catalog.
- Production identity/authentication, real-device location, real map navigation, real venue access/opening, route feasibility, protected C3/C4 buffer feasibility, physical arrival, and physical reunion remain **UNVERIFIED**.

## Files changed by the R83 integration commit

- `frontend/src/features/execution/MomentScoutCard.tsx` and `frontend/src/features/execution/LiveRecovery.tsx`: remount the scout component when the viewer member, active PlanVersion, execution cursor, or side-quest identity/state changes, so old private receipts, consent, and in-flight results cannot carry across contexts, following the remote review addendum.
- `frontend/e2e/r64-member-side-quest.spec.ts`: repairs signed Journey membership setup and extends the controlled R67 case through candidate materialization timing, map consent/cancel, private navigation, shared-rendezvous return navigation, and honest return reporting.
- `reports/e2e-provenance/authoritative.json`: records the final isolated run identity.
