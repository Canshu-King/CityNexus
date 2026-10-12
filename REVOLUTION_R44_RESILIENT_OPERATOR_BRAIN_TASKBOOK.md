# REVOLUTION R44 — Resilient Operator Brain & Recovery Resume

## Product-direction gate

This task is governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

The required one-sentence product answer is:

> **CityNexus newly learns to survive an external-AI outage during trip management: it keeps the real incident and recovery context, tells the traveller that its reasoning brain is unavailable, and automatically resumes the same unresolved recovery when a supported external model becomes usable — without asking the traveller to recreate the problem.**

If implementation becomes “add more health endpoints” or “prove R43 again”, stop and correct course.

## Starting truth

R43 is complete at commit `29a7cb4afd670c4d09e9953cfaaa8bf8c60ca245`.

R43 added the real user-facing Journey Operator:
- one-click “Take care of this trip”;
- standing mission + Guardian Autopilot;
- Operator state and timeline;
- approval card;
- deduped approval notification;
- exact AgentPendingAction continuation;
- post-approval convergence back to monitoring.

The fresh R43 experiment honestly ended:

`OPERATOR_EXTERNAL_AGENT_BLOCKED`

because no supported external reasoning runtime was configured.

R43 correctly refused deterministic fallback.

Do not rerun R33-R43 historical closures.

## Why R44 is a product capability, not infra cleanup

Without R44, a temporary model outage turns a long-running Journey Operator into a dead end.

The traveller must notice the degraded state and manually retrigger work later.

That is incompatible with:

> “Take care of this trip.”

A continuous travel operator must distinguish:
- no external brain is configured;
- a configured brain is temporarily failing;
- a prior recovery was blocked before model reasoning;
- a recovery already partially executed tools and therefore cannot safely switch brains.

It must preserve the incident and resume only when safe.

## 1. Operator Brain projection

Add one user-facing brain projection to Journey Operator.

Suggested states:

- `READY`
- `UNCONFIGURED`
- `TEMPORARILY_UNAVAILABLE`
- `RECOVERING`
- `ACTIVE`
- `ATTENTION_REQUIRED`

Example:

```json
{
  "state": "TEMPORARILY_UNAVAILABLE",
  "headline": "I’m still watching your trip, but my planning AI is unavailable.",
  "configured_runtimes": ["hermes", "deepseek"],
  "preferred_runtime": "hermes",
  "last_attempt": {
    "provider": "hermes",
    "reason": "MODEL_TIMEOUT"
  },
  "recovery_resume": {
    "pending": true,
    "incident_id": "...",
    "safe_to_resume": true
  }
}
```

Normal users do not need API-key names or environment-variable names.

Advanced details may show provider/model identity and last failure classification.

## 2. Supported external runtime pool

Keep the existing supported runtimes:
- Hermes/OpenAI-compatible runtime;
- DeepSeek native tool loop;
- native Hermes if existing server configuration supports it through the established path.

Do not add a fake deterministic “AI” runtime.

Create one server-owned runtime availability/selection contract.

A runtime candidate can be:
- CONFIGURED
- UNCONFIGURED
- TEMPORARILY_FAILED
- AVAILABLE

Do not claim network availability from configuration alone.

“Configured” means credentials/endpoint exist.
“Available” should mean either:
- a successful recent bounded runtime probe if an existing safe probe exists; or
- a successful recent Agent interaction.

If no safe provider probe exists, keep status CONFIGURED_UNKNOWN until the first actual run. Do not invent a health call that providers do not support.

## 3. Safe failover boundary

This is the critical correctness boundary.

External-model failover is allowed only before any irreversible/authority-relevant tool action from the failed model run.

Examples safe for another external runtime:
- provider connection failed before first model answer;
- timeout before any tool call;
- malformed first completion before tools;
- run failed with zero AgentRunStep tool actions.

Unsafe to blindly fail over:
- model already requested a replan;
- model acquired facts whose state changed recovery epoch;
- model produced an approval-bound action;
- model executed any mutating or proposal-generating tool.

In those cases:
- preserve the original run;
- Operator state = ATTENTION_REQUIRED or wait for the same recovery lineage;
- do not let another model independently choose a different action for the same generation without a server-owned new recovery epoch.

## 4. Recovery resume queue

When Operator is enabled and Guardian encounters a material incident but external reasoning cannot start safely:

persist a durable **resume intent** tied to:
- Journey;
- material incident fingerprint / Event;
- RecoveryEpoch;
- standing mission;
- GuardianRun lineage;
- active plan at block time;
- material world epoch;
- failure classification.

Prefer extending existing durable rows if a clean semantic home exists.

Do not create a second copy of the incident.

The resume intent means:

> “This exact unresolved recovery is waiting for an external reasoning runtime.”

## 5. Automatic resume

Guardian/Operator worker should be able to retry that blocked recovery later when:
- Operator remains enabled;
- incident remains open/actionable;
- recovery epoch is still current;
- active plan/material world basis has not invalidated the lineage;
- a supported external runtime is now configured/usable;
- no approval/pending action from the same lineage already exists;
- cooldown/backoff permits one bounded attempt.

The traveller should not need to:
- re-add the disruption;
- restart Operator;
- create another standing mission;
- press “try again” repeatedly.

One optional “Try now” control is acceptable, but automatic recovery is the product goal.

## 6. Bounded retry/backoff

Do not turn Operator into a provider hammer.

Use durable backoff.

Suggested:
- first blocked attempt records next eligible retry;
- subsequent external failures increase bounded delay;
- material-world change may reopen immediately under a new recovery epoch;
- user “Try now” may request one bounded immediate attempt if server says eligible.

