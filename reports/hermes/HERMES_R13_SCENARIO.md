# Hermes R13 — Weather Provenance and Safe Recovery

R13 is a real-model, proposal-only reliability checkpoint for a weather
disruption. Each trial resets a fresh disposable SQLite database, creates an
ACTIVE Journey with multiple activities, and injects one explicit
`WEATHER` event through the public event API.

The injected event is deliberately:

- `provenance=SIMULATED`
- `provider_key=demo-simulator` (server assigned)
- `kind=SYNTHETIC_WEATHER_FIXTURE`
- not produced by `/weather/refresh`
- not provider-verified or LIVE weather evidence

Two arms run twice each:

- `weather-proposal`: Hermes inspects the event and may request a feasible
  proposal. The current full proposal contract and persisted proposal IDs are
  required; no acceptance or other mutation is allowed.
- `weather-read-only`: Hermes reports the stored event and existing proposals
  without generating a new proposal or invoking any mutation.

The harness does not prescribe the model's tool sequence. It separately checks
the model/native invocation, MCP chronology, event provenance, proposal
contract, persisted identity, authority projection, and mutation absence.

## Command

```powershell
$env:PYTHONPATH='.'
$env:PYTHONDONTWRITEBYTECODE='1'
uv run --project backend python scripts/hermes_r13_weather_reliability_probe.py `
  --evidence-dir C:\path\outside\worktree\CityNexus-Hermes-R13-run `
  --trials 2
```

The independent validator is:

```powershell
python validate_hermes_r13_review.py --package <this-zip>
```

R13 remains `PLAN_ONLY`, `P7=false`, and does not call `accept_replan`,
booking, payment, commitment, or approval actions.
