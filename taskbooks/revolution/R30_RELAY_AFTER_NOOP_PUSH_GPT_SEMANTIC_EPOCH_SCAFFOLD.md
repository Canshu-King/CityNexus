# Revolution Relay — R30 After Codex No-op Push and GPT Semantic-Epoch Scaffold

## Binding branch

`gpt/revolution-r30-consent-epoch-shock-recovery`

## What happened

Codex reported testing and pushing, but GitHub still showed the branch at:

`8a039bc00cb39b6867c240dfc7845ae628dfb587`

That was the original GPT taskbook commit. No Codex R30 code commit was visible on the branch or another R30 branch.

Treat that as a no-op push / validation event, not as R30 progress.

GPT then advanced the branch directly.

## GPT commits now on the branch

1. `2f0a18b115ed03adeae7300a6033f6045fd5cb15`
   - strengthens `collective_decision_epoch`;
   - the epoch now binds proposal/plan identity **and** semantic option meaning:
     - fit-subject Place IDs;
     - fit-subject tags;
     - fit-subject basis;
     - required-member effective fit / tier / conflict;
     - fairness boundary;
   - normalizes required-member IDs once, avoiding iterable re-consumption;
   - exposes the resolved `decision_epoch` through `pending_resolved_mediation_selection`.

2. `2994b2539c9e107141a7541f7b407b16797a0651`
   - recomputes the resolved collective semantic epoch at `collective_mutation_gate`;
   - if semantic meaning changed while the selected proposal is still PRESENTED and the plan still CANDIDATE, core mutation now fails with:
     - code: `COLLECTIVE_CONSENT_EPOCH_STALE`
     - classification: `RENEWED_COLLECTIVE_CONSENT_STALE`
   - keeps semantic staleness distinct from:
     - `COLLECTIVE_SELECTED_PLAN_REVALIDATION_REQUIRED`

3. `c64219cf594fd2f7ac38598508842e547d28201d`
   - adds focused regression coverage:
     - semantic option changes alter the epoch;
     - irrelevant ordering/debug noise does not;
     - an epoch mismatch is rejected at the core mutation gate.

## First action for Codex

Do not begin with a repo-wide review.

Synchronize and validate only GPT's new scaffold:

```bash
git fetch origin
git checkout gpt/revolution-r30-consent-epoch-shock-recovery
git reset --hard origin/gpt/revolution-r30-consent-epoch-shock-recovery
git rev-parse HEAD

cd backend
python -m compileall -q app
python -m pytest -q tests/test_r29_disagreement_mediation.py
```

Expected remote HEAD at this handoff:

`c64219cf594fd2f7ac38598508842e547d28201d`

If GPT introduced a real test or syntax defect, fix it narrowly.

Do not revert the semantic-epoch behavior merely to preserve an old hash.

---

# What is already solved

R30 now has the first authority layer:

```text
same proposal ID + same plan ID
DOES NOT imply
same human decision meaning
```

Changes to the collective decision surface now invalidate old renewed consent at the mutation core.

Examples already covered in principle:

- changed optional Place identity;
- changed candidate tags/category meaning;
- changed required-member preferences;
- changed member role/capability/state;
- changed member-fit/fairness meaning;
- original option disappears from the PRESENTED/GROUNDED_FEASIBLE surface.

Do not spend another round rebuilding this layer.

---

# The remaining R30 blocker: physical-world authority epoch

The current semantic epoch is still not enough.

A selected future may retain:

- the same proposal ID;
- the same plan ID;
- the same optional Place IDs/tags;
- the same member preferences and fits;

while the physical evidence supporting that future changes.

That is the remaining R30 capability boundary.

## Required behavior

Renewed consent must also be bound to the **decision-material world facts** that made the selected future meaningful and executable.

At minimum cover:

### Selected Plan immutable physical evidence

Use the existing `PlanVersion.mobility_evidence_json` rather than inventing a second evidence store.

Inspect and reuse stable fields such as:

- `integrity_hash`
- `snapshot_id`
- selected relevant route facts / provider identity
- incident recovery evidence already embedded in the plan

Do not hash arbitrary serialization order.

### Current canonical facts for decision-relevant Places

For the selected plan's `fit_subject_place_ids`, derive a small canonical projection from current `Place` rows.

Candidate material fields should include only facts that can alter the decision:

- provider identity / external identity;
- normalized opening evidence;
- canonical cost evidence;
- category/tags if not already fully covered by semantic epoch;
- provider-backed status/provenance where available.

Do not include display names or timestamps just because they changed.

### Relevant post-consent Event / ProviderObservation facts

This is the hard part.

Do **not** hash every Journey observation.

A provider update is decision-material only when it concerns the selected future.

Use a relevance relation grounded in things already owned by the server, such as:

- selected plan activity IDs;
- selected plan fit-subject Place IDs;
- route legs required by the selected plan;
- an Event's `affected_activity_id`;
- payload place/route identifiers that actually intersect the selected future;
- incident fingerprints already connected to the selected plan/replan lineage.

An unrelated observation must not change the authority epoch.

## Strong recommendation

Create one server helper with a name like:

`collective_material_world_basis(...)`

or

`collective_authority_epoch(...)`

Keep hashing arithmetic/pure projection in `app.collective_mediation`.

Gather DB rows in `main.py` or a small domain helper.

