# ORD-0359 r3 readings

Backend tip `4ef864cfa49b805e3d41b7f079f5fb4184ccec3d`. Interpreter `D:/moodle/CityNexus/.venv/Scripts/python.exe`,
printed version 3.12.14. Every row below is a live HTTP GET against a uvicorn this lane started on its own
private port, with the listening pid, that pid parent, and a marker row in that process own sqlite file.

| label | ai | ai_state | port | db file | my child pid | listening pid | its parent | parent is mine | marker |
|---|---|---|---|---|---|---|---|---|---|
| switch_off_no_key | disabled | DISABLED_BY_OPS | 8631 | _n2r3_r1.db | 25876 | 44888 | 25876 | True | N2R3-switch_off_no_key-8631 |
| switch_on_no_key | disabled | NOT_CONFIGURED | 8632 | _n2r3_r2.db | 46832 | 42592 | 46832 | True | N2R3-switch_on_no_key-8632 |
| switch_on_fake_key | enabled | CONFIGURED_UNVERIFIED | 8633 | _n2r3_r3.db | 34260 | 33876 | 34260 | True | N2R3-switch_on_fake_key-8633 |

Backend suite, run from `backend/`: 9 failed, 1367 passed, 15 skipped, 1 xfailed, 2 warnings in 176.07s (0:02:56)
`--collect-only` on the same tree: 1392 tests collected, exit 0.
Failed nodeids in that round:
- tests/test_qoder_anywhere_gates.py::test_g5_an_ai_run_that_changed_must_say_which_it_was
- tests/test_qoder_anywhere_lock_duration.py::test_g9b_provider_http_never_runs_inside_an_open_write_transaction
- tests/test_qoder_anywhere_matrix_truth.py::test_g14a_an_oversized_matrix_fails_closed_and_invents_no_facts
- tests/test_qoder_anywhere_matrix_truth.py::test_g14c_the_verdict_must_not_depend_on_the_providers_wording
- tests/test_qoder_anywhere_provider_independence.py::test_g8a_default_suite_contains_no_live_provider_calls
- tests/test_qoder_anywhere_provider_truth.py::test_g10_every_normalised_place_carries_a_usable_coordinate_including_nodes
- tests/test_qoder_city_failure_reasons.py::test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at
- tests/test_qoder_g3_xproc_http.py::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation
- tests/test_qoder_ord0296_write_deadline.py::test_G4_the_lock_wait_is_written_in_exactly_one_place

OpenAPI parity at the r3 commit: `OpenAPI 3.1.0; formal 149; runtime 149; missing 0; extra 0`.
