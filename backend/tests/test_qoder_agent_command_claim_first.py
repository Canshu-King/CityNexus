"""ORD-0253 · **claim-first** 之后的常驻门：占了键却没回填时，谁都不许再写 mission。

形制说明（G5，先看这条再引用任何绿）：本文件**全部是单进程**（TestClient 与测试同进程，
`server_pid == os.getpid()`）。进程内那把 `journey_write_lock` 会把两线程串起来，所以
"两线程同键"在这里**永远**绿——它证明的是"没有回归"，不是"跨进程已闭"。跨进程那一格
（faces=2）归 verifier（仲裁 `5793495820` §3）。

我不再"赌一次 race"：把冲突做成**已落库的前置状态**（占位行 / 已填行 / 签名不符行），
于是每一格都是确定性的，并且判**在行上**（`journey_missions` 的行数），不判在状态码上。
"""
from __future__ import annotations

import contextlib
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event as sa_event, select

from app.commerce.idempotency import canonical_request_signature
from app.core.config import settings
from app.db.models import IdempotencyKey, JourneyMission
from app.db.session import SessionLocal, engine
from app.main import app

client = TestClient(app)
BACKEND = Path(__file__).resolve().parents[1] / "app"      # 被扫的产品代码根（⑦ 那格用）
TZ = timezone(timedelta(hours=8))
CMD_A = "我护照丢了，请告诉我怎么办。"
CMD_B = "帮我把今晚的安排换成室内活动，节奏慢一点。"

#: **门内自带的字面副本**（G4：不 import 产品常量——import 之后它就永远和自己相等，测不到漂移）。
#: 两句都是产品里已有的话，本次改动一个字都不新增。
SENT_DIFFERENT_REQUEST = "same idempotency key used for a different request"
SENT_INCOMPLETE_RECEIPT = "agent idempotency record is incomplete"


def _setup_journey() -> str:
    traveler = client.post("/api/v1/travelers",
                           json={"display_name": "claimfirst", "timezone": "Asia/Shanghai"})
    assert traveler.status_code == 201, traveler.text
    start = datetime(2026, 9, 26, 8, 0, tzinfo=TZ)
    journey = client.post("/api/v1/journeys", json={
        "traveler_id": traveler.json()["id"], "title": f"claimfirst-{uuid.uuid4().hex[:8]}",
        "city_code": "CNX-DEMO", "timezone": "Asia/Shanghai", "start_at": start.isoformat(),
        "end_at": (start + timedelta(days=1, hours=8)).isoformat(),
        "budget": {"amount_minor": 20000, "currency": "CNY"}, "planning_mode": "balanced"})
    assert journey.status_code == 201, journey.text
    return str(journey.json()["id"])


def _signature(jid: str, command: str = CMD_A, autonomy: str = "PLAN_ONLY") -> str:
    return canonical_request_signature({"journey_id": jid, "command": command,
                                        "requested_autonomy": autonomy})


def _post_key(jid: str, key: str, command: str = CMD_A, autonomy: str = "PLAN_ONLY"):
    return client.post(f"/api/v1/journeys/{jid}/agent/commands",
                       json={"command": command, "requested_autonomy": autonomy},
                       headers={"Idempotency-Key": key})


def _put_receipt(scoped_key: str, signature: str, *, body: dict | None) -> None:
    """把"别人已经占了这把键"做成**已落库**的前置状态，而不是赌一次时序。"""
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        session.add(IdempotencyKey(
            key=scoped_key, operation="agent.command", request_hash=signature,
            response_status=200 if body is not None else None,
            response_json=json.dumps(body, sort_keys=True) if body is not None else None,
            created_at=now.isoformat(), expires_at=(now + timedelta(days=7)).isoformat()))
        session.commit()


def _mission_rows(jid: str) -> list[str]:
    with SessionLocal() as session:
        return sorted(session.scalars(select(JourneyMission.id)
                                      .where(JourneyMission.journey_id == jid)).all())


def _receipt_rows(scoped_key: str) -> list[IdempotencyKey]:
    with SessionLocal() as session:
        return list(session.scalars(select(IdempotencyKey).where(IdempotencyKey.key == scoped_key)))


