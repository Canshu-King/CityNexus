# Hermes R12 — Traffic-Delay Intent Reliability

R12 extends the real-model reliability matrix to a non-closure disruption.
Each trial starts with RESET, a deterministic ACTIVE Journey with multiple
activities, and a synthetic `TRAFFIC_DELAY` event carrying a deterministic
60-minute impact and affecting the current activity. Two arms run twice each:

- `delay-proposal`: inspect the Journey and request a feasible proposal when
  the server says recovery is needed;
- `delay-read-only`: inspect and report only; never create a new proposal.

Hermes chooses the MCP sequence. The runner does not prescribe tool calls.
Every arm uses a fresh disposable SQLite database, a fresh Gateway/backend
process set, and loopback CityNexus/MCP traffic. Only the configured DeepSeek
provider may use network egress.

The event and mobility input are explicitly
`SYNTHETIC_HARNESS_FIXTURE`; they are not LIVE provider evidence.

## Gates

The proposal arm must return the current full
`hermes-replan-proposal-view.v1` contract, and every model-facing proposal ID
must exist in the post-run persisted ReplanProposal set. No mutation tool may
be called.

The read-only arm must not call `request_replan` or any mutation tool, and its
plan, event, and proposal sets must remain unchanged.

Both arms must preserve Journey authority, bookings, commitments, and payments;
`PLAN_ONLY` and `P7=false` remain explicit.

## Command

```powershell
$env:PYTHONPATH='.'
$env:PYTHONDONTWRITEBYTECODE='1'
uv run --project backend python scripts/hermes_r12_delay_reliability_probe.py `
  --evidence-dir C:\path\outside\worktree\CityNexus-Hermes-R12-run `
  --trials 2
```
