"""A closure keeps the leg the selected plan already measured.

The runtime capture used to relay the mock fixture's blanket constant for a pair the active plan had
measured with a live provider, so replan refused a leg the traveller had already walked with
``MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE``.  A closure changes whether a place is usable, not how long
the places that remain take to reach.  These cases pin that reading: a measured plan fact survives a
mock relay, a fresher live capture still wins, a traffic event never reuses a stale measurement, and
a synthetic plan fact never becomes hard truth by way of this path.
"""

from __future__ import annotations

import pytest

from app.integrations.mobility.snapshot_capture import MobilitySnapshotCaptureResult
from app.main import _reuse_measured_baseline_mobility
from app.replanning.provider_snapshots import (
    EXPLICIT_FROZEN_FIXTURE,
    LIVE_PROVIDER_CAPTURE,
    SYNTHETIC_DEFAULT,
    MobilitySnapshot,
    TravelEstimateFact,
)

STAMP = "2026-10-24T21:49:30+00:00"
PAIR = ("real-place-00d9e27cd4cc6c7b28b6509e", "real-place-62c2e60619da82efebfdea8c")


def _base(quality: str, minutes: int = 78) -> dict:
    return {
        "snapshot_id": "base-snapshot",
        "facts": [
            {
                "origin_key": PAIR[0],
                "destination_key": PAIR[1],
                "minutes": minutes,
                "provider": "amap_walking",
                "captured_at": STAMP,
                "fact_quality": quality,
            }
        ],
    }


def _captured(quality: str | None, minutes: int = 20) -> MobilitySnapshotCaptureResult:
    fact = TravelEstimateFact(
        origin_key=PAIR[0],
        destination_key=PAIR[1],
        minutes=minutes,
        provider_key="mock-mobility",
        captured_at=STAMP,
        fact_quality=quality,
    )
    snapshot = MobilitySnapshot(
        facts={PAIR: fact},
        source_provider_key="mock-mobility",
        captured_at=STAMP,
        snapshot_id="captured-snapshot",
    )
    return MobilitySnapshotCaptureResult(
        snapshot=snapshot,
        failed_primary_pairs=(),
        fallback_pairs=(PAIR,),
    )


def test_closure_reuses_the_measured_leg_instead_of_the_mock_constant() -> None:
    merged = _reuse_measured_baseline_mobility(
        event_type="CLOSURE",
        captured=_captured(SYNTHETIC_DEFAULT),
        base_evidence=_base(LIVE_PROVIDER_CAPTURE),
        operation_seed="trigger-1",
    )

    assert merged.snapshot.hard_minutes(*PAIR) == 78
    assert merged.snapshot.facts[PAIR].provider_key == "amap_walking"
    assert merged.snapshot.provider_capabilities["baseline_reuse"]["reused_pairs"] == 1
    assert merged.fallback_pairs == ()
    assert merged.snapshot.snapshot_id.startswith("replan-baseline-merged-")


def test_a_fresher_live_capture_still_wins() -> None:
    merged = _reuse_measured_baseline_mobility(
        event_type="CLOSURE",
        captured=_captured(LIVE_PROVIDER_CAPTURE, minutes=90),
        base_evidence=_base(LIVE_PROVIDER_CAPTURE),
        operation_seed="trigger-2",
    )

    assert merged.snapshot.hard_minutes(*PAIR) == 90
    assert "baseline_reuse" not in merged.snapshot.provider_capabilities


def test_traffic_event_never_reuses_a_stale_measurement() -> None:
    merged = _reuse_measured_baseline_mobility(
        event_type="TRAFFIC_DELAY",
        captured=_captured(SYNTHETIC_DEFAULT),
        base_evidence=_base(LIVE_PROVIDER_CAPTURE),
        operation_seed="trigger-3",
    )

    with pytest.raises(KeyError):
        merged.snapshot.hard_minutes(*PAIR)


def test_a_synthetic_plan_fact_never_becomes_hard_truth() -> None:
    merged = _reuse_measured_baseline_mobility(
        event_type="CLOSURE",
        captured=_captured(SYNTHETIC_DEFAULT),
        base_evidence=_base(SYNTHETIC_DEFAULT),
        operation_seed="trigger-4",
    )

    with pytest.raises(KeyError):
        merged.snapshot.hard_minutes(*PAIR)


def test_an_explicit_frozen_fixture_is_eligible_too() -> None:
    merged = _reuse_measured_baseline_mobility(
        event_type="WEATHER",
        captured=_captured(None),
        base_evidence=_base(EXPLICIT_FROZEN_FIXTURE, minutes=12),
        operation_seed="trigger-5",
    )

    assert merged.snapshot.hard_minutes(*PAIR) == 12
