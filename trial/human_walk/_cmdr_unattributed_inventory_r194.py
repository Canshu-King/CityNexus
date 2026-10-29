"""Empty the 'not yet attributed' bucket into a named inventory, using the census ruler's own grouping.

The whole-suite census r164 reports how many reds it could NOT explain, but it prints only the ten
largest unexplained groups.  A bucket of fifty-four cannot be argued down from ten rows, so this
inventory walks every group the same ruler produced, keeps the ones it labelled 'not yet
attributed', and writes them all out with file, line and message shape.

Two things are enforced rather than assumed:
  * the classification comes from importing r164 itself, so the inventory cannot drift from the table
    it is supposed to explain;
  * the count in the inventory must equal the number the census receipt already published, and if it
    does not the run aborts instead of writing a second, different total.
"""

import importlib.util
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CENSUS_MODULE = os.path.join(HERE, "_cmdr_full_red_reason_census_r164.py")
CENSUS_RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero", "bw163-red-census.txt")
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero", "bw194-unattributed-inventory.txt")


def load_census():
    spec = importlib.util.spec_from_file_location("cmdr_census_r164", CENSUS_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def published_bucket():
    """The number the census already put on paper, read from its own receipt."""
    text = io.open(CENSUS_RECEIPT, encoding="utf-8", errors="replace").read()
    match = re.search(r"^RED BY CAUSE (.*)$", text, re.M)
    if not match:
        return None, "census receipt has no 'RED BY CAUSE' line"
    table = json.loads(match.group(1))
    return table.get("not yet attributed"), table


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    census = load_census()
    expected, table = published_bucket()
    if expected is None:
        print("ABORT %s" % table)
        return 4
    if not os.path.exists(census.SUITE_OUT):
        print("ABORT suite output missing at %s" % census.SUITE_OUT)
        return 3

    text = census.logical_lines(
        io.open(census.SUITE_OUT, encoding="utf-8", errors="replace").read()
    )
    groups = {}
    for match in census.TAIL.finditer(text):
        file_name, outside = census.repo_relative(match.group("path"))
        reason = match.group("reason")
        key = (file_name, int(match.group("line")), census.signature(reason), outside)
        groups[key] = groups.get(key, 0) + 1

    unattributed = [
        (key, count)
        for key, count in groups.items()
        if census.classify(key[2], key[3]) == "not yet attributed"
    ]
    found = sum(count for _key, count in unattributed)
    if found != expected:
        print(
            "ABORT inventory holds %d reds but the census published %d -- the two rulers disagree"
            % (found, expected)
        )
        return 6

    lines = [
        "UNATTRIBUTED RED INVENTORY bw194",
        "CENSUS_BUCKET %d (read from the published census receipt)" % expected,
        "INVENTORY_TOTAL %d (enforced equal above)" % found,
        "DISTINCT_UNATTRIBUTED_GROUPS %d" % len(unattributed),
        "FILES_TOUCHED %d" % len(set(key[0] for key, _count in unattributed)),
        "GROUPS",
    ]
    for (file_name, line_no, reason, outside), count in sorted(
        unattributed, key=lambda item: (-item[1], item[0][0], item[0][1])
    ):
        marker = "(library) %s:%d" % (file_name, line_no) if outside else "%s:%d" % (file_name, line_no)
        lines.append("  %3d x %s  %s" % (count, marker, census.normalise(reason)))

    by_file = {}
    for (file_name, _line, _reason, _outside), count in unattributed:
        by_file[file_name] = by_file.get(file_name, 0) + count
    lines.append("BY FILE")
    for file_name, count in sorted(by_file.items(), key=lambda item: (-item[1], item[0])):
        lines.append("  %3d x %s" % (count, file_name))

    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
