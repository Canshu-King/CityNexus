"""ORD-0590 graft smoke proof: run against an exported tip tree, with and without the 5 candidate modules."""
import importlib
import json
import sys
from datetime import datetime, timezone

ARM = sys.argv[1]
out = {"arm": ARM}

try:
    m = importlib.import_module("app.execution.truth")
    out["import_truth"] = "OK"
except Exception as e:
    out["import_truth"] = "%s: %s" % (type(e).__name__, e)

# the tip's own execution package must still load next to the new files
for name in ["app.execution", "app.execution.clock", "app.execution.journey_twin",
             "app.execution.traveler_twin", "app.execution.location_scope",
             "app.execution.shared_walk", "app.execution.route_session_contract",
             "app.execution.departure_activation"]:
    try:
        importlib.import_module(name)
        out["import_" + name.split(".")[-1]] = "OK"
    except Exception as e:
        out["import_" + name.split(".")[-1]] = "%s: %s" % (type(e).__name__, e)

try:
    loc = importlib.import_module("app.execution.location_scope")
    out["location_scope_value"] = loc.PRIVATE_BUDDY_ROUTE_LOCATION_SOURCE
except Exception as e:
    out["location_scope_value"] = "ERR %s" % e

try:
    t = importlib.import_module("app.execution.truth")
    meta = {}
    rec = t.append_execution_truth(
        meta, kind=t.OPERATOR_CONFIRMED_EXECUTION, transition="EN_ROUTE",
        captured_at="2026-10-12T20:00:00+08:00", actor_type="operator", actor_id="op-1")
    out["truth_record_kind"] = rec["kind"]
    out["truth_history_len"] = len(meta["execution_truth_history"])
    try:
        t.append_execution_truth(meta, kind="MADE_UP_KIND", transition="X",
                                 captured_at="2026-10-12T20:00:00+08:00",
                                 actor_type="operator", actor_id="op-1")
        out["truth_rejects_bad_kind"] = "DID NOT RAISE"
    except ValueError as e:
        out["truth_rejects_bad_kind"] = "ValueError"
except Exception as e:
    out["truth_run"] = "%s: %s" % (type(e).__name__, e)

try:
    sw = importlib.import_module("app.execution.shared_walk")
    got = sw.parse_shared_walk_text(
        "meet at https://www.openstreetmap.org/node/1234567 then "
        "https://www.openstreetmap.org/way/7654321")
    out["shared_walk_parsed"] = [(o.osm_type, o.osm_id) for o in got]
    out["shared_walk_canonical"] = sw.canonical_osm_object_url("relation", "42")
    try:
        sw.parse_shared_walk_text("x" * 20000)
        out["shared_walk_oversize"] = "ACCEPTED"
    except sw.SharedWalkParseError:
        out["shared_walk_oversize"] = "rejected"
except Exception as e:
    out["shared_walk_run"] = "%s: %s" % (type(e).__name__, e)

try:
    rc = importlib.import_module("app.execution.route_session_contract")
    req = rc.RouteRequest(journey_id="j-1", origin_key="p-1", target_key="p-2",
                          target_activity_id=None, requested_mode="walk")
    fp1 = rc.route_request_fingerprint(req)
    fp2 = rc.route_request_fingerprint(req)
    out["rsc_fingerprint_stable"] = (fp1 == fp2)
    out["rsc_fingerprint_len"] = len(fp1)
    out["rsc_policy_versions"] = [rc.ROUTE_TRUTH_POLICY_VERSION, rc.ROUTE_PROVIDER_POLICY_VERSION]
except Exception as e:
    out["rsc_run"] = "%s: %s" % (type(e).__name__, e)

try:
    da = importlib.import_module("app.execution.departure_activation")
    now = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)
    proj = da.departure_activation_projection(
        {"target_activity_id": "a-1", "target_title": "Lecture", "must_leave_by": None,
         "state": "UNKNOWN"}, activity_status="PENDING", now=now)
    out["departure_state"] = proj.get("activation_state")
    out["departure_keys"] = sorted(proj.keys())
    fp = da.departure_cue_fingerprint(journey_id="j-1", activity_id="a-1",
                                       activation_state="DUE", readiness_state="READY")
    out["departure_fingerprint_len"] = len(fp)
except Exception as e:
    out["departure_run"] = "%s: %s" % (type(e).__name__, e)

print(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
