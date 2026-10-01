"""ORD-0544 diagnosis: which leg answers, and what the warm run actually reads.

g16b (an unexpired candidate set must answer without going outside) is red on today's line and
green at `8dd6905dec515b49b7713ea487806fe4f069d92a`, the generation before ORD-0519. Rather than
argue about which commit "caused" it, this prints the two things that decide the question, in one
run, on whatever tree runs it:

  * every outbound call the instrument caught, with its path, for the cold pass and the warm pass;
  * for each candidate row the cold pass left in the store: `provider_key`, `expires_at`, and the
    `request.query` the TTL gate matches on.

Run it in two trees and the readings either match the test's story or they do not. It uses only the
product's own functions and an in-memory provider, so nothing leaves the box and no store is shared.
"""

from __future__ import annotations

import json
import os
import sys
import uuid as uuidlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TREE = Path(os.environ.get("TREE", ".")).resolve()
sys.path.insert(0, str(TREE / "backend"))

import httpx  # noqa: E402

CAFE = {
    "type": "way",
    "id": 4242,
    "lat": 39.10,
    "lon": 117.20,
    "tags": {"amenity": "cafe", "name": "测试咖啡馆"},
}
NOMINATIM_ROW = {
    "osm_type": "relation",
    "osm_id": 1,
    "lat": "39.12",
    "lon": "117.19",
    "display_name": "Tianjin, China",
    "type": "city",
    "class": "place",
}

calls: list[dict] = []


def handler(request: httpx.Request) -> httpx.Response:
    body = request.content.decode("utf-8") if request.content else ""
    calls.append({"method": request.method, "path": request.url.path,
                  "params": dict(request.url.params), "body": body[:120]})
    if request.url.path.endswith("/interpreter"):
        return httpx.Response(200, json={"elements": [CAFE]})
    return httpx.Response(200, json=[NOMINATIM_ROW])


def main() -> int:
    tmp = TREE / "run_diag_tmp"
    tmp.mkdir(exist_ok=True)
    db = tmp / f"diag_{uuidlib.uuid4().hex[:8]}.db"
    os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    os.environ["CITYNEXUS_REAL_CITY_ENABLED"] = "true"
    os.environ["CITYNEXUS_DEMO_MODE"] = "false"
    os.environ["CITYNEXUS_PROVIDER_NETWORK_MODE"] = "env_proxy"

    from app.db.models import Journey, RealPlaceCandidate, Traveler
    from app.db.session import SessionLocal, ensure_schema
    from app.integrations.discovery import real_city

    engine = SessionLocal().get_bind()
    ensure_schema(engine)

    real_client = httpx.Client

    def factory(**kw):
        # `real_client` is captured before the swap, so building a client here cannot re-enter
        # this factory (the first version patched `httpx.Client` and called `httpx.Client`).
        kw.pop("timeout", None)
        kw.pop("trust_env", None)
        return real_client(transport=httpx.MockTransport(handler))

    # patch the one attribute the legs construct, and keep every other httpx name intact:
    # `except (httpx.HTTPError, ...)` in the orchestration needs them.
    httpx.Client = factory

    with SessionLocal() as session:
        now_iso = datetime.now(timezone.utc).isoformat()
        traveler = Traveler(id=str(uuidlib.uuid4()), display_name="diag", email="d@example.invalid",
                            locale="zh-CN", timezone="Asia/Shanghai",
                            created_at=now_iso, updated_at=now_iso)
        session.add(traveler)
        session.commit()   # the traveller row must exist before the journey's foreign key is checked
        start = datetime.now(timezone.utc).replace(microsecond=0)
        # no arrival anchor and no plan on purpose: `discovery_anchor_options` then has nothing
        # server-known, which is the state where the anchor leg has to speak - the thing being measured.
        journey = Journey(id=str(uuidlib.uuid4()), traveler_id=traveler.id, title="diag 天津",
                          city_code="CN-TIANJIN", timezone="Asia/Shanghai",
                          start_at=start.isoformat(),
                          end_at=(start + timedelta(days=2)).isoformat(),
                          budget_currency="CNY", budget_amount_minor=600000,
                          status="DRAFT", created_at=now_iso, updated_at=now_iso)
        session.add(journey)
        session.commit()
        jid = journey.id

    query = "cafes near me"
    out: dict = {"tree": str(TREE), "head": os.environ.get("HEAD", ""), "query": query}
    with SessionLocal() as session:
        journey = session.get(Journey, jid)
        calls.clear()
        cold = real_city.capture_real_city_candidates(
            session, journey, query=query, radius_m=2500, limit=5, mode="live")
        session.commit()
        out["cold"] = {"paths": [c["path"] for c in calls],
                       "mode": cold.get("mode"), "provenance": cold.get("provenance"),
                       "candidates": len(cold.get("candidates") or []),
                       "failure_stage": (cold.get("provider_status") or {}).get("failure_stage"),
                       "fallback_reason": (cold.get("provider_status") or {}).get("fallback_reason")}
        rows = list(session.query(RealPlaceCandidate).filter_by(journey_id=jid).all())
        out["cold_rows"] = [
            {"provider_key": r.provider_key, "external_id": r.external_id,
             "expires_at": r.expires_at,
             "recorded_query": ((json.loads(r.evidence_json or "{}").get("request") or {}).get("query")),
             "materialized": bool(r.materialized_place_id)}
            for r in rows
        ]

    with SessionLocal() as session:
        journey = session.get(Journey, jid)
        calls.clear()
        warm = real_city.capture_real_city_candidates(
            session, journey, query=query, radius_m=2500, limit=5, mode="live")
        session.commit()
        out["warm"] = {"paths": [c["path"] for c in calls], "mode": warm.get("mode"),
                       "candidates": len(warm.get("candidates") or []),
                       "provider_status_legs": {k: v for k, v in (warm.get("provider_status") or {}).items()
                                                if k in ("anchor", "overpass", "nominatim", "photon",
                                                          "cache", "failure_stage", "fallback_reason")}}
    httpx.Client = real_client
    print(json.dumps(out, ensure_ascii=False, indent=1))
    target = Path("D:/moodle/_qoder_seed_ord0489/evidence/ord0544")
    target.mkdir(parents=True, exist_ok=True)
    name = out["head"][:8] if out["head"] else TREE.name
    (target / f"diag_{name}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    import gc
    gc.collect()
    for suf in ("", "-wal", "-shm"):
        f = Path(str(db) + suf)
        try:
            if f.exists():
                f.unlink()
        except OSError as exc:
            print("temp db left behind:", f, exc.__class__.__name__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
