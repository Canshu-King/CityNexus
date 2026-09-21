# R14 — Causal Attribution Integrity / 因果归因真值

Status: arbiter contract note for CityNexus cross-layer error attribution.

## 1. Purpose

CityNexus MUST NOT present one failure class as another merely because both travel through a
shared fallback path, exception handler, UI banner, or default value.

Freeze sentence:

> **Fault attribution must come from the evidence that distinguishes the fault. A lower or
> adjacent layer may carry the result, but it may not invent a different cause.**

In practical terms: do not borrow a convenient message from another layer.

R14 does not replace R1, R7, R10, R13, or their detailed contracts. It is the common
cross-layer invariant that prevents the same category of truth defect from reappearing in a
different subsystem.

## 2. Four layers covered by R14

### R14-I — Input attribution

Input uncertainty, absence, or parse failure must not be rewritten into a concrete user value.

Examples:

- explicit budget 1600 CNY -> 1600 CNY;
- budget absent -> null / UNKNOWN;
- extraction uncertain -> NEEDS_CONFIRMATION / BLOCKED;
- parse failure -> named parse/input failure;
- none of the above may become numeric 0.

This is the cross-layer form of ORD-0152 / R7 input-truth parity.

### R14-R — Runtime / fallback attribution

A runtime or storage failure must keep its actual runtime class.

Examples:

- SQLite writer contention -> named transient database/runtime failure or retryable service
  state, not a naked generic 500 with no structured reason;
- resolver timeout -> resolver runtime failure, not structural destination UNAVAILABLE;
- a valid operation whose target set is empty -> successful idempotent no-op, not server error.

Fallback behavior may reduce functionality, but it must not rewrite the reason.

### R14-S — Resource / state attribution

A valid response that says a resource or state is missing must not be reclassified as transport
failure.

Examples:

- journey endpoint returns HTTP 404 for a stale stored journey id -> stale/missing journey
  state;
- 404 is positive evidence that the request reached the server and received an application
  response; it cannot be labeled "network unavailable";
- after stale-id detection, the client must clear or quarantine the invalid stored reference
  and offer a real recovery path instead of persisting the false offline state.

This covers ORD-0169.

### R14-P — Presentation attribution

User-visible text, aria-live output, telemetry, and recovery actions MUST be derived from the
same structured classification.

The frontend must not:

- map every fetch failure/status to an "offline" banner;
- infer reason by matching English text;
- show a user-corrective instruction when the product corrupted the input;
- hide major UI surfaces because one unrelated state failed unless that behavior is explicitly
  tied to the classified state.

For a given failure instance, screen copy, accessibility announcement, analytics/telemetry, and
recommended recovery action must agree on the same machine reason.

## 3. Evidence precedence

Classification should use the strongest discriminating evidence available.

Recommended precedence:

1. explicit typed domain/runtime result or structured error code;
2. HTTP status + structured response body from the same request;
3. transport exception / timeout / connection failure for that request;
4. browser/network heuristics only when no stronger request-specific evidence exists.

Important consequences:

- an HTTP 404/409/422/500 response is not "offline"; the server answered;
- `navigator.onLine=true` alone is not proof that every service is reachable, but a same-origin
  HTTP response is enough to disprove "no network response" for that request;
- a successful unrelated endpoint does not override the target endpoint's structured error, but
  it can help demonstrate that a global "network unavailable" banner is over-broad.

## 4. Required classification shape

Where practical, errors/states should have a server- or product-owned structured form such as:

    error_class
    reason_code
    retryable
    source_layer
    correlation_id
    recovery_action
    message_key

Equivalent field names are allowed. The important rule is that classification happens once at
the appropriate evidence boundary and is propagated, not re-invented independently by UI,
telemetry, and fallback code.

## 5. Recovery must match cause

Examples:

- stale journey id -> clear invalid local reference -> journey picker / current valid journey;
- true offline/transport failure -> cached read-only mode / retry when connectivity returns;
- server runtime/transient DB busy -> retry/backoff with named service state;
- structural no-match -> destination not identified / disambiguate or choose another;
- input uncertainty -> ask user to confirm, not "adjust budget";
- empty reset target -> no-op result, not server-error recovery.

A recovery action that only makes sense for a different failure class is itself an R14 failure.

## 6. Required gates

At minimum maintain these regression cases:

