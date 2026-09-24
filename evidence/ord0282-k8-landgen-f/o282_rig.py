"""ORD-0282 rig: 落地代 45b0a5e2 上，那一处守卫在**两个真进程 + 一座一次性库 + 带外 sqlite 读数**下翻不翻。

唯一变量 = 那一行守卫（`IdempotencyKey.response_json.is_(None)`）。每一轮：
  · 两个独立 uvicorn 进程（端口/ pid / 解析到的库文件三重归属证明），一座带 run id 的一次性 `_o282_*.db`；
  · 腿 A 在一号进程上真生成并回填；腿 B 在二号进程上打**同一个 mission、另一把客户端键**（判据点名的那一型）；
  · 带外 sqlite 读：A_filled / B_filled / A 的回执字节在 B 之后是否逐字存活；
  · 检测器自证：每轮末尾用带外写改一次 A 的字节，确认我的 `bytes_survive` 看得见变化（不是恒真谓词）。
0 demo/reset、0 用户库；跑完逐字节还原 main.py 并回验 sha。
"""
from __future__ import annotations

import argparse
import contextlib
import difflib
import hashlib
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BACKEND = Path("D:/moodle/_qoder_f_run/e_0282_45b0a5e/"
               "Canshu-King-CityNexus-45b0a5e281cae9c37715173afd3ac5778f309ca7/backend")
MAIN = BACKEND / "app/main.py"
HARNESS = Path("D:/moodle/_qoder_f_run/o282_harness")
WORKER = HARNESS / "_o282_worker.py"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
RUN_ID = f"O282-{datetime.now():%d%H%M}-{uuid.uuid4().hex[:6]}"
DEMO_CITY = "CNX-DEMO"
CMD_A = "我护照丢了，请告诉我怎么办。"
GUARD_ANCHOR = ("                    .where(IdempotencyKey.key == key,\n"
                "                           IdempotencyKey.response_json.is_(None))\n")
UNGUARDED = "                    .where(IdempotencyKey.key == key)\n"
LANDING_MAIN_BLOB = "416ea4f210e967130710a900cdecd20e7a1b5eca"
LISTENING_STATES = ("LISTENING",)


def blob_of(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def http(port: int, method: str, path: str, body=None, headers=None, timeout=90.0):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method=method, data=data)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            return {"status": r.status, "body": raw, "ms": round((time.perf_counter() - t0) * 1000, 1)}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        return {"status": exc.code, "body": raw, "ms": round((time.perf_counter() - t0) * 1000, 1)}
    except Exception as exc:  # noqa: BLE001
        return {"status": None, "body": f"{type(exc).__name__}:{str(exc)[:160]}",
                "ms": round((time.perf_counter() - t0) * 1000, 1)}


def netstat_owner(port: int):
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0].upper() == "TCP" and parts[1].endswith(f":{port}") \
                and parts[3].upper() in LISTENING_STATES:
            return int(parts[4])
    return None


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def durable(db: Path, sql: str, args=()):
    assert db.is_file(), f"SETUP：读不到 {db}"
    last = None
    for a in range(8):            # 上一位写者被 terminate 后， WAL 恢复窗口里首几次读会抛 disk I/O error
        try:
            with contextlib.closing(sqlite3.connect(str(db), timeout=60)) as conn:
                return list(conn.execute(sql, args))
        except sqlite3.OperationalError as exc:
            last = exc
            time.sleep(0.5 + 0.5 * a)
    raise last


def receipts(db: Path, keys: list[str]):
    got = {}
    for k in keys:
        rows = durable(db, "SELECT response_status, response_json FROM idempotency_keys WHERE key=?",
                       (k,))
        got[k] = ("absent" if not rows else
                  "unfilled" if rows[0][1] is None else "filled",
                  rows[0][0] if rows else None,
                  rows[0][1] if rows else None)
    return got


def spawn(port: int, db_url: str, log: Path):
    env = dict(os.environ)
    for name in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_AI_ENABLED",
                 "CITYNEXUS_LIVE_VALHALLA_URL"):
        env.pop(name, None)
    env["CITYNEXUS_DATABASE_URL"] = db_url
    env["PYTHONPATH"] = str(BACKEND)
    fh = log.open("w", encoding="utf-8")
    proc = subprocess.Popen([PY, "-X", "utf8", str(WORKER), str(port), db_url], cwd=str(BACKEND),
                            stdout=fh, stderr=subprocess.STDOUT, env=env)
    return proc, fh


