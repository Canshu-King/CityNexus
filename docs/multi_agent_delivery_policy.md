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

## 7. Freeze sentence

**Two consecutive delivery timeouts move coordination to the ledger; they do not move the work to failure.**
