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


def test_single_photon_candidate_returns_partial_live_result_without_fabricating_another(monkeypatch):
    provider_candidate = discovery.DiscoveryCandidate(
        provider_key="photon",
        external_id="photon:way/8123",
        name="Photon public gallery",
        category="gallery",
        latitude=31.2304,
        longitude=121.4737,
        tags=("gallery",),
        opening_hours={"status": "UNKNOWN"},
        metadata={"tags": {"name": "Photon public gallery", "tourism": "gallery"}},
        distance_m=84.0,
        cost_evidence={"status": "UNKNOWN"},
    )

    class _PhotonFixture:
        # This local fake covers the LIVE_RESULTS response contract only.
        base_url = "http://127.0.0.1:8765"
        closed = False

        def search_with_evidence(self, *_args, **kwargs):
            assert kwargs["max_attempts"] == 1
            return [provider_candidate], [
                {
                    "endpoint": f"{self.base_url}/reverse",
                    "answered": True,
                    "http_status": 200,
                    "features": 1,
                }
            ]

        def close(self):
            self.closed = True

    provider = _PhotonFixture()
    session = MagicMock()
    session.scalar.return_value = None
    private_rows_query = MagicMock()
    private_rows_query.all.return_value = []
    result_rows_query = MagicMock()
    result_rows_query.all.side_effect = lambda: [
        call.args[0]
        for call in session.add.call_args_list
        if isinstance(call.args[0], discovery.RealPlaceCandidate)
    ]
    session.scalars.side_effect = [private_rows_query, result_rows_query]
    monkeypatch.setattr(
        discovery,
        "_bootstrap_discovery_provider_config",
        lambda: {
            "provider": "photon",
            "provider_name": "Photon POI search",
            "expected_recipient": "Photon by Komoot public geocoding service",
            "base_url": provider.base_url,
        },
    )
    monkeypatch.setattr(
        discovery,
        "bootstrap_discovery_readiness",
        lambda **_kwargs: {
            "provider": "photon",
            "provider_name": "Photon POI search",
            "expected_recipient": "Photon by Komoot public geocoding service",
            "external_request_allowed": True,
            "test_only": True,
            "capability_state": "TEST_ONLY",
            "status": "READY",
            "reason_code": "READY",
            "provider_grade": "TEST_PROVIDER",
        },
    )
    monkeypatch.setattr(
        discovery, "_bootstrap_live_endpoint_block_reason", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        discovery, "_bootstrap_rate_limited", lambda *_args, **_kwargs: False
    )
    monkeypatch.setattr(discovery, "PhotonPOIProvider", lambda **_kwargs: provider)

    result = discovery.discover_bootstrap_candidates(
        session,
        SimpleNamespace(
            id="journey-photon-draft",
            status="DRAFT",
            active_plan_version_id=None,
            city_code="CN-PHOTON-DRAFT",
        ),
        member=SimpleNamespace(id="member-photon-draft"),
        traveler_id="traveler-photon-draft",
        query="public gallery",
        radius_m=2500,
        limit=10,
        source_kind="MANUAL_PUBLIC_CENTER",
        provider_consent=True,
        consented_provider="photon",
        latitude=31.2304,
        longitude=121.4737,
        accuracy_m=None,
    )

    private_candidate_rows = [
        call.args[0]
        for call in session.add.call_args_list
        if isinstance(call.args[0], discovery.RealPlaceCandidate)
    ]
    assert result["status"] == "LIVE_RESULTS"
    assert result["result_state"] == "PARTIAL_1"
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["external_id"] == "photon:way/8123"
    assert (
        result["candidates"][0]["draft_exploration"]["state"]
        == "DRAFT_EXPLORE_ONLY"
    )
    assert result["filter_summary"]["accepted_count"] == 1
    assert len(private_candidate_rows) == 1
    assert private_candidate_rows[0].status == "BOOTSTRAP_PRIVATE"
    assert provider.closed is True
