"""ORD-0191 ⑤ / ORD-0167 - the destination leg that lets a *real* provider name a place.

Why this file exists: `云和县` is a county that exists, and the only way this build could answer
about it was "structurally unusable" - because the resolver was allowed to read nothing but this
process.  The commander measured that at `8ee64ae` and asked for one function and one call site.
The other half of the truth is that a live leg inside a read endpoint would make the default suite
leave the process (§17C) and would let a developer's shell silently change product answers - so the
leg is **off by default** (R6), and every door here turns it on with a mocked transport and asserts
the transport is the thing that answered.

What each door refuses to allow:

* a fuzzy provider hit becoming an identity (a near match is not testimony);
* a hash or the traveller's text becoming an identity when the provider finds nothing;
* a timeout becoming `UNAVAILABLE` (R1's forbidden laundering, now with a real network in the loop);
* two disagreeing provider answers being collapsed into whichever came first;
* the seam being on in the default configuration, or any network attempt happening while it is off.
"""

from __future__ import annotations

import json
import os

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.anywhere_capability as capability_module
from app.db.models import CatalogHydrationOperation, Place
from app.db.session import SessionLocal
from app.integrations.discovery.photon import PhotonGeocoder
from app.main import app

client = TestClient(app)
CAPABILITY = "/api/v1/destinations/capability"
HYDRATIONS = "/api/v1/catalog-hydrations"

RAW_COUNTY = "云和县"
COUNTY_ENTITY_ID = "R:3289208"
COUNTY_CANONICAL = f"OSM:{COUNTY_ENTITY_ID}"
COUNTY_EXTENT = [119.36, 27.95, 119.79, 28.36]
COUNTY_CENTROID = [119.5684002, 28.1185318]


@pytest.fixture()
def seeded(monkeypatch) -> str:
    monkeypatch.setattr("app.main.demo_mode_enabled", lambda: True)
    reset = client.post("/api/v1/demo/reset")
    assert reset.status_code == 200, reset.text
    with SessionLocal() as session:
        session.execute(CatalogHydrationOperation.__table__.delete())
        session.commit()
    yield str(reset.json()["traveler_id"])
    with SessionLocal() as session:
        session.execute(CatalogHydrationOperation.__table__.delete())
        session.commit()


def _feature(
    *,
    osm_id: int,
    osm_type: str = "R",  # the letter Photon really returns, measured 2026-09-22 01:4x
    name: str,
    centre=None,
    extent=None,
    country: str = "中国",
    extra: str = "",
) -> dict:
    properties = {
        "osm_id": osm_id,
        "osm_type": osm_type,
        "name": name,
        "country": country,
        "type": "administrative",
    }
    if extent:
        properties["extent"] = extent
    geometry_centre = centre or [119.5684002, 28.1185318]
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": geometry_centre},
        "properties": properties,
    }


def _featurecollection(*features) -> str:
    return json.dumps({"type": "FeatureCollection", "features": list(features)}, ensure_ascii=False)


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(str(request.url))
        return self.response(request)

    def response(self, request: httpx.Request) -> httpx.Response:  # pragma: no cover - overridden
        raise AssertionError("not wired")


def _install(monkeypatch, recorder: _Recorder) -> None:
    """Point the product's resolver leg at a transport that cannot reach a network."""

    def build() -> PhotonGeocoder:
        http = httpx.AsyncClient(transport=httpx.MockTransport(recorder.handler))
        return PhotonGeocoder(client=http)

    monkeypatch.setattr(capability_module, "_provider_geocoder", build)


def _answer(monkeypatch, features=(), *, raise_with: Exception | None = None) -> _Recorder:
    class Recorder(_Recorder):
        def response(self, request: httpx.Request) -> httpx.Response:
            if raise_with is not None:
                raise raise_with
            return httpx.Response(200, text=_featurecollection(*features))

    recorder = Recorder()
    _install(monkeypatch, recorder)
    return recorder


def _enable(monkeypatch, name: str = "photon") -> None:
    monkeypatch.setenv("CITYNEXUS_ANYWHERE_RESOLVER", name)


def _capability(query: str) -> dict:
    read = client.get(CAPABILITY, params={"query": query})
    assert read.status_code == 200, read.text
    return read.json()


