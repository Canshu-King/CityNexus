import json
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient

from test_issue47_private_reads import stack  # noqa: F401 -- shared pytest fixture
from app import main, demo_access, traveler_principal
from app.db.models import (
    Activity,
    Event,
    Journey,
    JourneyRoleCapability,
    PlanVersion,
    Place,
    SimulationClock,
)
from app.db.session import get_session
from app.execution.clock import execution_clock
from app.simulation import api, clock
from app.simulation.models import SimulationRun, SimulationCommand


@pytest.fixture
def sim(stack, monkeypatch):  # noqa: F811 -- pytest injects the imported fixture
    client, ids, path = stack
    configured = replace(main.settings, simulation_enabled=True, ai_enabled=True)
    for mod in (main, demo_access, api, clock):
        monkeypatch.setattr(mod, "settings", configured)
    monkeypatch.setenv("CITYNEXUS_DEMO_DATABASE_PATH", str(path.resolve()))
    client.app.include_router(api.router)
    client = TestClient(client.app, client=("127.0.0.1", 30001))
    factory = client.app.dependency_overrides[get_session]
    db = factory()
    s = next(db)
    base = datetime(2026, 12, 3, 9, tzinfo=timezone(timedelta(hours=8)))
    stamp = datetime.now(timezone.utc).isoformat()
    journey = s.get(Journey, ids["journey"])
    journey.status = "ACTIVE"
    journey.start_at = base.isoformat()
    journey.end_at = (base + timedelta(days=2)).isoformat()
    ids["plan"] = str(uuid4())
    s.add(
        PlanVersion(
            id=ids["plan"],
            journey_id=journey.id,
            version_no=1,
            planning_mode="BALANCED",
            status="ACTIVE",
            source="TEST_FIXTURE",
            total_cost_minor=0,
            currency="CNY",
            estimated_duration_min=120,
            created_at=stamp,
        )
    )
    s.add(
        JourneyRoleCapability(
            role="OWNER",
            capability="JOURNEY_EXECUTION_UPDATE",
            scope_message_key="test",
            created_at=stamp,
        )
    )
    ids["activities"] = []
    for index, days in enumerate((0, 1)):
        pid = str(uuid4())
        aid = str(uuid4())
        start = base + timedelta(days=days, minutes=30)
        s.add(
            Place(
                id=pid,
                provider_key="TEST_FIXTURE",
                external_id=pid,
                city_code="CN-BJ",
                name="Synthetic station",
                category="PARK",
                latitude=39.8 + index * 0.01,
                longitude=116.4 + index * 0.01,
                opening_hours_json="{}",
                tags_json="[]",
                metadata_json="{}",
                updated_at=stamp,
            )
        )
        s.add(
            Activity(
                id=aid,
                plan_version_id=ids["plan"],
                sequence_no=index + 1,
                activity_type="SIGHTSEE",
                title="Synthetic station",
                place_id=pid,
                start_at=start.isoformat(),
                end_at=(start + timedelta(minutes=60)).isoformat(),
                travel_from_prev_min=10,
                estimated_cost_minor=0,
                currency="CNY",
                status="ACTIVE" if index == 0 else "PLANNED",
                locked=False,
                metadata_json="{}",
                created_at=stamp,
                updated_at=stamp,
            )
        )
        ids["activities"].append(aid)
    s.flush()
    journey.active_plan_version_id = ids["plan"]
    journey.current_activity_id = ids["activities"][0]
    s.commit()
    db.close()
    presenter = uuid4().hex + uuid4().hex
    monkeypatch.setenv("CITYNEXUS_DEMO_PRESENTER_KEY", presenter)
    headers = {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(ids["owner"]), "X-CityNexus-Presenter-Key": presenter}
    base_url = "/api/v1/journeys/" + ids["journey"] + "/simulation/runs"

    def post(url, body, key=None, as_headers=None):
        return client.post(
            url,
            json=body,
            headers={
                **(headers if as_headers is None else as_headers),
                "Idempotency-Key": key or uuid4().hex,
            },
        )

    return client, ids, path, factory, headers, base_url, post