def wait_serving(proc, port: int, log: Path, db_file: Path, deadline=90.0) -> dict:
    end = time.time() + deadline
    while time.time() < end:
        if proc.poll() is not None:
            raise RuntimeError(f"worker :{port} 先退了：{log.read_text(encoding='utf-8', errors='replace')[-400:]}")
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            if '"kind": "serving"' in line:
                rep = json.loads(line)
                r = http(port, "GET", "/api/v1/health", timeout=5.0)
                if r["status"] == 200:
                    rep["health"] = r
                    return rep
        time.sleep(0.2)
    raise RuntimeError(f"worker :{port} 在 {deadline}s 内没自报 serving 且答 200")


def ownership(label, proc, port, rep, db_file):
    listener = netstat_owner(port)
    assert listener is not None, f"{label}：netstat 上 :{port} 没有监听者"
    assert int(rep["pid"]) == int(listener), f"{label}：自报 pid {rep['pid']} ≠ 内核记的 {listener}"
    assert int(rep["ppid"]) == int(proc.pid), f"{label}：自报 ppid {rep['ppid']} ≠ 句柄 {proc.pid}"
    assert Path(rep["resolved_db_file"]).resolve() == db_file.resolve(), (
        f"{label}：子进程解析到的库不是本轮那座：{rep['resolved_db_file']} vs {db_file}")
    return {"pid": rep["pid"], "netstat_pid": listener, "ppid_ok": True,
            "resolved_db": rep["resolved_db_file"], "ai_key_present": rep["ai_api_key_present"],
            "stripped": rep["env_keys_stripped"]}


def seed_stage(db_url: str):
    """产品自己的 in-process seed（不是 demo/reset）：目录与可抄的演示旅程。"""
    code = ("import os;os.environ['CITYNEXUS_DATABASE_URL']=%r;os.environ['CITYNEXUS_AI_ENABLED']='false'\n"
            "from app.db.session import SessionLocal, ensure_schema\n"
            "from app.services import seed_demo\n"
            "ensure_schema()\n"
            "with SessionLocal() as s:\n"
            "    seed_demo(s)\n"
            "print('SEEDED')\n" % db_url)
    p = subprocess.run([PY, "-X", "utf8", "-c", code], cwd=str(BACKEND), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=600,
                       env={**os.environ, "PYTHONPATH": str(BACKEND),
                            **{k: v for k, v in (("CITYNEXUS_DATABASE_URL", db_url),)}})
    assert "SEEDED" in (p.stdout or ""), f"SETUP：seed 失败 rc={p.returncode} {p.stdout[-300:]} {p.stderr[-300:]}"


