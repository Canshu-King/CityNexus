from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.execution import bootstrap_discovery as discovery


def _photon_candidate(
    *,
    opening_status: str = "UNKNOWN",
    cost_status: str = "UNKNOWN",
) -> SimpleNamespace:
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    scope = {
        "member_id": "member-photon-draft",
        "traveler_id": "traveler-photon-draft",
        "receipt_id": "receipt-photon-draft",
        "source_kind": "MANUAL_PUBLIC_CENTER",
        "distance_m": 84.0,
        "expires_at": expires_at,
        "provider_provenance": "LIVE_PROVIDER",
        "observed_name": "Photon public gallery",
        "observed_category": "gallery",
        "latitude": 31.2304,
        "longitude": 121.4737,
        "captured_at": "2026-10-17T08:00:00+00:00",
        "opening_hours": {"status": opening_status},
        "cost_evidence": {"status": cost_status},
        "osm_tags": {"name": "Photon public gallery", "tourism": "gallery"},
        "public_access_state": "PUBLIC_ACCESS_UNVERIFIED",
        "source_url": "https://www.openstreetmap.org/way/8123",
    }
    return SimpleNamespace(
        id="candidate-photon-draft",
        provider_key="photon",
        external_id="photon:way/8123",
        journey_id="journey-photon-draft",
        city_code="CN-PHOTON-DRAFT",
        name="Photon public gallery",
        category="gallery",
        latitude=31.2304,
        longitude=121.4737,
        tags_json=json.dumps(["gallery"]),
        opening_hours_json=json.dumps({"status": opening_status}),
        metadata_json=json.dumps(
            {
                "osm_tags": scope["osm_tags"],
                "cost_evidence": {"status": cost_status},
            }
        ),
        captured_at="2026-10-17T08:00:00+00:00",
        expires_at=expires_at,
        distance_m=84.0,
        evidence_json=json.dumps(
            {
                "bootstrap": True,
                "osm_type": "way",
                "osm_id": "8123",
                "bootstrap_scopes": [scope],
            }
        ),
        materialized_place_id=None,
        status="BOOTSTRAP_PRIVATE",
    )


def test_unknown_photon_facts_stay_draft_explorable_with_source_and_distance():
    candidate = _photon_candidate()

    payload = discovery._candidate_payload(
        candidate,
        member_id="member-photon-draft",
        traveler_id="traveler-photon-draft",
    )

    assert payload["provider_key"] == "photon"
    assert payload["external_id"] == "photon:way/8123"
    assert payload["osm_id"] == "8123"
    assert payload["source_url"] == "https://www.openstreetmap.org/way/8123"
    assert payload["source_attribution"] == "© OpenStreetMap contributors"
    assert payload["source_attribution_url"] == "https://www.openstreetmap.org/copyright"
    assert payload["category"] == "gallery"
    assert payload["distance_m"] == 84.0
    assert payload["opening_state"] == "UNKNOWN"
    assert payload["price_state"] == "UNKNOWN"
    assert payload["selection_state"] != "READY_FOR_NATIVE_PLAN"
    assert payload["selection_blockers"] == ["OPENING_UNVERIFIED", "COST_UNKNOWN"]
    assert payload["draft_exploration"] == {
        "state": "DRAFT_EXPLORE_ONLY",
        "viewable": True,
        "pocket_walk_eligible": True,
        "formal_selection_eligible": False,
        "plan_version_id": None,
        "selected_place_id": None,
    }


def test_unknown_photon_cost_cannot_materialize_formal_candidate():
    candidate = _photon_candidate(opening_status="VERIFIED_PROVIDER")
    session = MagicMock()
    session.scalar.side_effect = [None, candidate]

    with pytest.raises(discovery.BootstrapDiscoveryError) as exc:
        discovery.select_bootstrap_candidate(
            session,
            SimpleNamespace(status="DRAFT", active_plan_version_id=None, id="journey-photon-draft"),
            member=SimpleNamespace(id="member-photon-draft"),
            traveler_id="traveler-photon-draft",
            receipt_id="receipt-photon-draft",
            candidate_id="candidate-photon-draft",
        )

    assert exc.value.code == "BOOTSTRAP_COST_UNVERIFIED"
    assert exc.value.details["price_state"] == "UNKNOWN"
    assert exc.value.details["explore_state"] == "DRAFT_EXPLORE_ONLY"
    session.execute.assert_not_called()
    session.add.assert_not_called()