@pytest.mark.parametrize("seed", [17, 409])
def test_two_days_native_steps_persist_and_replay(sim, seed, record_property):
    client, ids, path, factory, headers, url, post = sim
    created = post(url, {"seed": seed}, "start")
    assert created.status_code == 201, created.text
    run = created.json()
    rid = run["run_id"]
    runurl = url + "/" + rid
    assert post(url, {"seed": seed}, "start").json() == run
    assert post(url, {"seed": seed + 1}, "start").status_code == 409
    steps = []
    for number in range(8):
        response = post(runurl + "/advance", {"expected_sequence": number}, "step-" + str(number))
        assert response.status_code == 200, response.text
        latest = response.json()
        steps.append(latest)
        assert (
            post(runurl + "/advance", {"expected_sequence": number}, "step-" + str(number)).json()
            == latest
        )
    assert latest["status"] == "SIMULATED_COMPLETED"
    assert len(latest["state"]["completed_activity_ids"]) == 2
    assert datetime.fromisoformat(latest["virtual_now"]).day == 4
    assert latest["state"]["location"]["source"] == "SIMULATED_GPS"
    assert [item["event"] for item in latest["history"]].count("SIM_ARRIVAL") == 2
    assert post(runurl + "/advance", {"expected_sequence": 7}).status_code == 409
    # A fresh HTTP client and fresh DB session read the same durable result.
    fresh = TestClient(client.app)
    assert fresh.get(runurl, headers=headers).json() == latest
    db = factory()
    s = next(db)
    assert s.get(Journey, ids["journey"]).status == "COMPLETED"
    assert s.get(SimulationClock, ids["journey"]).virtual_now == latest["virtual_now"]
    for aid in ids["activities"]:
        row = s.get(Activity, aid)
        meta = json.loads(row.metadata_json)
        assert row.status == "COMPLETED"
        assert meta["execution_truth"]["kind"] == "SIMULATED_STATE_TRANSITION"
        assert len(meta["execution_truth_history"]) == 4
        assert all(
            x["kind"] != "DEVICE_LOCATION_VERIFIED_EXECUTION"
            for x in meta["execution_truth_history"]
        )
    assert len(list(s.scalars(select(SimulationCommand)))) == 9
    db.close()
    record_property(
        "simulation_receipt",
        json.dumps(
            {
                "evidence_grade": "TEST_FIXTURE",
                "seed": seed,
                "initial": run,
                "final": latest,
                "http_replay_checked": True,
                "fresh_session_readback_checked": True,
                "live_model_calls": 0,
            },
            ensure_ascii=False,
        ),
    )


def test_large_advance_visits_all_phases_and_security_clock_stays_real(sim):
    client, ids, path, factory, headers, url, post = sim
    run = post(url, {"seed": 1}).json()
    result = post(url + "/" + run["run_id"] + "/advance", {"expected_sequence": 0, "minutes": 2880})
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "SIMULATED_COMPLETED"
    events = [x["event"] for x in result.json()["history"]]
    assert (
        events.count("SIM_DEPARTURE")
        == events.count("SIM_ARRIVAL")
        == events.count("SIM_EXPERIENCE")
        == 2
    )
    db = factory()
    s = next(db)
    with clock.journey_business_time(s, ids["journey"]):
        assert execution_clock.now().month == 12
        assert clock.simulation_scope_active()
        # Token expiration still uses wall time, even in a business-time context.
        from starlette.requests import Request

        token = traveler_principal.issue_traveler_token(
            ids["owner"], now=int(time.time()) - 5, ttl_seconds=1
        )
        request = Request(
            {"type": "http", "headers": [(b"authorization", ("Bearer " + token).encode())]}
        )
        with pytest.raises(Exception) as exc:
            traveler_principal.resolve_traveler_principal(request, s)
        assert exc.value.status_code == 401
    assert not clock.simulation_scope_active()
    assert abs((execution_clock.now() - datetime.now(timezone.utc)).total_seconds()) < 2
    db.close()


