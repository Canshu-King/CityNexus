"""ORD-0476 slice 1 「打卡」 the trip footprint -- ported to the fusion branch, and re-armed.

Source: origin/mirror/integration-frontend-apple-pass1 (== `eeb8b8d2fd`),
`backend/tests/test_qoder_ord0476_checkins.py` (532 lines, ten arms).  This is that module imported
into `fusion/qoder-import-20261014`, not a rewrite: the store-shape arm, the target-words arm, the
two duplicate arms, the exactly-one-target arm, the check-ordering arm, the foreign-versus-absent
arm, the recycle-bin arm, the cascade arm and the `reset_all` ordering arm are carried with their
assertions intact.

WHAT MOVED, and it moved because the door moved.  The source's two doors resolved the trip with
`session.get(Journey, str(journey_id))` and nothing else -- no credential, no traveller field, no
membership lookup.  Its `list_journey_checkins` docstring describes an ordering and a batching and
names no reader at all, and its nearest sibling states the posture out loud ("the anonymous read
above is deliberately untouched", `backend/app/main.py` at the ORD-0434 share-grant header).  So in
that tree `GET /api/v1/journeys/{id}/checkins` returned 200 and a stranger's whole footprint to any
caller, and `POST` stamped onto anybody's trip.  `fusion/UNIFIED_FUSION_CHARTER.md` treats an
unsigned cross-member read as a stop condition, so the doors were rebuilt behind
`app/traveler_principal.py::resolve_traveler_principal` before their behaviour was ported, and the
arms changed with it:

  * arms 2-9 keep every assertion and gain a bearer token, because the door now needs one;
  * arm 8's bin walk is unchanged -- `DELETE /api/v1/journeys/{id}` and `/undelete` are this
    product's own doors and still are not principal-bound on this branch (a pre-existing gap outside
    this slice, said here rather than left to be discovered);
  * arm 2's forged-instant half changes from "201, and the stored moment is not the one you sent" to
    "422, refused out loud" -- `JourneyCheckinCreate` is `extra="forbid"` here.  The source said the
    server owns the instant in its docstring and then accepted a body that sent one and dropped it;
    `backend/tests/test_qoder_ord0476_checkins.py` proves that by asserting 201.  This is an upgrade
    of the contract, not a weakened test: the assertion is stronger, and no stored row is involved;
  * arm 11's contract reading changes because the contract changed: the read door now documents
    401/404/422 beside its promised 200/409, so the source's `named_expansion_get` whitelist --
    empty as it shipped -- has to name them.  Its `frontend/src/generated/api.ts` half is NOT ported
    (see the gap note on arm 11);
  * arms 12-18 are new, and the source could not have written any of them against its own door:
    12 no credential reads nothing and stamps nothing, 13 a stranger cannot read, stamp, or tell
    absent from not-mine, 14 a `traveler_id` query parameter is refused by name on both doors,
    15 a scoped read returns only the subject's own rows (measured against the store), 16 a
    stranger's activity id does not leak its journey through a refusal body, 17 the audit row names
    the principal the server verified, 18 the served document carries what the contract declares.

Hermeticity, because this file is run three times against one store.  `_stage()` mints a NEW traveller
and NEW trips on every call (`str(uuid4())`), which is what the source already did; `_RUN_TAG` covers
the ids that are *not* minted -- the activity rows, whose ids the source spelled out so a
`CHECKIN_ACTIVITY_NOT_IN_JOURNEY` could be told from `CHECKIN_ACTIVITY_UNKNOWN`.  Without the tag, a
second run's `ord0476-activity-words-own` would still belong to the first run's plan version and every
activity arm would answer the foreign refusal: a non-hermetic test, not a product defect.  Nothing is
dropped, reordered, loosened or cleaned up to get green; a fresh store and a twice-reused one must
both pass, and the place rows are get-or-created exactly as the source's `_place` did.

`contracts/openapi.yaml` is read rather than restated, and the run uses the store
`backend/tests/conftest.py` declares for this process.  Nothing here calls `POST /api/v1/demo/reset`.
"""

from __future__ import annotations

import ast
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

import app.main as main_module
from app.core.config import settings
from app.db.models import Activity, Journey, JourneyCheckin, Place, PlanVersion, Traveler
from app.db.session import SessionLocal
from app.traveler_principal import issue_traveler_token
from conftest import RESOLVED_TEST_DATABASE

client = TestClient(main_module.app, raise_server_exceptions=False)
ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "openapi.yaml"
SERVICES = ROOT / "backend/app/services.py"
MOMENT = datetime.now(timezone.utc).isoformat()

# A signing key for this process only, in the same shape every other fusion principal module uses
# (`test_qoder_ord0444_collections_fusion.py`, `test_r28_authenticated_member_principal.py`): a
# literal that is not a credential anywhere, installed on `settings` for the module and restored.
_TEST_SECRET = "ord0476-checkins-fusion-test-secret-0123456789abcdef"

# See the hermeticity note in the module docstring: this tags the ids the fixture spells out rather
# than mints, so each run of this file gets a subject no earlier run can have written to.
_RUN_TAG = uuid.uuid4().hex[:8]


@pytest.fixture(scope="module", autouse=True)
def _traveler_secret_is_installed():
    previous = settings.traveler_auth_secret
    object.__setattr__(settings, "traveler_auth_secret", _TEST_SECRET)
    try:
        yield
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous)


def _store_path() -> Path:
    return Path(RESOLVED_TEST_DATABASE.replace("sqlite:///", "", 1)).expanduser().resolve()


def _reason(body: object) -> str | None:
    error = (body or {}).get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and isinstance(error.get("reason_code"), str):
        return error["reason_code"]
    if isinstance(body, dict) and isinstance(body.get("reason_code"), str):
        return error["reason_code"]
    return None


def _code(body: object) -> str | None:
    error = (body or {}).get("error") if isinstance(body, dict) else None
    return error.get("code") if isinstance(error, dict) else None


def _message_key(body: object) -> str | None:
    error = (body or {}).get("error") if isinstance(body, dict) else None
    return error.get("message_key") if isinstance(error, dict) else None


def _details(body: object) -> dict:
    error = (body or {}).get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and isinstance(error.get("details"), dict):
        return error["details"]
    if isinstance(body, dict) and isinstance(body.get("details"), dict):
        return body["details"]
    return {}


