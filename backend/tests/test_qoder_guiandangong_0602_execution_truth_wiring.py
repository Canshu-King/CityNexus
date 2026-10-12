from __future__ import annotations

import json
from types import SimpleNamespace

from app.execution.truth import (
    DEVICE_LOCATION_VERIFIED_EXECUTION,
    EXECUTION_TRUTH_KINDS,
    SIMULATED_STATE_TRANSITION,
    append_execution_truth,
    current_execution_truth,
)
from app.operations.v9 import _execution_truth


def _activity(aid: str, status: str, metadata_json: str = "{}"):
    return SimpleNamespace(
        id=aid,
        title="Old Town walk",
        status=status,
        start_at="2026-10-12T09:00:00+08:00",
        end_at="2026-10-12T10:00:00+08:00",
        locked=False,
        metadata_json=metadata_json,
    )


def _leg(lid: str = "leg-1", mode: str = "WALK", duration_min: int = 7):
    return SimpleNamespace(id=lid, mode=mode, duration_min=duration_min)


def test_module_refuses_an_unknown_kind() -> None:
    for kind in ("HTTP_DEMO_OK", "SIMULATED", ""):
        try:
            append_execution_truth({}, kind=kind, transition="X", captured_at="t",
                                   actor_type="operator", actor_id=None)
        except ValueError:
            continue
        raise AssertionError("unsupported kind accepted: %r" % kind)


def test_module_round_trips_one_record_and_keeps_history_bounded() -> None:
    metadata: dict = {}
    first = append_execution_truth(
        metadata,
        kind=SIMULATED_STATE_TRANSITION,
        transition="START->EN_ROUTE",
        captured_at="2026-10-12T09:05:00+08:00",
        actor_type="operator",
        actor_id="op-1",
        evidence={"note": "demo"},
    )
    assert current_execution_truth(metadata) == first
    for i in range(30):
        last = append_execution_truth(
            metadata,
            kind=DEVICE_LOCATION_VERIFIED_EXECUTION,
            transition="EN_ROUTE->ARRIVED",
            captured_at="2026-10-12T09:%02d:00+08:00" % (i % 60),
            actor_type="device",
            actor_id="dev-1",
        )
    assert current_execution_truth(metadata) == last
    assert len(metadata["execution_truth_history"]) == 20
    assert {r["kind"] for r in metadata["execution_truth_history"]} <= EXECUTION_TRUTH_KINDS


def test_module_refuses_a_foreign_kind_already_in_metadata() -> None:
    metadata = {"execution_truth": {"kind": "HTTP_DEMO_OK", "transition": "X"}}
    assert current_execution_truth(metadata) is None
    assert current_execution_truth(None) is None
    assert current_execution_truth({"execution_truth": "not-a-dict"}) is None


def test_projection_surfaces_the_record_from_metadata_json() -> None:
    record = {
        "kind": DEVICE_LOCATION_VERIFIED_EXECUTION,
        "transition": "EN_ROUTE->ARRIVED",
        "captured_at": "2026-10-12T09:30:00+08:00",
        "actor_type": "device",
        "actor_id": "dev-1",
        "evidence": {"source": "gps"},
    }
    now = _activity("a-1", "EN_ROUTE", json.dumps({"execution_truth": record}))
    nxt = _activity("a-2", "PLANNED")
    out = _execution_truth([now, nxt], [_leg()], "a-1")
    assert out["now"]["execution_truth"] == record
    assert out["next"]["execution_truth"] is None
    assert out["execution_truth"] == record


def test_projection_is_null_when_no_record_was_written() -> None:
    out = _execution_truth([_activity("a-1", "EN_ROUTE")], [_leg()], "a-1")
    assert out["now"]["execution_truth"] is None
    assert out["execution_truth"] is None


def test_projection_does_not_trust_unparseable_metadata() -> None:
    broken = _activity("a-1", "EN_ROUTE", "{not json")
    out = _execution_truth([broken], [_leg()], "a-1")
    assert out["now"]["execution_truth"] is None
    foreign = _activity("a-2", "EN_ROUTE", json.dumps({"execution_truth": {"kind": "OPERATOR_SAID_SO"}}))
    assert _execution_truth([foreign], [_leg()], "a-2")["now"]["execution_truth"] is None
