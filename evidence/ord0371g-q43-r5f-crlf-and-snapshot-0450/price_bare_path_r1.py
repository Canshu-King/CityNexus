#!/usr/bin/env python3
"""ORD-0371 r5f: PRICE the one decision the commander has not made, without making it for him.

The three rules he ordered (line-level attribution, unit/count readings as a named conditional class,
named remedies) are implemented in r5f and, measured over the whole inbox, change no block's verdict:
r5e 106 findings / 4 green, r5f 106 findings / 4 green, block by block identical.  The reason is on the
record in backlog_r5f_r1.json - the burning lines contain a bare artifact path (`places_response.json`,
`contracts/openapi.yaml`), not a `path:line`, and a bare path is not one of the two forms he named.

So this tool answers the only question that moves the backlog: how many findings and how many blocks
would clear if a bare path with a file extension counted as a same-line coordinate.  It does not change
any ruler: it loads r5f into a module object, swaps the DURABLE pattern in that object only, and prints
the difference.  The number is for his ruling, not for me to land.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

LIVE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
INBOX = os.environ.get("CNX_INBOX", r"D:/moodle/_qoder_ledger_inbox")
WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0371"
BARE_PATH = (r"[A-Za-z0-9_.:/\\-]*\.[A-Za-z][A-Za-z0-9]{0,6}\b")   # `contracts/openapi.yaml`
KINDS = ("as_ordered", "bare_path_also_counts")


def load():
    sys.path.insert(0, LIVE)
    import claim_coordinate_check_r5f as m
    return m


def main():
    m = load()
    orig = m.DURABLE
    ruler_blob = hashlib.sha1(b"blob %d\x00" % len(open(os.path.join(LIVE, "claim_coordinate_check_r5f.py"), "rb").read())
                              + open(os.path.join(LIVE, "claim_coordinate_check_r5f.py"), "rb").read()).hexdigest()
    files = sorted(f for f in os.listdir(INBOX)
                   if f.endswith(".md") and re.match(r"^[A-Za-z0-9._-]+_[0-9]{4}\.md$", f))
    rows = []
    for kind in KINDS:
        m.DURABLE = orig if kind == "as_ordered" else re.compile(
            "(?:%s|%s)" % (orig.pattern, BARE_PATH), re.IGNORECASE)
        for f in files:
            path = os.path.join(INBOX, f)
            text = io.open(path, encoding="utf-8").read()
            claims, findings, exempt = m.scan(text)
            key = (f, kind)
            row = next((r for r in rows if r["file"] == f), None)
            if row is None:
                row = {"file": f, "bytes": os.path.getsize(path)}
                rows.append(row)
            row[kind] = {"claims": claims, "findings": len(findings),
                         "verdict": m.decide(claims, findings, text)[0],
                         "tokens": sorted({x["matched"] for x in findings})[:20]}
    m.DURABLE = orig
    for r in rows:
        r["cleared_by_bare_path"] = r["as_ordered"]["findings"] - r["bare_path_also_counts"]["findings"]
        r["green_only_with_bare_path"] = (r["as_ordered"]["verdict"] != "Q43_GATE_GREEN"
                                         and r["bare_path_also_counts"]["verdict"] == "Q43_GATE_GREEN")
    out = {"ruler": {"file": "claim_coordinate_check_r5f.py", "blob": ruler_blob},
           "hypothesis_under_test": "a bare artifact path (with an extension, no `:line`) counts as a "
                                    "same-line coordinate",
           "not_applied": "This tool does not change the ruler; it prices the decision for the "
                          "commander. r5f still accepts only `path:line` and a full 40-hex.",
           "summary": {
               "blocks": len(rows),
               "findings_as_ordered": sum(r["as_ordered"]["findings"] for r in rows),
               "findings_with_bare_path": sum(r["bare_path_also_counts"]["findings"] for r in rows),
               "green_as_ordered": len([r for r in rows if r["as_ordered"]["verdict"] == "Q43_GATE_GREEN"]),
               "green_with_bare_path": len([r for r in rows
                                            if r["bare_path_also_counts"]["verdict"] == "Q43_GATE_GREEN"]),
               "blocks_needing_this_ruling": sorted(r["file"] for r in rows if r["green_only_with_bare_path"]),
               "blocks_still_red_after_it": sorted(r["file"] for r in rows
                                                   if r["bare_path_also_counts"]["verdict"] != "Q43_GATE_GREEN")},
           "blocks": rows}
    io.open(os.path.join(WORK, "price_bare_path_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out["summary"], ensure_ascii=False, indent=1))
    for r in rows:
        if r["cleared_by_bare_path"]:
            print("%-24s findings %3d -> %3d  green_only_with_bare_path=%s" % (
                r["file"], r["as_ordered"]["findings"], r["bare_path_also_counts"]["findings"],
                r["green_only_with_bare_path"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
