# ORD-0471 — the ten red cells on the main execution path

Verdict: **this commit introduced them** — `02d4edec85eb19b4db42c1093769582c4c2fbbba`
(ORD-0437 batch 1, "the local import doors"). It is not a schema rename and no field was renamed.

## The defect

`/api/v1/journeys/{journey_id}/trip-studio/preview` was one of two paths stacked on a single
handler. Python applies decorators bottom-up, so two `@app.post` lines sitting directly above a
`def` register that function under both paths:

```
backend/app/main.py:6404  @app.post("/api/v1/journeys/{journey_id}/trip-studio/preview")   (8eb72e55)
backend/app/main.py:6405  @app.post("/api/v1/journeys/{journey_id}/plans/preview-reorder") (8eb72e55)
backend/app/main.py:6406  def trip_studio_preview(                                         (8eb72e55)
```

ORD-0437 batch 1 inserted its POI-import section **between those two decorator lines**, stranding
the first one. A stranded decorator binds whichever function comes next — here `poi_import_parse`:

```
backend/app/main.py:6524  @app.post("/api/v1/journeys/{journey_id}/trip-studio/preview")   (02d4edec .. 4037cb33)
backend/app/main.py:6525  # --- ORD-0437: POI text/link import ---                          (02d4edec .. 4037cb33)
backend/app/main.py:6528  @app.post("/api/v1/journeys/{journey_id}/poi-import/parse", ...)  (02d4edec .. 4037cb33)
backend/app/main.py:6529  def poi_import_parse(                                             (02d4edec .. 4037cb33)
```

So a `TripStudioPreviewRequest` body (`{"activity_ids": [...]}`) was validated against
`PoiImportParseRequest` (`backend/app/schemas.py:962`), whose own boundary is
`model_config = ConfigDict(extra="forbid")` (`backend/app/schemas.py:963`). Because that model's
only field is `text: str = Field(default="")` (`backend/app/schemas.py:964`), the body is not
missing anything — it is rejected for the one extra key, which is the exact single error reported:

```
{"loc":["body","activity_ids"],"msg":"Extra inputs are not permitted","type":"extra_forbidden"}
```

FastAPI resolves a path to the first route registered for it, and the stranded registration happens
~225 lines earlier in the module than the real one, so the real handler was unreachable on that
path.

## Proof: the route table, read from the app, four generations

Each file in this directory lists `(method, path) -> [handler]` taken from `app.routes` after
importing `app.main` in that generation's own tree:

| reading | `POST .../trip-studio/preview` binds | api routes | file |
| --- | --- | --- | --- |
| `8eb72e5579900f5f315e4d0d65a52e727494d199` (parent) | `trip_studio_preview` | 162 | `routes_8eb72e55_parent.txt` |
| `02d4edec85eb19b4db42c1093769582c4c2fbbba` (first red) | `poi_import_parse` | 164 | `routes_02d4edec_first-red.txt` |
| `83e676aab7376a893e03d22d8c2b3ea4d0ca85bf` (22:06 tip) | `poi_import_parse` | 164 | `routes_83e676aa_before.txt` |
| this commit, on `4037cb331ea00b83124316d40329762fa1131689` | `trip_studio_preview` | 164 | `routes_4037cb33_after.txt` |

`poi-import/parse` and `poi-import/add` keep their own handlers in all four readings and the route
count is 164 before and after the fix, so the stranded decorator was a *second* registration of
`poi_import_parse` and removing it costs POI nothing.

## Proof: the two named files, run standalone

Interpreter `D:/moodle/CityNexus/.venv/Scripts/python.exe` (CPython 3.12.14) with pytest 8.4.2,
`-p no:cacheprovider`, `DEEPSEEK_API_KEY` unset, one exported tree per commit
(`git archive <sha>` of `backend data contracts tools scripts agent-mcp frontend qoder-handoff review`
plus every root file), cwd = that tree's `backend/`. No uvicorn was started in any of those cwds;
none of `:8000` / `:4781` / `:4782` / `:8693` was touched.