def _assert_unauthorized(response) -> None:
    """401, in the envelope this tree already uses for it -- asserted, not assumed.

    `app/main.py`'s HTTPException handler maps a status to a `code` through
    {404: NOT_FOUND, 409: CONFLICT, 422: VALIDATION_ERROR} and falls through to REQUEST_ERROR for
    everything else, and `HTTP_MESSAGE_KEYS` carries no 401 entry either.  So a bare
    `HTTPException(401, ...)` from `resolve_traveler_principal` -- the shape every authenticated
    fusion door raises, and the one this port reuses rather than inventing -- answers
    `code = REQUEST_ERROR`, `message_key = error.request_error`.  The source's own test could not
    assert any of this: against its door the same request was a 200.
    """

    assert response.status_code == 401, response.text
    body = response.json()
    assert _code(body) == "REQUEST_ERROR", response.text
    assert _message_key(body) == "error.request_error", response.text
    # The refusal path leaks no footprint payload, under any spelling.
    dumped = json.dumps(body, ensure_ascii=False)
    assert "target_key" not in dumped, response.text
    assert "stamped_at" not in dumped, response.text


def _place(label: str) -> str:
    identifier = f"ord0476-{label}"
    with SessionLocal() as session:
        if session.get(Place, identifier) is None:
            session.add(
                Place(
                    id=identifier,
                    provider_key="ord0476-probe",
                    external_id=identifier,
                    city_code="CN-XIAMEN",
                    name=f"鼓浪屿轮渡码头 {label}",
                    category="ferry",
                    latitude=24.45,
                    longitude=118.07,
                    opening_hours_json=json.dumps({"open": "07:00", "close": "19:00"}),
                    tags_json=json.dumps(["ord0476"]),
                    metadata_json=json.dumps({"cost_minor": 0, "duration_min": 30}),
                    updated_at=MOMENT,
                )
            )
            session.commit()
    return identifier


def _traveller(name: str) -> str:
    """A real `travelers` row, minted for this call.

    UUID-shaped, and that is not a style choice: `journey_schema` types `traveler_id` as a UUID, so
    the recycle-bin walk in arm 8 goes through `journey_schema` on its way to writing `deleted_at`
    and refuses a fixture whose owner id is not parseable.  The source's `_stage` mints `uuid4()` for
    the same reason, whether or not it said so.
    """

    identifier = str(uuid.uuid4())
    with SessionLocal() as session:
        session.add(
            Traveler(
                id=identifier, display_name=name, email=None,
                locale="zh-CN", timezone="Asia/Shanghai", created_at=MOMENT, updated_at=MOMENT,
            )
        )
        session.commit()
    return identifier


def _plan_and_activity(session, journey, place_id, activity_id, role, tag):
    plan = PlanVersion(
        id=str(uuid.uuid4()), journey_id=journey.id, version_no=1, planning_mode="balanced",
        status="ACTIVE", source="INITIAL", total_cost_minor=40000, currency="CNY",
        estimated_duration_min=600, created_at=MOMENT,
    )
    session.add(plan)
    session.flush()
    activity = Activity(
        id=activity_id, plan_version_id=plan.id, sequence_no=1,
        activity_type="visit", title=f"stop-{role}", place_id=place_id,
        city_service_id=None, start_at="2031-05-01T01:00:00+00:00",
        end_at="2031-05-01T02:00:00+00:00", travel_from_prev_min=10,
        estimated_cost_minor=0, currency="CNY", status="PLANNED", locked=False,
        metadata_json="{}", created_at=MOMENT, updated_at=MOMENT,
    )
    session.add(activity)
    journey.active_plan_version_id = plan.id
    return {"journey": journey.id, "plan": plan.id, "activity": activity.id}


def _stage(tag: str = "a", traveller_name: str = "ORD-0476 探针") -> dict:
    """One traveller, two trips, one plan version each, one activity on each, one shared place.

    Built through the product's own models because this order is about the stamp, not about how a
    plan got its rows.  Two journeys are not decoration: `CHECKIN_ACTIVITY_NOT_IN_JOURNEY` cannot be
    told apart from `CHECKIN_ACTIVITY_UNKNOWN` without an activity that really belongs elsewhere.

    FUSION ADDITION to the source helper: the traveller is minted per call, so every arm runs against
    a subject that cannot have been written to by an earlier arm or an earlier run, and the scope a
    door answers for is knowable before the request is made.  Nothing in the source's shape is lost:
    same columns, same two journeys, same shared place.
    """

    # The place row goes in on its own connection BEFORE this session opens one of its own.  The
    # first cut of this helper called `_place()` inside the `with`, so the outer session was already
    # holding a write transaction and the inner connection waited on it until SQLite answered
    # `database is locked` -- a fixture deadlock, not a product one.
    place_id = _place(f"{tag}-place")
    identifier = _traveller(f"{traveller_name} {tag}")
    with SessionLocal() as session:
        made = {"traveler": identifier, "place": place_id}
        for role in ("own", "other"):
            journey = Journey(
                id=str(uuid.uuid4()), traveler_id=identifier, title=f"沿海一周 {role} {tag}",
                city_code="CN-XIAMEN", timezone="Asia/Shanghai",
                start_at="2031-05-01T00:00:00+00:00", end_at="2031-05-03T00:00:00+00:00",
                budget_amount_minor=120000, budget_currency="CNY", status="PLANNED",
                created_at=MOMENT, updated_at=MOMENT,
            )
            session.add(journey)
            session.flush()
            made[role] = _plan_and_activity(
                session, journey, place_id,
                # `_RUN_TAG` is what makes this id new on the second and third run of this file;
                # see the module docstring.
                f"ord0476-activity-{tag}-{role}-{_RUN_TAG}",
                role, tag,
            )
            session.commit()
    return made


def _auth(traveller_id: str | None) -> dict[str, str]:
    """The credential for a traveller, or no credential at all for `None`.

    Minted by the product's own server-side signer (`issue_traveler_token`), which is documented as
    the helper a trusted process uses; there is no endpoint on this server that hands out tokens for
    an id someone names, and that asymmetry is the point of the whole retrofit.
    """

    if traveller_id is None:
        return {}
    return {"Authorization": f"Bearer {issue_traveler_token(traveller_id)}"}


def _stamp(journey: str, body: dict, traveller: str | None = None):
    return client.post(
        f"/api/v1/journeys/{journey}/checkins", json=body, headers=_auth(traveller)
    )


def _list(journey: str, traveller: str | None = None):
    return client.get(f"/api/v1/journeys/{journey}/checkins", headers=_auth(traveller))


def _contract() -> dict:
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- the store, read from the store


