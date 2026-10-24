"""A second provider entry for the same venue is not a replacement.

Measured on the classroom journey: the closed 故宫博物院 (AMap) had a sibling
Overpass row with the same name ~110 m away and a different category vocabulary,
so the identity contract called them DIFFERENT and the replan offered the same
palace as its own replacement.  This guard is deliberately about what a traveller
can see, not about proving identity.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.replanning.mock_replan_engine import (
    should_exclude_replacement_candidate,
)

LAT = 39.9164375921294
LON = 116.39078695427294


def _place(name: str, category: str, lat: float, lon: float, key: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=key,
        name=name,
        category=category,
        latitude=lat,
        longitude=lon,
        provider_key="amap" if key == "a" else "overpass",
        external_id=("amap:B0" if key == "a" else "overpass:node/1"),
        metadata_json="{}",
        tags_json="[]",
        city_code="CN-RV-X",
    )


def test_same_name_nearby_with_a_different_category_vocabulary_is_excluded() -> None:
    closed = _place("故宫博物院", "风景名胜;风景名胜;世界遗产|科教文化服务;博物馆", LAT, LON, "a")
    sibling = _place("故宫博物院", "museum", LAT + 0.00099, LON + 0.000006, "b")

    assert should_exclude_replacement_candidate(sibling, closed) is True


def test_same_name_far_away_is_still_a_candidate() -> None:
    closed = _place("便利店", "retail", LAT, LON, "a")
    branch = _place("便利店", "shop", LAT + 0.0045, LON, "b")

    assert should_exclude_replacement_candidate(branch, closed) is False


def test_different_name_at_the_same_spot_is_still_a_candidate() -> None:
    closed = _place("故宫博物院", "museum", LAT, LON, "a")
    neighbour = _place("角楼咖啡", "cafe", LAT + 0.0001, LON + 0.0001, "b")

    assert should_exclude_replacement_candidate(neighbour, closed) is False
