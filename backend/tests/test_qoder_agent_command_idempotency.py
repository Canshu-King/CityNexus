"""ORD-0253 后端半件 · `POST /api/v1/journeys/{id}/agent/commands` 的 `Idempotency-Key` 常驻门。

仲裁验收形状（逐字实现，不自己换词）：
  1) 同端点 + 同 `Idempotency-Key` + 同归一化命令/上下文 ⇒ 同一个持久逻辑 mission / **1 行**
  2) 同 key + 不匹配的归一化请求/上下文 ⇒ **fail closed**，用现有 idempotency mismatch 语义，绝不静默 alias
  3) 不同 key ⇒ 保持独立

每道门只问它自己那一条问题（一臂红三条 ≠ 三份证据）：`owner` 标在名字与断言消息里，
反向突变必须只打红它那一格才算数。
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.db.models import IdempotencyKey, JourneyMission
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)
TZ = timezone(timedelta(hours=8))

# 两句都不会被识别成 DISRUPTION_REPORT（不建 Event），所以比较的是"同一份语义请求"而不是副作用巧合
CMD_A = "我护照丢了，请告诉我怎么办。"
CMD_B = "帮我把今晚的安排换成室内活动，节奏慢一点。"

#: 离线前提：带了真 key 会走真 agent，本门就变成网络依赖。skip 之外再在每格里 assert，
#: 免得有人把 skip 条件改掉之后，门在联网机器上悄悄换了形状。
OFFLINE = pytest.mark.skipif(bool(settings.ai_api_key), reason="本门要求离线判定：ai_api_key 必须为空")


def _setup() -> str:
    """开一只自己的 journey（不碰 demo/reset，不共享别人的行）。"""
    traveler = client.post(
        "/api/v1/travelers", json={"display_name": "ord0253", "timezone": "Asia/Shanghai"}
    )
    assert traveler.status_code == 201, traveler.text
    start = datetime(2026, 9, 26, 8, 0, tzinfo=TZ)
    journey = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": traveler.json()["id"],
            "title": "ord0253",
            "city_code": "CNX-DEMO",
            "timezone": "Asia/Shanghai",
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(days=1, hours=8)).isoformat(),
            "budget": {"amount_minor": 20000, "currency": "CNY"},
            "planning_mode": "balanced",
        },
    )
    assert journey.status_code == 201, journey.text
    return str(journey.json()["id"])


def _mission_ids(journey_id: str) -> list[str]:
    with SessionLocal() as session:
        return sorted(
            session.scalars(
                select(JourneyMission.id).where(JourneyMission.journey_id == journey_id)
            ).all()
        )


def _post(journey_id: str, command: str, key: str | None = None,
          autonomy: str = "PLAN_ONLY"):
    headers = {"Idempotency-Key": key} if key is not None else {}
    return client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        json={"command": command, "requested_autonomy": autonomy},
        headers=headers,
    )


def _assert_offline_determinism(response) -> None:
    """这格的读数只在"外部 AI 关着"时成立；开着就不算量到。"""
    assert not settings.ai_api_key, "SETUP：本门必须离线判定（ai_api_key 非空时形状会变）"
    assert response.status_code == 200, response.text
    assert response.json().get("mission"), f"没有 mission 载荷就没有可比较的逻辑作业：{response.text[:200]}"


# -------------------------------------------------------------------------------- 验收 1


@OFFLINE
def test_same_key_same_request_replays_the_one_persisted_mission() -> None:
    """owner=验收①：同 key + 同语义请求 ⇒ 同一个 mission、库里 **1 行**。"""
    jid = _setup()
    key = f"ord0253-replay-{jid}"
    first = _post(jid, CMD_A, key)
    _assert_offline_determinism(first)
    second = _post(jid, CMD_A, key)
    _assert_offline_determinism(second)

    assert second.json()["mission"]["id"] == first.json()["mission"]["id"], (
        "验收①：同 key 第二发必须回同一枚逻辑 mission，"
        f"拿到 {first.json()['mission']['id']} vs {second.json()['mission']['id']}"
    )
    ids = _mission_ids(jid)
    assert len(ids) == 1, f"验收①：两次激活只能持久 1 行 journey_missions，实际 {len(ids)} 行 {ids}"


# -------------------------------------------------------------------------------- 验收 2


@OFFLINE
def test_same_key_with_a_different_command_fails_closed_never_aliases() -> None:
    """owner=验收②-a：同 key 换命令 ⇒ 现有 mismatch 语义 fail closed，且不产生新行。"""
    jid = _setup()
    key = f"ord0253-mismatch-{jid}"
    first = _post(jid, CMD_A, key)
    _assert_offline_determinism(first)
    before = _mission_ids(jid)

    conflict = _post(jid, CMD_B, key)
    assert conflict.status_code == 409, (
        f"验收②：同 key 不同命令必须 409 拒掉，实际 {conflict.status_code} {conflict.text[:180]}"
    )
    detail = str(conflict.json())
    assert "idempotency" in detail.lower() or "different request" in detail.lower(), (
        f"验收②：要沿用现有 mismatch 语义那句话，实际回的是 {detail[:200]}"
    )
    assert _mission_ids(jid) == before, "验收②：拒收不能先把第二枚作业写进库里再报错"


@OFFLINE
def test_same_key_with_a_different_autonomy_fails_closed_too() -> None:
    """owner=验收②-b：归一化请求里 autonomy 也是语义的一部分，换它同样要红。"""
    jid = _setup()
    key = f"ord0253-autonomy-{jid}"
    assert _post(jid, CMD_A, key, autonomy="PLAN_ONLY").status_code == 200
    before = _mission_ids(jid)
    conflict = _post(jid, CMD_A, key, autonomy="EXECUTE_WITHIN_BOUNDS")
    assert conflict.status_code == 409, (
        f"验收②：换 requested_autonomy 就是另一个意图，实际 {conflict.status_code}"
    )
    assert _mission_ids(jid) == before


@OFFLINE
def test_same_key_on_another_journey_fails_closed_not_silently_reused() -> None:
    """owner=验收②-c：key 按 operation 作用域，但跨 journey 同 key 也是另一个意图 ⇒ 409。

    这是"复用 replan/accept 词汇"的必然结果（那边的 scoped key 也不带 journey），
    写成门是为了让它成为一个**声明过的语义**，而不是谁哪天顺手改成 alias。
    """
    jid_a, jid_b = _setup(), _setup()
    key = f"ord0253-cross-journey-{jid_a}"
    assert _post(jid_a, CMD_A, key).status_code == 200
    conflict = _post(jid_b, CMD_A, key)
    assert conflict.status_code == 409, (
        f"验收②：同一把 key 换 journey 不能静默返回别人的 mission，实际 {conflict.status_code}"
    )
    assert len(_mission_ids(jid_b)) == 0, "验收②：被拒的那一发不该在另一条 journey 上留下作业"


# -------------------------------------------------------------------------------- 验收 3


@OFFLINE
def test_different_keys_stay_independent() -> None:
    """owner=验收③：不同 key ⇒ 两枚独立作业（不许过度合并）。"""
    jid = _setup()
    one = _post(jid, CMD_A, f"ord0253-ind-1-{jid}")
    two = _post(jid, CMD_A, f"ord0253-ind-2-{jid}")
    _assert_offline_determinism(one)
    _assert_offline_determinism(two)
    assert one.json()["mission"]["id"] != two.json()["mission"]["id"], (
        "验收③：不同 key 必须各自成立，拿到同一个 mission id 就是过度合并"
    )
    assert len(_mission_ids(jid)) == 2, "验收③：不同 key 应当持久 2 行"


# ------------------------------------------------------------------ 持久性与既有语义


@OFFLINE
def test_the_receipt_is_a_durable_scoped_row_not_an_in_memory_map() -> None:
    """owner=持久化：收据落在 `idempotency_keys`，键带 operation 前缀，不同意图摘要不同。"""
    jid = _setup()
    key = f"ord0253-durable-{jid}"
    assert _post(jid, CMD_A, key).status_code == 200
    with SessionLocal() as session:
        rows = session.scalars(
            select(IdempotencyKey).where(IdempotencyKey.key == f"agent.command:{key}")
        ).all()
    assert len(rows) == 1, f"持久收据应恰好 1 行，实际 {len(rows)}"
    row = rows[0]
    assert row.operation == "agent.command", row.operation
    assert row.request_hash and row.response_json, "空摘要/空响应意味着下一次无从比对"
    assert str(jid) in row.request_hash and "requested_autonomy" in row.request_hash, (
        f"签名没把语义请求纳进来就没法判'不同意图'：{row.request_hash[:120]}"
    )


@OFFLINE
def test_headerless_call_keeps_todays_shape() -> None:
    """owner=向后兼容：不带 key 时行为与形状不变（这条红 ⇒ 我把默认路径改了形）。"""
    jid = _setup()
    keyed = _post(jid, CMD_A, f"ord0253-shape-{jid}")
    _assert_offline_determinism(keyed)
    plain = _post(jid, CMD_A, None)
    _assert_offline_determinism(plain)
    assert set(plain.json()) == set(keyed.json()), (
        f"不带 key 的响应键集变了：{sorted(set(plain.json()) ^ set(keyed.json()))}"
    )
    assert plain.json()["mission"]["id"] != keyed.json()["mission"]["id"], (
        "不带 key 就必须仍按旧语义各起一枚作业（幂等只在有键时生效）"
    )


@OFFLINE
def test_a_malformed_key_is_refused_with_the_existing_validation_message() -> None:
    """owner=词汇一致：键太短 ⇒ 走 `validate_idempotency_key` 的既有 422，不新造错误。"""
    jid = _setup()
    short = _post(jid, CMD_A, "abc123")
    assert short.status_code == 422, f"实际 {short.status_code} {short.text[:160]}"
    assert "8..128" in str(short.json()), f"没复用既有校验那句话：{short.text[:200]}"
    assert _mission_ids(jid) == [], "被拒的请求不该留下任何作业"


@OFFLINE
def test_the_contract_and_the_route_declare_the_same_header() -> None:
    """owner=词汇不漂移：契约与路由必须同时声明这一个头（只在纸面或只在代码里，都还是 ORD-0253）。"""
    import yaml

    spec = yaml.safe_load((Path(__file__).resolve().parents[2] / "contracts/openapi.yaml")
                          .read_text(encoding="utf-8"))
    op = spec["paths"]["/journeys/{journey_id}/agent/commands"]["post"]
    refs = [p.get("$ref", "") for p in (op.get("parameters") or [])]
    assert any(r.endswith("/IdempotencyKeyOptional") for r in refs), (
        f"契约里这个 operation 没声明幂等头：{refs}"
    )
    optional = spec["components"]["parameters"]["IdempotencyKeyOptional"]
    required = spec["components"]["parameters"]["IdempotencyKey"]
    assert (optional["name"], optional["in"], optional["schema"]) == (
        required["name"], required["in"], required["schema"]
    ), "另造了一个头形状 ⇒ 第二套词汇，正是这条单禁止的"
    assert optional["required"] is False and required["required"] is True, (
        "只有 requiredness 允许不同：本路由'带了就生效、没带保持旧行为'"
    )

    runtime = [p for p in app.openapi()["paths"]["/api/v1/journeys/{journey_id}/agent/commands"]
               ["post"].get("parameters", [])]
    assert any(p.get("name") == "Idempotency-Key" for p in runtime), (
        f"运行时的 OpenAPI 里没有这个头 ⇒ 代码没真的读它：{[p.get('name') for p in runtime]}"
    )


# ------------------------------------------------------------------------ 并发（排出来，不赌）


@OFFLINE
def test_two_threads_one_key_produce_one_mission() -> None:
    """owner=并发同键：真把两发排在同一时刻（Barrier），库里仍只能 1 行、两边答案同一枚 mission。"""
    jid = _setup()
    key = f"ord0253-race-{jid}"
    gate = threading.Barrier(2)
    out: list[tuple[int, str | None]] = []
    lock = threading.Lock()

    def click() -> None:
        gate.wait()  # 双方都到位才放行：排一次race，不赌时间窗
        response = _post(jid, CMD_A, key)
        mission = (response.json().get("mission") or {}).get("id")
        with lock:
            out.append((response.status_code, mission))

    threads = [threading.Thread(target=click) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(out) == 2, "两发都没回来，这一格什么都没量到"
    ids = {mission for _, mission in out}
    assert all(status == 200 for status, _ in out), f"同键并发里出现了非 200：{out}"
    assert len(ids) == 1 and None not in ids, (
        f"并发同键必须回到同一枚逻辑 mission：{sorted(map(str, ids))}"
    )
    assert len(_mission_ids(jid)) == 1, (
        f"并发同键只能持久 1 行 journey_missions，实际 {len(_mission_ids(jid))} 行"
    )
