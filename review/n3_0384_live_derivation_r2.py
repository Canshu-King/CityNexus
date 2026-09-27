#!/usr/bin/env python3
"""ORD-0384 -- derive the live :4781 checklist from the saved responses, with locatable coordinates.

r1 pointed every claim at `live_experience.json:1`, which is not a coordinate: both payloads are
single-line JSON, so a line number carries no information. This version gives a byte offset into the
saved file for each deciding field, and it evaluates all nine items the module can produce rather than
the four r1 sampled, so the "3 fired" denominator is the real one.

The predicates are re-implemented here in Python from the module's source, independently of it. Nothing
is fetched; both files are read-only inputs.
"""
import hashlib
import io
import json
import os
import sys

EV = os.path.join(r"D:/moodle/_qoder_n3_ord0357", "review", "evidence", "ord0384")
EXP = os.path.join(EV, "live_experience.json")
WAL = os.path.join(EV, "live_wallet.json")
ABSENT = (None, "", "__ABSENT__")


def is_absent(v):
    return v is None or v == ""


def coord(path, raw, needle):
    """`basename@<byte offset>` of the first occurrence, plus how many times it occurs."""
    n = raw.encode("utf-8")
    i = n.find(needle.encode("utf-8"))
    return {
        "coordinate": "%s@%s" % (os.path.basename(path), i),
        "occurrences_of_the_key": n.count(needle.encode("utf-8")),
    }


def main():
    eraw = io.open(EXP, encoding="utf-8").read()
    wraw = io.open(WAL, encoding="utf-8").read()
    eb, wb = eraw.encode("utf-8"), wraw.encode("utf-8")
    exp, wal = json.loads(eraw), json.loads(wraw)

    trip = exp.get("trip") or {}
    flags = exp.get("experience_flags") or {}
    budget = trip.get("stay_budget")
    feas = flags.get("feasibility_failures")
    sel = exp.get("selected_option_id")
    res, com = wal.get("reservations"), wal.get("commitments")
    rec = exp.get("recovery") or {}
    src = lambda p, k: coord(p, eraw if p == EXP else wraw, k)

    rules = [
        ("stay_budget_undeclared", isinstance(budget, dict) and budget.get("declared") is None,
         budget.get("declared") if isinstance(budget, dict) else "NOT_AN_OBJECT",
         EXP, '"stay_budget"'),
        ("plan_feasibility_open", isinstance(feas, list) and len(feas) > 0,
         feas, EXP, '"feasibility_failures"'),
        ("stay_chosen_but_unconfirmed", not is_absent(sel) and res == [] and com == [],
         {"selected_option_id": sel, "reservations": res, "commitments": com},
         WAL, '"reservations"'),
        ("stay_not_chosen", is_absent(sel), sel, EXP, '"selected_option_id"'),
        ("no_active_plan", exp.get("active_plan") is None, type(exp.get("active_plan")).__name__,
         EXP, '"active_plan"'),
        ("recovery_needs_decision", rec.get("requires_user_decision") is True,
         rec.get("requires_user_decision", "KEY_NOT_PRESENT"), EXP, '"requires_user_decision"'),
        ("arrival_anchor_missing", is_absent((trip.get("arrival_anchor") or {}).get("at")),
         (trip.get("arrival_anchor") or {}).get("at"), EXP, '"arrival_anchor"'),
        ("departure_anchor_missing", is_absent((trip.get("departure_anchor") or {}).get("at")),
         (trip.get("departure_anchor") or {}).get("at"), EXP, '"departure_anchor"'),
        ("offline_pack_not_ready", wal.get("offline_ready") is False, wal.get("offline_ready"),
         WAL, '"offline_ready"'),
    ]
    evaluated = []
    for key, holds, value, path, needle in rules:
        evaluated.append({"key": key, "holds": bool(holds), "deciding_value": value, **src(path, needle)})
    fired = [r["key"] for r in evaluated if r["holds"]]

    out = {
        "generated_by": os.path.basename(__file__),
        "order": "ORD-0384",
        "source": "the two responses saved verbatim from the :4781 phone chain",
        "live_experience_bytes": len(eb),
        "live_experience_sha256": hashlib.sha256(eb).hexdigest(),
        "live_wallet_bytes": len(wb),
        "live_wallet_sha256": hashlib.sha256(wb).hexdigest(),
        "journey_id": wal.get("journey_id"),
        "candidate_items_the_module_can_produce": len(evaluated),
        "rules": evaluated,
        "fired_keys": fired,
        "fired_count": len(fired),
        "note": "live_experience.json and live_wallet.json are single-line JSON, so a line number is not "
                "a coordinate here; every claim below carries a byte offset into the named file instead.",
    }
    p = os.path.join(EV, "live_derivation_r2.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    for r in evaluated:
        print("%-28s holds=%-5s %-24s %s" % (r["key"], r["holds"], r["coordinate"], str(r["deciding_value"])[:44]))
    print("FIRED %d of %d: %s" % (len(fired), len(evaluated), ", ".join(fired)))
    print("READING " + p.replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
