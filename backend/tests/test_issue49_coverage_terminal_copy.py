from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from test_issue47_private_reads import stack  # noqa: F401 -- shared fixture
from test_issue47_simulation import sim  # noqa: F401 -- signed simulation fixture
from app.db.models import (
    Activity,
    AgentRun,
    AgentRunStep,
    Journey,
    PlanVersion,
    Place,
    ProviderCall,
    ProviderObservation,
)
from app.simulation.coverage import (
    resolve_run_completed_activity_ids,
    summarize_activity_coverage,
)
from app.simulation.models import SimulationRun


RUN_ID = "run-fixture-1"
RUN_ACTOR_ID = "traveler-fixture-1"
RUN_SEQUENCE = 8
CAPTURED_AT = "2026-12-03T10:30:00+08:00"
EVIDENCE_RECORDED_AT = "2026-10-26T12:00:00+00:00"


def _truth() -> dict:
    return {
        "kind": "SIMULATED_STATE_TRANSITION",
        "transition": "COMPLETED",
        "captured_at": CAPTURED_AT,
        "actor_type": "TRAVELER",
        "actor_id": RUN_ACTOR_ID,
        "evidence": {
            "simulation_run_id": RUN_ID,
            "sequence": RUN_SEQUENCE,
            "recorded_at": EVIDENCE_RECORDED_AT,
            "location_source": "SIMULATED_GPS",
        },
    }


def _activity(activity_id: str, truth: dict, **overrides) -> dict:
    row = {
        "id": activity_id,
        "plan_version_id": "plan-source",
        "sequence_no": 1,
        "activity_type": "SIGHTSEE",
        "title": activity_id,
        "place_id": "place-canonical-1",
        "start_at": "2026-12-03T09:30:00+08:00",
        "end_at": "2026-12-03T10:30:00+08:00",
        "status": "COMPLETED",
        "metadata_json": json.dumps({"execution_truth": copy.deepcopy(truth)}),
    }
    row.update(overrides)
    return row


def _fixture():
    truth = _truth()
    source = _activity("source-a", truth)
    clone = _activity("clone-a", truth, plan_version_id="plan-active")
    history = [
        {
            "sequence": RUN_SEQUENCE,
            "event": "SIM_ACTIVITY_COMPLETED",
            "activity_id": source["id"],
            "virtual_now": CAPTURED_AT,
            "recorded_at": "2026-10-26T12:00:01+00:00",
        }
    ]
    return truth, source, clone, history


def _replace_truth(row: dict, truth: dict) -> None:
    metadata = json.loads(row["metadata_json"])
    metadata["execution_truth"] = copy.deepcopy(truth)
    row["metadata_json"] = json.dumps(metadata)


def _resolve(
    source,
    clone,
    history,
    *,
    run_sequence=RUN_SEQUENCE,
    source_activities=None,
):
    return resolve_run_completed_activity_ids(
        run_id=RUN_ID,
        run_sequence=run_sequence,
        run_actor_id=RUN_ACTOR_ID,
        history=history,
        source_activities=[source] if source_activities is None else source_activities,
        active_activities=[clone],
    )


def test_valid_same_run_terminal_truth_carries_to_an_exact_active_copy():
    _, source, clone, history = _fixture()

    # recorded_at is wall-clock audit metadata; history binding is virtual_now to captured_at.
    assert _resolve(source, clone, history) == {"source-a", "clone-a"}


