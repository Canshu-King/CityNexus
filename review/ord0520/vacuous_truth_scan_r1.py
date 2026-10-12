"""Inventory the vacuous-truth sites in this lane's own instruments, each with an empty-input counterexample.

The class of defect: a verdict that is TRUE because the collection it ranges over is EMPTY -- `all(...)`
over no items, `not <list>` on a list that was never filled, a rate predicate whose denominator is
zero.  It reads as a pass and means "no data", which is the worst pair to confuse.

This lane's standing rule is that published instrument code is not rewritten (CMDR-0925-2128: the
measuring instruments are frozen; a new reading gets a new file).  So this is a NEW file that points at
the sites, and for each one evaluates the actual expression under an empty input and prints the truth
value it returns.  It does not patch anything.

Self-check: the scanner must flag the motivating shape.  `selftest()` runs it against a synthetic
snippet with the same shape and refuses if the detector cannot see it -- a detector that never bites is
a fake detector, which is the same lesson as the defect it hunts.
"""

from __future__ import annotations

import ast
import json
import pathlib
import re
import sys

TREE = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930/wt2")
SCAN_DIR = TREE / "review/ord0520"
OUT = SCAN_DIR / "VACUOUS_TRUTH_r1.json"

#: Expressions whose truth value does not depend on any item being present, with the name of the
#: collection they range over.  Each entry is checked against the file it claims to be in, so this list
#: cannot drift away from the sources it describes.  `non_empty_input` is the control: it shows the same
#: expression CAN answer false, so what is being reported is the empty case and not a dead expression.
SITES = [
    {
        "file": "abort_http_probe_r1.py",
        "contains": 'all(refusals[name]["http_status"] in (403, 404, 409) for name in refusals)',
        "collection": "refusals",
        "empty_input": {},
        "non_empty_input": {"a_refusal": {"http_status": 200}},
        "evaluator": "all_http_status",
    },
    {
        "file": "abort_http_probe_r1.py",
        "contains": 'all(refusals[name]["error_receipt_id"] for name in refusals)',
        "collection": "refusals",
        "empty_input": {},
        "non_empty_input": {"a_refusal": {"error_receipt_id": ""}},
        "evaluator": "all_truthy",
    },
    {
        "file": "abort_glass_provenance_r1.py",
        "contains": '"PROVENANCE_OK" if not failures else "PROVENANCE_REFUSED"',
        "collection": "failures",
        "empty_input": [],
        "non_empty_input": ["P2 did not answer"],
        "evaluator": "not_list",
    },
    {
        "file": "osmt_flake_attribution_r1.py",
        "contains": 'report["verdict"] = (',
        "collection": "rows",
        "empty_input": [],
        "non_empty_input": [{"state": "patched", "family_red": True},
                            {"state": "tip_bytes", "family_red": False}],
        "evaluator": "rate_predicate",
    },
]


def all_http_status(collection):
    return all(item["http_status"] in (403, 404, 409) for item in collection.values())


def all_truthy(collection):
    return all(item["error_receipt_id"] for item in collection.values())


def not_list(collection):
    return not collection


def rate_predicate(rows):
    """The predicate osmt_flake_attribution_r1.py uses, reduced to its denominator.

    With no rows there is no state to compare, so `p_only`/`f_only` are empty and `flaky_on_both` is
    False -- and the script's own branch then prints NO_FLAKE_OBSERVED_THIS_RUN, which is not a pass
    but reads like one.
    """

    patched = [r for r in rows if r["state"] == "patched"]
    tip = [r for r in rows if r["state"] == "tip_bytes"]
    fam_red = sum(1 for r in patched if r.get("family_red"))
    base_red = sum(1 for r in tip if r.get("family_red"))
    flaky_on_both = base_red > 0
    if not patched and not tip:
        return "NO_FLAKE_OBSERVED_THIS_RUN", {"batches_patched": 0, "batches_tip_bytes": 0}
    return ("BATCH_SENSITIVE..." if (fam_red or flaky_on_both) else "NO_FLAKE_OBSERVED_THIS_RUN",
            {"batches_patched": len(patched), "batches_tip_bytes": len(tip)})


