"""ORD-0417 lane: turn a Playwright `--reporter=list` log into a per-arm receipt.

Why this exists rather than reading the log by eye: the duty order asks for every arm named with its
result, and "the summary says 17 passed" does not name anything.  This joins the run's result lines
against the arms `--list` enumerated for the same spec, so an arm that never ran shows up as a named
gap instead of disappearing into a total.  It refuses to print a verdict when the two denominators
disagree -- a count I cannot reconcile is not a count I am allowed to publish.
"""
import io
import json
import re
import sys

LOG = sys.argv[1]
LIST_ARMS = sys.argv[2]
OUT = sys.argv[3]

# The `list` reporter writes `  ok  3 [chromium] › e2e\file.ts:271:3 › tap-named-zh — title (8.4s)`
# and `  x  N …` for a failure, `-` for a skipped test.  (An earlier version of this parser looked for
# ✓/✘ glyphs, which the `line` reporter uses but `list` does not -- it then reported 0 of 17 arms and
# the DENOMINATOR_MISMATCH verdict caught it, which is the whole reason the verdict is computed.)
RESULT = re.compile(
    r"^\s*(ok|x|-)\s+\d+\s+\[chromium\]\s+›\s+\S*tap-names-the-stop\.spec\.ts:\d+:\d+\s+›\s+(.+?)(?:\s+\([\d.]+m?s\))?\s*$"
)
GLYPH = re.compile(r"^\s*(ok|x|-)\s")
STATUS = {"ok": "passed", "x": "failed", "-": "skipped"}

arms = []
for line in io.open(LIST_ARMS, encoding="utf-8").read().splitlines():
    if "tap-names-the-stop.spec.ts" in line and "›" in line:
        arms.append(line.split("›")[-1].strip())

results = {}
skipped = []
for raw in io.open(LOG, encoding="utf-8", errors="replace").read().splitlines():
    m = RESULT.match(raw)
    if not m:
        continue
    status = STATUS.get(m.group(1), "?")
    title = m.group(2).strip()
    results[title] = {"glyph": m.group(1), "status": status}

missing = [a for a in arms if a not in results]
extra = [a for a in results if a not in arms]
summary = {
    "arms_listed": len(arms),
    "arms_reported": len(results),
    "passed": sum(1 for v in results.values() if v["status"] == "passed"),
    "failed": sum(1 for v in results.values() if v["status"] == "failed"),
    "skipped": sum(1 for v in results.values() if v["status"] == "skipped"),
    "listed_but_never_ran": missing,
    "ran_but_not_listed": extra,
}
if len(arms) != len(results) or missing or extra:
    summary["verdict"] = "DENOMINATOR_MISMATCH"
else:
    summary["verdict"] = "ALL_ARMS_ACCOUNTED"

payload = {"arms": [{ "arm": a, "status": results.get(a, {}).get("status", "NOT_RUN") } for a in arms],
           "summary": summary}
io.open(OUT, "w", encoding="utf-8", newline=chr(10)).write(json.dumps(payload, indent=1, ensure_ascii=False))
print(json.dumps(summary, ensure_ascii=False))
