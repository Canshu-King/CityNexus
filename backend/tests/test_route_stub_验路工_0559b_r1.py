"""ORD-0559-b stub gap, family `journeys/mobility`: the door nothing ever answered.

`GET /api/v1/journeys/{journey_id}/mobility` is declared at `backend/app/main.py:6105` and no
test file on this line said its path.  These cases assert its response, field by field, against
the projection it actually builds (`fact_payload` at `backend/app/stay_mobility.py:2041`, the
one imported at `backend/app/main.py:493`) and against the three keys the handler itself names.

Fixtures are the line's own: `POST /api/v1/demo/reset` for a journey with a seeded city, and
`MobilityFact` rows written with the provider layer's own provenance class, the same shape
`backend/tests/test_qoder_mobility_hard_gap.py:95` uses.  Nothing here mocks a door out.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.models import MobilityFact, Place
from app.db.session import SessionLocal
from app.main import app
from app.replanning.provider_snapshots import LIVE_PROVIDER_CAPTURE
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(app)
TZ = timezone(timedelta(hours=8))
CITY_CODE = "CNX-DEMO"
DOOR = "/api/v1/journeys/{journey_id}/mobility"

# the three keys the handler writes, and the projection's own field list
DOOR_KEYS = {"modes", "available_modes", "choose_for_me"}
FACT_KEYS = {
    "id", "from_key", "to_key", "mode", "duration_min", "distance_m",
    "cost_amount_minor", "currency", "cost_status", "paid_mode", "walking_min",
    "transfers", "weather_exposure", "reliability_score", "provider_key",
    "provenance", "geometry", "crs", "evidence", "captured_at", "expires_at",
}
AVAILABLE_MODES = ["WALK", "BICYCLE", "TRANSIT", "AUTO", "RIDE_HAIL"]
PROVIDER_KEY = "yanlugong-0559b-fixture"


def _journey() -> str:
    return client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()["journey_id"]


def _city_pair() -> tuple[str, str]:
    with SessionLocal() as session:
        ids = list(
            session.scalars(
                select(Place.id).where(Place.city_code == CITY_CODE).order_by(Place.id)
            ).all()
        )
    assert len(ids) >= 2, f"SETUP 失败：{CITY_CODE} 在种子里不足 2 行，这扇门测不到东西"
    return str(ids[0]), str(ids[1])


def _clear() -> None:
    with SessionLocal() as session:
        session.execute(
            delete(MobilityFact).where(MobilityFact.provider_key == PROVIDER_KEY)
        )
        session.commit()


def _fact(journey_id: str, origin: str, destination: str, mode: str, *, minutes: int) -> str:
    fact_id = f"{PROVIDER_KEY}-{journey_id}-{origin}-{destination}-{mode}"
    stamp = datetime.now(TZ).isoformat()
    with SessionLocal() as session:
        session.add(
            MobilityFact(
                id=fact_id,
                journey_id=journey_id,
                option_id=None,
                from_key=origin,
                to_key=destination,
                mode=mode,
                duration_min=minutes,
                distance_m=1400,
                cost_amount_minor=None,
                currency=None,
                cost_status="UNKNOWN",
                walking_min=minutes,
                transfers=0,
                weather_exposure="NONE",
                reliability_score=0.9,
                provider_key=PROVIDER_KEY,
                provenance=LIVE_PROVIDER_CAPTURE,
                geometry_json="{}",
                crs="WGS84",
                paid_mode=False,
                evidence_json="{}",
                captured_at=stamp,
                expires_at=None,
            )
        )
        session.commit()
    return fact_id


def test_mobility_door_answers_the_projection_field_by_field():
    _clear()
    journey_id = _journey()
    first, second = _city_pair()
    walked = _fact(journey_id, first, second, "WALK", minutes=17)
    ridden = _fact(journey_id, first, second, "TRANSIT", minutes=31)
    back = _fact(journey_id, second, first, "AUTO", minutes=9)
    try:
        answer = client.get(DOOR.format(journey_id=journey_id))
        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert set(body) == DOOR_KEYS
        assert body["available_modes"] == AVAILABLE_MODES
        assert body["choose_for_me"] is True
        assert isinstance(body["modes"], list) and len(body["modes"]) == 3

        # the handler's own order: from_key, then to_key, then mode
        triples = [(item["from_key"], item["to_key"], item["mode"]) for item in body["modes"]]
        assert triples == sorted(triples)
        assert triples == sorted([(first, second, "TRANSIT"), (first, second, "WALK"),
                                  (second, first, "AUTO")])

        for item in body["modes"]:
            assert set(item) == FACT_KEYS
            assert item["provider_key"] == PROVIDER_KEY
            assert item["provenance"] == LIVE_PROVIDER_CAPTURE
            assert item["crs"] == "WGS84"
            assert item["cost_status"] == "UNKNOWN"
            assert item["cost_amount_minor"] is None
            assert item["currency"] is None
            assert item["paid_mode"] is False
            assert item["geometry"] == {}
            assert item["evidence"] == {}
            assert item["expires_at"] is None

        transit = next(item for item in body["modes"] if item["mode"] == "TRANSIT")
        assert transit["id"] == ridden
        assert transit["duration_min"] == 31
        assert transit["distance_m"] == 1400
        assert transit["walking_min"] == 31
        assert transit["transfers"] == 0
        assert transit["reliability_score"] == 0.9
        walk = next(item for item in body["modes"] if item["mode"] == "WALK")
        assert walk["id"] == walked
        assert walk["duration_min"] == 17
        assert walk["from_key"] == first and walk["to_key"] == second
        auto = next(item for item in body["modes"] if item["mode"] == "AUTO")
        assert auto["id"] == back
        assert auto["from_key"] == second and auto["to_key"] == first
        assert {item["id"] for item in body["modes"]} == {walked, ridden, back}
    finally:
        _clear()


def test_mobility_door_for_a_trip_without_facts_still_names_the_modes_it_could_compare():
    _clear()
    journey_id = _journey()
    answer = client.get(DOOR.format(journey_id=journey_id))
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["modes"] == []
    assert body["available_modes"] == AVAILABLE_MODES
    assert body["choose_for_me"] is True
    _clear()


def test_mobility_door_keeps_one_trip_facts_out_of_another():
    _clear()
    seeded = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    journey_id = seeded["journey_id"]
    first, second = _city_pair()
    stored = _fact(journey_id, first, second, "BICYCLE", minutes=12)
    try:
        later = datetime.now(TZ) + timedelta(days=300)
        other = client.post("/api/v1/journeys", json={
            "traveler_id": seeded["traveler_id"],
            "title": "ORD-0559-b isolation",
            "city_code": CITY_CODE,
            "timezone": "Asia/Shanghai",
            "start_at": later.isoformat(),
            "end_at": (later + timedelta(days=2)).isoformat(),
            "budget": {"amount_minor": 100000, "currency": "CNY"},
        })
        assert other.status_code == 201, other.text
        assert other.json()["id"] != journey_id

        empty = client.get(DOOR.format(journey_id=other.json()["id"]))
        assert empty.status_code == 200, empty.text
        assert empty.json()["modes"] == []

        mine = client.get(DOOR.format(journey_id=journey_id))
        assert mine.status_code == 200, mine.text
        assert [item["id"] for item in mine.json()["modes"]] == [stored]
    finally:
        _clear()


def test_mobility_door_names_the_trip_it_could_not_find():
    missing = "00000000-0000-4000-8000-000000000000"
    answer = client.get(DOOR.format(journey_id=missing))
    assert answer.status_code == 404, answer.text
    error = answer.json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert error["message_key"] == "resource.not_found"
    assert missing in error["message"]
    assert error["error_receipt_id"].startswith("CNX-")