def test_the_columns_the_key_and_the_two_scans_are_in_the_store():
    """`sqlite_master` says the container exists; an ORM class alone would have proved nothing.

    Carried verbatim from the source, and on this branch it is a stronger claim than it was there:
    nothing here builds storage from the ORM metadata, so the only reason these nine columns and
    these two indexes are in the file this process opens is `backend/db/schema.sql` -- applied by
    `app/db/session.py::ensure_schema()` with `executescript()` on every boot.
    """

    with sqlite3.connect(_store_path()) as connection:
        tables = {
            r[0] for r in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='journey_checkins'"
            )
        }
        assert tables == {"journey_checkins"}, tables
        info = list(connection.execute("PRAGMA table_info(journey_checkins)"))
        columns = {r[1] for r in info}
        assert columns == {
            "id", "journey_id", "activity_id", "place_id", "target_kind", "target_key",
            "stamped_at", "note", "source",
        }, sorted(columns)
        not_null = {r[1] for r in info if r[3] == 1}
        # `note` and the two target ids are the nullable ones, and that is the shape the door relies
        # on: "no note was written" must stay tellable apart from "an empty note was written".  `id`
        # is asserted through `pk` instead, because SQLite reports a PRIMARY KEY column's notnull
        # flag as 0 unless the column also says NOT NULL -- reading only the flag would have called
        # the key column nullable when it is not.
        assert not_null == {
            "journey_id", "target_kind", "target_key", "stamped_at", "source"
        }, sorted(not_null)
        assert {r[1] for r in info if r[5] == 1} == {"id"}, sorted(info)
        fks = list(connection.execute("PRAGMA foreign_key_list(journey_checkins)"))
        by_table = {r[2]: r for r in fks}
        assert by_table["journeys"][6] == "CASCADE", fks
        # The two decisions this order hangs on, read out of the store rather than out of a comment.
        assert by_table["activities"][6] == "SET NULL", fks
        assert by_table["places"][6] == "SET NULL", fks
        index_list = list(connection.execute("PRAGMA index_list(journey_checkins)"))
        columns_of = {
            r[1]: [x[2] for x in connection.execute(f"PRAGMA index_info('{r[1]}')")]
            for r in index_list
        }
    # A table-level UNIQUE becomes an *autoindex* whose `sql` column in `sqlite_master` is NULL, so
    # looking for the word "UNIQUE" there finds nothing about a constraint that is enforced.
    unique = [(r[1], r[4]) for r in index_list if r[3] == "u"]
    assert len(unique) == 1, unique
    key_name = unique[0][0]
    assert key_name.startswith("sqlite_autoindex_journey_checkins_"), key_name
    assert columns_of[key_name] == ["journey_id", "target_key"], columns_of
    assert "idx_journey_checkins_journey_stamped" in columns_of, sorted(columns_of)
    assert columns_of["idx_journey_checkins_journey_stamped"] == ["journey_id", "stamped_at"]


# ---------------------------------------------------------------------- the write door, for real


def test_a_stamp_on_an_activity_comes_back_with_the_targets_own_words():
    stage = _stage("words")
    own = stage["own"]
    answer = _stamp(own["journey"], {"activity_id": own["activity"], "note": "傍晚到的"}, stage["traveler"])
    assert answer.status_code == 201, answer.text
    body = answer.json()
    assert body["target_kind"] == "ACTIVITY", body
    assert body["target_key"] == f"activity:{own['activity']}", body
    assert body["activity_id"] == own["activity"], body
    # The title is the activity's own (`stop-own`), not the place's, and the place leg is not filled
    # in just because the activity happens to point at a row: the stamp named one target.
    assert body["activity_title"] == "stop-own", body
    assert body["activity_type"] == "visit", body
    assert body["place_id"] is None and body["place_name"] is None, body
    assert body["note"] == "傍晚到的", body
    assert body["source"] == "FOREGROUND_WEB", body
    assert body["journey_id"] == own["journey"], body

    # THE DOOR TAKES NO TIME -- answered differently here than in `eeb8b8d2fd`, and it is a stronger
    # answer.  The source asserted that a body carrying `stamped_at` came back 201 with a *different*
    # stored instant, i.e. the field was accepted, ignored and dropped without a word.  Here the
    # shape is `extra="forbid"`, so the same request is a named 422 and the client is told.  The
    # product rule is the same in both: the traveller's device clock does not become a store fact.
    before = datetime.now(timezone.utc)
    forged = _stamp(
        own["journey"],
        {"place_id": stage["place"], "stamped_at": "1999-01-01T00:00:00+00:00"},
        stage["traveler"],
    )
    assert forged.status_code == 422, forged.text
    assert _code(forged.json()) == "VALIDATION_ERROR", forged.text
    assert "extra_forbidden" in json.dumps(forged.json(), ensure_ascii=False), forged.text
    assert "stamped_at" in json.dumps(forged.json(), ensure_ascii=False), forged.text

    # A legitimate place stamp, and the instant on it is the server's own clock.
    stamped_place = _stamp(own["journey"], {"place_id": stage["place"]}, stage["traveler"])
    assert stamped_place.status_code == 201, stamped_place.text
    assert stamped_place.json()["target_key"] == f"place:{stage['place']}", stamped_place.json()
    assert stamped_place.json()["stamped_at"] != "1999-01-01T00:00:00+00:00", stamped_place.json()
    assert (
        datetime.fromisoformat(stamped_place.json()["stamped_at"]) >= before
    ), stamped_place.json()

    read = _list(own["journey"], stage["traveler"])
    assert read.status_code == 200, read.text
    stamps = read.json()
    assert len(stamps) == 2, stamps
    assert [s["target_key"] for s in stamps] == sorted(s["target_key"] for s in stamps), stamps


def test_a_second_tap_names_the_row_that_already_won():
    stage = _stage("dupe")
    own = stage["own"]
    first = _stamp(own["journey"], {"activity_id": own["activity"]}, stage["traveler"])
    assert first.status_code == 201, first.text
    again = _stamp(own["journey"], {"activity_id": own["activity"]}, stage["traveler"])
    assert again.status_code == 409, (again.status_code, again.text)
    assert again.status_code != 500
    assert _reason(again.json()) == "CHECKIN_DUPLICATE_STAMP", again.text
    details = _details(again.json())
    assert details["existing_checkin_id"] == first.json()["id"], details
    assert details["target_key"] == f"activity:{own['activity']}", details
    # A tap that is refused must not have written anything either.
    with SessionLocal() as session:
        rows = session.scalars(
            select(JourneyCheckin).where(JourneyCheckin.journey_id == own["journey"])
        ).all()
    assert len(rows) == 1, [r.target_key for r in rows]
    # The same activity under the *other* trip is a different target row, not a duplicate.
    other = _stamp(stage["other"]["journey"], {"activity_id": stage["other"]["activity"]}, stage["traveler"])
    assert other.status_code == 201, other.text


