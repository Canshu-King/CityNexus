# CODEX START HERE — Revolution R26

Read in this order:

1. `GPT_R25_EXTERNAL_CHECK.md`
2. `revolution/R26_DECISION_CRITICAL_CLARIFICATION_MISSION.md`
3. `revolution/R26_IMPLEMENTATION_SKETCH.md`

Before changing code, output:
- `TASKBOOK_READ`
- current base SHA
- taskbook blob SHA
- configured Agent provider/model
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY` value, must be false
- one sentence explaining why R25 DEFER currently checks GROUNDED more strongly in wording than in actual full-feasibility semantics
- one sentence explaining why a missing provider fact must be acquired, while a decision-sensitive human value should be clarified
- one sentence confirming that R26 must ask only when the answer can change the action

Then implement immediately.

Do not reopen R25.

R26 is not a chat feature.

It is:
truthful options -> detect that the remaining uncertainty belongs to the human -> ask one consequential question -> resume under the same authority -> act differently from the answer -> stay silent when the question would not matter.
