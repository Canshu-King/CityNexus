from __future__ import annotations

# PROPOSED R6.3 RED.
# Provider/catalogue template candidates should derive budget_fit from known
# candidate cost and Journey budget, not inherit frozen fixture scores.

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.db.models import Place, PlanVersion
from app.db.session import SessionLocal
from app.main import app

client=TestClient(app)


def _place(pid: str, city: str, amount: int, lat: float) -> Place:
    now=datetime.now(timezone.utc).isoformat()
    return Place(
        id=pid,
        provider_key="r63-synthetic-diagnostic",
        external_id=f"r63:{pid}",
        city_code=city,
        name=pid,
        category="park",
        latitude=lat,
        longitude=98.66,
        opening_hours_json=json.dumps({"status":"NORMALIZED","open":"09:00","close":"18:00"}),
        tags_json=json.dumps(["SYNTHETIC_DIAGNOSTIC_FIXTURE"]),
        metadata_json=json.dumps({
            "duration_min":60,
            "cost_minor":amount,
            "price_known":True,
            "cost_evidence":{"status":"KNOWN","amount_minor":amount,"currency":"CNY","source":"R63_BUDGET_CONTROL"},
        }),
        updated_at=now,
    )


def test_dynamic_catalogue_budget_fit_is_cost_derived() -> None:
    client.post("/api/v1/demo/reset").raise_for_status()
    city="R63-DYNAMIC-BUDGET"
    traveler=client.post("/api/v1/travelers",json={"display_name":"R63 budget","locale":"zh-CN","timezone":"Asia/Shanghai"})
    traveler.raise_for_status()
    journey=client.post("/api/v1/journeys",json={
        "traveler_id":traveler.json()["id"],
        "title":"R63 budget truth",
        "city_code":city,
        "timezone":"Asia/Shanghai",
        "start_at":"2026-10-02T09:00:00+08:00",
        "end_at":"2026-10-02T20:00:00+08:00",
        "party_size":1,
        "budget":{"amount_minor":10000,"currency":"CNY"},
    })
    journey.raise_for_status()
    jid=journey.json()["id"]
    with SessionLocal() as s:
        s.add_all([_place("r63-budget-a",city,2000,27.740),_place("r63-budget-b",city,3000,27.741)])
        s.commit()

    generated=client.post(f"/api/v1/journeys/{jid}/plans/generate",json={"candidate_count":1})
    assert generated.status_code==201,generated.text
    plan_id=generated.json()[0]["id"]
    with SessionLocal() as s:
        plan=s.get(PlanVersion,plan_id)
        assert plan is not None
        score=json.loads(plan.score_breakdown_json or "{}")
    assert plan.total_cost_minor==5000
    assert score["budget_fit"]==pytest.approx(0.5)