def test_the_index_refuses_a_second_key_even_when_no_door_looked():
    """The durable half, driven past the door: two rows for one target cannot both be written.

    The door's read catches a replayed tap; this arm is about the case that read cannot see -- a row
    that appears between the check and the insert.  It goes in through the ORM, because the store is
    what has to refuse, and a promise that only holds inside one process is not a promise.

    Unchanged by the retrofit, and that is worth saying out loud: the principal seam guards an HTTP
    door, not a `Session`.  The UNIQUE in `backend/db/schema.sql` is the half that holds against a
    writer that never passes a door at all.
    """

    stage = _stage("race")
    own = stage["own"]
    key = f"activity:{own['activity']}"
    with SessionLocal() as session:
        session.add(
            JourneyCheckin(
                id=str(uuid.uuid4()), journey_id=own["journey"], activity_id=own["activity"],
                place_id=None, target_kind="ACTIVITY", target_key=key, stamped_at=MOMENT,
                note=None, source="FOREGROUND_WEB",
            )
        )
        session.commit()
    with SessionLocal() as session:
        try:
            session.add(
                JourneyCheckin(
                    id=str(uuid.uuid4()), journey_id=own["journey"], activity_id=own["activity"],
                    place_id=None, target_kind="ACTIVITY", target_key=key,
                    stamped_at=datetime.now(timezone.utc).isoformat(),
                    note="第二次", source="FOREGROUND_WEB",
                )
            )
            session.commit()
            raise AssertionError("the UNIQUE (journey_id, target_key) index did not refuse a duplicate")
        except IntegrityError:
            session.rollback()
        rows = session.scalars(
            select(JourneyCheckin).where(JourneyCheckin.target_key == key)
        ).all()
    assert len(rows) == 1, [r.id for r in rows]
    # And the door says the same named thing about a row it did not write itself.
    answer = _stamp(own["journey"], {"activity_id": own["activity"]}, stage["traveler"])
    assert answer.status_code == 409, (answer.status_code, answer.text)
    assert _reason(answer.json()) == "CHECKIN_DUPLICATE_STAMP", answer.text


def test_a_stamp_has_to_name_exactly_one_target():
    stage = _stage("target")
    own = stage["own"]
    neither = _stamp(own["journey"], {}, stage["traveler"])
    assert neither.status_code == 422, (neither.status_code, neither.text)
    assert _reason(neither.json()) == "CHECKIN_TARGET_REQUIRED", neither.text
    both = _stamp(own["journey"], {"activity_id": own["activity"], "place_id": stage["place"]}, stage["traveler"])
    assert both.status_code == 422, (both.status_code, both.text)
    assert _reason(both.json()) == "CHECKIN_TARGET_AMBIGUOUS", both.text
    assert _list(own["journey"], stage["traveler"]).json() == [], "a refused tap must leave nothing behind"

    # An id that is only whitespace names nothing, so it is the same fact as sending no field at all.
    # Answering `CHECKIN_ACTIVITY_UNKNOWN` here would describe a target the traveller never chose.
    blank = _stamp(own["journey"], {"activity_id": "   "}, stage["traveler"])
    assert blank.status_code == 422, (blank.status_code, blank.text)
    assert _reason(blank.json()) == "CHECKIN_TARGET_REQUIRED", blank.text
    assert _list(own["journey"], stage["traveler"]).json() == [], "a refused tap must leave nothing behind"


def test_the_duplicate_is_answered_before_the_target_row_is_asked_about():
    """The order of the two checks is a claim about which row is being spoken of.

    Whether this trip already holds a footprint for a key is a fact about `journey_checkins`, and it
    stays true after the target row is deleted (`ON DELETE SET NULL`).  So a re-tap on a superseded
    stop is told "already stamped here", naming the stamp on file -- not "no such activity", which
    would be a statement about a different table that the traveller's own tap did not raise.
    """

    stage = _stage("order")
    own = stage["own"]
    first = _stamp(own["journey"], {"activity_id": own["activity"]}, stage["traveler"])
    assert first.status_code == 201, first.text
    with SessionLocal() as session:
        session.execute(delete(Activity).where(Activity.id == own["activity"]))
        session.commit()

    again = _stamp(own["journey"], {"activity_id": own["activity"]}, stage["traveler"])
    assert again.status_code == 409, (again.status_code, again.text)
    assert _reason(again.json()) == "CHECKIN_DUPLICATE_STAMP", again.text
    details = _details(again.json())
    assert details["existing_checkin_id"] == first.json()["id"], details
    assert details["target_key"] == f"activity:{own['activity']}", details
    assert len(_list(own["journey"], stage["traveler"]).json()) == 1, "the refused tap wrote nothing"


def test_an_activity_elsewhere_is_named_apart_from_a_row_that_is_not_there():
    stage = _stage("foreign")
    own, other = stage["own"], stage["other"]

    elsewhere = _stamp(own["journey"], {"activity_id": other["activity"]}, stage["traveler"])
    assert elsewhere.status_code == 409, (elsewhere.status_code, elsewhere.text)
    assert _reason(elsewhere.json()) == "CHECKIN_ACTIVITY_NOT_IN_JOURNEY", elsewhere.text
    details = _details(elsewhere.json())
    # The journey named here is the caller's own second trip, so the field stays -- see arm 16 for
    # what a *stranger's* activity does to it.
    assert details["plan_journey_id"] == other["journey"], details
    assert details["asked_journey_id"] == own["journey"], details

    ghost_activity = _stamp(own["journey"], {"activity_id": "ord0476-no-such-activity"}, stage["traveler"])
    assert ghost_activity.status_code == 404, (ghost_activity.status_code, ghost_activity.text)
    assert _reason(ghost_activity.json()) == "CHECKIN_ACTIVITY_UNKNOWN", ghost_activity.text

    ghost_place = _stamp(own["journey"], {"place_id": "ord0476-no-such-place"}, stage["traveler"])
    assert ghost_place.status_code == 404, ghost_place.text
    assert _reason(ghost_place.json()) == "CHECKIN_PLACE_UNKNOWN", ghost_place.text

    for answer in (elsewhere, ghost_activity, ghost_place):
        assert answer.status_code != 500
    assert _list(own["journey"], stage["traveler"]).json() == [], "a refused tap must leave nothing behind"


