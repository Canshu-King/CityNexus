from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main_module
from app.agent.gateway import AgentToolGateway
from app.db.models import Event
from app.db.session import SessionLocal
from app.integrations.context.open_meteo import (
    OpenMeteoContextProvider,
    WeatherObservation,
)
from app.main import app
from app.schemas import AgentToolCall
from demo_stage import demo_reset_headers

client = TestClient(app)


class _BenignLiveWeather:
    provider_key = "open-meteo"
    capture_provenance = "LIVE_PROVIDER"

    async def forecast(self, *, latitude: float, longitude: float) -> list[WeatherObservation]:
        return [
            WeatherObservation(
                at=datetime(2026, 10, 10, 7, 0, tzinfo=timezone.utc),
                precipitation_probability=20,
                weather_code=3,
            )
        ]

    def risks(self, observations: list[WeatherObservation]):
        return OpenMeteoContextProvider(client=None).risks(observations)  # type: ignore[arg-type]


def _started_journey_id() -> str:
    journey_id = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()["journey_id"]
    generated = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate",
        json={"candidate_count": 1},
    )
    assert generated.status_code == 201, generated.text
    plan_id = generated.json()[0]["id"]
    assert client.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select").status_code == 200
    assert client.post(f"/api/v1/journeys/{journey_id}/start").status_code == 200
    return journey_id


def test_r34_weather_code_materiality_expands_without_lowering_heavy_rain_threshold():
    provider = OpenMeteoContextProvider(client=None)  # type: ignore[arg-type]
    at = datetime(2026, 10, 10, 7, 0, tzinfo=timezone.utc)

    assert provider.risks(
        [WeatherObservation(at=at, precipitation_probability=69, weather_code=3)]
    ) == []

    threshold = provider.risks(
        [WeatherObservation(at=at, precipitation_probability=70, weather_code=3)]
    )
    assert [item.code for item in threshold] == ["HEAVY_RAIN_RISK"]

    rain = provider.risks(
        [WeatherObservation(at=at, precipitation_probability=20, weather_code=61)]
    )
    assert [item.code for item in rain] == ["RAIN_CONDITION_RISK"]
    assert rain[0].severity == "MEDIUM"
    assert rain[0].evidence["materiality_basis"] == "WMO_WEATHER_CODE"

    storm = provider.risks(
        [WeatherObservation(at=at, precipitation_probability=20, weather_code=97)]
    )
    assert [item.code for item in storm] == ["THUNDERSTORM_RISK"]
    assert storm[0].severity == "HIGH"


def test_r34_benign_provider_reading_survives_as_world_context_without_forging_event(monkeypatch):
    journey_id = _started_journey_id()
    monkeypatch.setattr(
        main_module,
        "build_open_meteo_provider",
        lambda _client: _BenignLiveWeather(),
        raising=False,
    )

    refreshed = client.post(f"/api/v1/journeys/{journey_id}/weather/refresh")
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["event_ids"] == []
    assert refreshed.json()["observation_ids"]

    context = client.get(f"/api/v1/journeys/{journey_id}/world-context")
    assert context.status_code == 200, context.text
    weather = [
        item
        for item in context.json()["observations"]
        if item["observation_type"] == "WEATHER"
        and item.get("activity_observations")
    ]
    assert weather
    relevant = weather[0]
    assert relevant["provenance"] == "LIVE_PROVIDER"
    assert relevant["material_risk"] is False
    assert relevant["activity_observations"][0]["precipitation_probability"] == 20
    assert relevant["activity_observations"][0]["weather_code"] == 3

    with SessionLocal() as session:
        provider_events = session.scalars(
            select(Event).where(
                Event.journey_id == journey_id,
                Event.provider_key == "open-meteo",
                Event.provenance == "PROVIDER_VERIFIED",
            )
        ).all()
    assert provider_events == []


def test_r34_agent_inspection_sees_world_context_but_not_a_fabricated_weather_event(monkeypatch):
    journey_id = _started_journey_id()
    monkeypatch.setattr(
        main_module,
        "build_open_meteo_provider",
        lambda _client: _BenignLiveWeather(),
        raising=False,
    )
    refreshed = client.post(f"/api/v1/journeys/{journey_id}/weather/refresh")
    assert refreshed.status_code == 200, refreshed.text

    with SessionLocal() as session:
        result = AgentToolGateway(session).inspect_twin(
            AgentToolCall(
                request_id="r34-inspect-world-0001",
                agent_id="r34-test-agent",
                journey_id=UUID(journey_id),
            )
        )
        provider_context = result["provider_context"]["observations"]
        weather = [
            item
            for item in provider_context
            if item["observation_type"] == "WEATHER"
            and item.get("activity_observations")
        ]
        assert weather
        assert weather[0]["material_risk"] is False
        assert result["current_event"] is None or result["current_event"]["provenance"] != "PROVIDER_VERIFIED"
