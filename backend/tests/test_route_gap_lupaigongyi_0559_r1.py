"""ORD-0559 路牌工乙: the journeys-family doors in the n-to-z slice, one field at a time.

The slice is `/api/v1/journeys/{journey_id}/<segment>` where the segment starts with n to z:
operations, outcomes, plans (preview-reorder / accept-reorder), provider-mesh, recovery,
stay-mobility, stays, web-observations.  The a-to-m slice belongs to 路牌工甲.

Every arm asserts response fields, not just status codes.  Field names are read off the handlers
on the authoritative tip this branch was cut from (the coordinates are listed per route in the
delivery block), and the reply shapes were taken from a real run of
`review/lupaigongyi-0559/probe_r1.py` against this same code.

Nothing inside the application is stubbed.  The two reorder doors need a real composed plan, so
they reuse the suite's own fixture outlet, `test_v12_authoritative_trip_execution._journey_with_inputs`
plus `POST .../authoritative-compose` and `POST .../plans/{id}/select` -- the same chain
`tests/test_v13_integrity.py` uses.  That outlet claims the demo reset door, so this module goes
through it rather than inventing a private shortcut; the database is the isolated one
`backend/tests/conftest.py` resolved for this run.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.db import models as M
from app.db.session import SessionLocal
from app.main import app
from demo_stage import demo_reset_headers

client = TestClient(app, raise_server_exceptions=False)
NOW = datetime.now(timezone.utc)
MOMENT = NOW.isoformat()
START = (NOW + timedelta(days=210)).isoformat()
END = (NOW + timedelta(days=212)).isoformat()
PAST_CURSOR = (NOW - timedelta(hours=1)).isoformat()

RECOVERY_PROVIDER_KEY = "citynexus-capability-recovery"
RECOVERY_EVENT_TYPE = "USER_CHANGE"

OUTCOMES_PATH = "/api/v1/journeys/{j}/outcomes"
WEB_OBSERVATIONS_PATH = "/api/v1/journeys/{j}/web-observations"
PROVIDERS_PATH = "/api/v1/journeys/{j}/stay-mobility/providers"
STAYS_SEARCH_PATH = "/api/v1/journeys/{j}/stays/search"
STREAM_PATH = "/api/v1/journeys/{j}/operations/stream"
ACKNOWLEDGE_PATH = "/api/v1/journeys/{j}/recovery/acknowledge"
MESH_PATH = "/api/v1/journeys/{j}/provider-mesh/discover"
REAL_CITY_ALIAS_PATH = "/api/v1/journeys/{j}/real-city/discover"
PREVIEW_PATH = "/api/v1/journeys/{j}/plans/preview-reorder"
ACCEPT_PATH = "/api/v1/journeys/{j}/plans/accept-reorder"


def _traveler(tag: str) -> str:
    ident = str(uuid.uuid4())
    with SessionLocal() as session:
        session.add(M.Traveler(id=ident, display_name=f"ORD-0559 路牌工乙 {tag}", email=None,
                               locale="zh-CN", timezone="Asia/Shanghai", created_at=MOMENT,
                               updated_at=MOMENT))
        session.commit()
    return ident


def _journey(tag: str, city_code: str = "CN-XIAMEN") -> tuple[str, str]:
    traveler_id = _traveler(tag)
    ident = str(uuid.uuid4())
    with SessionLocal() as session:
        session.add(M.Journey(id=ident, traveler_id=traveler_id, title=f"海河一周 {tag}",
                              city_code=city_code, timezone="Asia/Shanghai", start_at=START,
                              end_at=END, budget_amount_minor=120000, budget_currency="CNY",
                              status="PLANNED", created_at=MOMENT, updated_at=MOMENT))
        session.commit()
    return ident, traveler_id


def _error(body: dict) -> dict:
    return body.get("error") or {}


def _sse_frames(text: str) -> list[dict[str, str]]:
    """Split an event-stream body into frames exactly as the door emits them."""

    frames: list[dict[str, str]] = []
    for block in text.split("\n\n"):
        block = block.strip("\n")
        if not block or block.startswith(":"):
            continue
        frame: dict[str, str] = {}
        for line in block.split("\n"):
            if line.startswith("id: "):
                frame["id"] = line[4:]
            elif line.startswith("event: "):
                frame["event"] = line[7:]
            elif line.startswith("data: "):
                frame["data"] = line[6:]
        frames.append(frame)
    return frames


# --------------------------------------------------------------------------- GET /outcomes
def test_outcomes_on_a_fresh_journey_is_an_empty_wrapped_list():
    journey_id, _ = _journey("outcomes-empty")
    answer = client.get(OUTCOMES_PATH.format(j=journey_id))
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"journey_id", "events"}
    assert body["journey_id"] == journey_id
    assert body["events"] == []


def test_outcomes_hands_back_every_column_of_each_seeded_fact():
    journey_id, traveler_id = _journey("outcomes-rows")
    earlier = str(uuid.uuid4())
    later = str(uuid.uuid4())
    with SessionLocal() as session:
        session.add(M.JourneyOutcomeEvent(
            id=earlier, journey_id=journey_id, activity_id=None, event_type="activity.completed",
            actor_type="USER", actor_id=traveler_id,
            occurred_at_actual=(NOW - timedelta(days=1)).isoformat(), planned_start_at=START,
            planned_end_at=END, source="DOMAIN", related_proposal_id=None,
            related_agent_run_id=None, payload_json=json.dumps({"probe_key": "probe_value"}),
            created_at=MOMENT))
        session.add(M.JourneyOutcomeEvent(
            id=later, journey_id=journey_id, activity_id=None, event_type="activity.skipped",
            actor_type="AGENT", actor_id=None, occurred_at_actual=MOMENT,
            planned_start_at=None, planned_end_at=None, source="MANUAL",
            related_proposal_id=None, related_agent_run_id=None, payload_json="{}",
            created_at=MOMENT))
        session.commit()

    events = client.get(OUTCOMES_PATH.format(j=journey_id)).json()["events"]
    assert [item["id"] for item in events] == [earlier, later]
    assert set(events[0]) == {"id", "activity_id", "event_type", "actor_type",
                             "occurred_at_actual", "planned_start_at", "planned_end_at", "source",
                             "payload", "related_proposal_id", "related_agent_run_id"}
    assert events[0]["event_type"] == "activity.completed"
    assert events[0]["actor_type"] == "USER"
    assert events[0]["occurred_at_actual"] == (NOW - timedelta(days=1)).isoformat()
    assert events[0]["planned_start_at"] == START
    assert events[0]["planned_end_at"] == END
    assert events[0]["source"] == "DOMAIN"
    assert events[0]["payload"] == {"probe_key": "probe_value"}
    assert events[0]["activity_id"] is None
    assert events[0]["related_agent_run_id"] is None
    assert events[1]["source"] == "MANUAL"
    assert events[1]["actor_type"] == "AGENT"
    assert events[1]["planned_start_at"] is None
    assert events[1]["payload"] == {}


def test_outcomes_for_an_unknown_journey_is_a_named_absence():
    answer = client.get(OUTCOMES_PATH.format(j=str(uuid.uuid4())))
    assert answer.status_code == 404, answer.text
    error = _error(answer.json())
    assert error["code"] == "NOT_FOUND"
    assert error["message_key"] == "resource.not_found"
    assert error["error_receipt_id"].startswith("CNX-")


# ------------------------------------------------------------------- GET /web-observations
def test_web_observations_declares_its_authority_before_any_row_exists():
    journey_id, _ = _journey("web-empty")
    body = client.get(WEB_OBSERVATIONS_PATH.format(j=journey_id)).json()
    assert set(body) == {"journey_id", "authority", "observations"}
    assert body["journey_id"] == journey_id
    assert body["authority"] == "NON_AUTHORITATIVE"
    assert body["observations"] == []


def test_web_observations_maps_every_column_and_orders_by_capture_recency():
    journey_id, _ = _journey("web-rows")
    older = str(uuid.uuid4())
    newer = str(uuid.uuid4())
    with SessionLocal() as session:
        session.add(M.WebObservation(
            id=older, journey_id=journey_id, query="厦门 周末 展览", url="https://example.org/old",
            domain="example.org", title="Older note", source_class="OPEN_WEB",
            provider_key="deepseek_responses", model_key="deepseek-v3",
            captured_at=(NOW - timedelta(hours=2)).isoformat(),
            evidence_fingerprint="a" * 16, content_excerpt="old excerpt",
            authority_status="NON_AUTHORITATIVE", created_at=MOMENT))
        session.add(M.WebObservation(
            id=newer, journey_id=journey_id, query="天津 海河 骑行", url="https://example.org/new",
            domain="example.org", title="Newer note", source_class="OFFICIAL",
            provider_key="deepseek_responses", model_key="deepseek-r1", captured_at=MOMENT,
            evidence_fingerprint="b" * 16, content_excerpt="new excerpt",
            authority_status="NON_AUTHORITATIVE", created_at=MOMENT))
        session.commit()

    body = client.get(WEB_OBSERVATIONS_PATH.format(j=journey_id)).json()
    assert body["authority"] == "NON_AUTHORITATIVE"
    rows = body["observations"]
    assert [item["id"] for item in rows] == [newer, older]
    assert set(rows[0]) == {"id", "query", "url", "domain", "title", "source_class",
                           "provider_key", "model", "captured_at", "evidence_fingerprint",
                           "authority_status"}
    assert rows[0]["query"] == "天津 海河 骑行"
    assert rows[0]["url"] == "https://example.org/new"
    assert rows[0]["domain"] == "example.org"
    assert rows[0]["source_class"] == "OFFICIAL"
    assert rows[0]["provider_key"] == "deepseek_responses"
    assert rows[0]["model"] == "deepseek-r1"
    assert rows[0]["captured_at"] == MOMENT
    assert rows[0]["evidence_fingerprint"] == "b" * 16
    assert rows[0]["authority_status"] == "NON_AUTHORITATIVE"
    assert rows[1]["source_class"] == "OPEN_WEB"
    assert rows[1]["model"] == "deepseek-v3"


def test_web_observations_for_an_unknown_journey_is_a_named_absence():
    answer = client.get(WEB_OBSERVATIONS_PATH.format(j=str(uuid.uuid4())))
    assert answer.status_code == 404, answer.text
    error = _error(answer.json())
    assert error["code"] == "NOT_FOUND"
    assert error["message_key"] == "resource.not_found"


# ------------------------------------------------------ GET /stay-mobility/providers
def test_provider_mesh_names_both_accommodation_legs_and_their_configuration():
    journey_id, _ = _journey("providers-plain")
    answer = client.get(PROVIDERS_PATH.format(j=journey_id))
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"accommodation", "mobility"}
    assert set(body["accommodation"]) == {"captured", "live"}
    assert body["accommodation"]["captured"] == {
        "provider_key": "citynexus-city-fixture", "status": "UNAVAILABLE_FOR_CITY",
        "provenance": "CAPTURED_REPLAY"}
    assert body["accommodation"]["live"] == {"provider_key": "live-accommodation",
                                            "status": "NOT_CONFIGURED"}
    assert set(body["mobility"]) == {"amap", "valhalla", "transit_realtime", "ride_hail"}
    assert body["mobility"]["amap"]["status"] == "NOT_CONFIGURED"
    assert body["mobility"]["amap"]["captured_fallback"] == "UNAVAILABLE_FOR_CITY"
    assert body["mobility"]["amap"]["coordinate_crs"] == (
        "GCJ02 at provider boundary; canonical domain WGS84")
    assert body["mobility"]["valhalla"] == {"status": "NOT_CONFIGURED"}
    assert body["mobility"]["transit_realtime"] == {"status": "UNKNOWN_REALTIME"}
    assert body["mobility"]["ride_hail"] == {"status": "UNKNOWN_COST"}


def test_provider_mesh_promotes_the_captured_leg_once_a_real_capture_has_landed():
    journey_id, _ = _journey("providers-after-capture", "CN-TIANJIN")
    before = client.get(PROVIDERS_PATH.format(j=journey_id)).json()
    assert before["accommodation"]["captured"]["status"] == "UNAVAILABLE_FOR_CITY"
    captured = client.post(STAYS_SEARCH_PATH.format(j=journey_id), json={"query": "海河 住宿"})
    assert captured.status_code == 200, captured.text
    assert captured.json()["offers"]
    after = client.get(PROVIDERS_PATH.format(j=journey_id)).json()
    assert after["accommodation"]["captured"]["status"] == "READY"
    assert after["accommodation"]["captured"]["provider_key"] == "citynexus-city-fixture"
    assert after["accommodation"]["captured"]["provenance"] == "CAPTURED_REPLAY"
    assert after["mobility"]["amap"]["captured_fallback"] == "READY"


def test_provider_mesh_for_an_unknown_journey_is_a_named_absence():
    answer = client.get(PROVIDERS_PATH.format(j=str(uuid.uuid4())))
    assert answer.status_code == 404, answer.text
    error = _error(answer.json())
    assert error["code"] == "NOT_FOUND"
    assert error["message_key"] == "resource.not_found"


# ---------------------------------------------------------------- POST /stays/search
def test_stays_search_echoes_the_query_and_prices_each_captured_offer_by_nights():
    journey_id, _ = _journey("stays-query", "CN-TIANJIN")
    answer = client.post(STAYS_SEARCH_PATH.format(j=journey_id), json={"query": "海河 步行圈"})
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"query", "provenance", "offers"}
    assert body["query"] == "海河 步行圈"
    assert body["provenance"] == "CAPTURED_REPLAY"
    assert body["offers"], body
    first = body["offers"][0]
    assert set(first) == {"id", "property_name", "total_amount_minor", "nightly_amount_minor",
                         "currency", "refundable", "check_in_at", "check_out_at", "location"}
    assert first["property_name"] == "Haihe Riverside Hotel"
    assert first["currency"] == "CNY"
    assert first["refundable"] is True
    assert first["nightly_amount_minor"] == 18000
    assert first["total_amount_minor"] == first["nightly_amount_minor"] * 2
    assert set(first["location"]) == {"latitude", "longitude"}
    assert first["location"]["latitude"] == 39.1321
    assert first["check_in_at"] < first["check_out_at"]


def test_stays_search_without_a_body_falls_back_to_the_schema_default_query():
    journey_id, _ = _journey("stays-default", "CN-TIANJIN")
    body = client.post(STAYS_SEARCH_PATH.format(j=journey_id), json={}).json()
    assert body["query"] == "stay-aware journey"
    assert body["provenance"] == "CAPTURED_REPLAY"


def test_stays_search_recaptures_without_multiplying_offers():
    journey_id, _ = _journey("stays-idempotent", "CN-TIANJIN")
    first = client.post(STAYS_SEARCH_PATH.format(j=journey_id), json={"query": "同一城"}).json()
    second = client.post(STAYS_SEARCH_PATH.format(j=journey_id), json={"query": "同一城"}).json()
    assert [item["id"] for item in first["offers"]] == [item["id"] for item in second["offers"]]
    with SessionLocal() as session:
        rows = session.scalars(select(M.AccommodationOfferSnapshot).where(
            M.AccommodationOfferSnapshot.journey_id == journey_id)).all()
    assert len(rows) == len(first["offers"])


def test_stays_search_for_an_unknown_journey_is_a_named_absence():
    answer = client.post(STAYS_SEARCH_PATH.format(j=str(uuid.uuid4())), json={})
    assert answer.status_code == 404, answer.text
    error = _error(answer.json())
    assert error["code"] == "NOT_FOUND"
    assert error["message_key"] == "resource.not_found"


# --------------------------------------------------------------- GET /operations/stream
def _audit_row(journey_id: str, actor_id: str, action: str, after: dict) -> str:
    ident = str(uuid.uuid4())
    with SessionLocal() as session:
        session.add(M.AuditLog(id=ident, actor_type="USER", actor_id=actor_id,
                               journey_id=journey_id, action=action, entity_type="PlanVersion",
                               entity_id="probe-entity", before_json=None,
                               after_json=json.dumps(after), trace_id=ident, created_at=MOMENT))
        session.commit()
    return ident


def test_operations_stream_replays_the_projection_it_attaches_to_each_frame():
    journey_id, traveler_id = _journey("stream-replay")
    audit_id = _audit_row(journey_id, traveler_id, "trip_studio.accepted",
                          {"summary": "路牌工乙 的排程", "reason_codes": ["PROBE_ONE", "PROBE_TWO"],
                           "new_plan_version_id": "next-plan"})
    answer = client.get(STREAM_PATH.format(j=journey_id) + f"?after={PAST_CURSOR}&timeout_seconds=0.6")
    assert answer.status_code == 200, answer.text
    assert answer.headers["content-type"].startswith("text/event-stream")
    assert answer.headers["cache-control"] == "no-cache"
    assert answer.headers["x-accel-buffering"] == "no"
    frames = _sse_frames(answer.text)
    assert len(frames) == 1, answer.text
    frame = frames[0]
    assert frame["id"] == audit_id
    assert frame["event"] == "trip_studio.accepted"
    projection = json.loads(frame["data"])
    assert set(projection) == {"id", "timestamp", "event_type", "type", "summary", "actor_type",
                              "actor_id", "tool", "journey_id", "proposal_id", "entity_type",
                              "entity_id", "decision", "reason_codes", "trace_id", "source",
                              "facts"}
    assert projection["id"] == audit_id
    assert projection["event_type"] == projection["type"] == "trip_studio.accepted"
    assert projection["summary"] == "路牌工乙 的排程"
    assert projection["source"] == "audit_log"
    assert projection["reason_codes"] == ["PROBE_ONE", "PROBE_TWO"]
    assert projection["journey_id"] == journey_id
    assert projection["actor_type"] == "USER"
    assert projection["actor_id"] == traveler_id
    assert projection["entity_type"] == "PlanVersion"
    assert projection["entity_id"] == "probe-entity"
    assert projection["proposal_id"] is None
    assert projection["decision"] is None
    assert projection["tool"] is None
    assert projection["facts"] == {"summary": "路牌工乙 的排程", "reason_codes": ["PROBE_ONE", "PROBE_TWO"],
                                   "new_plan_version_id": "next-plan"}


def test_operations_stream_translates_a_guardian_pulse_into_its_named_event():
    journey_id, traveler_id = _journey("stream-event-type")
    _audit_row(journey_id, traveler_id, "guardian.pulse.started", {"summary": "pulse"})
    text = client.get(STREAM_PATH.format(j=journey_id) + f"?after={PAST_CURSOR}&timeout_seconds=0.6").text
    frames = _sse_frames(text)
    assert [frame["event"] for frame in frames] == ["guardian_wake"]
    assert json.loads(frames[0]["data"])["event_type"] == "guardian_wake"


def test_operations_stream_starts_at_the_connection_and_only_beats_afterwards():
    journey_id, traveler_id = _journey("stream-heartbeat")
    _audit_row(journey_id, traveler_id, "trip_studio.accepted", {"summary": "历史那一格"})
    text = client.get(STREAM_PATH.format(j=journey_id) + "?timeout_seconds=0.6").text
    assert _sse_frames(text) == []
    assert ": citynexus-heartbeat" in text


def test_operations_stream_refuses_a_timeout_above_the_contract_ceiling():
    journey_id, _ = _journey("stream-timeout")
    answer = client.get(STREAM_PATH.format(j=journey_id) + "?timeout_seconds=999")
    assert answer.status_code == 422, answer.text
    error = _error(answer.json())
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"]["errors"][0]["loc"] == ["query", "timeout_seconds"]
    assert error["details"]["errors"][0]["message_key"] == "validation.less.than.equal"


def test_operations_stream_for_an_unknown_journey_is_a_named_absence():
    answer = client.get(STREAM_PATH.format(j=str(uuid.uuid4())) + "?timeout_seconds=0.6")
    assert answer.status_code == 404, answer.text
    error = _error(answer.json())
    assert error["code"] == "NOT_FOUND"
    assert error["message_key"] == "resource.not_found"


# ------------------------------------------------------- POST /recovery/acknowledge
def _open_recovery(journey_id: str) -> str:
    ident = str(uuid.uuid4())
    with SessionLocal() as session:
        session.add(M.Event(id=ident, journey_id=journey_id, event_type=RECOVERY_EVENT_TYPE,
                           provider_key=RECOVERY_PROVIDER_KEY, status="DETECTED",
                           severity="MAJOR", provenance="SIMULATED", occurred_at=MOMENT,
                           detected_at=MOMENT, resolved_at=None,
                           payload_json=json.dumps({"capability_code": "SOLVER_FEASIBLE_PLAN"}),
                           created_at=MOMENT))
        session.commit()
    return ident


def test_recovery_acknowledge_without_an_open_event_is_a_named_absence():
    journey_id, _ = _journey("recovery-none")
    answer = client.post(ACKNOWLEDGE_PATH.format(j=journey_id))
    assert answer.status_code == 404, answer.text
    error = _error(answer.json())
    assert error["code"] == "NOT_FOUND"
    assert error["message"] == "no open recovery to acknowledge"
    assert error["message_key"] == "resource.not_found"


def test_recovery_acknowledge_records_the_look_without_resolving_anything():
    journey_id, _ = _journey("recovery-open")
    event_id = _open_recovery(journey_id)
    answer = client.post(ACKNOWLEDGE_PATH.format(j=journey_id))
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"journey_id", "acknowledged", "resolved", "recovery"}
    assert body["journey_id"] == journey_id
    assert body["acknowledged"] is True
    assert body["resolved"] is False
    recovery = body["recovery"]
    assert recovery["state"] == "RECOVERY_REQUIRED"
    assert recovery["kind"] == "CAPABILITY_HARD_RECOVERY"
    assert recovery["event_id"] == event_id
    assert recovery["event_status"] == "ACKNOWLEDGED"
    assert recovery["acknowledged"] is True
    assert recovery["capability_code"] == "SOLVER_FEASIBLE_PLAN"
    assert recovery["active_plan_version_id"] is None
    assert recovery["failures"] == []
    assert recovery["replan_attempted"] is False
    assert recovery["no_alternative"] is False
    assert recovery["candidate_plan_ids"] == []
    assert recovery["requires_user_decision"] is True
    assert recovery["silent_plan_mutation"] is False
    assert "REPLAN" in recovery["actions"]
    with SessionLocal() as session:
        row = session.get(M.Event, event_id)
        assert row is not None and row.status == "ACKNOWLEDGED"
        assert row.resolved_at is None
        assert json.loads(row.payload_json)["acknowledged_at"]
        audits = session.scalars(select(M.AuditLog).where(
            M.AuditLog.action == "journey.recovery.acknowledged",
            M.AuditLog.journey_id == journey_id)).all()
    assert len(audits) == 1
    assert json.loads(audits[0].after_json) == {"acknowledged": True, "resolved": False,
                                               "still_infeasible": False}


def test_recovery_acknowledge_keeps_the_event_open_when_called_twice():
    journey_id, _ = _journey("recovery-twice")
    event_id = _open_recovery(journey_id)
    first = client.post(ACKNOWLEDGE_PATH.format(j=journey_id)).json()["recovery"]["acknowledged_at"]
    second = client.post(ACKNOWLEDGE_PATH.format(j=journey_id)).json()["recovery"]["acknowledged_at"]
    assert first != second
    with SessionLocal() as session:
        row = session.get(M.Event, event_id)
        assert row is not None and row.status == "ACKNOWLEDGED" and row.resolved_at is None


def test_recovery_acknowledge_for_an_unknown_journey_is_a_named_absence():
    answer = client.post(ACKNOWLEDGE_PATH.format(j=str(uuid.uuid4())))
    assert answer.status_code == 404, answer.text
    error = _error(answer.json())
    assert error["code"] == "NOT_FOUND"
    assert error["message_key"] == "resource.not_found"


# ---------------------------------------------------- POST /provider-mesh/discover
def test_provider_mesh_discover_reports_the_sealed_replay_and_its_candidates():
    journey_id, _ = _journey("mesh-discover", "CN-TIANJIN")
    answer = client.post(MESH_PATH.format(j=journey_id), json={})
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"journey_id", "city_code", "city_context", "mode", "captured_at",
                        "expires_at", "provider_status", "provider_evidence", "provenance",
                        "runtime_provenance", "candidates"}
    assert body["journey_id"] == journey_id
    assert body["city_code"] == "CN-TIANJIN"
    assert body["city_context"] == "CN-TIANJIN"
    assert body["mode"] == "captured_replay"
    assert body["provenance"] == "SEALED_LIVE_CAPTURE"
    assert body["runtime_provenance"] == "SEALED_REAL_REPLAY"
    captured_at = datetime.fromisoformat(body["captured_at"])
    expires_at = datetime.fromisoformat(body["expires_at"])
    assert (expires_at - captured_at).total_seconds() == settings.real_city_cache_ttl_seconds
    status = body["provider_status"]
    assert status["nominatim"] == "REPLAY_NOT_CALLED"
    assert status["overpass"] == "REPLAY_NOT_CALLED"
    assert status["openstreetmap_replay"] == "SEALED_REAL_REPLAY"
    assert set(status["anchor"]) == {"latitude", "longitude", "display_name", "provider"}
    assert status["anchor"]["provider"] == "nominatim"
    assert status["anchor"]["display_name"] == "天津市, 中国"
    assert status["snapshot_anchor"] == status["anchor"]
    assert body["provider_evidence"]["snapshot_schema"] == "citynexus.real-city.snapshot.v135"
    assert body["candidates"], body
    candidate = body["candidates"][0]
    assert set(candidate) == {"provider_key", "external_id", "name", "category", "latitude",
                             "longitude", "tags", "opening_hours", "metadata", "distance_m",
                             "cost_evidence", "id", "materialized_place_id", "coordinate_system",
                             "source_coordinate_system"}
    assert candidate["id"] == candidate["materialized_place_id"]
    assert isinstance(candidate["name"], str) and candidate["name"]
    assert isinstance(candidate["category"], str) and candidate["category"]
    assert isinstance(candidate["tags"], list)
    assert candidate["coordinate_system"]
    assert isinstance(candidate["metadata"], dict)
    assert candidate["distance_m"] is None or isinstance(candidate["distance_m"], float)


def test_provider_mesh_discover_honours_its_own_radius_and_limit():
    journey_id, _ = _journey("mesh-limit", "CN-TIANJIN")
    body = client.post(MESH_PATH.format(j=journey_id),
                      json={"query": "coffee", "radius_m": 1200, "limit": 2,
                            "mode": "replay"}).json()
    assert len(body["candidates"]) <= 2
    assert body["mode"] == "replay"
    assert body["provenance"] == "REPLAY"
    assert body["runtime_provenance"] == "REPLAY"
    assert body["provider_evidence"] is not None


def test_provider_mesh_discover_is_the_same_door_as_the_real_city_alias():
    journey_id, _ = _journey("mesh-alias", "CN-TIANJIN")
    mesh = client.post(MESH_PATH.format(j=journey_id), json={"query": "coffee"}).json()
    alias = client.post(REAL_CITY_ALIAS_PATH.format(j=journey_id), json={"query": "coffee"}).json()
    assert alias["candidates"] == mesh["candidates"]
    assert alias["journey_id"] == mesh["journey_id"] == journey_id


def test_provider_mesh_discover_refuses_a_radius_below_the_floor():
    journey_id, _ = _journey("mesh-radius", "CN-TIANJIN")
    answer = client.post(MESH_PATH.format(j=journey_id), json={"radius_m": 1})
    assert answer.status_code == 422, answer.text
    error = _error(answer.json())
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"]["errors"][0]["loc"] == ["body", "radius_m"]


def test_provider_mesh_discover_for_an_unknown_journey_is_a_named_absence():
    answer = client.post(MESH_PATH.format(j=str(uuid.uuid4())), json={"query": "coffee"})
    assert answer.status_code == 404, answer.text
    error = _error(answer.json())
    assert error["code"] == "NOT_FOUND"
    assert error["message_key"] == "resource.not_found"


# ---------------------------------------------------------------- the two reorder doors
# Both aliases share one handler with `trip-studio/preview` and `trip-studio/accept`
# (`backend/tests/test_qoder_ord0478_route_ownership.py` pins that pairing), and neither alias had
# ever carried a payload before this module.  A reorder needs a real composed plan, so this goes
# through the suite's own outlet -- the demo reset door claimed by
# `test_v12_authoritative_trip_execution._journey_with_inputs`, then the product's own compose and
# select routes.  It is deliberately the last section: the reset clears the library, and every arm
# above has already spoken.

_STUDIO: dict[str, dict] = {}
SWAP_TITLES = ("Tea House", "Riverside Eye")


def _swap(order: list[str], titles: dict[str, str]) -> list[str]:
    moved = list(order)
    left = moved.index(titles[SWAP_TITLES[0]])
    right = moved.index(titles[SWAP_TITLES[1]])
    moved[left], moved[right] = moved[right], moved[left]
    return moved


def _protected_move(order: list[str], locked: list[str]) -> list[str]:
    """Send the first protected activity to the back: the gate must name this move."""

    anchor = locked[0]
    return [item for item in order if item != anchor] + [anchor]


def _plan_view(plan_id: str) -> dict:
    """Read a plan back through the product's own plan door, in its stored sequence."""

    answer = client.get(f"/api/v1/plans/{plan_id}")
    assert answer.status_code == 200, answer.text
    return answer.json()