# --------------------------------------------------------------------------------- bin, cascade


def test_a_trip_in_the_bin_is_neither_stampable_nor_stamp_readable():
    """The bin state is decided by the column, and one rule holds at both doors.

    The trip is put in the bin through the product's own `DELETE /api/v1/journeys/{id}`, and taken
    out again through `/undelete`, so what is asserted is the state a traveller can actually reach --
    not a column this module poked.

    Carried as written, including the two doors it touches that this slice does not own: on this
    branch `DELETE /api/v1/journeys/{id}` and `/undelete` are still not principal-bound, so a caller
    could drop a trip they do not hold.  That gap predates ORD-0476 and closing it is not this port's
    to do quietly; what this slice does guarantee is that a binned trip answers 409 at both footprint
    doors, to its owner and to everybody else.
    """

    stage = _stage("bin")
    own = stage["own"]
    stamped = _stamp(own["journey"], {"activity_id": own["activity"]}, stage["traveler"])
    assert stamped.status_code == 201, stamped.text

    dropped = client.delete(f"/api/v1/journeys/{own['journey']}")
    assert dropped.status_code == 204, dropped.text

    write = _stamp(own["journey"], {"place_id": stage["place"]}, stage["traveler"])
    assert write.status_code == 409, (write.status_code, write.text)
    assert _reason(write.json()) == "CHECKIN_JOURNEY_IN_RECYCLE_BIN", write.text
    assert _details(write.json())["deleted_at"], write.text

    read = _list(own["journey"], stage["traveler"])
    assert read.status_code == 409, (read.status_code, read.text)
    assert _reason(read.json()) == "CHECKIN_JOURNEY_IN_RECYCLE_BIN", read.text
    assert read.status_code != 500

    # An anonymous caller is refused for the credential before the bin is ever consulted, and gets
    # the bin's 409 in neither door.
    anonymous_read = _list(own["journey"])
    _assert_unauthorized(anonymous_read)

    back = client.post(f"/api/v1/journeys/{own['journey']}/undelete")
    assert back.status_code == 200, back.text
    after = _list(own["journey"], stage["traveler"])
    assert after.status_code == 200, after.text
    # Being in the bin is not being deleted: the stamp was there before and is still there after.
    assert [s["target_key"] for s in after.json()] == [f"activity:{own['activity']}"], after.json()


def test_a_footprint_outlives_the_rows_it_pointed_at():
    """The measured reason for `ON DELETE SET NULL`, replayed the way the replan path does it.

    `backend/app/operations/v9.py` deletes the activities of a superseded plan version, so this arm
    deletes that plan version and asserts three things: the stamp survives, its link goes to NULL
    through the store rather than through application code, and the door still says *what* was
    stamped from the key it wrote at the time.  A RESTRICT here would have broken that replan door --
    which is the same class of defect this project met once with `demo/reset` and a new table.
    """

    stage = _stage("cascade")
    own = stage["own"]
    stamped = _stamp(own["journey"], {"activity_id": own["activity"]}, stage["traveler"])
    assert stamped.status_code == 201, stamped.text
    stamp_id = stamped.json()["id"]

    with SessionLocal() as session:
        plan = session.get(PlanVersion, own["plan"])
        session.execute(delete(Activity).where(Activity.plan_version_id == plan.id))
        session.delete(plan)
        session.commit()

    with SessionLocal() as session:
        row = session.get(JourneyCheckin, stamp_id)
        assert row is not None, "the stamp was deleted along with its activity"
        assert row.activity_id is None, row.activity_id
        assert row.target_key == f"activity:{own['activity']}", row.target_key
        assert row.target_kind == "ACTIVITY", row.target_kind

    read = _list(own["journey"], stage["traveler"])
    assert read.status_code == 200, read.text
    bodies = read.json()
    assert len(bodies) == 1, bodies
    assert bodies[0]["activity_id"] is None, bodies[0]
    # The resolved title is null because the row is gone, and it is not filled in with anything.
    assert bodies[0]["activity_title"] is None and bodies[0]["activity_type"] is None, bodies[0]
    # And the freed key is not reusable: the stamp is still holding that target.
    again = _stamp(own["journey"], {"activity_id": own["activity"]}, stage["traveler"])
    assert again.status_code == 409, (again.status_code, again.text)
    assert _reason(again.json()) == "CHECKIN_DUPLICATE_STAMP", again.text


def test_reset_all_empties_the_footprints_before_it_empties_what_they_point_at():
    """Read out of `backend/app/services.py` rather than restated: a list order is a real ordering.

    The list is what `reset_all` walks, and it deletes children first because the schema turns
    foreign keys on.  A stamp references three tables, so its name has to come before all three or
    the reset answers a foreign-key failure having deleted half the store -- the exact shape this
    project already hit once when a new table was left out of that list.

    This arm reads the declared list rather than running it, because running it would empty the store
    this pytest process shares with every module that runs after it.
    """

    source = SERVICES.read_text(encoding="utf-8")
    tree = ast.parse(source)
    order = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "reset_all":
            for inner in ast.walk(node):
                if isinstance(inner, ast.Tuple):
                    names = [e.value for e in inner.elts if isinstance(e, ast.Constant)]
                    if "journey_checkins" in names:
                        order = names
                        break
    assert order is not None, "reset_all does not name journey_checkins at all"
    index = order.index("journey_checkins")
    for parent in ("journeys", "activities", "places"):
        assert parent in order, parent
        assert index < order.index(parent), (
            "journey_checkins would be deleted after", parent)
    assert len(order) == len(set(order)), "the reset list names a table twice"


