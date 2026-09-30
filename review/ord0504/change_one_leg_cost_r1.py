"""ORD-0504 counterexample 2's lever -- set one plan leg's price in this lane's own store.

    python change_one_leg_cost_r1.py <journey_id> <amount_minor>

Prints the value it found and the value it wrote, so the arms can assert the face moved by exactly
that delta and then put the number back.

Why a store write and not a door: no door on this tree prices a plan leg. That is measured, not
assumed -- `review/ord0504/spend_surface_r1.json` records `GET /journeys/{id}/legs` answering 404, and
the only leg writes are inside plan generation. The arm is testing that the screen follows the server's
number, so the channel that changes the number is beside the point, and it is named here rather than
presented as a product flow.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

TREE = Path("D:/moodle/_qoder_r_ord0465_20260929/wt")
sys.path.insert(0, str(TREE / "backend"))
sys.path.insert(0, str(TREE))

from sqlalchemy import select  # noqa: E402

from app.db.models import JourneyLeg  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


def main() -> int:
    journey_id, amount = sys.argv[1], int(sys.argv[2])
    with SessionLocal() as session:
        leg = session.scalars(
            select(JourneyLeg)
            .where(JourneyLeg.journey_id == journey_id, JourneyLeg.cost_status == "KNOWN")
            .order_by(JourneyLeg.sequence_no)
        ).first()
        if leg is None:
            print(json.dumps({"error": "NO_KNOWN_LEG", "journey_id": journey_id}))
            return 3
        before = leg.cost_amount_minor
        leg.cost_amount_minor = amount
        session.commit()
        print(json.dumps({"leg_id": leg.id, "before_minor": before, "after_minor": amount,
                          "currency": leg.currency, "delta_minor": amount - int(before or 0)}))
    return 0


if __name__ == "__main__":
    os.environ.setdefault("CITYNEXUS_DEMO_MODE", "true")
    raise SystemExit(main())
