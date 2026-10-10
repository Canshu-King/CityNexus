# REVOLUTION R54 — Reality Reconciliation / Source Conflict Resolver

## Product-direction gate

Governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

## User capability — put this sentence at the top of the result

> **When CityNexus receives conflicting travel facts from different sources, it no longer silently overwrites reality or follows “last write wins.” It reconciles source authority and freshness, freezes unsafe automation when the truth is genuinely contested, asks the traveller one bounded question only when needed, and resumes the same Journey once reality is resolved.**

If this becomes “add provenance fields” or “write more conflict reports”, stop and correct course.

## Starting truth

R53 is complete at `23735030b8d7440867a496187c81dbc163946e48`.

R53 proved:
- a pasted reservation update can update exact TransportReservation + Commitment truth;
- current execution remains unchanged;
- replay is idempotent;
- material impact enters the existing Guardian path;
- user-pasted evidence is not mislabeled LIVE.

Do not rerun R33-R53 historical closures.

## Existing facts to reconcile

Potential sources already exist:
- LIVE_PROVIDER
- LIVE_PROVIDER_CAPTURE
- USER_REPORTED
- USER_PASTED_TEXT
- USER_UPLOADED_IMAGE
- OPERATOR_CONFIRMED_EXECUTION
- DEVICE_LOCATION_VERIFIED_EXECUTION
- SEALED_REAL_REPLAY
- CAPTURED_REPLAY
- LAB_FIXTURE
- ESTIMATED_AGENT
- SYSTEM_DERIVED_PROVIDER_FACT
- frozen facts / snapshots
- explicit Preference / capability

R54 must not flatten all provenance into one confidence number.

## 1. First-class RealityClaim

Create a durable `RealityClaim` / semantic equivalent when multiple claims may target the same Journey fact.

Suggested fields:
- id
- journey_id
- fact_domain
- fact_key
- subject_type
- subject_id
- value_json
- provenance
- source_ref
- observed_at
- effective_at
- expires_at
- authority_class
- status
- generation
- created_at

Suggested status:
- CURRENT
- SUPERSEDED
- CONFLICTING
- REJECTED
- EXPIRED

Do not immediately duplicate every existing fact into this table if a cleaner adapter/read model can represent claims over current domain rows.

## 2. Fact domains for v1

Keep bounded:
- RESERVATION_TIME
- RESERVATION_STATUS
- VENUE_OPENING
- ROUTE_DURATION
- EXECUTION_PRESENCE

Do not generalize the whole database.

R54 fresh experiment should use RESERVATION_TIME because R53 already has the product path.

## 3. Source authority policy

Define server-owned authority classes.

Suggested rough ordering by domain, not universal:
- explicit operator-confirmed execution may dominate inferred presence;
- exact live reservation provider response may dominate stale user-pasted text;
- a newer explicit user-provided change may temporarily outrank an older frozen provider snapshot if no fresh provider evidence exists;
- SEALED_REAL_REPLAY is historical/replay evidence, never current-live authority;
- ESTIMATED_AGENT cannot win authoritative truth with lab estimate authority false.

Do not use one global enum rank for every fact domain.

Use domain-specific policy.

## 4. Freshness matters

A stronger source can still be stale.

Example:
- provider snapshot captured yesterday says 17:40;
- user message received today says 18:10.

Do not automatically choose provider just because provenance class sounds stronger.

Reconciliation considers:
- source authority;
- observed_at;
- effective_at;
- expiry;
- whether source can know this fact;
- exact identity binding.

## 5. Conflict classes

Suggested outcomes:
- `NO_CONFLICT`
- `NEWER_HIGHER_AUTHORITY_WINS`
- `OLDER_CLAIM_SUPERSEDED`
- `TEMPORARY_USER_OVERRIDE`
- `UNRESOLVED_MATERIAL_CONFLICT`
- `NONMATERIAL_CONFLICT`
- `STALE_SOURCE_IGNORED`

The product should care most about:
`UNRESOLVED_MATERIAL_CONFLICT`.

## 6. No silent last-write-wins

Critical invariant.

If current Reservation says 17:40 and a new exact claim says 18:10:
- evaluate reconciliation before mutating authoritative truth.

If another source later says 17:40:
- do not blindly flip back;
- reconcile against the active claim set.

Persist history.

## 7. Safe automation freeze

If a material fact is unresolved:
- mark that fact contested;
- prevent plan mutation / booking / departure advice that depends on it;
- Operator attention becomes reality-conflict-specific.

Do not freeze unrelated Journey work.

Example:
train departure time contested:
- current museum Activity continues;
- unrelated dinner booking can still proceed;
- transfer replan dependent on train time must pause.

## 8. R52 integration

Add attention kind:

`REALITY_CONFLICT_REQUIRED`

Example:

