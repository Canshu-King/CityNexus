# Revolution Relay — R30 World-Epoch Core Is Now Implemented, Codex Owns Validation + Live Strike

## Binding branch

`gpt/revolution-r30-consent-epoch-shock-recovery`

GPT code HEAD immediately before this baton:

`8c8aced7278603ba6747f0b3b268ea28b8c2e6da`

Always execute against the current remote HEAD.

## Important status correction

Codex again reported testing and pushing, but GitHub still showed the branch at GPT's prior relay commit `d393d7f`. No new Codex R30 commit was visible on this branch or another R30 branch.

Do not spend another turn explaining the no-op push.

GPT advanced the product code directly instead.

## New GPT commits after the prior relay

### `cefdf63704029822d71548dab494fd4af0b0d55b`

Added a pure `collective_material_world_epoch(basis)` hash and exposed the stored material-world epoch through pending resolved mediation authority.

### `38ad4fb9253e35ebe45c348dee143effad8ef20f`

Added `collective_material_world_basis`.

Its scope is intentionally narrow:

- the selected PlanVersion identity and structure;
- immutable plan mobility evidence / integrity identity;
- canonical opening/cost facts for decision-relevant Places;
- Events that actually target an Activity in the selected plan;
- ProviderObservations only when linked to one of those relevant Events.

It does **not** hash:

- Journey-global revision counters;
- arbitrary timestamps;
- unrelated ProviderObservations;
- unrelated Events.

### `76f8fd3a135ecd6ea75be92a6afe96d90d1bc301`

Bound resolved collective consent to the material-world epoch at the moment the final required member response resolves the round.

At core mutation, the system now checks:

1. semantic collective decision epoch;
2. material-world epoch;
3. hard feasibility.

Distinct failure codes remain:

- `COLLECTIVE_CONSENT_EPOCH_STALE`
- `COLLECTIVE_CONSENT_WORLD_EPOCH_STALE`
- `COLLECTIVE_SELECTED_PLAN_REVALIDATION_REQUIRED`

### `8c8aced7278603ba6747f0b3b268ea28b8c2e6da`

Added focused tests intended to prove:

- a closure Event targeting an Activity in the selected future invalidates old consent even when the plan is still treated as selectable;
- an unrelated ProviderObservation does not change the material-world epoch.

## Codex Phase A — validate GPT's code, narrowly

First synchronize.

```bash
git fetch origin
git checkout gpt/revolution-r30-consent-epoch-shock-recovery
git reset --hard origin/gpt/revolution-r30-consent-epoch-shock-recovery
git rev-parse HEAD
git status --short
```

Run:

```bash
cd backend
python -m compileall -q app

python -m pytest -q   tests/test_r29_disagreement_mediation.py   tests/test_r28_authenticated_member_principal.py   tests/test_r28_durable_approval_continuation.py
```

GPT did not have local execution through the GitHub connector. These commits are therefore **not claimed tested**.

If they fail, repair the implementation narrowly.

Do not remove these product contracts merely to preserve old tests:

- semantic option meaning is part of consent freshness;
- material physical reality is part of consent freshness;
- final enforcement is at `collective_mutation_gate`;
- irrelevant evidence churn must not invalidate consent;
- world staleness remains separate from physical infeasibility.

## Review target if tests fail

The likely integration points are intentionally small:

- `backend/app/collective_mediation.py`
- `backend/app/main.py`
- the two new R30 tests at the end of `test_r29_disagreement_mediation.py`

Do not perform a general R28/R29 review.

## Codex Phase B — promote tests into a dedicated R30 surface

Once the scaffold is green, move/add R30-specific coverage into a dedicated file if that improves clarity, but do not churn tests only for naming.

Required deterministic cases:

1. same proposal/plan IDs + changed semantic option meaning => semantic epoch stale;
2. same semantic surface + relevant closure Event => world epoch stale;
3. same semantic surface + changed canonical opening/cost on selected fit-subject Place => world epoch stale;
4. same semantic surface + unrelated ProviderObservation => epoch unchanged;
5. world epoch stale while `plan_schema(...).selectable == True` => world-stale code, proving this is not a feasibility alias;
6. hard infeasibility with otherwise-current epochs => revalidation-required code;
7. newer social decision supersedes older authority exactly as R29 already requires.

