# Revolution R16 — Event-Driven Guardian Operator Result

## Result

R16 achieved `REVOLUTION_C` on a fresh, truth-grounded Hangzhou Journey.
The running Journey received a truthful closure event, Autopilot woke the
Guardian, the configured Hermes-compatible runtime executed a real GLM AgentRun,
and the model selected `request_replan` followed by `accept_replan` through the
existing Gateway policy. The revised Journey was then executed to `COMPLETED`.

`REVOLUTION_D` was not claimed: this run used an operator-reported disruption,
not a live provider-generated incident.

## Source binding

- base SHA: `8aa1ca049a64524cbc14a80f3d7b53055ddbc351`
- branch: `codex/revolution-realtrip-recovery`
- worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- final experimental commit: the commit containing this report (reported
  exactly in the handoff)
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`
- no R16 product-code change was required; the existing Guardian/Autopilot/
  AgentRun/Gateway path became native when the configured runtime was actually
  available.

## Fresh Journey and initial truth

- Journey: `a943b06d-bb41-40e5-8af2-c9a6907f8364`
- city: `CN-HANGZHOU`
- initial PlanVersion: `6cfc6645-8233-5b13-ba36-63db2a7646bd`
- initial plan was selected and started before the disruption.
- initial route used live Valhalla mobility and deterministic hard-feasibility
  receipts; the Agent saw this through `inspect_twin`.
- initial used route: Silk Museum → Tea Museum, live Valhalla travel burden
  `62 min`, hard eligible.

The initial catalog and facts were already established provider-backed truth.
R16 did not use estimated facts as selection authority.

## Standing Guardian mission and wake-up

- standing mission: `d4fcd440-d43c-4f85-86b5-056d7aac6efd`
- mission autonomy: `EXECUTE_WITHIN_BOUNDS`
- traveler policy: `AUTONOMOUS`, `auto_accept_replan=true`
- max automatic cost delta: `0`
- max schedule drift: `0`
- provider degradation: not allowed for automatic recovery
- protected commitment: Tea Museum
- mutable activity: Silk Museum
- Autopilot interval: `0.2s`
- event: `807afd6d-b386-4fcf-8d43-a5e251af1667`
- event type: `CLOSURE`
- affected activity: `05ff9958-e529-5d72-8e8d-a06942167934`
- event provenance: operator/user-reported closure through the existing event
  path; not model-invented and not mislabeled as a provider pulse.

Autopilot observed the open event and invoked Guardian processing. No new event
bus or Agent framework was introduced.

## Native Agent evidence

- GuardianRun: `9ba173ef-6ad0-4ff0-87ab-f4724b29214f`
- GuardianRun status: `COMPLETED`
- Guardian action: `EXECUTED`
- controller: `configured_agent_runtime`
- provider key: `hermes`
- provider: `HERMES_COMPAT_ENDPOINT`
- model: `cn:glm-5.3-flash`
- AgentRun: `b84767f4-40fa-42cd-bf1f-5fed42738741`
- AgentRun status: `COMPLETED`
- AgentRun outcome: `EXECUTED`
- child mission: `6392061f-9922-4af6-99de-34634d8a7a25`

Persisted ordered tool trace:

1. `inspect_journey`
2. `inspect_twin`
3. `request_replan` with the exact closure event ID
4. `accept_replan` with the exact proposal ID

This is native Agent autonomy because the configured model inspected the live
Journey and Twin and chose the recovery tool sequence. A deterministic Guardian
fallback would only replay fixed recovery rules and therefore would not qualify
as R16 native autonomy.

## Replan and authority evidence

- proposal: `1ea39363-ea5b-422c-98c3-2ed22892d396`
- old active PlanVersion: `6cfc6645-8233-5b13-ba36-63db2a7646bd`
- new active PlanVersion: `f8d834a4-5027-4c7a-93e3-9af8b0e8707b`
- planner action: remove the closed Silk Museum activity, preserve the Tea
  Museum commitment, and keep cost/schedule drift at zero.
- Gateway decision: `ALLOW_AUTO`
- policy version: `3`
- reason codes: `DELEGATION_POLICY_MATCHED`, `DETERMINISTIC_GATE_VERIFIED`
- mutation: executed `true`
- incident mobility snapshot: `9940a687-c26a-466e-abfc-9c1dc5a351ed`
- incident mobility source: `valhalla-http`
- incident route provenance: `LIVE_PROVIDER_CAPTURE`
- incident hard feasibility: `true`

The final revised plan contains one remaining activity, so its final snapshot
has no inter-activity edge to report. The live edge above belongs to the initial
plan inspected by the Agent and to the incident proposal evidence; no synthetic
`used_edge_ids` were manufactured.

## Revised Journey execution

After Gateway acceptance, the revised activity was driven through the real
execution state machine:

`depart` → `EN_ROUTE` → `arrive` → `ARRIVED` → `begin` → `IN_PROGRESS` →
`complete` → `COMPLETED`

Final Journey state: `COMPLETED`.
Final active PlanVersion: `f8d834a4-5027-4c7a-93e3-9af8b0e8707b`.
The old PlanVersion remains in lineage; it was not overwritten.

## Fallback control run (not success evidence)

An earlier fresh Journey, `4d02b955-b36b-4260-85df-80d7e569ca73`, was run before
the process-only WB2api/Hermes key was loaded. Its GuardianRun
`582ab4a0-362c-4f9e-ad3c-93432554031c` recorded runtime unavailable and used:

`controller=deterministic_guardian_fallback`

with Agent provider `citynexus-guardian` and model
`deterministic-recovery-controller-v1`. This run is retained as resilience
evidence only and is explicitly excluded from the R16 native-autonomy result.
The raw credential was never persisted or included in this report.

## Focused verification

Command:

```text
uv run pytest tests/test_guardian_model_evidence.py tests/test_guardian_v4.py tests/test_agent_mission_runtime.py tests/test_r15_source_authority.py -q
```

Observed: `33 passed, 1 failed`.

The single failure is the pre-existing
`test_guardian_over_mission_budget_requires_confirmation` fixture. It mutates
legacy `Place.metadata_json.cost_minor`, while the current recovery proposal
uses the current cost-evidence path; the proposal therefore reports zero cost
delta and the test observes `EXECUTED` instead of its expected
`REQUIRE_CONFIRMATION`. This was not changed in R16 and must not be reported as
green. The native R16 runtime path, Guardian model evidence, Agent mission
runtime, and R15 source-authority focused tests passed.

The first test invocation with the configured live provider also reproduced the
same deterministic fixture mismatch; the focused rerun with model credentials
cleared produced the same single failure, confirming it is not a provider
timeout or Agent decision artifact.

## Boundaries preserved

- no authority/mainline merge
- no new event bus or Agent framework
- no fabricated provider event
- no fabricated route edge or selection receipt
- `MOCK != LIVE`
- estimate authority remained off
- Gateway/authority boundary performed the activation mutation
- deterministic fallback was not counted as Revolution success

## Exact replay

1. Check out branch `codex/revolution-realtrip-recovery` at the final report
   commit in the isolated worktree above.
2. Start the API against the lab SQLite database with real-city/live Valhalla
   enabled, `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`, and the configured
   process-only Hermes-compatible endpoint/model.
3. Create the fresh Hangzhou Journey from canonical provider-backed places.
4. Select and start the initial plan.
5. Enroll the standing Guardian mission and start Autopilot.
6. Submit the truthful `CLOSURE` event for the Silk Museum activity.
7. Wait for the Autopilot pulse and inspect the persisted GuardianRun and
   AgentRun tool steps.
8. Verify `request_replan` and `accept_replan` IDs, Gateway policy, and old/new
   PlanVersion lineage.
9. Execute the revised activity transitions through `complete` and verify
   Journey `COMPLETED`.

