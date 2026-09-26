# ORD-0355 r2 readings - derived, not typed

Interpreter: D:/moodle/CityNexus/.venv/Scripts/python.exe (Python 3.12.14).
Command form: `python -m pytest -q -p no:randomly [args]`, cwd `<tree>/backend`,
PYTHONPATH=`<tree>/backend;<tree>/agent-mcp;<tree>`,
CITYNEXUS_DATABASE_URL=`sqlite:///<tree>/backend/<_*.db>` (removed before each run).
Candidate tree `D:/moodle/_qoder_n2_ord0355_r2` HEAD 6fd43627e717a97ea779da866eb4546b8acb9deb;
base tree `D:/moodle/_qoder_n2_ord0355_base7e7` HEAD 7e728268a90c9d0f4accc7f117af1de73f65bc7a.

## Named runs

| run_id | tree | collected | failed | passed | skipped | xfailed | exit | wall_s | db | raw log sha1 |
|---|---|---|---|---|---|---|---|---|---|---|
| N2R2-A | cand | 11 | 0 | - | - | - | 0 | 3.35 | _n2r2_a.db | d78421a5202853a1d0eae4da3c73099c362d40a9 |
| N2R2-B | cand | - | 0 | 11 | - | - | 0 | 3.43 | _n2r2_b.db | c7afb57dbcf6bc5e5ab22b53b1ded95db78411dd |
| N2R2-C | cand | 1369 | 0 | - | - | - | 0 | 6.91 | _n2r2_c.db | 5404b108d4f75c7a36c7be2e7318a4d575ba0a5e |
| N2R2-D | cand | - | 11 | 1342 | 15 | 1 | 1 | 175.25 | _n2r2_d.db | 80fc7386734c43067f61e4755832b49ef156aa6c |
| N2R2-E | cand | - | 11 | 1342 | 15 | 1 | 1 | 153.17 | _n2r2_e.db | a3fd5e37f1434b414f258d23f6157a3422045e02 |
| N2R2-F | base | 1358 | 0 | - | - | - | 0 | 6.53 | _n2r2_f.db | 8f87c22d2752e29340c51d7ccbd1ca5a1c4cb7fa |
| N2R2-G | base | - | 10 | 1332 | 15 | 1 | 1 | 170.42 | _n2r2_g.db | 9f85789c94afe16f4008bea98cb57316dbe1bd8e |
| N2R2-H | cand | - | 3 | 6 | - | 1 | 1 | 5.73 | _n2r2_h.db | daa8cc14c4717d0a8cf29150fbb5753212539ad3 |
| N2R2-I | base | - | 2 | 7 | - | 1 | 1 | 8.58 | _n2r2_i.db | c92504f027f31e12e89f23cc87591232a12abc0e |
| N2R2-J | base | - | 9 | 2 | - | - | 1 | 2.04 | _n2r2_j.db | 9d8a52babcfdc6358ab15df345f7ab6b344aedfc |

## Red nodeids per full-suite run

- N2R2-D (cand, log 80fc7386734c43067f61e4755832b49ef156aa6c): 11 rows
  - tests/test_qoder_anywhere_gates.py::test_g3_xproc_loser_readback_five_processes_one_operation
  - tests/test_qoder_anywhere_gates.py::test_g5_an_ai_run_that_changed_must_say_which_it_was
  - tests/test_qoder_anywhere_lock_duration.py::test_g9a_the_instrument_actually_sees_write_transactions_and_provider_calls
  - tests/test_qoder_anywhere_lock_duration.py::test_g9b_provider_http_never_runs_inside_an_open_write_transaction
  - tests/test_qoder_anywhere_matrix_truth.py::test_g14a_an_oversized_matrix_fails_closed_and_invents_no_facts
  - tests/test_qoder_anywhere_matrix_truth.py::test_g14c_the_verdict_must_not_depend_on_the_providers_wording
  - tests/test_qoder_anywhere_provider_independence.py::test_g8a_default_suite_contains_no_live_provider_calls
  - tests/test_qoder_anywhere_provider_truth.py::test_g10_every_normalised_place_carries_a_usable_coordinate_including_nodes
  - tests/test_qoder_city_failure_reasons.py::test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at
  - tests/test_qoder_g3_xproc_http.py::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation
  - tests/test_qoder_ord0296_write_deadline.py::test_G4_the_lock_wait_is_written_in_exactly_one_place

