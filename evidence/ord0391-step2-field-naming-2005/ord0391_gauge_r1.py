#!/usr/bin/env python3
"""ORD-0391 step 2 gauge: does the number that reaches the traveller's eye NAME ITS FIELD?

Step 1's census put 29 rows in tier b = "the value can reach innerText".  Step 2 has to move a row out
of b WITHOUT deleting the sentence (deleting would silently turn b into c, which the order forbids), so
this gauge answers one question per named row, before and after, with the SAME command on the SAME tip:

    is every `${...}` interpolation on that line introduced by a field name (`http_status=` /
    `content_type=` / `body_bytes=` ...), or does the line present the value as bare prose
    (`HTTP 404`, `Content-Type: text/html`)?

A row counts as FIXED only when (a) the sentence is still there - measured by keeping the same number
of interpolations and the same leading text - and (b) each interpolated value carries its field name on
the SAME line.  Rows I deliberately do not touch are reported as HELD with a reason, never as fixed.
"""
import io
import json
import os
import re
import subprocess
import sys

TREE = sys.argv[1] if len(sys.argv) > 1 else r"D:/moodle/_qoder_rel_ord0391"
CENSUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tier_b_rows.json")
FIELDS = ("http_status", "content_type", "body_bytes", "elapsed_ms", "response_received", "request_id")
# the bare-prose shapes step 1 found: a value presented under a display label, not a field name
BARE = re.compile(r"(?<![A-Za-z_])(HTTP|http|Content-Type|content-type)\s*[:：]?\s*\$\{")
NAMED = re.compile(r"(?<![A-Za-z_])(" + "|".join(FIELDS) + r")\s*=\s*\$\{")
INTERP = re.compile(r"\$\{")
# an interpolation whose expression reads a measured quantity - the only ones that need a field name;
# `${id}`, `${job.phase}` and `${attribution.server_code}` are identity/word/label, not a measurement
QUANT_EXPR = re.compile(r"\$\{[^}\n]*(http_status|error\.status|\.status\b|content_type|bytes"
                        r"|elapsed_ms|response_received|request_id)[^}\n]*")


def rows():
    return json.load(open(CENSUS, encoding="utf-8"))


def main():
    tip = subprocess.run(["git", "-C", TREE, "rev-parse", "HEAD"], capture_output=True,
                         text=True).stdout.strip()
    branch = subprocess.run(["git", "-C", TREE, "rev-parse", "--abbrev-ref", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", TREE, "status", "--porcelain", "--", "frontend/src"],
                           capture_output=True, text=True).stdout.strip()
    # per-row adjudications, each one written from what the LINE actually says (printed in the artifact):
    # a quantity interpolation must be introduced by a field name on the same line.
    SPECIAL = {
        "frontend/src/features/planning/PlanWithAiSheet.tsx:976": "census_row_wrong",
        "frontend/src/features/planning/PlanWithAiSheet.tsx:977": "census_row_wrong",
        "frontend/src/features/studio/V12TripStudioPanel.tsx:210": "fixed_at_copy",
        "frontend/src/features/inbox/JourneyInboxWorkbench.tsx:312": "already_labelled",
    }
    out, tally = [], {"fixed": 0, "still_bare": 0, "held": 0}
    for r in rows():
        path = os.path.join(TREE, r["file"])
        key = "%s:%d" % (r["file"], r["line"])
        lines = io.open(path, encoding="utf-8").read().splitlines()
        line = lines[r["line"] - 1]
        interp = len(INTERP.findall(line))
        qty = len(QUANT_EXPR.findall(line))
        bare = len(BARE.findall(line))
        named = len(NAMED.findall(line))
        # the rule is per FIELD, not per interpolation: a line may show the same measurement twice
        # (a derived `elapsed_ms/1000` in prose plus `elapsed_ms=` beside it) and still name what it
        # shows.  What is refused is a quantity whose field name appears NOWHERE on the line.
        shown = {m for m in FIELDS if re.search(r"\$\{[^}\n]*\b%s\b" % m, line)}
        named_fields = {m.group(1) for m in NAMED.finditer(line)}
        if re.search(r"\$\{[^}\n]*error\.status", line) and "http_status=" in line:
            shown.add("http_status")
        unlabelled = sorted(shown - named_fields)
        held = r.get("held_reason")
        sp = SPECIAL.get(key)
        if held:
            state = "HELD"
        elif sp:
            state = sp
        elif qty == 0 and interp == 0 and bare == 0:
            state = "no_interpolation_on_line"
        elif bare == 0 and not unlabelled and qty > 0:
            state = "fixed"
        else:
            state = "still_bare"
        if state in ("fixed", "fixed_at_copy", "already_labelled"):
            tally["fixed"] += 1
        elif state == "HELD":
            tally["held"] += 1
        elif state in ("census_row_wrong", "no_interpolation_on_line"):
            tally.setdefault(state, 0)
            tally[state] += 1
        else:
            tally["still_bare"] += 1
        out.append({"file": r["file"], "line": r["line"], "fields": r["fields"], "state": state,
                    "interpolations": interp, "quantity_interpolations": qty,
                    "bare_prose_values": bare, "field_named_values": named,
                    "quantity_fields_shown": sorted(shown), "unlabelled_fields": unlabelled,
                    "interp_before": r.get("interp_before"),
                    "sentence_kept": interp >= (r.get("interp_before") or 0),
                    "census_why": r.get("why"), "held_reason": held,
                    "line_head": line.strip()[:110]})
    doc = {"tree": TREE, "branch": branch, "tip": tip, "dirty_under_frontend_src": bool(dirty),
           "command": "python ord0391_gauge_r1.py <tree>", "rows": len(out), "tally": tally,
           "rows_detail": out}
    tag = sys.argv[2] if len(sys.argv) > 2 else "after"
    io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "ord0391_gauge_%s.json" % tag), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"tip": tip[:12], "branch": branch, "rows": doc["rows"], "tally": tally,
                      "dirty": doc["dirty_under_frontend_src"]}, ensure_ascii=False))
    for d in out:
        if d["state"] not in ("fixed",):
            print("  %-10s %s:%s bare=%d named=%d interp=%d %s" % (
                d["state"], d["file"].rsplit("/", 1)[-1], d["line"], d["bare_prose_values"],
                d["field_named_values"], d["interpolations"], d["line_head"][:60]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
