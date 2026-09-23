"""ORD-0253 跨进程同键：**两个真 OS 进程、一个 sqlite 文件、一把 `Idempotency-Key`**。

为什么还要这一把：`test_qoder_agent_command_idempotency.py` 的并发格是**同进程两线程**，
`journey_write_lock` 会替我把 race 兜住 —— 那证明的是"进程内安全"，不是"跨进程安全"。
两个真进程各自持有自己的进程内锁，唯一还能保证恰好一次的只有**库**（唯一索引 + 已提交回执回放）。
这一格若拿不到，我原先写的 `CROSS_PROCESS = NOT_MEASURED` 就不能撤 —— 它不算通过。

形制（commander 2026-09-23 点头）：自己的端口、自己的库文件、自己的清理，不借别人的面；
归属一律走**具名 marker**：
  * A 面带 `CITYNEXUS_E2E_RUN_ID`（产品自己会回显 run id 与它打开的库文件名，`/api/v1/health`）
  * 两面各自 `netstat` 的 LISTENING PID == 我起的进程 PID
  * 只有我这个临时库里才有的唯一 journey（UUID 标题）能从**对面**读回来
证不到就 `SETUP_UNPROVEN` 红，不改判据、不静默跳过。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
TZ = timezone(timedelta(hours=8))
ROUNDS = 5                      # 每轮一条新 journey + 新键，逐轮独立断言（一轮绿不算稳）

CMD_A = "我护照丢了，请告诉我怎么办。"
CMD_B = "帮我把今晚的安排换成室内活动，节奏慢一点。"

#: 子进程环境里必须摘掉的东西：带着真 key 起面，幂等形状就会变成网络依赖
STRIP = (
    "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_AI_ENABLED",
    "CITYNEXUS_AI_PROVIDER", "CITYNEXUS_AI_MODEL", "CITYNEXUS_AI_VISION_MODEL",
    "CITYNEXUS_HERMES_API_KEY", "CITYNEXUS_HERMES_API_SERVER_KEY",
    "CITYNEXUS_LIVE_VALHALLA_URL", "CITYNEXUS_PHOTON_BASE_URL",
)


class SetupUnproven(RuntimeError):
    """仪器/归属证不到 ⇒ 红，并说清是哪一证缺（这一格绝不允许变成"看起来通过"）。"""


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _listener_pid(port: int) -> int | None:
    """`netstat -ano -p tcp` 里该端口的 LISTENING 行归属谁（按可执行名 + 端口数，不按命令行含串）。"""
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True)
    text = out.stdout.decode("utf-8", "replace")
    if out.returncode != 0:
        raise SetupUnproven(f"SETUP：netstat rc={out.returncode} ⇒ 端口归属无从证明")
    pids = {ln.split()[-1] for ln in text.splitlines()
            if f"127.0.0.1:{port}" in ln and "LISTENING" in ln.upper()}
    if len(pids) > 1:
        raise SetupUnproven(f"SETUP：端口 {port} 有 {len(pids)} 个监听者 {pids} ⇒ 归属不唯一，不测")
    return int(pids.pop()) if pids else None


def _spawn(db_file: Path, port: int, run_id: str | None):
    env = dict(os.environ)
    for name in STRIP:
        env.pop(name, None)
    env.pop("CITYNEXUS_E2E_RUN_ID", None)
    env["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    env["CITYNEXUS_AI_ENABLED"] = "false"
    if run_id:
        env["CITYNEXUS_E2E_RUN_ID"] = run_id          # 只有第一面能带：产品拒绝重开已存在的库
    log = db_file.with_name(f"{db_file.name}.port{port}.log")
    handle = log.open("wb")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "info"],
        cwd=str(BACKEND), env=env, stdout=handle, stderr=subprocess.STDOUT)
    return proc, log, handle


def _self_reported_pid(log: Path) -> int | None:
    """uvicorn 自己报的服务进程 PID（`Started server process [1234]`）。

    单靠它不算证据 —— 它只是"面自己说的"；必须与 netstat 的监听者对上才算。
    """
    text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""

    hits = re.findall(r"Started server process \[(\d+)\]", text)
    if not hits:
        return None
    if len(set(hits)) > 1:
        raise SetupUnproven(f"SETUP：同一份日志里报了多个服务 PID {sorted(set(hits))} ⇒ 面不可信")
    return int(hits[0])


def _parent_pid(pid: int) -> int | None:
    ps = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').ParentProcessId"],
        capture_output=True, text=True, errors="replace")
    out = (ps.stdout or "").strip()
    return int(out) if out.isdigit() else None


def _get(path: str, port: int, timeout: float = 5.0):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8", "replace"))


def _post(path: str, port: int, payload: dict, key: str | None = None, timeout: float = 25.0):
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if key is not None:
        headers["Idempotency-Key"] = key
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data,
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"_raw": body[:400]}


def _wait_ready(proc, port: int, log: Path, timeout: float = 90.0) -> dict:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SetupUnproven(f"SETUP：: {port} 的面自己退出了 rc={proc.returncode}\n"
                                f"日志尾：{log.read_text(encoding='utf-8', errors='replace')[-500:]}")
        try:
            status, body = _get("/api/v1/health", port)
            if status == 200:
                return body
            last = f"status={status}"
        except Exception as exc:                      # 起面期间的连接失败是常态
            last = f"{type(exc).__name__}: {exc}"[:120]
        time.sleep(0.4)
    raise SetupUnproven(f"SETUP：: {port} 在 {timeout}s 内没起来（最后一次 {last}）\n"
                        f"日志尾：{log.read_text(encoding='utf-8', errors='replace')[-500:]}")


def _stop(proc, port: int) -> None:
    if proc.poll() is None:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    deadline = time.time() + 15
    while time.time() < deadline:                     # 等 LISTENING 行真的消失再收工
        if _listener_pid(port) is None:
            return
        time.sleep(0.3)


@pytest.fixture(scope="module")
def pair():
    """自己起两面、自己的库、自己清干净（A 带 run id 建库，B 无标记地接同一枚文件）。"""
    tmp = Path(tempfile.mkdtemp(prefix=f"cnx_xproc_{uuid.uuid4().hex[:8]}_"))
    db = tmp / "xproc.db"
    run_id = f"ord0253-xproc-{uuid.uuid4().hex[:12]}"
    pa, pb = _free_port(), _free_port()
    proc_a, log_a, handle_a = _spawn(db, pa, run_id)
    proc_b: subprocess.Popen | None = None
    handle_b = None
    try:
        ha = _wait_ready(proc_a, pa, log_a)
        proc_b, log_b, handle_b = _spawn(db, pb, None)
        hb = _wait_ready(proc_b, pb, log_b)
        yield {"db": db, "a": (pa, proc_a), "b": (pb, proc_b),
               "logs": {pa: log_a, pb: log_b},
               "health": {pa: ha, pb: hb}, "run_id": run_id}
    finally:
        if proc_b is not None:
            _stop(proc_b, pb)
        _stop(proc_a, pa)
        for h in (handle_a, handle_b):            # 句柄不关，Windows 上整个目录删不掉
            if h is not None:
                h.close()
        for _ in range(25):
            shutil.rmtree(tmp, ignore_errors=True)
            if not tmp.exists():
                break
            time.sleep(0.2)
        assert not tmp.exists(), (
            f"自我清理失败：{tmp} 还在（里面的 .db/-wal/.log 会一次一次攒磁盘）")


# ------------------------------------------------------------------ 归属：三证齐了才允许报数

def test_0_the_two_faces_are_mine_and_offline(pair) -> None:
    """owner=归属：run id 回显 + 端口 PID 就是我起的进程 + 对面读得到我这枚库里独有的行。"""
    db = pair["db"]
    pa, proc_a = pair["a"]
    pb, proc_b = pair["b"]
    run_id = pair["run_id"]
    ha, hb = pair["health"][pa], pair["health"][pb]
    assert ha.get("e2e_run_id") == run_id, (
        f"A 面没回显我的 run id（拿到 {ha.get('e2e_run_id')!r}）⇒ 那个端口不是我的面")
    assert ha.get("e2e_database_id") == db.name, (
        f"A 面打开的库不是我建的 {db.name}（回显 {ha.get('e2e_database_id')!r}）")
    for port, proc in ((pa, proc_a), (pb, proc_b)):
        reported = _self_reported_pid(pair["logs"][port])
        listener = _listener_pid(port)
        assert reported is not None, (
            f"SETUP_UNPROVEN：:{port} 的面没在日志里报自己的服务 PID ⇒ 归属无证")
        assert listener == reported, (
            f"SETUP_UNPROVEN：:{port} 的监听者是 {listener}，面自报 {reported} ⇒ 不一致就不算我的面")
        father = _parent_pid(reported)
        assert reported == proc.pid or father == proc.pid, (
            f"SETUP_UNPROVEN：监听者 {reported}（父 {father}）不是我起的句柄 {proc.pid} "
            "（venv 启动器会 re-exec，故允许一跳）")
    for port, health in ((pa, ha), (pb, hb)):
        assert health.get("ai") == "disabled", (
            f"SETUP：:{port} 的面 ai={health.get('ai')} ⇒ 幂等形状会变成网络依赖，这一趟不算量到")
    # 独有行：只在 A 面上建，必须能从 B 面读回来（B 开的是同一个文件，不是"看起来像"）
    status, body = _post("/api/v1/travelers", pa,
                         {"display_name": "xproc", "timezone": "Asia/Shanghai"})
    assert status == 201, f"建 traveler 失败 {status} {body}"
    mark = f"xproc-marker-{uuid.uuid4().hex}"
    start = datetime(2026, 9, 26, 8, 0, tzinfo=TZ)
    status, jr = _post("/api/v1/journeys", pa, {
        "traveler_id": body["id"], "title": mark, "city_code": "CNX-DEMO",
        "timezone": "Asia/Shanghai", "start_at": start.isoformat(),
        "end_at": (start + timedelta(days=1, hours=8)).isoformat(),
        "budget": {"amount_minor": 20000, "currency": "CNY"}, "planning_mode": "balanced"})
    assert status == 201, f"建 journey 失败 {status} {jr}"
    status, seen = _get(f"/api/v1/journeys/{jr['id']}", pb)
    assert status == 200 and seen.get("title") == mark, (
        f"SETUP_UNPROVEN：B 面读不到我那枚独有 journey（{status} / {str(seen)[:160]}）")


# ------------------------------------------------------------------------ 跨进程：同键只能一行

def _seed_journey(port: int) -> str:
    status, t = _post("/api/v1/travelers", port,
                      {"display_name": "xproc", "timezone": "Asia/Shanghai"})
    assert status == 201, f"SETUP：建 traveler {status} {t}"
    start = datetime(2026, 9, 26, 8, 0, tzinfo=TZ)
    status, j = _post("/api/v1/journeys", port, {
        "traveler_id": t["id"], "title": f"xproc-{uuid.uuid4().hex[:8]}", "city_code": "CNX-DEMO",
        "timezone": "Asia/Shanghai", "start_at": start.isoformat(),
        "end_at": (start + timedelta(days=1, hours=8)).isoformat(),
        "budget": {"amount_minor": 20000, "currency": "CNY"}, "planning_mode": "balanced"})
    assert status == 201, f"SETUP：建 journey {status} {j}"
    return str(j["id"])


def _count(db: Path, sql: str, args: tuple = ()) -> int:
    with closing(sqlite3.connect(db, timeout=30)) as conn:
        return int(conn.execute(sql, args).fetchone()[0])


def _rows(db: Path, sql: str, args: tuple = ()) -> list[tuple]:
    with closing(sqlite3.connect(db, timeout=30)) as conn:
        return list(conn.execute(sql, args).fetchall())


def _log_tail(log: Path, limit: int = 3) -> str:
    """把面上的 traceback/异常行尾巴拿出来 —— 红要红得能归因，不印"Internal Server Error"就完了。

    帧行（`File "…"` / `raise`）与**最后一行原始输出**都要：异常类名与那句话在帧之后，
    只挑关键词会把最关键的一行筛掉（我第一次就这么丢过一次归因）。
    """
    if not log.is_file():
        return "(无日志)"
    raw = [ln.rstrip() for ln in log.read_text(encoding="utf-8", errors="replace").splitlines()]
    frames = [ln.strip() for ln in raw
              if any(k in ln for k in ("Traceback", 'File "', "raise ", "assert"))]
    named = [ln.strip() for ln in raw
             if re.search(r"\b\w*(?:Error|Exception|Timeout)\b", ln)]
    tail_raw = [ln.strip() for ln in raw[-6:] if ln.strip()]
    joined = " ⏎ ".join(named[-3:] + frames[-limit:] + ["── 末行 ──"] + tail_raw[-2:])
    return joined[:900] or "(日志里没有异常行)"


def test_1_two_processes_one_key_persist_exactly_one_mission(pair) -> None:
    """owner=跨进程同键：两发排在同一时刻、打在**不同进程**上 ⇒ 同一枚 mission、库里 1 行。"""
    db = pair["db"]
    pa, pb = pair["a"][0], pair["b"][0]
    failures: list[str] = []
    tally: dict[str, int] = {}
    for rnd in range(1, ROUNDS + 1):
        first_port, second_port = (pa, pb) if rnd % 2 else (pb, pa)   # 输赢轮流 ⇒ 两面都得读别人的行
        jid = _seed_journey(first_port)
        key = f"ord0253-xproc-{rnd}-{uuid.uuid4().hex[:8]}"
        barrier = threading.Barrier(2)
        out: list[dict] = []
        lock = threading.Lock()

        def click(port: int) -> None:
            barrier.wait(timeout=30)                    # 排一次 race，不赌时间窗
            status, body = _post(f"/api/v1/journeys/{jid}/agent/commands", port,
                                 {"command": CMD_A, "requested_autonomy": "PLAN_ONLY"}, key)
            with lock:
                out.append({"port": port, "status": status,
                            "mission": (body.get("mission") or {}).get("id"),
                            "body": str(body)[:160]})

        threads = [threading.Thread(target=click, args=(p,)) for p in (first_port, second_port)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)
        if len(out) != 2:
            failures.append(f"第 {rnd} 轮：只回来 {len(out)}/2 发 {out}")
            continue
        missions = {r["mission"] for r in out}
        rows = _count(db, "SELECT count(*) FROM journey_missions WHERE journey_id=?", (jid,))
        keys = _count(db, "SELECT count(*) FROM idempotency_keys WHERE key=?",
                      (f"agent.command:{key}",))
        bad = [r for r in out if r["status"] != 200]
        if bad or len(missions) != 1 or None in missions or rows != 1 or keys != 1:
            detail = _rows(db, "SELECT id, status, created_at FROM journey_missions "
                               "WHERE journey_id=? ORDER BY created_at", (jid,))
            tails = {p: _log_tail(pair["logs"][p]) for p in (pa, pb)}
            shape = ("GHOST_MISSION_ROW(两边都 200 且回同一枚 mission，库里却留了败者那枚)"
                     if not bad and rows > 1 else
                     "UNNAMED_500(库层唯一索引撞车被洗成裸 500，没走产品现成的 409/503 词汇)"
                     if bad else "SHAPE_UNCLASSIFIED")
            tally[shape] = tally.get(shape, 0) + 1
            failures.append(
                f"第 {rnd} 轮（首打 {first_port}）【{shape}】："
                f"两边={[(r['port'], r['status'], str(r['mission'])[:8]) for r in out]} "
                f"收据行={keys} 库内作业={[(str(i)[:8], s) for i, s, _c in detail]}；"
                f"面日志 A={tails[pa][:200]} ｜ B={tails[pb][:200]}")
    assert not failures, (
        f"跨进程同键必须每一轮都只持久 1 行、两边回同一枚 mission；{ROUNDS} 轮的红按形态计数 = "
        f"{tally} ⇒ 细节：\n" + "\n".join(failures))


def test_2_cross_process_different_intent_fails_closed(pair) -> None:
    """owner=跨进程不同意图：同键换命令，打到**对面**也必须走现成那句 409，且不落第二行。"""
    db = pair["db"]
    pa, pb = pair["a"][0], pair["b"][0]
    jid = _seed_journey(pa)
    key = f"ord0253-xproc-mismatch-{uuid.uuid4().hex[:8]}"
    status, body = _post(f"/api/v1/journeys/{jid}/agent/commands", pa,
                         {"command": CMD_A, "requested_autonomy": "PLAN_ONLY"}, key)
    assert status == 200, f"第一发必须成功才谈得上冲突：{status} {str(body)[:200]}"
    before = _count(db, "SELECT count(*) FROM journey_missions WHERE journey_id=?", (jid,))
    status, conflict = _post(f"/api/v1/journeys/{jid}/agent/commands", pb,
                             {"command": CMD_B, "requested_autonomy": "PLAN_ONLY"}, key)
    text = json.dumps(conflict, ensure_ascii=False)
    assert status == 409, f"跨进程同键不同意图必须 409：实际 {status} {text[:220]}"
    assert "different request" in text.lower() or "idempotency" in text.lower(), (
        f"必须沿用产品现成那句 mismatch 语义，别另造一套：{text[:220]}")
    after = _count(db, "SELECT count(*) FROM journey_missions WHERE journey_id=?", (jid,))
    assert (before, after) == (1, 1), f"拒收不该先落第二枚作业：{before} → {after}"


def test_3_the_loser_reads_the_winners_durable_receipt(pair) -> None:
    """owner=持久性（跨进程）：后发那发回到同一枚 mission，且那行在**文件**里不在内存里。"""
    db = pair["db"]
    pa, pb = pair["a"][0], pair["b"][0]
    jid = _seed_journey(pa)
    key = f"ord0253-xproc-durable-{uuid.uuid4().hex[:8]}"
    status, first = _post(f"/api/v1/journeys/{jid}/agent/commands", pa,
                          {"command": CMD_A, "requested_autonomy": "PLAN_ONLY"}, key)
    assert status == 200, f"{status} {str(first)[:200]}"
    mission = (first.get("mission") or {}).get("id")
    assert mission, f"没有 mission 就无从谈回放：{str(first)[:200]}"
    status, second = _post(f"/api/v1/journeys/{jid}/agent/commands", pb,
                           {"command": CMD_A, "requested_autonomy": "PLAN_ONLY"}, key)
    assert status == 200, f"对面同键同意图必须回放 200：{status} {str(second)[:200]}"
    assert (second.get("mission") or {}).get("id") == mission, (
        f"回放换了 mission：{mission} vs {second.get('mission')}")
    stored = _count(db, "SELECT count(*) FROM idempotency_keys WHERE key=?",
                    (f"agent.command:{key}",))
    assert stored == 1, f"收据在共享文件里应恰好 1 行，实际 {stored}"


def test_4_no_key_cross_process_stays_independent(pair) -> None:
    """owner=向后兼容（跨进程）：不带键时两发各自成立，且**不落**收据行（幂等只在带键时生效）。"""
    db = pair["db"]
    pa, pb = pair["a"][0], pair["b"][0]
    jid = _seed_journey(pa)
    receipts_before = _count(db, "SELECT count(*) FROM idempotency_keys "
                                  "WHERE key LIKE 'agent.command:%'")
    s1, b1 = _post(f"/api/v1/journeys/{jid}/agent/commands", pa,
                   {"command": CMD_A, "requested_autonomy": "PLAN_ONLY"})
    s2, b2 = _post(f"/api/v1/journeys/{jid}/agent/commands", pb,
                   {"command": CMD_A, "requested_autonomy": "PLAN_ONLY"})
    assert (s1, s2) == (200, 200), f"无键两发都该 200：{s1} {str(b1)[:120]} / {s2} {str(b2)[:120]}"
    m1, m2 = (b1.get("mission") or {}).get("id"), (b2.get("mission") or {}).get("id")
    assert m1 and m2 and m1 != m2, f"无键必须各自成立（若相等=过度合并）：{m1} vs {m2}"
    assert _count(db, "SELECT count(*) FROM journey_missions WHERE journey_id=?", (jid,)) == 2
    receipts_after = _count(db, "SELECT count(*) FROM idempotency_keys "
                                "WHERE key LIKE 'agent.command:%'")
    assert receipts_after == receipts_before, (
        f"不带键就不该造幂等收据：{receipts_before} → {receipts_after}")
