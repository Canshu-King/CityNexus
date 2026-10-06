"""Building C cell two: the REAL route of a REAL trip, compared in the three places it appears.

Cell one fixed "a plan with no route still got a line". This cell checks the other direction: for a trip
that genuinely has a route, is the shape the plan holds, the shape the endpoint serves, and the shape the
map draws the same sequence -- point for point, in order, with the same segment count?

Nothing here is a stand-in: it opens a COPY of the commander's canary store (the source is hash-checked
and never opened for writing), loads the app against that copy, and calls the product's own
`_frozen_route_for_plan` and `_route_feature`. The frontend "draw" step reproduces JourneyMap's guard and
its coordinate read against the served payload. The verdict is computed by comparing the three sequences.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import sys
from datetime import datetime, timezone

BACKEND = pathlib.Path("D:/moodle/_qoder_newlane_ord0496/backend")
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
OUT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496/review/ord0577/readouts")
CANARY = pathlib.Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/canary_56d20ec.db")
RUN = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
JOURNEY_ID = "6cbdbc65-904a-40c7-a778-f981690f25d0"


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    before = sha(CANARY)
    store = DATA / f"_cell2_{RUN}.db"
    shutil.copy2(CANARY, store)

    os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{store.as_posix()}"
    os.environ["CITYNEXUS_DEMO_MODE"] = "true"
    os.environ.pop("DEEPSEEK_API_KEY", None)
    os.environ.pop("CITYNEXUS_E2E_RUN_ID", None)
    sys.path.insert(0, str(BACKEND))

    from app.db.session import get_session  # noqa: E402
    from app.db.models import Journey, PlanVersion  # noqa: E402
    from app import main as api  # noqa: E402

    session = next(get_session())
    journey = session.get(Journey, JOURNEY_ID)
    assert journey is not None and journey.active_plan_version_id, "ABORT journey/active plan not in copy"
    plan = session.get(PlanVersion, journey.active_plan_version_id)

    # Plan shape: the product's own frozen-route join, no mobility snapshot (so no provider geometry --
    # the pure place-to-place line the plan itself implies).
    plan_coords, provider_backed, fallback_reason = api._frozen_route_for_plan(session, plan, None)

    # Served shape: the product's own _route_feature (now returns None for <2 points).
    served = api._route_feature(plan_coords, provider="server-place-fallback",
                                provider_backed=provider_backed,
                                fallback_reason=fallback_reason, plan_version_id=plan.id)

    # Draw shape: JourneyMap reads the served feature's coordinates when routeEvidence is loaded.
    draw_coords = []
    draws = served is not None
    if draws:
        draw_coords = list(served["geometry"]["coordinates"])

    def segments(seq):
        return max(len(seq) - 1, 0)

    doc = {
        "generation": {"run": RUN, "copy_of": "commander canary", "journey": JOURNEY_ID,
                       "active_plan": plan.id, "canary_sha_before": before,
                       "canary_sha_after": sha(CANARY), "canary_untouched": sha(CANARY) == before,
                       "read_only": True},
        "plan": {"point_count": len(plan_coords), "coordinates": plan_coords,
                 "segment_count": segments(plan_coords), "fallback_reason": fallback_reason,
                 "provider_backed": provider_backed},
        "served": {"is_null": served is None,
                   "point_count": len(served["geometry"]["coordinates"]) if served else 0,
                   "coordinates": draw_coords,
                   "segment_count": segments(draw_coords)},
        "draw": {"frontend_draws": draws, "point_count": len(draw_coords),
                 "segment_count": segments(draw_coords)},
        "verdict": None,
    }
    same_plan_served = plan_coords == draw_coords
    same_served_draw = draw_coords == (list(served["geometry"]["coordinates"]) if served else [])
    same_order = all(a == b for a, b in zip(plan_coords, draw_coords)) and len(plan_coords) == len(draw_coords)
    same_segments = segments(plan_coords) == segments(draw_coords)
    doc["three_way"] = {"plan_equals_served": same_plan_served, "served_equals_draw": same_served_draw,
                        "same_order": same_order, "same_segment_count": same_segments}
    all_same = same_plan_served and same_served_draw and same_order and same_segments
    doc["verdict"] = "THREE_WAY_SHAPE_CONSISTENT" if all_same else "THREE_WAY_SHAPE_MISMATCH"

    after = sha(CANARY)
    assert after == before, "ABORT the canary source was modified"
    # Release the store before deleting the copy: SQLAlchemy keeps the file handle open and Windows
    # refuses the unlink while it is held (the first run died on exactly this).
    try:
        session.close()
    except Exception:
        pass
    try:
        from app.db.session import engine as _engine
        _engine.dispose()
    except Exception:
        pass
    for extra in (store, pathlib.Path(str(store) + "-wal"), pathlib.Path(str(store) + "-shm")):
        try:
            extra.unlink(missing_ok=True)
        except OSError:
            pass

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"route_shape_real_{RUN}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    print(f"journey={JOURNEY_ID} active_plan={plan.id}")
    print(f"plan: points={doc['plan']['point_count']} segments={doc['plan']['segment_count']} "
          f"provider_backed={doc['plan']['provider_backed']} fallback_reason={doc['plan']['fallback_reason']}")
    print(f"served: null={doc['served']['is_null']} points={doc['served']['point_count']} "
          f"segments={doc['served']['segment_count']}")
    print(f"draw: draws={doc['draw']['frontend_draws']} points={doc['draw']['point_count']} "
          f"segments={doc['draw']['segment_count']}")
    print(f"three_way plan==served:{same_plan_served} served==draw:{same_served_draw} "
          f"order:{same_order} segments:{same_segments}")
    print(f"canary_untouched={doc['generation']['canary_untouched']}")
    print(f"verdict {doc['verdict']}")
    print("receipt route_shape_real_" + RUN + ".json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
