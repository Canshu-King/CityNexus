# CityNexus Multi-Agent Delivery Reliability Policy

Status: coordination contract for chat/session delivery failures and ledger-driven execution.

## 1. Source of truth

The project ledger / Issue bus is the durable source of execution instructions and acceptance state.
Chat/session delivery is an acceleration channel, not the only source of truth.

## 2. Repeated session-delivery timeout rule

If the same target session returns `CHAT_SESSION_RUNTIME_RECONCILE_TIMEOUT` (or an equivalent delivery-timeout condition) **two consecutive times for the same instruction epoch**, classify that session as:

    LEDGER_DRIVEN_ONLY

for the remainder of that instruction epoch.

After classification, the commander MUST:

1. stop repeating the same full payload into that session;
2. write the complete instruction/acceptance change to the durable ledger;
3. optionally send one short pointer message containing only the order id / ledger comment id if the channel later becomes responsive;
4. use a human-forwarded pointer only when needed;
5. not create duplicate orders merely because chat delivery timed out;
6. not infer that the lane is idle, stopped, or failed solely from delivery timeout.

## 3. Recovery

A session may leave `LEDGER_DRIVEN_ONLY` when one of these occurs:

- a short probe/pointer is delivered successfully and the lane acknowledges the current ledger order;
- the lane posts evidence against the current order;
- the session is intentionally replaced and the new session proves it has loaded the current ledger state.

Recovery does not require retransmitting the entire historical payload.

## 4. Payload discipline

When retrying before the threshold:

- first retry may use the original payload;
- second attempt should prefer a compact pointer if the durable ledger already contains the full order;
- after the threshold, no more full-payload retries.

This prevents compute and operator time from being burned on repeated delivery of content that is already durably recorded.

## 5. Classification boundaries

`LEDGER_DRIVEN_ONLY` means only that direct session delivery is unreliable.

It does NOT mean:

- the lane is unhealthy;
- the worker stopped;
- the order was rejected;
- the implementation failed;
- the evidence is invalid.

Those require their own evidence.

## 6. Chat rendering is not delivery truth

A chat/window rendering is a presentation surface, not the durable delivery record.

If a response appears truncated, contains only a fragment, renders only a few characters, or
otherwise looks suspiciously incomplete while a durable ledger/bus entry exists, classify the
window observation as:

    CHAT_RENDER_INCOMPLETE

and retrieve the durable bus/ledger message before deciding whether the other side answered.

Rules:

1. Do not resend a long instruction merely because the chat window rendered a fragment.
2. Do not infer "no answer", "partial answer", or "agent stopped" from rendered length alone.
3. When the durable bus contains the full message, the bus is authoritative for execution scope,
   acceptance text, and handoff content.
4. A short chat pointer may be used to direct a human/agent to the durable comment/order id.
5. If both the chat window and durable bus are incomplete, classify the delivery as genuinely
   incomplete and re-issue only the missing durable instruction.
6. Preserve comment/order ids in handoffs so the full text can be reloaded without replaying the
   whole conversation.
7. UI rendering defects and transport/delivery defects are different failure classes. A message
   can be durably delivered while the window renders only a fragment.

Recommended receipt fields:

    delivery_channel
    durable_comment_or_order_id
    durable_payload_present = true | false
    chat_render_complete = true | false
    classification = DELIVERED | CHAT_RENDER_INCOMPLETE | DELIVERY_INCOMPLETE

Freeze sentence:

> **The bus decides whether the work was delivered; the window only shows whether the UI rendered it.**

## 7. Observation-read failure is not an empty result

A monitoring/readback failure MUST NOT be interpreted as evidence that the target is empty,
missing, mismatched, or undelivered.

Examples:

- a ledger-anchor lookup using the wrong anchor or a corrupted rewrite must not become "no ORDERS";
- a bus readback using an invalid GitHub URL must not become "comment missing/mismatched";
- an API/read probe that errors before decoding the target must not become an empty collection;
- a filesystem/read tool failure must not become "file absent" without a successful inventory/read.

Use one of these explicit states:

    OBSERVATION_READ_FAILED
    OBSERVATION_ROUTE_INVALID
    OBSERVATION_DECODE_FAILED
    OBSERVATION_UNAVAILABLE

Only a successful read of the authoritative surface may yield an empty/absent verdict.

Required receipt shape:

    target
    read_method
    read_endpoint_or_anchor
    read_status
    read_error
    authoritative_fallback
    final_observation

When the primary monitor fails, use an independent authoritative read path if available. If the
fallback succeeds, the monitor failure remains a tooling defect and MUST NOT contaminate the
underlying delivery/state verdict.

Freeze sentence:

> **Read failure is unknown, not empty. Observe the authority before declaring absence.**

## 8. Verification-tool abort does not imply target corruption

A coordination/guard/proof script may fail because its own assertion, arithmetic, parsing, or
rollback proof is wrong. That failure MUST NOT be promoted into a claim that the ledger, bus,
repository, or target content is corrupt.

Use explicit classifications:

    TOOL_GUARD_ABORTED
    TOOL_PROOF_FAILED
    TARGET_UNCHANGED_CONFIRMED
    TARGET_STATE_UNKNOWN

Rules:

1. A fail-closed write helper is allowed to abort when its proof cannot establish safety.
2. If the helper aborts before mutation and an authoritative post-check proves the target SHA/bytes
   are unchanged, record:
       TOOL_PROOF_FAILED + TARGET_UNCHANGED_CONFIRMED
3. If the helper cannot prove whether a partial write occurred, record TARGET_STATE_UNKNOWN and stop.
   Do not call the target healthy or damaged until an authoritative reread resolves it.
4. A proof bug is a tooling defect even when fail-closed behavior successfully prevents damage.
   Record both facts separately.
5. Fixing the helper does not retroactively convert the aborted attempt into a successful write;
   the later successful attempt needs its own receipt.

Recommended receipt:

    tool
    intended_operation
    pre_target_sha_or_digest
    abort_stage
    tool_failure_reason
    write_started = true | false | unknown
    post_target_sha_or_digest
    target_verdict
    corrected_tool_version
    later_success_receipt

This rule is the write-side companion to the observation rule above: an instrument can be wrong
while the observed target remains correct.

Freeze sentence:

> **A failed proof is evidence about the instrument first; only authoritative target evidence can prove target damage.**

## 9. Cross-lane write-boundary wait rule

When work is split across lanes with mutually exclusive write domains, waiting for the upstream
lane does not authorize the downstream lane to cross the boundary and "help".

If lane A owns domain A and lane B owns domain B:

- A may stop at a typed interface/handoff;
- the Commander/ledger forwards the handoff;
- B changes only domain B;
- B must request, not perform, any required change in domain A;
- A must request, not perform, any required change in domain B.

Use a durable handoff when the dependency becomes blocking:

    upstream_order
    upstream_source
    interface/schema/version
    downstream_order
    requested_delta
    owner_of_requested_delta
    status = READY | BLOCKED_ON_UPSTREAM | CHANGE_REQUESTED

Do not resolve BLOCKED_ON_UPSTREAM by silently editing the upstream owner's files.

Freeze sentence:

> **A write boundary remains a boundary while waiting; blocked does not mean shared ownership.**

## 10. Freeze sentence

**Two consecutive delivery timeouts move coordination to the ledger; they do not move the work to failure.**
