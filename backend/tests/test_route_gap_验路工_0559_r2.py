"""ORD-0559 route gap round two: the five small groups nobody named (six doors).

GET /api/v1/shared/journeys/{token}, GET /api/v1/city-services,
GET /api/v1/bookings/{booking_id}, GET /api/v1/transactions/{transaction_id},
GET /api/v1/catalog-hydrations/{operation_id} and
POST /api/v1/catalog-hydrations/{operation_id}/abandon.

Every id under test is produced by a real door in the same suite path
(`POST /api/v1/demo/reset`, `plans/generate` + `plans/{id}/select`,
`POST .../bookings`, `POST .../transactions`, `POST .../share-grants`,
`POST /api/v1/catalog-hydrations`), so nothing here is mocked out.
"""

from __future__ import annotations

import time
import uuid

from fastapi.testclient import TestClient

import app.main as main_module
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(main_module.app)
CITY_CODE = "CNX-DEMO"
NULL_UUID = "00000000-0000-4000-8000-000000000000"


def _selected_cruise_journey() -> tuple[str, dict, dict]:
    """The bookable activity this line already supplies (same exit as wp04's fixture)."""
    journey_id = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()["journey_id"]
    plans = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 3}
    ).json()
    plan = next(item for item in plans if any(a["place_id"] == "place-river-cruise" for a in item["activities"]))
    cruise = next(a for a in plan["activities"] if a["place_id"] == "place-river-cruise")
    assert client.post(f"/api/v1/journeys/{journey_id}/plans/{plan['id']}/select").status_code == 200
    return journey_id, plan, cruise


def _wait_hydration_terminal(operation_id: str, seconds: float = 15.0) -> dict:
    """The read door is the door this line already polls (same bound as the hydration suite)."""
    deadline = time.monotonic() + seconds
    body: dict = {}
    while time.monotonic() < deadline:
        body = _hydration(operation_id)
        if body.get("terminal") is True:
            return body
        time.sleep(0.05)
    raise AssertionError(f"operation {operation_id} never reached a terminal state, last {str(body)[:200]}")


def _error_of(answer) -> dict:
    return answer.json()["error"]


def _hydration(operation_id: str) -> dict:
    answer = client.get(f"/api/v1/catalog-hydrations/{operation_id}")
    assert answer.status_code == 200, answer.text
    return answer.json()


def test_city_services_items_carry_the_five_catalog_fields():
    reset = client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    assert reset.status_code == 200
    assert reset.json()["city_code"] == CITY_CODE
    answer = client.get("/api/v1/city-services", params={"city_code": CITY_CODE})
    assert answer.status_code == 200
    items = answer.json()
    assert isinstance(items, list) and items
    for item in items:
        assert set(item) == {"id", "name", "service_type", "city_code", "place_id"}
        assert item["city_code"] == CITY_CODE
    cruise = next(item for item in items if item["id"] == "service-river-cruise-booking")
    assert cruise["service_type"] == "bookable_experience"
    assert cruise["place_id"] == "place-river-cruise"
    assert cruise["name"] == "River Cruise Booking"
    assert client.get(
        "/api/v1/city-services", params={"city_code": "CNX-NOWHERE"}
    ).json() == []


def test_city_services_service_type_filter_keeps_only_that_type():
    assert client.post("/api/v1/demo/reset", headers=demo_reset_headers()).status_code == 200
    answer = client.get(
        "/api/v1/city-services", params={"city_code": CITY_CODE, "service_type": "tradable_food"}
    )
    assert answer.status_code == 200
    items = answer.json()
    assert items
    assert {item["service_type"] for item in items} == {"tradable_food"}
    assert {item["id"] for item in items} == {"service-food-preorder"}


def test_booking_door_returns_the_projection_it_just_wrote():
    journey_id, _plan, cruise = _selected_cruise_journey()
    created = client.post(
        f"/api/v1/journeys/{journey_id}/bookings", json={"activity_id": cruise["id"]}
    )
    assert created.status_code == 201, created.text
    written = created.json()
    answer = client.get(f"/api/v1/bookings/{written['id']}")
    assert answer.status_code == 200
    payload = answer.json()
    assert payload == written
    assert set(payload) == {
        "id",
        "journey_id",
        "activity_id",
        "commitment_id",
        "provider_key",
        "external_ref",
        "status",
        "amount",
        "amount_status",
        "cancellation_policy",
    }
    assert payload["id"] == written["id"]
    assert payload["journey_id"] == journey_id
    assert payload["activity_id"] == cruise["id"]
    assert payload["provider_key"] == "mock-booking"
    assert payload["status"] == "CONFIRMED"
    assert payload["external_ref"].startswith("mock-booking:")
    assert payload["amount"] == {"amount_minor": 12000, "currency": "CNY"}
    assert set(payload["amount"]) == {"amount_minor", "currency"}
    assert payload["commitment_id"]
    assert isinstance(payload["cancellation_policy"], dict)


