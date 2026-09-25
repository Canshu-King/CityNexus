import json
from app.db.session import ensure_schema, SessionLocal
from app.db.models import Place
from app.services import seed_demo
from sqlalchemy import func, select
ensure_schema()
s = SessionLocal()
n0 = int(s.scalar(select(func.count()).select_from(Place)) or 0)
n = int(s.scalar(select(func.count()).select_from(Place).where(Place.city_code == "CNX-DEMO")) or 0)
seeded = n == 0
if seeded:
    seed_demo(s); s.commit()
n2 = int(s.scalar(select(func.count()).select_from(Place).where(Place.city_code == "CNX-DEMO")) or 0)
print("SEEDRESULT", json.dumps({"places_before": n0, "demo_places_before": n,
                                "seeded_by_this_call": seeded, "demo_places_after": n2}))