def _order_of(plan_id: str) -> dict:
    view = _plan_view(plan_id)
    activities = view["activities"]
    titles = {item["title"]: item["id"] for item in activities}
    canonical = [item["id"] for item in activities]
    locked = [item["id"] for item in activities if item["locked"]]
    return {"plan_id": plan_id, "canonical": canonical, "titles": titles, "locked": locked,
            "swapped": _swap(canonical, titles), "protected_move": _protected_move(canonical, locked),
            "sequence_titles": [item["title"] for item in activities],
            "place_ids": sorted(str(item.get("place_id") or "") for item in activities),
            "version_no": view["version_no"], "status": view["status"]}


def _active_order(journey_id: str) -> dict:
    with SessionLocal() as session:
        plan_id = session.get(M.Journey, journey_id).active_plan_version_id
    assert plan_id
    return _order_of(plan_id)


def _studio(tag: str) -> dict:
    if tag in _STUDIO:
        return _STUDIO[tag]
    from test_v12_authoritative_trip_execution import _journey_with_inputs

    reset = client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    assert reset.status_code == 200, reset.text
    journey_id, place_ids, commitment_id = _journey_with_inputs()
    composed = client.post(
        f"/api/v1/journeys/{journey_id}/authoritative-compose",
        json={"place_ids": place_ids, "candidate_count": 1, "reservation_id": commitment_id},
    )
    assert composed.status_code == 201, composed.text
    plan = composed.json()["top_k"][0]
    selected = client.post(f"/api/v1/journeys/{journey_id}/plans/{plan['id']}/select")
    assert selected.status_code == 200, selected.text
    studio = _order_of(plan["id"])
    for title in SWAP_TITLES:
        assert title in studio["titles"], sorted(studio["titles"])
    assert studio["locked"], "this plan is expected to carry a protected activity"
    studio["journey_id"] = journey_id
    studio["base_plan_id"] = plan["id"]
    _STUDIO[tag] = studio
    return _STUDIO[tag]


