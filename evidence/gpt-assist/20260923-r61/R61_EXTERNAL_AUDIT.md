# External audit — Revolution Lab R6.1

Frozen R6: `474e347d513538151f19de49b6248bfd586bc766`.
R6.1 RED checkpoint: `805877118db853e6c90a54a5ab6d4e9b97ce21e7`.
R6.1 LAB candidate: `39e028f914240d5421b1304b0dd83c7113705412`.

The package credibly reproduces the three R6.1 defects at the RED checkpoint (5 failed / 2 passed) and reports 31 passed plus frontend typecheck at the clean final commit. The patch direction is narrow: shared verified-cost states, explicit role gating through the existing visit predicate, per-Activity own-Place cost evidence binding, derived price_known, and named frontend refusal.

Gongshan remains correctly bounded as SYNTHETIC_DIAGNOSTIC_ONLY_NOT_LIVE with 422 CATALOG_INSUFFICIENT and no lodging visits. Mission A is not SELECTABLE.

## Gate

H11 validated frozen R6, not R6.1. Freeze `39e028f...` and run an independent R6.1 cross-test before promotion.

## New RED candidate: R62_STALE_COMPATIBILITY_COST_SURVIVES_UNKNOWN

R6.1 _place_metadata still uses metadata.setdefault("cost_minor", 0) when current cost evidence is UNKNOWN/unverified. Because metadata starts with candidate.metadata, a stale old cost_minor can survive while price_known=false and cost_evidence.status=UNKNOWN. Expected compatibility truth: UNKNOWN => cost_minor=0 and price_known=false; verified-known => exact amount including genuine zero.

## Investigation target: R62_ANCHOR_UNKNOWN_COST_COLLAPSE

R6.1 anchor_schedule._place_cost now consults verified evidence states but still returns integer 0 for UNKNOWN/unverified evidence. CandidateActivity has only numeric cost. Reproduce through a real C4/MID_TRIP compose path and determine whether PlanVersion total_cost / budget_fit presents the anchored unknown cost as free. Do not invent a cost to fix it.

## Evidence hygiene

The Gongshan SQLite is disposable but contains historical R5/R6 journey/plan rows. Scenario-specific R6.1 diagnostic journeys have zero PlanVersions/Activities, so the role conclusion survives, but future probes should use a brand-new DB containing only the seven required Place rows. Also rename catalog_before because the R6.1 receipt already shows SYNTHETIC_DIAGNOSTIC_FIXTURE values there; preserve a true pre-fixture snapshot separately.

## Audit coordinate

External lookup on 2026-09-23 did not resolve `39e028f...` or `8058771...` in Canshu-King/CityNexus or CityNexus-Workspace. Keep LOCAL-ONLY / NO RESOLVABLE AUDIT COORDINATE until Codex pushes the experimental branch without merging it.