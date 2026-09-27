#!/usr/bin/env python3
"""ORD-0384 -- for each checklist item, where its basis field is actually declared.

The order asks every item to name the endpoint and field that make it true. Measured against the live
:4781 responses that holds for all nine. Checked against `contracts/openapi.yaml` it does not: the
experience route types `trip` and `journey` as bare objects, and the wallet route gives its 200 as
`{type: object}` with no properties at all, so seven of the nine field paths exist only in the bytes the
server actually sends. That distinction decides whether a future contract-first change is allowed to
rename them, so it is recorded per item rather than asserted in prose.

A "property declaration" is counted only when the name is followed by a colon; a hit inside a
`description:` string is prose and says nothing about the payload shape.
"""
import io
import json
import os
import re
import sys

WT = r"D:/moodle/_qoder_n3_ord0357"
CONTRACT = os.path.join(WT, "contracts", "openapi.yaml")
EV = os.path.join(WT, "review", "evidence", "ord0384")
DERIVED = os.path.join(EV, "live_derivation_r2.json")

EXPERIENCE = "/api/v1/journeys/{journeyId}/experience"
WALLET = "/api/v1/journeys/{journeyId}/wallet"

# (item, endpoint, field the panel shows, the exact name to look for in the contract).
# The name is written out per row rather than derived from the dotted path: `trip.arrival_anchor.at`
# derives to `at`, which is not a field anybody would declare, and a silently wrong probe reads as
# "the contract does not name it" -- the very conclusion this receipt exists to make trustworthy.
ITEMS = [
    ("stay_budget_undeclared", EXPERIENCE, "trip.stay_budget.declared", "stay_budget"),
    ("plan_feasibility_open", EXPERIENCE, "experience_flags.feasibility_failures", "feasibility_failures"),
    ("stay_chosen_but_unconfirmed", WALLET, "reservations / commitments", "reservations"),
    ("stay_not_chosen", EXPERIENCE, "selected_option_id", "selected_option_id"),
    ("no_active_plan", EXPERIENCE, "active_plan", "active_plan"),
    ("recovery_needs_decision", EXPERIENCE, "recovery.requires_user_decision", "requires_user_decision"),
    ("arrival_anchor_missing", EXPERIENCE, "trip.arrival_anchor.at", "arrival_anchor"),
    ("departure_anchor_missing", EXPERIENCE, "trip.departure_anchor.at", "departure_anchor"),
    ("offline_pack_not_ready", WALLET, "offline_ready", "offline_ready"),
]


def declared(name):
    """(line, text) of the first `name:` property declaration in the contract, or (None, prose lines)."""
    lines = io.open(CONTRACT, encoding="utf-8").read().splitlines()
    prop = re.compile(r"(^|[{,\s])" + re.escape(name) + r"\s*:")
    for n, line in enumerate(lines, 1):
        if prop.search(line):
            return n, line.strip()[:120]
    prose = [n for n, line in enumerate(lines, 1) if name in line]
    return None, {"prose_only_lines": prose[:12], "prose_only_count": len(prose)}


def line_with(needle, start=1):
    """Line number of the first line at or after `start` holding `needle` -- computed, never typed."""
    for n, line in enumerate(io.open(CONTRACT, encoding="utf-8").read().splitlines(), 1):
        if n >= start and needle in line:
            return n
    return None


def main():
    derived = json.load(io.open(DERIVED, encoding="utf-8"))
    fired = set(derived["fired_keys"])
    live_coord = {r["key"]: r["coordinate"] for r in derived["rules"]}
    exp_path = line_with("/journeys/{journey_id}/experience:")
    wal_path = line_with("/journeys/{journey_id}/wallet:")
    trip_bare = line_with("trip: {type: object}", exp_path or 1)
    wal_200 = line_with("description: Confirmed reservations")
    rows = []
    for key, endpoint, field, leaf in ITEMS:
        line, detail = declared(leaf)
        rows.append({
            "key": key,
            "endpoint": endpoint,
            "field": field,
            "leaf_checked": leaf,
            "contract_declares_field": line is not None,
            "contract_line": line,
            "contract_evidence": detail,
            "live_response_carries_it": live_coord[key].split("@")[1] != "-1",
            "live_evidence_coordinate": live_coord[key],
            "fires_on_live": key in fired,
        })
    declared_n = sum(1 for r in rows if r["contract_declares_field"])
    out = {
        "generated_by": os.path.basename(__file__),
        "order": "ORD-0384",
        "contract": "contracts/openapi.yaml",
        "contract_sha256": __import__("hashlib").sha256(io.open(CONTRACT, "rb").read()).hexdigest(),
        "items": rows,
        "items_total": len(rows),
        "contract_declares_field_count": declared_n,
        "response_only_count": len(rows) - declared_n,
        "experience_route_line": exp_path,
        "wallet_route_line": wal_path,
        "trip_typed_as_bare_object_line": trip_bare,
        "wallet_200_schema_line": wal_200,
        "why_this_matters": "the experience route types `trip` as a bare object at "
                            "contracts/openapi.yaml:%s and the wallet route declares its 200 as an "
                            "unspecified object at contracts/openapi.yaml:%s, so a response-only field "
                            "name is pinned by no contract and can be renamed without the contract "
                            "noticing." % (trip_bare, wal_200),
    }
    p = os.path.join(EV, "basis_coverage_r1.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    for r in rows:
        print("%-28s %-9s contract=%-5s %s  live=%s" % (
            r["key"], "FIRED" if r["fires_on_live"] else "-",
            r["contract_line"] if r["contract_line"] else "NO",
            r["field"].ljust(42), r["live_evidence_coordinate"]))
    print("DECLARED %d of %d; RESPONSE-ONLY %d" % (declared_n, len(rows), len(rows) - declared_n))
    print("READING " + p.replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
