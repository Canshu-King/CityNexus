"""Diagnostic capture of complete successful Overpass candidates for R7.3."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import httpx

from app.integrations.discovery.real_city import OverpassPOIProvider


def _value(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default)


def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", action="append", required=True)
    parser.add_argument("--latitude", type=float, required=True)
    parser.add_argument("--longitude", type=float, required=True)
    parser.add_argument("--radius-m", type=int, default=5000)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--deadline-s", type=float, default=30.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows = []
    for query in args.query:
        started = time.monotonic()
        attempts = []
        candidates = []
        outcome = "PROVIDER_FAILURE"
        error = None
        with httpx.Client(timeout=12.0, trust_env=False) as client:
            provider = OverpassPOIProvider(client=client)
            try:
                candidates, attempts = provider.search_with_evidence(
                    query,
                    latitude=args.latitude,
                    longitude=args.longitude,
                    radius_m=args.radius_m,
                    limit=args.limit,
                    deadline_monotonic=time.monotonic() + args.deadline_s,
                    request_timeout_s=min(10.0, args.deadline_s),
                )
                outcome = "OK"
            except Exception as exc:
                attempts = list(getattr(exc, "provider_attempts", attempts) or attempts)
                error = f"{type(exc).__name__}: {exc}"
                outcome = "PROVIDER_TIMEOUT" if "timeout" in type(exc).__name__.casefold() else type(exc).__name__

        full = []
        for item in candidates:
            full.append({
                "provider_key": _value(item, "provider_key"),
                "external_id": _value(item, "external_id"),
                "name": _value(item, "name"),
                "category": _value(item, "category"),
                "latitude": _value(item, "latitude"),
                "longitude": _value(item, "longitude"),
                "tags": _jsonable(_value(item, "tags", [])),
                "opening_hours": _jsonable(_value(item, "opening_hours", {})),
                "cost_evidence": _jsonable(_value(item, "cost_evidence", {})),
                "metadata": _jsonable(_value(item, "metadata", {})),
                "distance_m": _value(item, "distance_m"),
            })

        rows.append({
            "query": query,
            "scope": {
                "kind": "centroid_radius",
                "latitude": args.latitude,
                "longitude": args.longitude,
                "radius_m": args.radius_m,
            },
            "elapsed_ms": round((time.monotonic() - started) * 1000.0, 1),
            "outcome": outcome,
            "error": error,
            "provider_attempts": _jsonable(attempts),
            "candidates": full,
        })

    payload = {
        "classification": "R73_LIVE_PROVIDER_CANDIDATE_CAPTURE",
        "truth_boundary": {
            "diagnostic_only_not_place_materialization": True,
            "unknown_opening_remains_unknown": True,
            "unknown_cost_remains_unknown": True,
        },
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
