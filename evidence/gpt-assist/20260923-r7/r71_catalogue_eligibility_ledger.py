from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from app.db.models import Place
from app.db.session import SessionLocal
from app.services import _catalogue_visit_eligible, _place_verified_cost, _place_window


def _load(raw: str | None) -> dict:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--city-code", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rows: list[dict] = []
    with SessionLocal() as session:
        places = list(
            session.scalars(
                select(Place).where(Place.city_code == args.city_code).order_by(Place.id)
            ).all()
        )

        for place in places:
            metadata = _load(place.metadata_json)
            opening = _load(place.opening_hours_json)
            role_ok = bool(_catalogue_visit_eligible(place))
            window = _place_window(place)
            verified_cost = _place_verified_cost(place)
            cost_evidence = metadata.get("cost_evidence")
            if not isinstance(cost_evidence, dict):
                cost_evidence = {}

            reasons: list[str] = []
            if not role_ok:
                reasons.append("ROLE_NOT_VISIT_ELIGIBLE")
            if window is None:
                reasons.append("OPENING_WINDOW_UNVERIFIED")
            if verified_cost is None:
                reasons.append("COST_UNVERIFIED")

            rows.append(
                {
                    "id": place.id,
                    "provider_key": place.provider_key,
                    "external_id": place.external_id,
                    "name": place.name,
                    "category": place.category,
                    "visit_role_eligible": role_ok,
                    "opening_status": opening.get("status"),
                    "opening_window": list(window) if window is not None else None,
                    "cost_status": cost_evidence.get("status"),
                    "cost_amount_minor": cost_evidence.get("amount_minor"),
                    "compatibility_cost_minor": metadata.get("cost_minor"),
                    "price_known": metadata.get("price_known"),
                    "template_eligible": not reasons,
                    "rejection_reasons": reasons,
                }
            )

    provider_rows = [
        row for row in rows if row["provider_key"] != "citynexus-v12-authoritative"
    ]
    payload = {
        "classification": "R71_CATALOGUE_ELIGIBILITY_LEDGER",
        "city_code": args.city_code,
        "provider_place_count": len(provider_rows),
        "template_eligible_place_count": sum(
            1 for row in provider_rows if row["template_eligible"]
        ),
        "places": provider_rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
