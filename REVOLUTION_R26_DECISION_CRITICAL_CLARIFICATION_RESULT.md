# Revolution R26 — Decision-Critical Clarification

## Machine result

- Taskbook: `Revolution R26 — Decision-Critical Clarification`
- Taskbook blob: `9e79c4dbeb30e9bdbc1453d7f409d1f198a9d325`
- Base SHA: `f1fbb8e8d67fe2946c0b0adde5d92586503850a3`
- Final SHA: filled by the commit containing this report
- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`
- Configured runtime: `HERMES_COMPAT_ENDPOINT`, primary `cn:glm-5.3-flash`, fallback `cn:deepseek-v4.1-flash`
- Mobility provider: `valhalla-http`

## R25 authority corrections

The horizon no longer treats “known cost + known route” as feasibility. Each window now carries `GROUNDED_FEASIBLE`, `GROUNDED_INFEASIBLE`, or `REVALIDATION_REQUIRED`, using canonical opening, visit duration, route duration, safety buffer, and commitment slack. `DEFER` is accepted only for two individually `GROUNDED_FEASIBLE` windows and a real scarce-resource conflict. Optional budget subtracts declared stay allocation, consumed cost, and unavoidable protected/locked future costs; ordinary future optional activities are not reserved.

## Main live run

Fresh disposable Journey created from the provider-backed Nara catalog:

- Traveler: `4a73bdf5-8846-4d45-803e-9b5e13be0a1b`
- Journey: `aa9c919e-b11a-477a-9a7c-eae509221afe`
- City: `JP-NARA`
- Active PlanVersion: `60d48102-3bb9-595c-bc01-0c1f1fd6473a`
- Journey budget: 2600 JPY
- Declared stay allocation: 800 JPY
- Optional budget: 1800 JPY
- Current activity: Nara Park, `e8d6401d-18c3-550b-8625-03dfaf718076`
- W1: Todaiji Museum, `real-place-1ffd66e7224682f5558f1579`, 800 JPY, `GROUNDED_FEASIBLE`
- W2: Isuien Garden, `real-place-22cf72809897ff4c7f312fcf`, 1200 JPY, `GROUNDED_FEASIBLE`
- `800 + 1200 > 1800`: genuine resource conflict; neither option is individually infeasible.
- Mobility evidence: Valhalla-backed frozen planning evidence; actual edges were hard eligible: Park→Museum 27 min and Museum→Garden 13 min. Future planning evidence explicitly records `future_live_traffic=false`.

## Agent and clarification trace

1. First live attempt with the placeholder WB2api key was recorded as `FAILED_EXTERNAL / PROVIDER_REFUSED / 401` for both configured models. No product success was claimed.
2. The WB2api key was loaded from the local supported configuration path at runtime only; no raw credential was persisted.
3. Main AgentRun: `841e1268-8183-4535-a692-17b399d91690`, mission `13e2db59-09bc-4dc2-b5a7-1a09f67dcd5a`.
4. The real Agent called `inspect_journey`, then `inspect_twin`, observed `decision_sensitive=true`, and called `conclude_recovery` with `CLARIFICATION_REQUIRED`.
5. Clarification: `63dd4cfb-97a1-4ca9-94a5-e13fdac5ad47`; decision epoch was persisted; server-owned option keys were exactly `TAKE_NOW` and `TAKE_LATER`; option mapping was `TAKE_NOW→TAKE_NOW`, `TAKE_LATER→DEFER`.
6. The question was about relative value of the current museum versus the later garden. No opening, cost, or mobility question was sent to the user.
7. Active plan and Journey remained unchanged while waiting.
8. User answer was applied through the product endpoint as `TAKE_LATER`, scope `THIS_JOURNEY`. Parent mission became `ANSWERED`; child mission `a06f5823-de4b-4363-8614-94b19a3b9fb8` was created with `parent_mission_id` and `CURRENT_EXPLICIT_MISSION` precedence, without widening authority.
9. Child resume used the normal configured Agent runtime. After one schema correction by the Agent (server rejected an incomplete one-item option list), the Agent inspected the Journey/Twin and concluded `NO_ACTION` with `horizon_decision=DEFER`; Gateway returned `ALLOW_AUTO`.
10. Child AgentRun: `b2280b58-0f44-42dc-9377-54b59388fcc6`; completion contract: `NO_ACTION`; mission status: `COMPLETED`; active PlanVersion remained unchanged.

## Execution result

The existing HTTP execution state machine was then used for the same active plan:

`depart → arrive → begin → complete` for Nara Park, Todaiji Museum, and Isuien Garden.

Final machine state:

- Journey status: `COMPLETED`
- Final active PlanVersion: `60d48102-3bb9-595c-bc01-0c1f1fd6473a`
- Current activity: `null`
- Twin projection: `READY`
- No direct active-pointer write, booking, reservation, or synthetic fact was used.

## Controls and boundaries

- When current explicit intent already resolves the value, the Twin returns `decision_sensitive=false`; the child trace proved this and did not ask again.
- A factual gap is not a clarification: the sensitivity helper requires two server-produced `GROUNDED_FEASIBLE` options, so `REVALIDATION_REQUIRED`/missing facts cannot produce `CLARIFICATION_REQUIRED`.
- Clarification answers are Journey-scoped by default. Cross-Journey persistence requires the explicit `REMEMBER_FOR_FUTURE_TRIPS` scope.
- Epoch fingerprints include Journey, active PlanVersion, current activity, and the first two server windows. A stale answer is rejected as `CLARIFICATION_STALE_RECOMPUTE_REQUIRED`.
- Server derives options and verifies sensitivity; Agent prose cannot create options or authority.
- P7 remains false. No mainline/authority merge was performed.

## Focused verification

```text
backend/tests/test_r26_decision_critical_clarification.py: 3 passed
python -m compileall -q backend/app: passed
git diff --check: passed
```

The three focused tests cover: true resource-conflict sensitivity, rejection of a non-feasible window, and suppression/fingerprint change for explicit intent and stale reality.

## Remaining limitation

The live run completed the decision-critical clarification, child mission, DEFER decision, and normal Journey execution. The current provider chain showed bounded model timeouts and fallback behavior in the persisted trace; those are recorded as external receipts, not converted to success prose. No claim is made that the provider is latency-perfect.

