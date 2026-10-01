"""ORD-0513 -- 收藏这一族的三句拒绝，把条件说给人听，把身份留在 `details` 里。

量出来的现状（现尖 `514b397f96f3b5165b24865f4a544ab6f8020084`，`backend/app/main.py:3532`、`:3539`、
`:3568` 三枚 f-string）：三句正文都把裸 id 印在句子里，例如号令者在 HTTP 层量到的

    Place place-old-town is already in collection folder c84de303-879f-4dc5-8bda-313a4a4cb395

同一份事实本来就在 `error.details` 里给全（`folder_id`、`place_id`、`existing_item_id`、
`existing_added_at`），所以那句 uuid 不是必需的。屏上那一格由车道在浏览器里量（zh-CN/en 两档、
390x844 与桌面两形，读数 `n2_0513_run_tip2.json`）：UI 真撞到了 `http_status=409`
`reason_code=PLACE_ALREADY_IN_COLLECTION`，而屏上 0 枚 uuid 形状、0 处上游原文——所以这一族的缺陷在
正文层，不在渲染层；改正文不动任何前端判据，也不动 `reason_code`。

每枚臂断的是**状态**，不是词：

* 三枚 HTTP 状态与三枚 `reason_code` 一字不改；
* 正文里没有 uuid 形状，也没有**本次调用自己送出去的那枚 id 字面**——这条让「空正文」或「正文里
  本来就没有这枚 id」都蒙不过去，因为同一枚 id 必须仍然在 `details` 里读得到：事实是搬走了，不是丢了；
* 反件就在臂自己身上：谁把 id 塞回正文，这一族立刻红。

夹具形制照 `test_qoder_ord0444_collections.py`：旅行者与地点走产品自己的模型写入，不碰
`/api/v1/demo/reset`，库是 `backend/tests/conftest.py` 每进程新生成的临时文件。
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.models import Place, Traveler
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
UUID_SHAPE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _traveller(label: str) -> str:
    identifier = f"ord0513-traveller-{label}"
    now = _now()
    with SessionLocal() as session:
        if session.get(Traveler, identifier) is None:
            session.add(
                Traveler(
                    id=identifier,
                    display_name=f"ORD0513 探针 {label}",
                    email=None,
                    locale="zh-CN",
                    timezone="Asia/Shanghai",
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()
    return identifier


def _place(label: str) -> str:
    identifier = f"ord0513-{label}"
    with SessionLocal() as session:
        if session.get(Place, identifier) is None:
            session.add(
                Place(
                    id=identifier,
                    provider_key="ord0513-probe",
                    external_id=identifier,
                    city_code="CNX-DEMO",
                    name=f"拒绝句探针 {label}",
                    category="museum",
                    latitude=24.4792,
                    longitude=118.3973,
                    opening_hours_json=json.dumps({"open": "09:00", "close": "17:00"}),
                    tags_json=json.dumps(["ord0513"]),
                    metadata_json=json.dumps({"cost_minor": 0, "duration_min": 60}),
                    updated_at=_now(),
                )
            )
            session.commit()
    return identifier


def _reason(body: object) -> str | None:
    error = (body or {}).get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and isinstance(error.get("reason_code"), str):
        return error["reason_code"]
    if isinstance(body, dict) and isinstance(body.get("reason_code"), str):
        return body["reason_code"]
    return None


def _message(body: object) -> str:
    error = (body or {}).get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"]
    if isinstance(body, dict) and isinstance(body.get("detail"), str):
        return body["detail"]
    return ""


def _details(body: object) -> dict:
    error = (body or {}).get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and isinstance(error.get("details"), dict):
        return error["details"]
    if isinstance(body, dict) and isinstance(body.get("details"), dict):
        return body["details"]
    return {}


def _judged(response, *, status: int, reason_code: str, sent_ids: list[str]):
    """One refusal, judged on state: the status and the name are the contract, the sentence is prose.

    `sent_ids` are identifiers THIS call actually put on the wire, so "no bare token in the message"
    is measured against values the arm knows are in play -- an empty body or a body that never saw
    these ids cannot pass, because the same ids must still be readable out of `details`.
    """
    assert response.status_code == status, response.text
    body = response.json()
    assert _reason(body) == reason_code, body
    message = _message(body)
    assert message.strip(), f"{reason_code} 的正文是空的，人就没有可读的条件句：{body!r}"
    assert not UUID_SHAPE.search(message), f"{reason_code} 的正文里还有 uuid 形状：{message!r}"
    details = json.dumps(_details(body), ensure_ascii=False, default=str)
    for identifier in sent_ids:
        assert identifier not in message, f"{reason_code} 把 {identifier!r} 印给了人：{message!r}"
        assert identifier in details, (
            f"{reason_code} 从正文拿走身份时也没留在 details 里：{_details(body)!r}"
        )
    return body


@pytest.fixture()
def stage():
    owner = _traveller("owner")
    created = client.post("/api/v1/collections", json={"name": "ORD0513 架子", "owner_traveler_id": owner})
    assert created.status_code == 201, created.text
    return {"owner": owner, "shelf_id": created.json()["id"], "place_id": _place("known")}


def test_unknown_shelf_says_the_condition_and_not_the_shelf_id(stage):
    """`backend/app/main.py` COLLECTION_FOLDER_NOT_FOUND：架子身份只在 details。"""
    missing = str(uuid4())
    _judged(
        client.post(f"/api/v1/collections/{missing}/items", json={"place_id": stage["place_id"]}),
        status=404,
        reason_code="COLLECTION_FOLDER_NOT_FOUND",
        sent_ids=[missing],
    )


def test_unknown_place_says_the_condition_and_not_the_place_id(stage):
    """PLACE_NOT_FOUND：地点身份只在 details。"""
    fake = "ord0513-never-a-place"
    _judged(
        client.post(f"/api/v1/collections/{stage['shelf_id']}/items", json={"place_id": fake}),
        status=404,
        reason_code="PLACE_NOT_FOUND",
        sent_ids=[fake],
    )


def test_duplicate_keeps_the_name_and_loses_both_ids_from_the_sentence(stage):
    """PLACE_ALREADY_IN_COLLECTION：这一句原来一枚里印了两枚 id。"""
    first = client.post(
        f"/api/v1/collections/{stage['shelf_id']}/items", json={"place_id": stage["place_id"]}
    )
    assert first.status_code == 201, first.text
    body = _judged(
        client.post(
            f"/api/v1/collections/{stage['shelf_id']}/items", json={"place_id": stage["place_id"]}
        ),
        status=409,
        reason_code="PLACE_ALREADY_IN_COLLECTION",
        sent_ids=[stage["shelf_id"], stage["place_id"]],
    )
    # 号令者量的那四个键一枚都不能少：搬走的是措辞，不是事实。
    assert set(_details(body)) == {
        "folder_id",
        "place_id",
        "existing_item_id",
        "existing_added_at",
    }, _details(body)


def test_the_family_has_no_other_bare_token_sentence_left():
    """这一族的收尾：源文里那三枚 f-string 之外，收藏这一段不再有任何把 id 印进正文的句子。

    枚举行号在现尖上是 `backend/app/main.py:3532`、`:3539`、`:3568`（号令者早先引的 `:3461` 已随两笔
    落地漂移，所以这里按名字扫，不按行号扫）。
    """
    # `inspect.getsource(app)` is NOT this repository's file: `app` is a FastAPI *instance*, so the
    # lookup lands on the library's class and the scan reads someone else's source. The arm reads the
    # module file it is supposed to be guarding.
    import app.main as main_module

    source = Path(main_module.__file__).read_text(encoding="utf-8")
    start = source.index("def add_collection_item")
    window = source[start:]
    cut = window.find("\n@")
    window = window[: cut if cut > 0 else len(window)]
    offenders = [
        line.strip()
        for line in window.splitlines()
        if re.search(r'f"[^"]*\{(folder_id|payload\.place_id)\}', line)
    ]
    assert not offenders, f"收藏这一族还有把 id 印进正文的句子：{offenders}"