def test_the_contract_declares_both_doors_and_no_control_they_lack():
    """The hand contract travels with the door -- and names the codes the retrofit added.

    PORTED WITH A WIDENED WHITELIST.  The source shipped this arm's `named_expansion_get` empty: its
    read door promised {200, 409} and documented exactly those two, because the door had no
    authentication to document.  This branch's read door also answers 401 (no credential), 404 (the
    trip is not the caller's) and 422 (a `traveler_id` was named in the query), and those three are
    named here in the same breath that documents them, which is what the source's own comment asked
    for: "a code that is named but never documented is red too, so the whitelist cannot rot into a
    list of intentions".

    NOT PORTED, and said as a gap rather than a silence: the source's last block reads
    `frontend/src/generated/api.ts` and asserts the generated client carries the path, both schemas
    and both operations.  That file is produced by an OpenAPI codegen step behind `npm`, which this
    transplant was instructed not to run and must not touch, so the generated client has not been
    re-taken and an arm asserting it would be a lie.  Everything that arm checked about the
    *contract* is checked above, and the served document is checked in arm 18.
    """

    paths = _contract()["paths"]
    node = paths["/journeys/{journey_id}/checkins"]
    listed, created = node["get"], node["post"]
    assert [p["$ref"].rsplit("/", 1)[-1] for p in node["parameters"]] == ["JourneyId"], node
    assert listed["operationId"] == "listJourneyCheckins", listed
    assert created["operationId"] == "createJourneyCheckin", created
    # Every named refusal the doors raise is in the contract, by name, so a screen may say it.
    raised = {
        "CHECKIN_JOURNEY_IN_RECYCLE_BIN", "CHECKIN_ACTIVITY_NOT_IN_JOURNEY",
        "CHECKIN_DUPLICATE_STAMP", "CHECKIN_ACTIVITY_UNKNOWN", "CHECKIN_PLACE_UNKNOWN",
        "CHECKIN_TARGET_REQUIRED", "CHECKIN_TARGET_AMBIGUOUS",
    }
    written = json.dumps(node, ensure_ascii=False)
    for name in sorted(raised):
        assert name in written, name
    assert sorted(created["responses"]) == ["201", "401", "404", "409", "422"], sorted(created["responses"])
    promised_get = {"200", "409"}
    # The three additions are this branch's authentication, named in the order that documents them.
    named_expansion_get: set[str] = {"401", "404", "422"}
    seen_get = set(listed["responses"])
    assert promised_get <= seen_get, ("a response ORD-0476 promised is gone from the read door",
                                      sorted(promised_get - seen_get), listed["responses"])
    assert seen_get - promised_get <= named_expansion_get, (
        "the read door documents a code this arm was never told about - name it in "
        "named_expansion_get in the same order that documents it",
        sorted(seen_get - promised_get - named_expansion_get))
    assert named_expansion_get <= seen_get, ("a code is whitelisted but not documented",
                                             sorted(named_expansion_get - seen_get))

    schemas = _contract()["components"]["schemas"]
    create = schemas["JourneyCheckinCreate"]
    # The door takes no time and no target-kind from a caller: those are the server's to decide.
    assert sorted(create["properties"]) == ["activity_id", "note", "place_id"], create
    # FUSION ADDITION: not merely "no time field declared" but no time field *tolerated* -- a body
    # that still carries one is refused rather than dropped.
    assert create.get("additionalProperties") is False, create
    read_shape = schemas["JourneyCheckin"]
    assert read_shape["properties"]["target_kind"]["enum"] == ["ACTIVITY", "PLACE"], read_shape
    assert read_shape["properties"]["source"]["enum"] == ["FOREGROUND_WEB"], read_shape
    for nullable in ("activity_id", "place_id", "note", "activity_title", "place_name"):
        assert read_shape["properties"][nullable]["type"] == ["string", "null"], nullable

    # AUTH RETROFIT, contract side: no caller-typed traveller id is declared on either door.  The
    # path parameter is the only control, and it is scoped by the credential behind it.
    for verb in ("get", "post"):
        dumped = json.dumps(node[verb].get("parameters"), ensure_ascii=False)
        assert "traveler_id" not in dumped, (verb, dumped)
        assert "query" not in dumped, (verb, dumped)


# ---------------------------------------------------- arms 12-18: the authentication this port added


def test_no_credential_reads_nothing_and_stamps_nothing():
    """The stop condition, measured on both doors rather than argued about.

    In `eeb8b8d2fd` both of these requests *succeeded*.  Its `create_journey_checkin` and
    `list_journey_checkins` took a journey id and answered it to whoever asked -- there was no
    credential to omit, and its test module never sent one -- so an anonymous cross-member read of a
    traveller's whole footprint, and an anonymous write into it, were the shipped behaviour.  Here
    each is refused before the store is read or written.
    """

    stage = _stage("anon")
    own = stage["own"]

    anonymous_read = _list(own["journey"])
    _assert_unauthorized(anonymous_read)

    anonymous_write = _stamp(own["journey"], {"activity_id": own["activity"]})
    _assert_unauthorized(anonymous_write)

    # "and nothing was stamped", taken from the store rather than assumed from the 401: the trip the
    # anonymous caller aimed at still holds exactly what its owner's own read reports -- nothing.
    from_store = _list(own["journey"], stage["traveler"])
    assert from_store.status_code == 200, from_store.text
    assert from_store.json() == [], from_store.json()
    with sqlite3.connect(_store_path()) as connection:
        written = connection.execute(
            "SELECT count(*) FROM journey_checkins WHERE journey_id = ?", (own["journey"],)
        ).fetchone()[0]
    assert written == 0, "the refused anonymous write reached the store"

    # The other three ways a request can fail to be a credential are refused the same way.
    garbage = client.get(
        f"/api/v1/journeys/{own['journey']}/checkins", headers={"Authorization": "Bearer not-a-token"}
    )
    assert garbage.status_code == 401, garbage.text
    body, signature = issue_traveler_token(stage["traveler"]).split(".", 1)
    forged = "forged" + body[6:] + "." + signature
    tampered = client.get(
        f"/api/v1/journeys/{own['journey']}/checkins", headers={"Authorization": f"Bearer {forged}"}
    )
    assert tampered.status_code == 401, tampered.text

    # A credential that verifies but whose traveller this server does not hold is refused at the seam
    # (`resolve_traveler_principal` answers "traveler principal no longer exists"), before the trip is
    # ever looked up.  Contrast the arm below, where a *real* traveller reading a trip they do not own
    # is a 404: the two failures are different facts and the doors keep them apart.
    vanished_id = str(uuid.uuid4())
    vanished = _list(own["journey"], vanished_id)
    assert vanished.status_code == 401, vanished.text
    assert _code(vanished.json()) == "REQUEST_ERROR", vanished.text
    assert _reason(vanished.json()) is None, vanished.text
    # ...and the same non-existent subject is refused on the write door, having stamped nothing.
    vanished_write = _stamp(own["journey"], {"activity_id": own["activity"]}, vanished_id)
    _assert_unauthorized(vanished_write)
    assert _list(own["journey"], stage["traveler"]).json() == []


