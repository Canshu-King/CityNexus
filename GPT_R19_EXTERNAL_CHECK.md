# GPT external check — R19 -> R20

Basis:
- uploaded `REVOLUTION_R19_LIVING_PLAN_PORTFOLIO_RESULT.md`
- R19 taskbook on `gpt/revolution-r19-living-plan-portfolio-20261001`
- remote `codex/revolution-realtrip-recovery`

## First: source publication is currently incomplete

The uploaded report binds the substantive R19 code to:

`9e261475b1274fe2b92e20866337cf374fefd538`

That commit is not currently reachable from GitHub, and the R19 result file is not present on the remote `codex/revolution-realtrip-recovery` branch.

The preceding base `0b90bdc7f5de0e6571d6189607d80ec229642546` is reachable.

Therefore:
- treat the local R19 worktree as the source of truth for R19 code until it is pushed;
- before R20 implementation, publish the R19 code/report commits to the experiment branch;
- record the actual remote SHA after push;
- do not accidentally check out this taskbook branch over the local R19 work.

This is a handoff correctness issue, not a new evidence project.

## R19 verdict

R19 made a real product leap.

The uploaded machine run supports:
- one current ACTIVE plan truth;
- one live-provider-backed standby branch with explicit mobility TTL;
- retirement of a legacy R18 standby lacking valid expiry;
- public standby projection as non-selectable;
- generic plan selection refusing standby;
- a dedicated `activate_standby` Gateway tool;
- Gateway returning `REQUIRE_CONFIRMATION`;
- normal user approval being consumed;
- atomic active-plan replacement and cursor remap;
- old plan retirement/supersession;
- compact standby portfolio exposure through the Agent/Twin surface.

This is materially stronger than R18's explanation-only shadow.

## What R19 did not yet prove

### 1. It did not prove autonomous model branch choice

The report explicitly says the activation was exercised through the machine Gateway tool directly.

No configured model independently chose:
- standby vs fresh replan;
- one standby vs another;
- NO_ACTION.

That is the next intelligence boundary.

### 2. It did not yet prove the originally requested multi-branch living portfolio

The R19 taskbook defined REVOLUTION_B as multiple distinct evidence-grounded standby branches.

The reported live run shows:
- one retired legacy R18 branch;
- one newly materialized R19 standby branch.

That proves lifecycle + activation machinery, but not sustained arbitration among multiple viable future branches.

### 3. Trigger semantic matching needs a hard check

The standby was produced by:

`rain_earlier / WEATHER_SHIFT`

The activation trigger reported later was:

`traveler-reported CLOSURE`

The report says activation requires an actionable non-synthetic trigger, but it does not demonstrate that the trigger's semantic contract must match the standby's counterfactual trigger.

This is a critical authority invariant.

A WEATHER_SHIFT standby must not become activatable merely because some unrelated actionable CLOSURE event exists.

R20 must add an exact deterministic trigger-compatibility gate and a negative proof:
- WEATHER standby + CLOSURE event => explicit refusal;
- CLOSURE standby + matching affected place/activity closure => eligible for Gateway evaluation.

The model may choose; the server decides whether the choice is legally/semantically admissible.

### 4. R19 direct regression coverage is not visible in the report

The reported command remains the 35-test R15-R18 focused suite.

R20 should add narrow direct tests for:
- trigger mismatch refusal;
- matching trigger acceptance;
- expired standby refusal;
- stale parent refusal;
- generic select refusal;
- Agent tool cannot bypass Gateway;
- only one active reality after activation.

Do not build a new test harness.

## Revolution frontier

R20 should not be "Agent calls activate_standby".

That would only move the direct tool call one layer upward.

The real frontier is Autonomous Branch Arbitration:

> give the real model at least two fresh, grounded future branches plus the live/current event, do not tell it which plan is correct, and require it to decide whether to activate a compatible standby, request a fresh replan, or do nothing, while deterministic trigger contracts and Gateway policy remain authoritative.

The successful model must discover the branch through read-only state inspection and choose it through the existing governed tool surface.
