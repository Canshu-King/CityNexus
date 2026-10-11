# -*- coding: utf-8 -*-
"""Read an r2 census artifact and print one file's remaining arm-A coordinates.

Why: a lane that wants the *next* three keys needs line numbers read off the generation it is
about to cut from.  A remembered list is already stale once the tip moves.
"""
import json
import sys

PATH = sys.argv[1]
NEEDLE = sys.argv[2] if len(sys.argv) > 2 else "LiveRecovery"

data = json.load(open(PATH, encoding="utf-8"))
print("sha=%s files=%s totals=%s" % (data["sha"], data["files_with_inline_pairs"], data["totals"]))

rows = [(k, v) for k, v in data["per_file"].items() if NEEDLE in k]
if not rows:
    print("ABORT needle matched no file -- this artifact is not evidence")
    sys.exit(3)

for path, hits in rows:
    a = [h for h in hits if h[1] == "A"]
    print("FILE %s rows=%d arm_A=%d arm_B=%d" % (path, len(hits), len(a), len(hits) - len(a)))
    for line, arm, snip in a:
        print("  A %s:%d | %s" % (path, line, snip[:70].replace("\n", " ")))
print("files_matched=%d" % len(rows))
