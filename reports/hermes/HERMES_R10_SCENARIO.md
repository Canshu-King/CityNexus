# Hermes R10 — Tool-Planning Efficiency

## Scope

R10 measures whether server-owned MCP tool descriptions can reduce avoidable
Hermes planning work without changing the CityNexus product contract. The
experiment is deliberately narrower than an API redesign:

- the natural-language traveller request is unchanged;
- CityNexus `request_replan` remains full fidelity;
- `structuredContent` is not removed or compacted;
- the only accepted candidate is description guidance telling the model that a
  successful complete `request_replan` already contains the new proposal;
- all arms use fresh disposable SQLite state, loopback CityNexus/MCP traffic,
  DeepSeek through the configured Hermes `citynexus` profile, and `PLAN_ONLY`.

No `accept_replan`, booking, payment, commitment, or other mutation tool is
called. `P7=false` throughout.

## Primary command

From a clean committed Hermes worktree:

```powershell
$env:PYTHONPATH='.'
$env:PYTHONDONTWRITEBYTECODE='1'
uv run --project backend python scripts/hermes_r10_tool_planning_probe.py `
  --evidence-dir C:\path\to\R10-evidence `
  --trials 3
```

The runner executes three baseline and three `r10-guided` real model trials.
Each trial records native Hermes events, provider usage, MCP chronology, raw
CallToolResult measurements, semantic proposal projections, authority checks,
and network guard output.

## Acceptance rule

The guided variant is accepted only when all trials are safe and semantically
complete, median provider total tokens improve, median model-visible response
bytes improve, median MCP calls do not regress, and both ordinary and
post-success redundant `list_replans` reads decrease. A token improvement alone
is not sufficient.

## Checkpoint result

The primary evidence set contains three completed baseline trials and three
completed guided trials. The guided variant is **REJECTED**: it reduced median
provider tokens and MCP calls but increased model-visible cumulative response
bytes and did not reduce post-success `list_replans`; one guided trial also
recorded MCP validation errors. The overall R10 measurement run is **PASS**
because the baseline safety arm completed and the rejected optimization is
reported as a rejected experiment, not promoted as product truth.

The proposal identity measurement reads both current response shapes:
`proposal_views[*].proposal_id` and `proposals[*].id`. The raw chronology is
the authority for this derived metric. The measurement correction itself does
not alter CityNexus behavior.

## Reproduction and evidence

Run the independent validator after collecting evidence:

```powershell
$env:PYTHONPATH='.'
uv run --project backend python scripts/validate_hermes_r10_review.py `
  --evidence-dir C:\path\to\R10-evidence
```

The validator derives trial statistics from the recorded trials and raw
chronologies, verifies the full current proposal contract and untouched
structured content, checks the PLAN_ONLY/no-mutation boundary, and recomputes
the raw Git commit object and blob identities when run against the review
package.

The package also records a later corrected rerun whose baseline arm was
blocked because one real model trial did not produce `request_replan`. That is
kept as an exact reproducibility observation; it does not replace the primary
complete evidence set.

