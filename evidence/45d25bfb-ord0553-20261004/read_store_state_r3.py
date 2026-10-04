"""ORD-0553 r3 -- read the probe store's execution state as it now stands (no writes).

The screen can only be judged against the state it is showing: the ARRIVED row the commander names has to
be present in the store the bundle is served from, or a green reading proves nothing.  This prints the
activity statuses and the twin's own now_state/next_state from the same port the statics proxy to.
"""
import json
import subprocess
import urllib.request

PORT = 8752
JID = "22222222-2222-4222-8222-222222222222"
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(path):
    with op.open("http://127.0.0.1:%d/api/v1%s" % (PORT, path), timeout=20) as r:
        return json.loads(r.read())


def owners(port):
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True).stdout
    return sorted({l.split()[-1] for l in out.splitlines()
                   if len(l.split()) >= 5 and l.split()[3].upper() == "LISTENING"
                   and l.split()[1].endswith(":%d" % port)})


plans = get("/journeys/%s/plans" % JID)
current = [p for p in plans if p.get("is_current")] or [p for p in plans if p.get("status") == "ACTIVE"]
twin = get("/journeys/%s/twin" % JID)["context"]["execution"]
print(json.dumps({
    "backend_port": PORT, "netstat_listening_owners": owners(PORT),
    "journey_id": JID, "plan_versions_listed": len(plans),
    "current_version_no": current[0]["version_no"], "current_version_id": current[0]["id"],
    "activity_statuses": [[a["sequence_no"], a["title"], a["status"]] for a in current[0]["activities"]],
    "twin_now_title": twin["now"]["title"], "twin_now_state": twin["now_state"],
    "twin_next_title": twin["next"]["title"] if twin.get("next") else None,
    "twin_next_state": twin["next_state"],
    "statuses_present_on_screen": sorted({a["status"] for a in current[0]["activities"]} | {twin["now_state"]}),
}, ensure_ascii=False, indent=1))
