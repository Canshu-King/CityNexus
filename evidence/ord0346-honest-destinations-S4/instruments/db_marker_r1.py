"""ORD-0346 S4: plant a private marker row so a later reading can prove which store answered.

The marker is instrument state, not product data: one `places` row under a city code that names no
destination (`CN-S4MARKER-<hex>`), written into this lane's own one-off SQLite.  A server that can
answer for it is reading this file and nobody else's store.
"""
import json
import os
import secrets
import sys
import uuid

BACKEND = "D:/moodle/_qoder_ord0346_S4/backend"
DB = os.environ["CNX_S4_DB"]
if "_qoder_lane_S4_0926" not in DB.replace("\\", "/") or not os.path.exists(DB):
    raise SystemExit("REFUSE: CNX_S4_DB must be this lane's own existing file, got %r" % DB)

os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + DB.replace("\\", "/")
os.environ["CITYNEXUS_ANYWHERE_RESOLVER"] = "off"
sys.path.insert(0, BACKEND)

from app.db.models import Place  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402

if str(engine.url) != os.environ["CITYNEXUS_DATABASE_URL"]:
    raise SystemExit("REFUSE: engine resolved %s" % engine.url)

marker_code = "CN-S4MARKER-" + secrets.token_hex(3).upper()
marker_name = "cnx-s4-ord0346-marker-" + secrets.token_hex(4)
absent_code = "CN-S4ABSENT-" + secrets.token_hex(3).upper()

with SessionLocal() as session:
    row = Place(
        id=str(uuid.uuid4()),
        provider_key="s4-lane-marker",
        external_id=marker_name,
        city_code=marker_code,
        name=marker_name,
        category="landmark",
        latitude=0.0,
        longitude=0.0,
        opening_hours_json="{}",
        tags_json="[]",
        metadata_json="{}",
        updated_at="2026-09-26T00:00:00+00:00",
    )
    session.add(row)
    session.commit()
    marker_id = row.id

print(json.dumps({
    "database_url": str(engine.url),
    "marker_city_code": marker_code,
    "marker_place_id": marker_id,
    "marker_name": marker_name,
    "absent_city_code": absent_code,
}, ensure_ascii=False, indent=1))
