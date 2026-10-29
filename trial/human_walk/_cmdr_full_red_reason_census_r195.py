"""Extend the whole-suite red census with named cause classes, without letting the labels float free.

The published census leaves fifty-four reds in 'not yet attributed'.  This second ruler reuses the
first one's grouping (it imports r164 rather than copying its parser) and adds classes that are each
keyed on a string taken verbatim out of a failure tail.  Three rules keep the extension honest:

  * reconciliation: the record count must still equal pytest's own failed number, and the reds that
    move out of 'not yet attributed' must land exactly in the new buckets -- no red disappears and no
    red is invented;
  * evidence: every new class prints the needle it matched and the number of groups it caught, so a
    reader can check the label against the message instead of trusting it;
  * honesty: a bucket that only says 'this guard names its own drift' is marked as needing a
    per-case read, and is NOT counted as an explained cause in the headline number.
"""

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import _cmdr_full_red_reason_census_r164 as census  # noqa: E402

RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero", "bw195-red-census-extended.txt")

# (label, needle read verbatim off a failure tail, is_this_an_explained_cause)
EXTRA_RULES = [
    ("demo door refused: product gate answers DEMO_DATABASE_NOT_ISOLATED",
     "DEMO_DATABASE_NOT_ISOLATED", True),
    ("private door refused: product gate answers TRAVELER_PRINCIPAL_VERIFIER_NOT_CONFIGURED",
     "TRAVELER_PRINCIPAL_VERIFIER_NOT_CONFIGURED", True),
    ("generic compose refused because a cost is unknown",
     "GENERIC_COMPOSE_INFEASIBLE", True),
    ("request body rejected by validation (VALIDATION_ERROR in the server answer)",
     '"code":"VALIDATION_ERROR"', True),
    ("answer lacks a key the test reads (KeyError off the server body)",
     "KeyError:", True),
    ("answer iterated as a mapping when the body is a string",
     "string indices must be integers", True),
    ("door answers 409 where the test expects 200",
     "assert 409 == 200", True),
    ("door answers 200 where the test expects 409",
     "assert 200 == 409", True),
    ("autonomy decided EXECUTED where the test expects confirmation",
     "'REQUIRE_CONFIRMATION' == 'EXECUTED'", True),
    ("test patches a module symbol the module no longer exports",
     "AttributeError: <module ", True),
    ("invariant guard prints its own drift; cause still needs the per-case read",
     "the order forbids changing this door", False),
]

# The guards below are the rows whose message already states what invariant broke.  They are put in
# one visible bucket, but that bucket is deliberately not counted as 'explained'.
GUARD_NEEDLES = (
    "the order forbids changing this door",
    "contract operations are absent from api.ts",
    "promised the anonymous read would not move one word",
    "CREDENTIAL_LITERAL_OUTSIDE_PRODUCT_PATH",
    "回执不落库是设计",
    "backend/tests/** 里没有对 provider 域名的真实调用",
    "期望：",
    "catalog_hydration_operations.py",
)