def test_a_stranger_can_read_nothing_stamp_nothing_and_cannot_tell_absent_from_not_mine():
    """The cross-member read and write the source's doors both allowed, refused without an oracle.

    `eeb8b8d2fd` looked the trip up by id alone, so traveller B holding A's journey id got A's
    footprints at the read door and could add to them at the write door.  Here the same lookup
    requires the row to belong to the caller, and A's trip gives B the identical answer a trip that
    does not exist gives -- a distinct 403 would turn either door into a way to enumerate which
    journey ids are taken and whose they are.  Same ruling `add_collection_item` records.
    """

    a = _stage("stranger-a")
    b = _stage("stranger-b")

    assert _stamp(a["own"]["journey"], {"activity_id": a["own"]["activity"]}, a["traveler"]).status_code == 201

    refused_read = _list(a["own"]["journey"], b["traveler"])
    assert refused_read.status_code == 404, refused_read.text
    assert _reason(refused_read.json()) == "CHECKIN_JOURNEY_UNKNOWN", refused_read.text
    assert refused_read.status_code != 500

    refused_write = _stamp(a["own"]["journey"], {"place_id": a["place"]}, b["traveler"])
    assert refused_write.status_code == 404, refused_write.text
    assert _reason(refused_write.json()) == "CHECKIN_JOURNEY_UNKNOWN", refused_write.text

    absent = _list(str(uuid.uuid4()), b["traveler"])
    assert absent.status_code == 404, absent.text
    # Same status, same token, same details shape: the two answers are indistinguishable from outside.
    assert _reason(absent.json()) == _reason(refused_read.json()), (absent.text, refused_read.text)
    assert _details(absent.json()) == _details(refused_read.json()), (absent.text, refused_read.text)

    # The refused reads and writes changed nothing on A's trip.
    still = _list(a["own"]["journey"], a["traveler"])
    assert [s["target_key"] for s in still.json()] == [f"activity:{a['own']['activity']}"], still.json()
    # And B's own trip is untouched too -- a refusal on A's row must not have stamped B's.
    assert _list(b["own"]["journey"], b["traveler"]).json() == []


def test_another_traveler_id_cannot_be_named_on_either_door_even_with_valid_credentials():
    """A's credential plus B's id is a refusal, not B's footprints.

    Neither door in the source had a `traveler_id` to refuse -- they scoped by the path id alone and
    answered anybody's trip -- so this arm is not repairing a parameter the transplant removed, it is
    pinning the rule that no such input may be added back.  Refusing it *by name* is the point: a
    door that quietly ignored it would let a client believe its request for somebody else's history
    had been honoured, which is how a hole survives a refactor.
    """

    a = _stage("scope-a")
    b = _stage("scope-b")
    assert _stamp(a["own"]["journey"], {"activity_id": a["own"]["activity"]}, a["traveler"]).status_code == 201

    for verb, call in (
        ("read", lambda: client.get(
            f"/api/v1/journeys/{a['own']['journey']}/checkins",
            params={"traveler_id": b["traveler"]}, headers=_auth(a["traveler"]))),
        ("write", lambda: client.post(
            f"/api/v1/journeys/{a['own']['journey']}/checkins",
            params={"traveler_id": b["traveler"]},
            json={"place_id": a["place"]}, headers=_auth(a["traveler"]))),
    ):
        attempted = call()
        assert attempted.status_code == 422, (verb, attempted.text)
        assert _reason(attempted.json()) == "CHECKIN_TRAVELER_SCOPE_PARAM_NOT_ACCEPTED", (verb, attempted.text)
        assert _details(attempted.json()).get("field") == "traveler_id", (verb, attempted.text)
        # The refusal carried no footprints -- not B's, and not a stripped-down version of A's.
        assert "target_key" not in json.dumps(attempted.json(), ensure_ascii=False), (verb, attempted.text)

    # Without a credential the same query is refused at the door before the parameter is read.
    unauthenticated = client.get(
        f"/api/v1/journeys/{a['own']['journey']}/checkins", params={"traveler_id": b["traveler"]}
    )
    assert unauthenticated.status_code == 401, unauthenticated.text

    # A body that tries to assert a traveller is refused as the unknown field it is.
    asserted = client.post(
        f"/api/v1/journeys/{a['own']['journey']}/checkins",
        json={"activity_id": a["other"]["activity"], "traveler_id": b["traveler"]},
        headers=_auth(a["traveler"]),
    )
    assert asserted.status_code == 422, asserted.text
    assert _code(asserted.json()) == "VALIDATION_ERROR", asserted.text

    # And A's own read, with nothing asserted, is the honest answer about A.
    own_rows = _list(a["own"]["journey"], a["traveler"])
    assert [s["target_key"] for s in own_rows.json()] == [f"activity:{a['own']['activity']}"]


def test_a_scoped_read_returns_only_the_subjects_own_rows():
    """「我的足迹」 is a claim about the credential, and it is measured against the store.

    Two travellers each stamp their own trip.  Each read is then compared not only to the other's
    absence but to the SQL that would answer it unscoped: the rows a caller sees are exactly the rows
    whose trip they own, and the door's own answer is what the store says about that trip.
    """

    a = _stage("mine-a")
    b = _stage("mine-b")
    assert _stamp(a["own"]["journey"], {"activity_id": a["own"]["activity"]}, a["traveler"]).status_code == 201
    assert _stamp(a["other"]["journey"], {"place_id": a["place"]}, a["traveler"]).status_code == 201
    assert _stamp(b["own"]["journey"], {"place_id": b["place"]}, b["traveler"]).status_code == 201

    rows_a = _list(a["own"]["journey"], a["traveler"]).json()
    assert [r["target_key"] for r in rows_a] == [f"activity:{a['own']['activity']}"], rows_a
    # Every row answered to A carries a journey A owns -- checked against `journeys.traveler_id`, the
    # same column the door reads, so this is not the door confirming its own filter with its own code.
    with sqlite3.connect(_store_path()) as connection:
        owned = {
            row[0] for row in connection.execute(
                "SELECT id FROM journeys WHERE traveler_id = ?", (a["traveler"],)
            )
        }
        answered = {
            row[0] for row in connection.execute(
                "SELECT journey_id FROM journey_checkins WHERE journey_id IN "
                "(SELECT id FROM journeys WHERE traveler_id = ?)",
                (a["traveler"],),
            )
        }
    assert answered <= owned, (sorted(answered), sorted(owned))
    assert b["own"]["journey"] not in owned

    # B sees its own row and nothing of A's, under either of A's journey ids.
    rows_b = _list(b["own"]["journey"], b["traveler"]).json()
    assert [r["target_key"] for r in rows_b] == [f"place:{b['place']}"], rows_b
    assert _list(a["own"]["journey"], b["traveler"]).status_code == 404
    assert _list(a["other"]["journey"], b["traveler"]).status_code == 404

    # A's second trip keeps its own footprint: scoping is per trip, not a global merge.
    assert [r["target_key"] for r in _list(a["other"]["journey"], a["traveler"]).json()] == [
        f"place:{a['place']}"
    ]


