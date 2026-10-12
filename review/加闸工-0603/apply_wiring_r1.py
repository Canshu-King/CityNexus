# -*- coding: utf-8 -*-
"""ORD-0603 candidate wiring, applied to a scratch tree only (never the shared worktree).

It proves two things by running them: the route can carry the landed contract's judgement with real
values, and the line's existing stub test refuses the extra key -- which is why this patch ships as
evidence instead of as a landed edit.
"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MAIN = "D:/moodle/_jz_0603/backend/app/main.py"

IMPORT_OLD = "from app.stay_mobility import (\n"
IMPORT_NEW = ('from app.execution.route_session_contract import fact_is_eligible_for_live_readiness  # ORD-0603\n'
              'from app.stay_mobility import (\n')

HANDLER_OLD = '''@app.get("/api/v1/journeys/{journey_id}/mobility")
def list_journey_mobility(journey_id: UUID, session: Session = Depends(get_session)):
    journey = require(session, Journey, str(journey_id), "Journey")
    return {
        "modes": [
            fact_payload(item)
            for item in session.scalars(
                select(MobilityFact)
                .where(MobilityFact.journey_id == journey.id)
                .order_by(MobilityFact.from_key, MobilityFact.to_key, MobilityFact.mode)
            ).all()
        ],
        "available_modes": ["WALK", "BICYCLE", "TRANSIT", "AUTO", "RIDE_HAIL"],
        "choose_for_me": True,
    }
'''
HANDLER_NEW = '''@app.get("/api/v1/journeys/{journey_id}/mobility")
def list_journey_mobility(journey_id: UUID, session: Session = Depends(get_session)):
    journey = require(session, Journey, str(journey_id), "Journey")
    modes = []
    for item in session.scalars(
        select(MobilityFact)
        .where(MobilityFact.journey_id == journey.id)
        .order_by(MobilityFact.from_key, MobilityFact.to_key, MobilityFact.mode)
    ).all():
        fact = fact_payload(item)
        # ORD-0603: the contract decides which route truth may drive a live leave-by; the door says so
        # instead of leaving every client to guess from a provenance string of its own choosing.
        fact["live_readiness_eligible"] = fact_is_eligible_for_live_readiness(fact)
        modes.append(fact)
    return {
        "modes": modes,
        "available_modes": ["WALK", "BICYCLE", "TRANSIT", "AUTO", "RIDE_HAIL"],
        "choose_for_me": True,
    }
'''

src = io.open(MAIN, encoding="utf-8", newline="").read()
orig = src
for name, old, new in (("import", IMPORT_OLD, IMPORT_NEW), ("handler", HANDLER_OLD, HANDLER_NEW)):
    n = src.count(old)
    if n != 1:
        print("ABORT %s 锚点命中 %d 次，不是 1 次" % (name, n))
        raise SystemExit(1)
    src = src.replace(old, new, 1)
io.open(MAIN + ".pristine", "w", encoding="utf-8", newline="").write(orig)
io.open(MAIN, "w", encoding="utf-8", newline="").write(src)
print("候选接线已打到临时树（原文件留在 main.py.pristine）")
print("新增行数：%d" % (src.count("\n") - orig.count("\n")))
