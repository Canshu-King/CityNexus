"""ORD-0496 slice 1 - the calendar door, tested where an iCalendar file actually goes wrong.

The order named seven arms.  Each one below is tied to a clause of that order, and the clauses that
matter are the ones nobody can see from a happy path:

1. one door, one read authority -- `GET /api/v1/journeys/{journey_id}` is the trip's read door, so
   the 404 here is that door's answer with the ORD-0101 name attached, and the plan it exports is
   the row `journeys.active_plan_version_id` points at, never a second notion of "the plan";
2. RFC 5545 escaping and line width, the escape and fold arms.  These are the two families this
   project has learned to expect a generator to get wrong, so they are judged by a **decoder written
   in this file** (`_unfold`, `_content_lines`, `_decode_text`, `_bare_special_positions`) and never
   by the exporter's own parser -- a writer that checks its output with its own reader proves
   nothing.  `_unfold` implements §3.1's rule that unfolding deletes the CRLF *and one following
   space*, which is what catches a fold placed at a space; and the width is measured in octets,
   because 75 characters of CJK is 225 octets and a file that passes a `len()` check is not a file;
3. no fabricated time: `DTSTART`/`DTEND` are the two instants the row carries converted to UTC, and
   `DTSTAMP` is the row's own `updated_at` (`created_at` behind it).  The determinism arm moves that
   column and shows the stamp moves with it, which is the only way to tell "from the row" apart from
   "from the request";
4. activities with no usable clock are skipped **and counted**.  The arithmetic arm asserts
   `activities = events + skipped_no_clock + skipped_no_stamp` against the store's own row count,
   the shape that makes "nothing was dropped" checkable from headers alone.  Its two input shapes (a
   bare date, a clock without an offset) are hand-inserted, and that is stated rather than hidden:
   the read-only census in `review/ord0496/store_shape_census_r1.py` measures 134 of 134 activity
   rows in the commander's live store carrying an explicit offset, so this arm guards a rule the
   column can hold but today's generator does not write;
5. three named refusals -- recycle bin, unknown trip, unreadable source -- all three in
   `contracts/openapi.yaml`, plus the six count headers and the invariant above;
6. the media type and the file name: `text/calendar; charset=utf-8`, an ASCII fallback that stays
   generic, and `filename*` carrying the real title back through percent-decoding -- including a
   title with a quote, a slash and a comma, which is the shape that would let a name restructure the
   header.

The two claims a reader would otherwise take on trust get arms of their own: that an interval
crossing the printed day boundary stays the one event the row is (splitting it would need two
instants that exist in no column), and that a SUPERSEDED plan version's rows cannot leak in.

Nothing here calls `POST /api/v1/demo/reset`, nothing opens a socket, and nothing writes outside the
temporary store `conftest.py` resolves for this process.

FUSION PORT NOTE (`fusion/qoder-import-20261014`, from `eeb8b8d2fd`).  The fifteen arms above were
copied byte-identical first, and run as they were: **all fifteen failed**, every one of them on
`401 {"code":"REQUEST_ERROR","message_key":"error.request_error"}` or on the contract.  That is the
measurement of the seam this branch put on the door -- the source door answered an anonymous request
with the whole schedule, so a test written against it had no credential to send.  Three things change
here and nothing else does:

* `_auth()`/`_OWNER` -- the traveller who owns each staged trip is minted by `_journey()` and recorded,
  and `_ics()` signs a token for that owner.  Every grammar, folding, clock and header arm below is
  unchanged, because the door's *behaviour* is unchanged for the traveller the file belongs to.
* three arms are ADDED (`ord0496-fusion`), for the states the source door could not have: an
  anonymous export, somebody else's valid token on my trip, and a `traveler_id` query parameter.
* two arms are DEFERRED and named, not deleted: the contract and generated-client arms.
  `test_the_two_source_arms_deferred_to_the_contract_leg_are_still_deferred_and_measured` re-measures
  why each time it runs, and will fail the moment this branch's contract grows the operation, which
  is the point at which those two arms must come back.

The bin walk is unchanged because `DELETE /api/v1/journeys/{id}` and `/undelete` are still not
principal-bound on this branch -- `test_qoder_ord0476_checkins_fusion.py` records that fact at its own
arm 8, and this port does not silently tighten a neighbour.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote
from uuid import uuid4

import yaml
from fastapi.testclient import TestClient
import pytest

from app.core.config import settings
from app.db.models import Activity, Journey, Place, PlanVersion, Traveler
from app.db.session import SessionLocal
from app.main import app
from app.traveler_principal import issue_traveler_token

client = TestClient(app, raise_server_exceptions=False)
ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "openapi.yaml"
GENERATED = ROOT / "frontend/src/generated/api.ts"
DOOR_PATH = "/journeys/{journey_id}/calendar.ics"
MOMENT = "2026-09-30T00:00:00+00:00"
MOVED_MOMENT = "2032-01-01T06:00:00+00:00"

# A signing key for this process only, in the same shape the other fusion principal tests use
# (`test_qoder_ord0476_checkins_fusion.py`, `test_qoder_ord0444_collections_fusion.py`): a literal
# that is a credential nowhere, installed on `settings` for the module and restored after it.
_TEST_SECRET = "ord0496-calendar-fusion-test-secret-0123456789abcdef"

# Which traveller a staged trip belongs to.  `_ics()` signs for the owner it finds here, so the arms
# that judge iCalendar grammar keep their exact source text; only the fusion-specific arms pass a
# different credential explicitly.
_OWNER: dict[str, str] = {}


@pytest.fixture(scope="module", autouse=True)
def _traveler_secret_is_installed():
    previous = settings.traveler_auth_secret
    object.__setattr__(settings, "traveler_auth_secret", _TEST_SECRET)
    try:
        yield
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous)

#: The four characters §3.3.11 escapes, plus a colon, a quote and a slash, which it must not escape.
NASTY_TITLE = "鼓浪屿:轮渡,第二站;备注\\末行\n换行之后"
NASTY_PLACE = '厦门市思明区,鹿礁路"18"号/2层'
LONG_TITLE = "环鼓浪屿一周——轮渡、日光岩、菽庄花园、皓月园、风琴博物馆与龙头路小吃街的行程说明"
#: Built by arithmetic rather than by guesswork, because the arm below asserts the fold actually
#: landed on a space: `SUMMARY:` costs 8 octets, 66 `a` reach 74, the next single space fills the
#: 75-octet line, and the character after it therefore has to break -- with a space at the end of
#: the line, which is exactly the position unfolding would silently eat.  The two trailing spaces
#: exist to make the trim arm of the same rule fire in the same body.
SPACE_EDGE_TITLE = "a" * 66 + " " + "b" * 40 + "  "


def _store_path() -> Path:
    from conftest import RESOLVED_TEST_DATABASE

    return Path(RESOLVED_TEST_DATABASE.replace("sqlite:///", "", 1)).expanduser().resolve()


# ------------------------------------------------------- the decoder, written from RFC 5545 itself


def _unfold(body: str) -> list[str]:
    """RFC 5545 §3.1 unfolding: CRLF ends a line, a continuation starts with one WSP.

    Written from the grammar rather than imported from `app.calendar_export`, so a fold the writer
    would mis-undo is still undone correctly here.  §3.1 deletes the CRLF *and one following space*.
    """

    assert body.endswith("\r\n"), "every line of an iCalendar object ends with CRLF"
    logical: list[str] = []
    for physical in body[:-2].split("\r\n"):
        if physical[:1] in (" ", "\t"):
            assert logical, f"the object opens with a continuation line: {physical!r}"
            logical[-1] += physical[1:]
        else:
            logical.append(physical)
    return logical


def _content_lines(body: str) -> list[tuple[str, str]]:
    """`(name, value)` per logical line, with §3.1's parameters cut off the name."""

    out: list[tuple[str, str]] = []
    for line in _unfold(body):
        if not line:
            continue
        name, separator, value = line.partition(":")
        assert separator, f"a contentline carries a colon: {line!r}"
        out.append((name.split(";", 1)[0], value))
    return out


