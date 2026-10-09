"""Derive deploy_bundle_r2.py - the F arm must tell "no HTTP answer at all" apart from "wrong HTTP answer".

Measured problem (2026-09-28 16:16+08, receipt `_deploy_pre_1616.txt`, published as
`evidence/cmdr-1647/deploy_preflight_r1.txt`, blob 46914c7499c5c4c1a1ac5800db7bd4295c5b8f74): the campus
box lost external DNS and the proxy listeners (7892/7897/9097) died, so the *public tunnel* leg of F could
not be probed at all - every probe returned status None. r1 folds that into RED, which blocks the switch
even though the two legs that actually serve the bundle (hop2 :4781 and the auth proxy :4782) were
measured GREEN. That is the same shape as the bug recorded on 2026-09-26 17:18 in this file's own header
comment: "a proxy port that refuses connections produced a false RED on the tunnel arm while the tunnel
itself answered - the gate must not attribute instrument noise to the product."

What r2 changes, and what it deliberately does NOT change:
  + a probe group where EVERY row has no HTTP status and carries a transport error is named UNREACHABLE;
  + F may report F_REMOTE_LEG_UNREACHABLE, but ONLY when the operator declared the gap (the existing
    --allow-proxy-unprobed switch), so silence still fails closed;
  + a leg that ANSWERS the wrong thing (200 + text/html on a .js ref) stays RED - that is the product
    defect the gate exists for, and nothing here forgives it;
  + the overall receipt still cannot say ALL_GREEN while any named gap exists: the gap class is not GREEN,
    so the switch is allowed while the receipt keeps the run non-green and names what is unproven.
"""
from __future__ import annotations

import ast
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "deploy_bundle.py")
DST = os.path.join(HERE, "deploy_bundle_r2.py")

ANCHORS = [
    ("""    rows = [asset_verdict(ref, expect_ct, serve, base=base, auth_file=auth_file) for _ in range(max(1, times))]
    ok = bool(rows) and all(r["verdict"] == "GREEN" for r in rows)
    return {"verdict": "GREEN" if ok else "RED", "times": len(rows),
            "statuses": [r["status"] for r in rows], "probes": rows,
            "red_refs": [f"{r['status']}/{r['content_type']}" for r in rows if r["verdict"] != "GREEN"]}""",
     """    rows = [asset_verdict(ref, expect_ct, serve, base=base, auth_file=auth_file) for _ in range(max(1, times))]
    # r2: "no answer at all" is a different fact from "an answer that is wrong". A row with no HTTP status
    # and a transport error says something about this box's DNS/proxy, not about the served bundle.
    transport_only = bool(rows) and all((r["status"] is None) and r.get("error") for r in rows)
    ok = bool(rows) and all(r["verdict"] == "GREEN" for r in rows)
    verdict = "GREEN" if ok else ("UNREACHABLE" if transport_only else "RED")
    return {"verdict": verdict, "times": len(rows),
            "statuses": [r["status"] for r in rows], "probes": rows,
            "transport_only": transport_only,
            "red_refs": [f"{r['status']}/{r['content_type']}" for r in rows if r["verdict"] != "GREEN"]}"""),
    ("""    unconfigured = any(p.get("verdict") == "NOT_CONFIGURED" for p in probes)
    if unconfigured and declared_unprobed:
        return "F_UNPROBED_DECLARED"          # declared gap, kept OUT of all_green by name
    if unconfigured:
        return "RED"                          # fail closed: absent comparison != passed comparison
    return "GREEN" if all(p.get("got", {}).get("verdict") == "GREEN" for p in probes) else "RED\"""",
     """    unconfigured = any(p.get("verdict") == "NOT_CONFIGURED" for p in probes)
    if unconfigured and declared_unprobed:
        return "F_UNPROBED_DECLARED"          # declared gap, kept OUT of all_green by name
    if unconfigured:
        return "RED"                          # fail closed: absent comparison != passed comparison
    got = [p.get("got", {}) for p in probes]
    unreachable = [g for g in got if g.get("verdict") == "UNREACHABLE"]
    if unreachable:
        # Declared -> a named gap that does not block the switch but never reads as GREEN.
        # Undeclared -> fail closed, exactly like the NOT_CONFIGURED case above.
        if declared_unprobed and all(g.get("verdict") in ("GREEN", "UNREACHABLE") for g in got):
            return "F_REMOTE_LEG_UNREACHABLE"
        return "RED"
    return "GREEN" if all(g.get("verdict") == "GREEN" for g in got) else "RED\""""),
]


def main():
    if os.path.exists(DST):
        print("REFUSED: %s exists - revisions go to a new filename (Q57)" % DST, file=sys.stderr)
        return 3
    src = open(SRC, encoding="utf-8").read()
    out = src
    report = []
    for i, (old, new) in enumerate(ANCHORS, 1):
        n = out.count(old)
        if n != 1:
            print("ABORT anchor %d matched %d times: %r" % (i, n, old[:70]), file=sys.stderr)
            return 4
        out = out.replace(old, new, 1)
        report.append({"anchor": i, "matched": n})
    try:
        ast.parse(out)
    except SyntaxError as exc:
        print("ABORT: derived file does not parse: %s" % exc, file=sys.stderr)
        return 5
    with open(DST, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    back = open(DST, encoding="utf-8").read()
    print(json.dumps({"source_lines": src.count(chr(10)) + 1, "derived_lines": out.count(chr(10)) + 1,
                      "written_bytes": len(back.encode("utf-8")), "readback_matches": back == out,
                      "UNREACHABLE_named_in_derived": back.count("UNREACHABLE") >= 4,
                      "F_REMOTE_LEG_UNREACHABLE_present": "F_REMOTE_LEG_UNREACHABLE" in back},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
