import json
from app.db.session import ensure_schema, SessionLocal
from app.db.models import Place
from app.services import seed_demo
from sqlalchemy import func, select
ensure_schema()
s = SessionLocal()
n = int(s.scalar(select(func.count()).select_from(Place).where(Place.city_code == "CNX-DEMO")) or 0)
seeded = n == 0
if seeded:
    seed_demo(s); s.commit()
print("SEEDRESULT", json.dumps({"places_after": int(s.scalar(select(func.count()).select_from(Place)) or 0),
                                "demo_places": n, "seeded_by_this_call": seeded}))