def _decode_text(value: str) -> str:
    """§3.3.11 TEXT unescaping, independent of the exporter's own `unescape_text`."""

    out: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            following = value[index + 1]
            if following in ("n", "N"):
                out.append("\n")
                index += 2
                continue
            if following in (",", ";", "\\"):
                out.append(following)
                index += 2
                continue
        out.append(value[index])
        index += 1
    return "".join(out)


def _bare_special_positions(value: str) -> list[int]:
    """Offsets where a `,` `;` `\\` sits with no escape in front, or a raw CR/LF appears at all.

    The point of checking this instead of just round-tripping: an unescaped comma is legal ASCII, a
    naive reader still prints it, and only the *consumer* that splits on the comma loses the rest of
    the property.  That is the class this arm exists to catch.
    """

    offenders: list[int] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\r" or char == "\n":
            offenders.append(index)
            index += 1
            continue
        if char == "\\":
            following = value[index + 1 : index + 2]
            if following in (",", ";", "\\", "n", "N"):
                index += 2
                continue
            offenders.append(index)
            index += 1
            continue
        if char in (",", ";"):
            offenders.append(index)
        index += 1
    return offenders


def _events(body: str) -> list[dict[str, str]]:
    """One dict per VEVENT, in the order the object prints them."""

    events: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for name, value in _content_lines(body):
        if name == "BEGIN" and value == "VEVENT":
            assert current is None, "VEVENT nested inside VEVENT"
            current = {}
        elif name == "END" and value == "VEVENT":
            assert current is not None, "END:VEVENT without a BEGIN"
            events.append(current)
            current = None
        elif current is not None:
            assert name not in current, f"{name} printed twice inside one VEVENT"
            current[name] = value
    assert current is None, "unclosed VEVENT"
    return events


def _physical_lines(body: str) -> list[str]:
    assert body.endswith("\r\n")
    return body[:-2].split("\r\n")


# ------------------------------------------------------------------ the fixtures, row by deliberate row


def _place(label: str, name: str) -> str:
    identifier = f"ord0496-{label}-{uuid4().hex[:8]}"
    with SessionLocal() as session:
        session.add(
            Place(
                id=identifier,
                provider_key="ord0496-probe",
                external_id=identifier,
                city_code="CN-XIAMEN",
                name=name,
                category="sight",
                latitude=24.45,
                longitude=118.07,
                opening_hours_json=json.dumps({"open": "07:00", "close": "19:00"}),
                tags_json=json.dumps(["ord0496"]),
                metadata_json="{}",
                updated_at=MOMENT,
            )
        )
        session.commit()
    return identifier


def _activity(plan: str, sequence: int, **fields: object) -> str:
    identifier = str(fields.pop("id", None) or f"ord0496-a{sequence}-{uuid4().hex[:8]}")
    row: dict[str, object] = {
        "id": identifier,
        "plan_version_id": plan,
        "sequence_no": sequence,
        "activity_type": "visit",
        "title": f"第 {sequence} 站",
        "place_id": None,
        "city_service_id": None,
        "start_at": "2031-05-01T09:00:00+08:00",
        "end_at": "2031-05-01T10:30:00+08:00",
        "travel_from_prev_min": 0,
        "estimated_cost_minor": 0,
        "currency": "CNY",
        "status": "PLANNED",
        "locked": False,
        "metadata_json": "{}",
        "created_at": MOMENT,
        "updated_at": MOMENT,
    }
    row.update(fields)
    with SessionLocal() as session:
        session.add(Activity(**row))  # type: ignore[arg-type]
        session.commit()
    return identifier


def _plan(journey: str, version_no: int, status: str) -> str:
    identifier = str(uuid4())
    with SessionLocal() as session:
        session.add(
            PlanVersion(
                id=identifier, journey_id=journey, version_no=version_no,
                planning_mode="balanced", status=status, source="INITIAL",
                total_cost_minor=0, currency="CNY", estimated_duration_min=600,
                created_at=MOMENT,
            )
        )
        session.commit()
    return identifier


def _journey(title: str = "沿海一周") -> str:
    identifier = str(uuid4())
    with SessionLocal() as session:
        traveler = Traveler(
            id=str(uuid4()), display_name="ORD-0496 探针", email=None, locale="zh-CN",
            timezone="Asia/Shanghai", created_at=MOMENT, updated_at=MOMENT,
        )
        session.add(traveler)
        session.flush()
        session.add(
            Journey(
                id=identifier, traveler_id=traveler.id, title=title, city_code="CN-XIAMEN",
                timezone="Asia/Shanghai", start_at="2031-05-01T00:00:00+08:00",
                end_at="2031-05-09T00:00:00+08:00", budget_amount_minor=120000,
                budget_currency="CNY", status="PLANNED", created_at=MOMENT, updated_at=MOMENT,
                active_plan_version_id=None,
            )
        )
        session.commit()
    # FUSION ADDITION: the owner is remembered, because on this branch the export door asks who is
    # asking.  The source helper minted the same traveller row and then dropped its id, since its
    # door never looked at a credential.
    _OWNER[identifier] = traveler.id
    return identifier