def _message_of(response) -> str:
    """信封里那句**服务器原话**。比较一律用 `==`，不用 `in` —— 理由见最后一格。"""
    return str(response.json()["error"]["message"])


def _message_equals(response, expected: str) -> bool:
    try:
        return _message_of(response) == expected
    except Exception:
        return False


# -------------------------------------------------------------------------------- G1

def test_1_an_unfilled_claim_blocks_the_write_and_is_answered_with_the_existing_409() -> None:
    """owner=G1：有人占了键却没回填 ⇒ 我不进 impl、库里 0 行、答案是现成那句 409。"""
    jid = _setup_journey()
    key = f"cf-unfilled-{uuid.uuid4().hex[:8]}"
    _put_receipt(f"agent.command:{key}", _signature(jid), body=None)

    response = _post_key(jid, key)
    assert response.status_code == 409, f"G1：实际 {response.status_code} {response.text[:220]}"
    assert _message_equals(response, SENT_INCOMPLETE_RECEIPT), (
        f"G1：必须逐字沿用现成那句（不新造词），实际 {_message_of(response)[:200]!r}")
    assert _mission_rows(jid) == [], (
        f"G1：占了键的那发不能替我建 mission ⇒ 这正是 GHOST_MISSION_ROW 的形状，"
        f"实际 {len(_mission_rows(jid))} 行")


# -------------------------------------------------------------------------------- G2

def test_2_a_filled_claim_is_replayed_without_building_a_second_mission() -> None:
    """owner=G2：键已被填好 ⇒ 回赢家那份正文，且**一行都不许多**。"""
    jid = _setup_journey()
    key = f"cf-filled-{uuid.uuid4().hex[:8]}"
    winner_mission = {"mission": {"id": str(uuid.uuid4()), "journey_id": jid}, "replayed": True}
    _put_receipt(f"agent.command:{key}", _signature(jid), body=winner_mission)

    response = _post_key(jid, key)
    assert response.status_code == 200, f"G2：实际 {response.status_code} {response.text[:200]}"
    assert response.json()["mission"]["id"] == winner_mission["mission"]["id"], (
        "G2：回放必须回**那一枚** mission，而不是另起一枚")
    assert _mission_rows(jid) == [], (
        f"G2：回放的一发不该建行，实际 {len(_mission_rows(jid))} 行")
    assert len(_receipt_rows(f"agent.command:{key}")) == 1, "G2：收据行也只能有一枚（唯一索引在，不该多插）"


# -------------------------------------------------------------------------------- G3

def test_3_same_key_different_intent_is_still_the_canonical_mismatch_409() -> None:
    """owner=G3：同键换意图 ⇒ 现成那句 mismatch，不许被新语义顶掉。"""
    jid = _setup_journey()
    key = f"cf-mismatch-{uuid.uuid4().hex[:8]}"
    _put_receipt(f"agent.command:{key}", _signature(jid), body={"mission": {"id": str(uuid.uuid4())}})

    response = _post_key(jid, key, command=CMD_B)
    assert response.status_code == 409, f"G3：实际 {response.status_code}"
    assert _message_equals(response, SENT_DIFFERENT_REQUEST), (
        f"G3：mismatch 那句话必须逐字原样，实际 {_message_of(response)[:200]!r}")
    assert _mission_rows(jid) == [], "G3：被拒的一发不许先建行再报错"


# -------------------------------------------------------------------------------- G4

def test_4_the_happy_path_still_creates_exactly_one_mission_and_fills_the_claim() -> None:
    """owner=G4：没人占键时一切照旧——1 行 mission，且收据行被**回填**（不是留个空壳）。"""
    jid = _setup_journey()
    key = f"cf-happy-{uuid.uuid4().hex[:8]}"
    first = _post_key(jid, key)
    assert first.status_code == 200, first.text
    assert len(_mission_rows(jid)) == 1, f"G4：实际 {len(_mission_rows(jid))} 行"
    rows = _receipt_rows(f"agent.command:{key}")
    assert len(rows) == 1, f"G4：收据应 1 行，实际 {len(rows)}"
    assert rows[0].response_json and json.loads(rows[0].response_json)["mission"]["id"] \
        == first.json()["mission"]["id"], (
        "G4：占位行必须被回填成「这一发的答案」，否则下一位只会拿到 409")
    assert rows[0].response_status == 200, rows[0].response_status


