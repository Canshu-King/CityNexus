"""Issue #33 第九笔 -- 一趟行程的名字，从写进去到读出来到导出去，都是同一串字。

壳以前自己拼 "<城市> · journey" 当行程名，所以一个用中文界面的人，名下列表上挂着的是
「北京 · journey」而 Today 的块头写的是「北京之旅」。改法在前端（名字改由字典生成），
但那一改成立的前提在服务器上：**这一趟存的名字，必须就是给出去的那串字**，不转写、不截断、
不因为不是拉丁字母就换一个名字。这一支钉的就是这个前提，外加导出那一格：日历文件的头是
ASCII 的，中文名只能以百分号编码的形式出去，而它解回来必须还是那个人写的名字。

- 建：`POST /api/v1/journeys`（`backend/app/main.py` 的 `create_journey`）
- 读：`GET /api/v1/journeys`（同一台，带这枚会话）
- 出：`app.calendar_export.content_disposition`（RFC 6266 / RFC 5987 那一对）
"""

from __future__ import annotations

from dataclasses import replace
from urllib.parse import unquote
from uuid import uuid4

from fastapi.testclient import TestClient

from app import traveler_principal
from app.calendar_export import content_disposition
from app.core.config import settings
from app.db.session import ensure_schema
from app.main import app

client = TestClient(app)
ensure_schema()

LONG_SECRET = uuid4().hex + uuid4().hex
CJK_TITLE = "天津之旅"
LATIN_TITLE = "Trip to Tianjin"


def _signed_traveler(monkeypatch) -> tuple[str, str]:
    monkeypatch.setattr(
        traveler_principal, "settings", replace(settings, traveler_auth_secret=LONG_SECRET)
    )
    answer = client.post(
        "/api/v1/travelers",
        json={"display_name": "名字呢", "locale": "zh-CN", "timezone": "Asia/Shanghai"},
    )
    assert answer.status_code == 201, answer.text
    body = answer.json()
    assert body["session_state"] == "SIGNED", body
    return body["id"], body["access_token"]


def _create_journey(traveler_id: str, token: str, title: str) -> dict:
    answer = client.post(
        "/api/v1/journeys",
        headers={"Authorization": "Bearer " + token},
        json={
            "traveler_id": traveler_id,
            "title": title,
            "city_code": "CN-TIANJIN",
            "timezone": "Asia/Shanghai",
            "start_at": "2026-11-01T09:00:00+08:00",
            "end_at": "2026-11-03T18:00:00+08:00",
            "budget": {"amount_minor": 120000, "currency": "CNY"},
            "stay_budget": {"amount_minor": 60000, "currency": "CNY"},
            "party_size": 2,
            "occupancy": {"adults": 2, "rooms": 1},
        },
    )
    assert answer.status_code == 201, answer.text
    return answer.json()


def test_a_trip_named_in_chinese_is_written_back_in_chinese(monkeypatch) -> None:
    traveler_id, token = _signed_traveler(monkeypatch)
    created = _create_journey(traveler_id, token, CJK_TITLE)
    assert created["title"] == CJK_TITLE, created
    assert "journey" not in created["title"].lower(), (
        "存进去的中文名被换成了带英文后缀的那一种：" + repr(created["title"])
    )


def test_the_list_door_repeats_the_words_it_was_given_on_both_names(monkeypatch) -> None:
    traveler_id, token = _signed_traveler(monkeypatch)
    cjk = _create_journey(traveler_id, token, CJK_TITLE)
    latin = _create_journey(traveler_id, token, LATIN_TITLE)
    answer = client.get(
        "/api/v1/journeys", headers={"Authorization": "Bearer " + token}
    )
    assert answer.status_code == 200, answer.text
    rows = {row["id"]: row for row in answer.json()}
    assert rows[cjk["id"]]["title"] == CJK_TITLE, rows.get(cjk["id"])
    assert rows[latin["id"]]["title"] == LATIN_TITLE, rows.get(latin["id"])


def test_the_list_door_carries_the_instant_a_row_is_drawn_from(monkeypatch) -> None:
    """Pass 10 put the trip's own start instant on its row in 我的行程.

    That is only honest if the list door sends the instant the create door was given -- not a
    re-based one, not the device's guess.  The row formats whatever arrives here, so this is the
    far end of that line on screen.
    """
    traveler_id, token = _signed_traveler(monkeypatch)
    created = _create_journey(traveler_id, token, CJK_TITLE)
    answer = client.get(
        "/api/v1/journeys", headers={"Authorization": "Bearer " + token}
    )
    assert answer.status_code == 200, answer.text
    rows = {row["id"]: row for row in answer.json()}
    row = rows[created["id"]]
    assert row["start_at"] == created["start_at"], (row, created)
    assert row["start_at"].startswith("2026-11-01"), row["start_at"]


def test_the_calendar_header_carries_the_name_without_inventing_an_ascii_one() -> None:
    header = content_disposition(CJK_TITLE, "journey-under-test")
    assert header.isascii(), "HTTP 头不能带非 ASCII 字节：" + repr(header)
    assert 'filename="calendar.ics"' in header, header
    marker = "filename*=UTF-8''"
    assert marker in header, header
    encoded = header.split(marker, 1)[1].split(";", 1)[0]
    name = unquote(encoded, encoding="utf-8")
    # 这一格的名字由两部分组成：人写的那串字在前，服务器的 durable id 在后。
    # 加 id 是这一扇门自己的决定，理由写在 `_ext_value` 的docstring 里：两趟同名的行程
    # 不能到手里变成同一个文件。这里要钉的是前半句——人的名字排在第一位，一个字没改。
    journey_id = "journey-under-test"
    assert name == CJK_TITLE + "--" + journey_id + ".ics", name
    assert name.startswith(CJK_TITLE), name
