from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import app.main as main_module
from app.db.models import Activity, JourneyMission, Place, ProviderObservation
from app.db.session import SessionLocal
from app.collective_mediation import collective_decision_epoch, decision_material_snapshot
from tests.test_r29_disagreement_mediation import _seed_r29_disagreement_http_fixture, _now


def _material_place(place_id: str) -> Place:
    return Place(
        id=place_id,
        provider_key="r30-provider",
        external_id=place_id,
        city_code="NARA",
        name="R30 selected place",
        category="garden",
        latitude=34.68,
        longitude=135.84,
        opening_hours_json=json.dumps({"status": "NORMALIZED_VALID", "open": "09:00", "close": "17:00"}),
        tags_json=json.dumps(["garden"]),
        metadata_json=json.dumps({"cost_evidence": {"status": "VERIFIED_PROVIDER", "amount_minor": 500}}),
        updated_at=_now(),
    )


def test_r30_epoch_changes_for_material_place_fact_but_ignores_unrelated_churn() -> None:
    seeded = _seed_r29_disagreement_http_fixture()
    selected_plan_id = str(seeded["options"][0]["plan_id"])
    options = list(seeded["options"])
    with SessionLocal() as session:
        place_id = str(uuid4())
        session.add(_material_place(place_id))
        session.flush()
        session.add(
            Activity(
                id=str(uuid4()),
                plan_version_id=selected_plan_id,
                sequence_no=1,
                activity_type="visit",
                title="R30 selected place",
                place_id=place_id,
                city_service_id=None,
                start_at="2026-10-08T10:00:00+00:00",
                end_at="2026-10-08T11:00:00+00:00",
                travel_from_prev_min=0,
                estimated_cost_minor=500,
                currency="JPY",
                status="PLANNED",
                locked=False,
                metadata_json=json.dumps({"semantic_key": place_id}),
                created_at=_now(),
                updated_at=_now(),
            )
        )
        session.flush()
        material = decision_material_snapshot(
            session,
            journey_id=str(seeded["journey_id"]),
            base_plan_version_id=str(seeded["base_id"]),
            options=options,
            selected_proposal_id=str(seeded["garden_proposal_id"]),
            selected_plan_version_id=selected_plan_id,
        )
        epoch_before = collective_decision_epoch(
            journey_id=str(seeded["journey_id"]),
            mission_id=str(seeded["parent_id"]),
            trigger_event_id=str(seeded["event_id"]),
            base_plan_version_id=str(seeded["base_id"]),
            options=options,
            required_member_ids=[str(seeded["owner_member_id"]), str(seeded["admin_member_id"])],
            members=[],
            decision_material=material,
        )
        session.add(
            ProviderObservation(
                id=str(uuid4()),
                journey_id=str(seeded["journey_id"]),
                provider_key="irrelevant-provider",
                observation_type="WEATHER",
                state="CAPTURED",
                incident_fingerprint="irrelevant",
                provenance="PROVIDER_VERIFIED",
                captured_at=_now(),
                expires_at=None,
                payload_json=json.dumps({"unrelated_place": str(uuid4()), "temperature": 20}),
                created_at=_now(),
            )
        )
        session.flush()
        unchanged_material = decision_material_snapshot(
            session,
            journey_id=str(seeded["journey_id"]),
            base_plan_version_id=str(seeded["base_id"]),
            options=options,
            selected_proposal_id=str(seeded["garden_proposal_id"]),
            selected_plan_version_id=selected_plan_id,
        )
        epoch_unchanged = collective_decision_epoch(
            journey_id=str(seeded["journey_id"]),
            mission_id=str(seeded["parent_id"]),
            trigger_event_id=str(seeded["event_id"]),
            base_plan_version_id=str(seeded["base_id"]),
            options=options,
            required_member_ids=[str(seeded["owner_member_id"]), str(seeded["admin_member_id"])],
            members=[],
            decision_material=unchanged_material,
        )
        assert epoch_unchanged == epoch_before
        place = session.get(Place, place_id)
        place.opening_hours_json = json.dumps({"status": "CLOSED", "open": None, "close": None})
        session.flush()
        changed_material = decision_material_snapshot(
            session,
            journey_id=str(seeded["journey_id"]),
            base_plan_version_id=str(seeded["base_id"]),
            options=options,
            selected_proposal_id=str(seeded["garden_proposal_id"]),
            selected_plan_version_id=selected_plan_id,
        )
        epoch_changed = collective_decision_epoch(
            journey_id=str(seeded["journey_id"]),
            mission_id=str(seeded["parent_id"]),
            trigger_event_id=str(seeded["event_id"]),
            base_plan_version_id=str(seeded["base_id"]),
            options=options,
            required_member_ids=[str(seeded["owner_member_id"]), str(seeded["admin_member_id"])],
            members=[],
            decision_material=changed_material,
        )
        assert epoch_changed != epoch_before


