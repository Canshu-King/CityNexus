import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app import fact_acquisition as facts
from app.agent.gateway import _city_category_terms, _city_search_terms
from app.agent.guardian import _cooldown_active
from app.db.models import GuardianRun, Place
from app.db.session import SessionLocal, ensure_schema


def test_official_japanese_am_pm_window_uses_closing_not_last_admission():
    opening = facts._plain_text_opening(
        "開館時間 午前10時から午後6時（入館は午後5時30分まで） 入館料 無料",
        "https://official.example/visit", reference_at="2026-10-08",
    )
    assert opening["status"] == "OFFICIAL_WEB_VERIFIED"
    assert (opening["open"], opening["close"]) == ("10:00", "18:00")


@pytest.mark.parametrize("text,currency", [("入館料 無料", "JPY"), ("门票 免费", "CNY")])
def test_explicit_free_does_not_guess_currency_from_han_characters(text, currency):
    cost = facts._plain_text_cost(text, "https://official.example/visit", reference_at=None)
    assert cost["status"] == "VERIFIED_PROVIDER"
    assert cost["amount_minor"] == 0
    assert cost["currency"] == currency


def test_missing_price_is_not_free():
    cost = facts._plain_text_cost("工艺馆 地址 电话", "https://official.example/visit", reference_at=None)
    assert cost["status"] == "UNKNOWN"
    assert cost["amount_minor"] is None


def test_english_category_search_expands_to_provider_place_categories():
    assert "museum" in _city_search_terms("culture")
    assert "gallery" in _city_search_terms("cultural")
    assert "garden" in _city_category_terms("experience")


@pytest.mark.parametrize("approval", ["OPERATOR_VERIFIED", "PROVIDER_TAG_EXACT_URL"])
def test_agent_source_candidate_cannot_downgrade_existing_approved_binding(monkeypatch, approval):
    ensure_schema()
    city = f"R22-TEST-{uuid4().hex}"
    binding = {
        "provider_entity": "overpass:node/1515", "source_url": "https://official.example/visit",
        "source_class": "OFFICIAL_WEB", "approval": approval,
        "identity_basis": {"matched_provider_entity": True, "provider_entity": "overpass:node/1515"},
    }
    monkeypatch.setattr(facts, "_acquire_overpass_payload", lambda *_: (
        {"elements": [{"type": "node", "id": 1515, "tags": {}}]}, "https://overpass.example", []))
    monkeypatch.setattr(facts, "_nominatim_lookup", lambda *_: ({}, "https://nominatim.example/lookup"))
    monkeypatch.setattr(facts, "_official_web_facts", lambda *_, **kw: {
        "status": "ACQUIRED", "source_binding": kw["source_binding"],
        "opening_hours": {"status": "OFFICIAL_WEB_VERIFIED", "open": "10:00", "close": "18:00"},
        "cost_evidence": {"status": "VERIFIED_PROVIDER", "amount_minor": 0, "currency": "JPY"},
    })
    monkeypatch.setattr(facts, "_search_fact_candidates", lambda *_, **kw: {"status": "UNCONFIGURED"})
    with SessionLocal() as session:
        place = Place(id=uuid4().hex, provider_key="overpass", external_id="overpass:node/1515",
            city_code=city, name="Museum", category="museum", latitude=1, longitude=2,
            opening_hours_json='{"status":"UNKNOWN"}', tags_json="[]",
            metadata_json=json.dumps({"fact_source_binding": binding}), updated_at="2026-10-03")
        session.add(place)
        session.flush()
        receipt = facts.acquire_place_facts(session, SimpleNamespace(city_code=city, id=uuid4().hex, start_at="2026-10-08"),
            source_bindings={place.id: {"source_url": "https://unverified.example/guess"}}, binding_origin="agent")
        assert receipt["places"][0]["source_binding"] == binding
        assert receipt["known_opening_count"] == 1
        assert receipt["known_cost_count"] == 1
        assert json.loads(place.metadata_json)["fact_source_binding"]["approval"] == approval


@pytest.mark.parametrize("action_status,retry", [("UNRESOLVED", True), ("RETRYABLE_FAILURE", True), ("EXECUTED", False), ("NO_ACTION", False)])
def test_guardian_unresolved_retry_does_not_erase_completed_idempotency(action_status, retry):
    now = datetime.now(timezone.utc)
    prior = GuardianRun(action_status=action_status, cooldown_until=(now + timedelta(minutes=10)).isoformat())
    session = SimpleNamespace(scalar=lambda *_: prior)
    result = _cooldown_active(session, journey_id=uuid4().hex, evidence_fingerprint="test", now=now)
    assert (result is None) == retry
