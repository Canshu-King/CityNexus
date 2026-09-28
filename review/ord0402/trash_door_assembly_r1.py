"""ORD-0402 slice 2 -- the test assembly's stand-in for slice 1's read door.

THIS IS NOT PRODUCT CODE AND IS NOT IMPORTED BY THE PRODUCT. It exists because ORD-0402 slice 1 (the
real "list the binned trips" door, assigned to another lane) is not on the authority line yet, and the
acceptance for slice 2 is a real click on a real row. The file is shipped as evidence so a reviewer can
see exactly which door the run answered, and what it returned.

What is real in this run: the process is `uvicorn` over a private sqlite file this lane created, the row
it lists is a row a real `DELETE /api/v1/journeys/{id}` wrote into `journeys.deleted_at`, and the 找回
tap goes to the landed `POST /api/v1/journeys/{id}/undelete` in `backend/app/main.py` -- this module
never touches the write path. What is stand-in: the enumeration query and the two field names
(`deleted_at`, `bin_state`), which slice 1 owns.
"""

from __future__ import annotations

import sys

REPO_BACKEND = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_q_ord0402/wt/backend"
if REPO_BACKEND not in sys.path:
    sys.path.insert(0, REPO_BACKEND)

from fastapi import Depends  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.models import Journey  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402


@app.get("/api/v1/recycle-bin/journeys")
def list_discarded(session: Session = Depends(get_session)):
    """Rows the durable column says are binned -- read from the same table the real doors write.

The path is `/api/v1/recycle-bin/journeys`, not `/api/v1/journeys/discarded`, because of a measurement
made on this stack: the landed `GET /api/v1/journeys/{journey_id}` door is declared earlier in
`app.main`, so it swallows the single-segment name and answers 422 with
`loc: ["path","journey_id"]`, `type: "uuid_parsing"`, `message_key: "validation.not_an_id"`. A
collection route under `/journeys/` therefore has to be declared *before* that door to be reachable at
all -- which is a fact slice 1 needs, and is recorded in this lane's delivery block."""

    items = session.scalars(
        select(Journey)
        .where(Journey.deleted_at.isnot(None))
        .order_by(Journey.created_at, Journey.id)
    ).all()
    return [
        {
            "id": item.id,
            "title": item.title,
            "city_code": item.city_code,
            "start_at": item.start_at,
            "end_at": item.end_at,
            "status": item.status,
            "deleted_at": item.deleted_at,
            "bin_state": "IN_RECYCLE_BIN",
        }
        for item in items
    ]
