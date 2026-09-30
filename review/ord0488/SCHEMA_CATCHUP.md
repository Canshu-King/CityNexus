# ORD-0488 — the schema a new generation declares, and whether a boot really delivers it

Base read off `refs/heads/mirror/integration-frontend-apple-pass1` at start:
`dcb90cccc68b81f2317b28db19051dedb9f06c80`.
Everything below is a reading taken in this session, not a restatement of the order.

## 1. Which path creates the tables

Not `create_all`, not a migration tool:

- `Base.metadata.create_all` appears in the tree exactly once outside the `review/` snapshots -- and
  that one is inside a test (`backend/tests/test_v6_enrollment.py:15`), so no boot reaches it.  The
  reading is `git grep -n create_all dcb90ccc | grep -v ':review/'`, which returns that single line.
- There is no alembic: `git ls-tree -r --name-only dcb90ccc | grep -i alembic` returns nothing, and
  the only files matching `migrat` are `backend/tests/test_sol_migration_truth.py`,
  `docs/LEGACY_E2E_MIGRATION.md` and two `review/ord0459/*` scripts.
- The boot itself applies the DDL: `backend/app/main.py:494` calls `ensure_schema()`, which is
  defined at `backend/app/db/session.py:588` and reaches the DDL at its
  `raw.executescript(sql)` on `backend/app/db/session.py:611` (line numbers are of THIS ref, whose
  `session.py` runs `1116` lines against the base's `1070`, a net `46` longer).
- That DDL is replayable by construction: all `59` `CREATE TABLE` statements carry
  `IF NOT EXISTS`, and all `36` `CREATE INDEX` statements do too. So a store that predates a table
  grows it on its own next boot -- which is why the shared preview store is stale rather than
  broken: nothing restarted it.

The instrument for this is `live_checks/ord0488_schema_catchup_r1.py`, three modes, re-runnable:
`--mode declared`, `--mode inspect --db PATH` (opens `mode=ro` only), `--mode boot --db PATH`
(boots the product's own startup path against PATH, then inspects).  `--mode inspect --routes` and
`--mode boot` against the shared store are **refused in code**, because importing the app writes and
this order says read-only there.

## 2. The shared preview store, read strictly `mode=ro`

`inspect_shared_preview_mode_ro.txt`:

```
declared_count: 59   present_count: 55
missing_in_db: journey_checkins, journey_members, journey_role_capabilities, journey_share_grants
present_not_declared: []
models_missing_from_ddl: []
```

Two corrections to the order's framing, both from what the files actually say:

- the fourth missing table is `journey_role_capabilities`, which the order did not list;
- two of the three named ones are really `journey_share_grants` and `journey_members`.  Searching
  the store for `share_grants` / `members` as bare names comes back empty because those words are
  the *door* names (`contracts/openapi.yaml` paths), not the table names.

Row census, same connection, still `mode=ro`: `journeys` 1, `plan_versions` 1, `activities` 6,
`places` 16, `travelers` 1 -- matching the order.

**What touching it did and did not cost**: `_preview.db` stayed at `7,213,056 B` with mtime
`Sep 29 09:20` and `_preview.db-wal` at `0 B` throughout.  The sidecar `_preview.db-shm` did move
(`11:36` -> `11:37`) during my first read: WAL readers write read-marks into shared memory, so a
read-only open of a live WAL store is not literally zero-impact on that sidecar.  I am not claiming
"nothing was touched" -- the store's own bytes and its WAL were not.

## 3. Can a from-zero environment serve every door? Yes, and here is the denominator

`route_denominators.txt`, measured on the delivered tree:

| reading | value |
| --- | --- |
| `openapi_paths` | 151 |
| `openapi_operations` | 166 |
| `app.routes` objects under `/api/v1` | 166 |
| `(method, path)` pairs | 166 |

The order's `151` is the **path** count; the same tree exposes `166` operations over those `151`
paths, which is the denominator ORD-0478 counts (`164` at `0dabe642`, grown by the two ORD-0476
doors).  Saying "all 151 routes" and measuring 166 is the same fact under two denominators.

The table question answers yes on both paths:

- `boot_B_from_zero.txt` -- a store that did not exist, booted through `import app.main`:
  `present_count: 59`, `missing_in_db: []`, child exit `0`.
- `boot_A_stale_copy_of_preview.txt` -- a **copy** of the preview store at `55` tables, booted once
  through the same path: `present_count: 59`, `missing_in_db: []`.  The four tables arrive.
- `models_missing_from_ddl: []` on both, which is the invariant that makes this hold for the *next*
  model too: `ensure_schema` applies only `schema.sql`, so an ORM table absent from the DDL is a
  table no boot can ever create.

## 4. The named process, and the test that can go red

`ensure_schema()` used to return `None`, so "healed four tables" and "healed nothing" printed the
same thing.  It now returns and records `SCHEMA_CATCHUP` (`database` / `before` / `after` /
`created`) and logs the created names through `logging.getLogger("citynexus.schema")`, published
only after the transaction commits.  The operator door is
`backend/db/apply_schema_catchup.py`, in the shape of `apply_ord0355_stay_budget_declared.py`:
report-only by default (read-only open), `--apply` to heal, and it refuses the shared store
(`operator_refusal_shared_store.txt`).

Before/after taken off a fresh copy, not off an already-healed one:

- `operator_before_apply_fresh_copy.txt` -> present 55, missing 4, named one per table
- `operator_after_apply_fresh_copy.txt` -> `catch-up created: 4 [...]`, `still missing after --apply: 0`

`backend/tests/test_qoder_ord0488_schema_catchup.py`, 4 cells, `--collect-only` reports
`4 tests collected` (`collect_only.txt`) and the run is `4 passed`
(`mutant_Z_after_restore_green.txt` shows the same four green on a restored tree):

1. `..._from_zero_boot_delivers_every_declared_table`
2. `..._every_model_table_is_declared_in_the_ddl`
3. `..._dropping_a_preview_missing_table_then_booting_heals_it` -- one pass per named table, and the
   assertion is on **column declarations and index names** equal to the from-zero build, not on the
   name reappearing
4. `..._the_catch_up_report_is_named_and_complete` -- field set, `before`/`after` counts, and the
   created list named table by table

Counter-examples, each run in its own exported tree (`backend` + `data` + `contracts` at
`c3d1b8b3`), pristine run first: `4 passed`:

| id | mutation | verdict | cells that fired |
| --- | --- | --- | --- |
| M1 | `executescript(sql)` and its fallback loop replaced by `pass` -- the heal is gone | 3 failed, 1 passed | 1, 3, 4 |
| M2 | DDL still applies, `created` hardcoded to `[]` -- the heal is silent | 2 failed, 2 passed | 3, 4 |
| M3 | the `journey_checkins` `CREATE TABLE` block deleted from `schema.sql` (`1,203 B`) | 4 failed | 1, 2, 3, 4 |
| Z | both files restored | 4 passed | -- |

M1 and M2 are the two directions the order asked for, and they are not one assertion in two
costumes: M2 keeps cells 1 and 2 green, which is what proves cell 4 judges the *report* rather than
the database, and M1 keeps cell 2 green, which is what proves cell 2 is a static claim about the DDL
and not a second copy of cell 1.  Every mutation was asserted to have landed (anchor appeared
exactly once, replaced text present, old text absent) before it was believed.

## 5. Blast radius, and what was NOT run

`session.py` changed by `48` added / `2` removed lines and the only behavioural difference to an
existing path is a return value plus one log line.  Measured, not assumed:

- `grep` over `backend/tests` shows the return value is consumed only by the new file (2 hits, both
  in `test_qoder_ord0488_schema_catchup.py`).
- the `18` modules that call `ensure_schema` plus `test_contract.py` run `153 passed, 2 failed`
  (`slice_ensure_schema_callers_after.txt`).
- both failures reproduce verbatim at the **unmodified** tip `dcb90cccc68b81f2317b28db19051dedb9f06c80`
  (`baseline_unmodified_tip_two_files.txt`): `test_qoder_ord0296_write_deadline.py::test_G4...`
  with the identical diff line `At index 2 diff: 'main.py' != 'session.py'`, and
  `test_qoder_g3_xproc_http.py::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation`
  with a `10061` connection refused from its own worker.  My red set is a subset of that baseline,
  not a new entry in it.

Not run, and named so it does not read as a claim: the full backend suite (a single full run is an
observation, not a baseline, and I had no unmodified-tip full-suite baseline to diff against), the
frontend build, and any e2e.  No product behaviour was changed for the shared preview store: it was
never written, never healed, never restarted, and `POST /api/v1/demo/reset` was never called.
Ports `:8000` / `:4781` / `:4782` / `:8693` were not touched and I started no service of my own.
