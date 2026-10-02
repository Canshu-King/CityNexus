"""前置单 -- turn the six Playwright reports (four neighbours on the day15 stack, two controls on this
lane's own stack) into one arm table, computed from the artifacts.

Two columns on purpose. The day15 stack is the commander's :4783/:4787 pair -- the generation the order
names. The control column re-runs the two footprint/map neighbours against byte-identical bundle bytes
(see day15_stack_proof_r1.json: the entry asset the front serves hashes the same as the dist this lane
built from the same commit) over a private database whose demo trip is still standing. Where the two
columns disagree, the difference is the store, not the generation, and this table is what says so
without me asserting it.
"""
import glob
import io
import json
import os
import re
import sys

RUN = "D:/moodle/_qoder_e766b154_ord0528_20261001/run"


EXPECTED_FILE = {
    "ord0502": "qoder-ord0502-phone-mainline.spec.ts",
    "ord0497": "qoder-bac10f40-ord0497-footprints-on-map.spec.ts",
    "ord0530": "qoder-bac10f40-ord0530-footprints-by-day.spec.ts",
    "ord0537": "qoder-bac10f40-ord0537-map-toggle-reach.spec.ts",
}


def walk(report):
    rows = []

    def visit(node):
        for spec in node.get("specs", []) or []:
            for test in spec.get("tests", []) or []:
                for result in test.get("results", []) or []:
                    message = ""
                    for key in ("errors", "error"):
                        bag = result.get(key)
                        if not bag:
                            continue
                        for item in (bag if isinstance(bag, list) else [bag]):
                            if isinstance(item, dict):
                                message = str(item.get("message") or item.get("value") or "")
                            else:
                                message = str(item)
                            if message:
                                break
                        if message:
                            break
                    first = message.splitlines()[0] if message else ""
                    locator = re.search(r"waiting for (.+)", message)
                    rows.append({
                        "file": spec.get("file", ""),
                        "arm": spec.get("title", ""),
                        "state": result.get("status", ""),
                        "duration_ms": result.get("duration", 0),
                        "first_error_line": first[:200],
                        "locator_wait": (locator.group(1)[:160] if locator else None),
                    })
        for suite in node.get("suites", []) or []:
            visit(suite)

    visit(report)
    return rows


def load(path):
    if not os.path.exists(path):
        return {"MISSING": path}
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main():
    table = {}
    # Three columns, one rule: the report file names the stack it came from, and the table is keyed by
    # that. day15 = the commander's shared stack, control = this lane's store with the same bytes,
    # cur16 = the authoritative tip with one pristine store per neighbour.
    for kind, pattern in (("day15", "report_neighbors_%s.json"), ("control", "report_control_%s.json"), ("cur16", "report_cur16_%s.json")):
        for stem in ("ord0502", "ord0497", "ord0530", "ord0537"):
            path = os.path.join(RUN, pattern % stem)
            if not os.path.exists(path):
                continue
            report = load(path)
            rows = walk(report)
            # A report is only this stem's if every row names this stem's file -- titles are not
            # identity (the ORD-0502 cells are titled C1..C7b, the footprint ones carry the order id),
            # and the file name is what the config matched on.
            wrong = sorted({r["file"] for r in rows if not r["file"].endswith(EXPECTED_FILE[stem])})
            if wrong or not rows:
                print("REFUSED %s/%s: rows=%d files_not_this_spec=%s" % (kind, stem, len(rows), wrong))
                sys.exit(3)
            table["%s/%s" % (kind, stem)] = {
                "arms": len(rows),
                "passed": len([r for r in rows if r["state"] == "passed"]),
                "failed": len([r for r in rows if r["state"] == "failed"]),
                "timed_out": len([r for r in rows if r["state"] == "timedOut"]),
                "rows": rows,
            }

    walk_files = sorted(glob.glob(os.path.join(RUN, "neighbors_ord0502/walk-*.json")))
    walks = {}
    for path in walk_files:
        with io.open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        walks[os.path.basename(path)] = {
            "chain": data.get("chain"),
            "cells_recorded": len(data.get("readings", [])),
            "cells_declared_in_file": len(data.get("cells", [])),
            "recorded": [r.get("cell") for r in data.get("readings", [])],
        }

    out = {"per_generation": table, "ord0502_walk_artifacts": walks}
    with io.open(os.path.join(RUN, "neighbors_summary_r1.json"), "w", encoding="utf-8") as handle:
        json.dump(out, handle, indent=1, ensure_ascii=False)

    print("walk_artifacts: %s" % json.dumps(walks, ensure_ascii=False)[:300])
    for key in sorted(table):
        entry = table[key]
        print("%s arms=%s passed=%s failed=%s timed_out=%s"
              % (key, entry["arms"], entry["passed"], entry["failed"], entry["timed_out"]))
        for row in entry["rows"]:
            if row["state"] != "passed":
                print("   [%s] %s :: %s" % (row["state"], row["arm"][:58], row["first_error_line"][:90]))
    print("WROTE %s" % os.path.join(RUN, "neighbors_summary_r1.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
