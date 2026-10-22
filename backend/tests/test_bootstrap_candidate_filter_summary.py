from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.db.models import ProviderCall
from app.execution import bootstrap_discovery as discovery


_FILTER_REASONS = (
    "provider_mismatch",
    "invalid_identity",
    "missing_name",
    "invalid_coordinates",
    "invalid_distance",
    "out_of_radius",
    "restricted_access",
    "duplicate",
)


def _candidate(
    *,
    provider_key: str = "photon",
    external_id: str = "photon:node/1",
    name: str = "Fixture place",
    latitude: float = 31.2,
    longitude: float = 121.4,
    distance_m=25,
    tags: dict[str, str] | None = None,
):
    candidate_tags = tags if tags is not None else ({"name": name} if name else {})
    return SimpleNamespace(
        provider_key=provider_key,
        external_id=external_id,
        name=name,
        category="public_place",
        latitude=latitude,
        longitude=longitude,
        distance_m=distance_m,
        metadata={"tags": candidate_tags},
        tags=list(candidate_tags),
        opening_hours={"status": "UNKNOWN"},
        cost_evidence={"status": "UNKNOWN"},
    )


def test_http_200_zero_results_returns_count_only_summary_and_provider_call(monkeypatch):
    raw_candidates = [
        _candidate(provider_key="overpass", external_id="overpass:node/2"),
        _candidate(external_id="photon:node/not-a-number"),
        _candidate(external_id="photon:node/3", name="", tags={}),
        _candidate(external_id="photon:node/4", latitude=float("nan")),
        _candidate(external_id="photon:node/5", distance_m="not-a-distance"),
        _candidate(external_id="photon:node/6", distance_m=3000),
        _candidate(
            external_id="photon:node/7",
            name="Restricted fixture place",
            tags={"name": "Restricted fixture place", "access": "private"},
        ),
    ]

    class _PhotonFixture:
        base_url = "https://photon.komoot.io"
        closed = False

        def search_with_evidence(self, *_args, **kwargs):
            assert kwargs["max_attempts"] == 1
            return raw_candidates, [
                {
                    "endpoint": "https://photon.komoot.io/api",
                    "answered": True,
                    "http_status": 200,
                    "features": len(raw_candidates),
                    "private_detail": "provider-only fixture data",
                }
            ]

        def close(self):
            self.closed = True

    provider = _PhotonFixture()
    session = MagicMock()
    session.scalar.return_value = None
    session.scalars.return_value.all.return_value = []
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
            "test_only": False,
            "capability_state": "LIVE_CAPABLE",
            "status": "READY",
            "reason_code": "READY",
            "provider_grade": "LIVE_CAPABLE",
        },
    )
    monkeypatch.setattr(
        discovery, "_bootstrap_live_endpoint_block_reason", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(discovery, "_bootstrap_rate_limited", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(discovery, "PhotonPOIProvider", lambda **_kwargs: provider)

    result = discovery.discover_bootstrap_candidates(
        session,
        SimpleNamespace(
            id="journey-filter-summary",
            status="DRAFT",
            active_plan_version_id=None,
            city_code="TST",
        ),
        member=SimpleNamespace(id="member-filter-summary"),
        traveler_id="traveler-filter-summary",
        query="public places",
        radius_m=2500,
        limit=10,
        source_kind="MANUAL_PUBLIC_CENTER",
        provider_consent=True,
        consented_provider="photon",
        latitude=31.2,
        longitude=121.4,
        accuracy_m=None,
    )

    expected = {
        "raw_count": 7,
        "accepted_count": 0,
        "rejected_by_reason": {
            "provider_mismatch": 1,
            "invalid_identity": 1,
            "missing_name": 1,
            "invalid_coordinates": 1,
            "invalid_distance": 1,
            "out_of_radius": 1,
            "restricted_access": 1,
            "duplicate": 0,
        },
    }
    assert result["status"] == "LIVE_ZERO_RESULTS"
    assert result["candidates"] == []
    assert result["filter_summary"] == expected
    assert provider.closed is True
    assert set(result["filter_summary"]) == {
        "raw_count",
        "accepted_count",
        "rejected_by_reason",
    }
    count_values = [
        result["filter_summary"]["raw_count"],
        result["filter_summary"]["accepted_count"],
        *result["filter_summary"]["rejected_by_reason"].values(),
    ]
    assert all(type(value) is int and value >= 0 for value in count_values)
    summary_json = json.dumps(result["filter_summary"])
    for private_value in ("Restricted fixture place", "31.2", "121.4", "private"):
        assert private_value not in summary_json

    provider_calls = [
        call.args[0]
        for call in session.add.call_args_list
        if call.args and isinstance(call.args[0], ProviderCall)
    ]
    assert len(provider_calls) == 1
    stored_response = json.loads(provider_calls[0].response_json)
    assert stored_response["filter_summary"] == expected
    assert stored_response["status"] == "LIVE_ZERO_RESULTS"
    assert "private_detail" not in stored_response["attempts"][0]
    assert "Restricted fixture place" not in provider_calls[0].response_json


def test_filter_summary_counts_duplicates_after_candidate_gates():
    candidate = _candidate(
        external_id="photon:node/9",
        name="Private test name",
        latitude=33.3,
        longitude=117.7,
        tags={"name": "Private test name"},
    )

    summary = discovery._bootstrap_filter_summary(
        [candidate, candidate], provider_key="photon", radius_m=2500
    )

    assert summary == {
        "raw_count": 2,
        "accepted_count": 1,
        "rejected_by_reason": {
            "provider_mismatch": 0,
            "invalid_identity": 0,
            "missing_name": 0,
            "invalid_coordinates": 0,
            "invalid_distance": 0,
            "out_of_radius": 0,
            "restricted_access": 0,
            "duplicate": 1,
        },
    }
    assert set(summary["rejected_by_reason"]) == set(_FILTER_REASONS)
    assert "Private test name" not in json.dumps(summary)
