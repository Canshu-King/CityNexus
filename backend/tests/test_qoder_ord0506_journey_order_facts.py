"""ORD-0506 片一 -- 行程列表要按真事实排，服务端得先把真事实给出来。

量到的现状（现尖 `514b397f96f3b5165b24865f4a544ab6f8020084`）：`journeys` 表本来就有 `created_at`
（`backend/app/db/models.py` 里 `class Journey` 的 `created_at: Mapped[str]`），但读模型 `Journey`
（`backend/app/schemas.py:250` 附近）与 `journey_schema()`（`backend/app/services.py:435`）都不带它，
所以 `GET /api/v1/journeys` 的应答里没有任何"这行是什么时候建的"。一屏要在这枚事实上排序，只能自己编
一枚时间——那正是这一单不许有的形状。本片只把事实搬上读门（契约与生成物跟着复现），排序开关与两枚反例
臂在屏上那一层，另片交。

每枚臂断的都是**状态**，不是词：

1. 读门每一行都答 `created_at`，并且它等于本进程写进 `journeys.created_at` 的那一枚——不是格式化出来的
   新值，也不是 `updated_at` 的复读；
2. 「创建序」与「出发序」在同一批行上是两枚不同的事实：臂自己造一批 `start_at` 顺序与创建顺序相反的
   行程，再断两种序真的不一样。若哪天有人把 `created_at` 写成 `start_at` 的别名，这一枚立刻红；
3. 契约要求它、生成物带着它：`components.schemas.Journey.required` 含 `created_at`，
   `frontend/src/generated/api.ts` 的 `Journey` 接口里有 `created_at: string;`——生成物由
   `openapi-typescript` 从契约复现，不是手写。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)
ROOT = Path(__file__).resolve().parents[2]
TZ = timezone(timedelta(hours=8))


def _store() -> sqlite3.Connection:
    from conftest import RESOLVED_TEST_DATABASE

    path = Path(RESOLVED_TEST_DATABASE.replace("sqlite:///", "", 1)).expanduser().resolve()
    return sqlite3.connect(path)


def _traveller(label: str) -> str:
    answer = client.post(
        "/api/v1/travelers",
        json={"display_name": f"ORD0506 {label}", "timezone": "Asia/Shanghai", "locale": "zh-CN"},
    )
    assert answer.status_code == 201, answer.text
    return answer.json()["id"]


def _journey(owner: str, title: str, start: datetime) -> dict:
    end = start + timedelta(days=2)
    answer = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": owner,
            "title": title,
            "city_code": "CN-XIAMEN",
            "timezone": "Asia/Shanghai",
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "budget": {"amount_minor": 300000, "currency": "CNY"},
        },
    )
    assert answer.status_code == 201, answer.text
    return answer.json()


def _listed() -> list[dict]:
    answer = client.get("/api/v1/journeys")
    assert answer.status_code == 200, answer.text
    rows = answer.json()
    assert isinstance(rows, list) and rows, f"读门没有分母可读：{rows!r}"
    return rows


def test_the_list_door_answers_created_at_for_every_row() -> None:
    """每一行都带着创建时间，且那确实是库里那一列的值。"""
    owner = _traveller("list")
    made = _journey(owner, "ORD0506 一枚", datetime(2027, 3, 1, 9, 0, tzinfo=TZ))
    rows = {row["id"]: row for row in _listed()}
    assert made["id"] in rows, sorted(rows)[:5]
    row = rows[made["id"]]
    assert "created_at" in row, sorted(row)
    with _store() as connection:
        stored = connection.execute(
            "select created_at, updated_at, start_at from journeys where id = ?", (made["id"],)
        ).fetchone()
    assert stored is not None, made["id"]
    # 比的是同一枚时刻，不是同一种写法：应答走的是 `Z` 后缀，库里存的是 `+00:00`。
    assert datetime.fromisoformat(row["created_at"]) == datetime.fromisoformat(stored[0]), (row, stored)
    # 它是独立的一枚事实：既不等于出发时间，也不被臂用 updated_at 顶替（两者在本用例里必须可分）。
    assert row["created_at"] != row["start_at"], row


def test_creation_order_and_departure_order_are_different_facts() -> None:
    """同一批行上，创建序与出发序必须能不同——否则"按时间排"与"按创建排"是同一句话。"""
    owner = _traveller("orders")
    # 创建顺序：先建出发最晚的，再建出发最早的。
    first = _journey(owner, "ORD0506 出发最晚", datetime(2028, 1, 2, 9, 0, tzinfo=TZ))
    second = _journey(owner, "ORD0506 出发最早", datetime(2026, 1, 3, 9, 0, tzinfo=TZ))
    rows = {row["id"]: row for row in _listed()}
    mine = [rows[first["id"]], rows[second["id"]]]
    by_creation = sorted(mine, key=lambda r: r["created_at"])
    by_departure = sorted(mine, key=lambda r: r["start_at"])
    assert [r["id"] for r in by_creation] != [r["id"] for r in by_departure], (
        "两枚序在同一批行上完全同序，臂就没有对照：",
        [(r["title"], r["created_at"], r["start_at"]) for r in mine],
    )
    assert by_creation[0]["title"] == "ORD0506 出发最晚", by_creation
    assert by_departure[0]["title"] == "ORD0506 出发最早", by_departure


def test_the_recycle_bin_row_carries_the_same_created_at_as_the_list() -> None:
    """同一行经过两扇读门，创建时间不许各说一套。"""
    owner = _traveller("bin")
    made = _journey(owner, "ORD0506 丢弃的那趟", datetime(2027, 6, 1, 9, 0, tzinfo=TZ))
    listed = next(r for r in _listed() if r["id"] == made["id"])
    dropped = client.delete(f"/api/v1/journeys/{made['id']}")
    assert dropped.status_code in (200, 204), dropped.text  # 这一扇答 204 No Content
    bin_rows = client.get("/api/v1/recycle-bin/journeys").json()
    row = next((r for r in bin_rows if r["id"] == made["id"]), None)
    assert row is not None, bin_rows
    assert row["created_at"] == listed["created_at"], (row["created_at"], listed["created_at"])
    assert row["deleted_at"], row


def test_the_contract_requires_the_field_and_the_artifact_carries_it() -> None:
    """契约要求它，生成物带着它——生成物是 `openapi-typescript` 复现出来的，不是手写的。"""
    spec = yaml.safe_load((ROOT / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
    journey = spec["components"]["schemas"]["Journey"]
    assert "created_at" in journey["required"], journey["required"]
    assert journey["properties"]["created_at"]["format"] == "date-time", journey["properties"]
    text = (ROOT / "frontend" / "src" / "generated" / "api.ts").read_text(encoding="utf-8")
    block = text[text.index("Journey:"):]
    head = block[: block.index("created_at") + 400]
    assert "created_at: string;" in head, json.dumps(head[-300:])
