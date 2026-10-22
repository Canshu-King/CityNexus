"""Signed, isolated API coverage for the mobile plan workbench; no provider calls."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
import app.traveler_principal as principal_module
from app.core.config import settings
from app.db.models import PlanVersion
from app.db.session import SessionLocal


@pytest.fixture
def _signed_auth():
    previous = settings.traveler_auth_secret
    object.__setattr__(settings, "traveler_auth_secret", uuid4().hex + uuid4().hex)
    try:
        yield
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous)


def test_mobile_plan_list_is_member_bound_and_not_cached(monkeypatch, _signed_auth):
    with TestClient(main_module.app) as client:
        def traveler(label):
            response = client.post("/api/v1/travelers", json={
                "display_name": label, "locale": "zh-CN", "timezone": "Asia/Shanghai",
            })
            assert response.status_code == 201, response.text
            record = response.json()
            return record, {"Authorization": f"Bearer {record['access_token']}"}

        owner, owner_headers = traveler("TEST_FIXTURE plan owner")
        _outsider, outsider_headers = traveler("TEST_FIXTURE plan outsider")
        response = client.post("/api/v1/journeys", headers=owner_headers, json={
            "traveler_id": owner["id"], "title": "TEST_FIXTURE mobile plan",
            "city_code": f"TEST-MOBILE-PLAN-{uuid4().hex[:8]}", "timezone": "Asia/Shanghai",
            "start_at": "2026-11-01T09:00:00+08:00", "end_at": "2026-11-03T18:00:00+08:00",
            "budget": {"amount_minor": 50000, "currency": "CNY"},
        })
        assert response.status_code == 201, response.text
        journey_id = response.json()["id"]
        plan_id = str(uuid4())
        with SessionLocal() as session:
            session.add(PlanVersion(
                id=plan_id, journey_id=journey_id, version_no=1, planning_mode="balanced",
                status="CANDIDATE", source="MANUAL", total_cost_minor=0, currency="CNY",
                estimated_duration_min=0, explanation_json='{"source":"TEST_FIXTURE"}',
                created_at=datetime.now(timezone.utc).isoformat(),
            ))
            session.commit()

        path = f"/api/v1/journeys/{journey_id}/plans"
        assert client.get(path).status_code == 401
        denied = client.get(path, headers=outsider_headers)
        assert denied.status_code == 403
        assert plan_id not in denied.text
        allowed = client.get(path, headers=owner_headers)
        assert allowed.status_code == 200, allowed.text
        assert allowed.json()[0]["id"] == plan_id
        assert allowed.json()[0]["is_current"] is False
        assert "no-store" in allowed.headers["cache-control"]
        assert "Authorization" in allowed.headers["vary"]
        monkeypatch.setattr(principal_module, "member_has_capability", lambda *_args: False)
        assert client.get(path, headers=owner_headers).status_code == 403
