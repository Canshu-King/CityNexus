# GPT assist - Revolution Lab R6 -> H11 -> R6.1

This branch is **coordination/evidence only**. It is based on the repository's current default branch and is **not** the Revolution Lab R6 product source.

Frozen R6 lab candidate under review:

`474e347d513538151f19de49b6248bfd586bc766`

The exact R6 commit still does not resolve in this GitHub repository, so the product candidate remains:

`LOCAL-ONLY / NO RESOLVABLE AUDIT COORDINATE`

## Immediate order

1. Do not mutate/amend/rebase the frozen R6 candidate.
2. Hand the exact candidate to independent Harness H11.
3. H11 independently tests:
   - live/provider-backed + KNOWN_PAID + mock => non-selectable; select 409; pointer unchanged
   - captured replay + KNOWN_PAID + mock => same
   - UNKNOWN cost + compatibility zero => 422 PLACE_COST_UNVERIFIED; zero PlanVersions
   - KNOWN_FREE zero => compose succeeds as KNOWN_FREE; mock mobility remains non-authoritative
   - sealed demo + mock => selectable; select 200; pointer changes to selected plan
4. Only after H11 acceptance start R6.1 from exact `474e347...`.

## External closeout findings for R6.1

### R61_EXPLICIT_ROLE_BYPASS

R6 applies `_catalogue_visit_eligible()` to AUTO catalog sourcing, but `_generic_compose_plans()` does not apply the same predicate to caller-supplied `place_ids`. It persists each explicit Place as `activity_type="visit"`. Two hotels with verified opening/cost evidence can therefore still become an explicit hotel-hopping sightseeing plan.

Required narrow fix after H11: reuse the existing shared visit-eligibility predicate in generic compose. Do not create a second category list. Reject ineligible explicit roles before persistence and keep PlanVersion/Activity counts at zero.

### R61_ACTIVITY_COST_EVIDENCE_CROSS_BIND

Inside `_generic_compose_plans()`, the Activity persistence loop uses `metadata.get("cost_evidence")`, where `metadata` is the loop variable left from the earlier scheduling loop. Activities can therefore inherit another Place's cost evidence.

Required narrow fix: reload metadata from the Activity's own `place` in the persistence loop and bind that Place's `cost_evidence`.

### R61_VERIFIED_COST_COMPATIBILITY_DRIFT

Planning accepts KNOWN / VERIFIED_OFFICIAL_WEB / OFFICIAL_WEB_VERIFIED / VERIFIED_PROVIDER as verified cost states, but `real_city._place_metadata()` sets compatibility `cost_minor` and `price_known=True` only for status KNOWN. Keep `cost_evidence` authoritative, but align compatibility fields with the full verified-known set.

## Evidence caveat

The R6 five-arm closeout probe resets the demo DB between arms. The JSON receipt records all arms, but the final SQLite file does not simultaneously preserve the earlier arm rows. This does not block H11, which must reproduce the arms independently.

## Scope warning

`CATALOGUE_VISIT_CATEGORIES` still includes cafe/food/restaurant/nightlife. R6 closes lodging-as-generic-visit in AUTO; it does not yet prove a complete meal/stay/visit role model.

P7=false. No mainline merge. No Harness product edits.