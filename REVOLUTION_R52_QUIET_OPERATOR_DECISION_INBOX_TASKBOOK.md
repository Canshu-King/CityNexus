# REVOLUTION R52 — Quiet Operator / Decision Inbox

## Product-direction gate

Governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

## User capability — put this sentence at the top of the result

> **The traveller can now hand the Journey to CityNexus and stop supervising every subsystem. The Operator works quietly by default and surfaces one unified, prioritized “Needs you” decision only when it cannot safely continue without the traveller; once the traveller responds, the original Journey flow resumes automatically.**

If this becomes “another dashboard”, “another notification list”, or “merge some cards in React”, stop and correct course.

## Starting truth

R51 is complete at `f6dd19ef5ba19cc636a991a9aa30a52321c0e96c`.

R51 proved:
- a running Journey can accept an authenticated natural-language temporary JourneyIntent;
- scope/expiry are server-owned;
- current execution remains untouched;
- global Preference/Twin remain untouched;
- shared/transaction authority remains behind existing R45/R47 gates;
- when no semantic model is configured, fallback asks for clarification instead of pretending model understanding.

Do not rerun R33-R51 historical closures.

## Existing user-interrupt sources to unify

Already present:
- R43 ActionApproval / AgentPendingAction;
- R45 WAITING_FOR_MEMBERS / collective mediation;
- R48 explicit execution confirmations:
  - depart
  - arrive
  - begin
  - complete;
- R50 MORNING_NEEDS_ATTENTION / route-needed morning state;
- R51 JourneyIntent NEEDS_CLARIFICATION;
- R47 PARTIALLY_APPLIED / transaction attention;
- route acquisition CTA;
- Operator NEEDS_ATTENTION / brain degraded states.

Today these are separate product surfaces.

R52 turns them into one server-owned interruption contract.

## 1. Quiet-by-default principle

The normal Operator should not ask the traveller to understand:
- Guardian;
- AgentRun;
- Approval;
- Collective clarification;
- Route operation;
- JourneyIntent;
- Transaction saga.

The product asks only:

> **What is the one next thing only this traveller can do?**

If there is no such thing:
- `attention = null`
- Operator keeps working.

## 2. Unified AttentionItem

Add one server-owned read model / durable projection:

`OperatorAttentionItem`

Suggested kinds:

- `APPROVAL_REQUIRED`
- `COLLECTIVE_RESPONSE_REQUIRED`
- `INTENT_CLARIFICATION_REQUIRED`
- `ROUTE_CHECK_REQUIRED`
- `CONFIRM_DEPARTURE`
- `CONFIRM_ARRIVAL`
- `CONFIRM_BEGIN`
- `CONFIRM_COMPLETE`
- `TRANSACTION_PARTIAL_ATTENTION`
- `MORNING_ATTENTION`
- `OPERATOR_DEGRADED`

This is a projection over existing truth, not a new authority source.

## 3. One current decision

GET `/operator` should expose:

```json
{
  "attention": {
    "kind": "APPROVAL_REQUIRED",
    "title": "CityNexus found a safer recovery",
    "body": "This changes the afternoon order and keeps your booking.",
    "action_label": "Review change",
    "action_type": "APPROVE_RECOVERY",
    "source_ref": {
      "approval_id": "..."
    },
    "priority": "HIGH",
    "blocking": true,
    "created_at": "..."
  }
}
```

If multiple things need attention:
- return one `primary`;
- optionally return a compact count / deferred list for advanced UI;
- do not show five competing cards.

## 4. Server-owned priority policy

Suggested priority order:

### P0 — safety / partial external reality
- TRANSACTION_PARTIAL_ATTENTION
- authority/security failure that means user must act now

### P1 — blocked continuation
- APPROVAL_REQUIRED
- COLLECTIVE_RESPONSE_REQUIRED
- INTENT_CLARIFICATION_REQUIRED