# ---------------------------------------------------------------------------------------------
# The reading the commander asked for, before and after
# ---------------------------------------------------------------------------------------------
def test_g1_default_off_still_answers_structurally_and_attempts_no_network(seeded, monkeypatch) -> None:
    """ seam 关着时行为一字不变，且一次网络都不试（默认套件不许出网）。"""

    monkeypatch.delenv("CITYNEXUS_ANYWHERE_RESOLVER", raising=False)
    recorder = _answer(monkeypatch, features=(_feature(osm_id=3289208, osm_type="R", name=RAW_COUNTY),))
    assert capability_module.anywhere_resolver_name() == "off"
    body = _capability(RAW_COUNTY)
    assert body["capability"] == "UNAVAILABLE", body["capability"]
    assert body["reason_code"] == capability_module.REASON_NO_CANONICAL_IDENTITY
    assert body["recommended_action"] == capability_module.ACTION_CHOOSE_ANOTHER_DESTINATION
    assert body["canonical_destination_id"] is None
    assert body["pending_destination_label"] == RAW_COUNTY
    assert "provider_status" not in body, (
        f"期望：没查过就没有观测（R2 的缺席即诚实）；实际：{body.get('provider_status')}"
    )
    assert recorder.calls == [], f"期望 seam 关着时一次外呼都不发；实际：{recorder.calls}"


def test_g2_a_provider_named_county_becomes_hydratable_not_dead(seeded, monkeypatch) -> None:
    """ORD-0191 ⑤ 的那一格：provider 认得 ⇒ 真 canonical + HYDRATABLE + 可准备，不再判死。"""

    _enable(monkeypatch)
    recorder = _answer(
        monkeypatch,
        features=(
            _feature(
                osm_id=3289208,
                osm_type="R",
                name=RAW_COUNTY,
                extent=COUNTY_EXTENT,
                centre=COUNTY_CENTROID,
            ),
        ),
    )
    body = _capability(RAW_COUNTY)
    assert body["canonical_destination_id"] == COUNTY_CANONICAL, (
        f"期望：provider 给的实体成为服务端持有的 canonical（{COUNTY_CANONICAL}）；实际："
        f"{body['canonical_destination_id']!r}"
    )
    assert body["destination_state"] == "RESOLVED", body["destination_state"]
    assert body["capability"] == "HYDRATABLE", (
        f"期望：地名成立但本地目录不足 ⇒ HYDRATABLE；实际：{body['capability']}"
    )
    assert body["recommended_action"] == capability_module.ACTION_START_HYDRATION, body[
        "recommended_action"
    ]
    assert body["pending_destination_label"] == RAW_COUNTY, (
        "期望：即使解析成功，原话仍逐字保留（审计半边归 0167 ②）；实际："
        f"{body['pending_destination_label']!r}"
    )
    assert recorder.calls and "q=" in recorder.calls[0], recorder.calls
    provenance = body.get("destination_provenance") or {}
    assert provenance.get("source_provider") == "photon", provenance
    assert provenance.get("source_entity_id") == COUNTY_ENTITY_ID, provenance
    assert provenance.get("coordinate_system") == "WGS84", provenance
    assert provenance.get("centroid") == {"latitude": COUNTY_CENTROID[1], "longitude": COUNTY_CENTROID[0]}, (
        provenance
    )
    assert provenance.get("extent") == COUNTY_EXTENT, (
        f"期望：provider 给的 extent 原样带上（发现范围不许退回 5 km 圆）；实际：{provenance}"
    )
    status = (body.get("provider_status") or [{}])[0]
    assert status.get("status") == "OK", body.get("provider_status")


# ---------------------------------------------------------------------------------------------
# The four classes, kept apart
# ---------------------------------------------------------------------------------------------
def test_g3_healthy_provider_with_no_answer_is_unavailable_and_invents_nothing(
    seeded, monkeypatch
) -> None:
    """provider 好好回答了但没这个东西 ⇒ UNAVAILABLE + canonical=null，且不落任何文本/摘要身份。"""

    _enable(monkeypatch)
    _answer(monkeypatch, features=())
    body = _capability("不存在的县xzq")
    assert body["capability"] == "UNAVAILABLE", body["capability"]
    assert body["canonical_destination_id"] is None, body["canonical_destination_id"]
    assert body["pending_destination_label"] == "不存在的县xzq"
    status = (body.get("provider_status") or [{}])[0]
    assert status.get("status") == "OK", (
        f"期望：200 + 空集合 = 一次成功的观测，不是失败；实际：{body.get('provider_status')}"
    )
    assert body["destination_state"] == "NO_MATCH", body["destination_state"]
    for key, value in body.items():
        if key in {"query", "pending_destination_label", "resolver_query_normalized"}:
            continue
        assert "xzq" not in str(value), f"字段 {key} 带着原文却不属于那三栏：{value!r}"