def classify_extra(reason):
    """(label, counted, needle) for the extended classes, or None when the tail still explains nothing."""
    for needle in GUARD_NEEDLES:
        if needle in reason:
            return ("invariant guard prints its own drift; cause still needs the per-case read", False, needle)
    for label, needle, counted in EXTRA_RULES:
        if needle in reason:
            return (label, counted, needle)
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not os.path.exists(census.SUITE_OUT):
        print("ABORT suite output missing at %s" % census.SUITE_OUT)
        return 3
    text = census.logical_lines(
        io.open(census.SUITE_OUT, encoding="utf-8", errors="replace").read()
    )
    summary = census.SUMMARY.findall(text)
    if not summary:
        print("ABORT no summary line, nothing to census")
        return 4
    failed, passed, errors = (int(item) for item in summary[-1])

    groups = {}
    for match in census.TAIL.finditer(text):
        file_name, outside = census.repo_relative(match.group("path"))
        reason = match.group("reason")
        key = (file_name, int(match.group("line")), census.signature(reason), outside)
        groups[key] = groups.get(key, 0) + 1
    total = sum(groups.values())
    if total != failed:
        print("ABORT records %d do not equal pytest's failed %d" % (total, failed))
        return 5

    base_by_class = {}
    moved = []
    for (file_name, line_no, reason, outside), count in groups.items():
        base = census.classify(reason, outside)
        base_by_class[base] = base_by_class.get(base, 0) + count
        if base != "not yet attributed":
            continue
        extra = classify_extra(reason)
        if extra is None:
            base_by_class["not yet attributed"] -= count
            base_by_class["still unexplained after the extended classes"] = (
                base_by_class.get("still unexplained after the extended classes", 0) + count
            )
            moved.append(("still unexplained after the extended classes", file_name, line_no, count, reason, ""))
        else:
            label, counted, needle = extra
            base_by_class["not yet attributed"] -= count
            base_by_class[label] = base_by_class.get(label, 0) + count
            moved.append((label, file_name, line_no, count, reason, needle))

    if base_by_class.get("not yet attributed", 0) != 0:
        print("ABORT the bucket did not empty exactly: %d left under the old label"
              % base_by_class["not yet attributed"])
        return 6

    # every new label must have been earned by a needle that is both declared for that label and
    # really present in the message it matched
    guard_label = "invariant guard prints its own drift; cause still needs the per-case read"
    declared = {}
    for label, needle, _counted in EXTRA_RULES:
        declared.setdefault(label, set()).add(needle)
    declared.setdefault(guard_label, set()).update(GUARD_NEEDLES)
    needle_proof = {}
    for (label, _file, _line, _count, reason, needle) in moved:
        if label.startswith("still unexplained"):
            continue
        if needle not in reason:
            print("ABORT label %r claims a needle that is not in the message it matched" % label)
            return 7
        if needle not in declared[label]:
            print("ABORT label %r matched an undeclared needle %r" % (label, needle))
            return 7
        needle_proof[label] = needle

    counted_explained = sum(
        count for (label, _f, _l, count, _r, _n) in moved
        if label in {name for name, _n, yes in EXTRA_RULES if yes}
    )
    guard_count = sum(
        count for (label, _f, _l, count, _r, _n) in moved if label == guard_label
    )
    still_count = sum(
        count for (label, _f, _l, count, _r, _n) in moved if label.startswith("still unexplained")
    )
    if counted_explained + guard_count + still_count != 54:
        print("ABORT the moved reds add up to %d, not the published bucket of 54"
              % (counted_explained + guard_count + still_count))
        return 8

    lines = [
        "WHOLE-SUITE RED CENSUS, EXTENDED CLASSES bw195",
        "SOURCE %s" % os.path.basename(census.SUITE_OUT),
        "SUMMARY failed=%d passed=%d errors=%d" % (failed, passed, errors),
        "STACK_TAIL_RECORDS %d (must equal failed, enforced above)" % total,
        "PREVIOUS_NOT_ATTRIBUTED 54 (re-used ruler r164, grouping imported from it)",
        "MOVED_TO_NAMED_CAUSE_CLASSES %d (needle proved present in each message)" % counted_explained,
        "MOVED_TO_INVARIANT_GUARD_BUCKET %d (message names the broken invariant, cause not yet read per case)"
        % guard_count,
        "STILL_UNEXPLAINED %d" % still_count,
        "RED BY CAUSE %s" % json.dumps(dict(sorted(base_by_class.items(), key=lambda item: -item[1])),
                                       sort_keys=False, ensure_ascii=False),
        "NEEDLES THAT EARNED EACH NEW LABEL",
    ]
    for label in sorted(needle_proof):
        lines.append("  %s  <-  %r" % (label, needle_proof[label]))
    lines.append("NEWLY ATTRIBUTED GROUPS")
    for label, file_name, line_no, count, reason, _needle in sorted(
        moved, key=lambda item: (item[0], -item[3])
    ):
        lines.append("  %3d x %s:%d [%s] %s" % (count, file_name, line_no, label, census.normalise(reason)[:110]))

    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines[:40]:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