def test_5_two_threads_one_key_in_one_process_stay_at_one_row() -> None:
    """owner=G5(回归面)：两线程同键 ⇒ 仍只 1 行。**这一格证明不了跨进程**（见文件头）。"""
    jid = _setup_journey()
    key = f"cf-threads-{uuid.uuid4().hex[:8]}"
    barrier = threading.Barrier(2)
    out: list[int] = []

    def fire() -> None:
        barrier.wait(timeout=30)
        out.append(_post_key(jid, key).status_code)

    threads = [threading.Thread(target=fire) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert len(out) == 2 and all(code == 200 for code in out), f"G5：读数 {out}"
    assert len(_mission_rows(jid)) == 1, f"G5：实际 {len(_mission_rows(jid))} 行"


# -------------------------------------------------------------------------------- G4 的字面等值自证

def test_6_the_two_sentences_are_compared_literally_and_the_door_would_notice_drift() -> None:
    """owner=G4：证明"比字面"这一手是咬着的——差一个标点就该红。

    不 import 产品常量：那样它永远等于自己，测不到漂移（这是我自己踩过的坑）。
    """
    assert SENT_INCOMPLETE_RECEIPT == "agent idempotency record is incomplete"
    assert SENT_DIFFERENT_REQUEST == "same idempotency key used for a different request"

    class _Resp:
        def __init__(self, message: str) -> None:
            self._message = message

        def json(self) -> dict:
            return {"error": {"message": self._message}}

    # 漂移样本：加标点、加后缀、截断、加尾空格 —— **逐字**比较必须全都不认。
    # （我上一版用 `in`，前两种会被读成"匹配"，于是门会一边红一边假称"沿用了现成那句"）
    for drifted in ("agent idempotency record is incomplete.",
                    "agent idempotency record is incomplete (stale claim)",
                    "agent idempotency record",
                    "same idempotency key used for a different request "):
        assert not _message_equals(_Resp(drifted), SENT_INCOMPLETE_RECEIPT), (
            f"G4：漂移被读成同一条 ⇒ 比较不咬字：{drifted!r}")
        assert not _message_equals(_Resp(drifted), SENT_DIFFERENT_REQUEST), (
            f"G4：漂移被读成同一条 ⇒ 比较不咬字：{drifted!r}")

    # 反面对照：完全相同的那句必须认。少了它，上面那一串"全都不认"可能只是比较坏了。
    assert _message_equals(_Resp(SENT_INCOMPLETE_RECEIPT), SENT_INCOMPLETE_RECEIPT), (
        "G4：连等值都不认 ⇒ 这一手是坏的，不是严的")


# ------------------------------------------- 仲裁 blocker：未回填占位不得成为"永久毒键"，
# ------------------------------------------- 但恢复规则只许 fail-closed，禁止"删行重跑"（会重复副作用）

def test_7_no_code_path_deletes_or_expires_away_an_idempotency_row() -> None:
    """owner=⑦：把被禁的那条路钉死——**全仓没有任何一处**删 idempotency_keys 的行。

    "按 expires_at 到点删掉占位再重跑 impl" 会在"赢家已落 mission、只来不及填回执"时重新
    制造重复副作用；仲裁禁止它。这里不靠我记得，靠扫：形制变了就红。
    """
    offenders = []
    for path in sorted(BACKEND.rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), start=1):
            low = line.lower()
            if "idempotency_keys" in low and ("delete from" in low or "truncate" in low):
                offenders.append(f"{path.relative_to(BACKEND)}:{number}")
            elif "idempotencykey" in low and (".delete()" in low or "delete(" in low):
                offenders.append(f"{path.relative_to(BACKEND)}:{number}")
    assert offenders == [], (
        f"⑦：出现删除/清空幂等行的路径 ⇒ 恢复规则被写成'删了重跑'（仲裁禁止）：{offenders}")