def _probe_traveller() -> str:
    """A credential with no trip of its own, for the arms that need *some* valid caller.

    `JOURNEY_NOT_FOUND` has to be asked by somebody who is authenticated; asking anonymously would
    answer 401 and measure a different fact.
    """

    identifier = str(uuid4())
    with SessionLocal() as session:
        session.add(
            Traveler(
                id=identifier, display_name="ORD-0496 无名探针", email=None, locale="zh-CN",
                timezone="Asia/Shanghai", created_at=MOMENT, updated_at=MOMENT,
            )
        )
        session.commit()
    return identifier



def _raw_update(statement: str, parameters: tuple = ()) -> None:
    """One statement straight to the store, foreign keys left off -- see the arm that needs it."""

    with sqlite3.connect(_store_path()) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(statement, parameters)
        connection.commit()


def _trip() -> dict:
    """One trip whose seven activity rows each exist to break one clause of the order.

    Rows 1-3 are the clocked days on three separate days (row 3 crossing the day boundary the file
    prints), rows 4-5 are the two ways "no usable clock" arrives, row 6 has a clock but no usable
    stamp of its own, and row 7 sits on a SUPERSEDED plan version to prove the pointer is the
    source.
    """

    place = _place("nasty", NASTY_PLACE)
    journey = _journey()
    plan = _plan(journey, 1, "ACTIVE")
    superseded = _plan(journey, 2, "SUPERSEDED")
    _raw_update(
        "UPDATE journeys SET active_plan_version_id = ? WHERE id = ?", (plan, journey)
    )
    clocked = [
        _activity(
            plan, 1, title=NASTY_TITLE, place_id=place, estimated_cost_minor=3500,
            start_at="2031-05-01T09:00:00+08:00", end_at="2031-05-01T11:00:00+08:00",
        ),
        _activity(
            plan, 2, title="日光岩,第二个入口", start_at="2031-05-08T09:30:00+08:00",
            end_at="2031-05-08T11:00:00+08:00",
        ),
        _activity(
            plan, 3, title="夜航跨日", start_at="2031-05-03T22:00:00+00:00",
            end_at="2031-05-04T01:30:00+00:00",
        ),
    ]
    no_clock = [
        _activity(
            plan, 4, title="只有日期的一格", start_at="2031-05-05",
            end_at="2031-05-05T23:59:00+08:00",
        ),
        _activity(
            plan, 5, title="有时刻无时区", start_at="2031-05-06T09:00:00",
            end_at="2031-05-06T10:00:00",
        ),
    ]
    no_stamp = _activity(
            plan, 6, title="没有自己时刻戳的一格", start_at="2031-05-07T14:00:00+08:00",
            end_at="2031-05-07T15:00:00+08:00", created_at="", updated_at="",
    )
    hidden = _activity(
        superseded, 1, title="上一版计划的格子绝不该出现",
        start_at="2031-05-01T08:00:00+08:00", end_at="2031-05-01T08:30:00+08:00",
    )
    return {
        "journey": journey, "plan": plan, "superseded": superseded, "place": place,
        # FUSION ADDITION: the trip's owner travels with the fixture, so an arm can ask as its own
        # traveller or as somebody else without re-deriving the id from the store.
        "traveler": _OWNER[journey],
        "clocked": clocked, "no_clock": no_clock, "no_stamp": no_stamp, "hidden": hidden,
    }


def _auth(traveller_id: str | None) -> dict[str, str]:
    """The credential for a traveller, or no credential at all for `None`.

    Minted by the product's own server-side signer (`issue_traveler_token`), the same helper the
    footprint and shelf tests use; there is no door on this server that hands out a token for an id
    somebody names, and that asymmetry is the whole point of the retrofit.
    """

    if traveller_id is None:
        return {}
    return {"Authorization": f"Bearer {issue_traveler_token(traveller_id)}"}


def _ics(journey: str, headers: dict | None = None):
    """The export door, signed for the trip's owner unless the caller names a credential.

    `headers={}` means "send nothing", which is why the override is tested against `None` and not
    against falsiness: the anonymous arm asks for exactly that state.
    """

    if headers is None:
        headers = _auth(_OWNER.get(journey))
    return client.get(f"/api/v1/journeys/{journey}/calendar.ics", headers=headers)


def _body(response) -> str:
    return response.content.decode("utf-8")


def _count(response, name: str) -> int:
    header = f"X-CityNexus-Ics-{name}"
    assert header in response.headers, sorted(response.headers)
    return int(response.headers[header])


def _error(body: object) -> dict:
    assert isinstance(body, dict) and isinstance(body.get("error"), dict), body
    return body["error"]


def _reason(body: object) -> str | None:
    return _error(body).get("reason_code")


def _details(body: object) -> dict:
    value = _error(body).get("details")
    return value if isinstance(value, dict) else {}


def _stored_rows(plan: str) -> list[dict]:
    with sqlite3.connect(_store_path()) as connection:
        connection.row_factory = sqlite3.Row
        return [
            dict(row)
            for row in connection.execute(
                "SELECT id, sequence_no, title, place_id, start_at, end_at, updated_at, created_at"
                " FROM activities WHERE plan_version_id = ? ORDER BY sequence_no",
                (plan,),
            )
        ]


def _utc(raw: str) -> str:
    return datetime.fromisoformat(raw).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# -------------------------------------------------------------------- clause 1: one door, one source


