from __future__ import annotations

from uuid import uuid4

from app.core.config import settings
from test_bootstrap_filter_summary_route import (
    TEST_SECRET,
    _new_journey,
    _new_traveler,
    client as TEST_CLIENT,
)


def test_signed_draft_bootstrap_shortlist_read_sets_private_cache_headers():
    previous_secret = settings.traveler_auth_secret
    try:
        object.__setattr__(settings, "traveler_auth_secret", TEST_SECRET)
        suffix = uuid4().hex
        traveler = _new_traveler(f"Pocket cache headers {suffix}")
        journey = _new_journey(traveler["id"], suffix)
        assert journey["status"] == "DRAFT"

        response = TEST_CLIENT.get(
            f"/api/v1/journeys/{journey['id']}/bootstrap-shortlist",
            headers={"Authorization": f"Bearer {traveler['access_token']}"},
        )

        assert response.status_code == 200, response.text
        assert response.headers.get("cache-control") == "private, no-store, max-age=0"
        vary = {
            value.strip().casefold()
            for value in response.headers.get("vary", "").split(",")
        }
        assert {"authorization", "x-citynexus-traveler-token"} <= vary
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)