def test_booking_door_names_the_id_it_could_not_find():
    client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    answer = client.get(f"/api/v1/bookings/{NULL_UUID}")
    assert answer.status_code == 404
    error = _error_of(answer)
    assert error["code"] == "NOT_FOUND"
    assert error["message_key"] == "resource.not_found"
    assert NULL_UUID in error["message"]
    assert error["details"] is None
    assert error["error_receipt_id"].startswith("CNX-")


def test_transaction_door_returns_the_projection_it_just_wrote():
    journey_id, _plan, cruise = _selected_cruise_journey()
    booking = client.post(
        f"/api/v1/journeys/{journey_id}/bookings", json={"activity_id": cruise["id"]}
    ).json()
    created = client.post(
        f"/api/v1/journeys/{journey_id}/transactions",
        json={
            "booking_id": booking["id"],
            "transaction_type": "CAPTURE",
            "amount": booking["amount"],
            "provider_key": "mock-payment",
        },
        headers={"Idempotency-Key": f"ord0559-r2-{uuid.uuid4()}"},
    )
    assert created.status_code == 201, created.text
    written = created.json()
    answer = client.get(f"/api/v1/transactions/{written['id']}")
    assert answer.status_code == 200
    payload = answer.json()
    assert payload == written
    assert set(payload) == {
        "id",
        "journey_id",
        "booking_id",
        "order_id",
        "provider_key",
        "transaction_type",
        "status",
        "amount",
        "external_ref",
    }
    assert payload["booking_id"] == booking["id"]
    assert payload["order_id"] is None
    assert payload["transaction_type"] == "CAPTURE"
    assert payload["status"] == "SUCCEEDED"
    assert payload["provider_key"] == "mock-payment"
    assert payload["amount"] == booking["amount"]
    assert payload["external_ref"].startswith("mock-payment:")


def test_transaction_door_names_the_id_it_could_not_find():
    client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    answer = client.get(f"/api/v1/transactions/{NULL_UUID}")
    assert answer.status_code == 404
    error = _error_of(answer)
    assert error["code"] == "NOT_FOUND"
    assert error["message_key"] == "resource.not_found"
    assert NULL_UUID in error["message"]


def test_shared_journey_answers_the_grant_with_the_plan_fields():
    journey_id, _plan, _cruise = _selected_cruise_journey()
    grant = client.post(
        f"/api/v1/journeys/{journey_id}/share-grants",
        json={"visibility": "LINK_READ", "created_by": "ord0559-r2"},
    )
    assert grant.status_code == 201, grant.text
    minted = grant.json()
    assert set(minted) == {
        "id",
        "journey_id",
        "token",
        "visibility",
        "created_by",
        "created_at",
        "updated_at",
        "expires_at",
        "revoked_at",
        "plan_version_id",
    }
    assert minted["journey_id"] == journey_id
    assert minted["visibility"] == "LINK_READ"
    assert minted["revoked_at"] is None

    answer = client.get(f"/api/v1/shared/journeys/{minted['token']}")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert {"id", "title", "city_code", "status", "timezone", "budget", "plan_state",
            "active_plan", "grant_scope"} <= set(body)
    assert body["id"] == journey_id
    assert body["city_code"] == CITY_CODE
    assert body["grant_scope"] == "JOURNEY"
    assert "shared_plan" not in body
    assert body["plan_state"] == "PLAN_PRESENT"
    guest = body["active_plan"]
    assert set(guest) == {"id", "version_no", "source", "stops"}
    assert guest["id"] == _plan["id"]
    assert guest["version_no"] == _plan["version_no"]
    assert guest["source"] == _plan["source"]
    assert {stop["id"] for stop in guest["stops"]} == {a["id"] for a in _plan["activities"]}
    cruise_stop = next(stop for stop in guest["stops"] if stop["id"] == _cruise["id"])
    assert set(cruise_stop) == {"id", "sequence_no", "title", "place_name", "activity_type",
                                "start_at", "end_at", "coordinate"}
    assert cruise_stop["place_name"] == _cruise["place_name"]
    assert cruise_stop["title"] == _cruise["title"]
    assert cruise_stop["activity_type"] == _cruise["activity_type"]
    assert set(cruise_stop["coordinate"]) == {
        "state", "reason", "latitude", "longitude", "coordinate_system", "source_coordinate_system",
    }
    assert cruise_stop["coordinate"]["coordinate_system"] == "WGS84"
    assert cruise_stop["coordinate"]["state"] == "READY"
    assert cruise_stop["sequence_no"] == _cruise["sequence_no"]
    assert body["timezone_honoured"] is True


