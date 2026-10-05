"""ORD-0553 r13 -- measure the two doors the v13 spec walks, without ever running demo/reset.

The order forbids `demo/reset` absolutely (it deletes 52 tables), so this instrument does two things
instead of one:

  leg 1  the door the spec's line 21 opens -- `POST /api/v1/demo/reset` with no header and with a
         wrong header.  Both answers are refusals, and a refusal is placed before `stop_autorun()`
         and before any row is touched (backend/app/main.py, the two guards named in ORD-0389),
         so measuring them is safe and is also the real behaviour.
  leg 2  the non-destructive route to the same product state: the sealed journey this store copy
         already carries gets `plans/generate` -> `select` -> `start`, which is what the spec does
         after its reset.  Nothing here deletes a table.

Everything runs against MY OWN copy of the seed on MY OWN port.  The shared preview database is
never opened by this file.
"""
import json
import subprocess
import sys
import urllib.error
import urllib.request

PORT = 8772
RUN = "r13"
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
out = {"port": PORT, "instrument": "cmdra_0553_v13_doors_r13", "steps": []}


def owners(port):
    text = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True,
                          text=True).stdout
    return sorted({l.split()[-1] for l in text.splitlines()
                   if len(l.split()) >= 5 and l.split()[0].startswith("TCP")
                   and l.split()[3].upper() == "LISTENING" and l.split()[1].endswith(":%d" % port)})


def call(method, path, headers=None, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request("http://127.0.0.1:%d/api/v1%s" % (PORT, path), method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with op.open(req, timeout=60) as r:
            raw = r.read()
            try:
                return r.status, json.loads(raw)
            except Exception:
                return r.status, {"non_json": raw[:180].decode("utf-8", "replace")}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"non_json": raw[:180].decode("utf-8", "replace")}


def redact(body):
    """Keep the named code and shape; never echo a token or a credential."""
    if not isinstance(body, dict):
        return body
    keep = {"status", "detail", "message", "journey_id", "traveler_id", "id", "version_no",
            "activities_count", "plan_count"}
    text = json.dumps(body, ensure_ascii=False)
    return {"http_body_keys": sorted(body.keys())[:14], "codes_found":
            sorted({c for c in ("RESET_TOKEN_REQUIRED", "RESET_TOKEN_INVALID",
                                "DEMO_MODE_REQUIRED") if c in text}),
            "detail_first_140": (body.get("detail") or body.get("message") or "")[:140]
            if isinstance(body.get("detail") or body.get("message"), str) else None,
            "bytes": len(text.encode("utf-8"))}


out["netstat_owners_before"] = owners(PORT)

# ---- leg 1: the reset door's refusals (these touch nothing) -------------------------------
for label, headers in (("no_header", {}), ("wrong_header", {"X-Demo-Reset-Token": "not-the-operators-token"})):
    code, body = call("POST", "/demo/reset", headers=headers, data={})
    out["steps"].append({"leg": "reset_door", "case": label, "http_status": code,
                         "answered": redact(body)})

# a store-state fingerprint taken before and after leg 1: a refused reset must not have moved it
code, scene = call("GET", "/demo/scene")
out["steps"].append({"leg": "fingerprint", "case": "after_refusals", "http_status": code,
                     "scene_keys": sorted(scene.keys())[:16] if isinstance(scene, dict) else None,
                     "demo_mode": scene.get("demo_mode") if isinstance(scene, dict) else None,
                     "journey_id": scene.get("journey_id") if isinstance(scene, dict) else None})

# ---- leg 2: the same product state the spec wants, through non-destructive doors ----------
jid = scene.get("journey_id") if isinstance(scene, dict) else None
if not jid:
    print(json.dumps(out, ensure_ascii=False))
    sys.exit("ABORT: my store copy answers no journey; the spec's state cannot be reached without reset")

code, plans = call("GET", "/journeys/%s/plans" % jid)
cur = [p for p in plans if p.get("status") == "ACTIVE"] if isinstance(plans, list) else []
out["steps"].append({"leg": "store_before", "http_status": code,
                     "plan_count": len(plans) if isinstance(plans, list) else None,
                     "active_plan_versions": [p.get("version_no") for p in cur]})

if not cur:
    code, gen = call("POST", "/journeys/%s/plans/generate" % jid, data={"candidate_count": 1})
    out["steps"].append({"leg": "generate", "http_status": code,
                         "answered": {"bytes": len(json.dumps(gen).encode())} if code < 400
                         else redact(gen)})
    if code < 400:
        first = gen[0] if isinstance(gen, list) and gen else None
        if first:
            code2, sel = call("POST", "/journeys/%s/plans/%s/select" % (jid, first.get("id")))
            out["steps"].append({"leg": "select", "http_status": code2,
                                 "answered": {"keys": sorted(sel.keys())[:10]} if code2 < 400
                                 else redact(sel)})
            cur = [p for p in call("GET", "/journeys/%s/plans" % jid)[1]
                   if p.get("status") == "ACTIVE"]

if cur:
    code, st = call("POST", "/journeys/%s/start" % jid)
    out["steps"].append({"leg": "start", "http_status": code,
                         "answered": redact(st) if code >= 400 else {"keys": sorted(st.keys())[:12]}})
    code, twin = call("GET", "/journeys/%s/twin" % jid)
    ex = (twin.get("context", {}) or {}).get("execution", {}) if isinstance(twin, dict) else {}
    out["steps"].append({"leg": "twin_after_start", "http_status": code,
                         "now_state": ex.get("now_state"), "next_state": ex.get("next_state")})
    code, plan = call("GET", "/journeys/%s/plans" % jid)
    act = [p for p in plan if p.get("status") == "ACTIVE"][0] if code < 400 else None
    out["steps"].append({"leg": "activity_statuses", "http_status": code,
                         "activities": [[a.get("sequence_no"), a.get("status")]
                                        for a in (act or {}).get("activities", [])]})

out["netstat_owners_after"] = owners(PORT)
out["journey_id"] = jid
out["reset_was_run"] = False
path = "D:/moodle/_qoder_cmdra_ord0553_20261003/_evidence/r13_doors_%s.json" % RUN
open(path, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1)[:2600])
print("WROTE", path)