| tree | result | receipt |
| --- | --- | --- |
| `8eb72e5579900f5f315e4d0d65a52e727494d199` | 25 passed, 0 failed | `pytest_8eb72e55_parent.txt` |
| `02d4edec85eb19b4db42c1093769582c4c2fbbba` | 10 failed, 15 passed | `pytest_02d4edec_first-red.txt` |
| `83e676aab7376a893e03d22d8c2b3ea4d0ca85bf` | 10 failed, 15 passed | `pytest_83e676aa_tip-before.txt` |
| this commit on `4037cb331ea00b83124316d40329762fa1131689` | 25 passed, 0 failed | `pytest_4037cb33_tip-after.txt` |

The two red receipts are separate runs (md5 `c0ee472d81aef4a086a46c5ffb2b0c7a` vs
`821ce8a717b34512ffb39126e6394162`, disjoint `trace_id` values, 23.41 s vs 31.16 s). Their FAILED
sets were compared with a non-empty guard on both sides (10 lines each) and are the same 10 nodeids —
so the ten cells are one family, not drift.

The ten coordinates, read back from `--tb=line` on the `83e676aa` tree
(`red_lines_83e676aa.txt`, 10 traceback lines):

- `backend/tests/test_v13_integrity.py:365`, `:426`, `:451`, `:474`, `:496`, `:522`, `:592`, `:829` — 8 cells
- `backend/tests/test_v12_authoritative_trip_execution.py:165`, `:202` — 2 cells

Six print `assert (422 == 200)`; two (`:365`, `:592`) print the whole 422 envelope carrying
`extra_forbidden`; the same `extra_forbidden` payload sits under all ten.

## Collateral checked

`backend/tests/test_qoder_ord0437_poi_import.py` — the only backend file naming POI import — is
9 passed before (`pytest_ord0437_poi_before.txt`, taken in the `83e676aa` tree) and 9 passed after
(`pytest_ord0437_poi_after.txt`, taken in this commit's tree). Nothing else under `backend/tests/`
mentions `trip-studio/preview` besides the two named files.

## The fix

`backend/app/main.py`: 1 line deleted, 2 lines added (the decorator back on the stack above
`def trip_studio_preview`, plus one comment stating the constraint so the next banner insertion has
something to hit). No test byte, no assertion, no skip, no `extra` mode changed, no file deleted.
`extra="forbid"` on `PoiImportParseRequest` is left exactly as ORD-0437 designed it.

No bytes changed in `backend/app/schemas.py`, `contracts/openapi.yaml`,
`frontend/src/generated/api.ts`, or any test. The contract never renamed this door:
`contracts/openapi.yaml:1418` declares `/journeys/{journey_id}/trip-studio/preview` as the primary
path with request schema `TripStudioPreviewRequest` (`contracts/openapi.yaml:1427`), and
`contracts/openapi.yaml:1435` declares `/journeys/{journey_id}/plans/preview-reorder` as an alias by
`$ref` to it (`contracts/openapi.yaml:1439`). The generated client mirrors the same shape
(`frontend/src/generated/api.ts:1238`) and the caller uses the primary path
(`frontend/src/api/v12Authoritative.ts:56`). Both paths were always meant to reach one handler, which
is what the restored stack does — so there was no rename to document and no caller to migrate.

## Not the cause

`10dc3654aeffbe791ca213f1359533c7e2938250` (ORD-0437 batch 24) was named as the prime suspect because
it changed `backend/app/schemas.py`. What it actually changed is 8 files:
`evidence/qoder-ord0437-20260929/control_exits_geometry_r1.log`,
`evidence/qoder-ord0437-20260929/exp_mine_r11b.json`,
`evidence/qoder-ord0437-20260929/gate_r32.log`,
`evidence/qoder-ord0437-20260929/gate_r33.log`,
`evidence/qoder-ord0437-20260929/tsc_r11b.txt`,
`frontend/tests/e2e/qoder-ord0437-poi-import-chain.spec.ts`,
`frontend/src/features/poiimport/PoiImportPanel.tsx`,
`frontend/src/features/poiimport/poi-import.css`.
No `backend/app/schemas.py`, and no backend file at all.

Also refuted: `activity_ids` is present and unchanged at `backend/app/schemas.py:570` in
`8f7172ee426f9fdac4906bc81c353ddbf4036f7d`, `10dc3654aeffbe791ca213f1359533c7e2938250` and
`83e676aab7376a893e03d22d8c2b3ea4d0ca85bf` alike, so no alias for an old caller is owed either —
the old callers were never calling a renamed field, they were reaching a different function.
