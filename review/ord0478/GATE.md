# ORD-0478 — the route-ownership gate for the ORD-0471 family

Instrument: `backend/tests/test_qoder_ord0478_route_ownership.py` (5 cells).
Judged base: `0dabe64223036391a6c25561a6b606e1533f3704`.
Product bytes changed: none. No test was edited, skipped, or deleted.

## Why a new instrument and not an existing one

`backend/tests/test_contract.py:16` builds `{(route.path, method) ...}` and `:39` asserts
`expected <= routes` — set membership of paths.  It never asks which function answers, which is
exactly the hole ORD-0471 fell through: at `83e676aab7376a893e03d22d8c2b3ea4d0ca85bf` the path
`/api/v1/journeys/{journey_id}/trip-studio/preview` was registered, present in that set, and
answered by `poi_import_parse`.  `grep -l 'app.routes' backend/tests/` names three pre-existing files (`test_contract.py`,
`test_qoder_anywhere_contract_parity.py`, `test_qoder_ord0402_recycle_bin.py`).  None of them reads
the handler off a route: `grep -n 'route\.endpoint\|\.endpoint\b'` over `backend/tests/` returns 0
code hits, and the single `endpoint` token in the parity file sits inside a docstring
(`backend/tests/test_qoder_anywhere_contract_parity.py:86`).  This gate is the first instrument in
the suite that asserts path↔handler, so nothing was duplicated.

## What it asserts, cell by cell

All five read `app.main:app`'s own route table (`route.path`, `route.methods`, `route.endpoint.__name__`),
the same object Starlette dispatches on.  No socket, no row, no fixture.

- **C1** `test_ord0478_every_owned_cell_is_registered_exactly_once` — no `(method, path)` key carries
  two handlers (a duplicate registration is first-wins, so the second handler is dead code), and all
  six owned cells are present.
- **C2** `test_ord0478_each_cell_resolves_to_the_named_handler` — each cell resolves to exactly
  `[<named handler>]`.  The declared six: `trip-studio/preview` and `plans/preview-reorder` →
  `trip_studio_preview`; `trip-studio/accept` and `plans/accept-reorder` → `trip_studio_accept`;
  `poi-import/parse` → `poi_import_parse`; `poi-import/add` → `poi_import_add`.
- **C3** `test_ord0478_each_alias_pair_shares_one_handler` — an alias pair must reach the *same*
  handler, not merely both exist.  This is the invariant ORD-0471 broke.
- **C4** `test_ord0478_the_two_door_families_never_answer_for_each_other` — no `poi_import_*` handler
  answers a trip-studio/reorder path and no `trip_studio_*` handler answers a poi-import path.
- **C5** `test_ord0478_no_unlisted_route_joins_the_family` — every registered api path wearing one of
  the family markers (`trip-studio`, `poi-import`, `preview-reorder`, `accept-reorder`) is declared in
  the table, so a new door cannot join unwatched.

## Readings

| run | verdict | receipt |
| --- | --- | --- |
| base `0dabe642`, gate alone, `-v` | 5 passed | `gate_base_0dabe642_green.txt` |
| base `0dabe642`, `--collect-only` | 5 tests collected | `collect_only.txt` |
| base, gate + `test_contract.py` + both ORD-0471 files | 34 passed | `combined_session.txt` |

The 34 is the sum of the per-file denominators, each measured in its own run: gate 5,
`test_contract.py` 4, `test_v13_integrity.py` 22, `test_v12_authoritative_trip_execution.py` 3.
POI family `test_qoder_ord0437_poi_import.py` measured 9 passed separately.
Interpreter `D:/moodle/CityNexus/.venv/Scripts/python.exe` (CPython 3.12.14), pytest 8.4.2,
`DEEPSEEK_API_KEY` unset, `-p no:cacheprovider`, cwd = that tree's `backend/`.

## The two counter-examples, plus a third that is the real thing

Every mutant tree is a full `git archive` export with only the gate file added; each ran the gate
alone in its own cwd, so nothing in the base tree was touched.

| id | what was changed | verdict | cells that fired | receipt |
| --- | --- | --- | --- | --- |
| 甲 | `backend/app/main.py` line 6750 (`@app.post("...trip-studio/preview")`) deleted — the stacked decorator pulled off its handler | 3 failed, 2 passed | C1, C2, C3 | `mutant_jia.txt` |
| 乙 | same line's path rewritten to `.../poi-import/parse` — a second registration of a live door | 4 failed, 1 passed | C1, C2, C3, C4 | `mutant_yi.txt` |
| 丙 | the historical defect itself: base swapped for `02d4edec85eb19b4db42c1093769582c4c2fbbba`, the commit that stranded the decorator | 3 failed, 2 passed | C2, C3, C4 | `mutant_bing.txt` |

The pair is complementary, which is what makes both directions real rather than one assertion
wearing two costumes:

- 甲 removes the path from the table, so only C1 can see it — C4 stays green there, because nothing
  crossed families; the path simply left.
- 丙 keeps the path registered exactly once, so C1 passes and C2/C3/C4 fire.  C2's message reads
  `POST /api/v1/journeys/{journey_id}/trip-studio/preview -> ['poi_import_parse'], wanted
  'trip_studio_preview'` — the ORD-0471 shape named in one line, which is the sentence that had to
  exist and did not.
- 乙 is 甲's shadow variant and is the only run that exercises C1's duplicate-registration arm:
  `('POST', '.../poi-import/parse'): ['poi_import_parse', 'trip_studio_preview']`.

Both mutants were checked to still parse (`ast.parse`) before running, so each red is a route-table
reading and not a broken file.

## Scope honesty

The gate pins six cells, not the whole 164-route table — 164 is the count the same probe reports at
`0dabe642`.  Widening it to every path would need a declared owner for all 164, which is a different
order.  It is a backend test: it cannot see a frontend caller that starts posting to a renamed door,
and it deliberately does not try to — `contracts/openapi.yaml:1435` `$ref`ing
`contracts/openapi.yaml:1418` is the contract half and is untouched here.
