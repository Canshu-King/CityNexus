"""ORD-0553 r3 -- drive the sealed trip forward on MY probe store so an activity reaches ARRIVED.

Why: the commander reads a standalone ARRIVED and a standalone COMPLETED on /v8/authoritative, and the
store copy I measured has no activity at ARRIVED at all (statuses: COMPLETED x3, ACTIVE x1, PLANNED x2).
A reading of a state that does not exist proves nothing about that state, so the transition the panel's
own button issues is issued here -- POST /api/v1/journeys/{id}/activities/{aid}/{step}, the call in
frontend/src/api/v12Authoritative.ts -- against a private copy of the seed. The shared preview DB and
every other lane's store are never touched.

Nothing is hidden: every step is recorded with its HTTP status and the activity status the server then
answers, including the refusals.
"""
import json
import subprocess
import sys
import urllib.error
import urllib.request

PORT = 8752
JID = "22222222-2222-4222-8222-222222222222"
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(path):
    with op.open("http://127.0.0.1:%d/api/v1%s" % (PORT, path), timeout=20) as r:
        return json.loads(r.read())


def post(path):
    req = urllib.request.Request("http://127.0.0.1:%d/api/v1%s" % (PORT, path), method="POST",
                                headers={"Content-Type": "application/json"})
    try:
        with op.open(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body[:200].decode("utf-8", "replace")}


def owners(port):
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True).stdout
    return sorted({l.split()[-1] for l in out.splitlines()
                   if len(l.split()) >= 5 and l.split()[3].upper() == "LISTENING"
                   and l.split()[1].endswith(":%d" % port)})


plan = [p for p in get("/journeys/%s/plans" % JID) if p.get("is_current") or p.get("status") == "ACTIVE"]
if not plan:
    print("ABORT: no ACTIVE plan version on the probe store", file=sys.stderr)
    sys.exit(1)
acts = plan[0]["activities"]
print(json.dumps({"store_port": PORT, "netstat_owners": owners(PORT),
                  "plan_version_id": plan[0]["id"], "version_no": plan[0]["version_no"],
                  "activities_before": [[a["sequence_no"], a["title"], a["status"]] for a in acts]},
                 ensure_ascii=False, indent=1))

steps = []
for a in acts:
    for step in ("depart", "arrive"):
        code, body = post("/journeys/%s/activities/%s/%s" % (JID, a["id"], step))
        detail = body.get("error", {}).get("code") if isinstance(body, dict) and code >= 400 else None
        steps.append({"sequence_no": a["sequence_no"], "title": a["title"], "step": step,
                      "http_status": code, "server_code": detail,
                      "now_state": (body.get("context", {}).get("execution", {}) or {}).get("now_state")
                      if code < 400 else None})
        if code >= 400:
            break
print(json.dumps(steps, ensure_ascii=False, indent=1))

after = [p for p in get("/journeys/%s/plans" % JID) if p["id"] == plan[0]["id"]][0]["activities"]
twin = get("/journeys/%s/twin" % JID)
print(json.dumps({"activities_after": [[a["sequence_no"], a["title"], a["status"]] for a in after],
                  "twin_execution": twin.get("context", {}).get("execution")}, ensure_ascii=False, indent=1))
