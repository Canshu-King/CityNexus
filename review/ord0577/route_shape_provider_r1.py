"""Building C cell three: the provider-geometry branch, same three-way comparison.

Cell two drove `_frozen_route_for_plan` with no snapshot, so the line was joined from place coordinates
only. The product's real path also splices provider geometry between consecutive activities
(`fact.route_geometry`) whenever a frozen mobility snapshot carries it. This cell exercises THAT branch,
using the geometry actually stored in the canary's `mobility_facts` rows -- so the coordinates under test
are real captured ones, not invented here.

Same three-way comparison as before: the plan's own frozen route, what `_route_feature` serves, and what
the map would read from that served feature -- compared point by point, in order, by segment count.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import sqlite3
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
    store = DATA / f"_cell3_{RUN}.db"
    shutil.copy2(CANARY, store)

    # Read the real stored provider geometry straight out of the copy.
    con = sqlite3.connect(store)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "select from_key, to_key, geometry_json, provider_key, provenance, mode "
        "from mobility_facts where journey_id=?", (JOURNEY_ID,)).fetchall()
    con.close()

    os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{store.as_posix()}"
    os.environ["CITYNEXUS_DEMO_MODE"] = "true"
    os.environ.pop("DEEPSEEK_API_KEY", None)
    os.environ.pop("CITYNEXUS_E2E_RUN_ID", None)
    sys.path.insert(0, str(BACKEND))

    from app.replanning.provider_snapshots import (  # noqa: E402
        MobilitySnapshot, TravelEstimateFact,
    )
    from app.db.session import get_session  # noqa: E402
    from app.db.models import Journey, PlanVersion  # noqa: E402
    from app import main as api  # noqa: E402

    facts = {}
    geom_pairs = 0
    for r in rows:
        try:
            payload = json.loads(r["geometry_json"] or "{}")
        except json.JSONDecodeError:
            continue
        coords = (payload.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        pair = (str(r["from_key"]), str(r["to_key"]))
        facts[pair] = TravelEstimateFact(
            origin_key=pair[0], destination_key=pair[1], minutes=10,
            provider_key=r["provider_key"] or "mobility-snapshot",
            captured_at="2026-09-21T12:00:55+00:00",
            route_geometry=tuple((float(c[0]), float(c[1])) for c in coords),
            mode=r["mode"],
        )
        geom_pairs += 1
    assert geom_pairs > 0, "ABORT no stored provider geometry with >=2 points to drive the branch"

    snapshot = MobilitySnapshot(
        facts=facts, source_provider_key="citynexus-synthetic-fixture",
        captured_at="2026-09-21T12:00:55+00:00", snapshot_id="cell3-snapshot",
    )

    session = next(get_session())
    journey = session.get(Journey, JOURNEY_ID)
    plan = session.get(PlanVersion, journey.active_plan_version_id)

    # The activity keys the product will look up, in order, so the receipt can say whether the snapshot
    # actually had a fact for any consecutive pair.
    from app.db.models import Activity  # noqa: E402
    from sqlalchemy import select as _sel  # noqa: E402
    activity_pairs = [a.place_id or a.city_service_id for a in session.scalars(
        _sel(Activity).where(Activity.plan_version_id == plan.id).order_by(Activity.sequence_no)).all()]

    plan_coords, provider_backed, fallback_reason = api._frozen_route_for_plan(session, plan, snapshot)
    served = api._route_feature(plan_coords, provider=snapshot.source_provider_key,
                                provider_backed=provider_backed,
                                fallback_reason=fallback_reason, plan_version_id=plan.id)
    draw_coords = list(served["geometry"]["coordinates"]) if served else []
    draws = served is not None

    def seg(seq):
        return max(len(seq) - 1, 0)

    same_seq = plan_coords == draw_coords
    same_order = len(plan_coords) == len(draw_coords) and all(a == b for a, b in zip(plan_coords, draw_coords))
    same_segments = seg(plan_coords) == seg(draw_coords)
    # Did the branch actually splice provider geometry? A point count alone cannot tell: the plan has
    # one coordinate per activity whether or not provider geometry was spliced in. The branch fired only
    # if _frozen_route_for_plan reported provider_backed=True with no fallback reason -- that is the
    # product's own signal that it used the frozen geometry.
    spliced = bool(provider_backed) and fallback_reason is None
    # did the snapshot even have a fact for the plan's consecutive activity pairs?
    matched_pairs = 0
    for a, b in zip(activity_pairs, activity_pairs[1:]):
        if (a, b) in facts:
            matched_pairs += 1

    doc = {
        "generation": {"run": RUN, "journey": JOURNEY_ID, "active_plan": plan.id,
                       "canary_sha_before": before, "canary_sha_after": sha(CANARY),
                       "canary_untouched": sha(CANARY) == before, "read_only": True,
                       "stored_geometry_pairs_used": geom_pairs},
        "plan": {"point_count": len(plan_coords), "segment_count": seg(plan_coords),
                 "provider_backed": provider_backed, "fallback_reason": fallback_reason},
        "served": {"is_null": served is None, "point_count": len(draw_coords),
                   "segment_count": seg(draw_coords)},
        "draw": {"frontend_draws": draws, "point_count": len(draw_coords), "segment_count": seg(draw_coords)},
        "three_way": {"plan_equals_served": same_seq, "same_order": same_order,
                      "same_segment_count": same_segments},
        "branch": {"provider_geometry_available": geom_pairs > 0, "provider_backed": provider_backed,
                   "spliced": spliced, "consecutive_pairs_matched_by_snapshot": matched_pairs,
                   "verdict": "BRANCH_EXERCISED" if spliced else "BRANCH_NOT_EXERCISED"},
        "verdict": None,
    }
    all_same = same_seq and same_order and same_segments
    doc["verdict"] = "THREE_WAY_SHAPE_CONSISTENT" if all_same else "THREE_WAY_SHAPE_MISMATCH"

    after = sha(CANARY)
    assert after == before, "ABORT canary source modified"

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"route_shape_provider_{RUN}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"journey={JOURNEY_ID} stored_geometry_pairs={geom_pairs}")
    print(f"plan: points={doc['plan']['point_count']} segments={doc['plan']['segment_count']} "
          f"provider_backed={doc['plan']['provider_backed']}")
    print(f"served: points={doc['served']['point_count']} draw={draws}")
    print(f"three_way plan==served:{same_seq} order:{same_order} segments:{same_segments}")
    print(f"branch spliced={spliced} canary_untouched={doc['generation']['canary_untouched']}")
    print(f"verdict {doc['verdict']}")

    # ---- SYNTHETIC ARM (clearly not product data) -----------------------------------------------
    # The canary's stored facts belong to a different trip, so the real-data arm above leaves the
    # provider-geometry splice unexercised. This arm builds a snapshot whose keys ARE the plan's
    # consecutive activity pairs, using each pair's two endpoint coordinates as a two-point "provider"
    # geometry, so the splice branch runs for real and the three places can be compared again.
    synth_facts = {}
    for a_key, b_key in zip(activity_pairs, activity_pairs[1:]):
        fa = session.get(api.Place, a_key)
        fb = session.get(api.Place, b_key)
        if fa is None or fb is None:
            continue
        synth_facts[(a_key, b_key)] = TravelEstimateFact(
            origin_key=a_key, destination_key=b_key, minutes=10,
            provider_key="synthetic-arm", captured_at="2026-09-21T12:00:55+00:00",
            route_geometry=((float(fa.longitude), float(fa.latitude)),
                            (float(fb.longitude), float(fb.latitude))),
            mode="SYNTHETIC",
        )
    synth_snapshot = MobilitySnapshot(
        facts=synth_facts, source_provider_key="synthetic-arm",
        captured_at="2026-09-21T12:00:55+00:00", snapshot_id="cell3-synthetic")
    s_coords, s_backed, s_fallback = api._frozen_route_for_plan(session, plan, synth_snapshot)
    s_served = api._route_feature(s_coords, provider="synthetic-arm",
                                   provider_backed=s_backed, fallback_reason=s_fallback,
                                   plan_version_id=plan.id)
    s_draw = list(s_served["geometry"]["coordinates"]) if s_served else []
    s_seq = s_coords == s_draw
    s_order = len(s_coords) == len(s_draw) and all(a == b for a, b in zip(s_coords, s_draw))
    s_seg = seg(s_coords) == seg(s_draw)
    doc["synthetic_arm"] = {
        "note": "synthetic: geometry is the plan's own activity coordinates, not captured provider data",
        "pairs": len(synth_facts), "spliced": bool(s_backed) and s_fallback is None,
        "provider_backed": s_backed, "plan_point_count": len(s_coords),
        "served_point_count": len(s_draw), "plan_equals_served": s_seq,
        "same_order": s_order, "same_segment_count": s_seg,
        "verdict": "THREE_WAY_SHAPE_CONSISTENT" if (s_seq and s_order and s_seg)
                   else "THREE_WAY_SHAPE_MISMATCH",
    }
    print(f"synthetic_arm: pairs={len(synth_facts)} spliced={doc['synthetic_arm']['spliced']} "
          f"plan_pts={len(s_coords)} served_pts={len(s_draw)} "
          f"seq={s_seq} order={s_order} seg={s_seg} verdict={doc['synthetic_arm']['verdict']}")

    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")
    # Teardown last: the synthetic arm above still reads places from this copy.
    try:
        session.close()
        from app.db.session import engine as _engine
        _engine.dispose()
    except Exception:
        pass
    for extra in (store, pathlib.Path(str(store) + "-wal"), pathlib.Path(str(store) + "-shm")):
        try:
            extra.unlink(missing_ok=True)
        except OSError:
            pass
    print("receipt route_shape_provider_" + RUN + ".json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
