#!/usr/bin/env python3
"""ORD-0384 -- derive the checklist from any saved experience+wallet pair, with byte coordinates.

r1 and r2 were hard-wired to the Guangzhou journey's saved bytes. That journey was deleted from
`_preview.db` by `POST /api/v1/demo/reset` at 03:55, so the delivery needs to re-derive against
whatever the chain holds now and against a journey this lane builds itself. This takes the two files
and a label as arguments and writes one receipt per label.

The predicates are re-implemented in Python from `frontend/src/lib/pretripChecklist.ts`, independently
of that module: agreeing with the module by construction would make this a self-proof.

Both saved payloads are single-line JSON, so a line number carries nothing here; every claim gets a
byte offset into the named file instead.
"""
import hashlib
import io
import json
import os
import sys

EV = r"D:/moodle/_qoder_n3_ord0357/review/evidence/ord0384"
LABEL = sys.argv[1]
EXP = sys.argv[2]
WAL = sys.argv[3]
NOTE = sys.argv[4] if len(sys.argv) > 4 else ""


def is_absent(v):
    return v is None or v == ""


def offset(path, needle):
    raw = io.open(path, "rb").read()
    return raw.find(needle.encode("utf-8"))


def coord(path, needle):
    i = offset(path, needle)
    return {"coordinate": "%s@%s" % (os.path.basename(path), i),
            "occurrences": io.open(path, "rb").read().count(needle.encode("utf-8")) if i >= 0 else 0}


def main():
    eraw = io.open(EXP, "rb").read()
    wraw = io.open(WAL, "rb").read()
    exp = json.loads(eraw.decode("utf-8"))
    wal = json.loads(wraw.decode("utf-8"))
    trip = exp.get("trip") or {}
    flags = exp.get("experience_flags") or {}
    budget = trip.get("stay_budget")
    feas = flags.get("feasibility_failures")
    sel = exp.get("selected_option_id")
    res, com = wal.get("reservations"), wal.get("commitments")
    rec = exp.get("recovery") or {}
    anchors = {"arrival": (trip.get("arrival_anchor") or {}).get("at"),
               "departure": (trip.get("departure_anchor") or {}).get("at")}

    rules = [
        ("stay_budget_undeclared", isinstance(budget, dict) and budget.get("declared") is None,
         budget.get("declared") if isinstance(budget, dict) else "NOT_AN_OBJECT", EXP, '"stay_budget"'),
        ("plan_feasibility_open", isinstance(feas, list) and len(feas) > 0, feas,
         EXP, '"feasibility_failures"'),
        ("stay_chosen_but_unconfirmed",
         not is_absent(sel) and isinstance(res, list) and len(res) == 0
         and isinstance(com, list) and len(com) == 0,
         {"selected_option_id": sel, "reservations_n": len(res or []), "commitments_n": len(com or [])},
         WAL, '"reservations"'),
        ("stay_not_chosen", is_absent(sel), sel, EXP, '"selected_option_id"'),
        ("no_active_plan", exp.get("active_plan") is None, type(exp.get("active_plan")).__name__,
         EXP, '"active_plan"'),
        ("recovery_needs_decision", rec.get("requires_user_decision") is True,
         rec.get("requires_user_decision", "KEY_NOT_PRESENT"), EXP, '"requires_user_decision"'),
        ("arrival_anchor_missing", is_absent(anchors["arrival"]), anchors["arrival"], EXP, '"arrival_anchor"'),
        ("departure_anchor_missing", is_absent(anchors["departure"]), anchors["departure"],
         EXP, '"departure_anchor"'),
        ("offline_pack_not_ready", wal.get("offline_ready") is False, wal.get("offline_ready"),
         WAL, '"offline_ready"'),
    ]
    rows = []
    for key, holds, value, path, needle in rules:
        rows.append({"key": key, "holds": bool(holds), "deciding_value": value, **coord(path, needle)})
    fired = [r["key"] for r in rows if r["holds"]]
    j = (exp.get("journey") or {})
    out = {
        "generated_by": os.path.basename(__file__),
        "order": "ORD-0384",
        "label": LABEL,
        "note": NOTE,
        "experience_file": os.path.basename(EXP),
        "experience_bytes": len(eraw),
        "experience_sha256": hashlib.sha256(eraw).hexdigest(),
        "wallet_file": os.path.basename(WAL),
        "wallet_bytes": len(wraw),
        "wallet_sha256": hashlib.sha256(wraw).hexdigest(),
        "journey_identity": {k: j.get(k) for k in ("id", "title", "city_code", "status") if k in j},
        "candidate_items_the_module_can_produce": len(rows),
        "rules": rows,
        "fired_keys": fired,
        "fired_count": len(fired),
    }
    p = os.path.join(EV, "derive_%s_r1.json" % LABEL)
    io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print("label=%s journey=%s" % (LABEL, json.dumps(out["journey_identity"], ensure_ascii=False)))
    for r in rows:
        print("  %-28s holds=%-5s %-26s %s" % (r["key"], r["holds"], r["coordinate"], str(r["deciding_value"])[:40]))
    print("FIRED %d of %d: %s" % (len(fired), len(rows), ", ".join(fired) or "(none)"))
    print("READING " + p.replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
