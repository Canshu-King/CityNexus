# Hermes R9 — MCP Context Transport Convergence

This checkpoint measures the actual MCP 2 transport envelope and the provider
conversation cost of the current CityNexus V2 Hermes surface. It does not
change the backend `request_replan` response contract, proposal authority,
approval lifecycle, deterministic feasibility, or P7 boundary.

Each arm uses a fresh disposable SQLite database, isolated loopback ports, the
official Hermes `citynexus` profile, the current 11-tool allowlist, DeepSeek's
configured model, and `PLAN_ONLY`. The direct envelope arm makes exactly these
calls: `inspect_journey`, `inspect_twin`, `list_replans`, `request_replan`,
`list_replans`.

For every call the runner records backend response bytes, adapter bytes,
TextContent bytes, structuredContent bytes, complete CallToolResult bytes,
request bytes, semantic hashes, and tool chronology. Model trials also record
provider-reported token usage, native Hermes events, turn-level response-byte
replay measurements, repeated reads, and authority state before/after.

The baseline and two three-trial experiments use the same natural-language
traveller request. Tool-guidance changes only server-owned descriptions: it
teaches the model that a successful `request_replan` already returns the new
proposal and that unchanged service searches should not be repeated. The
accepted tool-guidance result is now the committed MCP description. The
model-facing TextContent experiment derives a compact `request_replan` text
projection while preserving full structuredContent byte-for-byte; it is
rejected because its median MCP call count regressed even though bytes and
tokens fell.

No mutation tool is called, no plan is accepted, and no booking, payment, or
commitment operation is performed. `P7=false`; this is not an HJ-agent
activation claim. The evidence package contains no database, WAL/SHM file,
credential, token, private key, pycache, or pyc.
