from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.db.models import AccommodationOfferSnapshot, JourneyTripContext, StayJourneyOption
from app.execution.launch_origin import grounded_launch_origin


class _Rows:
    def __init__(self, row):
        self.row = row

    def all(self):
        return [self.row] if self.row is not None else []


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
        title="Target",
    )


def test_fresh_foreground_location_wins_but_stays_advisory():
    now = datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc)
    location = SimpleNamespace(
        id="loc1",
        latitude=35.0,
        longitude=135.0,
        accuracy_m=20.0,
        captured_at=now.isoformat(),
    )
    result = grounded_launch_origin(
        _Session(location=location),
        _journey(),
        target_activity=_target(now),
        now=now,
    )

    assert result["source"] == "FOREGROUND_LOCATION"
    assert result["authority"] == "ADVISORY_FOREGROUND"


def test_selected_stay_covering_target_beats_arrival_anchor():
    now = datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc)
    option = SimpleNamespace(
        id="stay-option",
        accommodation_offer_id="offer1",
        status="SELECTED",
        rank=1,
    )
    offer = SimpleNamespace(
        id="offer1",
        property_name="Hotel",
        latitude=34.9,
        longitude=135.7,
        check_in_at=(now - timedelta(hours=8)).isoformat(),
        check_out_at=(now + timedelta(hours=12)).isoformat(),
        captured_at=(now - timedelta(hours=24)).isoformat(),
        provider_key="hotel-provider",
    )
    context = SimpleNamespace(
        arrival_anchor_json='{"at":"2026-10-05T23:00:00+00:00","location":"Station","latitude":34.8,"longitude":135.6}'
    )
    result = grounded_launch_origin(
        _Session(stay_option=option, stay_offer=offer, trip_context=context),
        _journey(),
        target_activity=_target(now),
        now=now,
    )

    assert result["source"] == "SELECTED_STAY"
    assert result["reason_code"] == "SELECTED_STAY_COVERS_TARGET_START"


def test_future_hotel_checkin_does_not_replace_arrival_anchor():
    now = datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc)
    option = SimpleNamespace(
        id="stay-option",
        accommodation_offer_id="offer1",
        status="SELECTED",
        rank=1,
    )
    offer = SimpleNamespace(
        id="offer1",
        property_name="Hotel",
        latitude=34.9,
        longitude=135.7,
        check_in_at=(now + timedelta(hours=6)).isoformat(),
        check_out_at=(now + timedelta(hours=30)).isoformat(),
        captured_at=now.isoformat(),
        provider_key="hotel-provider",
    )
    context = SimpleNamespace(
        arrival_anchor_json=(
            '{"at":"2026-10-06T08:00:00+00:00","location":"Station",'
            '"latitude":34.8,"longitude":135.6,"reservation_id":"r1"}'
        )
    )
    result = grounded_launch_origin(
        _Session(stay_option=option, stay_offer=offer, trip_context=context),
        _journey(),
        target_activity=_target(now),
        now=now,
    )

    assert result["source"] == "ARRIVAL_ANCHOR"


def test_no_grounded_source_stays_unknown():
    now = datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc)
    result = grounded_launch_origin(
        _Session(),
        _journey(),
        target_activity=_target(now),
        now=now,
    )

    assert result["state"] == "UNKNOWN_ORIGIN"
    assert result["origin_key"] is None
