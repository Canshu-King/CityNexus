"""Dump the source window around each sweep hit so classification quotes lines actually read,
not the ruler's rule name. Read-only: content comes from git show at the tip."""
import io
import json
import os
import subprocess
import sys

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
SCRATCH = os.path.join(ROOT, "_sweep_scratch")
REPO = "D:/moodle/CityNexus"


def main():
    tip = sys.argv[1]
    agg = json.load(io.open(os.path.join(SCRATCH, "aggregate.json"), encoding="utf-8"))
    cache = {}
    out = []
    for idx, h in enumerate(agg["hits"]):
        p = h["path"]
        if p not in cache:
            r = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (tip, p)], capture_output=True)
            cache[p] = r.stdout.decode("utf-8", "replace").splitlines()
        lines = cache[p]
        ln = h["line"]
        lo, hi = max(1, ln - 3), min(len(lines), ln + 9)
        out.append("=== HIT %02d  %s:%d  %s  (blob %s)" % (idx, p, ln, h["rule"], h["blob"]))
        for i in range(lo, hi + 1):
            mark = ">>" if i == ln else "  "
            out.append("%s %5d | %s" % (mark, i, lines[i - 1][:170]))
        out.append("")
    io.open(os.path.join(SCRATCH, "hit_context.txt"), "w", encoding="utf-8", newline="\n").write(
        "\n".join(out) + "\n")
    print("hits=%d lines=%d bytes=%d" % (len(agg["hits"]), len(out),
                                         os.path.getsize(os.path.join(SCRATCH, "hit_context.txt"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
