"""ORD-0282 主面（seam 面）：落地代 Phase B 那个回填守卫，两个真进程 + 一座一次性库 + 带外读数。

判据 ② 的形状就是"两进程 + 带外 rowcount"，所以这一面**不**走 HTTP。HTTP 那一面我另跑过一份
（腿 B 在占位门前就被挡回去，根本到不了回填 ⇒ 那一面 NO_FLIP，见 o282_rig_readings.json）。
落地代没有候选代那枚 `_fill_plan_generation_receipts`（实测符号 0 命中），回填写在 Phase B 里面，
所以两个角色是：
  A = claim_and_fill：产品自己的 `_claim_plan_generation` 占位 + `_execute_plan_generation_claimed` 生成并回填；
  B = re_enter_phase_B：带**同一组键**再进一次 Phase B（落地代没有"只回填"的入口，这是最贴的形制）。
守卫在位 ⇒ B 填到 0 行、抛现成那句具名 409、A 的字节逐字存活；拆掉 ⇒ B 覆盖别人的回执。
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import o282_rig as R  # noqa: E402  复用已经跑通的起进程/带外读数/突变工具

CHILD = R.HARNESS / "_o282_seam_role.py"
RUN_ID = f"O282S-{datetime.now():%d%H%M}-{uuid.uuid4().hex[:6]}"
CHILD_SRC = '''
"""One ORD-0282 seam-face role, in its own OS process, against the exported landed tree."""
import json, os, sys
from datetime import datetime, timezone

db_url, role, journey_id, mission, transport = sys.argv[1:6]
os.environ["CITYNEXUS_DATABASE_URL"] = db_url
os.environ["CITYNEXUS_AI_ENABLED"] = "false"
for _n in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_LIVE_VALHALLA_URL"):
    os.environ.pop(_n, None)

from sqlalchemy import select

from app.commerce.idempotency import canonical_request_signature
from app.db.models import Journey
from app.db.session import SessionLocal, engine
from app.main import _claim_plan_generation, _execute_plan_generation_claimed
from app.schemas import GeneratePlansRequest

keys = [f"plans.generate:{transport}", f"plans.generate:cont:{mission}"]
now = datetime.now(timezone.utc)
out = {"role": role, "pid": os.getpid(), "ppid": os.getppid(), "keys": keys,
       "resolved_db_file": str(engine.url.database)}
with SessionLocal() as s:
    journey = s.scalars(select(Journey).where(Journey.id == journey_id)).one()
    req = GeneratePlansRequest(candidate_count=3, mission_id=mission)
    sig = canonical_request_signature({"journey_id": str(journey_id), "mission_id": mission,
                                       "planning_mode": journey.planning_mode,
                                       "candidate_count": 3, "place_ids": None})
    if role == "claim_and_fill":
        raced = _claim_plan_generation(keys, sig, s, now)
        out["claim_returned_replay"] = raced is not None
    try:
        answer = _execute_plan_generation_claimed(journey, req, keys, f"cont:{mission}", now)
        out["refused"] = None
        out["answer_shape"] = sorted(answer.keys())
    except Exception as exc:  # noqa: BLE001 - the refusal IS the reading
        out["refused"] = {"type": type(exc).__name__,
                          "status": getattr(exc, "status_code", None),
                          "detail": str(getattr(exc, "detail", exc))[:200]}
print(json.dumps(out, ensure_ascii=False), flush=True)
'''


def child_env(db_url: str) -> dict:
    e = dict(os.environ)
    for n in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_AI_ENABLED",
              "CITYNEXUS_LIVE_VALHALLA_URL"):
        e.pop(n, None)
    e["CITYNEXUS_DATABASE_URL"] = db_url
    e["PYTHONPATH"] = str(R.BACKEND)
    return e


def role_child(role: str, db_url: str, jid: str, mission: str, transport: str) -> dict:
    p = subprocess.run([R.PY, "-X", "utf8", str(CHILD), db_url, role, jid, mission, transport],
                       cwd=str(R.BACKEND), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=child_env(db_url), timeout=900)
    line = next((l for l in reversed((p.stdout or "").splitlines()) if l.startswith("{")), "")
    if not line:
        raise RuntimeError(f"SETUP：角色 {role} 没给读数 rc={p.returncode} "
                           f"stderr_tail={(p.stderr or '')[-500:]}")
    d = json.loads(line)
    d["child_rc"] = p.returncode
    d["stderr_tail"] = (p.stderr or "").strip().splitlines()[-3:]
    return d


def build_stage(db_url: str, db: Path, idx: int) -> dict:
    """舞台走产品自己的 HTTP 面（旅行者的建旅程与 mission 都不由我手写行）。"""
    R.seed_stage(db_url)
    port = R.free_port()
    log = R.HARNESS / f"_o282seam_{RUN_ID}_r{idx}_stage.log"
    proc, fh = R.spawn(port, db_url, log)
    try:
        rep = R.wait_serving(proc, port, log, db)
        own = R.ownership("stage", proc, port, rep, db)
        trav = json.loads(R.http(port, "POST", "/api/v1/travelers",
                                 {"display_name": f"o282s-{RUN_ID}",
                                  "timezone": "Asia/Shanghai"})["body"])
        with contextlib.closing(sqlite3.connect(str(db), timeout=60)) as conn:
            stage = conn.execute("SELECT city_code, timezone, start_at, end_at, planning_mode,"
                                 " budget_amount_minor, budget_currency FROM journeys"
                                 " WHERE city_code=? ORDER BY created_at LIMIT 1",
                                 (R.DEMO_CITY,)).fetchone()
        assert stage, f"SETUP：{R.DEMO_CITY} 没有可抄的演示旅程"
        jy = json.loads(R.http(port, "POST", "/api/v1/journeys", {
            "traveler_id": trav["id"], "title": f"o282s-{RUN_ID}-{idx}",
            "city_code": stage[0], "timezone": stage[1], "start_at": stage[2], "end_at": stage[3],
            "planning_mode": stage[4],
            "budget": {"amount_minor": stage[5], "currency": stage[6]}})["body"])
        jid = jy["id"]
        cmd = R.http(port, "POST", f"/api/v1/journeys/{jid}/agent/commands",
                     {"command": R.CMD_A, "requested_autonomy": "PLAN_ONLY"})
        mission = str(((json.loads(cmd["body"]).get("mission") or {}).get("id")) or "")
        assert mission, f"SETUP：拿不到真 mission rc={cmd['status']} {cmd['body'][:200]}"
    finally:
        with contextlib.suppress(Exception):
            proc.terminate()
            proc.wait(timeout=20)
        fh.close()
    with contextlib.suppress(Exception):
        R.durable(db, "PRAGMA wal_checkpoint(TRUNCATE)")   # 写者被强停后先收回主文件，后续带外读才稳
    return {"ownership": own, "journey_id": jid, "mission": mission}


def one_round(state: str, idx: int) -> dict:
    src = R.MAIN.read_text(encoding="utf-8")
    provenance = {"main_blob": R.blob_of(R.MAIN.read_bytes()),
                  "guard_hits": src.count(R.GUARD_ANCHOR),
                  "unguarded_hits": src.count(R.UNGUARDED),
                  "seam_symbol": "_fill_plan_generation_receipts" in src}
    db = R.HARNESS / f"_o282seam_{RUN_ID}_{state}_r{idx}.db"
    for suf in ("", "-wal", "-shm"):
        with contextlib.suppress(Exception):
            Path(str(db) + suf).unlink()
    db_url = f"sqlite:///{db.as_posix()}"
    stage = build_stage(db_url, db, idx)
    jid, mission = stage["journey_id"], stage["mission"]
    transport = f"o282s-{RUN_ID}-{state}-{idx}"
    keys = [f"plans.generate:{transport}", f"plans.generate:cont:{mission}"]

    pre = R.receipts(db, keys)
    a = role_child("claim_and_fill", db_url, jid, mission, transport)
    after_a = R.receipts(db, keys)
    b = role_child("re_enter_phase_B", db_url, jid, mission, transport)
    after_b = R.receipts(db, keys)

    payloads_a = {k: after_a[k][2] for k in keys if after_a[k][0] == "filled"}
    survive = all(after_b[k][2] == v for k, v in payloads_a.items()) if payloads_a else None
    overwritten = sum(1 for k in keys if after_b[k][0] == "filled" and after_b[k][2] != after_a[k][2])
    detector = None
    probe = next(iter(payloads_a), None)
    if probe:
        with contextlib.closing(sqlite3.connect(str(db), timeout=60)) as conn:
            conn.execute("UPDATE idempotency_keys SET response_json=? WHERE key=?",
                         ('{"o282_seam_probe":1}', probe))
            conn.commit()
        detector = R.receipts(db, [probe])[probe][2] != payloads_a[probe]
        with contextlib.closing(sqlite3.connect(str(db), timeout=60)) as conn:
            conn.execute("UPDATE idempotency_keys SET response_json=? WHERE key=?",
                         (payloads_a[probe], probe))
            conn.commit()
    plans = R.durable(db, "SELECT count(*) FROM plan_versions WHERE journey_id=?", (jid,))[0][0]
    receipt_json_len = {k: (len(after_b[k][2] or "")) for k in keys}
    return {"state": state, "round": idx, "run_id": RUN_ID, "db": db.name,
            "db_bytes": db.stat().st_size if db.exists() else None,
            "tree_provenance_at_round": provenance, "stage": {k: v for k, v in stage.items()
                                                              if k != "ownership"},
            "stage_ownership": stage["ownership"],
            "pids": {"A": a["pid"], "B": b["pid"], "stage": stage["ownership"]["pid"],
                     "all_distinct": len({a["pid"], b["pid"], stage["ownership"]["pid"]}) == 3},
            "role_A": a, "role_B": b,
            "receipts_pre": {k: pre[k][:2] for k in keys},
            "receipts_after_A": {k: after_a[k][:2] for k in keys},
            "receipts_after_B": {k: after_b[k][:2] for k in keys},
            "readings": {"A_filled_rows": sum(1 for k in keys if after_a[k][0] == "filled"),
                         "B_refused_status": (b.get("refused") or {}).get("status"),
                         "B_refused_detail": (b.get("refused") or {}).get("detail"),
                         "B_overwritten_rows": overwritten,
                         "A_bytes_survive": survive,
                         "detector_selftest_sees_change": detector,
                         "plan_versions_after_both": plans,
                         "stored_json_len_after_B": receipt_json_len}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--json", required=True)
    args = ap.parse_args()
    CHILD.write_text(CHILD_SRC, encoding="utf-8", newline="\n")
    original = R.MAIN.read_bytes()
    assert R.blob_of(original) == R.LANDING_MAIN_BLOB, f"SETUP：树不对 {R.blob_of(original)}"
    data = {"what": "ORD-0282 seam 面：落地代 Phase B 回填守卫的两进程读数（守卫在位 / 拆掉）",
            "lane": "F 8ccd71d8", "run_id": RUN_ID,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "tree": {"tip": "45b0a5e281cae9c37715173afd3ac5778f309ca7",
                     "source": "GitHub tarball 独立导出（不是任何车道工作树，也不是包工头那棵 _qoder_wt_45b0a5e）",
                     "backend_cwd": str(R.BACKEND), "main_py_before": R.blob_of(original),
                     "seam_symbol_present_in_landed_tree":
                         b"_fill_plan_generation_receipts" in original,
                     "guard_site": "backend/app/main.py 里 Phase B 的 `.where(key=?, response_json IS NULL)`"},
            "roles": {"A": "claim_and_fill：产品的占位 + Phase B 生成回填",
                      "B": "re_enter_phase_B：同一组键再进一次 Phase B（落地代无『只回填』入口）"},
            "why_not_http": "HTTP 面我先量过一轮：腿 B 的占位在唯一索引上撞回，走回放门 ⇒ 到不了回填语句，"
                            "所以那一面两态同判（NO_FLIP）；本文件量的是判据 ② 要的那一面。",
            "states": {}}
    try:
        data["states"]["guard"] = {"rounds": [one_round("guard", i) for i in range(1, args.rounds + 1)]}
        m = R.apply_mutation()
        data["mutation_applied"] = m
        assert m["py_compile_ok"] and m["hunks"] == 1, f"SETUP：突变不合格 {m}"
        data["states"]["mutant"] = {"mutation": m,
                                    "rounds": [one_round("mutant", i) for i in range(1, args.rounds + 1)]}
    finally:
        R.MAIN.write_bytes(original)
        data["restore"] = {"byte_exact": R.blob_of(R.MAIN.read_bytes()) == R.blob_of(original),
                           "blob": R.blob_of(R.MAIN.read_bytes())}
    g = data["states"].get("guard", {}).get("rounds", [])
    mu = data["states"].get("mutant", {}).get("rounds", [])
    derived = {
        "guard_all_survive": bool(g) and all(r["readings"]["A_bytes_survive"] for r in g),
        "guard_all_refused_named_409": bool(g) and all(
            r["readings"]["B_refused_status"] == 409 and "incomplete" in (r["readings"]["B_refused_detail"] or "")
            for r in g),
        "mutant_all_overwrote": bool(mu) and all(r["readings"]["B_overwritten_rows"] >= 1 for r in mu),
        "detector_never_blind": all(r["readings"]["detector_selftest_sees_change"] is True
                                    for r in g + mu),
        "three_distinct_pids_every_round": all(r["pids"]["all_distinct"] for r in g + mu),
        "guard_only_flip": None}
    derived["guard_only_flip"] = (derived["guard_all_survive"] and derived["mutant_all_overwrote"]
                                  and derived["detector_never_blind"] and derived["guard_all_refused_named_409"])
    derived["K8_SEAM_ON_LANDED_GENERATION"] = (
        "FLIP_OBSERVED" if derived["guard_only_flip"] else
        "NOT_REPRODUCED" if (derived["detector_never_blind"] and not derived["guard_all_survive"]) else
        "NO_FLIP")
    data["derived"] = derived
    Path(args.json).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8",
                               newline="\n")
    print(json.dumps({"run_id": RUN_ID, "restore": data["restore"], "derived": derived,
                      "mutation": data.get("mutation_applied"),
                      "per_round": {s: [{"A_filled": r["readings"]["A_filled_rows"],
                                         "B_status": r["readings"]["B_refused_status"],
                                         "B_detail": (r["readings"]["B_refused_detail"] or "")[:40],
                                         "B_overwrote": r["readings"]["B_overwritten_rows"],
                                         "survive": r["readings"]["A_bytes_survive"],
                                         "detector": r["readings"]["detector_selftest_sees_change"],
                                         "plans": r["readings"]["plan_versions_after_both"],
                                         "blob": r["tree_provenance_at_round"]["main_blob"][:9],
                                         "pids3": r["pids"]["all_distinct"]}
                                        for r in data["states"][s]["rounds"]] for s in data["states"]}},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
