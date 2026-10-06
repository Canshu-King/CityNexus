"""dsh_arm_streak.py — a repeatable DSH-driven arm over the CityNexus agent surface.

NOT the fleet ruler. The shared instrument (`evidence/0212/gate_streak_v2.py`) cannot
emit a receipt today: it references `PENDING_CLEANUP` at lines 468 and 664 and the name
is never defined anywhere in the file, so any run dies before the document is written.
That instrument belongs to the commander and its code path must not be rewritten by a
lane, so this runner exists beside it and says so in its own receipt.

Per run it does, serially, against a lane-owned throwaway DB:
  seed -> boot candidate backend -> build ACTIVE plan -> one headless DSH turn that must
  inspect, propose, accept and re-inspect -> read the DATABASE, not the model's prose.

Every verdict is computed from rows and log lines; nothing is written as a literal.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

LANE = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0212")
CAND = Path(os.environ.get("DSH_ARM_TREE", r"D:\moodle\_qoder_dsh_listreplans_20260929\wt"))
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
DSH_BIN = Path(os.path.expanduser("~")) / r".dsh\profiles\node_modules\@deepseek-ai\dsh\lib\bin.js"
PORT = 8513
BASE = f"http://127.0.0.1:{PORT}"
JOURNEY = "22222222-2222-4222-8222-222222222222"
TAG = os.environ.get("DSH_ARM_TAG", uuid.uuid4().hex[:8])
RUNS = int(os.environ.get("DSH_ARM_RUNS", "5"))
DB_PATH = None  # set per run; read by make_event()
PREDICATES = ["P0_event_written_into_my_own_db", "P1_single_active_before_after",
              "P2_active_flipped", "P3_new_proposal_accepted", "P4_no_booking_or_cancel",
              "P5_dsh_exit_zero", "P6_full_loop_hit", "P7_policy_actually_assisted_auto",
              "P8_started_from_advisory"]

TASK = (
    "你只能使用名字以 mcp__citynexus__ 开头的工具。目标：真的落地一次改判。"
    "步骤：1) 调 inspect_journey（journey_id={jid}，request_id 用新 uuid）记下 ACTIVE 计划版本 id；"
    "2) 调 request_replan（同一个 journey_id，trigger_event_id={eid}，request_id 用新 uuid），"
    "抄下返回的 decision 原文和 proposal id；3) 调 accept_replan（用第 2 步的 proposal id、"
    "同一个 journey_id、新 uuid 作 request_id），抄下 decision 原文；4) 再调一次 inspect_journey，"
    "报告 ACTIVE 版本 id 有没有变。禁止调用 list_replans。最后用不超过八行中文汇报，每步抄 decision 原文。"
)


def sh(cmd, env=None, timeout=600, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, timeout=timeout, cwd=cwd)


def db_state(path):
    c = sqlite3.connect(path)
    try:
        active = [r[0] for r in c.execute("select id from plan_versions where status='ACTIVE'").fetchall()]
        accepted = c.execute("select count(*) from replan_proposals where status='ACCEPTED'").fetchone()[0]
        events = [r[0] for r in c.execute("select id from events").fetchall()]
        bookings = c.execute("select count(*) from bookings").fetchone()[0]
    finally:
        c.close()
    return {"active_ids": active, "accepted": accepted, "events": events, "bookings": bookings}


def boot(db_path, log_path):
    # Preflight: this arm talks to a port it must own. An orphan from an earlier probe
    # answered on :8513 once (measured 09-29) and P0 caught it; refuse up front instead.
    busy = listener_pid()
    if busy:
        raise RuntimeError(f"port {PORT} already LISTENING on pid {busy} — sweep it first")
    env = {**os.environ, "PYTHONPATH": ".",
           "CITYNEXUS_DATABASE_URL": "sqlite:///" + str(db_path).replace("\\", "/")}
    p = subprocess.Popen([str(PY), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                          "--port", str(PORT)],
                         cwd=str(CAND / "backend"), env=env,
                         stdout=open(log_path, "w", encoding="utf-8"), stderr=subprocess.STDOUT)
    for _ in range(60):
        try:
            import httpx
            if httpx.get(BASE + "/api/v1/health", timeout=2).status_code == 200:
                return p
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("backend never became ready")


def listener_pid():
    out = sh(["netstat", "-ano"]).stdout
    for line in out.splitlines():
        if f"127.0.0.1:{PORT}" in line and "LISTENING" in line:
            return line.split()[-1]
    return None


def make_event():
    """Create a CLOSURE event over an activity in the ACTIVE plan, the same shape the
    product's own gate helper uses. Returns (event_id, activity_id) or (None, reason)."""
    import httpx

    c = sqlite3.connect(DB_PATH)
    try:
        plan = c.execute("select id from plan_versions where status='ACTIVE'").fetchone()
        if not plan:
            return None, "no ACTIVE plan"
        acts = [r for r in c.execute("select id, title from activities where plan_version_id=? order by start_at",
                                     (plan[0],)).fetchall()]
    finally:
        c.close()
    # Same preference the fleet ladder uses (its h4/h10 scenario builder, a script that is no
    # longer in this tree): the flagship
    # scenario is the Tech Art Center closure. The zero-budget policy the ruler installs
    # (cost delta / loss / drift all 0) legitimately refuses a *costly* replan, so
    # choosing an arbitrary activity measures the gate, not the arm.
    ordered = ([a for a in acts if "Tech Art" in (a[1] or "")]
               + [a for a in acts if "Tech Art" not in (a[1] or "")])
    for act_id, title in ordered:
        r = httpx.post(f"{BASE}/api/v1/journeys/{JOURNEY}/events", json={
            "event_type": "CLOSURE", "severity": "MAJOR", "affected_activity_id": act_id,
            "occurred_at": "2026-10-10T13:25:00+08:00", "payload": {"reason": "dsh arm streak"},
            "provenance": "SIMULATED"}, timeout=30)
        if r.status_code == 201:
            return r.json().get("id") or r.json().get("event", {}).get("id"), act_id
    return None, f"every activity rejected (tried {len(acts)})"