### P2 — execution milestone
- CONFIRM_ARRIVAL
- CONFIRM_BEGIN
- CONFIRM_COMPLETE
- CONFIRM_DEPARTURE

### P3 — preparation
- ROUTE_CHECK_REQUIRED
- MORNING_ATTENTION

### P4 — degraded info
- OPERATOR_DEGRADED

Do not let a low-value route check hide a required approval.

## 5. Viewer-specific attention

For shared Journeys:
- Alice sees Alice’s pending collective response;
- Bob sees Bob’s pending collective response;
- member C not required in that decision sees no collective attention.

One member must not see another member’s private intent clarification as their own task.

Approval visibility still follows existing auth/capability rules.

## 6. Attention is not authority

Clicking an AttentionItem does not magically authorize anything.

It should route to the existing server operation:

- approval -> existing ActionApproval endpoint;
- collective response -> existing R45 endpoint;
- intent clarification -> resume/update the same JourneyIntent;
- depart/arrive/begin/complete -> existing R48 execution transitions;
- route check -> existing R41 route operation;
- transaction attention -> review existing R47 execution plan.

No duplicated mutation endpoints unless an ergonomic façade delegates 1:1 to the existing authority path.

## 7. Intent clarification continuation

R51 exposed a real user-facing gap:
- intent can become NEEDS_CLARIFICATION;
- user currently has to conceptually “try again”.

R52 must allow the traveller to answer the clarification **inside the same intent lineage**.

Example:

Original:
> “I’m tired. Make the rest of today easier.”

CityNexus:
> “What matters most: less walking, fewer stops, or a slower pace?”

User:
> “Less walking.”

Server:
- updates/resolves the existing JourneyIntent clarification;
- keeps original source text + clarification answer;
- preserves scope;
- does not create a second unrelated intent;
- then evaluates the same intent.

This path must work even without an external semantic model when the clarification options are already server-bounded.

Do not pretend fallback performed open-ended semantic reasoning.

## 8. Execution confirmations should surface only when useful

Examples:
- ARRIVAL_READY -> primary attention may be “I’m here”
- READY_TO_BEGIN -> “Start”
- READY_TO_COMPLETE -> “Done”
- LEAVE_NOW -> “I’m leaving”

But if a P1 approval is blocking a required recovery at the same time:
- approval wins;
- flow milestone remains visible in the normal flow section.

Attention is “what needs me most”, not “hide all state”.

## 9. Notification policy

Notifications should be generated from **attention transitions**, not every subsystem separately.

One AttentionItem becoming newly blocking may notify.

Use stable dedupe:
- journey
- viewer/member
- attention semantic identity

Examples:
- approval id;
- clarification id;
- collective decision epoch + member;
- activity id + milestone;
- execution plan id + partial state.

When the item is resolved:
- no repeated notification.

Do not build a second notification system.

## 10. Quiet mode

Add a simple Operator preference:

- `NORMAL`
- `QUIET`

R52 v1 may make QUIET the recommended/default presentation without changing authority.

QUIET means:
- routine timeline chatter does not interrupt;
- only blocking/high-value attention is promoted;
- morning briefing remains visible but need not notify if no action required;
- R49 future-watch info stays passive unless action threshold is crossed.

Do not suppress safety-critical or authority-required interruptions.

## 11. Attention lifecycle

An item should be:
- PENDING
- RESOLVED
- SUPERSEDED
- EXPIRED

Prefer deriving state from source objects when possible rather than introducing a second mutable state machine.

Examples:
- approval approved/rejected -> attention resolved;
- intent clarification answered -> resolved;
- activity transition completed -> milestone attention resolved;
- route operation completed -> route-check attention resolved.

## 12. One action resumes the original flow

This is the core acceptance rule.

After user action:
- do not start a new generic Operator flow;
- resume the source lineage.

Examples:
- approval -> exact pending Agent action resumes;
- collective answer -> same collective decision continues;
- clarification answer -> same JourneyIntent evaluation continues;
- arrival confirmation -> same R48 continuous Journey continues.

