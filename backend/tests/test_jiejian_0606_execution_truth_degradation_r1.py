# -*- coding: utf-8 -*-
"""ORD-0606: the two degradation faces the landed wiring test does not pin.

``backend/tests/test_qoder_guiandangong_0602_execution_truth_wiring.py`` (103 lines, already on the
authoritative line) proves a well-formed attestation survives the round trip and surfaces on the
projection.  It does not prove what happens when the stored metadata *cannot* attest anything:
a row whose ``metadata_json`` was never valid JSON, and a projection that has no Now step at all
because the cursor names a step from a superseded plan.  Both must answer "there is no
attestation", and neither may invent one — the second case is the dangerous one, because a stored
record from a completed step would otherwise be shown as the traveller's present truth.
"""
from __future__ import annotations

import json

from app.db.models import Activity, JourneyLeg
from app.execution.truth import (
    DEVICE_LOCATION_VERIFIED_EXECUTION,
    append_execution_truth,
)
from app.operations.v9 import _execution_truth


def _activity(aid: str, status: str, metadata_json: str = "{}") -> Activity:
    row = Activity()
    row.id = aid
    row.title = f"step {aid}"
    row.status = status
    row.start_at = "2026-10-12T09:00:00"
    row.end_at = "2026-10-12T10:30:00"
    row.locked = False
    row.metadata_json = metadata_json
    return row


def _legs() -> list[JourneyLeg]:
    leg = JourneyLeg()
    leg.id = "leg-1"
    leg.mode = "walk"
    leg.duration_min = 12
    return [leg]


def _attested_metadata() -> str:
    metadata: dict[str, object] = {}
    append_execution_truth(
        metadata,
        kind=DEVICE_LOCATION_VERIFIED_EXECUTION,
        transition="EN_ROUTE",
        captured_at="2026-10-12T23:18:00+08:00",
        actor_type="traveler_device",
        actor_id="dev-1",
        evidence={"accuracy_m": 8.0},
    )
    return json.dumps(metadata, ensure_ascii=False)


def test_corrupt_attestation_metadata_degrades_to_none() -> None:
    # A row stored before this column carried an attestation, or written by a client that
    # put something else in it entirely. The projection must not raise and must not guess.
    projection = _execution_truth(
        [_activity("act-1", "EN_ROUTE", "not json at all"), _activity("act-2", "PENDING")],
        _legs(),
        "act-1",
    )

    assert projection["execution_truth"] is None
    assert projection["now"]["execution_truth"] is None
    assert projection["now_state"] == "EN_ROUTE"


def test_no_now_means_no_attestation_even_when_a_stale_one_is_stored() -> None:
    # A cursor naming a step that is not on this plan projects no Now. The attestation kept on
    # the completed step must not be shown as though it were the traveller's present truth.
    activities = [
        _activity("act-1", "COMPLETED", _attested_metadata()),
        _activity("act-2", "COMPLETED"),
    ]
    projection = _execution_truth(activities, _legs(), "act-from-a-superseded-plan")

    assert projection["now"] is None
    assert projection["execution_truth"] is None