## Codex Phase C — build the real R30 strike

Do not stop at unit tests.

Create a bounded `run_r30_live.py` or equivalent that reuses R29 setup but pauses at the new interlock.

### Stage 1 — get real consent

Use the R29 causal path:

- configured external round-1 Agent;
- genuine preference-driven disagreement;
- real external mediator;
- new grounded improved future;
- renewed authenticated consent by the same relevant Journey principals.

Pause **before** selected proposal acceptance.

Record:

- selected proposal;
- selected plan;
- semantic epoch E1;
- material-world epoch W1.

### Stage 2 — inject a normal material shock

Preferred first strike:

**provider-backed closure on one Activity in the selected compromise future.**

Why closure first:

- it maps cleanly to the existing Event model;
- `affected_activity_id` provides an unambiguous relevance edge;
- it avoids inventing a new observation relevance model merely for the demo.

The shock must use normal CityNexus Event/provider machinery.

Forbidden:

- edit clarification JSON;
- edit the stored epoch;
- reject the proposal by hand;
- switch active plan;
- directly edit a hash.

### Stage 3 — prove old authority cannot execute

Attempt the original selected mutation through the normal Agent / mutation path.

Required fact:

```text
old selected proposal still identifies the previous human choice
BUT
core mutation returns COLLECTIVE_CONSENT_WORLD_EPOCH_STALE
```

For this specific authority proof, keep the old plan otherwise selectable if practical.

If the live closure necessarily makes it hard-infeasible, retain the deterministic test proving world-stale as a separate layer.

### Stage 4 — autonomous recovery

Run a fresh configured external Agent after the shock.

It must:

- inspect current reality;
- preserve completed execution truth;
- preserve protected/C4 commitments;
- create a new server-owned recovery future;
- never copy E1 member responses;
- never resurrect an older mediation consent.

### Stage 5 — selective renewed authority

Recompute the current collective decision surface.

If a material human value trade-off remains:

- recompute decision-relevant members;
- open a new server-owned collective round;
- authenticate fresh answers;
- bind them to E2/W2.

If the changed world yields one clearly acceptable future under current authority, do **not** ask humans again merely because an Event occurred.

That distinction is part of R30.

### Stage 6 — continue exactly once

After fresh authority and normal approval:

- exactly one final proposal becomes accepted;
- Journey execution continues;
- R28 exactly-once semantics remain PROVEN;
- R29 no-authority-theft semantics remain PROVEN.

## Mandatory unrelated-change control

The live or deterministic evidence must also prove:

```text
unrelated observation
  -> W epoch unchanged
  -> pending consent remains valid
```

Do not use `latest_event_id`, observation count, max(captured_at), Journey updated_at, or any other global churn proxy.

## Machine verdict

Create the R30 verifier only after the causal product path works.

It should prove at least:

1. R29 inherited invariants remain PROVEN.
2. E1 and W1 were durably stored at real renewed consent.
3. the shock occurred after E1/W1 and before consumption.
4. the shock is materially linked to the selected future.
5. W changed while old social selection still existed.
6. the old mutation was rejected at core.
7. no sibling consumed E1/W1 authority.
8. no older consent resurrected.
9. a configured external Agent recovered after the shock.
10. protected commitments survived.
11. completed execution truth survived.
12. a new decision surface was created if needed.
13. decision-relevant member scope was recomputed.
14. any fresh responses were new authenticated responses, not copied E1 answers.
15. E2/W2 were durably bound.
16. exactly one final recovery proposal was accepted.
17. execution continued.
18. unrelated evidence churn leaves a valid consent epoch unchanged.

## Stop rule

On machine-PROVEN R30:

- commit product changes;
- commit focused tests;
- commit live harness;
- commit machine verdict;
- commit one concise result report;
- push;
- stop R30.

No R30.1.

## Revolution principle

R30 is not "more consent validation".

It is a new product property:

> human permission expires when the meaningfully relevant world changes, but CityNexus can recover without stealing authority and without asking people again for changes that do not matter.
