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

## 6. Freeze sentence

**Two consecutive delivery timeouts move coordination to the ledger; they do not move the work to failure.**
