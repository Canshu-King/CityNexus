#!/usr/bin/env python3
"""ORD-0384 -- read the saved generated contract and count what actually references the request schema.

r1 produced `review/evidence/ord0384/generated_openapi.json` and a per-field path list, but the claim I
then made in prose -- "zero responses reference `JourneyCreate`" -- was computed in an ad-hoc command and
never persisted, so the coordinate ruler was right to refuse it. This derives that count, plus the shape of
the experience route's 200 schema, from the saved document. No re-export, no server, no browser.
"""
import hashlib
import io
import json
import os
import sys

EV = r"D:/moodle/_qoder_n3_ord0357/review/evidence/ord0384"
DOC = os.path.join(EV, "generated_openapi.json")


def main():
    raw = io.open(DOC, "rb").read()
    doc = json.loads(raw.decode("utf-8"))
    paths = doc.get("paths") or {}
    resp_hits = []
    for p, item in paths.items():
        for method, op in item.items():
            if not isinstance(op, dict):
                continue
            for code, r in (op.get("responses") or {}).items():
                if "JourneyCreate" in json.dumps(r):
                    resp_hits.append("%s %s -> %s" % (method.upper(), p, code))
    exp = paths.get("/api/v1/journeys/{journey_id}/experience") or {}
    exp200 = (exp.get("get") or {}).get("responses", {}).get("200") or {}
    schema = (exp200.get("content") or {}).get("application/json", {}).get("schema")
    req_uses = ["%s %s" % (m.upper(), p) for p, item in paths.items() for m, op in item.items()
                if isinstance(op, dict) and "JourneyCreate" in json.dumps(op.get("requestBody") or {})]
    out = {"generated_by": os.path.basename(__file__), "order": "ORD-0384",
           "source": "review/evidence/ord0384/generated_openapi.json",
           "generated_bytes": len(raw),
           "generated_sha256": hashlib.sha256(raw).hexdigest(),
           "path_count": len(paths),
           "responses_referencing_JourneyCreate_count": len(resp_hits),
           "responses_referencing_JourneyCreate": resp_hits,
           "request_bodies_using_JourneyCreate": req_uses,
           "experience_200_schema": schema,
           "experience_200_schema_is_empty_object": schema == {},
           "consequence": "a field declared only under JourneyCreate is promised on the write side; the "
                          "experience response declares nothing at all in this document, so it cannot "
                          "anchor a read-derived item."}
    p = os.path.join(EV, "two_contracts_r2.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print("paths=%d responses_referencing_JourneyCreate=%d request_bodies_using_it=%d"
          % (len(paths), len(resp_hits), len(req_uses)))
    print("experience 200 schema:", json.dumps(schema), "| empty object:", schema == {})
    print("READING " + p.replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
