# ORD-0645 arms: `test_r15_source_authority.py` goes green with one config field; `test_r14_terminal_disruption_recovery.py` does not

Cut against the authoritative tip `0cf83ec149f9ba399c3fde7ecabff8a1bf3a6bb5` (`refs/heads/mirror/integration-frontend-apple-pass1`), read with `git ls-remote` at the moment of the cut.
Byte sources are the remote head of `refs/heads/gpt/revolution-r33-open-world-journey-adaptation` = `a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9` (the same-named local ref here is an older generation `1725a449a50898e1c63889f0e7c0a81f347a7a1f`; its `config.py` is 130 lines while the remote one is 151, so every line number below is quoted from the remote object, not the stale local ref).

## 1. What is on the tip right now

| reading | value | coordinate |
|---|---|---|
| tip `backend/app/core/config.py` | 105 lines, no `searxng_url`, no `city_search_enabled` | `backend/app/core/config.py:105` (`settings = Settings()`) |
| last setting the tip declares | `e2e_run_id` | `backend/app/core/config.py:102` |
| tip `backend/app/fact_acquisition.py` reads `settings.searxng_url` | three places | `backend/app/fact_acquisition.py:977`, `backend/app/fact_acquisition.py:1006`, `backend/app/fact_acquisition.py:1097` |
| product files on the tip that import `app.fact_acquisition` (excluding itself) | none | `backend/app/fact_acquisition.py:1077` (`def acquire_place_facts(`) |
| tip `backend/app/main.py` | 14604 lines | `backend/app/main.py:1` |
| the 409 the r14 test must get past | `replan does not preserve the current execution position` at line 13462, inside `@app.post("/api/v1/replans/{proposal_id}/accept")` declared at line 13132 | `backend/app/main.py:13462` |
| `terminal_disruption_removal` on the tip | no hit in `backend/app` | `backend/app/main.py:13462` is where it would sit |
| `ACTIVE_ACTIVITY_DISRUPTED_AND_REMOVED` on the tip | no hit in `backend/app` | `backend/app/main.py:13462` |

So the module landed by ORD-0644 already dereferences `settings.searxng_url`, and `Settings` does not declare it. Nothing on the tip calls that module yet, which is why the line still imports (`import app.main` and `import app.fact_acquisition` both succeed on the tip as-is). The first caller gets `AttributeError: 'Settings' object has no attribute 'searxng_url'`, and `test_r15_source_authority.py` is a caller.

## 2. Arms (interpreter 3.12.14, `-X utf8 -m pytest -q -p no:cacheprovider`, run in a throwaway `git archive` export of the tip, never in the shared worktree)

| arm | what the tree held | what was run | raw counting line | rc |
|---|---|---|---|---|
| A1 both ORD-0645 tests named on the command line | tip, nothing added | the two test paths | `no tests ran in 0.00s` | 4 |
| B both tests, tip config untouched | tip + 2 test files | the two test paths | `3 failed, 3 passed, 2 warnings in 1.89s` | 1 |
| B1 r15 alone | tip + 1 test file | r15 | `2 failed, 3 passed in 0.49s` | 1 |
| B2 r14 alone | tip + 1 test file | r14 | `1 failed, 2 warnings in 1.53s` | 1 |
| C both tests + the one config line | tip + 2 tests + 1 setting | the two test paths | `1 failed, 5 passed, 2 warnings in 1.91s` | 1 |
| C1 r15 alone with the line | tip + 2 tests + 1 setting | r15 | `5 passed in 0.49s` | 0 |
| C2 r14 alone with the line | tip + 2 tests + 1 setting | r14 | `1 failed, 2 warnings in 1.60s` | 1 |
| D negative control: line taken back out, r15 alone | tip + 2 tests | r15 | `2 failed, 3 passed in 0.58s` | 1 |
| E1 collection integrity, line out | tip + 2 tests | collect-only | `1887 tests collected, 21 errors in 2.51s` | 2 |
| E2 collection integrity, line in | tip + 2 tests + 1 setting | collect-only | `1887 tests collected, 21 errors in 2.38s` | 2 |
| E3 collection integrity, nothing added | tip, nothing added | collect-only | `1881 tests collected, 21 errors in 2.53s` | 2 |
| F the pre-existing reds, tip as-is | tip, nothing added | one file | `2 failed, 9 passed, 2 warnings in 3.46s` | 1 |

