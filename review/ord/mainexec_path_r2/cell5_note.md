# ORD main-exec-path, cell 5 — my own cell-4 tool had a fake gate; I found and removed it

Standing rule now in force (ledger `车主 · 04:15 常设：把「派单」换成「领域所有权」`): each lane is the standing
owner of a quality domain and no longer waits for the next task — it sweeps, finds, fixes, adds a regression
arm, and assigns its own next cell. My domain is assertion trust ("每条断言配反例臂"): an assertion, or a gate,
that cannot fail is worse than none. This cell applies that to my own cell-4 code.

## What I found (by measuring, not by reading)

Cell 4 added the `report_disruption` handler with this branch:

```python
if auth.decision is AuthorizationDecision.DENY:
    raise HTTPException(403, "the traveller's delegation policy denies report_disruption")
```

I asked whether that branch can ever fire. `REPORT_DISRUPTION` was placed beside `REQUEST_REPLAN` in
`delegation_policy.py`, and that branch returns `ALLOW_AUTO` before any mode check. Measured on this tree
(`policy_modes_r2.txt`), with the tightest envelope the product can express — `auto_accept_replan=False`,
zero cost allowance, zero loss allowance, zero schedule drift, no allowed activity types:

```
ADVISORY   -> ALLOW_AUTO
ASSISTED   -> ALLOW_AUTO
AUTONOMOUS -> ALLOW_AUTO
```

So in **every** product mode the DENY branch is unreachable. It was a fake gate: it advertised a policy
refusal that cannot happen, which is exactly the defect my domain exists to catch.

## The fix

Removed the dead branch. A check that can never fire implies a gate that is not there, so the honest code
says what actually gates this tool: the allowlist (a name not in the catalog is refused) and the
`agent_tool_requested` audit row that every dispatch writes. The handler still reports the decision in its
receipt (it is always `ALLOW_AUTO`), so the receipt stays truthful.

## The arm that keeps it honest

`tests/test_agent_runtime_gate.py::test_agt10_19b_report_disruption_is_v2_only_and_the_allowlist_is_its_real_gate`
pins the two facts that make the gate real:

- `report_disruption` is in the V2 catalog (so dispatch admits it), and
- it is NOT in the pinned V1 six (so the V1 surface is unchanged), and
- a name in neither is refused by the allowlist — the gate that actually bites.

Discriminating check: removing the `ToolDescriptor` from `TYPED_TOOLS` turns the arm red ("the tool is not in
V2, so dispatch would refuse it"). Restored byte-for-byte afterwards.

## Behaviour-unchanged proof (whole backend suite, same tip)

| run | passed | failed | skipped | xfailed |
|---|---|---|---|---|
| clean tip e9b231b8 | 1718 | 11 | 16 | 1 |
| cell 4 | 1720 | 10 | 16 | 1 |
| this cell | 1721 | 10 | 16 | 1 |

Every red is in the clean-tip set (the same comment-anchor drift ×3 and anywhere g5/g9b/g14a/g14c/g8a/g10 and
g3_xproc_http). Zero new failures; one more green than cell 4 (the added arm). `catalog_hydration` is
load-flaky under the full run on both sides.

## Next cell (self-assigned, per rule three: widen the coverage)

The same question — "can this gate actually fail?" — applies to the other tool handlers in the gateway. Cell 6
sweeps every `dispatch` handler and asks, per handler, whether its refusal branch is reachable, and records a
reachability receipt for each. A handler whose only refusal is unreachable is the same fake-gate shape this
cell found in mine.

## Boundary

Product bytes: `gateway.py` (one branch removed) and one test. No contract change beyond cell 4's. No authority
moved; branch only.