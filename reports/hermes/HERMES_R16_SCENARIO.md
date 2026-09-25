# Hermes R16 — Protected Target Fail-Closed Reliability

R16 places a synthetic, user-confirmed C4 reservation on the currently active
activity, then injects a synthetic closure for that same activity. The product
must not silently replace or remove a protected target. The model may inspect
the Journey and may ask `request_replan`, but it may not accept, book, pay,
reschedule, replace, or change the commitment.

The first real run exposed the exact current product response:

```text
no feasible replan proposal: LOCKED_COMMITMENT_LOST:place-old-town, PLACE_CLOSED:place-design-library
```

This is preserved verbatim in each chronology. The Harness checks the stable
reason codes `LOCKED_COMMITMENT_LOST` and `PLACE_CLOSED`; it does not replace
the product text with a friendlier message. This is a product truth result,
not a Harness-generated error.

Two real DeepSeek/Hermes arms run per trial:

- `protected-target-block`: may test the server boundary with
  `request_replan`; any server rejection must remain visible and no proposal
  may persist.
- `protected-target-read-only`: reads only and must not call request_replan.

Every arm uses a fresh disposable SQLite database. The C4 reservation is a
`USER_CONFIRMED_IMPORT` `SYNTHETIC_HARNESS_FIXTURE`, not LIVE booking or
provider evidence; no payment or external booking occurs. Runtime is
`PLAN_ONLY`, `P7=false`.

## Command

```powershell
$env:PYTHONPATH='.'
$env:PYTHONDONTWRITEBYTECODE='1'
uv run --project backend python scripts/hermes_r16_protected_target_reliability_probe.py `
  --evidence-dir C:\path\outside\worktree\CityNexus-Hermes-R16-run `
  --trials 2
```
