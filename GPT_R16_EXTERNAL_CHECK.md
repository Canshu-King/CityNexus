# GPT external check — R16 -> R17

Inspected report: `REVOLUTION_R16_EVENT_DRIVEN_GUARDIAN_RESULT.md`
Verified branch: `codex/revolution-realtrip-recovery`

## R16 verdict

R16 is a genuine Revolution step.

It demonstrated:
- a fresh truth-grounded ACTIVE Journey;
- estimate authority remained OFF;
- a persisted CLOSURE event with explicit operator/user provenance;
- Autopilot/Guardian wake-up;
- `controller=configured_agent_runtime`;
- real Hermes-compatible `cn:glm-5.3-flash` AgentRun;
- model-selected ordered tools:
  `inspect_journey -> inspect_twin -> request_replan -> accept_replan`;
- Gateway `ALLOW_AUTO` under bounded policy;
- live Valhalla incident evidence;
- old/new PlanVersion lineage;
- revised Journey executed to COMPLETED.

The deterministic fallback control run was correctly excluded from success evidence.

## What R16 did not prove

R16 remained reactive:
- the disruption was operator/user reported;
- the system woke after a hard event already existed.

REVOLUTION_D was therefore correctly not claimed.

The next capability frontier is not another closure run. It is prevention:
- provider signal arrives before the hard failure;
- CityNexus predicts a material weakness;
- a real model chooses a preventive recovery;
- deterministic authority validates the mutation;
- the new plan measurably reduces the forecast-linked risk before failure occurs.

## Existing product already contains the R17 skeleton

Do not invent a new predictive architecture.

Current code already provides:
- live OpenMeteo weather capture;
- live Valhalla mobility capture;
- provider-backed weather Event creation;
- `JourneyResilienceSnapshot`;
- status `PREDICTIVE_WEAKNESS`;
- bounded counterfactual simulations via CP-SAT V2;
- `run_preemptive_guardian`;
- Guardian Autopilot pulse;
- configured model runtime;
- policy/Gateway mutation boundary.

The product simply has not yet proved this chain with a real provider forecast and real configured model on a fresh truth-grounded trip.

## Important proof caveat

Do not call prevention successful merely because `run_preemptive_guardian` sets a `predictive_prevented` marker after an executed action.

R17 must show before/after machine evidence:
- provider forecast affected a future activity;
- pre-action snapshot was `PREDICTIVE_WEAKNESS`;
- model-requested preventive replan occurred;
- post-action future plan materially reduces or removes the provider-linked exposure;
- recomputed resilience/exposure is lower or the targeted risky activity is removed/rescheduled;
- protected commitments remain preserved.

## Cost-contract red test

R16 focused verification reported one pre-existing failure:
`test_guardian_over_mission_budget_requires_confirmation`.

The fixture mutates legacy `Place.metadata_json.cost_minor`, while current recovery uses canonical/current cost evidence and plan cost truth.

Treat this as a contract-drift cleanup:
- update the fixture to write through the current canonical cost-evidence path;
- add a regression that legacy `metadata_json.cost_minor` cannot silently override canonical truth;
- keep one authoritative cost interpretation for recovery.

Do not turn this into a cost subsystem project. The predictive product milestone remains the priority.
