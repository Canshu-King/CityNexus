# Revolution continuation — TravelerTwin evidence aging and conflict

## Result

This continuation advances the R23 product path without reopening R23 review:

```text
voluntary USER_REJECTED outcome
  -> LEARNED_SOFT avoid:<canonical-category>
  -> bounded soft ranking signal
  -> time-decayed effective strength before expiry
  -> explicit user preference overrides the learned direction
```

The new behavior is product code exercised through the real FastAPI HTTP
surface in the disposable LAB database used by the test harness. It does not
claim a new AgentRun. The last real configured AgentRun remains the R23
positive run, `5faf3952-a8f2-4e7a-bda8-82969b9b1a74`, using
`hermes / cn:deepseek-v4.1-flash`.

## Source binding

- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Starting code SHA: `3039a7ffddab2349bf1693b836e85abb6d16c0df`
- Final experimental code SHA: `44f621b7` (`feat: age and reconcile learned traveler evidence`)
- Code commit was pushed to `origin/codex/revolution-realtrip-recovery`.
- This round's shell did not have a live Agent provider environment configured;
  no model output is represented as this round's evidence.
- The successful product-test contract explicitly set
  `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`.

## Product change

### 1. Learned evidence now ages before hard expiry

`TravelerPreferenceEvidence.expires_at` remains the hard boundary. Before it,
the snapshot now exposes:

- raw `strength`;
- `effective_strength` used for planning weight;
- `decay_factor`;
- unchanged source, evidence class, provenance, and expiry.

The factor is bounded linear freshness over `created_at -> expires_at`.
Expired rows are still marked `EXPIRED` and do not enter the snapshot. No
authority, capability, budget, opening, mobility, or commitment truth is
derived from this soft signal.

### 2. Voluntary rejection is a real negative soft signal

`avoid:<category>` is matched against canonical provider category/tags. A
candidate in the avoided category receives no soft fit from that signal; a
candidate outside it satisfies the avoidance signal. The signal changes
ranking/explanation only and cannot make an infeasible candidate feasible.

### 3. Explicit preference wins at the planning surface

When a traveler explicitly chooses the same category that learned evidence
likes or avoids, the learned item remains inspectable with
`override_state=EXPLICIT_WINS`, but is removed from the effective planning
items. This makes the existing precedence machine-effective rather than
explanation-only.

## Machine execution

The HTTP integration test created a fresh disposable Journey, selected and
started a plan, recorded a voluntary `USER_REJECTED` outcome, and invoked the
normal reflect path. The resulting TravelerTwin contained:

- `source=LEARNED_SOFT`;
- `evidence_class=VOLUNTARY_CHOICE`;
- `direction=avoid:<canonical category>`;
- positive `effective_strength`;
- bounded `0 < decay_factor <= 1`.

The same product surface then installed an explicit interest for that category.
The planner context contained the explicit item and no longer contained the
learned avoidance item, while the Twin retained the historical learned record
and marked it `EXPLICIT_WINS`.

## Focused verification

Explicit estimate-off run:

```text
$env:CITYNEXUS_LAB_ESTIMATE_AUTHORITY='false'
py -3.13 -m pytest -q tests/test_r23_adaptive_traveler_twin.py tests/test_r24_adaptive_memory.py tests/test_v7_traveler_twin.py tests/test_agent_mission_runtime.py -s
37 passed, 1 warning
```

Cross-generation regression:

```text
py -3.13 -m pytest -q tests/test_foundation_opportunity_window.py tests/test_r20_standby_trigger.py tests/test_r21_autonomous_future_synthesis.py tests/test_r22_opportunity_capture.py tests/test_r23_adaptive_traveler_twin.py tests/test_r24_adaptive_memory.py tests/test_v7_traveler_twin.py tests/test_v19_traveler_capability.py tests/test_agent_mission_runtime.py -s
74 passed, 1 warning
```

Additional checks:

- changed Python modules and tests passed `py_compile`;
- `git diff --check` passed;
- the only warning is the existing Starlette/httpx TestClient deprecation.

## Truth boundaries kept

- `LEARNED_SOFT` remains ranking/explanation context only;
- `UNKNOWN` is not converted to free or known;
- no mock mobility is relabeled live;
- no Agent prose writes authority or an active plan pointer;
- no real-user database, payment, or persistent secret was touched;
- old R20/R21 runtime JSON files in the worktree were not staged.

## Replay

1. Use the isolated worktree at code SHA `44f621b7`.
2. Run the explicit estimate-off focused command above.
3. Inspect `GET /api/v1/travelers/{traveler_id}/traveler-twin` after a
   voluntary rejection and confirm `avoid:<category>`, `effective_strength`,
   and `decay_factor`.
4. Install an explicit preference for the same category and confirm the
   learned record remains historical with `EXPLICIT_WINS`, while
   `planning_preference_items` exposes only the explicit direction.

## Next autonomous experiment

Use two successive real opportunity windows with the same traveler: let a
voluntary reject create an avoidance, wait or inject an old evidence timestamp
inside its legal TTL, and let the configured Agent compare a grounded candidate
inside and outside the avoided category. The next product question is whether
the Agent can explain and choose the softer alternative without any wrapper
pre-selecting it.