def one_round(state: str, idx: int) -> dict:
    src = MAIN.read_text(encoding="utf-8")
    provenance = {"main_blob_at_round": blob_of(MAIN.read_bytes()),
                  "guard_anchor_hits_at_round": src.count(GUARD_ANCHOR),
                  "unguarded_anchor_hits_at_round": src.count(UNGUARDED),
                  "seam_symbol_at_round": "_fill_plan_generation_receipts" in src}
    db = HARNESS / f"_o282_{RUN_ID}_{state}_r{idx}.db"
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db) + suffix)
        if p.exists():
            p.unlink()
    db_url = f"sqlite:///{db.as_posix()}"
    seed_stage(db_url)
    p1, p2 = free_port(), free_port()
    logs = [HARNESS / f"_o282_{RUN_ID}_{state}_r{idx}_w{ i + 1}.log" for i in range(2)]
    procs = []
    try:
        w1, f1 = spawn(p1, db_url, logs[0])
        w2, f2 = spawn(p2, db_url, logs[1])
        procs = [(w1, f1), (w2, f2)]
        r1 = ownership("W1", w1, p1, wait_serving(w1, p1, logs[0], db), db)
        r2 = ownership("W2", w2, p2, wait_serving(w2, p2, logs[1], db), db)

        trav = http(p1, "POST", "/api/v1/travelers",
                    {"display_name": f"o282-{RUN_ID}", "timezone": "Asia/Shanghai"})
        assert trav["status"] == 201, f"SETUP：travelers 没建起来 {trav}"
        traveler = json.loads(trav["body"])
        with contextlib.closing(sqlite3.connect(str(db), timeout=60)) as conn:
            stage = conn.execute("SELECT city_code, timezone, start_at, end_at, planning_mode,"
                                 " budget_amount_minor, budget_currency FROM journeys"
                                 " WHERE city_code=? ORDER BY created_at LIMIT 1", (DEMO_CITY,)).fetchone()
        assert stage, f"SETUP：{DEMO_CITY} 没有可抄的演示旅程 ⇒ 自造窗口只会造假红"
        jy = http(p1, "POST", "/api/v1/journeys", {
            "traveler_id": traveler["id"], "title": f"o282-{RUN_ID}",
            "city_code": stage[0], "timezone": stage[1], "start_at": stage[2], "end_at": stage[3],
            "planning_mode": stage[4],
            "budget": {"amount_minor": stage[5], "currency": stage[6]}})
        assert jy["status"] == 201, f"SETUP：journeys 没建起来 {jy['body'][:200]}"
        jid = json.loads(jy["body"])["id"]

        cmd = http(p1, "POST", f"/api/v1/journeys/{jid}/agent/commands",
                   {"command": CMD_A, "requested_autonomy": "PLAN_ONLY"})
        mission = ""
        if cmd["status"] == 200:
            mission = str(((json.loads(cmd["body"]).get("mission") or {})).get("id") or "")
        if not mission:
            with contextlib.closing(sqlite3.connect(str(db), timeout=60)) as conn:
                row = conn.execute("SELECT id FROM journey_missions WHERE journey_id=? LIMIT 1",
                                   (jid,)).fetchone()
            mission = row[0] if row else ""
        assert mission, f"SETUP：拿不到真 mission ⇒ 没有续跑身份可绑：{cmd['status']} {cmd['body'][:200]}"

        key_a, key_b = f"plans.generate:o282A-{RUN_ID}-{idx}", f"plans.generate:o282B-{RUN_ID}-{idx}"
        cont = f"plans.generate:cont:{mission}"
        keys = [key_a, key_b, cont]
        pre_a = receipts(db, keys)          # 腿 A 之前：三把键都该是 absent（否则我量的不是那一发）
        plans_start = [r[0] for r in durable(db, "SELECT id FROM plan_versions WHERE journey_id=?"
                                                 " ORDER BY created_at, id", (jid,))]
        leg_a = http(p1, "POST", f"/api/v1/journeys/{jid}/plans/generate",
                     {"mission_id": mission, "candidate_count": 3},
                     headers={"Idempotency-Key": f"o282A-{RUN_ID}-{idx}"})
        before = receipts(db, keys)
        plans_after_a = [r[0] for r in durable(db, "SELECT id FROM plan_versions WHERE journey_id=?"
                                                   " ORDER BY created_at, id", (jid,))]
        leg_b = http(p2, "POST", f"/api/v1/journeys/{jid}/plans/generate",
                     {"mission_id": mission, "candidate_count": 3},
                     headers={"Idempotency-Key": f"o282B-{RUN_ID}-{idx}"})
        after = receipts(db, keys)
        plans_after_b = [r[0] for r in durable(db, "SELECT id FROM plan_versions WHERE journey_id=?"
                                                  " ORDER BY created_at, id", (jid,))]

        # 臂 C：同一 mission 的两发**同时**进来（一号与二号进程各一发，各自新客户端键）。
        # 这是"B 在 A 还占着 NULL 时到达"的那一型：要么等到 A 的答案并回放，要么吃现成 409。
        cmd2 = http(p1, "POST", f"/api/v1/journeys/{jid}/agent/commands",
                    {"command": CMD_A, "requested_autonomy": "PLAN_ONLY"})
        mission_c = str(((json.loads(cmd2["body"]).get("mission") or {}).get("id")) or "") if cmd2["status"] == 200 else ""
        race = None
        if mission_c:
            cont_c = f"plans.generate:cont:{mission_c}"
            kc1, kc2 = f"plans.generate:o282C1-{RUN_ID}-{idx}", f"plans.generate:o282C2-{RUN_ID}-{idx}"
            out: dict[int, dict] = {}

            def fire(slot: int, port: int, ckey: str) -> None:
                out[slot] = http(port, "POST", f"/api/v1/journeys/{jid}/plans/generate",
                                 {"mission_id": mission_c, "candidate_count": 3},
                                 headers={"Idempotency-Key": ckey})

            th = [threading.Thread(target=fire, args=(1, p1, kc1)),
                  threading.Thread(target=fire, args=(2, p2, kc2))]
            for t in th:
                t.start()
            for t in th:
                t.join(timeout=180)
            rows = receipts(db, [kc1, kc2, cont_c])
            race = {"mission": mission_c, "legs": {str(s): {"status": out.get(s, {}).get("status"),
                                                            "ms": out.get(s, {}).get("ms"),
                                                            "body_head": (out.get(s, {}).get("body") or "")[:170]}
                                                   for s in (1, 2)},
                    "receipts": {k: rows[k][:2] for k in rows},
                    "cont_c_filled_by_exactly_one": rows[cont_c][0] == "filled"}

        a_keys = [key_a, cont]
        a_filled = sum(1 for k in a_keys if pre_a[k][0] != "filled" and before[k][0] == "filled")
        a_payloads_before = {k: before[k][2] for k in a_keys if before[k][0] == "filled"}
        bytes_survive = all(after[k][2] == v for k, v in a_payloads_before.items())
        b_own_filled = after[key_b][0] == "filled"
        a_new_plans = len(set(plans_after_a) - set(plans_start))
        b_new_plans = len(set(plans_after_b) - set(plans_after_a))
        b_body_is_a_body = (json.loads(leg_a["body"]) == json.loads(leg_b["body"])
                            if leg_a["body"].startswith("{") and leg_b["body"].startswith("{") else None)
        # 检测器自证：带外真改一次 A 的字节，我的 bytes_survive 必须看得见（否则它是恒真谓词）
        probe_key = next((k for k in a_keys if after[k][0] == "filled"), None)
        detector_sees = None
        if probe_key:
            with contextlib.closing(sqlite3.connect(str(db), timeout=60)) as conn:
                conn.execute("UPDATE idempotency_keys SET response_json=? WHERE key=?",
                             ('{"o282_detector_probe":true}', probe_key))
                conn.commit()
            seen = receipts(db, [probe_key])[probe_key][2] != a_payloads_before.get(probe_key)
            detector_sees = bool(seen)
            with contextlib.closing(sqlite3.connect(str(db), timeout=60)) as conn:
                conn.execute("UPDATE idempotency_keys SET response_json=? WHERE key=?",
                             (a_payloads_before[probe_key], probe_key))
                conn.commit()
        return {"state": state, "round": idx, "run_id": RUN_ID, "db": str(db),
                "tree_provenance_at_round": provenance,
                "db_bytes": db.stat().st_size, "ports": [p1, p2],
                "ownership": {"W1": r1, "W2": r2,
                              "distinct_pids": r1["pid"] != r2["pid"],
                              "ai_key_present_either": bool(r1["ai_key_present"] or r2["ai_key_present"])},
                "mission_via": "agent/commands" if cmd["status"] == 200 else "durable read-back",
                "agent_command_status": cmd["status"],
                "legs": {"A": {"port": p1, "pid": r1["pid"], "status": leg_a["status"],
                               "ms": leg_a["ms"], "body_head": leg_a["body"][:180]},
                         "B": {"port": p2, "pid": r2["pid"], "status": leg_b["status"],
                               "ms": leg_b["ms"], "body_head": leg_b["body"][:180]}},
                "readings": {"receipts_before_A": {k: pre_a[k][:2] for k in keys},
                             "receipts_before_B": {k: before[k][:2] for k in keys},
                             "receipts_after_B": {k: after[k][:2] for k in keys},
                             "A_filled": a_filled, "B_own_key_filled": b_own_filled,
                             "A_bytes_survive": bytes_survive if a_payloads_before else None,
                             "detector_selftest_sees_change": detector_sees,
                             "n_filled_keys_after_both": sum(1 for k in keys if after[k][0] == "filled")},
                "arm_C_same_mission_race": race}
    finally:
        for proc, fh in procs:
            with contextlib.suppress(Exception):
                proc.terminate()
                proc.wait(timeout=20)
            fh.close()
        for suffix in ("", "-wal", "-shm"):
            with contextlib.suppress(Exception):
                Path(str(db) + suffix).unlink()