1. **Input truth**: explicit 1600 CNY remains 1600 through extraction -> normalization ->
   persistence -> readback -> planner input.
2. **Input unknown**: missing/uncertain budget cannot become 0.
3. **DB contention**: a forced SQLite writer-lock path returns a named structured runtime class;
   UI must not render a generic unexplained failure as if it were user error.
4. **Empty valid operation**: valid scoped reset with zero matching demo rows is 200/204
   idempotent no-op (or equivalent successful empty outcome), never 500.
5. **Stale journey 404**: stale localStorage journey id + target /experience 404 must produce a
   missing/stale-journey classification, clear/quarantine the stale id, expose a recovery path,
   and restore the map/normal shell as appropriate.
6. **True offline**: actual transport failure remains OFFLINE/NETWORK_UNAVAILABLE and is not
   accidentally reclassified as stale journey.
7. **Server 5xx**: application/runtime 5xx remains SERVER/RUNTIME failure and is not called
   OFFLINE merely because fetch did not yield usable domain data.
8. **UI consistency**: visible banner + aria-live + telemetry + recovery action all use the same
   machine reason for each of the above states.

## 7. Mutation-kill requirements

The suite must kill at least these mutations:

- change stale-journey 404 mapping to OFFLINE;
- change true transport failure mapping to JOURNEY_NOT_FOUND;
- change absent/uncertain budget fallback to 0;
- change valid-empty reset outcome to 500;
- collapse named DB/runtime contention to unstructured generic 500;
- let UI choose a message from a broad "catch" branch instead of the structured reason.

A test that only checks copy text without checking the discriminating evidence and machine reason
is insufficient.

## 8. Observability rule

Telemetry must record what the classifier actually decided and the evidence category it used.

Do not emit:

    network_unavailable

for an HTTP 404 merely because the UI entered a fallback screen.

Prefer structured fields such as:

    attribution_reason=JOURNEY_NOT_FOUND
    evidence_kind=HTTP_RESPONSE
    http_status=404
    source_layer=RESOURCE_STATE

This makes false-cause regressions discoverable in production instead of only from screenshots.

## 9. Relationship to existing rules

- R7 owns planner/input parity details; R14 forbids misattributing corrupted input to the user.
- R1/R10 own resolver state distinctions; R14 forbids rewriting runtime failure as structural
  destination truth.
- R13 owns destructive demo isolation; R14 says a valid empty reset target is not a server fault.
- ORD-0112 owns DB-lock implementation details; R14 requires the resulting cause to stay named.
- ORD-0169 owns stale-journey recovery; R14 defines the general attribution invariant.

## 9.5 Boundary argument attribution

A successful call must not claim that a caller-supplied parameter was honoured when the boundary
actually discarded it.

For semantically relevant arguments such as `solver_mode`, the boundary MUST choose one of two
observable outcomes:

1. **ACCEPTED**: validate the value, forward it, and expose the effective value used downstream; or
2. **REJECTED**: return a named machine-readable error for unsupported/unsafe/unknown input.

The following third state is forbidden:

    caller supplies parameter
    -> adapter silently drops parameter
    -> request succeeds
    -> downstream default is used
    -> result is reported as if the requested parameter was honoured

This is an R14 attribution failure because the observable success response misstates what the
system actually executed.

Recommended structured evidence:

    requested_parameter
    argument_disposition = ACCEPTED | REJECTED
    effective_parameter
    reason_code
    source_layer = ADAPTER_BOUNDARY

For solver parity work:

- both legs must expose the same effective `solver_mode` before planner-result parity is interpreted;
- a discarded `solver_mode` is not evidence that the boundary respected it;
- unknown parameters must not disappear silently.

### Current ORD-0176 correction

The currently reviewed MCP surface does **not** silently discard `solver_mode`:

- the MCP `request_replan` tool signature does not expose a `solver_mode` parameter;
- its JSON/tool schema likewise omits that parameter;
- the lower payload boundary rejects unknown argument names rather than silently dropping them.

Therefore the present ORD-0176 gap is **interface/capability parity**, not proven silent-discard behavior.

The implementation has two honest options:

1. add `solver_mode` to the MCP tool signature/schema, validate its allowed values, forward it, and report the effective mode; or
2. explicitly define the MCP contract as fixed/default-solver only, reject attempts to request another mode, expose the effective default mode, and narrow H10b to a comparison where both legs intentionally use that same solver.