Do not retry more frequently than Guardian watch policy allows.

Do not retry just to obtain a prettier outcome.

## 7. Runtime choice

Prefer the already configured runtime order, but make it explicit and inspectable.

Recommended policy:

1. configured Hermes-compatible runtime if present and not in backoff;
2. configured DeepSeek runtime if present and not in backoff;
3. native Hermes path if that is the explicitly configured primary path;
4. otherwise unavailable.

Adjust order to current architecture if necessary.

Important:
- runtime selection is a server product policy;
- the model still owns judgment once selected;
- do not translate “fallback” into deterministic recovery.

## 8. One recovery lineage, not duplicate brains racing

Do not run two external models concurrently against the same recovery epoch.

Only one selected external runtime owns the recovery attempt at a time.

If runtime A fails safely before tools:
- runtime B may take over the same unresolved recovery under a server-owned handoff record.

If runtime A has tool steps:
- do not ask runtime B to independently reinterpret the same incident unless server opens a new recovery generation.

This protects:
- proposal uniqueness;
- approval semantics;
- collective authority;
- user trust.

## 9. Operator UX

R43 DEGRADED is too generic.

Upgrade it.

Examples:

No external runtime configured:
> “I’m watching the trip, but no planning AI is connected.”

Temporary external failure:
> “I noticed a problem. My planning AI is temporarily unavailable, so I’m holding the trip state and will retry safely.”

Resume begins:
> “Planning is back. I’m continuing the recovery.”

Agent active:
> “I’m working out the best recovery.”

Success:
> “I found a recovery.”

The user should not need to understand:
- API keys;
- Hermes vs DeepSeek unless they open advanced details;
- AgentRun retry internals.

## 10. Operator start behavior

“Take care of this trip” should still enable monitoring even when no external model is configured.

Do not reject Operator start.

Instead:
- Operator = WATCHING;
- brain = UNCONFIGURED;
- Guardian can still observe real/world facts;
- actionable incident moves Operator to a clear degraded/waiting-for-brain state.

This preserves the value of sensing while keeping reasoning authority honest.

## 11. Configuration boundary

Do not persist raw provider API keys in Journey rows.

Environment / deployment secrets remain server configuration.

If the product needs a future “Connect AI provider” admin surface, that is a separate security-sensitive product slice.

R44 only needs to make existing supported external runtimes discoverable, selectable, and resumable.

## 12. Reuse R43 approval continuation

Once a resumed external Agent chooses an action:
- existing R43 Operator projection;
- ActionApproval;
- AgentPendingAction;
- notification;
- authenticated approval;
- resume_pending_action();

must take over.

Do not build a second approval system for resumed runs.

## 13. Honest lab proving

R44 does not need random real-world disruption.

Use one clearly labelled LAB_FIXTURE incident through the normal Guardian sensing path.

For focused tests, you may inject controlled external runtime adapters to prove:
- unavailable first;
- later available;
- one safe resume;
- no duplicate Agent run after unsafe partial tool execution.

This is an explicit lab simulation of provider availability, not fake world truth.

For a live/external experiment:
- if a real configured Hermes/DeepSeek runtime is available, use it once;
- if none is configured, do not fabricate success.

Valid outcomes:
- `OPERATOR_BRAIN_RESUMED_RECOVERY`
- `OPERATOR_BRAIN_FAILOVER_RECOVERED`
- `OPERATOR_BRAIN_STILL_UNCONFIGURED`
- `OPERATOR_BRAIN_UNSAFE_TO_FAILOVER`
- `OPERATOR_BRAIN_EXTERNAL_FAILURE`

## 14. Focused product tests

Keep this small and capability-driven.

At minimum:

1. Operator can start while brain UNCONFIGURED.
2. actionable incident persists one blocked recovery lineage.
3. blocked incident does not create duplicate Event/Guardian recovery rows each watch.
4. runtime becomes available -> same incident becomes eligible for resume.
5. safe zero-tool external failure may hand off to next configured external runtime.
6. any prior tool step blocks blind cross-model failover.
7. only one external runtime owns a recovery epoch at a time.
8. resumed Agent uses existing standing mission/incident lineage.
9. successful resumed recovery flows into R43 approval card.
10. approval continuation still causes zero extra model calls.
11. runtime outage never invokes deterministic fallback for Operator.
12. UI shows understandable brain state.
13. TypeScript + focused Operator Brain Playwright.

Do not rerun R34-R42 campaigns.

## 15. One bounded R44 product experiment

Use one fresh Journey.

Sequence:

1. Start Operator.
2. Confirm user-visible brain state.
3. Introduce one LAB_FIXTURE material incident through normal sensing.
4. Let one external reasoning attempt occur according to configured availability.
5. If unavailable, persist resume lineage.
6. If a second genuinely configured supported external runtime is available and first failure was safe, allow one bounded handoff.
7. If reasoning becomes available, continue the same recovery into the R43 approval path.
8. Stop after the first terminal product outcome.

Do not:
- recreate incident;
- create a second standing mission;
- hand-write proposal;
- use deterministic recovery;
- run parallel models;
- retry until green.

## Artifacts

Keep only the normal compact experiment artifacts:

- `REVOLUTION_R44_RESILIENT_OPERATOR_BRAIN_RESULT.md`
- `backend/output/r44-resilient-operator-brain-v1.json`

Artifact work must remain secondary to the product.

## Stop condition

Stop after one bounded Operator Brain experiment.

The end-user capability must be obvious:

> **“Even if CityNexus’s planning AI goes down while it is managing my trip, it does not forget the problem or make me start over. It keeps watching, waits safely, and continues the same recovery when its AI brain comes back.”**
