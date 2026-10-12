# CODEX START HERE — Revolution R16

Read in this order before changing code:

1. `GPT_R15_EXTERNAL_CHECK.md`
2. `revolution/R16_EVENT_DRIVEN_GUARDIAN_MISSION.md`
3. `revolution/R16_IMPLEMENTATION_SKETCH.md`

Startup receipt:
- `TASKBOOK_READ`
- current base SHA
- current taskbook blob SHA
- configured Agent provider/model
- planned estimate-authority value (must be false)
- one sentence stating why deterministic Guardian fallback does NOT count as R16 success

Then implement immediately.

Do not build a new event/agent framework. The repository already has Guardian, Autopilot, standing missions, configured Agent runtime, request_replan, accept_replan, policy gates and provider pulses.

The Revolution target is to make the real model path actually own the recovery decision after a truthful event.