For the negative control and the patch I re-read `backend/app/core/config.py` from disk after every write and asserted the field's presence, so a counting line can never be reported for a tree that did not actually hold the change.

Failure lines, verbatim from the run logs:

* B1 (r15 before the setting) rc=1: `E       AttributeError: 'Settings' object has no attribute 'searxng_url'`
* D (negative control) rc=1: `E       AttributeError: 'Settings' object has no attribute 'searxng_url'`
* B2 (r14 before) rc=1: `E       AssertionError: {'journey': {'abort_reason': None, 'aborted_at': None, 'active_plan_version_id': 'd7c02cd3-3258-4a06-a189-3849671d09f0...rrent_activity_id': 'c60f`
* C2 (r14 after) rc=1: `E       AssertionError: {'journey': {'abort_reason': None, 'aborted_at': None, 'active_plan_version_id': '8bbb37a9-7b1a-4304-96eb-76c4c08fa348...rrent_activity_id': '43c7`

r14's assertion that fails is `assert accepted.json()["journey"]["status"] == "COMPLETED"` -- it reads `ACTIVE`, i.e. the accept route completes the write but never closes the journey when the current activity was disrupted away. That branch is exactly what the representative branch carries in `backend/app/main.py` at lines 24538, 24565, 24574, 24622 (`terminal_disruption_removal`) and writes the skip reason at lines 24626, 24636 (`ACTIVE_ACTIVITY_DISRUPTED_AND_REMOVED`); the tip has neither word anywhere in `backend/app`.

## 3. Regression surface for the config line

The surface is every test file on the tip that mentions `core.config`, `from app.core import`, `Settings(`, `searxng` or `fact_acquisition` -- 22 files, run twice, once without my line and once with it:

* without: rc=1 `3 failed, 165 passed, 1 skipped, 1 xfailed, 2 warnings in 44.77s`
* with: rc=1 `3 failed, 165 passed, 1 skipped, 1 xfailed, 2 warnings in 42.00s`

Same three reds in both arms, all pre-existing on the tip as-is (`test_qoder_anywhere_matrix_truth.py::test_g14a_an_oversized_matrix_fails_closed_and_invents_no_facts`, `::test_g14c_the_verdict_must_not_depend_on_the_providers_wording`, `test_v18_3_convergence.py::test_release_metadata_and_map_entrypoint_are_converged`). Zero new red, zero changed count.

## 4. What this branch contains

* `backend/app/core/config.py` -- one added line, byte-identical to line 120 of `a5a2f1096e0f`'s `backend/app/core/config.py`: `searxng_url: str | None = os.getenv("CITYNEXUS_SEARXNG_URL") or None`
* `backend/tests/test_r15_source_authority.py` -- blob `a8ef3c5e65d6e6fc27dda3d9b83c4f3f8eb2e1ff`, byte-exact from the remote head `a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9`, 50 lines, assertions untouched
* this file, `review/jiejian/ORD0645_ARMS_R1.md`

Not included: `test_r14_terminal_disruption_recovery.py` (blob `3214622a7a9b5d9671b42032e82a59d1dadc9de7`, 168 lines). Landing it as-is would put a red test on the authoritative line, and the only way to green it runs through `backend/app/main.py`, which both ORD-0644/0645 and CMDR-ORDER-0650 put on the forbidden list. The call is the commander's, not mine.

## 5. The one number that will move when this lands

CMDR-DELIVER-0647's own table (`落地一枚能推进几行`) counts `backend/tests/test_r14_terminal_disruption_recovery.py` at nine rows and `backend/tests/test_r15_source_authority.py` at eight. The stamp is granted only when a row's difference set against the current tip is empty, so with this branch alone no row closes: the eight rows that gain r15 still lack r14, and the ninth row lacks both. What this branch does remove is the config hole that would have made any future caller of the already-landed `fact_acquisition.py` fail at its first invocation.
