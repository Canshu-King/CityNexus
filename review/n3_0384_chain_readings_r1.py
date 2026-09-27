#!/usr/bin/env python3
"""ORD-0384 -- read the phone chain's named available state over HTTP, and keep the bytes.

Why this exists: the previous live reading was taken with an ad-hoc shell command, so the delivery
cited bytes nobody can re-fetch. It also cited a journey (`9c6c3d73-...`, the Guangzhou two-day trip)
that `POST /api/v1/demo/reset` deleted from `_preview.db` at 03:55. This script is the instrument, and
it is pointed at whatever the chain actually holds now rather than at a remembered id.

What it does: `GET /api/v1/demo/scene` to ask the stage which journey it is serving, then one
`GET .../experience` and one `GET .../wallet` for that id. One request per endpoint on purpose --
`GET /experience` performs a write on a locked SQLite file, so a probe loop here would be a state
change on somebody else's chain, not a read.

Proxies are bypassed explicitly: this shell carries HTTP(S)_PROXY pointing at a dead listener, and
letting a loopback request through it produces a fake "unreachable". No credential is ever read,
sent, or printed.
"""
import hashlib
import io
import json
import os
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:4781"
LABEL = sys.argv[2] if len(sys.argv) > 2 else "chain"
EV = r"D:/moodle/_qoder_n3_ord0357/review/evidence/ord0384"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(path):
    req = urllib.request.Request(BASE + path, headers={"Accept": "application/json"}, method="GET")
    try:
        with OPENER.open(req, timeout=60) as r:
            return r.status, r.headers.get("content-type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("content-type", "") if e.headers else "", e.read()


def main():
    st, ct, body = get("/api/v1/demo/scene")
    scene = json.loads(body.decode("utf-8")) if st == 200 and body else {}
    jid = str(scene.get("journey_id") or "")
    out = {"base": BASE, "label": LABEL, "scene_status": st, "scene_bytes": len(body),
           "scene_sha256": hashlib.sha256(body).hexdigest(),
           "journey_id": jid or None,
           "scene_identity": {k: scene.get(k) for k in
                              ("journey_title", "title", "city_code", "status", "created_at")
                              if k in scene},
           "requests": []}
    if not jid:
        io.open(os.path.join(EV, "chain_%s_r1.json" % LABEL), "w", encoding="utf-8").write(
            json.dumps(out, ensure_ascii=False, indent=1) + "\n")
        print("SCENE_HAS_NO_JOURNEY status=%s bytes=%s" % (st, len(body)))
        return 3
    for name in ("experience", "wallet"):
        s, c, b = get("/api/v1/journeys/%s/%s" % (jid, name))
        fn = "chain_%s_%s.json" % (LABEL, name)
        io.open(os.path.join(EV, fn), "wb").write(b)
        out["requests"].append({"endpoint": "/api/v1/journeys/{journeyId}/%s" % name,
                                "http_status": s, "content_type": c, "body_bytes": len(b),
                                "sha256": hashlib.sha256(b).hexdigest(), "saved_as": fn})
    io.open(os.path.join(EV, "chain_%s_r1.json" % LABEL), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print("journey_id=%s scene_identity=%s" % (jid, json.dumps(out["scene_identity"], ensure_ascii=False)))
    for r in out["requests"]:
        print("  %-9s %s %s B sha %s" % (r["endpoint"].rsplit("/", 1)[-1], r["http_status"],
                                         r["body_bytes"], r["sha256"][:12]))
    print("READING " + os.path.join(EV, "chain_%s_r1.json" % LABEL).replace("\\", "/"))
    return 0 if all(r["http_status"] == 200 for r in out["requests"]) else 3


if __name__ == "__main__":
    sys.exit(main())