def test_preview_reorder_of_the_unchanged_order_passes_the_gate_and_mutates_nothing():
    studio = _studio("preview")
    journey_id = studio["journey_id"]
    answer = client.post(PREVIEW_PATH.format(j=journey_id), json={"activity_ids": studio["canonical"]})
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"preview_id", "journey_id", "base_plan_version_id", "draft_order",
                        "impact", "deterministic_gate", "evidence_snapshot_id",
                        "authoritative_gate", "can_accept", "mutation"}
    assert body["journey_id"] == journey_id
    assert body["base_plan_version_id"] == studio["plan_id"]
    assert body["draft_order"] == studio["canonical"]
    assert body["mutation"] == "NO_ACTIVE_PLAN_MUTATION"
    assert body["can_accept"] is True
    assert body["impact"]["changed"] is False
    assert body["impact"]["changed_activity_ids"] == []
    assert body["impact"]["risk_class"] == "LOW"
    gate = body["deterministic_gate"]
    assert gate["status"] == "PASSED"
    assert gate["failures"] == []
    assert gate["authoritative"] is True
    assert gate["evidence_valid"] is True
    assert body["evidence_snapshot_id"] == gate["evidence_snapshot_id"]
    assert body["authoritative_gate"]["frozen_facts"]
    assert body["authoritative_gate"]["failures"] == []
    assert body["authoritative_gate"]["evidence_valid"] is True
    again = client.post(PREVIEW_PATH.format(j=journey_id),
                        json={"activity_ids": studio["canonical"]}).json()
    assert again["preview_id"] == body["preview_id"]


