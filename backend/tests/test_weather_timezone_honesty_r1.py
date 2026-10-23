from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.models import Journey
from app.db.session import SessionLocal
from app.integrations.context.open_meteo import WeatherObservation, WeatherRisk
from app.integrations.context.weather_runtime import refresh_weather_runtime
from app.main import app
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(app)


class _RiskProvider:
    provider_key = "open-meteo"

    def __init__(self, *, risk_at: datetime) -> None:
        self.risk_at = risk_at

    async def forecast(self, *, latitude: float, longitude: float) -> list[WeatherObservation]:
        return [
            WeatherObservation(
                at=self.risk_at,
                precipitation_probability=90,
                weather_code=65,
            )
        ]

    def risks(self, observations: list[WeatherObservation]) -> list[WeatherRisk]:
        return [
            WeatherRisk(
                code="HEAVY_RAIN_RISK",
                severity="HIGH",
                at=item.at,
                evidence={
                    "precipitation_probability": item.precipitation_probability,
                    "weather_code": item.weather_code,
                },
            )
            for item in observations
        ]


def _started_journey() -> str:
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    jid = ids["journey_id"]
    generated = client.post(f"/api/v1/journeys/{jid}/plans/generate", json={"candidate_count": 1})
    assert generated.status_code == 201, generated.text
    plan = generated.json()[0]
    selected = client.post(f"/api/v1/journeys/{jid}/plans/{plan['id']}/select")
    assert selected.status_code == 200, selected.text
    started = client.post(f"/api/v1/journeys/{jid}/start")
    assert started.status_code == 200, started.text
    return jid


def _set_timezone(jid: str, value: str) -> None:
    with SessionLocal() as session:
        journey = session.get(Journey, jid)
        assert journey is not None
        journey.timezone = value
        session.commit()


@pytest.mark.asyncio
async def test_an_unusable_zone_keeps_the_weather_and_names_why_it_could_not_attribute():
    jid = _started_journey()
    _set_timezone(jid, "Mars/Phobos")
    provider = _RiskProvider(risk_at=datetime(2026, 10, 10, 7, 0, tzinfo=timezone.utc))
    with SessionLocal() as session:
        journey = session.get(Journey, jid)
        assert journey is not None
        result = await refresh_weather_runtime(
            session,
            journey,
            provider=provider,
            captured_at="2026-10-10T06:55:00+00:00",
        )

    assert result.timezone_honoured is False
    assert result.used_timezone is None
    assert result.attribution_skipped_reason_codes == ("JOURNEY_TIMEZONE_UNUSABLE",)
    assert result.degraded is True
    assert result.attributions == ()
    assert result.event_ids == ()
    assert result.snapshots, "the provider evidence must survive an unusable zone"
    evidence = result.to_evidence()
    assert evidence["timezone_honoured"] is False
    assert evidence["used_timezone"] is None
    assert evidence["attribution_skipped_reason_codes"] == ["JOURNEY_TIMEZONE_UNUSABLE"]


@pytest.mark.asyncio
async def test_a_usable_zone_still_attributes_and_says_which_zone_it_used():
    jid = _started_journey()
    _set_timezone(jid, "Asia/Shanghai")
    provider = _RiskProvider(risk_at=datetime(2026, 10, 10, 7, 0, tzinfo=timezone.utc))
    with SessionLocal() as session:
        journey = session.get(Journey, jid)
        assert journey is not None
        result = await refresh_weather_runtime(
            session,
            journey,
            provider=provider,
            captured_at="2026-10-10T06:55:00+00:00",
        )

    assert result.timezone_honoured is True
    assert result.used_timezone == "Asia/Shanghai"
    assert result.attribution_skipped_reason_codes == ()
    assert result.degraded is False
    assert result.attributions
    assert result.attributions[0].local_risk_start_at == "2026-10-10T15:00:00+08:00"
    assert result.event_ids
