"""Exact-object OSM fact probe for the R7.2 acquisition frontier.

Diagnostic only. It does not materialize Place rows and does not promote facts.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import httpx

from app.integrations.discovery.real_city import (
    OVERPASS_MIRRORS,
    cost_evidence_from_tags,
    normalize_opening_hours,
)


def _parse_object(value: str) -> tuple[str, int]:
    raw_type, raw_id = value.strip().split("/", 1)
    kind = {"n": "node", "w": "way", "r": "relation"}.get(raw_type.casefold(), raw_type.casefold())
    if kind not in {"node", "way", "relation"}:
        raise argparse.ArgumentTypeError(f"unsupported OSM object type: {raw_type}")
    try:
        object_id = int(raw_id)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid OSM id: {raw_id}") from exc
    return kind, object_id


def _category(tags: dict[str, Any]) -> str:
    return str(tags.get("tourism") or tags.get("amenity") or tags.get("leisure") or "service")


def _official_hints(tags: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "website", "contact:website", "operator", "operator:wikidata",
        "wikipedia", "wikidata", "phone", "contact:phone", "fee",
        "charge", "price", "currency", "opening_hours",
    )
    return {key: tags[key] for key in keys if key in tags}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--object", action="append", required=True, dest="objects")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--request-timeout-s", type=float, default=12.0)
    args = parser.parse_args()

    objects = [_parse_object(value) for value in args.objects]
    rows: list[dict[str, Any]] = []

    with httpx.Client(timeout=args.request_timeout_s, trust_env=False) as client:
        for kind, object_id in objects:
            query = f"[out:json][timeout:10];{kind}({object_id});out center tags;"
            attempts: list[dict[str, Any]] = []
            element: dict[str, Any] | None = None
            for endpoint in OVERPASS_MIRRORS:
                started = time.monotonic()
                try:
                    response = client.post(
                        endpoint,
                        data={"data": query},
                        headers={"User-Agent": "CityNexus-R7.2-Diagnostic/1.0"},
                    )
                    status = response.status_code
                    response.raise_for_status()
                    payload = response.json()
                    elements = payload.get("elements") or []
                    attempts.append({
                        "endpoint": endpoint,
                        "http_status": status,
                        "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
                        "elements": len(elements),
                        "error": None,
                    })
                    if elements:
                        element = elements[0]
                        break
                except Exception as exc:
                    attempts.append({
                        "endpoint": endpoint,
                        "http_status": getattr(getattr(exc, "response", None), "status_code", None),
                        "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
                        "elements": 0,
                        "error": f"{type(exc).__name__}: {exc}",
                    })

            if element is None:
                rows.append({
                    "object": f"{kind}/{object_id}",
                    "outcome": "PROVIDER_UNAVAILABLE",
                    "attempts": attempts,
                })
                continue

            tags = element.get("tags") or {}
            center = element.get("center") or element
            rows.append({
                "object": f"{kind}/{object_id}",
                "outcome": "FOUND",
                "name": tags.get("name"),
                "category": _category(tags),
                "latitude": center.get("lat"),
                "longitude": center.get("lon"),
                "raw_tags": tags,
                "opening_hours": normalize_opening_hours(tags.get("opening_hours")),
                "cost_evidence": cost_evidence_from_tags(tags, source="overpass-exact-object"),
                "official_evidence_hints": _official_hints(tags),
                "attempts": attempts,
            })

    result = {
        "classification": "R72_EXACT_OSM_FACT_PROBE",
        "objects": rows,
        "truth_boundary": {
            "missing_opening_remains_unknown": True,
            "missing_cost_remains_unknown": True,
            "diagnostic_only_not_materialization": True,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