User experience:

> “Done. CityNexus is taking it from here.”

## 13. UI

Replace scattered competing CTAs with one primary block:

### Needs you

**CityNexus found a safer plan**
This changes one stop and preserves your booking.

[Review change]

or:

**One quick question**
When you said “take it easy,” what matters most?

[Less walking]
[Fewer stops]
[Slower pace]

or:

**You’re near the museum**
Confirm when you arrive.

[I’m here]

Below it, the normal Operator sections remain:
- Now
- Looking ahead
- Overnight
- Timeline

But they should not each compete with separate primary buttons when attention exists.

## 14. Operator state vs attention

Do not overload the top-level Operator state.

Example:
- Operator state may remain WATCHING;
- attention may be CONFIRM_COMPLETE.

Or:
- Operator state WAITING_FOR_APPROVAL;
- attention APPROVAL_REQUIRED.

Both are useful.

## 15. No external model dependency required

R52 must not depend on configuring a model merely to prove the product.

Use server-owned durable truth to derive attention.

For R51 clarification continuation:
- if the clarification question/options are already bounded and persisted, user choosing one can deterministically fill that specific missing semantic slot;
- if truly open-ended semantic reinterpretation is needed and no external model is configured, remain blocked honestly.

Do not call deterministic option selection “model reasoning”.

## 16. Focused tests

Only tests that prove the new human-interruption loop:

1. no unresolved source -> attention null.
2. approval beats route check.
3. transaction partial beats ordinary milestone.
4. viewer-specific collective attention is isolated.
5. intent clarification becomes one primary AttentionItem.
6. bounded clarification answer resumes same JourneyIntent id.
7. clarification resolution does not create a duplicate intent.
8. approval action delegates to existing approval path.
9. arrival/start/done attention delegates to R48 strong execution path.
10. route-check attention delegates to R41 operation.
11. source resolution removes/supersedes attention.
12. repeated GET is read-only.
13. notifications dedupe by attention identity.
14. quiet mode suppresses nonblocking chatter but not P0/P1.
15. one user action returns Operator to autonomous continuation where appropriate.
16. TypeScript + focused Decision Inbox Playwright.

Do not rerun historical campaigns.

## 17. One bounded R52 product experiment

Use one fresh Journey with Operator ON.

Create a real product-state interruption through an existing path.

Preferred experiment because it does not require external model credentials:

1. Submit the same style of R51 temporary intent and let it enter NEEDS_CLARIFICATION using the honest deterministic fallback.
2. Operator exposes exactly one primary AttentionItem:
   `INTENT_CLARIFICATION_REQUIRED`.
3. User answers one bounded option:
   e.g. `LESS_WALKING`.
4. The same JourneyIntent id becomes resolved/ACTIVE with the missing semantic constraint filled.
5. No duplicate JourneyIntent.
6. Current Activity remains unchanged.
7. If further Agent evaluation requires an unavailable external model, stop honestly at BRAIN_BLOCKED; do not fake it.
8. The important R52 proof is that the user did not need to resubmit/rephrase the whole request.

Alternative bounded experiment:
- use an R48 execution milestone attention.

Valid outcomes:
- `DECISION_INBOX_CLARIFICATION_RESOLVED`
- `DECISION_INBOX_APPROVAL_RESUMED`
- `DECISION_INBOX_EXECUTION_CONFIRMED`
- `DECISION_INBOX_BRAIN_BLOCKED_AFTER_RESPONSE`
- `DECISION_INBOX_NO_ATTENTION`

## Stop condition

Stop after one real “Needs you” item is surfaced, answered once, and the original source flow resumes or honestly blocks at the next external dependency.

End-user capability:

> **“I don’t supervise CityNexus anymore. It works quietly, and when it truly needs me, it asks one clear thing in one place. I answer once, and it keeps going.”**