@pytest.mark.parametrize(
    "mutation",
    [
        "bad_kind",
        "bad_transition",
        "bad_gps_source",
        "wrong_run_id",
        "wrong_actor_id",
        "wrong_actor_type",
        "truth_history_sequence_mismatch",
        "history_sequence_mismatch",
        "history_captured_at_mismatch",
        "wrong_history_event",
        "source_without_terminal_history",
        "future_sequence",
        "malformed_metadata_json",
        "non_mapping_execution_truth",
    ],
)
def test_invalid_source_terminal_proof_never_certifies_an_active_copy(mutation):
    truth, source, clone, history = _fixture()
    run_sequence = RUN_SEQUENCE

    if mutation == "bad_kind":
        truth["kind"] = "UNVERIFIED"
    elif mutation == "bad_transition":
        truth["transition"] = "ARRIVED"
    elif mutation == "bad_gps_source":
        truth["evidence"]["location_source"] = "DEVICE_GPS"
    elif mutation == "wrong_run_id":
        truth["evidence"]["simulation_run_id"] = "another-run"
    elif mutation == "wrong_actor_id":
        truth["actor_id"] = "another-traveler"
    elif mutation == "wrong_actor_type":
        truth["actor_type"] = "SYSTEM"
    elif mutation == "truth_history_sequence_mismatch":
        truth["evidence"]["sequence"] = RUN_SEQUENCE - 1
    elif mutation == "history_sequence_mismatch":
        history[0]["sequence"] = RUN_SEQUENCE - 1
    elif mutation == "history_captured_at_mismatch":
        history[0]["virtual_now"] = "2026-12-03T10:31:00+08:00"
    elif mutation == "wrong_history_event":
        history[0]["event"] = "SIM_ACTIVITY_SKIPPED"
    elif mutation == "source_without_terminal_history":
        history.clear()
    elif mutation == "future_sequence":
        truth["evidence"]["sequence"] = RUN_SEQUENCE + 1
        history[0]["sequence"] = RUN_SEQUENCE + 1
    elif mutation == "malformed_metadata_json":
        source["metadata_json"] = "{malformed"
    elif mutation == "non_mapping_execution_truth":
        source["metadata_json"] = json.dumps({"execution_truth": "not-an-object"})

    if mutation not in {"malformed_metadata_json", "non_mapping_execution_truth"}:
        _replace_truth(source, truth)
        _replace_truth(clone, truth)

    # source_activities is already the state/history/Journey/Place-filtered input.
    # The helper preserves that direct ID and must refuse only the copied active ID.
    if mutation == "source_without_terminal_history":
        # progress omits this source before calling the helper when its run history has no terminal event.
        source_activities = []
        expected_ids = set()
    else:
        source_activities = [source]
        expected_ids = {"source-a"}
    assert _resolve(
        source,
        clone,
        history,
        run_sequence=run_sequence,
        source_activities=source_activities,
    ) == expected_ids


@pytest.mark.parametrize(
    "mutation",
    [
        "changed_place",
        "changed_activity_type",
        "changed_start_at",
        "changed_end_at",
        "not_completed",
        "free_time",
        "missing_place",
        "malformed_clone_metadata",
        "missing_execution_truth",
        "clone_truth_mismatch",
    ],
)
def test_active_copy_must_match_the_completed_source_exactly(mutation):
    _, source, clone, history = _fixture()

    if mutation == "changed_place":
        clone["place_id"] = "different-canonical-place"
    elif mutation == "changed_activity_type":
        clone["activity_type"] = "MEAL"
    elif mutation == "changed_start_at":
        clone["start_at"] = "2026-12-03T09:31:00+08:00"
    elif mutation == "changed_end_at":
        clone["end_at"] = "2026-12-03T10:31:00+08:00"
    elif mutation == "not_completed":
        clone["status"] = "PLANNED"
    elif mutation == "free_time":
        clone["activity_type"] = "FREE_TIME"
    elif mutation == "missing_place":
        clone["place_id"] = None
    elif mutation == "malformed_clone_metadata":
        clone["metadata_json"] = "{malformed"
    elif mutation == "missing_execution_truth":
        clone["metadata_json"] = json.dumps({"other": "metadata"})
    elif mutation == "clone_truth_mismatch":
        metadata = json.loads(clone["metadata_json"])
        metadata["execution_truth"]["evidence"]["recorded_at"] = "different-recording"
        clone["metadata_json"] = json.dumps(metadata)

    assert _resolve(source, clone, history) == {"source-a"}