def test_a_multi_day_trip_exports_one_vevent_per_clocked_activity_in_the_plants_own_order() -> None:
    """The positive case the order asked for: activities on three separate days, one event each."""

    stage = _trip()
    response = _ics(stage["journey"])
    assert response.status_code == 200, response.text
    body = _body(response)

    events = _events(body)
    assert [_decode_text(event["SUMMARY"]) for event in events] == [
        NASTY_TITLE, "日光岩,第二个入口", "夜航跨日",
    ], [_decode_text(event["SUMMARY"]) for event in events]

    first = events[0]
    assert first["DTSTART"] == "20310501T010000Z", first
    assert first["DTEND"] == "20310501T030000Z", first
    assert first["DTSTAMP"] == _utc(MOMENT), first
    assert _decode_text(first["UID"]) == f"{stage['clocked'][0]}@journeys.citynexus", first["UID"]

    lines = _content_lines(body)
    assert ("VERSION", "2.0") in lines, lines[:3]
    assert ("CALSCALE", "GREGORIAN") in lines, lines[:3]
    assert ("METHOD", "PUBLISH") in lines, lines[:3]
    assert ("X-WR-CALNAME", "沿海一周") in lines, lines[:3]
    assert [name for name, _ in lines[:1]] == ["BEGIN"], lines[:1]
    days = sorted(event["DTSTART"][:8] for event in events)
    assert days == ["20310501", "20310503", "20310508"], days

    # Printed in `sequence_no` order, which here is deliberately NOT chronological: row 2 is the
    # 08th and row 3 the 03rd, so an `ORDER BY start_at` would reorder them and the string compare
    # across mixed offsets would be a fake chronology.  Calendar clients sort by DTSTART themselves.
    assert [event["DTSTART"] for event in events] == [
        "20310501T010000Z", "20310508T013000Z", "20310503T220000Z",
    ], [event["DTSTART"] for event in events]

    assert _count(response, "Events") == 3, dict(response.headers)
    assert _count(response, "Skipped-No-Clock") == 2, dict(response.headers)
    assert _count(response, "Skipped-No-Stamps") == 1, dict(response.headers)
    stored = _stored_rows(stage["plan"])
    assert _count(response, "Activities") == len(stored), (dict(response.headers), len(stored))
    assert (
        _count(response, "Activities")
        == _count(response, "Events")
        + _count(response, "Skipped-No-Clock")
        + _count(response, "Skipped-No-Stamps")
    ), dict(response.headers)

    # A row with no place emits no LOCATION rather than a name this server made up.
    assert "LOCATION" in events[0], sorted(events[0])
    assert "LOCATION" not in events[1], sorted(events[1])
    assert _decode_text(events[0]["LOCATION"]) == NASTY_PLACE, events[0]["LOCATION"]
    # `cost_minor` stays in the column's own unit: formatting 3500 as money would be a claim about
    # currency rounding that no column here makes.
    assert _decode_text(events[0]["DESCRIPTION"]) == (
        "sequence=1\ntype=visit\nstatus=PLANNED\ncost_minor=3500 CNY"
    ), events[0]["DESCRIPTION"]
    print(
        f"[ord0496][positive] store={_store_path()} journey={stage['journey']} "
        f"plan={stage['plan']} events={_count(response, 'Events')} "
        f"skipped_no_clock={_count(response, 'Skipped-No-Clock')} "
        f"skipped_no_stamp={_count(response, 'Skipped-No-Stamps')} stored_rows={len(stored)} "
        f"days={days} body_bytes={len(response.content)}"
    )


# --------------------------------------------------------------------------------- clause 2: escaping


def test_comma_semicolon_backslash_and_newline_are_escaped_and_survive_the_round_trip() -> None:
    """§3.3.11: four characters move, a colon does not, and every value comes back identical."""

    stage = _trip()
    response = _ics(stage["journey"])
    assert response.status_code == 200, response.text
    events = _events(_body(response))

    summary = events[0]["SUMMARY"]
    assert _decode_text(summary) == NASTY_TITLE, summary
    assert _bare_special_positions(summary) == [], summary
    assert "\\," in summary and "\\;" in summary and "\\\\" in summary and "\\n" in summary, summary

    location = events[0]["LOCATION"]
    assert _decode_text(location) == NASTY_PLACE, location
    assert _bare_special_positions(location) == [], location

    description = _decode_text(events[0]["DESCRIPTION"])
    assert description.splitlines() == [
        "sequence=1", "type=visit", "status=PLANNED", "cost_minor=3500 CNY",
    ], description.splitlines()

    # A colon is only special in a parameter value and this exporter writes none, so an eager `\:`
    # would itself be the interop bug.  The title's colon has to arrive verbatim.
    for printed in (summary, location):
        assert "\\:" not in printed, printed
    assert ":" in summary, summary

    # Every value the object prints must be free of bare specials, not only the ones I picked.
    for event in events:
        for name in ("UID", "SUMMARY", "LOCATION", "DESCRIPTION"):
            if name in event:
                assert _bare_special_positions(event[name]) == [], (name, event[name])
    print(
        f"[ord0496][escape] summary_octets={len(summary.encode('utf-8'))} "
        f"escaped_commas={summary.count(chr(92) + chr(44))} "
        f"escaped_semicolons={summary.count(chr(92) + chr(59))} "
        f"escaped_newlines={summary.count(chr(92) + 'n')} "
        f"bare_special_offsets=0 round_trip_equal=True"
    )


# --------------------------------------------------------------------------------- clause 3: folding


def test_no_physical_line_exceeds_seventy_five_octets_and_unfolding_restores_every_value() -> None:
    """§3.1's 75-octet ceiling, measured in bytes, on a title that costs 3 octets a character.

    Three ways to get this wrong and the arm fails for each: counting characters instead of octets;
    letting a continuation line carry 75 octets of content on top of its leading space; and cutting
    between the octets of one multi-byte character, which hands a receiver bytes that decode to
    nothing.
    """

    stage = _trip()
    with SessionLocal() as session:
        session.get(Place, stage["place"]).name = LONG_TITLE
        session.get(Activity, stage["clocked"][1]).title = LONG_TITLE
        session.commit()

    response = _ics(stage["journey"])
    assert response.status_code == 200, response.text
    body = _body(response)
    physical = _physical_lines(body)

    octets = [len(line.encode("utf-8")) for line in physical]
    assert max(octets) <= 75, (max(octets), physical[7:11])
    for line in physical:  # no fold may cut a character in half
        line.encode("utf-8").decode("utf-8")
    continuations = [line for line in physical if line[:1] in (" ", "\t")]
    assert continuations, "a 3-octet title should have needed at least one fold"
    assert all(len(line.encode("utf-8")) <= 75 for line in continuations), continuations
    # None of the values in *this* body carries a plain space, so no continuation here may carry a
    # migrated one; the case where a fold does land on a space is the next arm's business, and it
    # asserts the doubled space must appear there.
    assert all(line[1:2] not in (" ", "\t") for line in continuations), [
        line[:4] for line in continuations
    ]

    events = _events(body)
    assert _decode_text(events[1]["SUMMARY"]) == LONG_TITLE, events[1]["SUMMARY"]
    assert _decode_text(events[0]["LOCATION"]) == LONG_TITLE, events[0]["LOCATION"]
    # The property name is on the first physical line, never carried onto a continuation.
    starts = [line for line in physical if not line.startswith((" ", "\t"))]
    assert any(line.startswith("SUMMARY:") for line in starts), starts[:4]
    assert any(line.startswith("DESCRIPTION:") for line in starts), starts[:4]
    print(
        f"[ord0496][fold] longest_line_octets={max(octets)} physical_lines={len(physical)} "
        f"continuation_lines={len(continuations)} title_characters={len(LONG_TITLE)} "
        f"title_octets={len(LONG_TITLE.encode('utf-8'))}"
    )


