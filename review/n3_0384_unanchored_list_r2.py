#!/usr/bin/env python3
"""ORD-0384 -- classify each checklist class by where its field is declared, across BOTH contracts.

r1 asked one question of one artifact ("is the name in contracts/openapi.yaml?"). Two things make that
insufficient: the repo carries a second, generated document, and a name can be declared on the *write*
side while the item reads it from a *response*. `stay_budget`, `arrival_anchor` and `departure_anchor`
are each declared exactly once in the generated document -- under `JourneyCreate/properties/`, the
request body of `POST /api/v1/journeys` -- and zero responses reference `JourneyCreate`. Treating that as
an anchor would let the panel claim a field the experience response never promised.

So the status per class is computed from `two_contracts_r1.json`:
  ANCHORED_ON_RESPONSE    the hand contract declares the field inside the response schema of the endpoint
  DECLARED_ON_REQUEST_ONLY the name exists in a contract, but only as a request-body property
  ABSENT_IN_BOTH          neither document names it anywhere as a property

Outputs both, from the same run: the reading for the ledger and the next order, and the e2e module the
gate asserts against.
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
TWO = os.path.join(EV, "two_contracts_r1.json")
TSDST = os.path.join(WT, "frontend", "e2e", "_qoderUnanchoredClasses.ts")

EXPERIENCE = "/api/v1/journeys/{journeyId}/experience"
WALLET = "/api/v1/journeys/{journeyId}/wallet"

# key, endpoint the item reads, field it would name, contract property name to look for,
# and the JSON-pointer prefix a *response-side* declaration would have to sit under
CANDIDATES = [
    ("plan_feasibility_open", EXPERIENCE, "experience_flags.feasibility_failures", "feasibility_failures",
     "nothing further needed -- it is declared inside the experience response"),
    ("recovery_needs_decision", EXPERIENCE, "recovery.requires_user_decision", "requires_user_decision",
     "nothing further needed -- RecoveryState is referenced by the experience response"),
    ("stay_budget_undeclared", EXPERIENCE, "trip.stay_budget.declared", "stay_budget",
     "declare `stay_budget` on the experience response (today it exists only as `JourneyCreate/properties/stay_budget`, i.e. on the write side)"),
    ("stay_chosen_but_unconfirmed", WALLET, "reservations / commitments", "reservations",
     "give the wallet route a response schema with `reservations` and `commitments`; both the hand route and the generated one answer `{type: object}` / `{}`"),
    ("stay_not_chosen", EXPERIENCE, "selected_option_id", "selected_option_id",
     "declare `selected_option_id` on the experience response"),
    ("no_active_plan", EXPERIENCE, "active_plan", "active_plan",
     "declare `active_plan` on the experience response (today the concept appears only in route prose)"),
    ("arrival_anchor_missing", EXPERIENCE, "trip.arrival_anchor.at", "arrival_anchor",
     "declare `arrival_anchor` on the experience response (today only `JourneyCreate/properties/arrival_anchor`, the write side)"),
    ("departure_anchor_missing", EXPERIENCE, "trip.departure_anchor.at", "departure_anchor",
     "declare `departure_anchor` on the experience response (today only `JourneyCreate/properties/departure_anchor`, the write side)"),
    ("offline_pack_not_ready", WALLET, "offline_ready", "offline_ready",
     "declare `offline_ready` on the wallet response"),
]

HAND_RESPONSE_SCHEMA = {EXPERIENCE: "/journeys/{journey_id}/experience", WALLET: "/journeys/{journey_id}/wallet"}


def hand_route_block(lines, endpoint):
    """The hand contract's line range for the route's own block, or None."""
    route = HAND_RESPONSE_SCHEMA[endpoint]
    start = next((n for n, l in enumerate(lines, 1) if l.strip().startswith(route + ":")), None)
    if start is None:
        return None
    end = next((n for n in range(start + 1, len(lines) + 1)
                if n <= len(lines) and re.match(r"^  /", lines[n - 1])), len(lines) + 1)
    return start, end


def hand_component_block(lines, name):
    """The line range of `components/schemas/<name>:` , or None."""
    start = next((n for n, l in enumerate(lines, 1)
                  if re.match(r"^    %s:\s*$" % re.escape(name), l)), None)
    if start is None:
        return None
    end = next((n for n in range(start + 1, len(lines) + 1)
                if n <= len(lines) and re.match(r"^    \S", lines[n - 1])), len(lines) + 1)
    return start, end


def hand_declared_under_response(lines, name, endpoint):
    """
    Is `name:` declared where this endpoint's response can actually carry it?

    Two ways that happens in the hand contract, and both count: written inline inside the route block,
    or written inside a component schema the route block pulls in with `$ref`. Skipping the second would
    have mis-classified `recovery.requires_user_decision` as un-anchored, because RecoveryState is declared
    once under `components/schemas` and referenced from the experience response.
    """
    blk = hand_route_block(lines, endpoint)
    if blk is None:
        return None, None
    start, end = blk
    scope = lines[start - 1:end - 1]
    pat = re.compile(r"(^|[{,\s])" + re.escape(name) + r"\s*:")
    for off, line in enumerate(scope):
        if pat.search(line):
            return start + off, "inline"
    for ref in set(re.findall(r"\$ref:\s*'#?/?components/schemas/(\w+)'", "\n".join(scope))):
        cblk = hand_component_block(lines, ref)
        if not cblk:
            continue
        cs, ce = cblk
        for off, line in enumerate(lines[cs - 1:ce - 1]):
            if pat.search(line):
                return cs + off, "via $ref %s" % ref
    return None, None


def main():
    head = subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    two = json.load(io.open(TWO, encoding="utf-8"))
    byfield = {r["field"]: r for r in two["fields"]}
    lines = io.open(CONTRACT, encoding="utf-8").read().splitlines()
    rows = []
    for key, endpoint, field, probe, needs in CANDIDATES:
        g = byfield[probe]
        resp_line, via = hand_declared_under_response(lines, probe, endpoint)
        req_only = g["generated_declared"] and all("/properties/" in p and "Create" in p
                                                   for p in g["generated_paths"])
        if resp_line:
            status, where = "ANCHORED_ON_RESPONSE", "contracts/openapi.yaml:%d (%s)" % (resp_line, via)
        elif req_only:
            status, where = "DECLARED_ON_REQUEST_ONLY", g["generated_paths"][0]
        elif g["generated_declared"]:
            status, where = "DECLARED_OUTSIDE_RESPONSE", g["generated_paths"][0]
        else:
            status, where = "ABSENT_IN_BOTH", "-"
        rows.append({"key": key, "endpoint": endpoint, "field": field, "contract_probe_name": probe,
                     "status": status, "anchor_coordinate": where, "anchor_via": via,
                     "hand_declared_under_response_line": resp_line,
                     "generated_paths": g["generated_paths"], "generated_path_count": g["generated_path_count"],
                     "what_would_anchor": needs})
    anchored = [r["key"] for r in rows if r["status"] == "ANCHORED_ON_RESPONSE"]
    unanchored = [r["key"] for r in rows if r["status"] != "ANCHORED_ON_RESPONSE"]
    out = {"generated_by": os.path.basename(__file__), "order": "ORD-0384", "commit": head,
           "hand_contract_sha256": hashlib.sha256(io.open(CONTRACT, "rb").read()).hexdigest(),
           "generated_contract_sha256": two["generated_sha256"],
           "generated_experience_200_schema": "empty object -- see two_contracts_r1.json",
           "candidates": len(rows), "anchored_count": len(anchored), "unanchored_count": len(unanchored),
           "anchored_keys": anchored, "unanchored_keys": unanchored, "rows": rows,
           "rule": "an anchor is a declaration on the response side of the endpoint the item reads. "
                   "A name that exists only under a request-body schema (JourneyCreate) is not one."}
    io.open(os.path.join(EV, "unanchored_classes_r2.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    ts = ["/* GENERATED by review/n3_0384_unanchored_list_r2.py -- do not edit by hand.",
          " *",
          " * ORD-0384 re-scoped: the checklist may only show an item whose field is declared on the",
          " * RESPONSE side of the endpoint it reads. Measured against BOTH contracts in the repo (the",
          " * hand-written contracts/openapi.yaml and the document FastAPI generates), because a name can",
          " * exist only under `JourneyCreate/properties/` -- the write side -- and that is not an anchor.",
          " * The gate asserts two things from this list: only ANCHORED_ITEM_KEYS ever render, and no",
          " * UNANCHORED_ITEM_KEYS string ever reaches the DOM.",
          " */",
          "",
          "export const UNANCHORED_MEASURED_AT_COMMIT = %r;" % head,
          "export const UNANCHORED_HAND_CONTRACT_SHA256 = %r;" % out["hand_contract_sha256"],
          "export const UNANCHORED_GENERATED_CONTRACT_SHA256 = %r;" % out["generated_contract_sha256"],
          "export const ANCHORED_ITEM_KEYS: readonly string[] = [%s];" % ", ".join('"%s"' % k for k in anchored),
          "export const UNANCHORED_ITEM_KEYS: readonly string[] = [%s];" % ", ".join('"%s"' % k for k in unanchored),
          "export const UNANCHORED_CLASSES: ReadonlyArray<{ key: string; endpoint: string; field: string;",
          "  status: string; anchor_coordinate: string; why_no_anchor: string; what_would_anchor: string }> = [",
          ]
    for r in rows:
        if r["status"] == "ANCHORED_ON_RESPONSE":
            continue
        why = {"DECLARED_ON_REQUEST_ONLY": "declared only on the request body: %s (%d occurrence(s)), and no response references it"
                                          % (r["anchor_coordinate"], r["generated_path_count"]),
               "DECLARED_OUTSIDE_RESPONSE": "declared somewhere the item does not read: %s" % r["anchor_coordinate"],
               "ABSENT_IN_BOTH": "named by neither contract as a property anywhere"}[r["status"]]
        ts.append("  { key: %r, endpoint: %r, field: %r, status: %r, anchor_coordinate: %r, why_no_anchor: %r, what_would_anchor: %r },"
                  % (r["key"], r["endpoint"], r["field"], r["status"], r["anchor_coordinate"], why, r["what_would_anchor"]))
    ts += ["];", ""]
    io.open(TSDST, "w", encoding="utf-8", newline="\n").write("\n".join(ts))
    for r in rows:
        print("%-28s %-26s %s" % (r["key"], r["status"], r["anchor_coordinate"]))
    print("ANCHORED_ON_RESPONSE %d of %d: %s" % (len(anchored), len(rows), ", ".join(anchored)))
    print("NOT ANCHORED %d: %s" % (len(unanchored), ", ".join(unanchored)))
    print("READING " + os.path.join(EV, "unanchored_classes_r2.json").replace("\\", "/"))
    print("WROTE " + TSDST.replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
