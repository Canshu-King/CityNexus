# CityNexus Revolution Lab — R6 cursor repair result

## Scope and binding

- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- cursor-round starting source commit: `0dfe2621c254d16c9e65dc8189433fd7e3ae6c78`
- cursor-round final source commit: `e8c13a1e63b7075fbb2a63cb51d5e39c5658c73b`
- disposable database only; no authority/mainline merge; `P7=false`

## Defect reproduced

DeepSeek's final R6 review found that the Journey was `PLANNED` with active plan
`09715a08-4e06-57b7-bebc-b9a5adf872a2`, but `current_activity_id` still named an activity from
the replaced plan chain. The Twin correctly reported `STALE`, so this was not merely a report
wording issue: the Journey pointer and execution projection disagreed.

Before the repair, machine evidence was:

```text
Journey.status = PLANNED
Journey.active_plan_version_id = 09715a08-...
Journey.current_activity_id = bc23dc8e-5f91-5994-af00-0771d47bc084
```

## Bounded repair

Commit `e8c13a1e` makes plan selection clear a non-null cursor whenever the Journey is not
executing. It also repairs the already-current/idempotent selection path, so a retry cannot leave
an old cursor behind. Active journeys keep the existing re-anchoring behavior.

No plan, activity, mobility fact, identity, cost, opening-hours, payment, booking, or authority
decision was fabricated or changed by this repair.

## Same-destination real product replay

The same Suzhou Journey and selected plan were used. A real HTTP POST to:

```text
POST /api/v1/journeys/9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2/plans/09715a08-4e06-57b7-bebc-b9a5adf872a2/select
```

returned HTTP 200. The readback changed:

```text
before current_activity_id = bc23dc8e-5f91-5994-af00-0771d47bc084
after  current_activity_id = null
```

Final product readback:

- Journey: `PLANNED`
- active plan: `09715a08-4e06-57b7-bebc-b9a5adf872a2`
- Twin projection: `READY`
- execution cursor: `ABSENT_FALLBACK`, persisted cursor `null`
- Scene mobility: 3 total / 3 hard-eligible
- `all_actual_edges_hard_eligible=true`

The selected plan's official facts and live mobility evidence remained unchanged:

- 网师园: OSM `way/44679452`, official municipal source id=45, official opening and seasonal
  cost verified;
- 拙政园: OSM `way/468359738`, official municipal source id=58, official opening and seasonal
  cost verified;
- all three actual edges: `valhalla-http`, `LIVE_PROVIDER_CAPTURE`, non-degraded,
  `HARD_ELIGIBLE`.

## DeepSeek execution

Final native run:

- run: `7f1060cd-f305-4ea2-9146-a8fef22c8ad2`
- runtime: `NATIVE_DEEPSEEK_TOOL_LOOP`
- status: `COMPLETED`
- autonomy: `PLAN_ONLY`
- tool calls: 11, all read-only
- no replan, booking, payment, or evidence fabrication

DeepSeek independently confirmed the cursor repair, `READY` projection, selected plan pointer,
official source bindings, and 3/3 live hard-eligible mobility edges. Its only qualification was
that the cursor check was indirect because the current agent tool surface does not expose a full
plan activity list; the machine Journey/Twin readbacks above are the authoritative state proof.

Hermes remains honestly unconfigured (`configured=false`, `reachable=false`, `ready=false`); no
Hermes trace is claimed.

## Focused tests

```text
55 passed, 2 warnings
```

Suites:

- `tests/test_qoder_current_plan_is_named.py`
- `tests/test_revolution_r77_recovery.py`
- `tests/test_agent_runtime_gate.py`
- `tests/test_qoder_mobility_evidence_sources.py`
- `tests/test_qoder_catalog_reason_code.py`

The warnings are the existing Starlette/httpx deprecation warnings.

## Result

The same destination remains on a real selected, user-visible product plan, and the stale cursor
truth gap is repaired and replayed. No real-world execution was started, which is intentional.

Next autonomous experiment: inspect the duplicate provider entities named 网师园 in the exact
catalog and prove whether any planner candidate source can select the generic node instead of the
OSM-bound way. Keep ambiguity fail-closed; do not alias, fuzzy-match, or merge identities without
provider-backed proof.

