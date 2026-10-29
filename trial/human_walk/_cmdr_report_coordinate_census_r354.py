"""Census every file:line coordinate the walk report cites and say, per coordinate, whether it retrieves.

The Q43 door judges shape, not existence, so a report section can be full of green-verdict coordinates that
no reader can open.  This ruler reads the whole report once and sorts every citation:

  ok                the path is on disk and the line number is inside the file
  missing_prefix    the path is not on disk, but the same tail is under frontend/src/ - a dropped prefix
  out_of_range      the path is on disk but the cited line is past its end
  nowhere           neither the path nor a prefixed twin exists at all

Line one carries the tally and its own line number, so a block can cite this sheet at a coordinate that does
not move when the sheet is re-run.  A coordinate that reads ok here is not proof the reading is right - only
that a reader can open it.
"""

import io
import os
import re
import subprocess
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REPORT_REL = "trial/results/20261026_GO_FROM_BLANK_REPORT.md"
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw342-are-the-report-coordinates-retrievable.txt")
PATTERN = re.compile(r"((?:trial|frontend|backend|live_checks|tests)/[A-Za-z0-9_./-]+"
                     r"\.(?:txt|md|py|tsx|ts|json|spec\.ts)):(\d+)")
PREFIXES = ("", "frontend/src/", "frontend/", "backend/")


def exists_with_prefixes(path):
    for prefix in PREFIXES:
        candidate = prefix + path if prefix else path
        if os.path.exists(os.path.join(ROOT, candidate.replace("/", os.sep))):
            return candidate
    return None


def main(receipt=RECEIPT) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    lines = io.open(os.path.join(ROOT, REPORT_REL.replace("/", os.sep)), encoding="utf-8",
                    errors="replace").read().split("\n")
    counts = {"ok": 0, "missing_prefix": 0, "out_of_range": 0, "nowhere": 0}
    # every bucket needs a row even when it is empty: an absent bucket reads the same as an unmeasured one
    rows = dict((state, []) for state in counts)
    total = 0
    for index, cell in enumerate(lines, start=1):
        for path, line in PATTERN.findall(cell):
            total += 1
            resolved = exists_with_prefixes(path)
            if resolved is None:
                state = "nowhere"
                detail = "no such path, with or without a prefix"
            else:
                length = len(io.open(os.path.join(ROOT, resolved.replace("/", os.sep)), encoding="utf-8",
                                     errors="replace").read().split("\n"))
                if int(line) > length:
                    state, detail = "out_of_range", "file holds %d lines" % length
                elif resolved != path:
                    state, detail = "missing_prefix", "retrieves as %s" % resolved
                else:
                    state, detail = "ok", "opens as cited"
            counts[state] += 1
            rows.setdefault(state, []).append((index, path, int(line), detail))
    if sum(counts.values()) != total:
        raise SystemExit("ABORT the buckets read %d while the scan found %d coordinates"
                         % (sum(counts.values()), total))
    distinct = len(set((row[1], row[2]) for bucket in rows.values() for row in bucket))

    out = ["REPORT COORDINATE RETRIEVABILITY CENSUS bw342 | PLACEHOLDER_TALLY",
           "report %s lines=%d" % (REPORT_REL, len(lines))]
    for state in ("ok", "missing_prefix", "out_of_range", "nowhere"):
        out.append("")
        out.append("BUCKET %s = %d" % (state, counts[state]))
        for index, path, line, detail in rows[state][:40]:
            out.append("  report:%d  %s:%d  %s" % (index, path, line, detail))
        if len(rows[state]) > 40:
            out.append("  (%d more in this bucket, printed count capped at 40)" % (len(rows[state]) - 40))
    sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    if subprocess.run(["git", "-C", ROOT, "cat-file", "-t", sha], capture_output=True, text=True,
                      check=True).stdout.strip() != "commit":
        raise SystemExit("ABORT the cited object is not a commit")
    tally_line = len(out) + 3  # blank, VERDICT, then the tally is appended right after this rewrite
    out[0] = out[0].replace("PLACEHOLDER_TALLY",
                            "TALLY_LINE %d | coordinates %d distinct %d ok %d missing_prefix %d "
                            "out_of_range %d nowhere %d"
                            % (tally_line, total, distinct, counts["ok"], counts["missing_prefix"],
                               counts["out_of_range"], counts["nowhere"]))
    out.append("")
    out.append("VERDICT the buckets cover every coordinate scanned; a coordinate reading ok here only means "
               "a reader can open it, not that the reading it supports is right")
    out.append("TALLY coordinates=%d distinct=%d ok=%d missing_prefix=%d out_of_range=%d nowhere=%d"
               % (total, distinct, counts["ok"], counts["missing_prefix"], counts["out_of_range"],
                  counts["nowhere"]))
    out.append("GENERATION %s" % sha)
    out.append("")
    io.open(receipt, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    landed = io.open(receipt, encoding="utf-8", errors="replace").read().split("\n")
    anchor = re.match(r"^.*TALLY_LINE (\d+) \| coordinates (\d+) distinct (\d+) ok (\d+) "
                      r"missing_prefix (\d+) out_of_range (\d+) nowhere (\d+)", landed[0])
    if not anchor:
        raise SystemExit("ABORT line one lost the self-anchor blocks are told to cite")
    pointed = landed[int(anchor.group(1)) - 1]
    if pointed != "TALLY coordinates=%s distinct=%s ok=%s missing_prefix=%s out_of_range=%s nowhere=%s" \
            % anchor.groups()[1:]:
        raise SystemExit("ABORT the self-anchor points at %r, not at its own tally" % pointed[:70])
    print("STABLE_ANCHOR line 1 -> line %s reads %s" % (anchor.group(1), pointed))
    for row in out[:6] + out[-4:]:
        print(row)
    for state in ("missing_prefix", "out_of_range", "nowhere"):
        for index, path, line, detail in rows[state][:12]:
            print("  %s  report:%d %s:%d  %s" % (state, index, path, line, detail))
    print("WROTE %s" % receipt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
