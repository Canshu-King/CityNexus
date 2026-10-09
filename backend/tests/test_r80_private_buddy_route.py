from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.main as main_module
from app.core.config import settings
from app.db.models import (
    AgentRun,
    AuditLog,
    Event,
    GuardianPulse,
    GuardianRun,
    Journey,
    JourneyOutcomeEvent,
    JourneyRendezvousBuddyHandoff,
    LocationObservation,
    MobilityFact,
    PlanVersion,
    ProviderCall,
    RouteAcquisitionOperation,
)
from app.db.session import SessionLocal
from app.traveler_principal import issue_traveler_token
from demo_stage import demo_reset_headers

client = TestClient(main_module.app)
TEST_SECRET = "r80-private-buddy-route-test-secret-0123456789"


@pytest.fixture(autouse=True)
def _private_route_environment():
    previous_secret = settings.traveler_auth_secret
    previous_provider = settings.live_valhalla_url
    object.__setattr__(settings, "traveler_auth_secret", TEST_SECRET)
    object.__setattr__(settings, "live_valhalla_url", None)
    try:
        yield
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)
        object.__setattr__(settings, "live_valhalla_url", previous_provider)


def _auth(traveler_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_traveler_token(traveler_id)}"}


def _new_traveler(name: str) -> str:
    response = client.post("/api/v1/travelers", json={
        "display_name": name,
        "email": None,
        "locale": "en-US",
        "timezone": "UTC",
    })
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _join(journey_id: str, owner_id: str, traveler_id: str) -> None:
    offer = client.post(
        f"/api/v1/journeys/{journey_id}/membership-invitations",
        headers={**_auth(owner_id), "Idempotency-Key": "r80-invite-" + str(uuid4())},
        json={"target_traveler_id": traveler_id},
    )
    assert offer.status_code == 201, offer.text
    accepted = client.post(
        f"/api/v1/journey-membership-invitations/{offer.json()['invitation_id']}/respond",
        headers=_auth(traveler_id),
        json={"decision": "ACCEPT"},
    )
    assert accepted.status_code == 200, accepted.text


