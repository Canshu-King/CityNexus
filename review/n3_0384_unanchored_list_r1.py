#!/usr/bin/env python3
"""ORD-0384 -- measure which checklist classes have a contract anchor, and emit the ones that do not.

The order was re-scoped: the panel may only show an item whose field the contract actually names, and the
classes that cannot be anchored must not appear on screen at all -- they go into a named list that is the
input for the next order. So this file decides nothing by hand: for every candidate class it asks the
contract three questions and records the answer.

Three questions per class, against `contracts/openapi.yaml` at the working tree's commit:
  1. is the field written as a property declaration (`name:` at a schema position)?  -> ANCHORED
  2. if not, does the name appear anywhere at all (prose, a description, a path)?   -> PROSE_ONLY
  3. if not, is it absent from the contract entirely?                               -> ABSENT

`PROSE_ONLY` is deliberately not an anchor: a word inside a `description:` string pins no payload shape,
and treating it as one is how the first version of this order nearly shipped.

Outputs, both computed from the same run so they cannot disagree:
  review/evidence/ord0384/unanchored_classes_r1.json   -- the reading, for the ledger and the next order
  frontend/e2e/_qoderUnanchoredClasses.ts              -- the same list, so the gate can assert that none
                                                          of these keys ever reach the DOM
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

WT = r"D:/moodle/_qoder_n3_ord0357"
CONTRACT = os.path.join(WT, "contracts", "openapi.yaml")
EV = os.path.join(WT, "review", "evidence", "ord0384")
TSDST = os.path.join(WT, "frontend", "e2e", "_qoderUnanchoredClasses.ts")

EXPERIENCE = "/api/v1/journeys/{journeyId}/experience"
WALLET = "/api/v1/journeys/{journeyId}/wallet"

# key, endpoint, the field the item would name, the contract name to probe, and what a real anchor looks like
CANDIDATES = [
    ("plan_feasibility_open", EXPERIENCE, "experience_flags.feasibility_failures",
     "feasibility_failures", "already declared; nothing further needed"),
    ("recovery_needs_decision", EXPERIENCE, "recovery.requires_user_decision",
     "requires_user_decision", "already declared; nothing further needed"),
    ("stay_budget_undeclared", EXPERIENCE, "trip.stay_budget.declared", "stay_budget",
     "declare `trip` as an object with a `stay_budget: {declared: boolean, amount_minor: integer, currency: string}` property"),
    ("stay_chosen_but_unconfirmed", WALLET, "reservations / commitments", "reservations",
     "give the wallet route's 200 a schema with `reservations: array` and `commitments: array` instead of `{type: object}`"),
    ("stay_not_chosen", EXPERIENCE, "selected_option_id", "selected_option_id",
     "declare `selected_option_id: {type: [string, 'null']}` as a property of the experience response"),
    ("no_active_plan", EXPERIENCE, "active_plan", "active_plan",
     "declare `active_plan` as a nullable object property of the experience response (today only its prose at the plans route mentions the concept)"),
    ("arrival_anchor_missing", EXPERIENCE, "trip.arrival_anchor.at", "arrival_anchor",
     "declare `trip.arrival_anchor` as an object with `at` inside the experience response"),
    ("departure_anchor_missing", EXPERIENCE, "trip.departure_anchor.at", "departure_anchor",
     "declare `trip.departure_anchor` as an object with `at` inside the experience response"),
    ("offline_pack_not_ready", WALLET, "offline_ready", "offline_ready",
     "declare `offline_ready: boolean` as a property of the wallet response"),
]


def prop_line(lines, name):
    pat = re.compile(r"(^|[{,\s])" + re.escape(name) + r"\s*:")
    for n, line in enumerate(lines, 1):
        if pat.search(line):
            return n, line.strip()[:120]
    return None, None


def prose_lines(lines, name):
    return [n for n, line in enumerate(lines, 1) if name in line]


def main():
    text = io.open(CONTRACT, encoding="utf-8").read()
    lines = text.splitlines()
    head = subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    for key, endpoint, field, probe, needs in CANDIDATES:
        line, decl = prop_line(lines, probe)
        prose = prose_lines(lines, probe)
        status = "ANCHORED" if line else ("PROSE_ONLY" if prose else "ABSENT")
        rows.append({"key": key, "endpoint": endpoint, "field": field, "contract_probe_name": probe,
                     "status": status, "contract_line": line, "contract_declaration": decl,
                     "prose_only_lines": prose[:12], "prose_only_count": len(prose),
                     "what_would_anchor": needs})
    anchored = [r["key"] for r in rows if r["status"] == "ANCHORED"]
    unanchored = [r["key"] for r in rows if r["status"] != "ANCHORED"]
    out = {"generated_by": os.path.basename(__file__), "order": "ORD-0384",
           "commit": head, "contract": "contracts/openapi.yaml",
           "contract_sha256": hashlib.sha256(io.open(CONTRACT, "rb").read()).hexdigest(),
           "candidates": len(rows), "anchored_count": len(anchored), "unanchored_count": len(unanchored),
           "anchored_keys": anchored, "unanchored_keys": unanchored, "rows": rows,
           "rule": "PROSE_ONLY is not an anchor: a name inside a description string pins no payload shape."}
    io.open(os.path.join(EV, "unanchored_classes_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    ts = ["/* GENERATED by review/n3_0384_unanchored_list_r1.py -- do not edit by hand.",
          " *",
          " * ORD-0384 re-scoped: the checklist may only show an item whose field the contract names.",
          " * The classes below are measured as un-anchored against contracts/openapi.yaml at the commit",
          " * recorded in review/evidence/ord0384/unanchored_classes_r1.json, so the gate can assert two",
          " * things at once: only the anchored keys ever render, and none of these keys ever reach the DOM.",
          " */",
          "",
          "export const UNANCHORED_CONTRACT_COMMIT = %r;" % head,
          "export const UNANCHORED_CONTRACT_SHA256 = %r;" % out["contract_sha256"],
          "export const ANCHORED_ITEM_KEYS: readonly string[] = [%s];" % ", ".join('"%s"' % k for k in anchored),
          "export const UNANCHORED_ITEM_KEYS: readonly string[] = [%s];" % ", ".join('"%s"' % k for k in unanchored),
          "export const UNANCHORED_CLASSES: ReadonlyArray<{ key: string; endpoint: string; field: string;",
          "  status: string; why_no_anchor: string; what_would_anchor: string }> = [",
          ]
    for r in rows:
        if r["status"] == "ANCHORED":
            continue
        why = {"PROSE_ONLY": "the name appears only inside description prose (%d line(s), first %s)"
                            % (r["prose_only_count"], r["prose_only_lines"][0] if r["prose_only_lines"] else "-"),
               "ABSENT": "the name does not appear anywhere in the contract"}[r["status"]]
        ts.append("  { key: %r, endpoint: %r, field: %r, status: %r, why_no_anchor: %r, what_would_anchor: %r },"
                  % (r["key"], r["endpoint"], r["field"], r["status"], why, r["what_would_anchor"]))
    ts += ["];", ""]
    io.open(TSDST, "w", encoding="utf-8", newline="\n").write("\n".join(ts))
    for r in rows:
        print("%-28s %-10s %s" % (r["key"], r["status"], r["contract_line"] or ""))
    print("ANCHORED %d of %d: %s" % (len(anchored), len(rows), ", ".join(anchored)))
    print("UNANCHORED %d: %s" % (len(unanchored), ", ".join(unanchored)))
    print("READING " + os.path.join(EV, "unanchored_classes_r1.json").replace("\\", "/"))
    print("WROTE " + TSDST.replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