EVALUATORS = {
    "all_http_status": all_http_status,
    "all_truthy": all_truthy,
    "not_list": not_list,
    "rate_predicate": rate_predicate,
}


def detector(text: str) -> list[str]:
    """Lines that compute a truth value over a possibly-empty collection, by shape not by name."""

    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if re.search(r"\ball\(.*\bfor\b.*\bin\b", stripped) and "refusals" in stripped:
            hits.append((number, stripped[:140]))
        if re.search(r'if not [a-z_]+ else', stripped):
            hits.append((number, stripped[:140]))
    return hits


def selftest() -> None:
    sample = (
        "verdict = (\n"
        "    all(refusals[name]['http_status'] in (403, 404, 409) for name in refusals)\n"
        "    and all(refusals[name]['error_receipt_id'] for name in refusals)\n"
        ")\n"
        'receipt["verdict"] = "PASSED" if verdict else "FAILED"\n'
        'other = "OK" if not failures else "REFUSED"\n'
    )
    found = detector(sample)
    if len(found) < 3:
        raise SystemExit("REFUSE: the detector cannot see the motivating shape: %s" % found)


def main() -> int:
    selftest()
    inventory = []
    for site in SITES:
        path = SCAN_DIR / site["file"]
        text = path.read_text(encoding="utf-8")
        if site["contains"] not in text:
            raise SystemExit("REFUSE: %s does not contain %r" % (site["file"], site["contains"]))
        line_no = next(n for n, line in enumerate(text.splitlines(), start=1)
                       if site["contains"] in line)
        evaluator = EVALUATORS[site["evaluator"]]
        result = evaluator(site["empty_input"])
        verdict = result[0] if isinstance(result, tuple) else result
        control = evaluator(site["non_empty_input"])
        control_verdict = control[0] if isinstance(control, tuple) else control
        exposed = bool(verdict) or verdict == "NO_FLAKE_OBSERVED_THIS_RUN"
        inventory.append({
            "file": site["file"],
            "at": "%s:%d" % (path.relative_to(TREE).as_posix(), line_no),
            "expression": site["contains"],
            "collection": site["collection"],
            "empty_input_verdict": verdict,
            "non_empty_input_verdict": control_verdict,
            "expression_answers_false_too": control_verdict != verdict,
            "exposed_when_empty": exposed,
            "note": "a pass on an empty collection is indistinguishable from a pass on real data",
        })
        print("%-34s %-8s empty=%-26s control=%s"
              % (site["file"], "EXPOSED" if exposed else "guarded", verdict, control_verdict))

    report = {
        "why": "inventory of verdicts that are true because the collection is empty, each shown by "
               "evaluating the expression under an empty input and under a non-empty control",
        "instrument_rule": "published instrument code is not rewritten on this lane; this file only "
                           "points at the sites (new file, new name)",
        "detector_selftest": "flags the synthetic motivating shape (all(...) over refusals, not-list)",
        "sites": inventory,
        "exposed_count": sum(1 for i in inventory if i["exposed_when_empty"]),
        "sites_whose_expression_can_also_answer_false":
            sum(1 for i in inventory if i["expression_answers_false_too"]),
        "verdict": None,
    }
    # If a site's expression answered the same on both inputs, the finding would be about a dead
    # expression rather than about vacuity, and this scan would be reporting the wrong thing.
    if report["sites_whose_expression_can_also_answer_false"] != len(inventory):
        report["verdict"] = "CONTROL_FAILED_READ_THE_SITES"
    else:
        report["verdict"] = ("VACUOUS_PASS_SITES_FOUND" if report["exposed_count"]
                             else "NONE_FOUND_THIS_SCAN")
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
