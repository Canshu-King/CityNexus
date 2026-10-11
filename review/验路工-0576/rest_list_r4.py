# -*- coding: utf-8 -*-
"""Turn an r2 census artifact into blob-verified coordinates for one file.

The census ruler locates pairs inside comment-masked text, and `strip_comments` at
live_checks/bilingual_pair_census_r2.py:63 appends one newline per `/*` opener, so its line number
equals the real line plus the openers above it (proved row-by-row in
review/验路工-0576/census_line_drift_probe_r3.txt).  Counts from the artifact are fine; coordinates
are not, so this inverts the offset and refuses any row that does not resolve to exactly one line.
"""
import json
import re
import subprocess
import sys

ARTIFACT = sys.argv[1]
NEEDLE = sys.argv[2] if len(sys.argv) > 2 else "LiveRecovery"
LITERAL = re.compile(r'"((?:[^"\\]|\\.)+)"')

data = json.load(open(ARTIFACT, encoding="utf-8"))
sha = data["sha"]
print("artifact_sha=%s files=%s totals=%s" % (sha, data["files_with_inline_pairs"], data["totals"]))

hits = [(k, v) for k, v in data["per_file"].items() if NEEDLE in k]
if not hits:
    print("ABORT needle matched no file in this artifact")
    sys.exit(3)

fail = 0
for path, rows in hits:
    blob = subprocess.run(["git", "-C", "D:/moodle/CityNexus", "show", "%s:%s" % (sha, path)],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if blob.returncode != 0:
        print("ABORT SHOW_FAIL %s:%s" % (sha, path))
        sys.exit(3)
    lines = blob.stdout.decode("utf-8", "replace").split("\n")

    def census_of(real_line):
        return real_line + sum(l.count("/*") for l in lines[: real_line - 1])

    arm_a = [r for r in rows if r[1] == "A"]
    print("FILE %s rows=%d arm_A=%d arm_B=%d" % (path, len(rows), len(arm_a), len(rows) - len(arm_a)))
    for cens_line, _arm, snip in arm_a:
        lits = [x for x in LITERAL.findall(snip) if x.strip()]
        cands = [i for i, ln in enumerate(lines, start=1)
                 if census_of(i) == cens_line and any(x[:14] in ln for x in lits)]
        if len(cands) == 1:
            print("  real=%d census=%d %s:%d | %s" % (cands[0], cens_line, path, cands[0], snip[:58].replace("\n", " ")))
        else:
            fail += 1
            print("  UNRESOLVED census=%d candidates=%d literals=%d | %s" % (
                cens_line, len(cands), len(lits), snip[:58].replace("\n", " ")))
print("unresolved=%d" % fail)
if fail:
    print("REFUSE the list is not clean -- do not plan a batch from it")
    sys.exit(4)
