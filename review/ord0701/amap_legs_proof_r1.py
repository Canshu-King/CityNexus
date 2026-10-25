"""Re-take the two live Amap readings `fusion/QODER_RESULT.md` §9 cites.

    python review/ord0701/amap_legs_proof_r1.py

B (place discovery): asks the live POI provider for 天津博物馆, persists what it found into a
throwaway in-memory catalogue, reads it back, then discovers the same thing again to show the
provider item is the identity.

C (routing): hands two of those just-persisted place ids to the product's own
`capture_runtime_mobility_snapshot` as a hard capture, and prints the fact the gate would read.

Nothing here writes the development database and nothing prints the key: the only key-shaped
output is a three-character fingerprint.  Exit code 0 means both legs answered live;
`ORD0701_PROOF=FAIL` plus the reason otherwise.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

import httpx  # noqa: E402
from sqlalchemy import create_engine, func, select  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db import models  # noqa: E402
from app.db.models import Place  # noqa: E402
from app.integrations.capability import place_leads as lead_surface  # noqa: E402
from app.integrations.capability.place_discovery import persist_leads  # noqa: E402
from app.integrations.china import amap  # noqa: E402
from app.integrations.mobility import runtime  # noqa: E402

CITY_CODE = "CN-TIANJIN"
QUERY = "天津博物馆"
REGION = "天津市"
FAILURES: list[str] = []


def say(name: str, value: object) -> None:
    print(f"{name}={value}")


def require(name: str, ok: bool, detail: object = "") -> None:
    if not ok:
        FAILURES.append(name)
        print(f"ORD0701_{name}=FAIL {detail}")


def _catalogue() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


async def discover_once(session: Session) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        sources = lead_surface.build_sources(city_code=CITY_CODE, client=client)
        result = await lead_surface.collect_place_leads(
            QUERY, region=REGION, sources=sources, limit=5
        )
    persisted = persist_leads(session, result.leads, city_code=CITY_CODE)
    if persisted:
        session.commit()
    return {
        "readings": result.provider_readings,
        "leads": result.leads,
        "persisted": persisted,
        "counts_as_draft_supply": result.counts_as_draft_supply,
        "unknown_fields": result.unknown_fields,
    }


def place_rows(session: Session) -> list[Place]:
    return list(
        session.scalars(
            select(Place)
            .where(Place.city_code == CITY_CODE, Place.provider_key == "amap-web-service")
            .order_by(Place.name)
        )
    )


def main() -> int:
    key = amap.web_key()
    say("KEY_CONFIGURED", bool(key))
    say("KEY_ENV_NAME", amap.key_env_name())
    if key:
        say("KEY_FINGERPRINT", f"{key[:3]}... len={len(key)}")
    say("VALHALLA_URL_SET", bool(settings.live_valhalla_url))
    say("ROUTING_SEAM", amap.china_routing_seam())
    say("ROUTES_VIA_AMAP", amap.routes_via_amap(CITY_CODE))
    require("KEY", bool(key), amap.missing_key_reason())
    require("SEAM_AMAP", amap.routes_via_amap(CITY_CODE))
    if FAILURES:
        print("ORD0701_PROOF=FAIL")
        return 1

    # The guard this branch added: a region Amap would silently ignore never reaches the provider.
    say("REGION_GUARD_INTERNAL_CODE", amap.is_amap_region("CN-12-01"))
    say("REGION_GUARD_CITY_NAME", amap.is_amap_region("天津市"))
    say("REGION_GUARD_ADCODE", amap.is_amap_region("120000"))
    require("REGION_GUARD", not amap.is_amap_region("CN-12-01") and amap.is_amap_region("天津市"))

    session = _catalogue()
    try:
        first = asyncio.run(discover_once(session))
        say(
            "B_SOURCE_READINGS",
            ";".join(
                f"{item.get('source')}:{item.get('outcome')}"
                + (f":rows={item['rows']}" if "rows" in item else "")
                for item in first["readings"]
            ),
        )
        located = [lead for lead in first["leads"] if lead.has_position()]
        say("B_LEADS", len(first["leads"]))
        say("B_WITH_POSITION", len(located))
        say("B_UNKNOWN_FIELDS", ",".join(first["unknown_fields"]) or "none")
        say("B_PERSISTED", len(first["persisted"]))
        say("B_PERSISTED_PROVIDER_KEY", first["persisted"][0]["provider_key"] if first["persisted"] else "none")
        say("B_PERSISTED_CRS", first["persisted"][0]["coordinate_system"] if first["persisted"] else "none")
        say("B_PERSISTED_SOURCE_CRS", first["persisted"][0]["source_coordinate_system"] if first["persisted"] else "none")
        rows = place_rows(session)
        say("B_DB_ROWS", len(rows))
        say("B_DB_NAMES", "|".join(row.name for row in rows[:5]))
        require("B_ANSWERED_LIVE", bool(first["persisted"]) and first["persisted"][0]["provider_key"] == "amap-web-service")
        require("B_DB_ROWS", len(rows) == len(first["persisted"]) and len(rows) > 0)

        # Discovering the same provider items again must update rows, not add them.
        second = asyncio.run(discover_once(session))
        rows_after = place_rows(session)
        say("B_SECOND_PERSISTED", len(second["persisted"]))
        say("B_DB_ROWS_AFTER_REPEAT", len(rows_after))
        require("B_IDEMPOTENT", len(rows_after) == len(rows) and len(rows_after) > 0)

        pair_source = rows_after[:2]
        require("C_TWO_PLACES", len(pair_source) == 2, [row.name for row in rows_after])
        if len(pair_source) == 2:
            pair = (pair_source[0].id, pair_source[1].id)
            say("C_PAIR_NAMES", f"{pair_source[0].name}->{pair_source[1].name}")
            journey = SimpleNamespace(id="ord0701-proof-journey", city_code=CITY_CODE)
            result = runtime.capture_runtime_mobility_snapshot(
                session,
                journey,
                [pair],
                operation_key="ord0701:live-proof",
                require_explicit_facts=True,
                requested_mode="WALK",
            )
            fact = result.snapshot.facts[pair]
            say("C_PROVIDER", fact.provider_key)
            say("C_MINUTES", fact.minutes)
            say("C_FACT_QUALITY", fact.fact_quality)
            say("C_TIME_BASIS", fact.time_basis)
            say("C_MODE", fact.mode)
            say("C_GEOMETRY_POINTS", len(fact.route_geometry))
            say("C_GEOMETRY_PROVIDER", fact.geometry_provider)
            say("C_FACT_DEGRADED", fact.degraded)
            say("C_CAPTURE_DEGRADED", result.snapshot.degraded)
            say("C_FALLBACK_PAIRS", len(result.fallback_pairs))
            say("C_FAILED_PRIMARY_PAIRS", len(result.failed_primary_pairs))
            say("C_PROVIDER_CAPABILITIES", sorted(result.snapshot.provider_capabilities))
            require("C_LIVE_FACT", fact.provider_key == "amap-web-service")
            require("C_QUALITY", fact.fact_quality == "LIVE_PROVIDER_CAPTURE")
            require("C_DURATION", isinstance(fact.minutes, int) and fact.minutes > 0)
            require("C_GEOMETRY", len(fact.route_geometry) > 0)
    finally:
        session.close()

    if FAILURES:
        say("ORD0701_FAILED_LEGS", ",".join(FAILURES))
        print("ORD0701_PROOF=FAIL")
        return 1
    print("ORD0701_PROOF=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
