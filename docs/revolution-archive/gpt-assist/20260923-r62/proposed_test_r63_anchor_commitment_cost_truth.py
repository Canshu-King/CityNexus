from __future__ import annotations

# PROPOSED R6.3 RED TESTS.
# Copy/adapt into the exact R6.3 Lab worktree only after freezing fe3369f.
# Purpose: prove that C4 anchor money comes from Commitment, not Place fallback
# or a literal zero.

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.models import Activity, Commitment, PlanVersion, Place
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def _journey(city: str) -> str:
    traveler = client.post("/api/v1/travelers", json={
        "display_name": "R63 anchor truth",
        "locale": "zh-CN",
        "timezone": "Asia/Shanghai",
    })
    traveler.raise_for_status()
    res = client.post("/api/v1/journeys", json={
        "traveler_id": traveler.json()["id"],
        "title": "R63 anchor truth",
        "city_code": city,
        "timezone": "Asia/Shanghai",
        "start_at": "2026-10-02T09:00:00+08:00",
        "end_at": "2026-10-02T20:00:00+08:00",
        "party_size": 1,
        "budget": {"amount_minor": 100000, "currency": "CNY"},
    })
    res.raise_for_status()
    return res.json()["id"]


def _place(pid: str, city: str, amount: int, lat: float) -> Place:
    now = datetime.now(timezone.utc).isoformat()
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
            "cost_evidence":{"status":"KNOWN","amount_minor":amount,"currency":"CNY","source":"R63_PLACE_CONTROL"},
        }),
        updated_at=now,
    )


def _commit(journey_id: str, place_id: str, *, amount: int, status: str, currency: str="CNY") -> str:
    cid=str(uuid4())
    now=datetime.now(timezone.utc).isoformat()
    with SessionLocal() as s:
        s.add(Commitment(
            id=cid,
            journey_id=journey_id,
            activity_id=None,
            kind="BOOKING",
            level="C4_Anchored",
            status="ACTIVE",
            monetary_value_minor=amount,
            monetary_value_status=status,
            currency=currency,
            external_ref=f"R63-{cid}",
            policy_json=json.dumps({
                "anchor_role":"MID_TRIP",
                "semantic_key":place_id,
                "scheduled_start_at":"2026-10-02T14:00:00+08:00",
                "source":"SYNTHETIC_DIAGNOSTIC_FIXTURE",
            }),
            created_at=now,
            updated_at=now,
        ))
        s.commit()
    return cid


def _counts(journey_id: str) -> tuple[int,int]:
    with SessionLocal() as s:
        plans=int(s.scalar(select(func.count()).select_from(PlanVersion).where(PlanVersion.journey_id==journey_id)) or 0)
        acts=int(s.scalar(select(func.count()).select_from(Activity).join(PlanVersion, Activity.plan_version_id==PlanVersion.id).where(PlanVersion.journey_id==journey_id)) or 0)
    return plans,acts


def test_known_paid_commitment_amount_is_not_forced_to_zero_in_explicit_compose() -> None:
    client.post("/api/v1/demo/reset").raise_for_status()
    city="R63-KNOWN-ANCHOR"
    jid=_journey(city)
    anchor="r63-anchor"
    with SessionLocal() as s:
        s.add_all([
            _place("r63-a",city,1000,27.740),
            _place("r63-b",city,1000,27.741),
            _place(anchor,city,0,27.742),  # catalogue says free; Commitment says 2500
        ])
        s.commit()
    cid=_commit(jid,anchor,amount=2500,status="KNOWN")

    res=client.post(f"/api/v1/journeys/{jid}/plans/generate",json={"candidate_count":1,"place_ids":["r63-a","r63-b"]})
    assert res.status_code==201,res.text
    plan_id=res.json()[0]["id"]
    with SessionLocal() as s:
        plan=s.get(PlanVersion,plan_id)
        acts=list(s.scalars(select(Activity).where(Activity.plan_version_id==plan_id)).all())
        a=next(x for x in acts if x.place_id==anchor)
        md=json.loads(a.metadata_json or "{}")
    assert a.estimated_cost_minor==2500
    assert plan is not None and plan.total_cost_minor==4500
    assert md["price_known"] is True
    assert md["cost_evidence"]["amount_minor"]==2500
    assert md["cost_evidence"]["source"]=="COMMITMENT"
    assert md["cost_evidence"]["commitment_id"]==cid


def test_unknown_commitment_amount_fails_closed_without_plan_persistence() -> None:
    client.post("/api/v1/demo/reset").raise_for_status()
    city="R63-UNKNOWN-ANCHOR"
    jid=_journey(city)
    anchor="r63-anchor-unknown"
    with SessionLocal() as s:
        s.add_all([
            _place("r63-a",city,1000,27.740),
            _place("r63-b",city,1000,27.741),
            _place(anchor,city,9999,27.742),  # public price must not replace booking amount
        ])
        s.commit()
    cid=_commit(jid,anchor,amount=0,status="UNKNOWN")

    res=client.post(f"/api/v1/journeys/{jid}/plans/generate",json={"candidate_count":1,"place_ids":["r63-a","r63-b"]})
    assert res.status_code==422,res.text
    assert res.json()["error"]["reason_code"]=="COMMITMENT_COST_UNVERIFIED"
    assert _counts(jid)==(0,0)
    with SessionLocal() as s:
        c=s.get(Commitment,cid)
        assert c is not None and c.status=="ACTIVE" and c.monetary_value_status=="UNKNOWN"


def test_commitment_currency_is_not_silently_relabelled() -> None:
    client.post("/api/v1/demo/reset").raise_for_status()
    city="R63-CURRENCY-ANCHOR"
    jid=_journey(city)
    anchor="r63-anchor-usd"
    with SessionLocal() as s:
        s.add_all([
            _place("r63-a",city,1000,27.740),
            _place("r63-b",city,1000,27.741),
            _place(anchor,city,0,27.742),
        ])
        s.commit()
    _commit(jid,anchor,amount=2500,status="KNOWN",currency="USD")
    res=client.post(f"/api/v1/journeys/{jid}/plans/generate",json={"candidate_count":1,"place_ids":["r63-a","r63-b"]})
    assert res.status_code==422,res.text
    assert res.json()["error"]["reason_code"]=="COMMITMENT_CURRENCY_MISMATCH"
    assert _counts(jid)==(0,0)
