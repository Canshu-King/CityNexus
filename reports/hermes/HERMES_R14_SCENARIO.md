# Hermes R14 — Zero-Remaining-Budget Recovery Reliability

R14 extends the real-model reliability matrix to budget pressure. Each trial
resets a fresh disposable SQLite database, creates an ACTIVE Journey and plan,
then uses the public Journey update endpoint to set the budget equal to the
selected plan's server-returned total cost. The remaining budget is therefore
exactly zero without any direct database mutation. A synthetic closure event
then affects the current activity.

The closure is explicitly `SIMULATED` from `demo-simulator` and is a
`SYNTHETIC_HARNESS_FIXTURE`, not live provider evidence. The budget and
feasibility envelope remain server-owned.

Two arms run twice each:

- `budget-proposal`: Hermes inspects the zero-budget Journey and may request a
  proposal only when the server's deterministic feasibility says it fits. A
  conservative no-request result is also valid when the model cannot establish
  that the disruption is actionable from server-owned evidence; across the two
  trials, at least one full persisted proposal contract is required.
- `budget-read-only`: Hermes reports budget, event provenance, feasibility and
  persisted proposals without generating or mutating anything.

The harness does not prescribe the model's tool sequence. It proves real model
invocation, native MCP chronology, exact event/budget fixture identity, full
proposal contract and persisted IDs, unchanged Journey authority, and absence
of acceptance/booking/payment/commitment/approval mutation.

## Command

```powershell
$env:PYTHONPATH='.'
$env:PYTHONDONTWRITEBYTECODE='1'
uv run --project backend python scripts/hermes_r14_budget_reliability_probe.py `
  --evidence-dir C:\path\outside\worktree\CityNexus-Hermes-R14-run `
  --trials 2
```

R14 remains `PLAN_ONLY`, `P7=false`, and does not call `accept_replan`.
