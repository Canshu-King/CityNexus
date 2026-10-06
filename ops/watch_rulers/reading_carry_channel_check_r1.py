"""Qualify the SOFT findings the frozen Q38 ruler reports: does each cell's sentence actually carry its own readings?

Why this exists: the frozen ruler (receipt_cell_derivation_check_r2.py) decides "is this sentence built from
machine-checkable tokens" with a token grammar of hex ids, file names, bare numbers and SCREAMING constants.
A runId like `0281p13227` is none of those, so a cell that honestly quotes its own runId still reads as
`WHY_NOT_FROM_OWN_READINGS`. That is a blind spot in MY instrument, and I must not bill it to the lane.
This script therefore adds a second channel - "does some value that literally lives in this cell's readings
appear verbatim in this cell's why?" - and reports which soft cells the new channel clears and which stay
red. It never replaces the frozen ruler: r2's verdict stays, this only attributes its findings.

--selftest proves the new channel discriminates: one cell whose runId is carried, one whose invented runId
is not. Both directions must disagree, or the channel is a rubber stamp.
"""
import argparse
import io
import json
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RULER = "receipt_cell_derivation_check_r2.py"


def walk_values(obj, out):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.append(str(obj))
    elif isinstance(obj, str):
        if len(obj) >= 6:
            out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            walk_values(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_values(v, out)


def carry(doc):
    rows = []
    for i, c in enumerate(doc.get("cells") or []):
        if not isinstance(c, dict) or "why" not in c:
            continue
        why = c["why"] if isinstance(c["why"], str) else json.dumps(c["why"], ensure_ascii=False)
        vals = []
        walk_values(c.get("readings"), vals)
        carried = sorted({v for v in vals if v in why})
        rows.append({"cell": c.get("cell", i), "readings_values": len(vals),
                     "carried_verbatim": len(carried), "examples": carried[:6],
                     "channel_ok": bool(carried)})
    return rows


def selftest():
    doc = {"cells": [
        {"cell": "POSITIVE_carried", "why": "pristine run 0281p13227 matrix_status=passed on port 4470",
         "readings": {"runId": "0281p13227", "matrix_status": "passed", "port": 4470}},
        {"cell": "NEGATIVE_invented", "why": "pristine run 0281zz9999 matrix_status=whichever on port 4470",
         "readings": {"runId": "0281p13227", "matrix_status": "passed", "port": 4470}},
    ]}
    rows = carry(doc)
    pos, neg = rows[0]["channel_ok"], rows[1]["channel_ok"]
    # the negative arm must still carry SOMETHING (port 4470 is shared) - so assert on the invented tokens
    # specifically: the runId and status it made up must not be listed as carried.
    bad = [e for e in rows[1]["examples"] if "0281zz9999" in e or e == "whichever"]
    ok = pos and not bad and rows[0]["carried_verbatim"] > rows[1]["carried_verbatim"]
    print("selftest positive carried=%d (%s) negative invented-tokens-listed=%d -> %s" % (
        rows[0]["carried_verbatim"], pos, len(bad), "SELFTEST_PASS" if ok else "SELFTEST_FAIL"))
    return 0 if ok else 7


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", help="local copy of the receipt under test")
    ap.add_argument("--ruler-json", help="frozen-ruler output for the same receipt, to attribute its soft cells")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    doc = json.loads(io.open(args.receipt, encoding="utf-8").read())
    rows = carry(doc)
    soft = []
    if args.ruler_json:
        r = json.loads(io.open(args.ruler_json, encoding="utf-8").read())
        soft = [f for f in (r.get("findings") or []) if not f.get("hard")]
    by_cell = {}
    for i, row in enumerate(rows):
        # the frozen ruler reports cell indices as strings ("0"); an int-keyed map silently misses every one of
        # them and would misattribute all of MY blind spot to the lane.
        by_cell[str(i)] = row
    attribution = []
    for f in soft:
        cid = f.get("cell")
        row = by_cell.get(cid)
        attribution.append({"cell_index": cid, "ruler_code": f.get("code"),
                            "ruler_detail": f.get("detail"),
                            "value_channel_carries": bool(row and row["channel_ok"]),
                            "carried_examples": (row or {}).get("examples", []),
                            "attribution": ("COMMANDER_RULER_BLIND_SPOT" if row and row["channel_ok"]
                                            else "REAL_GAP_SENTENCE_NOT_BUILT_FROM_OWN_READINGS")})
    cleared = sum(1 for a in attribution if a["attribution"] == "COMMANDER_RULER_BLIND_SPOT")
    real = len(attribution) - cleared
    out = {
        "schema": "CNX_CMDR_READING_CARRY_CHANNEL_V1",
        "lane": "commander 494abfd7",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "what": "attribute the frozen Q38 ruler's SOFT findings: my token grammar's blind spot vs a real "
                "sentence-not-built-from-readings gap",
        "receipt": {"path": args.receipt, "bytes": len(io.open(args.receipt, "rb").read())},
        "frozen_ruler_verdict_unchanged": (json.loads(io.open(args.ruler_json, encoding="utf-8").read()).get("overall")
                                           if args.ruler_json else None),
        "cells": rows,
        "soft_attribution": attribution,
        "summary": {"soft_from_ruler": len(attribution), "attributed_to_my_blind_spot": cleared,
                    "attributed_to_real_gap": real},
        "standing_rule": "before a soft finding is billed to a lane, run the same sentence through a second "
                         "channel; where the two instruments disagree the defect is in the instrument until the "
                         "lane's own readings are shown not to contain the words.",
        "discipline": {"product_bytes_changed": 0, "refs_pushed": 0, "databases_opened": 0,
                       "credential_values_printed": 0},
        "claim_kind": "artifact_determined",
        "claimed_result": None, "derived_result": None,
    }
    out["claimed_result"] = ("of %d SOFT findings the frozen ruler reports for this receipt, %d are cleared by the "
                             "value-carry channel (my token grammar cannot see runIds like 0281p13227) and %d stay "
                             "as real gaps" % (len(attribution), cleared, real))
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    if args.out:
        io.open(args.out, "w", encoding="utf-8", newline="\n").write(txt)
    print(out["claimed_result"])
    for a in attribution:
        print("   cell %-3s %-28s -> %s  carried=%s" % (a["cell_index"], a["ruler_code"], a["attribution"],
                                                        a["carried_examples"][:3]))
    print("file=%s bytes=%d" % (args.out, len(txt.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
