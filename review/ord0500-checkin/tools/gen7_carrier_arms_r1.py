"""Per-arm statuses for the ORD-0500 carrier, read out of Playwright's own JSON reports.

The sweep runner prints one verdict line per face; a counter-example claim needs the arm names with
their individual statuses, and it must not be a list I typed.  One run per served face, one report
file per run.
"""
import json
import os
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
LABELS = ["base_tip", "candidate_o0500", "mutant_clientbool_ce2"]

out = {"tool": "gen7_carrier_arms_r1", "took_local": datetime.now().astimezone().isoformat(),
       "why": "gen7_carrier_r1 prints one verdict line per face; this is the per-arm table",
       "runs": []}
for label in LABELS:
    p = os.path.join(LANE, "run", "report_%s.json" % label)
    if not os.path.exists(p):
        out["runs"].append({"label": label, "ABORT": "REPORT_MISSING", "report": os.path.basename(p)})
        continue
    d = json.load(open(p, encoding="utf-8"))
    arms = []
    for suite in d.get("suites", []):
        for spec in suite.get("specs", []):
            for t in spec.get("tests", []):
                results = t.get("results", [])
                status = results[-1].get("status") if results else "NO_RESULT"
                msg = ""
                for r in results:
                    m = (r.get("error") or {}).get("message", "")
                    if "spec.ts ::" in m:
                        msg = next(l.strip() for l in m.splitlines() if "spec.ts ::" in l)
                        break
                arms.append({"arm": spec.get("title"), "status": status, "node_message": msg[:400]})
    stats = d.get("stats", {})
    out["runs"].append({"label": label, "report": os.path.basename(p),
                        "stats": {k: stats.get(k) for k in ("expected", "unexpected",
                                                            "flaky", "skipped")},
                        "arms": arms})
    print("## %s %s" % (label, out["runs"][-1]["stats"]))
    for a in arms:
        print("   %-8s %s" % (a["status"], str(a["arm"])[:76]))
        if a["node_message"]:
            print("        %s" % a["node_message"][:230])
path = os.path.join(LANE, "evidence", "gen7_carrier_arms_r1.json")
json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("WROTE " + path)