def test_a_fold_never_eats_the_space_it_breaks_at_and_a_value_keeps_its_edges() -> None:
    """§3.1's unfolding deletes CRLF *and one following space*, so a line must not end at a space.

    `SPACE_EDGE_TITLE` is chosen so the 75-octet budget cuts right after one of its single spaces --
    the one position where a fold silently loses a character.  A value that begins or ends with a
    space cannot be written at all under §3.1, which is why the exporter trims and *reports* it
    instead of spending the character quietly.
    """

    stage = _trip()
    with SessionLocal() as session:
        session.get(Activity, stage["clocked"][1]).title = SPACE_EDGE_TITLE
        session.commit()

    response = _ics(stage["journey"])
    assert response.status_code == 200, response.text
    physical = _physical_lines(_body(response))
    doubled = [line for line in physical if line.startswith("  ")]
    assert doubled, (
        "no fold landed on a space, so this arm measured nothing -- the title has to force the "
        "75-octet budget to cut right after one"
    )
    assert all(not line.endswith((" ", "\t")) for line in physical), [
        line[-8:] for line in physical if line.endswith((" ", "\t"))
    ]

    events = _events(_body(response))
    wanted = f"{stage['clocked'][1]}@journeys.citynexus"
    printed = next(
        event["SUMMARY"] for event in events if _decode_text(event["UID"]) == wanted
    )
    assert _decode_text(printed) == SPACE_EDGE_TITLE.strip(), repr(printed)
    assert _bare_special_positions(printed) == [], printed
    # The interior single spaces are the value's own and every one must still be there.
    assert printed.count(" ") == SPACE_EDGE_TITLE.strip().count(" "), printed
    assert _count(response, "Whitespace-Trimmed") >= 1, dict(response.headers)
    print(
        f"[ord0496][space] stored_characters={len(SPACE_EDGE_TITLE)} "
        f"printed_interior_spaces={printed.count(' ')} "
        f"trimmed_values={_count(response, 'Whitespace-Trimmed')} "
        f"physical_lines={len(physical)} folds_that_landed_on_a_space={len(doubled)}"
    )


# ------------------------------------------------------------------------ clause 4: skipped, not lost


def test_an_activity_without_a_usable_clock_is_skipped_and_counted_never_silently_lost() -> None:
    """The two ways "no clock" arrives land in one named bucket, and neither one is printed anyway.

    No `DTSTART` is invented for them and no line is emitted at all: the row's absence is visible as
    a number, which is the difference between "skipped" and "dropped".
    """

    stage = _trip()
    response = _ics(stage["journey"])
    assert response.status_code == 200, response.text
    body = _body(response)
    uids = [_decode_text(event["UID"]) for event in _events(body)]

    for identifier in stage["no_clock"]:
        assert f"{identifier}@journeys.citynexus" not in uids, identifier
        row = next(item for item in _stored_rows(stage["plan"]) if item["id"] == identifier)
        assert row["start_at"] in ("2031-05-05", "2031-05-06T09:00:00"), row
    assert _count(response, "Skipped-No-Clock") == len(stage["no_clock"])
    assert f"{stage['no_stamp']}@journeys.citynexus" not in uids
    assert _count(response, "Skipped-No-Stamps") == 1

    # Every printed instant is one a row carries, re-derived here from the store.
    printed = {
        (event["UID"], event["DTSTART"], event["DTEND"], event["DTSTAMP"])
        for event in _events(body)
    }
    derived = {
        (
            f"{row['id']}@journeys.citynexus", _utc(row["start_at"]), _utc(row["end_at"]),
            _utc(row["updated_at"]),
        )
        for row in _stored_rows(stage["plan"])
        if all(("+" in row[field] or "Z" in row[field]) for field in
               ("start_at", "end_at", "updated_at"))
    }
    assert derived, "the fixture stopped carrying a clockable row"
    assert printed == derived, sorted(printed ^ derived)
    census = Path(ROOT / "review/ord0496/store_shape_census_r1.py")
    assert census.is_file(), census
    print(
        f"[ord0496][skipped] skipped_no_clock={_count(response, 'Skipped-No-Clock')} "
        f"skipped_no_stamp={_count(response, 'Skipped-No-Stamps')} events_printed={len(printed)} "
        f"store_rows_with_a_clock={len(derived)} live_store_rows_without_a_clock=NOT_REACHABLE"
    )


def test_an_interval_crossing_the_printed_day_boundary_stays_one_event_and_is_counted() -> None:
    """Splitting it would need a start for the second half, and no column holds one.

    The row runs 22:00Z to 01:30 the next day, so the two dates the file prints differ; the object
    says so once, and the count says so out loud instead of leaving a reader to notice.
    """

    stage = _trip()
    response = _ics(stage["journey"])
    assert response.status_code == 200, response.text
    events = _events(_body(response))
    crossing = next(event for event in events if _decode_text(event["SUMMARY"]) == "夜航跨日")
    assert crossing["DTSTART"] == "20310503T220000Z", crossing
    assert crossing["DTEND"] == "20310504T013000Z", crossing
    assert crossing["DTSTART"][:8] != crossing["DTEND"][:8], crossing
    assert len(events) == 3, "the crossing interval was split into more than one VEVENT"
    assert _count(response, "Cross-Day") == 1, dict(response.headers)
    assert _count(response, "Events") == 3, dict(response.headers)
    print(
        f"[ord0496][cross-day] uid={_decode_text(crossing['UID'])} "
        f"dtstart={crossing['DTSTART']} dtend={crossing['DTEND']} "
        f"cross_day={_count(response, 'Cross-Day')} events={_count(response, 'Events')}"
    )