def test_preview_reorder_of_a_feasible_pair_names_the_changed_activities():
    studio = _studio("preview")
    journey_id = studio["journey_id"]
    body = client.post(PREVIEW_PATH.format(j=journey_id),
                       json={"activity_ids": studio["swapped"]}).json()
    assert body["draft_order"] == studio["swapped"]
    assert body["impact"]["changed"] is True
    assert set(body["impact"]["changed_activity_ids"]) == {
        studio["titles"][SWAP_TITLES[0]], studio["titles"][SWAP_TITLES[1]]}
    assert body["can_accept"] is True
    assert body["deterministic_gate"]["status"] == "PASSED"
    canonical_preview = client.post(PREVIEW_PATH.format(j=journey_id),
                                   json={"activity_ids": studio["canonical"]}).json()
    assert body["preview_id"] != canonical_preview["preview_id"]


def test_preview_reorder_reads_the_draft_order_alias_over_activity_ids():
    studio = _studio("preview")
    journey_id = studio["journey_id"]
    aliased = client.post(PREVIEW_PATH.format(j=journey_id),
                          json={"activity_ids": studio["canonical"],
                                "draft_order": studio["swapped"]}).json()
    explicit = client.post(PREVIEW_PATH.format(j=journey_id),
                           json={"activity_ids": studio["swapped"]}).json()
    assert aliased["draft_order"] == studio["swapped"] == explicit["draft_order"]
    assert aliased["preview_id"] == explicit["preview_id"]


