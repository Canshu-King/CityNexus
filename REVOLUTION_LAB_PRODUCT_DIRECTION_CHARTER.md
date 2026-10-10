# Revolution Lab Product Direction Charter

This charter governs task selection for Revolution Lab after the already-issued R42 work completes.

## Mission

Revolution Lab is not a stricter copy of mainline. It is not a factory for more verifiers, receipts, taskbooks, or numbered proof loops.

Its purpose is to give CityNexus important product capabilities that mainline is unlikely to attempt quickly.

Every new Revolution task must first answer:

> What can the user do now that they could not do before?

Not:

> What existing behavior did we prove again?

## Product-first task selection

Prefer work that produces visible new user capability.

Examples of the intended direction:
- better AI planning;
- coordinating multiple travellers;
- proactive observation of real-world changes;
- handling disruptions;
- requesting necessary human approval;
- continuing execution after approval;
- completing meaningful work on the traveller's behalf.

A new API, database table, state field, verifier, receipt, or test is not a product leap by itself.

Validation exists to support the new capability. It is not the capability.

If several consecutive Revolution rounds do not create a product change a normal user could notice, assume the direction has drifted.

## Aggressive experimentation is allowed

Revolution Lab may fail.

Acceptable honest outcomes include:
- BLOCKED
- NO_MATERIAL_CHANGE
- provider unavailable
- an idea proving not viable
- a capability remaining partially experimental

Do not manufacture success for a green result.

At the same time, honesty must not become conservatism.

Within clear provenance and authority boundaries, prefer ambitious experiments over safe cleanup.

Coursework/lab stages may use simulation, synthetic data, limited live data, or experimental providers when the boundary is explicit.

Unknown stays unknown.
Simulation stays simulation.
A provider that supplied no fact must not be rewritten as if it did.

But production-grade perfection must not block useful experimental product progress.

## System direction

DeepSeek / external reasoning models should increasingly own:
- judgment;
- reasoning;
- selection;
- planning;
- trade-off decisions.

Hermes / tool layers should increasingly own:
- execution;
- provider interaction;
- bounded real-world actions.

Journey, Traveler Twin, Guardian, World Context, planning, recovery, approval, and execution should converge into one continuously operating Agent instead of remaining isolated feature modules.

## North star

The long-term goal is not R41, R42, R43, or any other numbered round.

The target user experience is:

> “Handle this trip for me.”

CityNexus should then be able to:
1. understand goals and constraints;
2. build and maintain the Journey;
3. coordinate fellow travellers;
4. observe relevant real-world changes;
5. judge when intervention is needed;
6. propose or choose an adjustment;
7. wait for required human authority;
8. execute through tools;
9. continue operating after the action;
10. manage the Journey through completion.

Mainline guards the city.
Revolution expands it.

## Anti-regression rules

After R42 completes:

- Do not return to proving R34-R40 one item at a time unless a specific defect genuinely blocks the next new product capability.
- Do not enter verifier/evidence/receipt loops.
- Do not create report carousels.
- Do not choose a task because it is easy to verify.
- Do not keep polishing an existing surface when a larger missing product loop is available.
- Do not confuse stronger infrastructure with a user-visible capability unless the infrastructure directly enables that capability.

Before accepting the next task, write one sentence:

> CityNexus newly learns to ________.

If that sentence is weak, repetitive, or describes only internal plumbing, pick a different task.

## Preferred post-R42 direction

Prefer connecting the capabilities that already exist:

- Guardian
- World Context
- Journey state
- launch context
- exact mobility / Route Session
- replanning
- group coordination
- human approval
- Agent/Hermes execution

into one user-visible **Autonomous Journey Operator** loop.

The next substantial milestone should look more like:

> “A real-world change happened; CityNexus noticed it, understood its impact, chose what to do, asked me only when authority was required, executed the approved action, and continued managing the trip.”

and less like:

> “Another subsystem now has one more endpoint and eleven more assertions.”

## R42 continuity

The already-issued R42 Departure Activation work remains in force and must not be interrupted.

R42 should finish under its existing authority boundary.

This charter governs task selection starting with the first baton after R42.

## Task-selection checklist

For every post-R42 Revolution baton, answer all five:

1. **New capability** — What can the traveller now do that was impossible before?
2. **Visible loop** — What changes in the actual user experience?
3. **Agent convergence** — Which previously separate Journey/Guardian/World/Agent/tool pieces become one operating loop?
4. **Authority boundary** — What may the system do autonomously, and where must it wait?
5. **Stop condition** — What one bounded experiment proves the capability without turning into a verifier campaign?

If the first three answers are not strong, do not spend a Revolution round on it.
