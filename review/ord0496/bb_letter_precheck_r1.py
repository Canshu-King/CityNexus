#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-flight a BB-机 letter against the hub's own acceptance rule before spending a send.

WHY: the hub rejects a message whose body cites a number that no evidence leg's output contains
(bus_hub.validate), and a rejected send still costs the commander a round trip.  The hub reads the
*whole* evidence output, not just the 400-byte excerpt, so guessing from the head of a log is wrong
in both directions.  This script imports the hub's real extractor and the client's real collector,
runs the legs, and prints the orphan list -- the same verdict the hub will reach, locally, first.

Usage:  python bb_letter_precheck_r1.py <body-file> <evidence-json>
        <evidence-json> = [{"label": "...", "spec": "label|shell command"}, ...]  (same specs bus.py takes)
Exit 0 = the hub would accept; 1 = it would reject (or a leg is unhealthy).
"""
import io
import json
import os
import sys

AGENT_BUS = os.environ.get("AGENT_BUS_DIR", r"D:\moodle\agent_bus")


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    sys.path.insert(0, AGENT_BUS)
    import bus       # noqa: E402  collect_evidence runs the legs exactly like a real send
    import bus_hub   # noqa: E402  numeric_claims is the hub's own extractor

    body = io.open(sys.argv[1], encoding="utf-8").read()
    legs = [l["spec"] for l in json.load(io.open(sys.argv[2], encoding="utf-8"))]
    nums = bus_hub.numeric_claims(body)
    ev = bus.collect_evidence(legs, nums=nums)

    # The hub's present(): a token must appear in the excerpt or in some hit's context snippet.
    hay = " ".join([u(e["excerpt"]) for e in ev] +
                   [u(h["text"]) for e in ev for h in (e["hits"] or []) if isinstance(h, dict)])
    hay_norm = hay.replace(",", "")

    def present(tok):
        if tok in hay or tok.rstrip(".,") in hay:
            return True
        if "," in tok:
            bare = tok.replace(",", "")
            if bare and bare in hay_norm:
                return True
        return False

    unhealthy = []
    for i, e in enumerate(ev):
        print("LEG[%d] rc=%s bytes=%s cmd=%s" % (i, e["rc"], e["bytes"], e["cmd"][:120]))
        if e["rc"] not in (0, None):
            unhealthy.append("evidence[%d] rc=%s" % (i, e["rc"]))
        elif e["rc"] == 0 and not e["excerpt"].strip():
            unhealthy.append("evidence[%d] rc=0 but empty output" % i)

    orphan = [t for t in sorted(set(nums)) if not present(t)]
    print("NUMERIC_CLAIMS", len(nums), "DISTINCT", len(set(nums)))
    print("EVIDENCE_HEALTH", "OK" if not unhealthy else "BAD " + " | ".join(unhealthy))
    print("ORPHAN_COUNT", len(orphan))
    for t in orphan:
        for line in body.splitlines():
            if t in line:
                print("  ORPHAN", t, "|", line.strip()[:150])
                break
    print("PRECHECK", "PASS" if not orphan and not unhealthy else "FAIL")
    return 0 if (not orphan and not unhealthy) else 1


def u(v):
    return v if isinstance(v, str) else str(v)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
