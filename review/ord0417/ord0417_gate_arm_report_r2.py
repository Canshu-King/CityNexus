"""ORD-0417 lane: per-arm receipt for any spec (r2 of the arm reporter).

r1 hard-wired the map-page spec's file name into its regex, so it could not read the hub file's log --
the same mistake as a ruler that only fits the thing it was written for.  r2 takes the spec basename as
an argument and keeps the two properties that matter: the arms it reports are joined against the
`--list` denominator, and a mismatch is a REFUSE, not a smaller number.

usage: python ord0417_gate_arm_report_r2.py <log> <list-arms-file|-> <spec-basename> <out.json>
"""
import io
import json
import re
import sys

LOG, LISTED, BASE, OUT = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

RESULT = re.compile(
    r"^\s*(ok|x|-)\s+\d+\s+\[(?:chromium|setup)?\w*\]\s+›\s+\S*" + re.escape(BASE) + r"\.spec\.ts:\d+:\d+\s+›\s+(.+?)\s*$"
)
STATUS = {"ok": "passed", "x": "failed", "-": "skipped"}

arms = []
if LISTED != "-":
    for line in io.open(LISTED, encoding="utf-8").read().splitlines():
        if BASE + ".spec.ts" in line and "›" in line:
            arms.append(line.split("›")[-1].strip())

# The identity that joins the two files is the arm slug (everything before the em dash), not the whole
# title: the `--list` writer and the reporter both re-render the dash, and joining on prose turns a real
# 12-for-12 match into 12 phantom "never ran" rows.
slug = lambda title: title.split(" — ")[0].strip()


results = {}
for raw in io.open(LOG, encoding="utf-8", errors="replace"):
    m = RESULT.match(raw.rstrip())
    if m:
        results[slug(m.group(2).strip())] = STATUS.get(m.group(1), "?")

arms = [slug(a) for a in arms]

summary = {
    "spec": BASE,
    "arms_listed": len(arms),
    "arms_reported": len(results),
    "passed": sum(1 for v in results.values() if v == "passed"),
    "failed": sum(1 for v in results.values() if v == "failed"),
    "skipped": sum(1 for v in results.values() if v == "skipped"),
    "listed_but_never_ran": [a for a in arms if a not in results],
    "ran_but_not_listed": [a for a in results if arms and a not in arms],
}
if arms and (len(arms) != len(results) or summary["listed_but_never_ran"] or summary["ran_but_not_listed"]):
    summary["verdict"] = "DENOMINATOR_MISMATCH"
else:
    summary["verdict"] = "ALL_ARMS_ACCOUNTED" if arms else "NO_LIST_DENOMINATOR"

payload = {"arms": [{"arm": a, "status": results.get(a, "NOT_RUN")} for a in (arms or sorted(results))],
           "summary": summary}
io.open(OUT, "w", encoding="utf-8", newline=chr(10)).write(json.dumps(payload, indent=1, ensure_ascii=False))
print(json.dumps(summary, ensure_ascii=False)[:400])
