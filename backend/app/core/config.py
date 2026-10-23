from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("CITYNEXUS_ENV", "development")
    database_url: str = os.getenv("CITYNEXUS_DATABASE_URL", "sqlite:///./citynexus.db")
    # ORD-0058: the only switch that turns the seeded scenario into something a person can
    # walk through.  Default OFF, and off means a normal production journey never silently
    # inherits simulation semantics.  Guarded doors read this through
    # `app.main.demo_mode_enabled()` so a test can exercise both states.
    demo_mode: bool = os.getenv("CITYNEXUS_DEMO_MODE", "false").lower() == "true"
    ai_enabled: bool = os.getenv("CITYNEXUS_AI_ENABLED", "false").lower() == "true"
    ai_provider: str = os.getenv("CITYNEXUS_AI_PROVIDER", "deepseek")
    ai_model: str = os.getenv("CITYNEXUS_AI_MODEL", "deepseek-v4-flash")
    ai_vision_model: str = os.getenv(
        "CITYNEXUS_AI_VISION_MODEL", "deepseek-v4-flash-vision-exp"
    )
    ai_api_key: str | None = (
        os.getenv("CITYNEXUS_AI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or None
    )
    deepseek_api_url: str = os.getenv(
        "CITYNEXUS_DEEPSEEK_API_URL", "https://api.deepseek.com/responses"
    )
    deepseek_reasoning_effort: str = os.getenv("CITYNEXUS_DEEPSEEK_REASONING_EFFORT", "high")
    deepseek_web_search_enabled: bool = (
        os.getenv("CITYNEXUS_DEEPSEEK_WEB_SEARCH", "true").lower() == "true"
    )
    vapid_public_key: str | None = os.getenv("CITYNEXUS_VAPID_PUBLIC_KEY") or None
    vapid_private_key: str | None = os.getenv("CITYNEXUS_VAPID_PRIVATE_KEY") or None
    vapid_subject: str = os.getenv("CITYNEXUS_VAPID_SUBJECT", "mailto:ops@citynexus.local")
    impact_provider: str = os.getenv("CITYNEXUS_IMPACT_PROVIDER", "disabled")
    impact_timeout_seconds: float = float(os.getenv("CITYNEXUS_IMPACT_TIMEOUT_SECONDS", "10"))
    # Agent identity is server-owned. A configured token is required outside
    # local development; the request body's agent_id is never authoritative.
    agent_token: str | None = os.getenv("CITYNEXUS_AGENT_TOKEN") or None
    agent_principal_id: str = os.getenv("CITYNEXUS_AGENT_PRINCIPAL_ID", "citynexus-local-agent")
    # ORD-0685: the traveller principal's signing secret.  Empty means the door refuses every
    # caller (503, named) rather than accepting an identity it cannot verify; it is never
    # defaulted to a literal, because a default secret is a public secret.
    traveler_auth_secret: str | None = os.getenv("CITYNEXUS_TRAVELER_AUTH_SECRET") or None
    traveler_auth_ttl_seconds: int = int(
        os.getenv("CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS", "900")
    )
    # GPT P0-SEC (Issue #31): once this build CAN verify a traveller, dropping the `Authorization`
    # header must not be a way to step outside that check.  Anonymous reads of private trips are
    # therefore refused by default whenever a signing secret is configured.  A demo or public
    # preview that genuinely needs anonymous reads opts back in **by name**, in its own local
    # configuration -- not by the accident of "nobody carried a token today".
    traveler_auth_allow_anonymous_private: bool = (
        os.getenv("CITYNEXUS_TRAVELER_AUTH_ALLOW_ANONYMOUS_PRIVATE", "").strip().lower()
        in {"1", "true", "yes"}
    )
    agent_allowed_traveler_ids: tuple[str, ...] = tuple(
        item.strip()
        for item in os.getenv("CITYNEXUS_AGENT_ALLOWED_TRAVELER_IDS", "").split(",")
        if item.strip()
    )
    live_valhalla_url: str | None = os.getenv("CITYNEXUS_LIVE_VALHALLA_URL") or None
    open_meteo_url: str = os.getenv("CITYNEXUS_OPEN_METEO_URL", "https://api.open-meteo.com")
    open_meteo_timeout_seconds: float = float(
        os.getenv("CITYNEXUS_OPEN_METEO_TIMEOUT_SECONDS", "10")
    )
    solver_mode: str = os.getenv("CITYNEXUS_SOLVER", "deterministic")
    hermes_api_url: str | None = os.getenv("CITYNEXUS_HERMES_API_URL")
    hermes_api_key: str | None = os.getenv("CITYNEXUS_HERMES_API_KEY")
    hermes_model: str = os.getenv("CITYNEXUS_HERMES_MODEL", "hermes")
    hermes_native_binary: str | None = os.getenv("CITYNEXUS_HERMES_BINARY") or None
    hermes_native_proven: str | None = os.getenv("CITYNEXUS_HERMES_NATIVE_PROVEN") or None
    hermes_native_api_url: str | None = os.getenv("CITYNEXUS_HERMES_NATIVE_API_URL") or None
    hermes_api_server_key: str | None = os.getenv("CITYNEXUS_HERMES_API_SERVER_KEY") or None
    hermes_native_profile: str = os.getenv("CITYNEXUS_HERMES_NATIVE_PROFILE", "citynexus")
    # Native Hermes Runs API selection is separate from the legacy OpenAI-compatible
    # Hermes endpoint. Leave both unset to let the Hermes profile choose its own model.
    hermes_native_provider: str | None = os.getenv("CITYNEXUS_HERMES_NATIVE_PROVIDER") or None
    hermes_native_model: str | None = os.getenv("CITYNEXUS_HERMES_NATIVE_MODEL") or None
    guardian_autorun: bool = os.getenv("CITYNEXUS_GUARDIAN_AUTORUN", "false").lower() == "true"
    guardian_interval_seconds: float = float(os.getenv("CITYNEXUS_GUARDIAN_INTERVAL_SECONDS", "60"))
    guardian_signal_provider: str = os.getenv("CITYNEXUS_GUARDIAN_SIGNAL_PROVIDER", "demo").lower()
    guardian_cooldown_seconds: int = int(os.getenv("CITYNEXUS_GUARDIAN_COOLDOWN_SECONDS", "900"))
    real_city_enabled: bool = os.getenv("CITYNEXUS_REAL_CITY_ENABLED", "false").lower() == "true"
    real_city_mode: str = os.getenv("CITYNEXUS_REAL_CITY_MODE", "replay").lower()
    # Revolution Lab only: estimated opening/cost facts may make a plan selectable inside an
    # explicitly labelled coursework envelope. The default remains false.
    lab_estimate_authority: bool = (
        os.getenv("CITYNEXUS_LAB_ESTIMATE_AUTHORITY", "false").lower() == "true"
    )
    real_city_replay_snapshot_path: str = os.getenv(
        "CITYNEXUS_REAL_CITY_REPLAY_SNAPSHOT", "data/replay/tianjin_v135_journey_snapshot.json"
    )
    nominatim_url: str = os.getenv("CITYNEXUS_NOMINATIM_URL", "https://nominatim.openstreetmap.org")
    overpass_url: str = os.getenv("CITYNEXUS_OVERPASS_URL", "https://overpass-api.de/api")
    # Optional sourceful search for fact acquisition. Search results are leads only;
    # they never become authoritative opening or cost facts by themselves.
    searxng_url: str | None = os.getenv("CITYNEXUS_SEARXNG_URL") or None
    real_city_timeout_seconds: float = float(os.getenv("CITYNEXUS_REAL_CITY_TIMEOUT_SECONDS", "12"))
    real_city_cache_ttl_seconds: int = int(
        os.getenv("CITYNEXUS_REAL_CITY_CACHE_TTL_SECONDS", "900")
    )
    openfreemap_style_url: str = os.getenv(
        "CITYNEXUS_OPENFREEMAP_STYLE_URL", "https://tiles.openfreemap.org/styles/liberty"
    )
    predictive_risk_threshold: int = int(os.getenv("CITYNEXUS_PREDICTIVE_RISK_THRESHOLD", "65"))
    predictive_autopilot_enabled: bool = (
        os.getenv("CITYNEXUS_PREDICTIVE_AUTOPILOT_ENABLED", "true").lower() == "true"
    )
    solver_random_seed: int = int(os.getenv("CITYNEXUS_SOLVER_RANDOM_SEED", "1"))
    solver_max_time_seconds: float = float(os.getenv("CITYNEXUS_SOLVER_MAX_TIME_SECONDS", "1.0"))
    # ORD-0296 (ORD-0281's backend half): the server's own bound on a write attempt, and the only
    # place SQLite's lock wait is configured.  `write_busy_timeout_ms` is what the engine actually
    # hands to SQLite; `write_deadline_ms` is the budget a caller declares for the whole write, and
    # `effective_busy_timeout_ms()` caps the wait by it.  A deadline at or below the lock wait is
    # rejected at the doors: it would make *my configuration* the reason a write gave up, which is
    # how a deadline ends up impersonating the server (ORD-0281 T-b).  Per-scenario values come from
    # `write_deadline_scenarios` so one route can be tightened without moving everyone's default.
    write_busy_timeout_ms: int = int(os.getenv("CITYNEXUS_WRITE_BUSY_TIMEOUT_MS", "30000"))
    write_deadline_ms: int = int(os.getenv("CITYNEXUS_WRITE_DEADLINE_MS", "45000"))
    write_deadline_scenarios: str = os.getenv("CITYNEXUS_WRITE_DEADLINE_SCENARIOS", "")
    # Process-ownership token for the authoritative frontend E2E gate.  The suite
    # starts its own backend with a per-run value and refuses to trust a /health
    # that does not echo it, so a server belonging to another checkout or another
    # agent lane can never answer for this tree's tests again.
    e2e_run_id: str | None = os.getenv("CITYNEXUS_E2E_RUN_ID") or None


settings = Settings()