def test_preview_reorder_refuses_a_partial_order_by_name():
    studio = _studio("preview")
    answer = client.post(PREVIEW_PATH.format(j=studio["journey_id"]),
                         json={"activity_ids": studio["canonical"][:-1]})
    assert answer.status_code == 422, answer.text
    error = _error(answer.json())
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message"] == "TRIP_STUDIO_REQUIRES_FULL_ACTIVE_PLAN_ORDER"
    assert error["message_key"] == "request.invalid"


def test_preview_reorder_refuses_a_protected_move_with_a_named_failure():
    studio = _studio("preview")
    body = client.post(PREVIEW_PATH.format(j=studio["journey_id"]),
                       json={"activity_ids": studio["protected_move"]}).json()
    assert body["can_accept"] is False
    assert body["deterministic_gate"]["status"] == "FAILED"
    assert "PROTECTED_ACTIVITY_REORDER" in body["deterministic_gate"]["failures"]
    assert body["impact"]["risk_class"] == "BLOCKED"
    assert body["impact"]["protected_commitments_preserved"] is False


def test_preview_reorder_without_an_active_plan_is_a_named_conflict():
    journey_id, _ = _journey("preview-no-plan", "CN-TIANJIN")
    answer = client.post(PREVIEW_PATH.format(j=journey_id),
                         json={"activity_ids": [str(uuid.uuid4()), str(uuid.uuid4())]})
    assert answer.status_code == 409, answer.text
    error = _error(answer.json())
    assert error["code"] == "CONFLICT"
    assert error["message"] == "Trip Studio requires an active plan"
    assert error["error_receipt_id"].startswith("CNX-")


