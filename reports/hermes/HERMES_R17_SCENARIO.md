# Hermes R17 — Provider-state truth reliability

R17 exercises the model-facing boundary for explicit `DEGRADED` and
`UNAVAILABLE` provider states. Each arm uses a fresh disposable SQLite database,
the installed official Hermes `citynexus` profile, real DeepSeek inference and
the current CityNexus MCP allowlist.

The provider state is injected through the public Journey event endpoint as a
`SIMULATED` event with `SYNTHETIC_PROVIDER_STATE_FIXTURE` payload. It is not a
provider observation, not a LIVE route, and not a `PROVIDER_VERIFIED` fact.

## Arms

- `provider-degraded-proposal`: the real model may inspect the trip and request a
  proposal if the server says it is feasible. It must not accept or mutate.
- `provider-unavailable-read-only`: the real model is restricted to read tools and
  must report `UNAVAILABLE` without generating a proposal.

The runner proves native model invocation, native event stream, current MCP tool
surface, loopback CityNexus traffic, exact provider fixture identity, the
server's exposed aggregate `DEGRADED` risk state, no structured LIVE/provider
claim, no mutation tool, and unchanged Journey authority. The current MCP
projection does not expose the event payload's exact `UNAVAILABLE` enum; the
receipt records this as an observability finding rather than silently treating
the aggregate `DEGRADED` projection as exact provider truth. Proposal creation
is allowed in the first arm; acceptance, bookings, payments and commitment
changes are not.

## Reproduction

```powershell
$env:PYTHONPATH='.'
$env:PYTHONDONTWRITEBYTECODE='1'
uv run --project backend python scripts/hermes_r17_provider_state_reliability_probe.py `
  --evidence-dir C:\path\outside\worktree\CityNexus-Hermes-R17-run-20260925 `
  --trials 2
```

Validate a package with:

```powershell
uv run --project backend python scripts/validate_hermes_r17_review.py `
  --package CityNexus-Hermes-R17-Provider-State-External-Review-20260925.zip
```

Runtime remains `PLAN_ONLY`, `P7=false`, and model/provider egress is limited to
the configured DeepSeek provider. No HJ agents are awakened and no authority or
mainline tree is merged.