def test_unknown_share_token_is_answered_by_name():
    client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    answer = client.get("/api/v1/shared/journeys/nobody-minted-this-one")
    assert answer.status_code == 404
    error = _error_of(answer)
    assert error["code"] == "NOT_FOUND"
    assert error["reason_code"] == "SHARE_GRANT_UNKNOWN"
    assert error["message"] == "No share grant carries that token."
    assert error["details"] == {"field": "token"}


def test_hydration_read_points_at_its_own_doors_and_invents_no_progress():
    accepted = client.post("/api/v1/catalog-hydrations", json={"query": "Beijing"})
    assert accepted.status_code in (200, 202), accepted.text
    minted = accepted.json()
    operation_id = minted["operation_id"]
    assert minted["status_url"] == f"/api/v1/catalog-hydrations/{operation_id}"
    assert minted["abandon_url"] == f"/api/v1/catalog-hydrations/{operation_id}/abandon"

    answer = client.get(f"/api/v1/catalog-hydrations/{operation_id}")
    assert answer.status_code == 200
    payload = answer.json()
    assert payload["operation_id"] == operation_id
    assert "progress" not in payload
    assert set(payload) == {
        "operation_id",
        "fingerprint",
        "reused",
        "status",
        "recorded_status",
        "phase",
        "outcome",
        "terminal",
        "elapsed_ms",
        "retry_after_ms",
        "canonical_destination_id",
        "pending_destination_label",
        "resolver_query_normalized",
        "destination_pending_key",
        "pending_label_fidelity",
        "destination_state",
        "retryable",
        "catalog_schema_version",
        "readiness_policy_version",
        "provider_policy_version",
        "journey_id",
        "result",
        "error",
        "submitted_at",
        "started_at",
        "finished_at",
        "abandon_requested_at",
        "status_url",
        "abandon_url",
    }
    assert payload["status_url"] == f"/api/v1/catalog-hydrations/{operation_id}"
    assert payload["abandon_url"] == f"/api/v1/catalog-hydrations/{operation_id}/abandon"
    assert payload["reused"] is False
    assert isinstance(payload["terminal"], bool)
    assert isinstance(payload["retryable"], bool)
    assert payload["fingerprint"]
    assert isinstance(payload["elapsed_ms"], int)


def test_hydration_abandon_of_a_settled_job_keeps_its_own_words():
    """The race-free arm: the job is already terminal, so abandon must not pretend it stopped it."""
    operation_id = client.post("/api/v1/catalog-hydrations", json={"query": "Beijing"}).json()["operation_id"]
    settled = _wait_hydration_terminal(operation_id)
    assert settled["terminal"] is True

    first = client.post(f"/api/v1/catalog-hydrations/{operation_id}/abandon")
    assert first.status_code == 200, first.text
    payload = first.json()
    assert payload["operation_id"] == operation_id
    assert payload["terminal"] is True
    assert payload["status"] == payload["recorded_status"]
    assert payload["recorded_status"] == settled["recorded_status"]
    assert payload["outcome"] == "ALREADY_CURRENT"
    assert payload["abandon_requested_at"] is None
    assert payload["status_url"] == f"/api/v1/catalog-hydrations/{operation_id}"
    assert payload["abandon_url"] == f"/api/v1/catalog-hydrations/{operation_id}/abandon"

    again = client.post(f"/api/v1/catalog-hydrations/{operation_id}/abandon")
    assert again.status_code == 200
    assert again.json() == payload


def test_hydration_read_names_the_operation_it_could_not_find():
    client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    answer = client.get(f"/api/v1/catalog-hydrations/{uuid.uuid4()}")
    assert answer.status_code == 404
    error = _error_of(answer)
    assert error["code"] == "NOT_FOUND"
    assert error["message_key"] == "resource.not_found"