def test_preview_reorder_for_an_unknown_journey_is_a_named_absence():
    studio = _studio("preview")
    answer = client.post(PREVIEW_PATH.format(j=str(uuid.uuid4())),
                         json={"activity_ids": studio["canonical"]})
    assert answer.status_code == 404, answer.text
    error = _error(answer.json())
    assert error["code"] == "NOT_FOUND"
    assert error["message_key"] == "resource.not_found"


def test_accept_reorder_lands_a_successor_plan_and_moves_the_journey_pointer():
    studio = _studio("accept")
    journey_id = studio["journey_id"]
    preview = client.post(PREVIEW_PATH.format(j=journey_id),
                          json={"activity_ids": studio["swapped"]}).json()
    assert preview["can_accept"] is True
    answer = client.post(ACCEPT_PATH.format(j=journey_id),
                         json={"activity_ids": studio["swapped"],
                               "preview_id": preview["preview_id"]})
    assert answer.status_code == 201, answer.text
    body = answer.json()
    assert set(body) == {"plan", "preview_id", "impact", "deterministic_gate", "frozen_evidence_id"}
    assert body["preview_id"] == preview["preview_id"]
    assert body["impact"]["changed"] is True
    assert body["deterministic_gate"]["status"] == "PASSED"
    assert body["frozen_evidence_id"]
    plan = body["plan"]
    assert {"id", "status", "version_no", "activities", "journey_id"} <= set(plan)
    assert plan["id"] != studio["base_plan_id"]
    assert plan["status"] == "SELECTED"
    assert plan["version_no"] == studio["version_no"] + 1
    expected_titles = list(studio["sequence_titles"])
    tea = expected_titles.index(SWAP_TITLES[0])
    river = expected_titles.index(SWAP_TITLES[1])
    expected_titles[tea], expected_titles[river] = expected_titles[river], expected_titles[tea]
    assert [item["title"] for item in plan["activities"]] == expected_titles
    assert [item["sequence_no"] for item in plan["activities"]] == list(
        range(1, len(expected_titles) + 1))
    assert sorted(str(item.get("place_id") or "") for item in plan["activities"]) == (
        studio["place_ids"])
    successor_ids = [item["id"] for item in plan["activities"]]
    assert len(successor_ids) == len(set(successor_ids))
    with SessionLocal() as session:
        journey = session.get(M.Journey, journey_id)
        assert journey is not None and journey.active_plan_version_id == plan["id"]
        base = session.get(M.PlanVersion, studio["base_plan_id"])
        assert base is not None and base.status == "SUPERSEDED"
        audits = session.scalars(select(M.AuditLog).where(
            M.AuditLog.action == "trip_studio.accepted",
            M.AuditLog.journey_id == journey_id)).all()
    assert len(audits) == 1
    after = json.loads(audits[0].after_json)
    assert set(after) == {"new_plan_version_id", "draft_order", "frozen_evidence_id"}
    assert after["new_plan_version_id"] == plan["id"]
    assert after["draft_order"] == studio["swapped"]
    assert after["frozen_evidence_id"] == body["frozen_evidence_id"]


