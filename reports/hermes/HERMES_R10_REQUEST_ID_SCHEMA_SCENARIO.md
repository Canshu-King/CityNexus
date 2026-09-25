# Hermes R10.1 — Request-ID Schema Alignment

## Finding being repaired

The R10 guided model arm produced two legitimate MCP failures because the
model used `read-1` and `read-2` as `request_id` values. The server-owned
`AgentToolCall` contract requires 8–128 characters, but the MCP V2 schema only
advertised `request_id` as an unconstrained string. The invalid calls therefore
reached the HTTP validation boundary and returned `422 VALIDATION_ERROR`.

This is a transport-contract mismatch, not a reason to relax the server gate.

## Narrow repair

The Hermes MCP adapter now exposes the existing server constraint in both V2
schema paths:

- `request_id`: string, `minLength=8`, `maxLength=128`;
- description identifies it as an opaque per-call idempotency identity;
- V2 server instructions repeat the constraint;
- FastMCP annotations and low-level MCP2 schemas use the same bounds.

The backend request model, idempotency semantics, proposal contract, and
authority policy are unchanged.

## Executable command

From the clean Hermes worktree:

```powershell
$env:PYTHONPATH='.'
$env:PYTHONDONTWRITEBYTECODE='1'
uv run --project backend python scripts/hermes_r10_request_id_schema_probe.py `
  --evidence-dir C:\path\to\request-id-evidence `
  --trials 3
```

The probe runs three fresh real DeepSeek/Hermes `r10-guided` trials on fresh
disposable state. It records native events, provider usage, raw MCP chronology,
proposal semantics, and authority state.

## Required result

PASS requires all three runs to complete with:

- zero MCP errors;
- no adapter request ID shorter than 8 characters;
- a real `request_replan` call and full
  `hermes-replan-proposal-view.v1` response;
- no mutation tool, no booking/commitment/payment mutation, and unchanged
  Journey authority;
- `PLAN_ONLY`, `P7=false`, and loopback CityNexus traffic.

## Observed result

The three-run probe passed. All adapter request IDs were 8–128 characters,
`mcp_error_count=0` in every run, and the model produced the full proposal
contract. The model still sometimes rereads `list_replans`; that remains the
separate R10 orchestration finding and is not silently claimed fixed here.

