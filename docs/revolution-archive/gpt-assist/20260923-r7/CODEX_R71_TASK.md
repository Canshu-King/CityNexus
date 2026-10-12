# R7.1 Codex execution contract

Use this as a narrow next task, not permission for broad enrichment.

## Gate 1 - source binding
Capture PRE and POST:
- git rev-parse HEAD
- git branch --show-current
- git status --porcelain

Separate stdout JSON from stderr warnings.

## Gate 2 - exact planner eligibility ledger
For each Place in OSM:R:2729765 record:
- provider_key/external_id/category
- visit-role eligible
- opening status + parsed window
- cost status + amount
- final template eligibility
- rejection reasons

Publish provider_place_count and template_eligible_place_count separately.

## Gate 3 - preparation fairness
Run attraction, museum, park, restaurant, hotel either isolated or in rotated order.
Record order position, query scope, endpoint/provider class, elapsed ms, rows, timeout/error, reused flag.

If success depends on going early, classify R71_PREPARATION_BUDGET_STARVATION.

## Gate 4 - evidence acquisition
Do not weaken truth gates. Seek at least two provider-backed visit stops whose opening and cost are actually evidenced. Missing facts stay UNKNOWN.

## Gate 5 - mobility
Only after >=2 template-eligible stops, capture mobility for actual used pairs. Synthetic mobility cannot become authoritative for provider-backed content.

## Gate 6 - planner
Run exact AUTO generation. Save pure JSON response, PlanVersion/Activity counts, selectable blocker, active pointer before/after selection attempt.

Mission A OPEN. P7=false.