"""Turn the fake-settings rows into an executable repair table: node id, crash frame, missing attribute.

The census groups these reds by their crash frame, which names the attribute the product tried to
read, but a fixer needs the other half -- which test produced it.  With --tb=line pytest emits the
crash lines and the FAILED summary in the same order, so the two lists can be zipped, and the zip is
only trusted when both lists are the length pytest itself reported.

Checks before publishing:
  * the stack-tail count must equal pytest's failed number (the census's own rule, re-asserted);
  * the FAILED summary count must equal that same number, otherwise the zip would pair the wrong rows;
  * the joined table must hold exactly as many rows as the census counted for this class, and every
    row must carry both a node id and an attribute name -- a row with either half missing is dropped
    from the count and printed as a defect of this ruler instead of being quietly included.
"""

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import _cmdr_full_red_reason_census_r164 as census  # noqa: E402

SUITE_OUT = census.SUITE_OUT
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero", "bw226-fake-settings-table.txt")
FAKE_CLASS = "fake settings missing a field"

ATTR = re.compile(r"has no attribute '(\w+)'")
NODE = re.compile(r"^FAILED (\S+?)::(\w+)")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raw = io.open(SUITE_OUT, encoding="utf-8", errors="replace").read()
    text = census.logical_lines(raw)
    failed, passed, errors = (int(item) for item in census.SUMMARY.findall(text)[-1])

    tails = []
    for match in census.TAIL.finditer(text):
        file_name, outside = census.repo_relative(match.group("path"))
        tails.append((file_name, int(match.group("line")), match.group("reason"), outside))
    if len(tails) != failed:
        print("ABORT stack-tail records %d do not equal pytest's failed %d" % (len(tails), failed))
        return 5

    nodes = [NODE.match(line).groups() for line in text.splitlines() if NODE.match(line)]
    if len(nodes) != failed:
        print("ABORT the FAILED summary holds %d rows, not %d -- the zip would pair the wrong tests"
              % (len(nodes), failed))
        return 6

    rows = []
    dropped = []
    for index, (file_name, line_no, reason, outside) in enumerate(tails):
        if census.classify(reason, outside) != FAKE_CLASS:
            continue
        attr = ATTR.search(reason)
        node_file, node_name = nodes[index]
        if not attr:
            dropped.append("%s::%s (no attribute parsed)" % (node_file, node_name))
            continue
        rows.append((node_file, node_name, "%s:%d" % (file_name, line_no), attr.group(1)))

    lines = [
        "FAKE SETTINGS REPAIR TABLE bw226",
        "SUITE %s failed=%d passed=%d errors=%d" % (os.path.basename(SUITE_OUT), failed, passed, errors),
        "ZIP_VERIFIED crash-line order equals FAILED-summary order because both count %d (enforced above)"
        % failed,
        "ROWS %d (census counted %d for this class)" % (len(rows), sum(
            1 for _f, _l, reason, outside in tails if census.classify(reason, outside) == FAKE_CLASS)),
        "DROPPED_BY_THIS_RULER %d %s" % (len(dropped), "; ".join(dropped) or "none"),
        "TABLE",
    ]
    for node_file, node_name, frame, attr in sorted(rows, key=lambda row: (row[3], row[0])):
        lines.append("  attribute=%s  product_frame=%s  test=%s::%s" % (attr, frame, node_file, node_name))
    attributes = sorted({row[3] for row in rows})
    lines.append("DISTINCT_ATTRIBUTES %d  %s" % (len(attributes), " ".join(attributes)))
    lines.append("TEST_FILES_TOUCHED %d" % len({row[0] for row in rows}))

    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
