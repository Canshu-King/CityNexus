"""One ledger that maps every red in the run to a node id and a cause class, so rulings can be batched.

Class counts alone cannot be acted on: the commander needs "these node ids, this cause, this fix
side".  This joins pytest's crash lines to its FAILED summary (same order, both counts required to
equal the run's own failed number), applies the class table from the census plus the three
refinements measured today, and prints per-class node lists.

Refinements applied, each backed by a measurement elsewhere in this shift rather than by taste:
  * a KeyError off a private door is the bearer-less family, unless the missing key is error_type,
    which the product only sets on exception paths (section 14.13, bw213);
  * any refusal naming DEMO_DATABASE_NOT_ISOLATED or DEMO_PRESENTER_REQUIRED is filed under the
    classroom/demo door, whose behaviour under environment-only arms was measured in bw223.

Everything is refused rather than guessed if the arithmetic does not close: distinct node ids must
equal the crash-line count, and the class buckets must sum to it.
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
import _cmdr_full_red_reason_census_r195 as extended  # noqa: E402

RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero", "bw234-red-node-ledger.txt")
NODE = re.compile(r"^FAILED (\S+)")
DEMO_DOOR = "classroom/demo door refuses (fixture declares neither isolation nor presenter)"
KEYERR = "answer lacks a key the test reads (KeyError off the server body)"
CREDENTIAL = "bearer-less private read (measured this shift)"


GUARD = "invariant guard names its own drift (side per-case, section 14.11)"
NAMED_NOT_MEASURED = "cause named by the extended ruler, side not measured"
UNEXPLAINED = "neither cause nor side measured"


def refined_class(reason, base_class):
    if "DEMO_DATABASE_NOT_ISOLATED" in reason or "DEMO_PRESENTER_REQUIRED" in reason:
        return DEMO_DOOR
    if "KeyError:" in reason or base_class == KEYERR:
        return KEYERR if "error_type" in reason else CREDENTIAL + " -- KeyError shape off the 401 body (bw213)"
    if base_class == "not yet attributed":
        # cross-read the extended ruler so the two published artifacts cannot disagree about the same row
        extra = extended.classify_extra(reason)
        if extra is None:
            return UNEXPLAINED
        label, _counted, _needle = extra
        return GUARD if label.startswith("invariant guard") else NAMED_NOT_MEASURED + " (" + label + ")"
    return base_class


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = census.logical_lines(io.open(census.SUITE_OUT, encoding="utf-8", errors="replace").read())
    failed, passed, errors = (int(item) for item in census.SUMMARY.findall(text)[-1])

    tails = []
    for match in census.TAIL.finditer(text):
        file_name, outside = census.repo_relative(match.group("path"))
        tails.append((file_name, int(match.group("line")), match.group("reason"), outside))
    nodes = [NODE.match(line).groups() for line in text.splitlines() if NODE.match(line)]
    if len(tails) != failed or len(nodes) != failed:
        print("ABORT crash lines %d / FAILED rows %d / pytest failed %d do not agree"
              % (len(tails), len(nodes), failed))
        return 5
    distinct = {pair[0] for pair in nodes}
    if len(distinct) != failed:
        print("ABORT %d distinct node ids for %d failures; two rows would be double counted"
              % (len(distinct), failed))
        return 6

    buckets = {}
    for index, (file_name, line_no, reason, outside) in enumerate(tails):
        base = census.classify(reason, outside)
        node = nodes[index]
        buckets.setdefault(refined_class(reason, base), []).append(node)
    if sum(len(v) for v in buckets.values()) != failed:
        print("ABORT the buckets do not add up to the failed count")
        return 7

    fixture_side = [name for name in buckets if name.startswith(("bearer-less", "door answers 401",
                  "body iterated", "answer lacks a key", "classroom/demo", "fake settings",
                  "credential refused"))]
    unknown = [name for name in buckets if name.startswith("not yet attributed")
                 or name.startswith("neither cause") or name.startswith("cause named by")
                 or name.startswith("invariant guard")]
    lines = [
        "RED NODE LEDGER bw234",
        "SUITE %s failed=%d passed=%d errors=%d" % (os.path.basename(census.SUITE_OUT), failed, passed, errors),
        "DISTINCT_NODE_IDS %d (must equal failed, enforced above)" % len(distinct),
        "BUCKETS %d sum=%d (enforced equal failed above)" % (len(buckets), sum(len(v) for v in buckets.values())),
        "FIXTURE_SIDE_TOTAL %d rows across %d buckets" % (
            sum(len(buckets[name]) for name in fixture_side), len(fixture_side)),
        "PRODUCT_OR_SEED_SIDE_TOTAL %d rows across %d buckets (identified cause, product or seed side)" % (
            failed - sum(len(buckets[n]) for n in fixture_side) - sum(len(buckets[n]) for n in unknown),
            len(buckets) - len(fixture_side) - len(unknown)),
        "SIDE_UNKNOWN_TOTAL %d rows across %d buckets -- the side was not measured for these (some"
        " carry a named cause from the extended ruler), so none is counted as a product defect" % (
            sum(len(buckets[n]) for n in unknown), len(unknown)),
    ]
    for name in sorted(buckets, key=lambda key: -len(buckets[key])):
        members = sorted(buckets[name])
        if name in fixture_side:
            tag = "fixture-side"
        elif name in unknown:
            tag = "side not measured"
        else:
            tag = "product/seed-side"
        lines.append("BUCKET %s | %d rows | %s" % (name, len(members), tag))
        lines += ["    %s" % node for node in members]
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines[:14]:
        print(line)
    print("... %d lines total, written for batched rulings" % len(lines))
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