def test_r30_gate_rejects_feasible_selected_plan_when_consent_epoch_is_stale(monkeypatch) -> None:
    seeded = _seed_r29_disagreement_http_fixture()
    selected_plan_id = str(seeded["options"][0]["plan_id"])
    selected_proposal_id = str(seeded["garden_proposal_id"])
    options = list(seeded["options"])
    now = _now()
    with SessionLocal() as session:
        place_id = str(uuid4())
        session.add(_material_place(place_id))
        session.flush()
        session.add(
            Activity(
                id=str(uuid4()), plan_version_id=selected_plan_id, sequence_no=1,
                activity_type="visit", title="R30 selected place", place_id=place_id,
                city_service_id=None, start_at="2026-10-08T10:00:00+00:00",
                end_at="2026-10-08T11:00:00+00:00", travel_from_prev_min=0,
                estimated_cost_minor=500, currency="JPY", status="PLANNED", locked=False,
                metadata_json=json.dumps({"semantic_key": place_id}), created_at=now, updated_at=now,
            )
        )
        session.flush()
        material = decision_material_snapshot(
            session, journey_id=str(seeded["journey_id"]),
            base_plan_version_id=str(seeded["base_id"]), options=options,
            selected_proposal_id=selected_proposal_id, selected_plan_version_id=selected_plan_id,
        )
        old_epoch = collective_decision_epoch(
            journey_id=str(seeded["journey_id"]), mission_id=str(uuid4()),
            trigger_event_id=str(seeded["event_id"]), base_plan_version_id=str(seeded["base_id"]),
            options=options, required_member_ids=[str(seeded["owner_member_id"]), str(seeded["admin_member_id"])],
            members=[], decision_material=material,
        )
        mediator_id = str(uuid4())
        session.add(
            JourneyMission(
                id=mediator_id, journey_id=str(seeded["journey_id"]), traveler_id=str(seeded["owner_id"]),
                trigger_event_id=str(seeded["event_id"]), parent_mission_id=str(seeded["parent_id"]),
                user_text="R30 resolved authority", requested_autonomy="EXECUTE_WITHIN_BOUNDS", status="ANSWERED",
                resolved_intent_json=json.dumps({"collective_mediation": {"kind": "DISAGREEMENT_MEDIATION", "round": 2}}, sort_keys=True),
                clarification_json=json.dumps({
                    "kind": "COLLECTIVE_TRADEOFF", "status": "RESOLVED", "clarification_id": "r30-resolved",
                    "decision_epoch": old_epoch, "consent_epoch": old_epoch,
                    "trigger_event_id": str(seeded["event_id"]), "base_plan_version_id": str(seeded["base_id"]),
                    "candidate_options": options, "required_member_ids": [str(seeded["owner_member_id"]), str(seeded["admin_member_id"])],
                    "selected_proposal_id": selected_proposal_id, "selected_candidate_id": selected_proposal_id,
                }, sort_keys=True),
                created_at=now, started_at=now, completed_at=now,
            )
        )
        session.commit()
        monkeypatch.setattr(main_module, "collective_proposal_receipt", lambda *_args, **_kwargs: {
            "proposal_collective_decisions": {item["proposal_id"]: item for item in options},
        })
        monkeypatch.setattr(main_module, "active_journey_members_with_capabilities", lambda _s, _j, **kwargs: (
            {"member_count": 2, "members": []} if kwargs.get("candidate_windows") is None else {
                "member_count": 2, "members": [], "candidate_fit_matrix": [],
                "mediation": {"classification": "COMPROMISE_AVAILABLE", "candidate_ids": [selected_plan_id], "selected_candidate_id": selected_plan_id},
            }
        ))
        place = session.get(Place, place_id)
        place.opening_hours_json = json.dumps({"status": "CLOSED"})
        journey = session.get(main_module.Journey, str(seeded["journey_id"]))
        selected_plan = session.get(main_module.PlanVersion, selected_plan_id)
        gate = main_module.collective_mutation_gate(session, journey, selected_plan, hard_feasible_plan_ids={selected_plan_id})
        assert gate["allowed"] is False
        assert gate["code"] == "COLLECTIVE_CONSENT_EPOCH_STALE"
        assert gate["classification"] == "RENEWED_COLLECTIVE_CONSENT_STALE"
