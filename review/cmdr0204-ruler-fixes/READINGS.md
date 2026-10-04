# CMDR 02:04 rulings 1-3, ruler side only

Two shipped test files changed in this branch. 0 product bytes, 0 contract bytes, 0 OpenAPI bytes.

- `backend/tests/test_qoder_ord197_four_class_receipt.py`: r3 and r4 now take the module's own
  `_wait_closed(operation_id)` before asserting concluded fields (`outcome`, `provider_attempts`,
  `survey`). The arms used to read the row straight after `_replay_semantics` posted, so which side
  they landed on depended on when the worker happened to conclude.
- `backend/tests/test_qoder_city_failure_reasons.py`: the two 5xx expectations move from
  `PROVIDER_BAD_RESPONSE` to `PROVIDER_SERVER_ERROR`, the name the product has used for 5xx since
  the "six named reds close" commit. The malformed-payload expectation
  (`KeyError -> PROVIDER_BAD_RESPONSE`) is unchanged, so a server error and a malformed answer stay
  separately named.

Counter-checks, same tree, snapshot-restored, all four as predicted
(`cmdr0204_mutants_r2.txt`, instrument `D:/moodle/_qoder_seed_ord0489/run/cmdr0204_mutants_r1.py`):

- R1 fix present + a 0.4 s hold injected at the worker's conclusion site: `2 passed, 5 deselected` x3.
- R2 same hold, the two `_wait_closed` lines removed: `2 failed, 5 deselected` x3. The pair is the
  point: the hold is the race, and the added wait absorbs it.
- R3 worker writes `OUTCOME_PREPARED` instead of the runtime-failure outcome: r4 fails x3, at
  `test_qoder_ord197_four_class_receipt.py:508`.
- R4 product maps 5xx back to `PROVIDER_BAD_RESPONSE`: the city arm fails x3, at
  `test_qoder_city_failure_reasons.py:302` (`assert 'PROVIDER_BAD_RESPONSE' == 'PROVIDER_SERVER_ERROR'`);
  raw tail in `r4_mutant_tail.txt`.

Instrument note for ruling 1: `discriminate_r3_no_my_file_r1.py` and `discriminate_r3_fb549_r1.py`
now pair each FAILED node with its own `--tb=line` reason by position instead of searching backwards
for the nearest line containing "assert", which used to hand one reason to several nodes.
