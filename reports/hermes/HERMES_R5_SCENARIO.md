# HERMES R5 runtime scenario

Scenario ID: `hermes-r5-request-replan-idempotency-upgrade`

Run from a clean checkout on `hermes/validation-0212`. The probe refuses to
start if the source has tracked or untracked changes and rechecks source HEAD,
branch, porcelain, and tracked blobs after all runtime calls. All SQLite files
and receipts go to a caller-selected directory outside the worktree.

Arm A reruns the accepted R4 direct-versus-stdio contract probe and retains its
full receipt, including the V2 11-tool surface, full proposal projection,
proposal-only authority, mock/synthetic provenance, `P7=false`, and model
`NOT_USED` / `NOT_RUN`.

Arm B makes a stdio `request_replan` call with `CITYNEXUS_AGENT_ID=hermes-test`
and request ID `hermes-r5-legacy-cache-0001`, records the source response and
the exact entity state, rewrites only the outer `agent.request_replan`
idempotency response's proposal summaries to the parent four-field shape, then
restarts service processes against the same disposable SQLite file and retries
the same request identity and arguments. It requires complete ordered proposal
views, semantic parity, byte-for-byte unchanged stored legacy response and
request signature, and unchanged Journey, PlanVersion, Event, ReplanProposal,
and IdempotencyKey identities/state. No accept tool is called.

Arm C copies the legacy state, substitutes one unresolved cached proposal ID,
restarts the service, and retries the identical request. It requires the
deterministic MCP error `AGENT_IDEMPOTENCY_RESPONSE_SCHEMA_UNAVAILABLE` and
unchanged identity/state snapshots.

The backend principal is resolved server-side as
`hermes-r4-server-principal`; the MCP process identity remains `hermes-test`
in every process. `solver_mode` and `mission_id` are omitted by the MCP schema
and recorded as their defaults (`null` and no mission). No model-backed H11
execution occurs.