def test_g4_a_timeout_stays_a_named_runtime_failure_and_never_structural(seeded, monkeypatch) -> None:
    """硬负例（仲裁原列）：超时/传输失败不得变成 NO_MATCH/UNAVAILABLE，也不得写 hash。"""

    _enable(monkeypatch)
    _answer(monkeypatch, raise_with=httpx.ConnectTimeout("connect timed out"))
    body = _capability(RAW_COUNTY)
    assert body["destination_state"] == "RUNTIME_FAILURE", body["destination_state"]
    assert body["capability"] == "HYDRATABLE", (
        f"期望：连不上不是结构结论，目的地仍是可准备的；实际：{body['capability']}"
    )
    assert body["reason_code"] == capability_module.REASON_RESOLVER_UNAVAILABLE, body["reason_code"]
    assert body["reason_code"] in capability_module.TRANSIENT_REASONS
    assert body["retryable"] is True, body["retryable"]
    assert body["canonical_destination_id"] is None
    status = (body.get("provider_status") or [{}])[0]
    assert status.get("status") == "UNREACHABLE", body.get("provider_status")
    assert body["pending_destination_label"] == RAW_COUNTY, (
        "期望：失败也要原样留着用户那句话，重试不用重打；实际："
        f"{body['pending_destination_label']!r}"
    )


def test_g5_two_disagreeing_answers_must_not_pick_one(seeded, monkeypatch) -> None:
    """两个**都带边界**的同名实体 ⇒ 不许替用户选（面 vs 点的收敛另有一条门，别混过来）。"""

    _enable(monkeypatch)
    _answer(
        monkeypatch,
        features=(
            _feature(
                osm_id=3289208, osm_type="R", name=RAW_COUNTY, country="中国",
                extent=COUNTY_EXTENT,
            ),
            _feature(
                osm_id=999, osm_type="R", name=RAW_COUNTY, country="蒙古",
                extent=[100.1, 46.1, 100.9, 47.2],
            ),
        ),
    )
    body = _capability(RAW_COUNTY)
    assert body["destination_state"] == "AMBIGUOUS", body["destination_state"]
    assert body["canonical_destination_id"] is None
    ids = {item.get("source_entity_id") for item in body.get("candidates") or []}
    assert ids == {COUNTY_ENTITY_ID, "R:999"}, body.get("candidates")


def test_g6_a_fuzzy_near_match_is_not_an_identity(seeded, monkeypatch) -> None:
    """Photon 会容错：回来的名字不是用户问的那个 ⇒ 这不是解析成功，是"没这个东西"。"""

    _enable(monkeypatch)
    _answer(
        monkeypatch,
        features=(_feature(osm_id=1234567, osm_type="W", name="遂昌县", country="中国"),),
    )
    body = _capability("云合")
    assert body["destination_state"] == "NO_MATCH", body["destination_state"]
    assert body["canonical_destination_id"] is None, (
        f"期望：近似命中不得冒充身份；实际：{body['canonical_destination_id']!r}"
    )
    assert body["capability"] == "UNAVAILABLE", body["capability"]


def test_g10_one_place_two_index_entries_collapses_under_a_named_version(seeded, monkeypatch) -> None:
    """实测形状（02:2x 打真 provider 拿到的读数）：同名同地有两条记录——面（带 extent 的 relation）
    与点（裸 node）。这是同一座城的两种表达，不是两座城市，所以不得反过来要求用户裁决；
    但收敛必须由**具名版本化策略**做，并把它放弃的那条**记下来**。"""

    _enable(monkeypatch)
    _answer(
        monkeypatch,
        features=(
            _feature(
                osm_id=3289208, osm_type="R", name=RAW_COUNTY, extent=COUNTY_EXTENT, centre=COUNTY_CENTROID
            ),
            _feature(osm_id=244082768, osm_type="N", name=RAW_COUNTY, centre=[119.5779441, 28.1096051]),
        ),
    )
    body = _capability(RAW_COUNTY)
    assert body["destination_state"] == "RESOLVED", body["destination_state"]
    assert body["canonical_destination_id"] == COUNTY_CANONICAL, (
        f"期望：面（relation + extent）是目的地身份；实际：{body['canonical_destination_id']!r}"
    )
    provenance = body["destination_provenance"]
    assert provenance["discriminated_by"] == (
        capability_module.DESTINATION_DISCRIMINATION_POLICY_VERSION
    ), provenance
    collapsed = {item["source_entity_id"] for item in provenance["collapsed_candidates"]}
    assert collapsed == {"N:244082768"}, (
        f"期望：被放弃的那条要**记名**，不是静默丢；实际：{provenance['collapsed_candidates']}"
    )
    assert provenance["extent"] == COUNTY_EXTENT and len(provenance["extent"]) == 4


