# Source-bound opening dates — 2026-10-26

Product `724f44a084da738657603be402260c0f999412b9` fixes a real draft-to-departure blocker in `goal_opening_date.py`. The preserved Suzhou Museum provider sentence says `10/07-12/31 周二–周日 09:00–17:00`, but the previous parser treated Saturday 2026-12-05 at 14:00 as `CLOSED_ON_DATE / SOURCE_SERVES_OTHER_DAYS_ONLY`. It did not recognize the en dash weekday range or numeric month/day seasons.

The reader now recognizes numeric month/day spans and keeps the applicable date span, weekday and window together. A seasonal Monday closure applies only to the named Mondays in that span. Another weekday, another season, holiday-only hours and flattened intervals cannot supply an unrelated opening window. Invalid/incomplete spans remain unknown; existing Chinese seasons, cross-year spans and notice/holiday deferrals retain their refusal behavior. No source text, canonical Place fact, price policy, booking evidence or API contract was changed. This increment does not add new last-entry or reservation semantics.

## Root serial validation

Explicit isolated database: `C:/Users/仓鼠王/cn51/classroom-20261026-qa/opening-numeric-20261026/isolated-regression.db`.

`python -m pytest -q tests/test_issue49_goal_opening_numeric.py tests/test_qoder_goal_opening_date_r1.py tests/test_goal_preparation.py --tb=short --junitxml <owned-QA>/results.xml`

**35 passed, 4 warnings, exit 0**. Raw stdout and JUnit remain in the same owned QA directory. The new source-derived fixture is embedded in the test and performs no local receipt read or provider request; its signed native prepare arm uses the isolated test database. Existing opening-date and preparation regressions passed together, including Monday closures, seasonal hours, cross-year gaps, malformed dates, holiday-only flattened intervals and notice deferrals.

## Actual signed native replay on the preserved owned database

After a normal stop/resume of only the owned launcher, the backend loaded product 724f44. A consistent prewrite SQLite backup was taken. The same Journey `e7f868e4-2d03-4d3c-b563-962e47b185f4` / task `ad695293-72e5-4482-9659-0784b98e829f` kept the same four chosen Places and schedule:

1. Signed GET draft 200 → PUT the same chosen days with the current revision 200.
2. Native prepare-plan 201 created **new** candidate `6ae4591b-8b5a-4d46-b30b-a8fb77d2f45a`. Original candidate `07a894f2-1e00-41bd-95da-70c6118b89ca` remains CANDIDATE.
3. The new candidate no longer contains the museum's false `DATE_SPECIFIC_OPENING` gap. Its canonical source envelope was compared to the pre-fix extract and is unchanged.
4. Native freeze-routes 200 verified **3/3**, all three **REUSED_PROVIDER_RECEIPT**. AgentRun remained **39**, ProviderCall remained **115**. No map/model request was needed to rebuild the corrected candidate.
5. Signed departure GET 200 read the new candidate. Both candidates remain **CANDIDATE**, all new activities **PLANNED**. The real unresolved Lion Grove opening hours and four unknown admission prices remain; no acknowledgement, selection, ACTIVE state or completion was manufactured.

`20261026_SUZHOU_OPENING_REPREPARE_HTTP.json` records the original source/refusal, native HTTP results, both plan identities, unchanged counts and the actual persisted new snapshot/activities. Guarded QA replay and prewrite backup remain in `supply-native-20261026`; do not repeat that write sequence.

This is a source-parser correction plus native candidate replay, not a live-model run, browser acceptance or physical-device verification. Three-city publication was already proven separately and was not repeated. Parallel frontend dirty files and Qoder's database/services remain outside this increment.
