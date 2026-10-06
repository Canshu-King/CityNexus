from types import SimpleNamespace

from app.live_context_watch import _place_receipt, classify_opening_hours, observation_is_fresh


def activity(start="2026-10-08T09:00:00+09:00", end="2026-10-08T10:00:00+09:00"):
    return SimpleNamespace(id="a1", start_at=start, end_at=end)


def place():
    return SimpleNamespace(id="p1", external_id="overpass:node/1", name="Exact Venue")


def test_opening_hours_open_compatible_uses_journey_timezone():
    result = classify_opening_hours(
        activity=activity(),
        place=place(),
        opening={"status": "NORMALIZED_VALID", "intervals": [{"days": ["Th"], "open": "08:00", "close": "18:00"}]},
        timezone_name="Asia/Tokyo",
    )
    assert result["status"] == "OPEN_COMPATIBLE"


def test_explicit_closed_is_material_conflict():
    result = classify_opening_hours(
        activity=activity(), place=place(), opening={"status": "CLOSED", "raw": "closed", "intervals": []}, timezone_name="Asia/Tokyo"
    )
    assert result["status"] == "CLOSED_CONFLICT"
    assert result["reason_code"] == "EXPLICIT_CLOSED_STATE"


def test_outside_verified_hours_is_conflict_but_unknown_is_not():
    outside = classify_opening_hours(
        activity=activity(), place=place(), opening={"status": "OFFICIAL_WEB_VERIFIED", "intervals": [{"days": ["Th"], "open": "11:00", "close": "18:00"}]}, timezone_name="Asia/Tokyo"
    )
    unknown = classify_opening_hours(
        activity=activity(), place=place(), opening={"status": "RAW_UNPARSED", "raw": "maybe open", "intervals": []}, timezone_name="Asia/Tokyo"
    )
    assert outside["status"] == "OUTSIDE_VERIFIED_HOURS"
    assert unknown["status"] == "UNKNOWN"


def test_overnight_hours_cover_local_activity_interval():
    result = classify_opening_hours(
        activity=activity("2026-10-08T23:30:00+09:00", "2026-10-09T00:30:00+09:00"),
        place=place(),
        opening={"status": "NORMALIZED_VALID", "intervals": [{"days": ["Th"], "open": "22:00", "close": "24:00"}]},
        timezone_name="Asia/Tokyo",
    )
    assert result["status"] == "OPEN_COMPATIBLE"


def test_stale_observation_cannot_override_newer_evidence():
    assert observation_is_fresh("2026-10-08T01:00:00+00:00", "2026-10-08T00:59:59+00:00")
    assert not observation_is_fresh("2026-10-08T00:59:59+00:00", "2026-10-08T01:00:00+00:00")
    assert not observation_is_fresh("2026-10-08T01:00:00", "2026-10-08T00:59:59+00:00")


def test_receipt_binding_requires_exact_place_id():
    receipt = {"places": [{"place_id": "p1", "provider_entity": "overpass:node/1"}]}
    assert _place_receipt(receipt, "p1")["provider_entity"] == "overpass:node/1"
    assert _place_receipt(receipt, "p2") is None
