# Route cache identity repair — 2026-10-26

Changing a prepared candidate from provider lead IDs to canonical Place IDs previously missed the same task's stored route. The Nanjing supply run exposed one duplicate measurement; both historical provider receipts remain preserved.

The freeze cache now resolves both stored endpoints and activity identities through the current task's exact `research_places.id` / `canonical_place_id` mapping to existing Place rows. Unknown, dangling, conflicting and ambiguous aliases cannot authorize cache reuse. Names and coordinates do not establish aliases. Forward and reverse lookups share the same identity mapping; reverse reuse keeps the original receipt and measurement endpoints while reversing geometry. The HTTP response contract is unchanged.

## Root validation

- Checkout: `D:/moodle/_codex_workers/citynexus-sandbox-security-20261025`, branch `codex/sandbox-execution-security-20261025`; parent `a1e82da35b005dfd874dc478bab3f580123a37a6`.
- Root-only serial command, Python 3.12.14: `python -m pytest -q tests/test_issue49_route_cache_alias.py tests/test_goal_route_freeze.py tests/test_issue49_goal_route_geometry.py --tb=short --junitxml <owned-QA>/final-results.xml`.
- Explicit isolated database: `C:/Users/仓鼠王/cn51/classroom-20261026-qa/route-cache-alias-20261026/isolated-regression-final.db`.
- Result: **26 passed, 4 warnings, exit 0**. Raw log and JUnit receipt: the same QA directory, `final-pytest.log` and `final-results.xml`.
- The first run had 21 passes and 5 test failures because the new tests expected geometry fields in a response model that deliberately omits them. The tests were corrected to inspect persisted mobility evidence and the domain result; no response fields were added. Initial log/XML remain retained.
- The regression uses declared offline fixtures. Two distinct prepared candidates and different idempotency keys reuse a stored route with zero measuring/provider-client calls. Both stored key formats, both geometry directions, blocked geometry and unknown/foreign/ambiguous aliases are covered.

No live provider/model call, browser action, owned demo DB mutation or service restart was performed for this repair. Nanjing still has only two countable geometric edges; its third edge and three-city readiness remain blocked. The existing 1m geometry junction limit was not changed. This proves the cache repair under isolated regression, not live classroom completion or physical-device acceptance.

Only the backend module, its new regression file and this receipt belong to this increment. Parallel frontend changes remain outside the commit. Qoder owns rescue integration.