# ---------------------------------------------------------------------------------------------
# The identity has to survive into the job, not just the answer
# ---------------------------------------------------------------------------------------------
def test_g7_a_resolved_identity_reaches_the_stored_operation_without_any_pending_token(
    seeded, monkeypatch
) -> None:
    """⑤ 的后半：服务端持有的身份要落进作业行，且 `pending:` 一个都不留。"""

    _enable(monkeypatch)
    _answer(
        monkeypatch,
        features=(_feature(osm_id=3289208, osm_type="R", name=RAW_COUNTY, extent=COUNTY_EXTENT),),
    )
    posted = client.post(HYDRATIONS, json={"query": RAW_COUNTY})
    assert posted.status_code in (200, 202), posted.text
    body = posted.json()
    assert body["canonical_destination_id"] == COUNTY_CANONICAL, body["canonical_destination_id"]
    with SessionLocal() as session:
        row = session.scalar(
            select(CatalogHydrationOperation).where(
                CatalogHydrationOperation.id == body["operation_id"]
            )
        )
    assert row is not None
    assert row.canonical_destination_id == COUNTY_CANONICAL
    assert row.pending_destination_label == RAW_COUNTY
    assert row.destination_pending_key is None, (
        f"期望：已经有真身份的作业不发 correlation token；实际：{row.destination_pending_key!r}"
    )
    assert not str(row.canonical_destination_id or "").startswith(
        capability_module.LEGACY_PENDING_PREFIX
    )
    assert not capability_module._normalise(RAW_COUNTY) in str(row.canonical_destination_id), (
        f"期望：身份里没有查询文本；实际：{row.canonical_destination_id!r}"
    )
    read_back = client.get(f"{HYDRATIONS}/{body['operation_id']}").json()
    assert read_back["canonical_destination_id"] == COUNTY_CANONICAL, read_back


def test_g8_the_seam_is_read_per_call_and_defaults_off(monkeypatch) -> None:
    """默认关，且按调用读：一次导入期的常量会把整条套件带到网上。"""

    monkeypatch.delenv("CITYNEXUS_ANYWHERE_RESOLVER", raising=False)
    assert capability_module.anywhere_resolver_name() == "off"
    monkeypatch.setenv("CITYNEXUS_ANYWHERE_RESOLVER", "PHOTON ")
    assert capability_module.anywhere_resolver_name() == "photon", "大小写/空白要折，但不许改语义"
    monkeypatch.setenv("CITYNEXUS_ANYWHERE_RESOLVER", "photonnn")
    assert capability_module.anywhere_resolver_name() == "photonnn"
    assert capability_module.anywhere_resolver_attempted() is False, (
        "拼错的 seam 名不得被当成'开了'"
    )
    assert "photon" in capability_module.RESOLVER_SEAMS, capability_module.RESOLVER_SEAMS
    assert "off" in capability_module.RESOLVER_SEAMS


def test_g9_provider_leg_never_writes_a_digest_or_a_placeholder(seeded, monkeypatch) -> None:
    """把原文哈希成身份是今晚第一次被拒的做法；provider 腿也不许换个马甲再来一次。"""

    import re

    _enable(monkeypatch)
    _answer(monkeypatch, raise_with=httpx.ReadTimeout("read timed out"))
    body = _capability(RAW_COUNTY)
    identity = str(body["canonical_destination_id"] or "")
    assert identity == "", f"期望身份为空；实际：{identity!r}"
    assert not re.search(r"[0-9a-f]{8,}", identity), identity
    for key in ("pending_destination_label", "resolver_query_normalized"):
        assert re.search(r"[0-9a-f]{16,}", str(body.get(key) or "")) is None, (
            f"{key} 里出现了摘要：{body.get(key)!r}"
        )
    identity_fields = {
        key: value
        for key, value in body.items()
        if key.endswith("destination_id") or key in {"canonical_destination_id", "city_code"}
    }
    assert set(identity_fields.values()) <= {None}, (
        f"期望：传输失败时任何身份字段都是空的；实际：{identity_fields}"
    )
    assert body["retryable"] is True, body["retryable"]