def apply_mutation():
    before = MAIN.read_bytes()
    text = before.decode("utf-8")
    n = text.count(GUARD_ANCHOR)
    assert n == 1, f"SETUP：守卫锚点出现 {n} 次（必须正好 1）⇒ 中止，不猜位置"
    mutated = text.replace(GUARD_ANCHOR, UNGUARDED)
    hunks = [l for l in difflib.unified_diff(text.splitlines(), mutated.splitlines(), lineterm="")
             if l.startswith("@@")]
    MAIN.write_bytes(mutated.encode("utf-8"))
    after_bytes = MAIN.read_bytes()
    compile_ok = subprocess.run([PY, "-m", "py_compile", str(MAIN)], capture_output=True).returncode == 0
    return {"before_blob": blob_of(before), "before_blob_matches_landing": blob_of(before) == LANDING_MAIN_BLOB,
            "after_blob_40": blob_of(after_bytes), "hunks": len(hunks), "hunk_headers": hunks,
            "py_compile_ok": compile_ok,
            "removed_expression": "IdempotencyKey.response_json.is_(None)",
            "lines_delta": [len(text.splitlines()), len(mutated.splitlines())]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--json", required=True)
    args = ap.parse_args()
    original = MAIN.read_bytes()
    assert blob_of(original) == LANDING_MAIN_BLOB, (
        f"SETUP：落地代 main.py 当前 blob 不是判据那枚：{blob_of(original)}")
    data = {"what": "ORD-0282 rig：落地代 45b0a5e2 上两进程一次性库的守卫读数（两态）",
            "lane": "F 8ccd71d8", "run_id": RUN_ID,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "tree": {"exported_from": "GitHub tarball @45b0a5e281cae9c37715173afd3ac5778f309ca7",
                     "backend_cwd": str(BACKEND), "main_py_blob": blob_of(original),
                     "seam_symbol_present": "_fill_plan_generation_receipts" in original.decode("utf-8"),
                     "guard_line_present": GUARD_ANCHOR in original.decode("utf-8")},
            "states": {}}
    try:
        data["states"]["guard"] = {"mutation": "未突变（守卫在位）",
                                   "rounds": [one_round("guard", i) for i in range(1, args.rounds + 1)]}
        mut = apply_mutation()
        data["mutation_applied"] = mut
        assert mut["py_compile_ok"] and mut["hunks"] == 1, f"SETUP：突变体不合格 {mut}"
        data["states"]["mutant"] = {"mutation": mut,
                                    "rounds": [one_round("mutant", i) for i in range(1, args.rounds + 1)]}
    finally:
        MAIN.write_bytes(original)
        data["restore"] = {"restored_byte_exact": blob_of(MAIN.read_bytes()) == blob_of(original),
                           "blob": blob_of(MAIN.read_bytes())}
    Path(args.json).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8",
                               newline="\n")
    print(json.dumps({"run_id": RUN_ID, "restore": data["restore"],
                      "mutation": data.get("mutation_applied"),
                      "per_round": {s: [{"A_filled": r["readings"]["A_filled"],
                                         "B_own_filled": r["readings"]["B_own_key_filled"],
                                         "A_bytes_survive": r["readings"]["A_bytes_survive"],
                                         "detector_sees": r["readings"]["detector_selftest_sees_change"],
                                         "A_status": r["legs"]["A"]["status"],
                                         "B_status": r["legs"]["B"]["status"],
                                         "C_statuses": [x["status"] for x in
                                                        (r.get("arm_C_same_mission_race") or {}).get("legs", {}).values()],
                                         "C_cont_filled_by_one": (r.get("arm_C_same_mission_race") or {}).get("cont_c_filled_by_exactly_one")}
                                        for r in data["states"][s]["rounds"]]
                                    for s in data["states"]}}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
