"""ORD-0701: one Amap key, two accepted environment names.

This deployment's local configuration tool writes ``CITYNEXUS_AMAP_WEB_KEY`` while this module has
always read ``AMAP_WEB_KEY``.  A backend restarted with the configured name therefore answered
NOT_CONFIGURED even though a key was present - which reads to a traveller as "this city has no
routing provider", and to whoever restarts the service as a reason to re-enter a secret somewhere
it should never need re-entering.  Both names are now accepted, in a stated order, from one reader.

Nothing here uses a real key: the values are invented for the assertion, and a test would fail if
any of them ever reached a payload.
"""

from __future__ import annotations

import asyncio
import pathlib

import pytest

from app.integrations.china import amap
from app.integrations.china.amap import (
    AmapMobilityProvider,
    AmapPoiProvider,
    KEY_ENV_LEGACY,
    KEY_ENV_PREFERRED,
    amap_status,
    key_env_name,
    missing_key_reason,
    web_key,
)

PREFERRED_VALUE = "preferred-name-answer"
LEGACY_VALUE = "legacy-name-answer"


@pytest.fixture(autouse=True)
def _no_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neither name is set unless a test says so - the machine's own env must not leak in."""

    monkeypatch.delenv(KEY_ENV_PREFERRED, raising=False)
    monkeypatch.delenv(KEY_ENV_LEGACY, raising=False)


def test_preferred_name_alone_is_enough_to_call_the_provider_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(KEY_ENV_PREFERRED, PREFERRED_VALUE)

    status = amap_status()
    assert status.status == "READY"
    assert status.provenance == "LIVE"
    assert status.reason is None
    assert key_env_name() == KEY_ENV_PREFERRED


def test_the_name_this_machine_already_uses_keeps_answering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(KEY_ENV_LEGACY, LEGACY_VALUE)

    status = amap_status()
    assert status.status == "READY"
    assert web_key() == LEGACY_VALUE
    assert key_env_name() == KEY_ENV_LEGACY


def test_the_preferred_name_wins_when_both_are_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(KEY_ENV_PREFERRED, PREFERRED_VALUE)
    monkeypatch.setenv(KEY_ENV_LEGACY, LEGACY_VALUE)

    assert web_key() == PREFERRED_VALUE
    assert key_env_name() == KEY_ENV_PREFERRED


def test_absent_keys_are_named_without_naming_a_value() -> None:
    status = amap_status()
    reason = status.reason or ""

    assert status.status == "NOT_CONFIGURED"
    assert KEY_ENV_PREFERRED in reason
    assert KEY_ENV_LEGACY in reason
    assert missing_key_reason() == reason
    assert PREFERRED_VALUE not in reason and LEGACY_VALUE not in reason


def test_a_call_still_refuses_to_leave_without_a_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The guard is the first statement in each provider method - no key, no request."""

    monkeypatch.setenv(KEY_ENV_PREFERRED, PREFERRED_VALUE)
    monkeypatch.delenv(KEY_ENV_PREFERRED)

    with pytest.raises(RuntimeError) as poi:
        asyncio.run(AmapPoiProvider().search("noodles", "CN-TIANJIN"))
    with pytest.raises(RuntimeError) as route:
        asyncio.run(
            AmapMobilityProvider().route(
                "WALK",
                origin_wgs84=(39.13, 117.20),
                destination_wgs84=(39.12, 117.19),
                city_code="CN-TIANJIN",
            )
        )

    assert missing_key_reason() in str(poi.value)
    assert missing_key_reason() in str(route.value)


def test_no_reader_asks_for_one_environment_name_alone() -> None:
    """A second reader would reintroduce the half-configured answer this order exists to stop."""

    roots = [
        pathlib.Path(amap.__file__),
        pathlib.Path(amap.__file__).parents[2] / "stay_mobility.py",
    ]
    needle = f'os.getenv("{KEY_ENV_LEGACY}")'
    offenders = [
        f"{path.name}:{number}"
        for path in roots
        for number, row in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if needle in row
    ]

    assert offenders == []