def test_8_a_committed_run_never_leaves_an_unfilled_claim() -> None:
    """owner=⑧：同事务落库 ⇒ 成功那发之后，库里**不该存在** response_json 为空的行。

    这不是"顺手查一下"：它正是"未回填占位=永久毒键"这一担忧的反证——形状根本不出来，
    就不需要谁去回收它。
    """
    jid = _setup_journey()
    key = f"cf-noshell-{uuid.uuid4().hex[:8]}"
    response = _post_key(jid, key)
    assert response.status_code == 200, response.text
    # 只查**这一发**留下的行：前面几格是故意预置"未回填占位"当输入的，把它们算进来
    # 就等于我的仪器在测我自己的夹具，而不是测产品（这个错我自己刚踩过一次）。
    with SessionLocal() as session:
        shells = list(session.scalars(select(IdempotencyKey).where(
            IdempotencyKey.key == f"agent.command:{key}",
            (IdempotencyKey.response_json.is_(None)) | (IdempotencyKey.response_status.is_(None)))))
    assert shells == [], (
        f"⑧：留下 {len(shells)} 行未回填占位 ⇒ 这一把键会永久废掉（仲裁 blocker），"
        "且说明占位与答案没在同一次提交里")


def test_9_completed_receipts_keep_the_existing_seven_day_semantics() -> None:
    """owner=⑨：completed 回执的有效期**沿用 +7d**，不许为了"回收占位"偷偷改成短 TTL。"""
    jid = _setup_journey()
    key = f"cf-ttl-{uuid.uuid4().hex[:8]}"
    assert _post_key(jid, key).status_code == 200
    rows = _receipt_rows(f"agent.command:{key}")
    assert len(rows) == 1, f"⑨：应 1 行，实际 {len(rows)}"
    created = datetime.fromisoformat(rows[0].created_at)
    expires = datetime.fromisoformat(rows[0].expires_at)
    assert (expires - created) == timedelta(days=7), (
        f"⑨：有效期变成 {expires - created} ⇒ 有人把它当回收钩子用了（应为现成的 +7d）")


# ========================== 仲裁 5796421307 §② 的五格机械门（Phase A CLAIM / Phase B EXECUTE）
# ========================== 缺一格不算完成；每格只问它自己那一条问题，owner 写在名字与断言里

DB_PATH = Path(settings.database_url.replace("sqlite:///", "", 1))


def _durable(sql: str, args: tuple = ()) -> list[tuple]:
    """**门外第二条连接**的 durable 读数。

    SQLAlchemy 那条连接看不见自己未提交的东西；这一条只承认"已经提交到盘上"的。
    (ii)/(iii) 要判的正是后者，所以这里绝不用 SessionLocal 自证。
    """
    assert DB_PATH.is_file(), f"SETUP：读不到 {DB_PATH} ⇒ durable 读数无从判定，不许当通过"
    with contextlib.closing(sqlite3.connect(DB_PATH, timeout=30)) as conn:
        return list(conn.execute(sql, args))


def _side_effect_counts(jid: str) -> dict[str, int]:
    """这一发可能留下的四类副作用，一次数齐（②④⑤ 都判这张表）。"""
    return {table: int(_durable(f"SELECT count(*) FROM {table} WHERE journey_id=?", (jid,))[0][0])
            for table in ("journey_missions", "agent_runs", "audit_logs", "events")}


@pytest.fixture(autouse=True)
def _offline_precondition() -> None:
    """本文件每一格的前提：外部 AI 与 Hermes native 都关着。开着 ⇒ **红**，不是 skip。

    为什么不用 skip：机械门①②④⑤判的是"durable 行"，而外部 run 不在 Phase B 的提交边界里
    （`HermesNativeClient` 是 httpx 客户端，本地根本没有它的行）。一台开着外部 AI 的机器上，
    "没量到"绝不该被读成"过了"。
    """
    from app.integrations.hermes.native_client import native_hermes_status

    assert not settings.ai_api_key, "SETUP：这台机器开着外部 AI ⇒ 本门量不到我想量的那一发"
    assert not native_hermes_status().get("ready"), (
        "SETUP：Hermes native 就绪 ⇒ 外部 run 落在提交边界之外，durable 读数不成立")


