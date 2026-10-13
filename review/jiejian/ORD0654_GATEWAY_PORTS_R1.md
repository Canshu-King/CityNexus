# ORD-0654, gateway.py half: seven module-level names ported verbatim, plus the import the file was missing

Cut against tip `4f20a166a9cefdfc49068ef9ae0581802e60cb7e` (`refs/heads/mirror/integration-frontend-apple-pass1`), read with `git ls-remote` at the moment of the cut; the parent of the commit carrying this file is that same generation, so it is a direct child and fast-forwards.
Byte source is the representative generation `843844c5587da01287faa8f384411915eade9a87`. Nothing else in the file was touched: zero lines removed, zero lines rewritten, the additions are seven module-level blocks appended and one stdlib import inserted at the top of the import list.

## 1. The four the order names, and the three they drag along

| ported name | kind | lines on the rep generation | size | verbatim copy | already on the tip before this cut |
|---|---|---|---|---|---|
| `_latest_actionable_event` | def | 166-172 | 7 lines | yes (checked by re-reading the file bytes) | no |
| `_resolve_actionable_event` | def | 150-163 | 14 lines | yes (checked by re-reading the file bytes) | no |
| `_city_category_terms` | def | 217-221 | 5 lines | yes (checked by re-reading the file bytes) | no |
| `_city_search_terms` | def | 205-214 | 10 lines | yes (checked by re-reading the file bytes) | no |
| `_actionable_events` | def | 120-137 | 18 lines | yes (checked by re-reading the file bytes) | no |
| `_CITY_CATEGORY_ALIASES` | assign | 190-202 | 13 lines | yes (checked by re-reading the file bytes) | no |
| `_CITY_SEARCH_ALIASES` | assign | 174-189 | 16 lines | yes (checked by re-reading the file bytes) | no |
| `import re` | import | rep gateway.py line 5 | 1 line | yes | no |

gateway.py line count: 1386 -> 1477. CR bytes in the result: 0 -- the file is LF, and `.gitattributes` on this line says '*.py text eol=lf', so I did NOT convert the port to CRLF the way CMDR-DELIVER-0659 suggested; following that advice would have rewritten all 1386 lines of the file.

## 2. Why the closure had to come along (this is the part a green import hides)

The first pass appended only the four named helpers and `import app.agent.gateway` still succeeded. A scope-exact check (symtable, so a local can never mask a global) then showed four of them read module-level names that the tip does not have:

* `_resolve_actionable_event` reads `_actionable_events`
* `_city_category_terms` reads `_CITY_CATEGORY_ALIASES`
* `_city_search_terms` reads `_CITY_SEARCH_ALIASES` and `re`

All four were ported from the same file and the same generation, and the resolution check is clean now: every ported name has zero unresolved globals, and the module imports.

One instrument flaw worth naming, because it nearly shipped: my first closure pass looked for the missing standard-library import with a substring test, `"import re" in gateway.py`, and that matched the existing line `from app.core.audit import record_audit` -- the substring "import re" is inside "import **re**cord_audit". So the pass reported nothing to add and `_city_search_terms` would have gone in with a live NameError. The check is now a real module-level binding test, and that is what caught it the second time.

## 3. What moved, measured

Both gap tests were placed in the throwaway export tree (never in the shared worktree) and run with the interpreter `D:/moodle/CityNexus/.venv` 3.12.14, `-X utf8 -m pytest -q -p no:cacheprovider`.

| test | first thing that fails before this cut | first thing that fails after |
|---|---|---|
| `test_r21_autonomous_future_synthesis.py` | `cannot import name '_latest_actionable_event' from 'app.agent.gateway'` | ` cannot import name '_material_difference_fingerprint' from 'app.agent.predictive'` |
| `test_r22_opportunity_capture.py` | `cannot import name '_city_category_terms' from 'app.agent.gateway'` | ` cannot import name 'plan_authority_blocker' from 'app.services'` |

That is the boundary CMDR-DELIVER-0659 could not finish computing for r21 (its log stopped while still reporting missing symbols): after the gateway half, r21's next block is `_material_difference_fingerprint` in `app.agent.predictive`, and r22's is `plan_authority_blocker` in `app.services`. Neither file is in this order's scope, so I stopped there instead of widening the cut.

Two more names that CMDR-DELIVER-0659's chain账 lists for r21 are still absent on the tip and do live in `backend/app/agent/runtime.py` (`_model_mission_payload`, `reconcile_stale_agent_runs`). I did not port them: the chain does not reach them yet, and landing module-level code that nothing on the line can call is the same shape of debt as the searxng field I reported this morning. Say the word and they come as their own cut.

## 4. Regression

The surface is the 9 test files on the tip that import either module: `tests/test_agent_mission_runtime.py`, `tests/test_agent_runtime_state_epoch.py`, `tests/test_dsh_list_replans_bound.py`, `tests/test_hermes_r5_cached_replan_compatibility.py`, `tests/test_qoder_ord0359_ai_state_three_ways.py`, `tests/test_qoder_prompt_tool_grant_is_per_mission.py`, `tests/test_v17_semantic_compiler.py`, `tests/test_v18_2_agent_productization.py`, `tests/test_v18_3_convergence.py`.

* without the ports: `1 failed, 54 passed, 2 warnings in 3.07s`
* with the ports: `1 failed, 54 passed, 2 warnings in 3.06s`
* red set identical in both arms; the one red is pre-existing on the tip as-is: `FAILED tests/test_v18_3_convergence.py::test_release_metadata_and_map_entrypoint_are_converged`

Whole-directory collection: without `1886 tests collected, 21 errors`, with `1886 tests collected, 21 errors` (rc=2 both ways, the same 21 pre-existing collection errors) -- this cut changes neither number.

## 5. What is not in this branch

No test files (both gap tests still stop on files outside this order, so landing them would put red on the line), no `runtime.py` bytes (the `_server_completion_contract` half landed on the line while I was measuring, byte-identical to the same rep generation -- re-verified here: present and equal), no `predictive.py`, no `services.py`, no `main.py`, no `schemas.py`, no `contracts/openapi.yaml`, no dictionary file, no manifest tsv, no assertion rewritten.
