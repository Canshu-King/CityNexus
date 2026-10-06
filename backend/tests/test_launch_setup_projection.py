from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.db.models import AccommodationOfferSnapshot, JourneyTripContext, StayJourneyOption
from app.execution.launch_setup import launch_setup_projection


class _Session:
    def __init__(self, *, location=None, stay_option=None, stay_offer=None, trip_context=None):
        self.location = location
        self.stay_option = stay_option
        self.stay_offer = stay_offer
        self.trip_context = trip_context

    def scalar(self, statement):
        text = str(statement)
        if "location_observations" in text:
            return self.location
        if "stay_journey_options" in text:
            return self.stay_option
        return None

    def get(self, model, row_id):
        if model is AccommodationOfferSnapshot and self.stay_offer is not None:
            return self.stay_offer if str(self.stay_offer.id) == str(row_id) else None
        if model is JourneyTripContext:
            return self.trip_context
        return None


def _journey():
    return SimpleNamespace(id="j1")


def _target(now):
    return SimpleNamespace(
        id="a1",
        start_at=(now + timedelta(hours=2)).isoformat(),
        place_id="target-place",
    )


def test_unknown_origin_exposes_only_real_actions():
    now = datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc)
    result = launch_setup_projection(
        _Session(),
        _journey(),
        target_activity=_target(now),
        now=now,
    )

    assert result["status"] == "NEEDS_ORIGIN"
    assert "SHARE_LOCATION" in result["actions"]
    assert "CHOOSE_PLACE" in result["actions"]
    assert "USE_SELECTED_STAY" not in result["actions"]
    assert "USE_ARRIVAL_POINT" not in result["actions"]


def test_temporally_valid_stay_is_offered():
    now = datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc)
    option = SimpleNamespace(id="s1", accommodation_offer_id="o1", status="SELECTED", rank=1)
    offer = SimpleNamespace(
        id="o1",
        property_name="Hotel",
        provider_key="hotel-provider",
        check_in_at=(now - timedelta(hours=6)).isoformat(),
        check_out_at=(now + timedelta(hours=12)).isoformat(),
    )
    result = launch_setup_projection(
        _Session(stay_option=option, stay_offer=offer),
        _journey(),
        target_activity=_target(now),
        now=now,
    )

    assert "USE_SELECTED_STAY" in result["actions"]
    stay = next(item for item in result["candidates"] if item["kind"] == "SELECTED_STAY")
    assert stay["eligible"] is True


def test_future_checkin_stay_is_visible_but_not_actionable():
    now = datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc)
    option = SimpleNamespace(id="s1", accommodation_offer_id="o1", status="SELECTED", rank=1)
    offer = SimpleNamespace(
        id="o1",
        property_name="Hotel",
        provider_key="hotel-provider",
        check_in_at=(now + timedelta(hours=6)).isoformat(),
        check_out_at=(now + timedelta(hours=20)).isoformat(),
    )
    result = launch_setup_projection(
        _Session(stay_option=option, stay_offer=offer),
        _journey(),
        target_activity=_target(now),
        now=now,
    )

    assert "USE_SELECTED_STAY" not in result["actions"]
    stay = next(item for item in result["candidates"] if item["kind"] == "SELECTED_STAY")
    assert stay["eligible"] is False


def test_coordinate_bearing_arrival_anchor_is_actionable():
    now = datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc)
    context = SimpleNamespace(
        arrival_anchor_json=(
            '{"at":"2026-10-06T08:00:00+00:00","location":"Nara Station",'
            '"latitude":34.6800,"longitude":135.8180,"reservation_id":"r1"}'
        )
    )
    result = launch_setup_projection(
        _Session(trip_context=context),
        _journey(),
        target_activity=_target(now),
        now=now,
    )

    assert "USE_ARRIVAL_POINT" in result["actions"]
    anchor = next(item for item in result["candidates"] if item["kind"] == "ARRIVAL_ANCHOR")
    assert anchor["eligible"] is True