Do not put SQLAlchemy queries inside the pure hashing function.

---

# Durable resolved authority

When the final relevant member response changes a round to `RESOLVED`, persist both:

- the existing semantic `decision_epoch`;
- the new decision-material world epoch / basis identity.

Suggested durable fields inside the existing server-owned clarification JSON:

```json
{
  "decision_epoch": "...",
  "material_world_epoch": "...",
  "material_world_basis": {
    "...": "bounded audit facts"
  }
}
```

The basis may be compact.

Do not duplicate full provider payloads already stored elsewhere.

The resolved record must represent what people actually agreed to at that moment.

---

# Core mutation contract

Before consuming pending renewed consent:

1. recompute current semantic decision epoch;
2. recompute current material-world epoch;
3. compare both to the resolved values;
4. then run hard feasibility revalidation.

Keep failures distinct:

### Semantic/social meaning changed

`COLLECTIVE_CONSENT_EPOCH_STALE`

### Material world changed but plan may still be technically selectable

Use a distinct code, recommended:

`COLLECTIVE_CONSENT_WORLD_EPOCH_STALE`

classification may remain:

`RENEWED_COLLECTIVE_CONSENT_STALE`

### Selected plan is physically no longer valid

Keep:

`COLLECTIVE_SELECTED_PLAN_REVALIDATION_REQUIRED`

The ordering should preserve truth.

A material-world epoch mismatch should not be hidden merely because a later feasibility check also fails.

For deterministic unit tests, include a case where world epoch changes while `plan_schema(...).selectable == True`.

That proves this is an authority layer, not an alias for feasibility.

---

# Control case is mandatory

Prove an unrelated observation does **not** invalidate consent.

Example:

- selected compromise uses Garden + Museum;
- add a provider observation about an unrelated place/route not present in:
  - selected plan activities;
  - fit-subject Place IDs;
  - selected plan relevant legs;
- epoch remains stable;
- pending consent remains consumable.

If your implementation hashes `latest_event_id`, global Journey revision, observation count, or arbitrary captured_at values, this control should fail.

That is intentional.

Fix the relevance model rather than the test.

---

# R30 live strike

After narrow tests pass, build the causal strike.

## 1. Reach the R29 interlock point

Reuse R29 only as setup.

Get to:

- genuine preference-driven disagreement;
- real external mediator;
- genuinely improved grounded future;
- same relevant signed Journey principals renew consent;
- selected proposal remains PRESENTED;
- proposed plan remains CANDIDATE;
- **do not consume it yet**.

Capture:

- semantic decision epoch E1;
- material world epoch W1.

## 2. Inject a normal provider-backed shock

Preferred shock:

- opening/closure change on one selected compromise Place; or
- incident mobility change on one selected required leg.

The shock must enter through normal CityNexus provider/event/evidence machinery.

Forbidden:

- editing clarification JSON;
- manually changing the stored epoch;
- setting proposal status to REJECTED;
- switching the active plan;
- direct test-only mutation whose only purpose is to change a hash.

## 3. Old consent must fail closed

Attempt the normal mutation with the original selected proposal.

Required result:

- proposal still has the old social selection;
- core gate refuses it;
- old renewed consent is not consumed;
- no sibling consumes it;
- no older consent resurrects.

## 4. External Agent recovery

Run a configured external Agent after the shock.

It must:

- inspect changed reality;
- preserve completed execution truth;
- preserve C4/protected commitments;
- produce a new server-owned recovery future;
- never copy old human responses into the new decision.

## 5. Recompute who matters

If the shock creates another human value trade-off:

- recompute decision-relevant members;
- ask only those people;
- authenticate fresh responses;
- bind them to semantic epoch E2 and world epoch W2.

If current reality produces an unambiguous unanimously acceptable future, do not force unnecessary re-consent.

That selective behavior is part of R30.

## 6. Resume exactly once

After fresh authority and normal approval:

- exactly one recovery proposal becomes accepted;
- Journey execution continues;
- R28 exactly-once and R29 social-authority invariants stay intact.

---

# Suggested narrow test set during development

Keep loops small:

```bash
python -m pytest -q   tests/test_r29_disagreement_mediation.py   tests/test_r28_authenticated_member_principal.py   tests/test_r28_durable_approval_continuation.py
```

Add a dedicated R30 test file once the world-epoch helper exists.

Then run only the directly relevant replan/provider evidence tests.

Do not run the entire historical suite after each change.

---

# One important review note on GPT scaffold

GPT could not execute the repository locally through GitHub connector.

Therefore Codex owns local validation of commits:

- `2f0a18b`
- `2994b253`
- `c64219c`

If a defect exists, fix the implementation while preserving the contract:

> semantic option meaning must be part of consent freshness, and the core mutation gate must be the final enforcement point.

---

# Stop rule

R30 closes only when a live post-consent shock proves:

```text
fresh consent E1/W1
  -> material world shock
  -> old authority rejected at core
  -> autonomous recovery
  -> selective fresh authority E2/W2 if needed
  -> exactly-once continuation
```

plus the unrelated-observation control.

Then commit one machine verdict and one concise result report.

No R30.1.

## Revolution principle

Do not optimize for making the test green.

Optimize for this product truth:

> CityNexus must know when reality has changed enough that a human's previous yes no longer means yes — and it must recover without either stealing authority or pestering people about changes that do not matter.
