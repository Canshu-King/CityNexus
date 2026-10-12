from __future__ import annotations
from types import SimpleNamespace
import pytest
from app.integrations.discovery.real_city import _place_metadata

@pytest.mark.parametrize("status", ["KNOWN","VERIFIED_OFFICIAL_WEB","OFFICIAL_WEB_VERIFIED","VERIFIED_PROVIDER"])
def test_verified_zero_cost_remains_known_free(status: str) -> None:
    metadata = _place_metadata(
        SimpleNamespace(metadata={"osm_id":"node/r62-free"}),
        "live",
        {"status":status,"amount_minor":0,"currency":"CNY","source":"r62"},
        {},
    )
    assert metadata["cost_minor"] == 0
    assert metadata["price_known"] is True
    assert metadata["cost_evidence"]["status"] == status

def test_unknown_evidence_clears_stale_compatibility_cost() -> None:
    metadata = _place_metadata(
        SimpleNamespace(metadata={"osm_id":"node/r62-stale","cost_minor":2500,"price_known":True}),
        "live",
        {"status":"UNKNOWN","amount_minor":None,"currency":"CNY","source":"r62"},
        {},
    )
    assert metadata["cost_evidence"]["status"] == "UNKNOWN"
    assert metadata["price_known"] is False
    assert metadata["cost_minor"] == 0