TRAVELER = "11111111-1111-4111-8111-111111111111"


def set_policy():
    """Mirror the fleet ruler's own per-run policy step (its `set_policy` equivalent, in a ruler
    script that is no longer in this tree):
    a freshly seeded traveller is ADVISORY, so `accept_replan` correctly answers
    REQUIRE_CONFIRMATION and mutates nothing. Recording before/after keeps that
    honest — the arm asks for auto-accept, it does not fake a confirmation."""
    import httpx

    before = httpx.get(f"{BASE}/api/v1/travelers/{TRAVELER}/agent-policy", timeout=30).json()
    httpx.put(f"{BASE}/api/v1/travelers/{TRAVELER}/agent-policy", json={
        "mode": "ASSISTED", "auto_accept_replan": True,
        "max_auto_replan_cost_delta_minor": 0, "max_auto_loss_minor": 0,
        "max_auto_schedule_drift_min": 0, "allow_auto_commitment_management": False,
    }, timeout=30)
    after = httpx.get(f"{BASE}/api/v1/travelers/{TRAVELER}/agent-policy", timeout=30).json()
    keep = ("mode", "auto_accept_replan", "version")
    return {"before": {k: before.get(k) for k in keep}, "after": {k: after.get(k) for k in keep}}


def one_run(i):
    global DB_PATH
    db = LANE / f"_dsharm_{TAG}_{i}.db"
    DB_PATH = db
    for suffix in ("", "-wal", "-shm"):
        Path(str(db) + suffix).unlink(missing_ok=True)
    seed_env = {**os.environ, "CITYNEXUS_DATABASE_URL": "sqlite:///" + str(db).replace("\\", "/"),
                "LANE_BACKEND_ROOT": str(CAND / "backend")}
    s = sh([str(PY), str(LANE / "seed_lane_db.py")], env=seed_env, timeout=300)
    if s.returncode != 0:
        return {"run": i, "fatal": "seed", "tail": (s.stderr or s.stdout)[-400:]}

    log = LANE / f"_dsharm_{TAG}_{i}_backend.log"
    proc = boot(db, log)
    try:
        b = sh([str(PY), str(LANE / "build_active_plan.py")], timeout=420)
        policy = set_policy()
        event_id, activity = make_event()
        before = db_state(db)
        # Identity proof: the event I created over HTTP must be readable from MY file.
        # A foreign backend answering this port could not have written into it.
        landed = bool(event_id) and event_id in [e for e in before["events"]]
        if not (landed and len(before["active_ids"]) == 1):
            return {"run": i, "fatal": "precondition", "event_id": event_id,
                    "activity": activity, "landed_in_my_db": landed,
                    "build_rc": b.returncode, "before": before,
                    "tail": (b.stderr or b.stdout)[-300:]}

        patch = LANE / f"_dsharm_{TAG}_{i}_mcp.yml"
        patch.write_text(
            "- insert:\n    - id: mcp-citynexus\n      name: '@deepseek-ai/dsh-mcp-client'\n"
            "      config:\n        serverName: citynexus\n        transport: stdio\n"
            f"        command: '{PY}'\n        args: ['-m', 'citynexus_mcp.server', '--v2']\n"
            f"        cwd: '{CAND}\\agent-mcp'\n        env:\n"
            f"          PYTHONPATH: '{CAND}\\agent-mcp'\n"
            f"          CITYNEXUS_API_BASE_URL: '{BASE}'\n"
            "        toolCallTimeoutMs: 120000\n        failOnStartupError: true\n",
            encoding="utf-8", newline="\n")

        t0 = time.time()
        r = sh(["node", str(DSH_BIN), "--profile", "headless", "--patch", str(patch),
                TASK.format(jid=JOURNEY, eid=event_id)], timeout=900)
        wall = round(time.time() - t0, 1)
        wire = log.read_text(encoding="utf-8", errors="replace")
        hits = re.findall(r"POST /api/v1/agent/tools/([a-z_]+)", wire)
        after = db_state(db)
        flips = before["active_ids"] != after["active_ids"]
        return {
            "run": i, "listener_pid": listener_pid(), "my_child_pid": proc.pid,
            "event_id": event_id, "dsh_rc": r.returncode, "wall_s": wall,
            "policy": policy,
            "tools_hit": hits, "counts": {t: hits.count(t) for t in sorted(set(hits))},
            "before": before, "after": after,
            "P0_event_written_into_my_own_db": landed,
            "P1_single_active_before_after": len(before["active_ids"]) == 1 and len(after["active_ids"]) == 1,
            "P2_active_flipped": flips,
            "P3_new_proposal_accepted": after["accepted"] == before["accepted"] + 1,
            "P4_no_booking_or_cancel": not [h for h in hits if h in ("create_booking", "cancel_refundable_booking")],
            "P5_dsh_exit_zero": r.returncode == 0,
            "P6_full_loop_hit": all(t in hits for t in ("inspect_journey", "request_replan", "accept_replan")),
            "P7_policy_actually_assisted_auto": (policy.get("after") or {}).get("mode") == "ASSISTED"
            and bool((policy.get("after") or {}).get("auto_accept_replan")),
            "P8_started_from_advisory": (policy.get("before") or {}).get("mode") == "ADVISORY",
            "answer_tail": (r.stdout or "")[-260:],
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except Exception:
            proc.kill()


def main():
    runs = [one_run(i) for i in range(1, RUNS + 1)]
    preds = PREDICATES
    def is_green(r):
        return all(bool(r.get(k)) for k in preds)
    green = [r for r in runs if is_green(r)]
    streak = 0
    for r in runs:
        if not is_green(r):
            break
        streak += 1
    doc = {
        "instrument": "dsh_arm_streak.py (lane runner, NOT the fleet ruler)",
        "fleet_ruler_status": "BROKEN: gate_streak_v2.py:468 and :664 use undefined PENDING_CLEANUP",
        "tag": TAG, "candidate": str(CAND), "port": PORT,
        "predicates": preds,
        "runs_requested": RUNS, "runs_green": len(green),
        "consecutive_from_first": streak,
        "runs": runs,
    }
    out = LANE / f"DSH_ARM_STREAK_{TAG}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({k: doc[k] for k in ("instrument", "tag", "predicates", "runs_requested",
                                          "runs_green", "consecutive_from_first")}, ensure_ascii=False))
    for r in runs:
        print("run", r["run"], "green" if is_green(r) else "RED",
              "|", r.get("counts") or r.get("fatal"), "| wall", r.get("wall_s"), "s")
    return 0 if doc["runs_green"] == RUNS else 1


if __name__ == "__main__":
    raise SystemExit(main())
