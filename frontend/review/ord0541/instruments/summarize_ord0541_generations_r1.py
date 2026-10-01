"""ORD-0541 lane -- build the delivery's generation table from the three Playwright JSON reports.

Every number here is read out of a report file this lane ran, not typed: per generation the arm name, the
Playwright state, the duration, and the first failing message line. The point is that the candidate is
green, the base is red, and the mutant is red on exactly the arm the tier ruling lives in -- and that
"which arm" is a fact taken from the artifact rather than from memory of running it.
"""
import io
import json
import sys

LANE = "D:/moodle/_qoder_e766b154_ord0528_20261001/run"
GENS = ["candidate", "base", "mutant"]
# Which trip of the ruler to summarise: the same three bundles are run more than once on purpose, and a
# reading that only exists for one trip is a reading to report twice, not to pick the nicer of.
PASS = sys.argv[1] if len(sys.argv) > 1 else "r2"


def walk(report):
    """Flatten Playwright's JSON into one row per test, keeping its failure message."""
    rows = []

    def visit(node):
        for spec in node.get("specs", []) or []:
            for test in spec.get("tests", []) or []:
                for result in test.get("results", []) or []:
                    # Playwright has shipped this under both `errors` (a list of objects or strings) and
                    # `error` (one object), and the message has moved between `message` and `value`
                    # across versions -- so all four shapes are read, and the table says which one hit.
                    message = ""
                    channel = ""
                    for key in ("errors", "error"):
                        bag = result.get(key)
                        if not bag:
                            continue
                        items = bag if isinstance(bag, list) else [bag]
                        for item in items:
                            if isinstance(item, dict):
                                for field in ("message", "value"):
                                    if item.get(field):
                                        message = str(item[field])
                                        channel = "%s.%s" % (key, field)
                                        break
                            else:
                                message = str(item)
                                channel = key
                            if message:
                                break
                        if message:
                            break
                    rows.append(
                        {
                            "arm": spec.get("title", ""),
                            "state": result.get("status", ""),
                            "duration_ms": result.get("duration", 0),
                            "error_channel": channel,
                            "first_error_line": message.splitlines()[0][:220] if message else "",
                        }
                    )
        for suite in node.get("suites", []) or []:
            visit(suite)

    visit(report)
    return rows


def main():
    table = {}
    for gen in GENS:
        path = "%s/report_ord0541_%s_%s.json" % (LANE, gen, PASS)
        try:
            with io.open(path, encoding="utf-8") as handle:
                report = json.load(handle)
        except (IOError, ValueError) as error:
            table[gen] = {"UNREADABLE": type(error).__name__ + " " + str(error)[:120]}
            continue
        rows = walk(report)
        # The rule bolted into this tool: a report is only this order's if every arm title in it says so.
        # The first cut of this file read `report_candidate.json`, which was yesterday's ORD-0528 run under
        # the same name, and printed its counts as if they were this order's -- so the check is on the
        # artifact, and a mismatch is a refusal rather than a number.
        foreign = [row["arm"] for row in rows if not row["arm"].startswith("ORD-0541")]
        if foreign:
            table[gen] = {
                "REFUSED": "report holds %d arm(s) not titled ORD-0541, first: %s"
                % (len(foreign), foreign[0][:80])
            }
            continue
        stats = report.get("stats", {}) or {}
        table[gen] = {
            "report_stats": {"expected": stats.get("expected"), "unexpected": stats.get("unexpected"),
                             "flaky": stats.get("flaky"), "skipped": stats.get("skipped")},
            "arms": len(rows),
            "passed": len([row for row in rows if row["state"] == "passed"]),
            "failed": len([row for row in rows if row["state"] == "failed"]),
            "rows": rows,
        }

    out = "%s/ord0541_generation_table_%s.json" % (LANE, PASS)
    with io.open(out, "w", encoding="utf-8") as handle:
        json.dump(table, handle, indent=1, ensure_ascii=False)

    lines = []
    for gen in GENS:
        entry = table[gen]
        if "UNREADABLE" in entry:
            lines.append("%s UNREADABLE %s" % (gen, entry["UNREADABLE"]))
            continue
        lines.append(
            "%s arms=%d passed=%d failed=%d" % (gen, entry["arms"], entry["passed"], entry["failed"])
        )
        for row in entry["rows"]:
            lines.append("   [%s] %s -- %s" % (row["state"], row["arm"][:64], row["first_error_line"][:120]))
    text = "\n".join(lines)
    with io.open("%s/ord0541_generation_table.txt" % LANE, "w", encoding="utf-8") as handle:
        handle.write(text + "\n")
    # The console is cp93b on this box and the arm titles are ASCII anyway, but the error lines can carry
    # CJK, so the printed copy is transcoded rather than risking a GBK blow-up after the file is written.
    print(text.encode("ascii", "replace").decode("ascii"))
    print("WROTE %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
