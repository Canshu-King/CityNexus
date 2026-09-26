# ORD-0359 full-suite round

Command: `python -m pytest -q -p no:randomly` from `backend/`, interpreter
`D:/moodle/CityNexus/.venv/Scripts/python.exe` (3.12.14),
PYTHONPATH `<tree>/backend;<tree>/agent-mcp;<tree>`, database `_o359_full.db` (removed before the run).
Tree `D:/moodle/_qoder_n2_ord0359` at commit `dc25926bf80664e4f2da8dd7f16e80b1fc4243b5`, base `b6a8ea5c625d7e3e82f7348fad57d595a8a403c0`.

Separate denominator run (`--collect-only` on the same tree): 1377 tests collected, exit 0.
This round: 9 failed, 1352 passed, 15 skipped, 1 xfailed, 2 warnings in 236.13s (0:03:56)

## Failed rows, 9 of them, verbatim from the run

```
FAILED tests/test_qoder_anywhere_gates.py::test_g5_an_ai_run_that_changed_must_say_which_it_was
FAILED tests/test_qoder_anywhere_lock_duration.py::test_g9b_provider_http_never_runs_inside_an_open_write_transaction
FAILED tests/test_qoder_anywhere_matrix_truth.py::test_g14a_an_oversized_matrix_fails_closed_and_invents_no_facts
FAILED tests/test_qoder_anywhere_matrix_truth.py::test_g14c_the_verdict_must_not_depend_on_the_providers_wording
FAILED tests/test_qoder_anywhere_provider_independence.py::test_g8a_default_suite_contains_no_live_provider_calls
FAILED tests/test_qoder_anywhere_provider_truth.py::test_g10_every_normalised_place_carries_a_usable_coordinate_including_nodes
FAILED tests/test_qoder_city_failure_reasons.py::test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at
FAILED tests/test_qoder_g3_xproc_http.py::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation
FAILED tests/test_qoder_ord0296_write_deadline.py::test_G4_the_lock_wait_is_written_in_exactly_one_place
```

## Attribution against the pre-existing set

The red set recorded in `review/ord0355-r2-readings/readings.json` at run `N2R2-G` (tree without any
of my commits, blob `5310cccd7803860021386410a0308750d3887f07`) holds 10 nodeids. Compared with this
round, exactly one nodeid is new here:
`tests/test_qoder_g3_xproc_http.py::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation`.
That nodeid was already measured in isolation on both trees at 0 red / 3 attempts, tabled in
`review/ord0355-r2-readings/probe_readings.json` (blob `952ad7dbc2f8796ab37b0f0d621dfe149cae3738`),
so it is the documented whole-suite-context flake, not this order.

`tests/test_qoder_ord0359_ai_state_three_ways.py`, `tests/test_health.py`, `tests/test_contract.py`,
`tests/test_agent_runtime_gate.py`, `tests/test_v17_semantic_compiler.py` and
`tests/test_e2e_provenance.py` produced no failed row in this round.
