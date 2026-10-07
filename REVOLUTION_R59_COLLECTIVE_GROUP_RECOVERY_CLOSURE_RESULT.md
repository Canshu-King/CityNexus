# Revolution R59 — Collective Group Recovery Closure

## Outcome

R59 now connects a shared recovery decision to the existing member-response and authority machinery. The Agent Gateway can open or safely reuse one collective room; signed member responses are individually recorded and replay-safe; a changed physical decision basis makes the room stale; and the recovery card explains waiting, mediation, stale state, and authority without claiming that a receipt has applied a plan.

This is a server-native closure of the decision-room handoff, not a live-city/provider or external-Agent closure. The bounded integration run used test-seeded proposals and an explicit test-only user-reported trigger. No external model or mobility provider was called.

## Implementation and verification

- Implementation commit: `0a8cecd90` (`Close R59 collective recovery decision room`)
- GPT pre-baton mission-plan seam: **4 passed**
- Focused backend lineage (R59, collective operator, R29 disagreement, R28 principal/continuation/execution-truth, R30 authority receipt): **86 passed**
- TypeScript typecheck: **passed**
- Vite production build: **passed** (existing large-chunk advisory only)
- Python `compileall`: **passed**
- Focused two-browser Playwright: **2 passed**, including the repository's real-seed setup and R59 shared-room test
- `git diff --cached --check`: **passed**
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`; no external Agent/provider call.

## Bounded server-native handoff trace

The integration test created a fresh Journey and used two distinct signed test principals. The server opened a single room through `request_collective_decision`; the OWNER and ADMIN each answered their own member slot through the authenticated HTTP route. Both selected the same server-derived option. The existing receipt issuer produced a current, proposal-bound collective authority receipt. The Journey itself did not move.

| Fact | Recorded result |
|---|---|
| Journey | `1ed64cd6-2229-4a32-bfd0-7c38c315938e` (fresh local test Journey) |
| Members | OWNER `fc887f35-bd7a-4994-847e-fe28b3dbbd7a`; ADMIN `9a74d29d-2fcc-4f09-b245-eefed0a3aaf8` |
| Risk authority | `USER_REPORTED_TEST_INPUT`; not a live human observation or device attestation |
| Trigger | `8f8478d5-af89-4f49-b8bd-4a6bb41c7229`, `USER_CHANGE`, `USER_REPORTED_TEST_INPUT` |
| Mission | `fdef8f8d-1fbc-4af0-9553-9420ce18017a`, final parent status `ANSWERED` |
| Clarification | `b318d52d-0521-4a35-a114-2c3dd7921544`, `RESOLVED` |
| Required members / responses | 2 / 2; both signed test principals answered their own member slot |
| Mediation | Server classified the seeded choices as `HUMAN_TRADEOFF_REQUIRED`; the two answers aligned, so no disagreement-mediation child was needed |
| Proposals | `32e83a08-7d41-4786-ba95-3a8a2278c9ce` and `4e9507c8-870a-43db-8542-db41dec8c42d`; both remained `PRESENTED` test fixtures, explicitly **not provider-grounded** |
| Collective authority receipt | `013b36fd-9d1d-422c-8ca3-70464b1e214f`, `AUTHENTICATED_MEMBER_CONSENT`, bound to the selected proposal and both required members |
| Active PlanVersion | `7d4a6b2b-40a4-4ffb-b0e6-0083f638bc57` before and after |
| Mutation count | 0; the receipt authorized only the exact option and did not accept it or change the Journey |
| External Agent | `NOT_CALLED` in this strike; the prior R58 `FAILED_EXTERNAL` history was not retried |

## User-visible behavior

The two-context UI test presents one shared incident and one decision room, shows the same 1/2 response progress to both viewers, permits only the unresponded viewer to submit, and carries the collective state into the group-recovery surface. Its route is labeled replay evidence, not live traffic. After the fixture response, the screen says that current collective authority exists for the exact proposal but normal approval/acceptance still applies; it does not say the Journey is continuing or has changed.

## Limits

- The backend proposal/fairness projection in the integration test is a deterministic test seam. It does not prove canonical Place truth, live Valhalla mobility, or a real grounded recovery option.
- The trigger is a test-only USER_REPORTED input, not a real companion report or trusted device signal.
- The Playwright operator/read model is mocked for the UI contract; its `CAPTURED_REPLAY` label is deliberate.
- No plan was accepted, no activity was executed, and no physical-world execution is claimed.
- Therefore this closes the server-owned shared decision-room and authority handoff mechanics, but not a provider-grounded live group recovery or physical execution. Those stronger claims require a separately bounded live experiment.
