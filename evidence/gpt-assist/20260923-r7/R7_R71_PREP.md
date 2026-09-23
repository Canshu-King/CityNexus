# GPT assist - Revolution Lab R7 -> R7.1

R6.3 frozen lab checkpoint remains 74005fa8b191511b48df395abda6033fdb93aec3.

## R7 machine facts

- Gongshan live hydration source binds to exact clean 74005fa.
- Provider identity resolves to OSM:R:2729765 with ACCEPTED_PROVIDER_IDENTITY.
- Live preparation completes CATALOG_PREPARED but only PARTIAL.
- One Overpass viewpoint is materialized.
- Its opening evidence is UNKNOWN.
- Its cost evidence is UNKNOWN with amount null; compatibility cost_minor=0, price_known=false.
- Mobility has zero explicit pairs and is not hard eligible.
- Matrix/truth probes correctly refuse to infer planner truth with only one provider-backed Place.
- Direct AUTO generation returns 422 CATALOG_INSUFFICIENT.
- Focused tests report 32 passed.

Mission A remains OPEN. P7=false.

## Important decomposition

Raw provider place count is not the planner-ready count. _catalogue_templates() requires visit-role eligibility + concrete opening window + verified cost and then at least two packed stops. With the sole Gongshan row UNKNOWN for opening and cost, the effective template-eligible count is zero.

R7.1 must publish both raw provider count and exact template-eligible count with per-Place rejection reasons.

## Timeout/order-bias clue

Preparation durations are approximately:

- attraction 4.51s -> 1 row
- museum 7.12s -> 0 rows
- restaurant 21.09s -> timeout
- cafe 15.99s -> timeout
- park 12.02s -> timeout
- hotel 8.84s -> timeout

These sum to about 69.58s against about 72.54s whole hydration time, while later timeout durations shrink. This is consistent with shared-deadline/order starvation, but is not proof.

Before modifying provider queries, run isolated or rotated category arms. If a category succeeds when early/isolated but fails late, repair orchestration budget fairness rather than blaming the provider.

## Next order

1. Freeze 74005; do not mutate it.
2. Bind every R7.1 run with PRE/POST HEAD/branch/clean status.
3. Run an exact catalogue eligibility ledger.
4. Diagnose category order/deadline bias.
5. If needed compare canonical-area acquisition with an explicitly labeled bounded centroid-radius diagnostic. Do not silently redefine destination coverage.
6. Prioritize >=2 real planner-eligible visit stops, not broad category completeness.
7. Missing opening/cost remains UNKNOWN; never infer free or 24/7.
8. Only after >=2 eligible real stops, acquire real/hard-eligible mobility for actual used pairs.
9. Then run AUTO generation and capture clean JSON, persistence counts, selectable blocker and pointer state.
10. Mission A stays OPEN until full independent real-content + real-fact + real-mobility + authority chain closes.

## Evidence hygiene gaps in current R7 archive

- generate_plans_exact_blocker.json is not valid JSON as archived because a deprecation warning is prepended.
- Direct 422 blocker is not independently PRE/POST bound to the claimed source commit.
- Final commit 705c41b is provided without commit list/diff proving post-74005 changes are evidence/tooling-only.
- Some receipt filenames differ from archive filenames.
- R7 commits still do not resolve in the connected GitHub repositories; label them LOCAL-ONLY / NO RESOLVABLE AUDIT COORDINATE unless the isolated branch is pushed without merge.