def test_accept_reorder_of_an_unchanged_order_answers_a_no_op_without_a_second_plan():
    studio = _studio("accept")
    journey_id = studio["journey_id"]
    current = _active_order(journey_id)
    answer = client.post(ACCEPT_PATH.format(j=journey_id),
                         json={"activity_ids": current["canonical"]})
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"plan", "preview_id", "impact", "deterministic_gate",
                        "frozen_evidence_id", "no_op"}
    assert body["no_op"] is True
    assert body["preview_id"] is None
    assert body["impact"]["changed"] is False
    assert body["plan"]["id"] == current["plan_id"]
    with SessionLocal() as session:
        plans = session.scalars(select(M.PlanVersion).where(
            M.PlanVersion.journey_id == journey_id)).all()
        audits = session.scalars(select(M.AuditLog).where(
            M.AuditLog.action == "trip_studio.accepted",
            M.AuditLog.journey_id == journey_id)).all()
    assert len(plans) == 2
    assert len(audits) == 1


def test_accept_reorder_with_a_stale_preview_id_is_refused_by_name():
    studio = _studio("accept")
    journey_id = studio["journey_id"]
    current = _active_order(journey_id)
    answer = client.post(ACCEPT_PATH.format(j=journey_id),
                         json={"activity_ids": current["canonical"],
                               "preview_id": str(uuid.uuid4())})
    assert answer.status_code == 409, answer.text
    error = _error(answer.json())
    assert error["code"] == "CONFLICT"
    assert error["message"] == "TRIP_STUDIO_PREVIEW_STALE"
    assert error["message_key"] == "request.conflict"


