import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, r"D:/moodle/_cmdr_rescue_v3_1022/backend")
os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///D:/moodle/_cmdr_v3_live_1022/citynexus_v3_gozero_1026.db"
os.environ.setdefault("CITYNEXUS_ENV", "test")

from sqlalchemy import select  # noqa: E402
from app.db.models import Activity, Journey, PlanVersion, Place  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services import _plan_staleness, plan_authority_blocker  # noqa: E402

JOURNEY = "1acb10a6-c234-4765-a88a-4bd56f0985f7"
out = []
session = SessionLocal()
try:
    journey = session.get(Journey, JOURNEY)
    out.append(f"JOURNEY_STATUS {journey.status} ACTIVE_PV {journey.active_plan_version_id}")
    item = session.scalars(
        select(PlanVersion).where(PlanVersion.journey_id == JOURNEY).order_by(PlanVersion.version_no)
    ).all()
    for plan in item:
        activities = session.scalars(
            select(Activity).where(Activity.plan_version_id == plan.id).order_by(Activity.sequence_no)
        ).all()
        place_ids = [str(a.place_id) for a in activities if a.place_id]
        places = {str(p.id): p for p in session.scalars(select(Place).where(Place.id.in_(place_ids))).all()}
        evidence = json.loads(plan.mobility_evidence_json or "{}")
        out.append(f"PLAN v{plan.version_no} status={plan.status} lifecycle={plan.lifecycle} pv={plan.id}")
        out.append(f"  EVIDENCE_KEYS {sorted(evidence)}")
        out.append(f"  snapshot_id={evidence.get('snapshot_id')!r} expires_at={evidence.get('expires_at')!r}")
        out.append(f"  NOW_UTC {datetime.now(timezone.utc).isoformat()}")
        out.append(f"  STALENESS {_plan_staleness(plan)}")
        keys = [str(a.place_id or a.city_service_id or '') for a in activities]
        out.append(f"  AUTHORITY_BLOCKER {plan_authority_blocker(plan, places, used_place_ids=keys)!r}")
        expl = json.loads(plan.explanation_json or "{}")
        rows = expl.get("unresolved_facts") or []
        kinds = {}
        for row in rows:
            kinds[str(row.get("kind"))] = kinds.get(str(row.get("kind")), 0) + 1
        out.append(f"  AUTHORITY_STATE {expl.get('authority_state')!r} UNRESOLVED_KINDS {json.dumps(kinds, ensure_ascii=False)}")
        out.append(f"  PLACE_IDS_IN_ACTIVITIES {len(place_ids)} PLACES_FOUND {len(places)}")
        out.append(f"  PLACE_ID_SAMPLES {json.dumps(sorted(places)[:3], ensure_ascii=False)}")
finally:
    session.close()

sys.stdout.reconfigure(encoding="utf-8")
print("\n".join(out))