def test_only_the_active_plan_versions_rows_are_exported_and_a_superseded_plan_cannot_leak() -> None:
    """The pointer is the source: `journeys.active_plan_version_id`, and nothing else."""

    stage = _trip()
    response = _ics(stage["journey"])
    assert response.status_code == 200, response.text
    body = _body(response)
    assert "绝不该出现" not in _decode_text(body), "a SUPERSEDED plan leaked into the export"
    with sqlite3.connect(_store_path()) as connection:
        rows_by_plan = dict(
            connection.execute(
                "SELECT plan_version_id, COUNT(*) FROM activities"
                " WHERE plan_version_id IN (?, ?) GROUP BY plan_version_id",
                (stage["plan"], stage["superseded"]),
            ).fetchall()
        )
    assert rows_by_plan[stage["superseded"]] == 1, rows_by_plan
    assert _count(response, "Activities") == rows_by_plan[stage["plan"]], (
        dict(response.headers), rows_by_plan,
    )
    print(
        f"[ord0496][pointer] active_plan_rows={rows_by_plan[stage['plan']]} "
        f"superseded_plan_rows={rows_by_plan[stage['superseded']]} "
        f"exported_events={_count(response, 'Events')}"
    )


# ------------------------------------------------------------------------------ clause 5: the bin


def test_a_trip_in_the_recycle_bin_is_refused_by_name_and_not_as_an_empty_calendar() -> None:
    """A binned trip must not export, and "nothing scheduled" would be a lie about the reason."""

    stage = _trip()
    deleted = client.delete(f"/api/v1/journeys/{stage['journey']}")
    assert deleted.status_code == 204, deleted.text

    response = _ics(stage["journey"])
    assert response.status_code == 409, response.text
    body = response.json()
    assert _reason(body) == "CALENDAR_JOURNEY_IN_RECYCLE_BIN", body
    assert _error(body)["code"] == "CONFLICT", body
    assert _details(body)["journey_id"] == stage["journey"], body
    assert _details(body)["deleted_at"], body
    assert not response.content.startswith(b"BEGIN:VCALENDAR"), response.content[:32]

    # 找回 puts the export back, because the refusal named a state and not the row.
    assert client.post(f"/api/v1/journeys/{stage['journey']}/undelete").status_code == 200
    restored = _ics(stage["journey"])
    assert restored.status_code == 200, restored.text
    print(
        f"[ord0496][bin] reason_code={_reason(body)} status={response.status_code} "
        f"error_code={_error(body)['code']} after_undelete={restored.status_code} "
        f"bin_column_read=journeys.deleted_at"
    )


# ------------------------------------------------------------------ clause 6: unknown trip, one answer


def test_an_unknown_trip_gets_the_read_authoritys_own_404_plus_the_name() -> None:
    """No second 404 shape: status, code, key and sentence are `get_journey`'s."""

    missing = str(uuid4())
    reference = client.get(f"/api/v1/journeys/{missing}")
    # FUSION PORT: the source sent this anonymously, and its door answered.  Here the credential is
    # checked before the trip is looked up, so an anonymous probe would measure the 401 instead of
    # the 404 this arm is about.  A valid caller who simply does not own the id is the same question
    # the source asked.
    response = _ics(missing, headers=_auth(_probe_traveller()))
    assert reference.status_code == 404, reference.text
    assert response.status_code == 404, response.text
    body = response.json()
    assert _reason(body) == "JOURNEY_NOT_FOUND", body
    assert _error(body)["code"] == _error(reference.json())["code"], (body, reference.json())
    assert _error(body)["message_key"] == _error(reference.json())["message_key"]
    assert _error(body)["message"] == _error(reference.json())["message"]
    assert _details(body)["journey_id"] == missing, body

    # A malformed path id is the validation door's business and this door does not reinterpret it.
    malformed = client.get(f"/api/v1/journeys/not-a-uuid/calendar.ics")
    assert malformed.status_code == 422, malformed.text
    print(
        f"[ord0496][not-found] status={response.status_code} reason_code={_reason(body)} "
        f"error_code={_error(body)['code']} same_answer_as_read_door=True "
        f"malformed_id_status={malformed.status_code}"
    )


# ------------------------------------------------------------------- clause 8: the source is unreadable


def test_a_pointer_that_does_not_resolve_is_refused_by_name_with_which_condition_it_is() -> None:
    """Three states, one code, and a `reason` that tells them apart.

    "This trip has no plan" is honest; "here is your empty calendar" is not.  The dangling and the
    foreign pointers are written with `PRAGMA foreign_keys = OFF`, which is how the schema-catchup
    migrations in `app/db/session.py` themselves reach those states -- the real FK is
    `ON DELETE SET NULL`, so an ordinary delete could never leave a dangling pointer behind.
    """

    declared = _journey()
    response = _ics(declared)
    assert response.status_code == 409, response.text
    assert _reason(response.json()) == "CALENDAR_SOURCE_UNREADABLE", response.text
    assert _details(response.json())["reason"] == "ACTIVE_PLAN_NOT_DECLARED", response.json()

    owner = _trip()
    foreign = _journey()
    _raw_update(
        "UPDATE journeys SET active_plan_version_id = ? WHERE id = ?", (owner["plan"], foreign)
    )
    response = _ics(foreign)
    assert response.status_code == 409, response.text
    assert _details(response.json())["reason"] == "ACTIVE_PLAN_BELONGS_TO_ANOTHER_JOURNEY", (
        response.json()
    )
    assert _details(response.json())["plan_journey_id"] == owner["journey"], response.json()

    dangling = _journey()
    _raw_update(
        "UPDATE journeys SET active_plan_version_id = ? WHERE id = ?", (str(uuid4()), dangling)
    )
    response = _ics(dangling)
    assert response.status_code == 409, response.text
    assert _details(response.json())["reason"] == "ACTIVE_PLAN_ROW_ABSENT", response.json()

    # A plan that holds no activity at all is not an unreadable source: it answers, empty and named.
    emptied = _trip()
    _raw_update("DELETE FROM activities WHERE plan_version_id = ?", (emptied["plan"],))
    response = _ics(emptied["journey"])
    assert response.status_code == 200, response.text
    assert _events(_body(response)) == []
    assert _count(response, "Activities") == 0, dict(response.headers)
    assert _count(response, "Events") == 0, dict(response.headers)
    print(
        f"[ord0496][unreadable] not_declared={409} belongs_to_another={409} row_absent={409} "
        f"empty_plan_status={response.status_code} empty_plan_events=0"
    )


# ------------------------------------------------------------------- clause 7: media type and naming


