"""Attribute g10's red: is the collection missing because the job is still in flight, or because
the door's payload never carries the key the arm reads?

One process, one fresh database, both doors read through the app's own TestClient.  Prints the
shape of every answer, then waits the job out and reads the same door again -- so the two
hypotheses get different numbers rather than my opinion.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time

BACKEND = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(BACKEND))
os.chdir(str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

CAPABILITY = "/api/v1/destinations/capability"
HYDRATIONS = "/api/v1/catalog-hydrations"
UNSEEN_COUNTY = sys.argv[2] if len(sys.argv) > 2 else "贡山独龙族怒族自治县"

client = TestClient(app)

post = client.post(HYDRATIONS, json={"query": UNSEEN_COUNTY})
print("POST http_status=%d" % post.status_code)
print("POST body %s" % json.dumps(post.json(), ensure_ascii=False)[:600])
operation_id = None
try:
    body = post.json()
    operation_id = (body.get("operation") or {}).get("id") or body.get("operation_id") or body.get("id")
except Exception:
    pass
print("operation_id %r" % operation_id)

immediate = client.get(CAPABILITY, params={"query": UNSEEN_COUNTY})
ib = immediate.json()
print("IMMEDIATE http_status=%d keys=%s" % (immediate.status_code, sorted(ib)))
for key in ("places", "catalog", "candidates", "malformed_candidates", "hard_gaps"):
    value = ib.get(key)
    print("  immediate %-20s type=%s len=%s" % (key, type(value).__name__,
                                                len(value) if isinstance(value, (list, dict, str)) else "n/a"))
print("  immediate capability=%r destination_state=%r coverage=%r canonical=%r"
      % (ib.get("capability"), ib.get("destination_state"), ib.get("coverage"),
         ib.get("canonical_destination_id")))

if operation_id:
    deadline = time.time() + 40
    last = None
    while time.time() < deadline:
        poll = client.get("%s/%s" % (HYDRATIONS, operation_id))
        last = poll.json() if poll.status_code == 200 else {"http_status": poll.status_code}
        status = (last.get("status") or (last.get("operation") or {}).get("status")
                  or (last.get("data") or {}).get("status"))
        if status in ("COMPLETED", "FAILED", "UNAVAILABLE", "CANCELLED", "PARTIAL"):
            break
        time.sleep(1)
    print("AFTER-WAIT job %s" % json.dumps(last, ensure_ascii=False)[:600])

    after = client.get(CAPABILITY, params={"query": UNSEEN_COUNTY})
    ab = after.json()
    print("AFTER-WAIT http_status=%d keys=%s" % (after.status_code, sorted(ab)))
    for key in ("places", "catalog", "candidates", "malformed_candidates", "hard_gaps"):
        value = ab.get(key)
        print("  after     %-20s type=%s len=%s" % (key, type(value).__name__,
                                                    len(value) if isinstance(value, (list, dict, str)) else "n/a"))
    print("  after     capability=%r destination_state=%r coverage=%r canonical=%r"
          % (ab.get("capability"), ab.get("destination_state"), ab.get("coverage"),
             ab.get("canonical_destination_id")))
    cand = ab.get("candidates") or []
    if cand:
        print("  first candidate keys %s" % sorted(cand[0]))
        print("  first candidate %s" % json.dumps(cand[0], ensure_ascii=False)[:400])
    plist = ab.get("places") or []
    kinds = {}
    for row in plist:
        kind = str(row.get("source_kind_geometry") or row.get("geometry") or row.get("osm_type") or "UNKNOWN")
        kinds[kind] = kinds.get(kind, 0) + 1
    print("  places_rows %d kinds_as_the_arm_reads_them %s" % (len(plist), kinds))
    print("  place_key_union %s" % sorted({k for row in plist for k in row}))
    for row in plist[:3]:
        print("  place_row %s" % json.dumps(row, ensure_ascii=False)[:220])
    print("  rows_missing_coordinates %d" % len([r for r in plist
          if r.get("latitude") is None or r.get("longitude") is None]))
    print("VERDICT %s" % ("COLLECTION_NEVER_HAS_THE_READ_KEY"
                          if not (ab.get("places") or ab.get("catalog"))
                          else "READ_KEY_APPEARS_AFTER_WAIT"))
else:
    print("VERDICT NO_OPERATION_ID_IN_POST_ANSWER")
