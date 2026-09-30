# ORD-0464 r8 -- whose lines are whose in backend/app/main.py

The tip (bf3ad1635873) holds this one file as CRLF (13847 lines, 0 CR bytes; every other
face of mine is LF), which is why `git apply --3way` of my LF patch conflicted over the whole file
rather than over my region. The resolution keeps both sides: the tip's bytes are taken as the file,
my six hunks are replayed onto it, and CRLF is restored on every line.

Proof, not intent: `git diff --ignore-cr-at-eol -U0 <tip> -- backend/app/main.py` yields the same
six hunks with the same added and removed lines as `git diff -U0 <r6 base> <r6>` -- so nothing of the
796 lines the tip added to this file since my r6 base was rewritten, and none of my lines
replaced them.
numstat against the tip reads 46 added / 2 deleted both raw and --ignore-cr-at-eol.  File after the replay: 13891 lines, 13891 CR bytes, 610421 B.

Hunk by hunk (positions are in the tip's file; `mine` lists what this order adds there):

## hunk 1  @@ -20 +20 @@ import httpx
  lines that were the tip's and this order replaces:
    - from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
  lines this order adds:
    + from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, Request, Response

## hunk 2  @@ -341,0 +342 @@ from app.schemas import (
  lines this order adds:
    +     JourneyAbortRequest,

## hunk 3  @@ -3036 +3037,5 @@ def list_journeys(session: Session = Depends(get_session)):
  lines that were the tip's and this order replaces:
    - def delete_journey(journey_id: UUID, session: Session = Depends(get_session)):
  lines this order adds:
    + def delete_journey(
    +     journey_id: UUID,
    +     session: Session = Depends(get_session),
    +     abort: JourneyAbortRequest | None = Body(default=None),
    + ):

## hunk 4  @@ -3049,0 +3055,16 @@ def delete_journey(journey_id: UUID, session: Session = Depends(get_session)):
  lines this order adds:
    + 
    +     ORD-0464 added the optional reason object.  It arrives as a body on this same door rather than
    +     as a second call, because two calls can fail independently: a screen that recorded a reason and
    +     then lost the delete would leave a trip with a stated cause nobody acted on, and a screen that
    +     deleted and then failed to record would look like the traveller left without a word.  One
    +     request, one transaction, one outcome row - the same `journey_outcome_events` table the
    +     execution timeline already writes, with `event_type = "JOURNEY_DELETED"`, which this door is the
    +     only producer of (`OutcomeEventCreate` does not list it, so a client cannot file the fact of a
    +     deletion through the generic outcomes door).
    + 
    +     Three states travel, and none of them is a default.  A body whose `answered` is false is the
    +     traveller declining to say (`SKIPPED_BY_TRAVELER`); a body naming reasons is `DECLARED`; and no
    +     body at all is `NOT_ASKED`, which is what every client that predates this order sent.  That
    +     third one cannot be claimed in a payload on purpose: `answered` is a required field, so a caller
    +     that never showed the question records the absence, not a word the traveller never said - the
    +     `stay_budget_declared` rule from ORD-0355 applied to a question this server asks once per trip.

## hunk 5  @@ -3064,0 +3086,8 @@ def delete_journey(journey_id: UUID, session: Session = Depends(get_session)):
  lines this order adds:
    +     if abort is None:
    +         reason_state = "NOT_ASKED"
    +         codes: list[str] = []
    +         note: str | None = None
    +     else:
    +         reason_state = "DECLARED" if abort.answered else "SKIPPED_BY_TRAVELER"
    +         codes = abort.unique_codes() if abort.answered else []
    +         note = abort.note

## hunk 6  @@ -3073,0 +3103,15 @@ def delete_journey(journey_id: UUID, session: Session = Depends(get_session)):
  lines this order adds:
    +     _record_outcome_event(
    +         session,
    +         journey,
    +         activity=None,
    +         event_type="JOURNEY_DELETED",
    +         actor_type="USER",
    +         occurred_at_actual=journey.deleted_at,
    +         payload={
    +             "reason_state": reason_state,
    +             # `codes` means anything only beside DECLARED; the empty list in the other two states is
    +             # the shape of the question going unanswered, not a reason that happens to be blank.
    +             "codes": codes,
    +             "note": note,
    +         },
    +     )

Everything else in the file -- including the 796 lines that arrived after my r6 base (the member
doors, the calendar export door, the footprint doors, the share landing) -- is the tip's own text,
untouched and in the tip's own order.

## Where the other faces landed

`backend/app/schemas.py`, `contracts/openapi.yaml`, `frontend/src/app/v8PanelRegistry.tsx` and
`frontend/src/generated/api.ts` were all also changed by the tip since my r6 base, but those apply
cleanly (schemas 74/0, contract 80/0 in two pure appends, registry 16/0, client 35/1 by
regeneration). The four new files (this order's panel, copy table, service module, css) and the
test and spec files are additions with no counterpart on the tip.
