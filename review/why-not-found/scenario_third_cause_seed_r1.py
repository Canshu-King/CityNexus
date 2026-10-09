"""Seed the third cause for real: one catalog row that carries an identity and no coordinate.

This is the scenario the building exists for.  "Resolved but has no coordinate" cannot be produced by
typing something into the UI -- it is a state of the DATA, and before the model change it could not even be
stored.  So the scenario is built the way the product itself builds places (the same ORM row the discovery
path writes at `real_city.py`), standing in for a provider that returned an identity without a point.

It resolves the destination through the product's own resolver to get the real city code, so the seeded row
lands under the same city the capability endpoint looks up -- no hand-typed code, nothing the product could
disagree with.

Reads/writes only the running instance's own database; it touches no other file and no other database.
"""

from __future__ import annotations

import pathlib
import sys

BACKEND = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/wt504/backend")
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))

QUERY = "北京"


def main() -> int:
    from sqlalchemy import select
    from app.db.models import Place
    from app.db.session import SessionLocal
    from app.core.config import settings
    from app.anywhere_capability import resolve_destination

    print(f"database_url = {settings.database_url}")
    with SessionLocal() as session:
        resolution = resolve_destination(session, QUERY)
        city_code = getattr(resolution, "city_code", None)
        print(f"resolved {QUERY}: state={resolution.state} city_code={city_code}")
        if not city_code:
            print("REFUSE: the query did not resolve to a city code; the third cause cannot be seeded here")
            return 9

        existing = session.scalars(select(Place).where(Place.city_code == city_code)).all()
        print(f"places already in catalog for {city_code}: {len(existing)}")

        # one row: identity yes, coordinate no -- exactly the shape a provider can hand back
        seed_id = "seed-nocoord-1"
        row = session.scalar(select(Place).where(Place.id == seed_id))
        if row is None:
            row = Place(
                id=seed_id,
                provider_key="seed",
                external_id="way/1464199917",
                city_code=city_code,
                name="种子地点（有身份、无坐标）",
                category="attraction",
                latitude=None,
                longitude=None,
                opening_hours_json="{}",
                tags_json="[]",
                metadata_json="{}",
                updated_at="2026-10-07T00:00:00",
            )
            session.add(row)
        else:
            row.latitude = None
            row.longitude = None
        session.commit()
        after = session.scalars(select(Place).where(Place.city_code == city_code)).all()
        print(f"places after seed: {len(after)}")
        for p in after:
            print(f"  {p.id} identity={p.external_id} lat={p.latitude} lon={p.longitude}")
    print("SEEDED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())