def test_a_strangers_activity_id_does_not_leak_its_journey_through_a_refusal():
    """FUSION ADDITION, one field wide.

    The source's `CHECKIN_ACTIVITY_NOT_IN_JOURNEY` details carried `plan_journey_id` unconditionally.
    The condition it names is real and the traveller needs the sentence, so the token and the status
    stay exactly as they were -- but a guessed activity id belonging to another traveller returned
    *their* journey id in an error body, which is a cross-member read measured one field at a time.
    Here the field is filled only when that trip is the caller's own, which is the case the source's
    own test stage exercises (one traveller's activity under one of their other trips), so nothing
    the source could distinguish stops being distinguishable.
    """

    a = _stage("leak-a")
    b = _stage("leak-b")

    stranger = _stamp(a["own"]["journey"], {"activity_id": b["own"]["activity"]}, a["traveler"])
    assert stranger.status_code == 409, stranger.text
    assert _reason(stranger.json()) == "CHECKIN_ACTIVITY_NOT_IN_JOURNEY", stranger.text
    details = _details(stranger.json())
    assert details["plan_journey_id"] is None, details
    assert details["asked_journey_id"] == a["own"]["journey"], details
    assert b["own"]["journey"] not in json.dumps(stranger.json(), ensure_ascii=False), stranger.text
    # B's trip holds nothing A wrote: the refused tap stamped no footprint anywhere.
    assert _list(b["own"]["journey"], b["traveler"]).json() == []

    # The caller's own foreign trip is still named, because naming it is not a leak.
    mine = _stamp(a["own"]["journey"], {"activity_id": a["other"]["activity"]}, a["traveler"])
    assert mine.status_code == 409, mine.text
    assert _reason(mine.json()) == "CHECKIN_ACTIVITY_NOT_IN_JOURNEY", mine.text
    assert _details(mine.json())["plan_journey_id"] == a["other"]["journey"], _details(mine.json())


def test_the_audit_row_names_the_principal_the_server_verified():
    """`actor_id` is the credential, so the log answers who stamped rather than who was named.

    The source's door recorded no actor at all -- there was no actor to record, since nothing in the
    request identified a caller -- so `audit_logs.actor_id` stayed NULL while the row's own journey
    id went into `after`.  Here the actor columns come from the principal, which is the difference an
    operator reads when reconstructing who stamped what on whose trip.
    """

    a = _stage("audit-a")
    b = _stage("audit-b")
    stamped = _stamp(a["own"]["journey"], {"activity_id": a["own"]["activity"]}, a["traveler"])
    assert stamped.status_code == 201, stamped.text

    with sqlite3.connect(_store_path()) as connection:
        rows = connection.execute(
            "SELECT action, actor_type, actor_id, journey_id FROM audit_logs WHERE entity_id = ?",
            (stamped.json()["id"],),
        ).fetchall()
    by_action = {row[0]: row for row in rows}
    assert "journey.checkin.stamped" in by_action, rows
    row = by_action["journey.checkin.stamped"]
    assert row[1] == "traveler", row
    assert row[2] == a["traveler"], row
    assert row[3] == a["own"]["journey"], row
    # The refused stranger's attempt recorded nothing at all under B's id.
    refused = _stamp(a["own"]["journey"], {"place_id": a["place"]}, b["traveler"])
    assert refused.status_code == 404, refused.text
    with sqlite3.connect(_store_path()) as connection:
        acting = connection.execute(
            "SELECT count(*) FROM audit_logs WHERE action = 'journey.checkin.stamped' "
            "AND actor_id = ?",
            (b["traveler"],),
        ).fetchone()[0]
    assert acting == 0, "a refused footprint write left an audit row as if it had succeeded"


def test_the_served_document_declares_the_refusals_the_contract_declares():
    """`/openapi.json` is a second artifact, and a code unnamed in the decorator never reaches it.

    The rule ORD-0395 states in this file, applied to the doors this port added: a hand contract that
    declares a 401 the decorator does not name would leave the served document silent about the very
    behaviour the transplant exists to install, and a consumer reading `/openapi.json` -- which is
    what the frontend's type file is generated from -- would see an open door.
    """

    served = main_module.app.openapi()
    contract = _contract()["paths"]
    doors = {
        ("/journeys/{journey_id}/checkins", "get"): {"200", "401", "404", "409", "422"},
        ("/journeys/{journey_id}/checkins", "post"): {"201", "401", "404", "409", "422"},
    }
    for (path, verb), expected in doors.items():
        assert path in contract, path
        # the runtime mounts everything under /api/v1, which the contract path omits by design
        node = served["paths"]["/api/v1" + path][verb]
        got = set(node.get("responses", {}))
        assert expected <= got, (path, verb, sorted(got))
        for code in sorted(expected):
            assert code in contract[path][verb].get("responses", {}), (path, verb, code)
    # Every refusal token the doors can emit is reachable from the served document's prose too, so a
    # consumer of /openapi.json alone can name what happened to it.
    served_dump = json.dumps(served["paths"]["/api/v1/journeys/{journey_id}/checkins"], ensure_ascii=False)
    for token in (
        "CHECKIN_JOURNEY_UNKNOWN", "CHECKIN_JOURNEY_IN_RECYCLE_BIN", "CHECKIN_DUPLICATE_STAMP",
        "CHECKIN_ACTIVITY_UNKNOWN", "CHECKIN_PLACE_UNKNOWN", "CHECKIN_TARGET_REQUIRED",
        "CHECKIN_TARGET_AMBIGUOUS", "CHECKIN_ACTIVITY_NOT_IN_JOURNEY",
        "CHECKIN_TRAVELER_SCOPE_PARAM_NOT_ACCEPTED",
    ):
        assert token in served_dump, token
    shapes = served["components"]["schemas"]
    assert sorted(shapes["JourneyCheckinCreate"]["properties"]) == ["activity_id", "note", "place_id"]
    assert shapes["JourneyCheckinCreate"].get("additionalProperties") is False
    assert set(shapes["JourneyCheckin"]["properties"]) == {
        "id", "journey_id", "activity_id", "place_id", "target_kind", "target_key", "stamped_at",
        "note", "source", "activity_title", "activity_type", "place_name", "place_category",
    }
