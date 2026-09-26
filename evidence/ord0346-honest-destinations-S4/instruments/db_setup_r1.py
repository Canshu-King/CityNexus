"""ORD-0346 S4: build my own one-off SQLite for the capability reading.

Nothing here touches a shared store: the database URL is taken from CNX_S4_DB and must be an
absolute path inside this lane's directory, asserted before any import that could open a file.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = "D:/moodle/_qoder_ord0346_S4/backend"

db = os.environ.get("CNX_S4_DB", "")
if not os.path.isabs(db) or "_qoder_lane_S4_0926" not in db.replace("\\", "/"):
    raise SystemExit("REFUSE: CNX_S4_DB must be an absolute path inside this lane's directory, got %r" % db)
if os.path.exists(db):
    raise SystemExit("REFUSE: %s already exists - this step builds a fresh store, it does not reuse one" % db)

os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.replace("\\", "/")
os.environ["CITYNEXUS_ANYWHERE_RESOLVER"] = "off"
os.environ["CITYNEXUS_DEMO_MODE"] = "true"
os.environ["CITYNEXUS_AI_ENABLED"] = "false"
os.environ["CITYNEXUS_GUARDIAN_AUTORUN"] = "false"
# Tripwire: if anything below reaches for a geocoder it will fail against a closed port on
# loopback rather than ask the internet what it thinks about a city name.
os.environ.setdefault("PHOTON_BASE_URL", "http://127.0.0.1:9")
os.environ.setdefault("CITYNEXUS_LIVE_VALHALLA_URL", "")

sys.path.insert(0, BACKEND)
from app.core.config import settings  # noqa: E402
from app.db import models  # noqa: E402,F401  - registers the tables
from app.db.session import SessionLocal, engine, ensure_schema  # noqa: E402

if str(engine.url) != os.environ["CITYNEXUS_DATABASE_URL"]:
    raise SystemExit("REFUSE: the engine resolved %s, not the URL this lane named" % engine.url)

ensure_schema(engine)
from app.services import seed_demo  # noqa: E402

with SessionLocal() as session:
    summary = seed_demo(session)

from sqlalchemy import func, select  # noqa: E402
from app.db.models import CityService, Place  # noqa: E402

with SessionLocal() as session:
    places = dict(session.execute(select(Place.city_code, func.count(Place.id))
                                 .group_by(Place.city_code)).all())
    services = dict(session.execute(select(CityService.city_code, func.count(CityService.id))
                                    .group_by(CityService.city_code)).all())
    categories = {code: sorted({str(row[1]) for row in session.execute(
        select(Place.id, Place.category).where(Place.city_code == code)).all()}) for code in places}

print(json.dumps({
    "database_url": str(engine.url),
    "db_exists": os.path.exists(db),
    "db_bytes": os.path.getsize(db),
    "resolver": os.environ["CITYNEXUS_ANYWHERE_RESOLVER"],
    "demo_mode": settings.demo_mode,
    "seed_summary": summary,
    "places_by_city": places,
    "city_services_by_city": services,
    "place_categories": categories,
}, ensure_ascii=False, indent=1))