def _watch_impl(monkeypatch, probe=None) -> list[str]:
    """把 impl 换成"记一笔自己被人叫过"再原样转发 ⇒ 允许断言"根本没叫"。

    `probe(journey_id)` 在**进入 impl 的那一刻**跑，用来量"这一发开始干活时盘上已经有什么"。
    """
    import app.main as product
    original = product._run_agent_command_impl
    calls: list[str] = []

    def spy(journey_id, payload, session):
        calls.append(str(journey_id))
        if probe is not None:
            probe(str(journey_id))
        return original(journey_id, payload, session)

    monkeypatch.setattr(product, "_run_agent_command_impl", spy)
    return calls


def test_10_a_competing_connection_sees_the_committed_null_claim_before_impl_starts(
        monkeypatch) -> None:
    """owner=机械门①：跨进程所有权点必须**先于任何副作用**已经 durable。"""
    jid = _setup_journey()
    key = f"cf-mech1-{uuid.uuid4().hex[:8]}"
    scoped = f"agent.command:{key}"
    seen: list[tuple] = []

    def probe(journey_id: str) -> None:
        seen.append((_durable("SELECT response_json, response_status FROM idempotency_keys "
                              "WHERE key = ?", (scoped,)),
                     _side_effect_counts(journey_id)))

    calls = _watch_impl(monkeypatch, probe)
    # 绝对零不行：建 journey 自己就会留一行 audit_logs ⇒ 判**相对夹具的增量**
    baseline = _side_effect_counts(jid)
    response = _post_key(jid, key)
    assert response.status_code == 200, response.text
    assert calls == [jid], f"①：impl 应当恰好被叫一次（量的是这一发），实际 {calls}"

    claim_rows, effects = seen[0]
    assert len(claim_rows) == 1, (
        f"① **claim-first 不成立**：impl 已经开始干活，门外那条独立连接却看到 "
        f"{len(claim_rows)} 行占位 ⇒ 占位没有先提交，两个进程都会先各自跑一遍 impl：{claim_rows}")
    assert claim_rows[0] == (None, None), (
        f"①：impl 开始时占位行必须仍是未回填的 NULL（现在才是 IN_FLIGHT），实际 {claim_rows[0]}")
    assert effects == baseline, (
        f"①：所有权被裁决之前盘上多了 durable 副作用（相对夹具的增量），"
        f"基线 {baseline} → impl 入口 {effects}")


def test_11_the_loser_is_stopped_before_impl_and_persists_nothing(monkeypatch) -> None:
    """owner=机械门②：键已被占 ⇒ 败者**不进 impl**，mission/run 的行数一根不长。"""
    jid = _setup_journey()
    key = f"cf-mech2-{uuid.uuid4().hex[:8]}"
    _put_receipt(f"agent.command:{key}", _signature(jid), body=None)
    calls = _watch_impl(monkeypatch)
    before = _side_effect_counts(jid)

    response = _post_key(jid, key)
    assert response.status_code == 409, (
        f"②：占了键的败者不该被放行去干活，实际 {response.status_code} {response.text[:180]}")
    assert _message_equals(response, SENT_INCOMPLETE_RECEIPT), (
        f"②：等不到答案时必须逐字沿用现成那句 fail-closed，实际 {_message_of(response)[:160]!r}")
    assert calls == [], (
        f"② **败者进了 impl**：它已经替赢家跑了一遍副作用（被叫在 {calls}），"
        "唯一索引没有成为进 impl 之前的门")
    assert _side_effect_counts(jid) == before, (
        f"②：败者一行都不许多加，前 {before} → 后 {_side_effect_counts(jid)}")