def test_the_media_type_the_file_name_and_a_title_that_could_restructure_the_header() -> None:
    """`text/calendar`, an ASCII fallback, and the real title in `filename*`.

    The fallback stays generic on purpose: 沿海 has no honest ASCII form, and transliterating one
    would be this server naming a trip the traveller never named.  The dangerous shape is a title
    carrying a double quote, a backslash or a slash -- written into `filename=` unescaped, any of
    them ends the parameter early and lets the rest of the title dictate header structure.
    """

    stage = _trip()
    nasty = '厦门"站/点\\.. 与 , 号'
    with SessionLocal() as session:
        session.get(Journey, stage["journey"]).title = nasty
        session.commit()

    response = _ics(stage["journey"])
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "text/calendar; charset=utf-8", dict(response.headers)
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment;"), disposition
    assert 'filename="calendar.ics"' in disposition, disposition
    assert "\r" not in disposition and "\n" not in disposition, repr(disposition)
    star = disposition.split("filename*=", 1)[1]
    assert '"' not in star and "\\" not in star, star
    assert star.startswith("UTF-8''"), star

    recovered = unquote(star.removeprefix("UTF-8''"), encoding="utf-8", errors="strict")
    assert recovered.endswith(".ics"), recovered
    # The CJK survives; the structural characters are dropped, and the journey id -- hyphens and all,
    # since they are RFC 5987 safe -- keeps the file addressable even for two trips sharing a title.
    assert "厦门站点" in recovered, recovered
    assert stage["journey"] in recovered, recovered
    assert not recovered.startswith("."), recovered
    for forbidden in ('"', "\\", "/", ";", ","):
        assert forbidden not in recovered, (forbidden, recovered)

    body = _body(response)
    assert body.startswith("BEGIN:VCALENDAR\r\n"), body[:32]
    assert body.endswith("END:VCALENDAR\r\n"), body[-32:]
    print(
        f"[ord0496][naming] content_type={response.headers['content-type']} "
        f"disposition_octets={len(disposition.encode('utf-8'))} fallback=calendar.ics "
        f"filename_star_prefix=UTF-8'' title_characters={len(nasty)} "
        f"body_bytes={len(response.content)}"
    )


# --------------------------------------------------------------------------- clause 9: no local clock


def test_two_exports_are_the_same_bytes_and_moving_the_rows_moment_moves_the_stamp() -> None:
    """`DTSTAMP` is the row's own moment, so the object is a function of the store alone.

    sameness alone cannot tell "from the row" apart from "from the request, and the request happened
    to be twice in the same second" -- so the arm also moves the column and shows the printed stamp
    follow it.  This is what makes an export checkable at all: if the generating instant were the
    request's, two reads would differ and no byte comparison could ever be evidence.
    """

    stage = _trip()
    first = _ics(stage["journey"])
    second = _ics(stage["journey"])
    assert first.status_code == 200 and second.status_code == 200
    assert first.content == second.content, "the export is not a function of the rows"
    assert {_event["DTSTAMP"] for _event in _events(_body(first))} == {_utc(MOMENT)}

    with SessionLocal() as session:
        session.get(Activity, stage["clocked"][0]).updated_at = MOVED_MOMENT
        session.commit()
    moved = _ics(stage["journey"])
    assert moved.content != first.content, "the rows moved and the object did not"
    stamps = {event["UID"]: event["DTSTAMP"] for event in _events(_body(moved))}
    assert stamps[_decode_text(f"{stage['clocked'][0]}@journeys.citynexus")] == _utc(MOVED_MOMENT), (
        stamps
    )
    assert sum(value == _utc(MOMENT) for value in stamps.values()) == 2, stamps
    print(
        f"[ord0496][determinism] bytes_first={len(first.content)} "
        f"bytes_second={len(second.content)} identical=True "
        f"stamps_after_move={sorted(set(stamps.values()))}"
    )


# ------------------------------------------------------------------ clause 10: line terminators only


def test_every_line_ends_with_crlf_and_the_object_carries_no_bare_line_feed() -> None:
    """§3.1: CRLF is the only line terminator.  A bare LF ships silently and breaks strict readers.

    Counting is the whole judgement: CR must equal LF must equal the physical line count, and the
    body must contain no LF outside a pair.
    """

    stage = _trip()
    response = _ics(stage["journey"])
    raw = response.content
    body = _body(response)
    assert raw.count(b"\r\n") == len(_physical_lines(body)), "a fold-line mismatch"
    assert raw.count(b"\n") == raw.count(b"\r\n"), (raw.count(b"\n"), raw.count(b"\r\n"))
    assert raw.count(b"\r") == raw.count(b"\n"), (raw.count(b"\r"), raw.count(b"\n"))
    assert b"\n\n" not in raw and b"\r\r" not in raw, "an empty line is not a contentline"
    assert raw.decode("utf-8").encode("utf-8") == raw
    print(
        f"[ord0496][crlf] crlf_pairs={raw.count(bytes([13, 10]))} "
        f"lone_lf={raw.count(bytes([10])) - raw.count(bytes([13, 10]))} "
        f"lone_cr={raw.count(bytes([13])) - raw.count(bytes([13, 10]))} "
        f"physical_lines={len(_physical_lines(body))}"
    )


# ------------------------------------------- FUSION clauses: the credential, and a metered debt


DEFERRED_TO_THE_CONTRACT_LEG = {
    "test_the_contract_declares_the_door_its_refusals_and_its_counts": (
        "this branch's contracts/openapi.yaml does not declare the calendar.ics operation"
    ),
    "test_the_generated_client_carries_the_new_operation_and_drops_none_of_the_old_ones": (
        "frontend/src/generated/api.ts is generated from that contract, so it cannot carry an "
        "operation the contract does not declare"
    ),
}