def test_scene_is_durable_idempotent_and_stops_progress(sim):
    client, ids, path, factory, headers, url, post = sim
    run = post(url, {"seed": 5}).json()
    runurl = url + "/" + run["run_id"]
    scene = {
        "expected_sequence": 0,
        "scene_id": "closed-d1",
        "event_type": "CLOSURE",
        "activity_id": ids["activities"][0],
    }
    response = post(runurl + "/scenes", scene, "scene")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "PAUSED_FOR_GUARDIAN"
    assert post(runurl + "/scenes", scene, "scene").json() == response.json()
    assert post(runurl + "/advance", {"expected_sequence": 1}).status_code == 409
    assert post(runurl + "/resume", {"expected_sequence": 1}).status_code == 409
    db = factory()
    s = next(db)
    events = list(s.scalars(select(Event)))
    assert len(events) == 1
    assert events[0].provenance == "SIMULATED"
    assert events[0].occurred_at == run["virtual_now"]
    assert datetime.fromisoformat(events[0].detected_at).month == datetime.now(timezone.utc).month
    from app.agent.signal_pipeline import refresh_demo_signals

    first = refresh_demo_signals(s, s.get(Journey, ids["journey"]))
    second = refresh_demo_signals(s, s.get(Journey, ids["journey"]))
    assert first.event_ids == second.event_ids == (events[0].id,)
    assert first.provider_provenance == {"environment": "SIMULATED"}
    assert len(list(s.scalars(select(Event)))) == 1
    events[0].status = "RESOLVED"
    s.commit()
    db.close()
    resumed = post(runurl + "/resume", {"expected_sequence": 1})
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "RUNNING"
    scene["expected_sequence"] = 2
    assert post(runurl + "/scenes", scene).status_code == 409


def test_authority_and_default_disabled(sim, monkeypatch):
    client, ids, path, factory, headers, url, post = sim
    assert post(url, {"seed": 1}, as_headers={}).status_code == 401
    other = {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(ids["stranger"])}
    assert post(url, {"seed": 1}, as_headers=other).status_code == 403
    member = {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(ids["member"])}
    assert post(url, {"seed": 1}, as_headers=member).status_code == 403
    monkeypatch.setattr(api, "settings", replace(api.settings, simulation_enabled=False))
    assert post(url, {"seed": 1}).status_code == 404


def test_guardian_failure_is_paused_and_replay_never_calls_again(sim, monkeypatch):
    client, ids, path, factory, headers, url, post = sim
    run = post(url, {"seed": 5}).json()
    runurl = url + "/" + run["run_id"]
    post(
        runurl + "/scenes",
        {
            "expected_sequence": 0,
            "scene_id": "closed",
            "event_type": "CLOSURE",
            "activity_id": ids["activities"][0],
        },
    )
    calls = []

    def unavailable(*args, **kwargs):
        calls.append(True)
        raise RuntimeError("private provider details must not be returned")

    from app.agent import guardian

    monkeypatch.setattr(guardian, "scan_guardian", unavailable)
    body = {"expected_sequence": 1, "model_consent": True}
    result = post(runurl + "/guardian", body, "model")
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "PAUSED_MODEL_UNAVAILABLE"
    assert "private provider" not in result.text
    assert post(runurl + "/guardian", body, "model").json() == result.json()
    assert len(calls) == 1


def test_concurrent_cas_only_one_step_writes(sim):
    from concurrent.futures import ThreadPoolExecutor

    client, ids, path, factory, headers, url, post = sim
    run = post(url, {"seed": 7}).json()
    runurl = url + "/" + run["run_id"]

    def press(index):
        return post(
            runurl + "/advance", {"expected_sequence": 0}, "double-" + str(index)
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(press, range(2)))
    assert sorted(statuses) == [200, 409]
    read = client.get(runurl, headers=headers).json()
    assert read["sequence"] == 1
    assert [x["event"] for x in read["history"]].count("SIM_DEPARTURE") == 1


def test_preflight_does_not_promote_synthetic_places(sim):
    client, ids, path, factory, headers, url, post = sim
    response = client.get(url.replace("/runs", "/cities") + "?seed=17", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "BLOCKED"
    assert response.json()["eligible_city_count"] == 0
    assert response.json()["provider_requests"] == 0


def test_schema_upgrade_keeps_existing_rows_and_adds_simulation_tables(tmp_path):
    from sqlalchemy import create_engine, inspect, text
    from app.db.session import ensure_schema

    engine = create_engine("sqlite:///" + (tmp_path / "migration.db").as_posix())
    ensure_schema(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO travelers (id,display_name,locale,timezone,created_at,updated_at) VALUES ('migration-test','Keep me','zh-CN','Asia/Shanghai','2026-10-25','2026-10-25')"
            )
        )
    ensure_schema(engine)
    assert {"simulation_runs", "simulation_commands"} <= set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT display_name FROM travelers WHERE id='migration-test'")
            ).scalar_one()
            == "Keep me"
        )
    engine.dispose()


