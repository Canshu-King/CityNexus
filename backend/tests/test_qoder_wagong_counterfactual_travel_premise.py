"""A counterfactual must not move an anchor by a leg nobody routed.

`_scenario_problem` builds the frozen travel matrix the what-if solver moves real C4 anchors
with.  It used to read

    int(current_minutes.get(f"{origin}|{destination}", 15)) + scenario_delta

so every origin/destination pair the guardian's mobility observation did not cover was filled
with 15 minutes.  That number is not a slow route or a fast one; it is a value this build made
up, and it entered the solver beside `frozen_mobility_snapshot_id` -- the field whose whole job
is to name the evidence the numbers came from.  The solver then published
`feasible=true`, `c4_preserved=true` and a `schedule_drift_min` measured against those invented
legs, all under a problem fingerprint, on a row a later caller reads as a fact about the
traveller's trip.

Measured on the offline demo journey (six activities, `POST /resilience/refresh`): the MOBILITY
observation carried 0 pairs, the matrix carried 36, and 30 of them sat at exactly the invented
15.  In the seeded predictive flow it was 5 evidenced pairs against 76 invented.  `feasible`
was true and `c4_preserved` true in both.

There is no honest substitute figure, so the scenario declines and says which gap it hit.  The
distinction that matters downstream: "this trip cannot be rerouted" (INFEASIBLE) is a verdict
about the traveller; "we never asked the provider about these routes" (PREMISE_NOT_EVIDENCED)
is a statement about this build.  Collapsing them tells a traveller their trip is impossible
when the truth is that nobody looked.

These arms are behavioural: each one drives the real endpoint and reads the payload a consumer
receives.  None of them greps the source for the literal 15.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.db.models import Journey, ProviderObservation
from app.db.session import SessionLocal
from app.agent.autorun import stop_autorun
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)
from sqlalchemy import select

client = TestClient(main_module.app)

SCENARIO_KEYS = {
    "rain_earlier",
    "route_plus_10",
    "route_plus_20",
    "route_plus_30",
    "mutable_place_closes",
    "replacement_disappears",
}


@pytest.fixture
def started_journey() -> str:
    """A running demo journey with a selected plan and no mobility observation of its own."""

    stop_autorun()
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    journey_id = ids["journey_id"]
    plan = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 1}
    ).json()[0]
    assert client.post(
        f"/api/v1/journeys/{journey_id}/plans/{plan['id']}/select"
    ).status_code == 200
    assert client.post(f"/api/v1/journeys/{journey_id}/start").status_code == 200
    return journey_id


def _counterfactuals(journey_id: str) -> list[dict]:
    response = client.get(f"/api/v1/journeys/{journey_id}/resilience/counterfactuals")
    assert response.status_code == 200, response.text
    return response.json()["counterfactuals"]


def _refresh(journey_id: str) -> dict:
    response = client.post(
        f"/api/v1/journeys/{journey_id}/resilience/refresh", json={"mode": "replay"}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_every_scenario_reports_its_premise_not_an_invented_leg(
    started_journey: str,
) -> None:
    """All six scenarios decline with a named reason, and each states its coverage.

    This is the arm the defect is named by: on tip-bytes each row reports `feasible=true`
    with a 90-minute drift derived from legs nobody routed.
    """

    _refresh(started_journey)
    rows = _counterfactuals(started_journey)
    assert len(rows) == 6
    assert {row["scenario_key"] for row in rows} == SCENARIO_KEYS

    for row in rows:
        key = row["scenario_key"]
        evidence = row["evidence"]
        premise = evidence["premise"]
        assert evidence["solver_status"] == "PREMISE_NOT_EVIDENCED", key
        assert evidence["premise_holds"] is False, key
        assert premise["complete"] is False, key
        assert premise["reason"] == "MOBILITY_NOT_OBSERVED", key
        assert premise["observed"] is False, key
        # The shortfall is counted, not hidden: this journey had 0 evidenced pairs and every
        # origin/destination pair the scenario would move is therefore unbacked.
        assert premise["required_pairs"] > 0, key
        assert premise["evidenced_pairs"] == 0, key
        assert premise["missing_pair_count"] == premise["required_pairs"], key


def test_an_unanswered_scenario_publishes_no_verdict_numbers(
    started_journey: str,
) -> None:
    """A declined scenario reports nulls, not zeros.

    A 0 in `cost_delta_minor` reads downstream as "switching costs nothing" and in
    `schedule_drift_min` as "disrupts nothing" -- verdicts about a trip nobody routed.
    """

    _refresh(started_journey)
    for row in _counterfactuals(started_journey):
        key = row["scenario_key"]
        assert row["answered"] is False, key
        assert row["feasible"] is None, f"{key}: a declined scenario is not 'infeasible'"
        assert row["c4_preserved"] is None, key
        assert row["cost_delta_minor"] is None, key
        assert row["schedule_drift_min"] is None, key
        assert row["plan_changes"] is None, key


def test_the_previous_verdict_words_are_gone(
    started_journey: str,
) -> None:
    """`INFEASIBLE` and `NO_FEASIBLE_PLAN` must not stand in for "we never asked"."""

    _refresh(started_journey)
    for row in _counterfactuals(started_journey):
        evidence = row["evidence"]
        assert evidence["solver_status"] != "INFEASIBLE", row["scenario_key"]
        assert evidence["solver_kind"] != "NO_FEASIBLE_PLAN", row["scenario_key"]
        assert evidence["problem_fingerprint"] is None, row["scenario_key"]


def test_the_risk_fact_is_kept_while_the_what_if_is_withheld(
    started_journey: str,
) -> None:
    """Withholding the what-if must not also throw away the journey's own risk score.

    `expected_failure_risk` is read off the resilience snapshot, which is a fact about the
    traveller's journey whether or not a scenario could be run against it. Blanket nulling
    would be the other half of the same dishonesty.
    """

    body = _refresh(started_journey)
    score = body["snapshot"]["score"]
    for row in _counterfactuals(started_journey):
        assert row["evidence"]["expected_failure_risk"] == round(score / 100, 3)


def _active_place_ids(session, journey) -> list[str]:
    """The location keys the counterfactual matrix is built from, in `_location` order.

    `_location` is `place_id or city_service_id or activity.id`, so an activity with neither a
    place nor a service still contributes a key.  Reading them through the same expression keeps
    this arm from quietly covering a different pair set than the product asks for.
    """

    from app.agent.predictive import _location
    from app.db.models import Activity

    activities = list(
        session.scalars(
            select(Activity).where(Activity.plan_version_id == journey.active_plan_version_id)
        )
        .unique()
        .all()
    )
    return [_location(item) for item in activities]


def _latest_capture(session, journey_id: str) -> str:
    row = session.scalars(
        select(ProviderObservation)
        .where(
            ProviderObservation.journey_id == journey_id,
            ProviderObservation.observation_type == "MOBILITY",
        )
        .order_by(ProviderObservation.captured_at.desc())
    ).first()
    return row.captured_at if row is not None else "2999-01-01T00:00:00+00:00"


def _observe(session, journey, pairs: dict[str, int], *, provider_key: str, snapshot_id: str) -> None:
    from uuid import uuid4

    stamp = _latest_capture(session, journey.id)
    session.add(
        ProviderObservation(
            id=str(uuid4()),
            journey_id=journey.id,
            provider_key=provider_key,
            observation_type="MOBILITY",
            state="CAPTURED",
            provenance="PROVIDER_VERIFIED",
            captured_at=stamp,
            created_at=stamp,
            payload_json=json.dumps(
                {
                    "snapshot_id": snapshot_id,
                    "current_minutes": pairs,
                    "meaningful_deltas": [],
                }
            ),
        )
    )
    session.commit()


def test_a_fully_covered_scenario_still_solves_and_keeps_the_three_state(
    started_journey: str,
) -> None:
    """The refusal is about missing evidence, not about refusing what-ifs.

    Writes a MOBILITY observation covering every pair the scenario needs, then reads the
    payload again: the scenario must solve, publish numbers, and report `answered=true` --
    so the honest path is not a blanket "no" wearing a better vocabulary.
    """

    _refresh(started_journey)
    before = _counterfactuals(started_journey)
    assert {row["evidence"]["solver_status"] for row in before} == {"PREMISE_NOT_EVIDENCED"}

    with SessionLocal() as session:
        journey = session.get(Journey, started_journey)
        assert journey is not None
        keys = _active_place_ids(session, journey)
        wanted = [(o, d) for o in keys for d in keys if o != d]
        assert wanted, "the demo journey must have at least one routable leg"
        assert before[0]["evidence"]["premise"]["missing_pair_count"] == len(wanted)
        _observe(
            session,
            journey,
            {f"{o}|{d}": 10 + index for index, (o, d) in enumerate(wanted)},
            provider_key="arm-mobility",
            snapshot_id="arm-snapshot",
        )

    _refresh(started_journey)
    for row in _counterfactuals(started_journey):
        key = row["scenario_key"]
        evidence = row["evidence"]
        premise = evidence["premise"]
        assert premise["complete"] is True, key
        assert evidence["premise_holds"] is True, key
        assert premise["reason"] is None, key
        assert premise["observed"] is True, key
        assert premise["evidenced_pairs"] == premise["required_pairs"], key
        assert premise["missing_pair_count"] == 0, key
        assert row["answered"] is True, key
        # A real what-if gets a real fingerprint and a named status; it is never the refusal.
        assert evidence["problem_fingerprint"] is not None, key
        assert evidence["solver_status"] in {"FEASIBLE", "INFEASIBLE"}, key
        assert isinstance(row["feasible"], bool), key
        assert isinstance(row["cost_delta_minor"], int), key


def test_a_partially_covered_matrix_is_refused_named_as_incomplete(
    started_journey: str,
) -> None:
    """Some evidence is not enough, and it must not be reported as "never asked".

    Half the pairs covered says the provider answered and did not cover this route, which is a
    different defect from having no observation at all -- and a caller that retries on
    NOT_OBSERVED would wait forever for one that INCOMPLETE tells it to go and capture.
    """

    _refresh(started_journey)
    before = _counterfactuals(started_journey)
    assert before[0]["evidence"]["premise"]["missing_pair_count"] > 1

    with SessionLocal() as session:
        journey = session.get(Journey, started_journey)
        assert journey is not None
        keys = _active_place_ids(session, journey)
        wanted = [(o, d) for o in keys for d in keys if o != d]
        assert before[0]["evidence"]["premise"]["missing_pair_count"] == len(wanted)
        half = len(wanted) // 2
        _observe(
            session,
            journey,
            {f"{o}|{d}": 12 for o, d in wanted[:half]},
            provider_key="arm-partial-mobility",
            snapshot_id="arm-partial",
        )

    _refresh(started_journey)
    for row in _counterfactuals(started_journey):
        premise = row["evidence"]["premise"]
        assert premise["observed"] is True, row["scenario_key"]
        assert premise["reason"] == "MOBILITY_PREMISE_INCOMPLETE", row["scenario_key"]
        assert premise["evidenced_pairs"] == len(wanted[:half]), row["scenario_key"]
        assert premise["missing_pair_count"] == len(wanted) - len(wanted[:half])
        assert row["answered"] is False, row["scenario_key"]
        assert row["feasible"] is None, row["scenario_key"]