def test_the_two_source_arms_deferred_to_the_contract_leg_are_still_deferred_and_measured() -> None:
    """A deferred arm is a debt with a meter on it, not a deleted test.

    Both source arms read `contracts/openapi.yaml` and `frontend/src/generated/api.ts`.  This branch's
    contract does not carry the operation, so those two arms would fail for a reason that has nothing
    to do with the exporter -- and marking them `xfail` would hide the day the contract leg lands.

    This arm measures the deferral's precondition instead: the door is registered at runtime, the six
    count headers come back from a real export, and the contract still does NOT declare the operation.
    That last assertion is the tripwire -- when the contract leg ports it, this arm goes red and names
    the two arms that have to come back.
    """

    stage = _trip()
    response = _ics(stage["journey"])
    assert response.status_code == 200, response.text
    runtime = {(route.path, method) for route in app.routes
               for method in (getattr(route, "methods", None) or set())}
    assert (f"/api/v1{DOOR_PATH}", "GET") in runtime, sorted(path for path, _ in runtime)[:4]

    counts = {
        name: _count(response, name)
        for name in (
            "Events", "Skipped-No-Clock", "Skipped-No-Stamps", "Cross-Day", "Activities",
            "Whitespace-Trimmed",
        )
    }
    assert counts["Activities"] == counts["Events"] + counts["Skipped-No-Clock"] + (
        counts["Skipped-No-Stamps"]
    ), counts

    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    declared = DOOR_PATH in (spec.get("paths") or {})
    assert not declared, (
        "the contract leg has landed -- bring back the arms named in DEFERRED_TO_THE_CONTRACT_LEG "
        "instead of this tripwire"
    )
    print(
        f"[ord0496][deferred] arms_deferred={len(DEFERRED_TO_THE_CONTRACT_LEG)} "
        f"count_headers_at_runtime={len(counts)} contract_declares_door={declared} "
        f"contract_lines={len(CONTRACT.read_text(encoding='utf-8').splitlines())} "
        f"generated_client_bytes={GENERATED.stat().st_size}"
    )


def test_an_anonymous_export_is_refused_and_hands_out_no_calendar_bytes() -> None:
    """The state the source door could not express: nobody asked, and nothing may be answered.

    Three things are asserted together because any one of them alone is satisfiable by accident: the
    status, the envelope this tree already uses for a missing credential (401 maps to
    `REQUEST_ERROR`/`error.request_error` -- `resolve_traveler_principal` raises a bare
    `HTTPException(401, ...)`, and `test_qoder_ord0476_checkins_fusion.py::_assert_unauthorized`
    records that mapping rather than inventing a friendlier one), and that the refusal body carries
    neither the calendar's opening nor any of the trip's own words.
    """

    stage = _trip()
    response = _ics(stage["journey"], headers={})
    assert response.status_code == 401, response.text
    body = response.json()
    assert _error(body)["code"] == "REQUEST_ERROR", body
    assert _error(body)["message_key"] == "error.request_error", body
    dumped = response.content.decode("utf-8")
    assert "BEGIN:VCALENDAR" not in dumped, dumped[:64]
    for word in ("沿海一周", "鼓浪屿", "DTSTART"):
        assert word not in dumped, word
    # and the same request with the owner's credential is a 200, so the refusal above is the
    # credential's absence and not a broken door.
    assert _ics(stage["journey"]).status_code == 200

    print(
        f"[ord0496][fusion-anonymous] status={response.status_code} "
        f"error_code={_error(body)['code']} message_key={_error(body)['message_key']} "
        f"calendar_bytes=0 owner_export_status=200"
    )


def test_a_valid_credential_for_another_traveller_is_answered_exactly_like_a_missing_trip() -> None:
    """"Not there" and "not yours" are ONE response, built by one code path.

    This is the claim the seam rests on, so it is measured rather than described: a stranger holding a
    real, unexpired token for a trip they do not own gets the same status, the same `reason_code`, the
    same sentence and the same details as a caller asking for an id this server has never heard of.
    A distinct 403 would turn the export door into an oracle for which journey ids exist -- the
    reasoning `_checkin_journey_read` records for the footprint doors, carried here.
    """

    stage = _trip()
    stranger = _probe_traveller()
    foreign = _ics(stage["journey"], headers=_auth(stranger))
    missing = _ics(str(uuid4()), headers=_auth(stranger))

    assert foreign.status_code == 404 == missing.status_code, (foreign.text, missing.text)
    assert _reason(foreign.json()) == "JOURNEY_NOT_FOUND", foreign.text
    assert _reason(foreign.json()) == _reason(missing.json()), (foreign.text, missing.text)
    # THE SENTENCES ARE THE SAME SHAPE, AND THIS IS WHERE THE HONESTY SITS.  `require`'s wording
    # echoes the id the caller typed -- `Journey <uuid> was not found` -- which is ORD-0500's
    # complaint about the read authority, and this port does not fix a neighbour's prose.  So the two
    # answers are compared with that id cut out: what a stranger can learn from either response is
    # only the id they themselves sent.
    foreign_message = _error(foreign.json())["message"].replace(stage["journey"], "<id>")
    missing_message = _error(missing.json())["message"].replace(
        _details(missing.json())["journey_id"], "<id>"
    )
    assert foreign_message == missing_message == "Journey <id> was not found", (
        foreign_message, missing_message
    )
    assert _details(foreign.json()) == {"journey_id": stage["journey"]}, foreign.text
    assert "BEGIN:VCALENDAR" not in foreign.content.decode("utf-8"), foreign.content[:64]
    # the owner is unaffected: the refusal is about the caller, not about the trip being exportable
    owned = _ics(stage["journey"])
    assert owned.status_code == 200, owned.text
    assert owned.content.startswith(b"BEGIN:VCALENDAR"), owned.content[:32]

    print(
        f"[ord0496][fusion-not-yours] status={foreign.status_code} reason_code={_reason(foreign.json())} "
        f"same_message_as_unknown_id=True calendar_bytes_for_stranger=0 owner_status={owned.status_code} "
        f"owner_events={owned.headers['X-CityNexus-Ics-Events']}"
    )


def test_a_request_that_names_another_traveller_in_the_query_is_refused_by_name() -> None:
    """No spelling of "and also for this other person" is accepted, and none is silently ignored.

    The door never had a `traveler_id` parameter, so this arm is not testing that a removed input
    still works -- it is testing that the server says NO out loud.  Ignoring the parameter would be
    the worst answer, because the caller would believe it had been honoured.  The credential is still
    refused first, which is why this request carries a valid token.
    """

    stage = _trip()
    response = client.get(
        f"/api/v1/journeys/{stage['journey']}/calendar.ics",
        headers=_auth(stage["traveler"]),
        params={"traveler_id": _probe_traveller()},
    )
    assert response.status_code == 422, response.text
    body = response.json()
    assert _reason(body) == "CALENDAR_TRAVELER_SCOPE_PARAM_NOT_ACCEPTED", body
    assert _details(body) == {"field": "traveler_id"}, body
    assert "BEGIN:VCALENDAR" not in response.content.decode("utf-8"), response.content[:64]
    print(
        f"[ord0496][fusion-scope-param] status={response.status_code} "
        f"reason_code={_reason(body)} details_field={_details(body)['field']} "
        f"ignored_silently=False"
    )