def test_12_the_claim_commits_first_and_the_answer_shares_one_commit_with_the_work() -> None:
    """owner=机械门③：占位先提交；赢家的 mission 副作用与 completed 回执**同一次提交**可见。

    判的是引擎上真实发出的语句顺序与所属连接，不是我记得的代码形状。
    """
    jid = _setup_journey()
    key = f"cf-mech3-{uuid.uuid4().hex[:8]}"
    scoped = f"agent.command:{key}"
    observed: list[tuple[str, int]] = []

    def on_sql(conn, cursor, statement, parameters, context, executemany) -> None:
        head = " ".join(statement.split()[:3]).upper()
        blob = str(parameters)
        if scoped in blob and head.startswith("INSERT INTO IDEMPOTENCY_KEYS"):
            observed.append(("INSERT claim", id(conn)))
        elif scoped in blob and head.startswith("UPDATE IDEMPOTENCY_KEYS"):
            observed.append(("UPDATE claim", id(conn)))
        elif jid in blob and head.startswith("INSERT INTO JOURNEY_MISSIONS"):
            observed.append(("mission", id(conn)))

    def on_commit(conn) -> None:
        observed.append(("COMMIT", id(conn)))

    sa_event.listen(engine, "after_cursor_execute", on_sql)
    sa_event.listen(engine, "commit", on_commit)
    try:
        response = _post_key(jid, key)
    finally:
        sa_event.remove(engine, "after_cursor_execute", on_sql)
        sa_event.remove(engine, "commit", on_commit)
    assert response.status_code == 200, response.text
    assert observed, "SETUP：一条语句都没量到 ⇒ 仪器没挂上，不许当通过"
    claim_conn = next((c for n, c in observed if n == "INSERT claim"), None)
    work_conn = next((c for n, c in observed if n == "mission"), None)
    fill_conn = next((c for n, c in observed if n == "UPDATE claim"), None)
    assert claim_conn and work_conn and fill_conn, (
        f"③：Phase A 的插入 / mission 的写入 / 回执的回填缺任何一段 ⇒ 这一发没走 claim-first："
        f"{observed}")
    assert work_conn == fill_conn, (
        f"③：mission 与回执回填不在同一条连接 ⇒ 不可能同一次提交可见")
    first_claim = observed.index(("INSERT claim", claim_conn))
    claim_commit = next((i for i, (n, c) in enumerate(observed)
                         if n == "COMMIT" and c == claim_conn and i > first_claim), None)
    mission_at = observed.index(("mission", work_conn))
    assert claim_commit is not None and claim_commit < mission_at, (
        f"③：占位行的那次提交没有排在第一条 mission 之前 ⇒ 所有权点仍在副作用之后：{observed}")
    fill_at = observed.index(("UPDATE claim", fill_conn))
    between = [n for n, c in observed[mission_at + 1:fill_at] if n == "COMMIT" and c == work_conn]
    assert between == [], (
        f"③：mission 已单独提交、回执还没填 ⇒ 中间存在「有作业无答案」的窗口：{observed}")
    after = [n for n, c in observed[fill_at + 1:] if n == "COMMIT" and c == work_conn]
    assert after, f"③：回执回填之后没有提交 ⇒ 赢家的工作与答案都没落：{observed}"
    assert _side_effect_counts(jid)["journey_missions"] == 1
    assert _durable("SELECT response_json IS NOT NULL FROM idempotency_keys WHERE key = ?",
                    (scoped,))[0][0] == 1, "③：盘上那枚占位必须已被填成答案"


class _InjectedPhaseBFailure(RuntimeError):
    """故障注入用：只在「mission 已建、receipt 尚未填」那一点抛。"""


def test_13_a_phase_b_failure_leaves_no_durable_side_effect_but_keeps_the_null_claim(
        monkeypatch) -> None:
    """owner=机械门④：Phase B 回滚 ⇒ mission/run/audit/event 一行不留，NULL 占位仍在。

    注入点是 impl 里的 `mission_payload(...)`：它在 mission 与 run 都已写出之后、
    回执回填之前被调用 —— 正好是仲裁点名的那一格。
    """
    jid = _setup_journey()
    key = f"cf-mech4-{uuid.uuid4().hex[:8]}"
    scoped = f"agent.command:{key}"

    def explode(_mission):
        raise _InjectedPhaseBFailure("injected between mission and receipt")

    monkeypatch.setattr("app.main.mission_payload", explode)
    baseline = _side_effect_counts(jid)          # 夹具自己那行 audit 计入基线，不算产品的账
    with pytest.raises(_InjectedPhaseBFailure):
        _post_key(jid, key)

    effects = _side_effect_counts(jid)
    assert effects == baseline, (
        f"④ **Phase B 逃出了提交边界**：注入点之前写的东西 durable 了下来 ⇒ 回滚收不回它，"
        f"这正是 1f86a8f 的 ghost 形制。基线 {baseline} → 回滚后 {effects}")
    assert (effects["journey_missions"], effects["events"]) == (0, 0), (
        f"④：新 journey 的 mission/event 本底就是 0，绝对值必须也是 0（不许被基线吸收）："
        f"{effects}")
    claim = _durable("SELECT response_json, response_status FROM idempotency_keys WHERE key = ?",
                     (scoped,))
    assert claim == [(None, None)], (
        f"④：Phase A 的 NULL 占位必须**留着**（它是有主之物没跑完的证据，不删不顶），"
        f"实际 {claim}")