def _accepted_pair() -> tuple[str, str, str, str, str]:
    reset = client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    assert reset.status_code == 200, reset.text
    journey_id = str(reset.json()["journey_id"])
    helper_id = str(reset.json()["traveler_id"])
    plan = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 1}
    )
    assert plan.status_code == 201, plan.text
    assert client.post(
        f"/api/v1/journeys/{journey_id}/plans/{plan.json()[0]['id']}/select",
        headers=_auth(helper_id),
    ).status_code == 200
    assert client.post(
        f"/api/v1/journeys/{journey_id}/start", headers=_auth(helper_id)
    ).status_code == 200

    bystander_id = _new_traveler("R80 bystander")
    requester_id = _new_traveler("R80 requester")
    _join(journey_id, helper_id, bystander_id)
    _join(journey_id, helper_id, requester_id)

    presence_response = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(requester_id)
    )
    assert presence_response.status_code == 200, presence_response.text
    presence = presence_response.json()["group_presence"]
    target = presence["rendezvous"]
    audience = sorted(member["member_id"] for member in presence["members"])
    audience_sha = hashlib.sha256(json.dumps(audience, separators=(",", ":")).encode()).hexdigest()
    signal = client.post(
        f"/api/v1/journeys/{journey_id}/rendezvous-member-signals",
        headers={**_auth(requester_id), "Idempotency-Key": "r80-help-" + str(uuid4())},
        json={
            "signal_kind": "NEEDS_COORDINATION",
            "expected_active_plan_version_id": presence["active_plan_version_id"],
            "expected_current_activity_id": presence["current_activity_id"],
            "expected_rendezvous_activity_id": target["activity_id"],
            "expected_public_place_id": target["place_id"],
            "expected_audience_sha256": audience_sha,
        },
    )
    assert signal.status_code == 201, signal.text
    signal_id = str(signal.json()["signal_id"])
    acknowledgement = client.post(
        f"/api/v1/journeys/{journey_id}/rendezvous-member-signals/{signal_id}/acknowledge",
        headers=_auth(helper_id),
    )
    assert acknowledgement.status_code == 200, acknowledgement.text
    candidates_response = client.get(
        f"/api/v1/journeys/{journey_id}/rendezvous-buddy-handoffs/candidates?signal_id={signal_id}",
        headers=_auth(helper_id),
    )
    assert candidates_response.status_code == 200, candidates_response.text
    candidates = candidates_response.json()
    selected = candidates["items"][-1]
    handoff = client.post(
        f"/api/v1/journeys/{journey_id}/rendezvous-buddy-handoffs",
        headers={**_auth(helper_id), "Idempotency-Key": "r80-offer-" + str(uuid4())},
        json={
            "help_signal_id": signal_id,
            "expected_active_plan_version_id": candidates["active_plan_version_id"],
            "expected_current_activity_id": candidates["current_activity_id"],
            "expected_rendezvous_activity_id": candidates["rendezvous_activity_id"],
            "expected_original_public_place_id": candidates["original_public_place_id"],
            "expected_audience_sha256": candidates["audience_sha256"],
            "handoff_place_id": selected["place_id"],
        },
    )
    assert handoff.status_code == 201, handoff.text
    handoff_id = str(handoff.json()["handoff_id"])
    accepted = client.post(
        f"/api/v1/journeys/{journey_id}/rendezvous-buddy-handoffs/{handoff_id}/respond",
        headers=_auth(requester_id),
        json={"decision": "ACCEPT"},
    )
    assert accepted.status_code == 200, accepted.text
    return journey_id, helper_id, bystander_id, requester_id, handoff_id


