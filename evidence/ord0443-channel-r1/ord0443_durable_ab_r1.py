"""ORD-0443: read the wiring result off the durable side instead of the response body.

The A/B's own verdict came out false because I guessed at response field names; the product's state is
in its own sqlite, so this reads the two arm databases directly and names the rows: which tables grew
rows only when the channel was wired, whose text the mission stored, which compiler answered, and what
the agent run recorded as its outcome. No model call, no credential.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

LANE = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0443")
OUT = LANE / "ORD0443_DURABLE_AB.json"
TABLES = ["journey_missions", "agent_runs", "agent_run_steps", "events", "audit_logs"]


def read_arm(db: Path) -> dict:
    c = sqlite3.connect(db)
    out: dict = {"db": str(db)}
    for t in TABLES:
        out[f"rows_{t}"] = c.execute(f"select count(*) from {t}").fetchone()[0]
    m = c.execute("select id, user_text, status, compiler_provider_key, compiler_model_key,"
                  " allowed_action_classes_json, failure_reason from journey_missions limit 1").fetchone()
    out["mission"] = None if not m else {
        "id": m[0], "user_text_head": str(m[1])[:120], "status": m[2],
        "compiler_provider_key": m[3], "compiler_model_key": m[4],
        "allowed_action_classes": json.loads(m[5] or "[]"), "failure_reason": m[6]}
    r = c.execute("select id, provider_key, model_key, status, outcome, failure_reason"
                  " from agent_runs limit 1").fetchone()
    out["agent_run"] = None if not r else {
        "id": r[0], "provider_key": r[1], "model_key": r[2], "status": r[3],
        "outcome_head": str(r[4] or "")[:220], "failure_reason": r[5]}
    c.close()
    return out


def main() -> int:
    off, on = read_arm(LANE / "_ab_off.db"), read_arm(LANE / "_ab_on.db")
    report = {"off": off, "on": on,
              "durable_difference": {t: {"off": off["rows_" + t], "on": on["rows_" + t]} for t in TABLES
                                     if off["rows_" + t] != on["rows_" + t]},
              "verdict_channel_writes_product_state": bool(
                  on["rows_journey_missions"] and on["rows_agent_runs"]
                  and not off["rows_agent_runs"] and on["agent_run"]["outcome_head"].strip()),
              "open_gaps_measured": {
                  "mission_compiler_fell_back": on["mission"]["compiler_model_key"],
                  "agent_run_steps_rows_with_completed_run": on["rows_agent_run_steps"],
                  "events_rows_created_by_the_model_turn": on["rows_events"]}}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({"durable_difference": report["durable_difference"],
                      "agent_run": on["agent_run"], "open_gaps": report["open_gaps_measured"],
                      "verdict": report["verdict_channel_writes_product_state"]},
                     ensure_ascii=False, indent=1)[:1700])
    print("WROTE", OUT)
    return 0 if report["verdict_channel_writes_product_state"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
