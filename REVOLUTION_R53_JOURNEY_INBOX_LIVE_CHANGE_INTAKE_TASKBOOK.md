# REVOLUTION R53 — Journey Inbox / Live Reservation Change Intake

## Product-direction gate

Governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

## User capability — put this sentence at the top of the result

> **The traveller can now forward a booking confirmation, schedule-change message, cancellation notice, or reservation screenshot to the running Journey, and CityNexus turns it into grounded Journey reality: it binds the message to the right reservation/activity, updates Commitment truth only when sufficiently grounded, asks one clear question when ambiguous, and automatically hands any material impact to the existing Journey Operator for recovery.**

If this becomes “improve OCR”, “add another upload page”, or “test reservation import harder”, stop and correct course.

## Starting truth

R52 is complete at `b660688c15294897554a9afc47f7675e40b7b0bb`.

R52 proved:
- one unified Needs-you decision;
- same-lineage bounded clarification;
- no duplicate intent;
- honest BRAIN_BLOCKED after the user supplied the missing meaning;
- user does not need to understand internal subsystems.

Do not rerun R33-R52 historical closures.

## Existing capabilities to connect — do not reimplement

Already present:
- reservation text extraction;
- reservation image extraction;
- `ExternalReservationDraft`;
- `prepare_semantic_intake()`;
- server-side semantic target resolution;
- journey-match confidence;
- duplicate confirmation detection;
- arrival/departure/mid-trip roles;
- `TransportReservation`;
- `Commitment`;
- reservation confirmation/import;
- Journey Operator / Guardian / recovery;
- R52 Needs-you inbox.

The missing capability:

**new reservation/change information is not yet a first-class continuous Operator input that can change Journey truth and automatically trigger impact handling.**

## 1. First-class Journey Inbox item

Create a durable `JourneyInboxItem` / semantic equivalent for each external message/artifact.

Suggested fields:
- id
- journey_id nullable until bound
- traveler_id
- source_kind
- source_label
- raw_text_hash / artifact_hash
- received_at
- extraction_status
- semantic_kind
- reservation_type
- confirmation_ref
- change_kind
- effective_at
- target_binding_json
- extracted_json
- provenance
- status
- linked_draft_id
- linked_reservation_id
- linked_commitment_id
- impact_status
- created_at / updated_at

Suggested source kinds:
- PASTED_TEXT
- IMAGE_UPLOAD
- EMAIL_FORWARD_REPLAY
- LAB_MESSAGE_FIXTURE

Do not claim actual email integration unless a real connector exists.

## 2. Message kinds

Bound v1 to:
- NEW_CONFIRMATION
- SCHEDULE_CHANGE
- CANCELLATION
- LOCATION_CHANGE
- STATUS_CHANGE
- UNKNOWN

Examples:
- “Your train now departs at 18:10 instead of 17:40.”
- “Your hotel reservation is confirmed.”
- “Restaurant booking cancelled.”
- “Gate changed” may be captured as STATUS_CHANGE but only becomes planning-relevant if the server has grounded semantics.

Do not build a universal email understanding system.

## 3. Extraction vs truth

Model/extractor may suggest:
- reservation type;
- confirmation ref;
- old/new times;
- provider;
- semantic target;
- change kind.

Server owns:
- Journey identity;
- exact Reservation/Commitment identity;
- target Activity;
- duplicate detection;
- conflict detection;
- whether the change is grounded enough to update truth.

The model must not directly mutate:
- TransportReservation;
- Commitment;
- Activity;
- PlanVersion.

## 4. Journey binding

If the inbox item is submitted from inside a Journey:
- that Journey is the primary candidate;
- still validate obvious mismatch.

If submitted globally:
- use existing candidate-journey match semantics;
- auto-bind only with strong confidence;
- otherwise R52 attention asks:
  > “Which trip does this belong to?”

Do not silently attach a weakly matched reservation to the wrong Journey.

## 5. Reservation identity

Prefer exact matching by:
1. confirmation_ref + provider/type;
2. linked existing draft;
3. server-resolved semantic target + compatible time/provider;
4. bounded user clarification.

Do not use fuzzy title matching alone to overwrite an existing commitment.

## 6. Change application contract

For NEW_CONFIRMATION:
- use existing reservation confirmation/import path;
- create/update TransportReservation + Commitment through existing services.

For SCHEDULE_CHANGE:
- update the existing reservation/commitment only after exact binding;
- preserve prior value in audit/history;
- mark source/provenance.

For CANCELLATION:
- do not delete history;
- transition reservation/commitment to cancelled/inactive using existing semantics.

For UNKNOWN:
- keep inbox item review-only.

## 7. Material impact handoff

After grounded truth changes, compute Journey impact.

Examples:
- train now arrives 45 min later;
- hotel cancellation removes protected stay;
- restaurant cancellation affects a booked Activity;
- flight schedule change compresses transfer slack.

If no material plan impact:
- Operator timeline records the update;
- no AgentRun.

If material:
- create/enter the normal existing recovery path;
- Guardian/Operator handles it;
- R49 future-risk semantics apply if the effect is still future;
- R43 approval / R45 collective / R47 transaction remain authoritative.

Do not create a special “reservation recovery Agent”.

## 8. Future vs current truth

A future schedule change is real reservation truth but may still be a future planning impact.

Example:
- tomorrow train changed from 09:00 to 10:00.

Truth:
- TransportReservation scheduled departure is now 10:00.

Execution:
- current Activity today is untouched.

