# R83 GPT remote review — 2026-10-09 (after e3d15bff)

## Remote verification
- Branch: `gpt/revolution-r33-open-world-journey-adaptation`, reviewed HEAD: `e3d15bffa0107cfad7fa47c49f03b6ba15e3ae9b` (R83 taskbook only).
- `REVOLUTION_R83_ONE_TAP_LIVE_CITY_ADVENTURE_RESULT.md` not yet present at reviewed HEAD; **do not claim R83 accepted**.
- R82 report exists and states 21 focused backend + 2 Chromium passes; these are **Codex-reported**, not independently rerun by web reviewer.

## Narrow implementation attention (prioritize user action)
1. `MomentScoutCard.tsx`: cached scout receipts are cleared for `journeyId` transitions and TTL, but do not assume this alone addresses **same-Journey member switch / PlanVersion or execution-cursor changes**. Re-evaluate or remount/clear member-private state on authoritative context changes; revalidate on server at selection; do not expose a stale candidate or preserve map-consent across identities.
2. Place discovery must be useful from normal active Journey with ZERO pre-seeded city Places. Cancel before consent -> zero external contacts. Authenticated fresh foreground observation is not anonymous location; clearly disclose server persistence and possible group-presence effects.
3. Source-bound named OSM entity only, explicit access deny filter; selection, not query, materializes a Place. OSM geometry/distance must NOT masquerade as route ETA or C3/C4 commitment feasibility.
4. Use existing `MemberSideQuestCard` and current shared-stop flow for **two separate destination-only external map consents**: outward to selected real POI and back to CURRENT shared stop. On PlanVersion/cursor/membership changes, old map release is cancelled. Opening map is not travel proof.
5. **One** fresh signed A/B browser closure, focused backend/typecheck/build/compile/diff. Browser-controlled Overpass fixture is TEST_PROVIDER; at most one true external Overpass attempt if enabled, otherwise report BLOCKED honestly. No unrelated historical strike reruns.

## Result required before acceptance
Push implementation + `REVOLUTION_R83_ONE_TAP_LIVE_CITY_ADVENTURE_RESULT.md` on the SAME remote branch. Record commit SHAs; new Journey and identities; real versus test provider distinctions; request count; source IDs and selected Place; destination-only URL proof; A/B privacy; active PlanVersion before/after; physical traversal as UNVERIFIED; actual Agent/Guardian/provider counts. If missing the direct travel/return action, call it PARTIAL, not COMPLETE.

Continue R83 now. Do not open an R84 planning loop before delivering the R83 end-to-end user experience.