def test_real_guardian_uses_virtual_business_time_and_refuses_rule_fallback(sim, monkeypatch):
    client, ids, path, factory, headers, url, post = sim
    run = post(url, {"seed": 5}).json()
    runurl = url + "/" + run["run_id"]
    post(
        runurl + "/scenes",
        {
            "expected_sequence": 0,
            "scene_id": "closed",
            "event_type": "CLOSURE",
            "activity_id": ids["activities"][0],
        },
    )
    db = factory()
    s = next(db)
    from app.agent.mission import create_mission

    mission = create_mission(
        s,
        s.get(Journey, ids["journey"]),
        command="闭馆时帮我找替代选择，先给我确认。",
        requested_autonomy="PROPOSE_ONLY",
        trigger_event_id=None,
        is_standing=True,
        use_model_draft=False,
    )
    mission.status = "ACTIVE"
    s.commit()
    db.close()
    from app.agent import guardian
    from app.agent.runtime import AgentRuntimeUnavailable

    def unavailable(*args, **kwargs):
        assert execution_clock.now().month == 12
        raise AgentRuntimeUnavailable("503 unavailable")

    def no_fallback(*args, **kwargs):
        raise AssertionError("simulation must not generate a rule-based Agent success")

    monkeypatch.setattr(guardian, "_model_recovery", unavailable)
    monkeypatch.setattr(guardian, "_deterministic_recovery", no_fallback)
    response = post(runurl + "/guardian", {"expected_sequence": 1, "model_consent": True})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "PAUSED_MODEL_UNAVAILABLE"
    event = response.json()["history"][-1]
    assert event["event"] == "GUARDIAN_RESULT", event
    assert event["guardian"]["action_status"] == "RETRYABLE_FAILURE"
    assert event["model_execution"] == "NOT_EXECUTED"
    db = factory()
    s = next(db)
    from app.db.models import GuardianRun, AgentRun

    actual = list(s.scalars(select(GuardianRun)))
    assert len(actual) == 1
    assert (
        datetime.fromisoformat(
            json.loads(actual[0].evidence_json)["observation"]["business_now"]
        ).month
        == 12
    )
    assert len(list(s.scalars(select(AgentRun)))) == 0
    db.close()


def test_simulation_agent_must_propose_before_signed_acceptance(sim):
    client, ids, path, factory, headers, url, post = sim
    post(url, {"seed": 5})
    db = factory()
    s = next(db)
    from app.agent.gateway import AgentToolGateway

    with clock.journey_business_time(s, ids["journey"]):
        with pytest.raises(Exception) as exc:
            AgentToolGateway(s).dispatch("accept_replan", None)
        assert exc.value.status_code == 403
        assert exc.value.detail == "SIMULATION_REQUIRES_SIGNED_PLAN_ACCEPTANCE"
    db.close()


def test_interrupted_runtime_recovery_uses_wall_lease(sim):
    client, ids, path, factory, headers, url, post = sim
    run = post(url, {"seed": 5}).json()
    runurl = url + "/" + run["run_id"]
    db = factory()
    s = next(db)
    stored = s.get(SimulationRun, run["run_id"])
    state = json.loads(stored.state_json)
    stored.status = "GUARDIAN_RUNNING"
    state["guardian_lease_expires_at"] = (
        datetime.now(timezone.utc) + timedelta(minutes=10)
    ).isoformat()
    stored.state_json = json.dumps(state)
    s.commit()
    assert post(runurl + "/recover", {"expected_sequence": 0}).status_code == 409
    s.refresh(stored)
    state["guardian_lease_expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    ).isoformat()
    stored.state_json = json.dumps(state)
    s.commit()
    db.close()
    result = post(runurl + "/recover", {"expected_sequence": 0})
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "PAUSED_MODEL_UNAVAILABLE"
    assert result.json()["history"][-1]["event"] == "GUARDIAN_INTERRUPTED"
