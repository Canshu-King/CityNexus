
"""One ORD-0282 seam-face role, in its own OS process, against the exported landed tree."""
import json, os, sys
from datetime import datetime, timezone

db_url, role, journey_id, mission, transport = sys.argv[1:6]
os.environ["CITYNEXUS_DATABASE_URL"] = db_url
os.environ["CITYNEXUS_AI_ENABLED"] = "false"
for _n in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_LIVE_VALHALLA_URL"):
    os.environ.pop(_n, None)

from sqlalchemy import select

from app.commerce.idempotency import canonical_request_signature
from app.db.models import Journey
from app.db.session import SessionLocal, engine
from app.main import _claim_plan_generation, _execute_plan_generation_claimed
from app.schemas import GeneratePlansRequest

keys = [f"plans.generate:{transport}", f"plans.generate:cont:{mission}"]
now = datetime.now(timezone.utc)
out = {"role": role, "pid": os.getpid(), "ppid": os.getppid(), "keys": keys,
       "resolved_db_file": str(engine.url.database)}
with SessionLocal() as s:
    journey = s.scalars(select(Journey).where(Journey.id == journey_id)).one()
    req = GeneratePlansRequest(candidate_count=3, mission_id=mission)
    sig = canonical_request_signature({"journey_id": str(journey_id), "mission_id": mission,
                                       "planning_mode": journey.planning_mode,
                                       "candidate_count": 3, "place_ids": None})
    if role == "claim_and_fill":
        raced = _claim_plan_generation(keys, sig, s, now)
        out["claim_returned_replay"] = raced is not None
    try:
        answer = _execute_plan_generation_claimed(journey, req, keys, f"cont:{mission}", now)
        out["refused"] = None
        out["answer_shape"] = sorted(answer.keys())
    except Exception as exc:  # noqa: BLE001 - the refusal IS the reading
        out["refused"] = {"type": type(exc).__name__,
                          "status": getattr(exc, "status_code", None),
                          "detail": str(getattr(exc, "detail", exc))[:200]}
print(json.dumps(out, ensure_ascii=False), flush=True)