Do not report a caller-selected solver as honored when the public MCP interface cannot express it.

The generic R14 freeze sentence still applies to any boundary that truly does discard an accepted
parameter:

> **Parameter discarded is not boundary honoured.**

## 9.6 Provider HTTP / adapter attribution

A provider transport or access response is not a semantic place-resolution result.

For external resolver/discovery adapters:

- HTTP 401/403 access rejection is PROVIDER_ACCESS / RUNTIME_FAILURE class, not NO_MATCH;
- HTTP 429 is provider throttling/runtime state, not NO_MATCH;
- HTTP 5xx is provider/runtime failure, not NO_MATCH;
- timeout / DNS / transport error is runtime failure, not NO_MATCH;
- NO_MATCH is valid only after a request that satisfied the provider transport/protocol contract
  receives a successful semantic response whose parsed result set is explicitly empty/no-match.

The adapter must preserve the discriminating evidence needed to tell these apart, including where
available:

    provider
    request_kind
    http_status
    response_class
    retryable
    adapter_configuration_reason
    observed_at

### Photon User-Agent standing requirement

For the currently configured Photon path, the adapter must send the descriptive User-Agent required
by the provider contract instead of relying on the default httpx User-Agent.

A 403 caused by an unacceptable/default User-Agent is an adapter/protocol-access failure. It MUST
NOT be reported as "Gongshan/Yunhe could not be resolved" or as structural NO_MATCH.

Required regression shape:

1. adapter request contains the configured descriptive User-Agent;
2. semantic empty-result response may map to NO_MATCH;
3. provider 403 maps to a named provider-access/runtime result with HTTP evidence;
4. timeout remains distinct from NO_MATCH;
5. correcting the adapter header may permit the same query to succeed without changing the user
   destination text or canonical semantics.

Freeze sentence:

> **Provider access failure is not geographic no-match; classify the HTTP/transport evidence before interpreting the place result.**

## 10. ORD acceptance binding

R14 is a **hard acceptance condition** for any ORD whose scope creates, transforms, classifies,
propagates, displays, logs, or recovers from an error/state distinction.

Such an ORD MUST NOT be accepted merely because the visible copy looks correct.

Acceptance requires a machine-readable causal classification at the appropriate evidence
boundary, plus propagation of that classification to every downstream consumer that the ORD
touches.

Equivalent implementations are allowed:

- a server-owned `reason_code` / typed error returned by the backend;
- a typed client classifier derived from strong request-specific evidence such as HTTP status +
  structured response, when the distinction is genuinely client-owned;
- a typed input-state enum for parser/normalizer outcomes.

What is not allowed:

- copy-only fixes;
- broad `catch` branches choosing prose directly;
- English-string matching to infer cause;
- telemetry/aria/recovery using a different cause from the machine classifier;
- using a generic fallback reason where stronger discriminating evidence exists.

### Acceptance consequence

If an ORD in R14 scope does not provide a named machine reason/state (or equivalent typed
classification) and a regression gate proving that the visible/recovery behavior is driven by it,
the ORD remains **NOT ACCEPTED**, even if the screenshot appears correct.

### Current mappings

- ORD-0112: backend/runtime layer MUST return a named structured DB/runtime contention class;
  a UI-only copy change does not satisfy R14-R.
- ORD-0158: the normalized input pipeline MUST preserve typed states for explicit value /
  missing / uncertain / parse failure; prose-only correction does not satisfy R14-I.
- ORD-0169: stale journey / true offline / server runtime error MUST be distinct machine states
  and banner + aria-live + telemetry + recovery action must all consume that same classification.
- ORD-0125 empty-target behavior: successful empty/no-op is a typed successful state, not a
  generic 500.
- ORD-0176: current gap is MCP interface/capability parity for `solver_mode`, not proven silent discard. Either expose+validate+forward it with effective-mode evidence, or explicitly define/reject non-default solver selection and narrow parity to the same effective solver.
- Any other ORD (including ORD-0130 if it touches fault/state attribution) inherits R14 as a hard
  acceptance item for the attribution surface it changes.

R14 is not a universal requirement to add new reason codes to unrelated feature work. It binds
only where the ORD crosses a causal-attribution boundary.

## 10. Freeze sentence

**Classify from discriminating evidence, propagate the classification, and never borrow a
convenient cause from another layer.**
