# ORD-0422 branch fixture. Reaches the screen states that no public door on this line can produce,
# and names them as such: the rows written here live only in this lane's private copy of the preview
# database, so a reading taken after this script is a READING OF THE PANEL, not evidence that a
# traveller can reach that state in production. Which door refuses instead is recorded separately.
#
#   proposal  -> a PRESENTED replan proposal row, which POST /api/v1/journeys/{id}/replans refuses to
#                create here (422 MOBILITY_DATA_UNAVAILABLE, no reachable routing provider on this box)
#   capability-> a stored capability with confirmed = 0, which POST
#                /api/v1/travelers/{id}/capabilities/confirm refuses to leave unconfirmed
#   nopolicy  -> removes the traveller's stored delegation policy row, the only way this screen's
#                policy prop is ever null
import json
import sqlite3
import sys
import urllib.request
import uuid

DB = "D:/moodle/_qoder_q_ord0422/q0422_private.db"
# The write bolt: this script may only touch this lane's private copy. The shared preview database is
# read-only to every lane, so the path is checked before the connection opens, not after.
assert "q0422_private" in DB and "_preview" not in DB, DB
API = "http://127.0.0.1:8734"
JOURNEY = "22222222-2222-4222-8222-222222222222"
TRAVELER = "11111111-1111-4111-8111-111111111111"
PLAN_VERSION = "55523d40-cafe-5bd2-b30a-de057ec7a839"
mode = sys.argv[1]

TABLES = ("replan_proposals", "traveler_capabilities", "traveler_agent_policies", "plan_versions")
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
before = {t: con.execute("select count(*) from %s" % t).fetchone()[0]
          for t in TABLES}


def door(path):
    with urllib.request.urlopen(API + path, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


if mode == "proposal":
    diff = {
        "removed": ["09:30 Harbour Market walk"],
        "added": ["11:10 Riverside Museum slot"],
        "cost_delta_minor": -1200,
        "travel_delta_min": 8,
        "verified_evidence": {
            "baseline_plan_evidence": {"snapshot_id": "snap-baseline-01"},
            "incident_recovery_evidence": {
                "route_provenance": "frozen_matrix", "source_provider": "citynexus-mobility",
                "mobility_snapshot": {"snapshot_id": "snap-mobility-07",
                                      "source_provider": "citynexus-mobility", "degraded": False},
            },
            "impact_resolution": {"semantic_reason": "TRAFFIC_DELAY",
                                  "semantic_explanation": "a simulated delay moved the morning slot"},
        },
    }
    con.execute(
        "insert into plan_versions (id, journey_id, version_no, planning_mode, status, source,"
        " parent_plan_version_id, total_cost_minor, currency, estimated_duration_min, utility_score,"
        " score_breakdown_json, explanation_json, mobility_snapshot_id, mobility_evidence_json,"
        " created_at) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (proposed := str(uuid.uuid4()), JOURNEY, 2, "balanced", "CANDIDATE", "REPLAN", PLAN_VERSION,
         35800, "CNY", 578, 0.91, json.dumps({"cost": -1200}),
         json.dumps({"reason": "fixture: a candidate produced by the deterministic gate"}),
         "snap-mobility-07", json.dumps({"snapshot_id": "snap-mobility-07"}), "2026-09-29T03:40:00Z"))
    con.execute(
        "insert into replan_proposals (id, journey_id, trigger_event_id, base_plan_version_id,"
        " proposed_plan_version_id, status, hard_constraints_passed, locked_commitments_preserved,"
        " utility_score, score_breakdown_json, diff_json, explanation_json, created_at, decided_at)"
        " values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), JOURNEY, None, PLAN_VERSION, proposed, "PRESENTED", 1, 1, 0.62,
         json.dumps({"cost": -1200}), json.dumps(diff),
         json.dumps({"impact_model": "deterministic-gate-v1", "impact_provider": "citynexus-solver"}),
         "2026-09-29T03:40:00Z", None))
    con.commit()
    printed = [p for p in door("/api/v1/journeys/%s/replans" % JOURNEY)
               if p["status"] == "PRESENTED"]
    verdict = "the read door serves the row, so the panel's proposal branch renders" if printed \
        else "the read door did not serve the row"
elif mode == "capability":
    for code, cls, sev, conf in (("STEP_FREE_REQUIRED", "HARD_ACCESSIBILITY_NEED", "HARD", 1),
                                 ("QUIET_ENVIRONMENT", "SOFT_PREFERENCE", "SOFT", 0)):
        con.execute(
            "insert into traveler_capabilities (id, traveler_id, journey_id, code, capability_class,"
            " severity, params_json, scope, source, provenance, explicit, confirmed, active,"
            " created_at, updated_at, confirmed_at) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), TRAVELER, None, code, cls, sev, "{}", "TRAVELER",
             "USER_CONFIRMED" if conf else "USER_STATED", "USER_STATED", 1, conf, 1,
             "2026-09-29T03:40:00Z", "2026-09-29T03:40:00Z",
             "2026-09-29T03:40:00Z" if conf else None))
    con.commit()
    twin = door("/api/v1/journeys/%s/experience" % JOURNEY).get("traveler_twin", {})
    stored = twin.get("explicit_capabilities", [])
    printed = [{"code": c["code"], "severity": c["severity"], "confirmed": c["confirmed"]}
               for c in stored]
    verdict = "the twin payload carries a confirmed=false row, which the /confirm door refuses to leave" \
        if any(c["confirmed"] is False for c in stored) else "no unconfirmed row in the payload"
elif mode == "nopolicy":
    con.execute("delete from traveler_agent_policies")
    con.commit()
    try:
        answer = door("/api/v1/travelers/%s/agent-policy" % TRAVELER)
    except Exception as exc:
        answer = str(exc)[:120]
    after_delete = con.execute("select count(*) from traveler_agent_policies").fetchone()[0]
    printed = {"policy_door_answer": answer, "rows_right_after_delete": after_delete}
    verdict = ("deleting the stored row did not make the policy prop null: the read door answered and "
               "the row count after the call is %s"
               % con.execute("select count(*) from traveler_agent_policies").fetchone()[0])
else:
    raise SystemExit("mode must be proposal | capability | nopolicy")

after = {t: con.execute("select count(*) from %s" % t).fetchone()[0]
         for t in TABLES}
out = {"mode": mode, "database": DB, "rows_before": before, "rows_after": after,
       "door_reading": printed, "verdict": verdict}
print(json.dumps(out, ensure_ascii=False, indent=1))