def _expiry_pruning_hits(lines) -> list[str]:
    """哪些行把幂等行**按有效期**筛了（= 到点回收的钩子）。⑤ 与它的自测共用同一把尺。"""
    hits = []
    for number, line in enumerate(lines, start=1):
        if "IdempotencyKey.expires_at" in line or (
                "idempotency_keys" in line and "expires_at" in line):
            hits.append(f"{number}:{line.strip()[:70]}")
    return hits


def test_14_stale_claim_recovery_fails_closed_and_duplicates_nothing(
        monkeypatch) -> None:
    """owner=机械门⑤：恢复只许 fail-closed —— 不按 expires_at 删、不重跑副作用；换新键才成功。"""
    # 先证明这把尺咬得住：一条该抓、一条不该抓。少了这两条，下面的 0 命中什么都不是。
    healthy = "    row = session.get(IdempotencyKey, scoped_key)"
    assert _expiry_pruning_hits([healthy]) == [], (
        f"⑤ 自测：一把连「按主键读」都抓的尺不能用来宣布 0 命中")
    caught = _expiry_pruning_hits([
        '    s.query(IdempotencyKey).filter(IdempotencyKey.expires_at < now).delete()',
        '    conn.execute("SELECT key FROM idempotency_keys WHERE expires_at < ?")'])
    assert len(caught) == 2, f"⑤ 自测：这把尺抓不到「到点回收」的写法 ⇒ 它是空的：{caught}"

    offenders: list[str] = []
    for path in sorted(BACKEND.rglob("*.py")):
        offenders += [f"{path.relative_to(BACKEND)}:{h}"
                      for h in _expiry_pruning_hits(path.read_text(
                          encoding="utf-8", errors="replace").splitlines())]
    assert offenders == [], (
        f"⑤：产品里出现了按有效期筛幂等行的读法 ⇒ 有人把它当回收钩子用了（仲裁禁止）：{offenders}")

    jid = _setup_journey()
    dead = f"cf-mech5-dead-{uuid.uuid4().hex[:8]}"
    scoped_dead = f"agent.command:{dead}"

    def explode(_mission):
        raise _InjectedPhaseBFailure("injected: claim left unfilled")

    monkeypatch.setattr("app.main.mission_payload", explode)
    with pytest.raises(_InjectedPhaseBFailure):
        _post_key(jid, dead)
    monkeypatch.undo()

    baseline = _side_effect_counts(jid)          # 崩溃之后盘上只有夹具自己的账
    calls = _watch_impl(monkeypatch)
    same_key = _post_key(jid, dead)
    assert same_key.status_code == 409, (
        f"⑤：未回填的占位上再打同一把键必须 fail closed，实际 {same_key.status_code}")
    assert calls == [], f"⑤：恢复路径重跑了 impl（{calls}）⇒ 会重复既有副作用"
    assert _side_effect_counts(jid) == baseline, (
        f"⑤：被拒的恢复动了盘，基线 {baseline} → 现在 {_side_effect_counts(jid)}")
    assert _durable("SELECT response_json, response_status FROM idempotency_keys WHERE key = ?",
                    (scoped_dead,)) == [(None, None)], "⑤：占位既没被回收也没被顶掉（这条要成立）"

    fresh = f"cf-mech5-new-{uuid.uuid4().hex[:8]}"
    answer = _post_key(jid, fresh)
    assert answer.status_code == 200, answer.text
    after = _side_effect_counts(jid)
    assert after["journey_missions"] - baseline["journey_missions"] == 1, (
        f"⑤：换一把新键应当正好补出 1 枚作业（多了就是重复了副作用），实际 {baseline} → {after}")