### Needs you
**I have two different departure times for the same train**

Provider snapshot: 17:40
Your forwarded update: 18:10

[Use 18:10]
[Keep 17:40]
[Check again later]

Only show claims the server has actually bound to the same fact.

Do not ask user to choose if server policy can deterministically resolve the conflict safely.

## 9. User choice is not magic provider truth

If the traveller chooses:
> Use 18:10

record:
- USER_CONFIRMED_REALITY_RESOLUTION
- linked conflict id
- selected claim id

This authorizes CityNexus’s internal truth selection.

It does not mean the provider itself confirmed 18:10.

Keep provenance explicit.

## 10. Provider refresh

If a fresh exact provider read becomes available after user resolution:
- it may supersede the user-confirmed internal selection according to domain policy;
- if it disagrees materially, open a new conflict generation.

Do not silently erase the user’s prior decision history.

## 11. R53 integration

R53 intake should no longer mutate reservation truth before reconciliation.

New flow:
message -> exact binding -> RealityClaim -> reconcile -> either:
- apply authoritative winner;
- keep existing truth;
- open conflict.

R53 remains the intake channel.
R54 owns truth arbitration.

## 12. Guardian integration

Only after reconciled authoritative truth changes:
- calculate impact;
- open/update normal Event / future risk;
- Guardian runs if material.

Do not start recovery from an unresolved conflict.

The Operator should say:
> “I’m holding off on replanning until I know which departure time is real.”

## 13. R49 / R50 integration

Future/overnight projections should:
- surface contested facts;
- avoid deriving exact leave-by from unresolved reservation time;
- morning briefing says:
  > “Your train time still needs confirmation.”

No fake schedule precision.

## 14. R47 transaction protection

If a transaction saga depends on a contested fact:
- do not execute irreversible commerce steps until resolved;
- existing completed steps remain historical truth.

Do not roll back unrelated actions.

## 15. Idempotency and generations

Same claim replay:
- reuse claim.

Materially changed source value:
- create new claim generation.

Same unresolved claim set:
- reuse same conflict generation;
- no repeated attention spam.

## 16. Product UI

Operator should show one compact reality status when relevant:

> “I have conflicting information about your train departure.”

Advanced details may show:
- source
- received/captured time
- provenance
- selected authority reason

Default UI should not expose internal rank numbers.

## 17. Focused tests

Only tests proving the capability:

1. identical claims -> no conflict.
2. stale lower-authority claim ignored.
3. newer user message can outrank older provider snapshot temporarily.
4. fresh live provider can supersede stale user message.
5. ESTIMATED_AGENT never wins authority.
6. unresolved material conflict blocks dependent replan.
7. unrelated current execution remains unchanged.
8. R52 attention appears only when unresolved and material.
9. bounded user resolution updates same conflict generation.
10. user resolution provenance is explicit.
11. later fresh provider disagreement opens new generation.
12. same claim replay does not duplicate conflict.
13. R53 intake routes through reconciliation before mutation.
14. Guardian starts only after reconciled truth changes.
15. R49/R50 avoid fake timing when fact contested.
16. TypeScript + focused Reality Conflict Playwright.

Do not rerun historical campaigns.

## 18. One bounded R54 product experiment

Use one fresh Journey.

Prepare:
- future train reservation AB123;
- current authoritative reservation time 17:40 from an older exact provider/replay claim.

Then submit one R53 pasted exact update:
- 18:10
- USER_PASTED_TEXT
- newer than existing claim.

Depending on policy, one acceptable path is:
- newer user claim temporarily wins because provider claim is stale;
- truth updates to 18:10;
- no conflict.

Then add one fresh exact provider claim that still says 17:40.

Now:
- same reservation/fact key;
- both exact identities;
- materially conflicting current claims.

Expected:
- `UNRESOLVED_MATERIAL_CONFLICT`
- no automatic flip;
- no new Guardian recovery yet;
- R52 shows one `REALITY_CONFLICT_REQUIRED` item;
- user selects one bounded option once;
- same conflict generation resolves;
- only then truth changes/impact handling continues;
- stop.

If a real live provider is unavailable, use clearly labeled captured provider replay for the provider-side claim and do not call it live.

Valid outcomes:
- `REALITY_RECONCILIATION_AUTO_RESOLVED`
- `REALITY_RECONCILIATION_USER_RESOLVED`
- `REALITY_RECONCILIATION_WAITING_FOR_TRUTH`
- `REALITY_RECONCILIATION_PROVIDER_DEGRADED`

## Stop condition

Stop after one conflict is either safely auto-resolved or surfaced once and resolved through the same conflict lineage.

End-user capability:

> **“If two travel sources disagree, CityNexus doesn’t quietly pick one and hope. It knows reality is contested, pauses only the dependent actions, asks me once if it truly needs me, and then keeps going.”**