Operator:
- ahead/future impact may become actionable.

Do not confuse “fact is real now” with “execution disruption is current now”.

## 9. One clear clarification through R52

Ambiguity should become one Needs-you item.

Examples:
- same provider has two bookings with no confirmation ref;
- screenshot omits which traveler;
- cancellation text does not identify which reservation.

Attention kind suggestion:
`INBOX_BINDING_REQUIRED`

Question:
> “I found two matching train bookings. Which one changed?”

The user chooses from server-owned candidates.

After answer:
- same JourneyInboxItem continues;
- do not ask them to re-upload/re-paste.

## 10. Idempotency

Same artifact/message replay must not:
- create duplicate reservation;
- duplicate commitment;
- duplicate Event;
- duplicate recovery.

Identity should use:
- artifact/text hash;
- provider confirmation ref when present;
- change semantic fingerprint.

Repeated processing returns the same inbox item/result.

## 11. Provenance

Clearly distinguish:
- USER_PASTED_TEXT
- USER_UPLOADED_IMAGE
- CAPTURED_REPLAY
- LIVE_CONNECTED_INBOX (future only when actually connected)

Do not label a pasted screenshot as provider-live.

The external document is user-provided evidence; it may still be strong enough to update a reservation when the product’s existing import semantics permit it.

## 12. Operator projection

Add `inbox` to Journey Operator:

```json
{
  "latest": {
    "kind": "SCHEDULE_CHANGE",
    "headline": "Your train time changed",
    "status": "APPLIED",
    "impact": "RECOVERY_REQUIRED"
  },
  "pending_count": 0
}
```

User-facing examples:

> “Your 17:40 train now leaves at 18:10. I updated the reservation and I’m checking the rest of your evening.”

or:

> “I received a booking update, but I need one detail before I can apply it.”

## 13. R52 integration

If inbox clarification is needed:
- surface it in the single Needs-you card;
- give it appropriate P1 priority;
- do not add another competing inbox UI.

Suggested attention kind:
`INBOX_BINDING_REQUIRED`

Once answered:
- same inbox item continues automatically.

## 14. R50 overnight integration

If a grounded booking update arrives/gets imported overnight:
- same Operator remains responsible;
- morning briefing reflects it;
- if approval is needed, morning briefing says “1 thing needs you.”

No new Journey/session.

## 15. Collective journeys

A reservation belonging to one member should not automatically become a group commitment.

Bind to:
- correct traveler/member;
- Journey shared context;
- exact Activity/Commitment scope.

If a grounded change materially affects the shared plan:
- R45 collective authority applies.

## 16. External model availability

Do not make R53 dependent on a configured external model for its core proof.

Use the existing deterministic extraction/import path where fields are explicit in a structured pasted message or LAB fixture.

If image/OCR/semantic ambiguity truly needs an external model and none is configured:
- keep NEEDS_REVIEW;
- do not invent interpretation.

R53's product proof can use a clear structured schedule-change message with exact confirmation ref.

## 17. Focused tests

Only tests needed for the new capability:

1. pasted message creates one JourneyInboxItem.
2. duplicate text/artifact reuses same item.
3. exact confirmation ref binds existing reservation.
4. weak fuzzy match does not overwrite reservation.
5. grounded schedule change updates TransportReservation once.
6. linked Commitment reflects the new time.
7. cancellation preserves history and cancels truth.
8. current Activity remains unchanged for a future reservation change.
9. no material impact -> no AgentRun.
10. material impact -> normal Operator recovery path.
11. ambiguous binding -> one R52 attention item.
12. clarification updates same inbox item.
13. no duplicate Event/recovery after replay.
14. provenance never claims LIVE provider for pasted/replayed content.
15. overnight briefing sees applied future change.
16. shared Journey respects member/collective authority.
17. TypeScript + focused Journey Inbox Playwright.

Do not rerun historical campaigns.

## 18. One bounded R53 product experiment

Use one fresh Journey with:
- Operator ON;
- one real/sandbox imported transport reservation + Commitment;
- current Activity still active;
- future reservation later in the Journey.

Submit exactly one clear LAB/user-pasted schedule-change message, e.g.:

> “Booking ZX42 update: departure changed from 17:40 to 18:10. Confirmation AB123.”

Use exact confirmation ref so the core experiment does not require external semantic-model credentials.

Sequence:
1. inbox item persisted once;
2. exact reservation binding;
3. reservation/commitment truth updates;
4. current Activity execution truth unchanged;
5. impact resolver evaluates downstream Journey;
6. if material, existing Operator recovery starts;
7. if not material, timeline acknowledges update and stops;
8. replay same message once -> idempotent reuse, no duplicate mutation/recovery;
9. stop.

Valid outcomes:
- `JOURNEY_INBOX_CHANGE_APPLIED_NO_MATERIAL_IMPACT`
- `JOURNEY_INBOX_CHANGE_TRIGGERED_RECOVERY`
- `JOURNEY_INBOX_BINDING_REQUIRED`
- `JOURNEY_INBOX_NEEDS_REVIEW`
- `JOURNEY_INBOX_DUPLICATE_REUSED`

## Stop condition

Stop after one incoming travel message becomes either:
- grounded Journey truth with correct impact handling; or
- one bounded Needs-you clarification.

End-user capability:

> **“When a booking or schedule update arrives, I can hand it to CityNexus instead of manually editing the trip. It understands what changed, updates the real reservation/commitment, and takes care of the knock-on effects.”**