def test_unplaced_source_id_does_not_count_as_named_place_coverage():
    _, source, clone, history = _fixture()
    source["place_id"] = None
    clone["place_id"] = None

    run_ids = _resolve(source, clone, history)
    days = summarize_activity_coverage(
        [source, clone],
        run_ids,
        journey_timezone="Asia/Shanghai",
    )

    assert run_ids == {"source-a"}
    assert days[0]["distinct_place_count"] == 0
    assert days[0]["run_completed_place_count"] == 0


def test_duplicate_place_copies_do_not_increase_daily_place_count():
    _, source, first_clone, history = _fixture()
    second_clone = copy.deepcopy(first_clone)
    second_clone["id"] = "clone-b"
    second_clone["sequence_no"] = 2

    run_ids = resolve_run_completed_activity_ids(
        run_id=RUN_ID,
        run_sequence=RUN_SEQUENCE,
        run_actor_id=RUN_ACTOR_ID,
        history=history,
        source_activities=[source],
        active_activities=[first_clone, second_clone],
    )
    days = summarize_activity_coverage(
        [first_clone, second_clone],
        run_ids,
        journey_timezone="Asia/Shanghai",
    )

    assert run_ids == {"source-a", "clone-a", "clone-b"}
    assert days[0]["run_completed_activity_ids"] == ["clone-a", "clone-b"]
    assert days[0]["run_completed_place_count"] == 1


def _add_place(session, place_id: str, stamp: str, *, name: str) -> None:
    session.add(
        Place(
            id=place_id,
            provider_key="TEST_FIXTURE_" + uuid4().hex,
            external_id=place_id,
            city_code="CN-BJ",
            name=name,
            category="PARK",
            latitude=39.8,
            longitude=116.4,
            opening_hours_json="{}",
            tags_json="[]",
            metadata_json="{}",
            updated_at=stamp,
        )
    )


def _activity_copy(source: Activity, plan_id: str, sequence_no: int, stamp: str) -> Activity:
    return Activity(
        id=str(uuid4()),
        plan_version_id=plan_id,
        sequence_no=sequence_no,
        activity_type=source.activity_type,
        title=source.title,
        place_id=source.place_id,
        start_at=source.start_at,
        end_at=source.end_at,
        travel_from_prev_min=source.travel_from_prev_min or 0,
        estimated_cost_minor=source.estimated_cost_minor or 0,
        currency=source.currency,
        status="COMPLETED",
        locked=source.locked,
        metadata_json=source.metadata_json,
        created_at=stamp,
        updated_at=stamp,
    )


_READ_ONLY_SNAPSHOT_FIELDS = (
    (
        SimulationRun,
        (
            "id",
            "journey_id",
            "sequence",
            "status",
            "virtual_now",
            "state_json",
            "history_json",
            "updated_at",
        ),
    ),
    (Activity, ("id", "plan_version_id", "sequence_no", "status", "metadata_json", "updated_at")),
    (
        AgentRun,
        ("id", "journey_id", "mission_id", "status", "outcome", "failure_reason", "completed_at"),
    ),
    (AgentRunStep, ("id", "run_id", "sequence_no", "status", "result_json", "completed_at")),
    (
        ProviderObservation,
        ("id", "journey_id", "provider_key", "observation_type", "state", "payload_json", "created_at"),
    ),
    (
        ProviderCall,
        ("id", "provider_key", "operation", "request_json", "response_json", "status", "created_at"),
    ),
)


def _read_only_snapshot(factory) -> dict[str, list[tuple]]:
    generator = factory()
    session = next(generator)
    try:
        return {
            model.__tablename__: [
                tuple(getattr(row, field) for field in fields)
                for row in session.scalars(select(model).order_by(model.id))
            ]
            for model, fields in _READ_ONLY_SNAPSHOT_FIELDS
        }
    finally:
        generator.close()