- N2R2-E (cand, log a3fd5e37f1434b414f258d23f6157a3422045e02): 11 rows
  - tests/test_qoder_anywhere_gates.py::test_g5_an_ai_run_that_changed_must_say_which_it_was
  - tests/test_qoder_anywhere_lock_duration.py::test_g9a_the_instrument_actually_sees_write_transactions_and_provider_calls
  - tests/test_qoder_anywhere_lock_duration.py::test_g9b_provider_http_never_runs_inside_an_open_write_transaction
  - tests/test_qoder_anywhere_matrix_truth.py::test_g14a_an_oversized_matrix_fails_closed_and_invents_no_facts
  - tests/test_qoder_anywhere_matrix_truth.py::test_g14c_the_verdict_must_not_depend_on_the_providers_wording
  - tests/test_qoder_anywhere_provider_independence.py::test_g8a_default_suite_contains_no_live_provider_calls
  - tests/test_qoder_anywhere_provider_truth.py::test_g10_every_normalised_place_carries_a_usable_coordinate_including_nodes
  - tests/test_qoder_city_failure_reasons.py::test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at
  - tests/test_qoder_g3_xproc_http.py::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation
  - tests/test_qoder_ord0296_write_deadline.py::test_G4_the_lock_wait_is_written_in_exactly_one_place
  - tests/test_qoder_ord197_four_class_receipt.py::test_r3_an_empty_answer_proves_it_came_from_a_reply_and_not_from_an_outage

- N2R2-G (base, log 9f85789c94afe16f4008bea98cb57316dbe1bd8e): 10 rows
  - tests/test_qoder_anywhere_gates.py::test_g5_an_ai_run_that_changed_must_say_which_it_was
  - tests/test_qoder_anywhere_lock_duration.py::test_g9a_the_instrument_actually_sees_write_transactions_and_provider_calls
  - tests/test_qoder_anywhere_lock_duration.py::test_g9b_provider_http_never_runs_inside_an_open_write_transaction
  - tests/test_qoder_anywhere_matrix_truth.py::test_g14a_an_oversized_matrix_fails_closed_and_invents_no_facts
  - tests/test_qoder_anywhere_matrix_truth.py::test_g14c_the_verdict_must_not_depend_on_the_providers_wording
  - tests/test_qoder_anywhere_provider_independence.py::test_g8a_default_suite_contains_no_live_provider_calls
  - tests/test_qoder_anywhere_provider_truth.py::test_g10_every_normalised_place_carries_a_usable_coordinate_including_nodes
  - tests/test_qoder_city_failure_reasons.py::test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at
  - tests/test_qoder_ord0296_write_deadline.py::test_G4_the_lock_wait_is_written_in_exactly_one_place
  - tests/test_sol_guardian_projection.py::test_guardian_status_lists_runs_newest_first

## Stable across both trees: 9 nodeids (red in N2R2-D, N2R2-E and N2R2-G)
- tests/test_qoder_anywhere_gates.py::test_g5_an_ai_run_that_changed_must_say_which_it_was
- tests/test_qoder_anywhere_lock_duration.py::test_g9a_the_instrument_actually_sees_write_transactions_and_provider_calls
- tests/test_qoder_anywhere_lock_duration.py::test_g9b_provider_http_never_runs_inside_an_open_write_transaction
- tests/test_qoder_anywhere_matrix_truth.py::test_g14a_an_oversized_matrix_fails_closed_and_invents_no_facts
- tests/test_qoder_anywhere_matrix_truth.py::test_g14c_the_verdict_must_not_depend_on_the_providers_wording
- tests/test_qoder_anywhere_provider_independence.py::test_g8a_default_suite_contains_no_live_provider_calls
- tests/test_qoder_anywhere_provider_truth.py::test_g10_every_normalised_place_carries_a_usable_coordinate_including_nodes
- tests/test_qoder_city_failure_reasons.py::test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at
- tests/test_qoder_ord0296_write_deadline.py::test_G4_the_lock_wait_is_written_in_exactly_one_place

## Differing nodeids, isolated repeats

| nodeid | cand red/attempts | base red/attempts | raw log sha1 (first red seen) |
|---|---|---|---|
| tests/test_qoder_anywhere_gates.py::test_g3_xproc_loser_readback_five_processes_one_operation | 1/3 | 0/3 | 38268224eeb975692394985a4ffe66b56ed38526 |
| tests/test_qoder_g3_xproc_http.py::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation | 0/3 | 0/3 | - |
| tests/test_qoder_ord197_four_class_receipt.py::test_r3_an_empty_answer_proves_it_came_from_a_reply_and_not_from_an_outage | 1/3 | 1/3 | 5299a2316780efc974880bd4da78033ef29443a0 |
| tests/test_sol_guardian_projection.py::test_guardian_status_lists_runs_newest_first | 0/3 | 0/3 | - |
| tests/test_qoder_anywhere_gates.py::test_g3_xproc_loser_readback_five_processes_one_operation (6 more per side) | 0/6 | 0/6 | none red |

## Set arithmetic (computed above from the rows in this file)
- candidate(D|E) minus base(G) = 3 nodeids:
  - tests/test_qoder_anywhere_gates.py::test_g3_xproc_loser_readback_five_processes_one_operation
  - tests/test_qoder_g3_xproc_http.py::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation
  - tests/test_qoder_ord197_four_class_receipt.py::test_r3_an_empty_answer_proves_it_came_from_a_reply_and_not_from_an_outage
- base(G) minus candidate(D&E) = 1 nodeids:
  - tests/test_sol_guardian_projection.py::test_guardian_status_lists_runs_newest_first