def _observation(journey_id: str, traveler_id: str, handoff_id: str, latitude: float) -> str:
    response = client.post(
        f"/api/v1/journeys/{journey_id}/rendezvous-buddy-handoffs/{handoff_id}/route/location",
        headers=_auth(traveler_id),
        json={
            "latitude": latitude,
            "longitude": 116.4074,
            "accuracy_m": 12,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["principal_bound"] is True
    assert response.json()["visibility"] == "CALLER_PRIVATE"
    assert response.json()["external_provider_contacted"] is False
    assert str(latitude) not in response.text
    return str(response.json()["location_observation_id"])


def _count(model) -> int:
    with SessionLocal() as session:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _matching_paths(value, needle: str, path: str = "$") -> list[str]:
    if isinstance(value, dict):
        return [match for key, item in value.items() for match in _matching_paths(item, needle, f"{path}.{key}")]
    if isinstance(value, list):
        return [match for index, item in enumerate(value) for match in _matching_paths(item, needle, f"{path}[{index}]")]
    return [path] if isinstance(value, str) and needle in value else []


def test_r80_private_routes_are_separate_consented_member_bound_and_hidden_from_bystander():
    journey_id, helper_id, bystander_id, requester_id, handoff_id = _accepted_pair()
    handoff_path = f"/api/v1/journeys/{journey_id}/rendezvous-buddy-handoffs/{handoff_id}"
    helper_current = client.get(handoff_path + "/route/current", headers=_auth(helper_id))
    requester_current = client.get(handoff_path + "/route/current", headers=_auth(requester_id))
    bystander_current = client.get(handoff_path + "/route/current", headers=_auth(bystander_id))
    assert helper_current.status_code == 200, helper_current.text
    assert requester_current.status_code == 200, requester_current.text
    assert helper_current.json()["status"] == "NOT_REQUESTED"
    assert requester_current.json()["status"] == "NOT_REQUESTED"
    assert bystander_current.status_code == 403

    baseline = {
        "observations": _count(LocationObservation),
        "operations": _count(RouteAcquisitionOperation),
        "provider_calls": _count(ProviderCall),
        "plans": _count(PlanVersion),
        "mobility_facts": _count(MobilityFact),
        "agents": _count(AgentRun),
        "guardians": _count(GuardianRun),
        "pulses": _count(GuardianPulse),
        "events": _count(Event),
        "outcomes": _count(JourneyOutcomeEvent),
    }
    assert baseline["observations"] >= 0
    assert baseline["operations"] >= 0

    # The R79 acceptance itself did not capture location or begin a route.
    assert client.get(handoff_path + "/route/current", headers=_auth(helper_id)).json()["status"] == "NOT_REQUESTED"
    assert _count(LocationObservation) == baseline["observations"]
    bystander_capture = client.post(
        handoff_path + "/route/location",
        headers=_auth(bystander_id),
        json={
            "latitude": 35.6762,
            "longitude": 139.6503,
            "accuracy_m": 20,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert bystander_capture.status_code == 403
    assert _count(LocationObservation) == baseline["observations"]

    helper_observation = _observation(journey_id, helper_id, handoff_id, 39.9042)
    assert _count(LocationObservation) == baseline["observations"] + 1
    assert _count(RouteAcquisitionOperation) == baseline["operations"]
    assert client.get(handoff_path + "/route/current", headers=_auth(helper_id)).json()["status"] == "NOT_REQUESTED"
    no_disclosure = client.post(
        handoff_path + "/route",
        headers=_auth(helper_id),
        json={
            "location_observation_id": helper_observation,
            "requested_mode": "WALK",
            "external_provider_disclosure_confirmed": False,
        },
    )
    assert no_disclosure.status_code == 400
    assert _count(RouteAcquisitionOperation) == baseline["operations"]
    assert _count(ProviderCall) == baseline["provider_calls"]

    helper_route = client.post(
        handoff_path + "/route",
        headers=_auth(helper_id),
        json={
            "location_observation_id": helper_observation,
            "requested_mode": "WALK",
            "external_provider_disclosure_confirmed": True,
        },
    )
    assert helper_route.status_code == 200, helper_route.text
    helper_result = helper_route.json()
    assert helper_result["route_state"] == "UNKNOWN"
    assert helper_result["status"] == "UNAVAILABLE"
    assert helper_result["duration_min"] is None
    assert helper_result["provider"] is None
    assert helper_result["shared_plan_changed"] is False
    assert helper_result["physical_arrival_verified"] is False
    assert helper_result["guardian_triggered"] is False
    assert helper_observation not in json.dumps(helper_result)
    assert _count(RouteAcquisitionOperation) == baseline["operations"] + 1
    assert _count(ProviderCall) == baseline["provider_calls"]
    assert _count(MobilityFact) == baseline["mobility_facts"]
    generic_route = client.post(
        f"/api/v1/journeys/{journey_id}/group-presence/route",
        headers=_auth(helper_id),
        json={"location_observation_id": helper_observation, "requested_mode": "WALK"},
    )
    assert generic_route.status_code == 409
    assert _count(RouteAcquisitionOperation) == baseline["operations"] + 1
    assert _count(ProviderCall) == baseline["provider_calls"]

    helper_operation = None
    with SessionLocal() as session:
        operations = session.scalars(select(RouteAcquisitionOperation).where(
            RouteAcquisitionOperation.journey_id == journey_id,
            RouteAcquisitionOperation.target_key != "",
        )).all()
        private = [row for row in operations if "R80_PRIVATE_BUDDY_HANDOFF" in row.request_json]
        assert len(private) == 1
        helper_operation = private[0]
        request_json = json.loads(helper_operation.request_json)
        evidence = request_json["origin_evidence"]
        assert evidence["journey_member_id"] == session.scalar(select(LocationObservation.journey_member_id).where(
            LocationObservation.id == helper_observation
        ))
        assert evidence["traveler_id"] == helper_id
        assert evidence["handoff_id"] == handoff_id
        assert helper_observation in helper_operation.request_json
        assert "39.9042" not in helper_operation.request_json
        assert "116.4074" not in helper_operation.request_json
        audit_after_json = json.dumps([
            row.after_json for row in session.scalars(select(AuditLog)).all()
        ])
        assert helper_observation not in audit_after_json

    # The legacy operation read endpoint must authenticate and sanitize private rows.
    bystander_operation = client.get(
        f"/api/v1/journeys/{journey_id}/routes/operations/{helper_operation.id}",
        headers=_auth(bystander_id),
    )
    assert bystander_operation.status_code == 403
    helper_operation_read = client.get(
        f"/api/v1/journeys/{journey_id}/routes/operations/{helper_operation.id}",
        headers=_auth(helper_id),
    )
    assert helper_operation_read.status_code == 200, helper_operation_read.text
    assert "geometry" not in json.dumps(helper_operation_read.json()).lower()
    assert helper_observation not in json.dumps(helper_operation_read.json())

    requester_before = client.get(handoff_path + "/route/current", headers=_auth(requester_id)).json()
    assert requester_before["status"] == "NOT_REQUESTED"
    requester_observation = _observation(journey_id, requester_id, handoff_id, 31.2304)
    replayed_observation = client.post(
        handoff_path + "/route",
        headers=_auth(helper_id),
        json={
            "location_observation_id": requester_observation,
            "requested_mode": "WALK",
            "external_provider_disclosure_confirmed": True,
        },
    )
    assert replayed_observation.status_code == 403
    assert _count(RouteAcquisitionOperation) == baseline["operations"] + 1
    requester_route = client.post(
        handoff_path + "/route",
        headers=_auth(requester_id),
        json={
            "location_observation_id": requester_observation,
            "requested_mode": "WALK",
            "external_provider_disclosure_confirmed": True,
        },
    )
    assert requester_route.status_code == 200, requester_route.text
    assert requester_route.json()["route_state"] == "UNKNOWN"
    assert helper_observation not in json.dumps(requester_route.json())
    assert requester_observation not in json.dumps(requester_route.json())
    assert _count(RouteAcquisitionOperation) == baseline["operations"] + 2
    assert _count(ProviderCall) == baseline["provider_calls"]
    assert _count(PlanVersion) == baseline["plans"]
    assert _count(AgentRun) == baseline["agents"]
    assert _count(GuardianRun) == baseline["guardians"]
    assert _count(GuardianPulse) == baseline["pulses"]
    assert _count(Event) == baseline["events"]
    assert _count(JourneyOutcomeEvent) == baseline["outcomes"]

    bystander_handoffs = client.get(
        f"/api/v1/journeys/{journey_id}/rendezvous-buddy-handoffs/current",
        headers=_auth(bystander_id),
    )
    assert bystander_handoffs.status_code == 200
    assert bystander_handoffs.json() == {"items": []}
    bystander_operator = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(bystander_id)
    )
    assert bystander_operator.status_code == 200
    visible = json.dumps(bystander_operator.json())
    assert handoff_id not in visible
    assert helper_observation not in visible
    assert requester_observation not in visible, _matching_paths(bystander_operator.json(), requester_observation)
    assert str(helper_operation.id) not in visible
    assert "39.9042" not in visible and "31.2304" not in visible
    helper_operator = client.get(
        f"/api/v1/journeys/{journey_id}/operator", headers=_auth(helper_id)
    )
    assert helper_operator.status_code == 200
    helper_projection = json.dumps(helper_operator.json())
    assert helper_observation not in helper_projection
    assert requester_observation not in helper_projection
    assert "39.9042" not in helper_projection and "31.2304" not in helper_projection
    from app.operations.v9 import refresh_offline_snapshot

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        offline = refresh_offline_snapshot(session, journey)
        offline_payload = json.loads(offline.payload_json)
    assert helper_observation not in json.dumps(offline_payload)
    assert requester_observation not in json.dumps(offline_payload)
    assert "39.9042" not in json.dumps(offline_payload)
    assert "31.2304" not in json.dumps(offline_payload)


def test_r80_route_and_legacy_operation_read_fail_closed_after_handoff_revocation():
    journey_id, helper_id, bystander_id, requester_id, handoff_id = _accepted_pair()
    handoff_path = f"/api/v1/journeys/{journey_id}/rendezvous-buddy-handoffs/{handoff_id}"
    observation_id = _observation(journey_id, helper_id, handoff_id, 39.9042)
    route = client.post(
        handoff_path + "/route",
        headers=_auth(helper_id),
        json={
            "location_observation_id": observation_id,
            "requested_mode": "WALK",
            "external_provider_disclosure_confirmed": True,
        },
    )
    assert route.status_code == 200, route.text
    with SessionLocal() as session:
        operation = session.scalar(select(RouteAcquisitionOperation).where(
            RouteAcquisitionOperation.journey_id == journey_id,
            RouteAcquisitionOperation.request_json.like("%R80_PRIVATE_BUDDY_HANDOFF%"),
        ))
        assert operation is not None
        operation_id = str(operation.id)

    revoke = client.post(handoff_path + "/revoke", headers=_auth(requester_id))
    assert revoke.status_code == 200, revoke.text
    assert client.get(handoff_path + "/route/current", headers=_auth(helper_id)).status_code == 409
    assert client.get(
        f"/api/v1/journeys/{journey_id}/routes/operations/{operation_id}",
        headers=_auth(helper_id),
    ).status_code == 409
    assert client.get(
        f"/api/v1/journeys/{journey_id}/routes/operations/{operation_id}",
        headers=_auth(bystander_id),
    ).status_code == 403


def test_r80_replay_is_historical_and_mock_cannot_be_projected_as_live():
    journey_id, helper_id, _bystander_id, _requester_id, handoff_id = _accepted_pair()
    handoff_path = f"/api/v1/journeys/{journey_id}/rendezvous-buddy-handoffs/{handoff_id}"
    observation_id = _observation(journey_id, helper_id, handoff_id, 39.9042)
    route = client.post(
        handoff_path + "/route",
        headers=_auth(helper_id),
        json={
            "location_observation_id": observation_id,
            "requested_mode": "WALK",
            "external_provider_disclosure_confirmed": True,
        },
    )
    assert route.status_code == 200, route.text
    with SessionLocal() as session:
        operation = session.scalar(select(RouteAcquisitionOperation).where(
            RouteAcquisitionOperation.journey_id == journey_id,
            RouteAcquisitionOperation.request_json.like("%R80_PRIVATE_BUDDY_HANDOFF%"),
        ))
        assert operation is not None
        stamp = datetime.now(timezone.utc).isoformat()
        operation.status = "COMPLETED"
        operation.outcome = "ROUTE_READY"
        operation.error_json = "{}"
        operation.result_json = json.dumps({
            "provider": "sealed-route-cache",
            "provenance": "CAPTURED_REPLAY",
            "duration_min": 17,
            "captured_at": stamp,
        })
        session.commit()

    replay = client.get(handoff_path + "/route/current", headers=_auth(helper_id))
    assert replay.status_code == 200, replay.text
    assert replay.json()["route_state"] == "REPLAY"
    assert replay.json()["reason"] == "CAPTURED_HISTORICAL_ROUTE_NOT_CURRENT_TRAFFIC"
    assert replay.json()["duration_min"] == 17
    assert observation_id not in replay.text
    assert "39.9042" not in replay.text

    with SessionLocal() as session:
        operation = session.scalar(select(RouteAcquisitionOperation).where(
            RouteAcquisitionOperation.journey_id == journey_id,
            RouteAcquisitionOperation.request_json.like("%R80_PRIVATE_BUDDY_HANDOFF%"),
        ))
        assert operation is not None
        operation.result_json = json.dumps({
            "provider": "mock-mobility",
            "provenance": "LIVE_PROVIDER_CAPTURE",
            "duration_min": 3,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        })
        session.add(ProviderCall(
            id=str(uuid4()),
            provider_key="mock-mobility",
            operation="ROUTE_ACQUISITION",
            request_json=operation.request_json,
            response_json=json.dumps({"operation_id": str(operation.id)}),
            status="SUCCESS",
            latency_ms=1,
            created_at=datetime.now(timezone.utc).isoformat(),
        ))
        session.commit()

    mock = client.get(handoff_path + "/route/current", headers=_auth(helper_id))
    assert mock.status_code == 200, mock.text
    assert mock.json()["route_state"] == "UNKNOWN"
    assert mock.json()["duration_min"] is None

    # An operation result can *claim* a legitimate provider/provenance. An
    # unrelated or failed ProviderCall, even one naming the operation ID,
    # must never convert it into a LIVE route for a traveller.
    with SessionLocal() as session:
        operation = session.scalar(select(RouteAcquisitionOperation).where(
            RouteAcquisitionOperation.journey_id == journey_id,
            RouteAcquisitionOperation.request_json.like("%R80_PRIVATE_BUDDY_HANDOFF%"),
        ))
        assert operation is not None
        stamp = datetime.now(timezone.utc).isoformat()
        claimed_result = {
            "operation_id": str(operation.id),
            "provider": "valhalla-http",
            "provenance": "LIVE_PROVIDER_CAPTURE",
            "duration_min": 8,
            "captured_at": stamp,
        }
        operation.result_json = json.dumps(claimed_result)
        for provider_key, status, request_json in [
            ("mock-mobility", "SUCCESS", operation.request_json),
            ("valhalla", "FAILURE", operation.request_json),
            ("valhalla", "SUCCESS", "{}"),
        ]:
            session.add(ProviderCall(
                id=str(uuid4()),
                provider_key=provider_key,
                operation="ROUTE_ACQUISITION",
                request_json=request_json,
                response_json=json.dumps(claimed_result),
                status=status,
                latency_ms=1,
                created_at=stamp,
            ))
        session.commit()

    mismatched_receipts = client.get(handoff_path + "/route/current", headers=_auth(helper_id))
    assert mismatched_receipts.status_code == 200, mismatched_receipts.text
    assert mismatched_receipts.json()["route_state"] == "UNKNOWN"
    assert mismatched_receipts.json()["duration_min"] is None

    # This is a synthetic *database-contract* test, NOT a real Valhalla run.
    # An internally consistent persisted successful Valhalla receipt is the
    # minimum LIVE receipt contract; only a real configured provider may
    # create such a receipt in normal product operation.
    with SessionLocal() as session:
        operation = session.scalar(select(RouteAcquisitionOperation).where(
            RouteAcquisitionOperation.journey_id == journey_id,
            RouteAcquisitionOperation.request_json.like("%R80_PRIVATE_BUDDY_HANDOFF%"),
        ))
        assert operation is not None
        session.add(ProviderCall(
            id=str(uuid4()),
            provider_key="valhalla",
            operation="ROUTE_ACQUISITION",
            request_json=operation.request_json,
            response_json=operation.result_json,
            status="SUCCESS",
            latency_ms=1,
            created_at=datetime.now(timezone.utc).isoformat(),
        ))
        session.commit()
    internally_matched_receipt = client.get(handoff_path + "/route/current", headers=_auth(helper_id))
    assert internally_matched_receipt.status_code == 200, internally_matched_receipt.text
    assert internally_matched_receipt.json()["route_state"] == "LIVE"
    assert internally_matched_receipt.json()["duration_min"] == 8