def test_signed_progress_counts_same_run_copies_and_get_is_read_only(sim):
    client, ids, _, factory, headers, url, post = sim
    generator = factory()
    session = next(generator)
    stamp = datetime.now(timezone.utc).isoformat()
    journey = session.get(Journey, ids["journey"])
    original_sources = list(
        session.scalars(
            select(Activity)
            .where(Activity.plan_version_id == ids["plan"])
            .order_by(Activity.sequence_no)
        )
    )
    assert len(original_sources) == 2

    day_one = datetime.fromisoformat(journey.start_at)
    day_two = day_one + timedelta(days=1)
    original_sources[1].start_at = "2026-12-03T14:00:00+08:00"
    original_sources[1].end_at = "2026-12-03T15:00:00+08:00"
    original_sources[1].updated_at = stamp

    added_sources = []
    for sequence_no, start_at, end_at in (
        (3, day_two.replace(hour=9, minute=30).isoformat(), day_two.replace(hour=10, minute=30).isoformat()),
        (4, day_two.replace(hour=14, minute=0).isoformat(), day_two.replace(hour=15, minute=0).isoformat()),
    ):
        place_id = str(uuid4())
        activity_id = str(uuid4())
        _add_place(session, place_id, stamp, name=f"Synthetic station {sequence_no}")
        activity = Activity(
            id=activity_id,
            plan_version_id=ids["plan"],
            sequence_no=sequence_no,
            activity_type="SIGHTSEE",
            title=f"Synthetic station {sequence_no}",
            place_id=place_id,
            start_at=start_at,
            end_at=end_at,
            travel_from_prev_min=10,
            estimated_cost_minor=0,
            currency="CNY",
            status="PLANNED",
            locked=False,
            metadata_json="{}",
            created_at=stamp,
            updated_at=stamp,
        )
        session.add(activity)
        added_sources.append(activity)

    source_rows = [*original_sources, *added_sources]
    ids["activities"] = [row.id for row in source_rows]
    session.commit()
    generator.close()

    started = post(url, {"seed": 49}, "coverage-copy-start")
    assert started.status_code == 201, started.text
    run_id = started.json()["run_id"]
    latest = started.json()
    for expected_sequence in range(16):
        latest_response = post(
            url + "/" + run_id + "/advance",
            {"expected_sequence": expected_sequence},
            f"coverage-copy-step-{expected_sequence}",
        )
        assert latest_response.status_code == 200, latest_response.text
        latest = latest_response.json()
    assert latest["status"] == "SIMULATED_COMPLETED"
    assert len(latest["state"]["completed_activity_ids"]) == 4

    original_progress = client.get(url + "/" + run_id + "/progress", headers=headers)
    assert original_progress.status_code == 200, original_progress.text
    original_coverage = original_progress.json()["activity_coverage"]
    assert original_coverage["plan_version_id"] == ids["plan"]
    assert [day["run_completed_place_count"] for day in original_coverage["days"]] == [2, 2, 0]

    generator = factory()
    session = next(generator)
    journey = session.get(Journey, ids["journey"])
    run = session.get(SimulationRun, run_id)
    source_rows = list(
        session.scalars(
            select(Activity)
            .where(Activity.plan_version_id == ids["plan"])
            .order_by(Activity.sequence_no)
        )
    )
    accepted_plan_id = str(uuid4())
    accepted_plan = PlanVersion(
        id=accepted_plan_id,
        journey_id=journey.id,
        version_no=2,
        planning_mode="BALANCED",
        status="ACTIVE",
        source="TEST_ACCEPTED_COPY",
        total_cost_minor=0,
        currency="CNY",
        estimated_duration_min=240,
        created_at=stamp,
    )
    session.add(accepted_plan)
    session.flush()
    journey.active_plan_version_id = accepted_plan_id
    journey.status = "ACTIVE"
    journey.current_activity_id = None
    clone_rows = []
    for sequence_no, source in enumerate(source_rows, start=1):
        clone = _activity_copy(source, accepted_plan_id, sequence_no, stamp)
        session.add(clone)
        clone_rows.append(clone)

    # Add a forged-but-well-shaped foreign-Journey source and matching active copy.
    # The history and state IDs alone must not let it cross the PlanVersion Journey boundary.
    foreign_journey_id = str(uuid4())
    foreign_plan_id = str(uuid4())
    foreign_place_id = str(uuid4())
    foreign_source_id = str(uuid4())
    foreign_clone_id = str(uuid4())
    foreign_journey = Journey(
        id=foreign_journey_id,
        traveler_id=ids["owner"],
        title="Foreign source fixture",
        city_code="CN-BJ",
        timezone="Asia/Shanghai",
        start_at="2026-12-03T09:00:00+08:00",
        end_at="2026-12-05T09:00:00+08:00",
        budget_currency="CNY",
        budget_amount_minor=30000,
        status="ACTIVE",
        created_at=stamp,
        updated_at=stamp,
    )
    session.add(foreign_journey)
    session.flush()
    session.add(
        PlanVersion(
            id=foreign_plan_id,
            journey_id=foreign_journey_id,
            version_no=1,
            planning_mode="BALANCED",
            status="ACTIVE",
            source="TEST_FOREIGN_SOURCE",
            total_cost_minor=0,
            currency="CNY",
            estimated_duration_min=60,
            created_at=stamp,
        )
    )
    session.flush()
    foreign_journey.active_plan_version_id = foreign_plan_id
    _add_place(session, foreign_place_id, stamp, name="Foreign synthetic station")

    source_truth = json.loads(source_rows[0].metadata_json)["execution_truth"]
    foreign_metadata = json.dumps({"execution_truth": source_truth})
    foreign_source = Activity(
        id=foreign_source_id,
        plan_version_id=foreign_plan_id,
        sequence_no=1,
        activity_type="SIGHTSEE",
        title="Foreign synthetic station",
        place_id=foreign_place_id,
        start_at="2026-12-05T08:00:00+08:00",
        end_at="2026-12-05T09:00:00+08:00",
        travel_from_prev_min=0,
        estimated_cost_minor=0,
        currency="CNY",
        status="COMPLETED",
        locked=False,
        metadata_json=foreign_metadata,
        created_at=stamp,
        updated_at=stamp,
    )
    foreign_clone = Activity(
        id=foreign_clone_id,
        plan_version_id=accepted_plan_id,
        sequence_no=5,
        activity_type=foreign_source.activity_type,
        title=foreign_source.title,
        place_id=foreign_source.place_id,
        start_at=foreign_source.start_at,
        end_at=foreign_source.end_at,
        travel_from_prev_min=0,
        estimated_cost_minor=0,
        currency="CNY",
        status="COMPLETED",
        locked=False,
        metadata_json=foreign_metadata,
        created_at=stamp,
        updated_at=stamp,
    )
    session.add_all([foreign_source, foreign_clone])

    history = json.loads(run.history_json)
    matching_history = next(
        item
        for item in history
        if item.get("event") == "SIM_ACTIVITY_COMPLETED"
        and item.get("activity_id") == source_rows[0].id
    )
    foreign_history = copy.deepcopy(matching_history)
    foreign_history["activity_id"] = foreign_source_id
    history.append(foreign_history)
    state = json.loads(run.state_json)
    state["completed_activity_ids"] = [
        *state["completed_activity_ids"],
        foreign_source_id,
    ]
    run.history_json = json.dumps(history)
    run.state_json = json.dumps(state)
    journey.updated_at = stamp
    clone_ids = [row.id for row in clone_rows]
    session.commit()
    generator.close()

    before = _read_only_snapshot(factory)
    response = client.get(url + "/" + run_id + "/progress", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    coverage = body["activity_coverage"]
    assert coverage["plan_version_id"] == accepted_plan_id
    assert [day["date"] for day in coverage["days"]] == [
        "2026-12-03",
        "2026-12-04",
        "2026-12-05",
    ]
    days = coverage["days"]
    assert [day["run_completed_place_count"] for day in days] == [2, 2, 0]
    assert set(days[0]["run_completed_activity_ids"]) == set(clone_ids[:2])
    assert set(days[1]["run_completed_activity_ids"]) == set(clone_ids[2:4])
    assert days[2]["run_completed_activity_ids"] == []
    assert days[2]["inherited_completed_activity_ids"] == [foreign_clone_id]
    assert foreign_clone_id not in {
        activity_id
        for day in days
        for activity_id in day["run_completed_activity_ids"]
    }
    assert _read_only_snapshot(factory) == before