def test_accept_reorder_of_a_protected_move_is_refused_without_a_third_plan():
    studio = _studio("accept")
    journey_id = studio["journey_id"]
    current = _active_order(journey_id)
    answer = client.post(ACCEPT_PATH.format(j=journey_id),
                         json={"activity_ids": current["protected_move"]})
    assert answer.status_code == 422, answer.text
    error = _error(answer.json())
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message"].startswith("TRIP_STUDIO_DETERMINISTIC_GATE_FAILED:")
    assert "PROTECTED_ACTIVITY_REORDER" in error["message"]
    with SessionLocal() as session:
        journey = session.get(M.Journey, journey_id)
        assert journey.active_plan_version_id == current["plan_id"]
        plans = session.scalars(select(M.PlanVersion).where(
            M.PlanVersion.journey_id == journey_id)).all()
    assert len(plans) == 2


def test_accept_reorder_for_an_unknown_journey_is_a_named_absence():
    answer = client.post(ACCEPT_PATH.format(j=str(uuid.uuid4())), json={"activity_ids": [
        "00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002"]})
    assert answer.status_code == 404, answer.text
    error = _error(answer.json())
    assert error["code"] == "NOT_FOUND"
    assert error["message_key"] == "resource.not_found"
    assert "was not found" in error["message"]

