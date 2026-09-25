import json
from app.db.session import ensure_schema, SessionLocal
from app.db.models import Place
from app.services import seed_demo
from sqlalchemy import func, select
ensure_schema()
s = SessionLocal()
if not int(s.scalar(select(func.count()).select_from(Place)) or 0):
    seed_demo(s); s.commit()
print("SEEDRESULT", json.dumps({"places": int(s.scalar(select(func.count()).select_from(Place)) or 0)}))