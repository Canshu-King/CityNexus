"""一枚地图线索能不能只靠服务器交回的指针走到照片——链路 spec，全程离线。

Issue #42 的复核令要的下一格是「精确来源身份补齐 → 有效转场冻结 → 本人确认」。这一支先量链路里前两跳
的形状，用真路由、真鉴权、真 `place_is_in_journey`，provider 那一侧只留记录用的夹具（所以答案必须写
`TEST_FIXTURE`，不许读成真照片）：

* 走通的那一格：线索 `photon:node:9001` 命中一支写者存的裸形制行，身份读交回 `media_path`，客户端只把
  那串原样再按一次就拿到媒体——中间没有任何一处由客户端编 URL、也没有一处按名字找地方；
* 歧义那一格断在身份门上：同一枚身份两种列形制各有一行，`LEAD_AMBIGUOUS`，且答复里不给 `media_path`；
* 不在范围那一格也断在身份门上：`PLACE_NOT_IN_JOURNEY`；手搓那枚地点 id 去按媒体读，仍然 404——
  门不是靠"客户端不知道路径"实现的；
* 无座位的人两跳都 403。

token 密钥每次现生成，不写进树、不进日志（同 `test_qoder_place_source_lead_r1.py` 的做法）。
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import place_media_routes, place_source_lead, traveler_principal
from app.core.config import settings
from app.db.models import Base, Journey, JourneyCheckin, Place, Traveler
from app.db.session import get_session

IDENTITY_PATH = "/api/v1/journeys/{}/place-identity"
SECRET = uuid.uuid4().hex + uuid.uuid4().hex
#: 第二跳交给 provider 的入参，逐枚留痕，断的是「行自己的两列」而不是线索文本。
HANDED: list[dict] = []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_row(session, *, provider_key: str, external_id: str, name: str, city_code: str) -> str:
    """按某支 shipped 写者的形制落一行：id 用 `minted_place_id` 现算，绝不手写。"""
    ident = place_source_lead.minted_place_id(provider_key, external_id)
    session.add(Place(id=ident, provider_key=provider_key, external_id=external_id,
                      city_code=city_code, name=name, category="poi", latitude=25.7,
                      longitude=116.75, opening_hours_json="{}", tags_json="[]",
                      metadata_json="{}", updated_at=_now()))
    return ident


def _stamp(session, journey_id: str, place_id: str) -> None:
    session.add(JourneyCheckin(id=str(uuid.uuid4()), journey_id=journey_id, activity_id=None,
                               place_id=place_id, target_kind="place", target_key=place_id,
                               stamped_at=_now()))


class _FixtureResult:
    """provider 边界的替身：只记录被问了什么，并如实回 TEST_FIXTURE。"""

    def __init__(self, place_id: str):
        self.place_id = place_id

    def as_payload(self):
        return {"place_id": self.place_id, "status": "TEST_FIXTURE", "reason_code": "TEST_FIXTURE",
                "media": None, "provider_readings": [], "attempted": False}


@pytest.fixture()
def seeded():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    ids = {"owner": str(uuid.uuid4()), "outsider": str(uuid.uuid4()), "journey": str(uuid.uuid4())}
    with factory() as session:
        for key in ("owner", "outsider"):
            session.add(Traveler(id=ids[key], display_name=key, email=None, locale="zh-CN",
                                 timezone="Asia/Shanghai", created_at=_now(), updated_at=_now()))
        session.add(Journey(id=ids["journey"], traveler_id=ids["owner"], title="连城",
                            city_code="350825", timezone="Asia/Shanghai", start_at=_now(),
                            end_at=_now(), budget_currency="CNY", budget_amount_minor=1,
                            status="ACTIVE", created_at=_now(), updated_at=_now()))
        # 一·photon.py 那支写者的裸形制行，本趟持有
        ids["bare"] = _seed_row(session, provider_key="photon", external_id="node:9001",
                                name="冠豸山", city_code="连城县")
        _stamp(session, ids["journey"], ids["bare"])
        # 二·同一枚身份两种形制各一行，且都被本趟持有：范围救不了它，只能拒
        ids["whole"] = _seed_row(session, provider_key="amap", external_id="nominatim:node/9002",
                                 name="外滩源", city_code="上海市")
        ids["half"] = _seed_row(session, provider_key="nominatim", external_id="node/9002",
                                name="外滩源", city_code="厦门市")
        _stamp(session, ids["journey"], ids["whole"])
        _stamp(session, ids["journey"], ids["half"])
        # 三·库里在世、这趟没持有
        ids["unheld"] = _seed_row(session, provider_key="photon", external_id="node:9003",
                                  name="别处的一站", city_code="北京市")
        session.commit()
    return SimpleNamespace(factory=factory, ids=ids)


def _app(seeded, monkeypatch):
    monkeypatch.setattr(traveler_principal, "settings",
                        replace(settings, traveler_auth_secret=SECRET))
    from app import main as main_module

    app = FastAPI()
    app.include_router(place_media_routes.router)
    app.add_exception_handler(StarletteHTTPException, main_module.http_error)

    def override_session():
        with seeded.factory() as inner:
            yield inner

    async def _spy(**kwargs):
        HANDED.append(dict(kwargs))
        return _FixtureResult(str(kwargs.get("place_id")))

    monkeypatch.setattr(place_media_routes.place_media, "collect_place_media", _spy)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[place_media_routes._media_client] = (
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={}))))
    return TestClient(app)


def _header(traveler_id: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(traveler_id)}


def _identity(client, seeded, lead, traveler_id=None):
    url = IDENTITY_PATH.format(seeded.ids["journey"]) + "?lead=" + lead
    return client.get(url, headers=_header(traveler_id or seeded.ids["owner"]))


def test_a_bare_form_lead_walks_the_chain_on_pointers_the_server_handed(seeded, monkeypatch):
    """身份读交回的 media_path 原样再按一次就到底，中间没有一处由客户端拼。"""
    client = _app(seeded, monkeypatch)
    HANDED.clear()
    ok = _identity(client, seeded, "photon:node:9001")
    assert ok.status_code == 200, ok.text
    first = ok.json()
    assert first["place_id"] == seeded.ids["bare"]
    assert first["matched_by"] == "provider_key_and_object_id", first
    media_path = first["media_path"]
    assert media_path, first
    assert "冠豸山" not in media_path, "the path carries the id, never the name"
    second = client.get(media_path, headers=_header(seeded.ids["owner"]))
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["status"] == "TEST_FIXTURE", body
    assert body["place_id"] == first["place_id"], (body, first)
    handed = HANDED[-1]
    assert handed["provider_object_id"] == "node:9001", handed
    assert handed["place_id"] == seeded.ids["bare"], handed


def test_the_ambiguity_stops_at_the_identity_door_and_hands_no_path(seeded, monkeypatch):
    """两种形制各一行时，答复不给下一跳的指针——歧义不该被包装成一条可按的路。"""
    client = _app(seeded, monkeypatch)
    refused = _identity(client, seeded, "nominatim:node/9002")
    assert refused.status_code == 404, refused.text
    error = refused.json()["error"]
    assert error["reason_code"] == place_source_lead.REASON_AMBIGUOUS, error
    assert "media_path" not in refused.text


def test_a_place_this_journey_does_not_hold_stops_at_both_doors(seeded, monkeypatch):
    """身份门断一次；手搓那枚 id 去按媒体读，门照样断——范围不是靠客户端不知道路径实现的。"""
    client = _app(seeded, monkeypatch)
    refused = _identity(client, seeded, "photon:node:9003")
    assert refused.status_code == 404, refused.text
    assert refused.json()["error"]["reason_code"] == place_source_lead.REASON_NOT_IN_JOURNEY

    sneaky = place_media_routes.MEDIA_PATH.format(
        journey_id=seeded.ids["journey"], place_id=seeded.ids["unheld"])
    bypass = client.get(sneaky, headers=_header(seeded.ids["owner"]))
    assert bypass.status_code == 404, bypass.text


def test_a_stranger_without_a_seat_is_refused_on_both_hops(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    outside = _identity(client, seeded, "photon:node:9001", seeded.ids["outsider"])
    assert outside.status_code == 403, outside.text
    path = place_media_routes.media_path_for(seeded.ids["journey"], seeded.ids["bare"])
    media_outside = client.get(path, headers=_header(seeded.ids["outsider"]))
    assert media_outside.status_code == 403, media_outside.text
