"""by305: take the 17 not-retrievable citations and say, one by one, what would fix each.

Section 14.24 reduced this family from 33 to 17 by committing this line's own artifacts.  The number
alone is not actionable: some of the remainder are citation wording that never matched a real file
(a name written with an ellipsis), some are files a .gitignore rule swallowed, some belong to the
frontend writer, and only some are this line's own to fix.  This ruler reads the audit receipt, pulls
each named item, searches the tree for the closest real file, and reports a candidate coordinate plus
the face that owns it, so the commander can point at one line per item instead of at a count.

Read-only: it searches, it does not add, rename, or delete anything.
"""

import difflib
import io
import os
import re
import subprocess
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
AUDIT = os.path.join(ROOT, "trial", "results", "20261026_gozero", "by179-cited-artifact-audit.txt")
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "by305-not-retrievable-one-by-one.txt")

LINE_RE = re.compile(r"^\s+(present-but-untracked|gitignored-so-never-committed|"
                     r"no-file-answers-to-the-name)\s+(\S+)\s+\(cited by ([^)]*)\)")
IGNORED = ("error-context.md", "test-results/", "playwright-report/", "node_modules/",
           "__pycache__", ".png", ".log")


def tracked_and_on_disk():
    """Everything git tracks, plus every untracked file on disk.

    The untracked set has to come from git itself: the audit reports some names as
    present-but-untracked under frontend/, and a pool limited to trial/ would deny those and read as
    a second ruler disagreeing with the first.
    """
    listing = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace").stdout.split("\n")
    names = [line for line in listing if line.strip()]
    status = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace").stdout
    for row in status.split("\n"):
        if row.startswith("?? "):
            rel = row[3:].strip().strip('"').replace("\\", "/")
            if rel and rel not in names:
                names.append(rel)
    return names


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    audit = io.open(AUDIT, encoding="utf-8", errors="replace").read()
    header = [row for row in audit.split("\n") if row.startswith("NOT_RETRIEVABLE")][:1]
    if not header:
        raise SystemExit("ABORT the audit receipt has no NOT_RETRIEVABLE line - re-run by179")
    declared = int(header[0].split()[-1])
    items = []
    for row in audit.split("\n"):
        match = LINE_RE.match(row)
        if match:
            items.append({"state": match.group(1), "name": match.group(2),
                          "cited_by": match.group(3).strip()})
    if len(items) != declared:
        raise SystemExit("ABORT the receipt declares %d but this ruler parsed %d - "
                         "fix the parser before publishing a per-item sheet"
                         % (declared, len(items)))

    pool = tracked_and_on_disk()
    basenames = {}
    for rel in pool:
        basenames.setdefault(os.path.basename(rel), []).append(rel)

    out = ["NOT-RETRIEVABLE CITATIONS, ONE BY ONE by305",
           "SOURCE %s (declared %d, parsed %d)"
           % (os.path.relpath(AUDIT, ROOT).replace("\\", "/"), declared, len(items)),
           "POOL searched: git-tracked files plus every file under trial/ (tracked or not)",
           ]
    tally = {}
    for item in items:
        name = item["name"]
        bare = name.replace("…", "")
        exact = basenames.get(name, [])
        candidates = []
        if not exact:
            # an ellipsis-written name: match the visible fragments against real basenames
            fragments = [part for part in name.split("…") if len(part) >= 4]
            for base_name, rels in basenames.items():
                if fragments and all(part.strip(".-/") in base_name for part in fragments[:2]):
                    candidates.extend(rels[:2])
            if not candidates:
                close = difflib.get_close_matches(name, list(basenames), n=2, cutoff=0.6)
                for hit in close:
                    candidates.extend(basenames[hit][:2])
        if exact:
            verdict = "name exists - the citation omits its directory"
            fix = "cite one of: " + ", ".join(sorted(set(exact))[:3])
            face = "this line" if any(rel.startswith("trial/") for rel in exact) else "another writer"
        elif any(marker in name for marker in IGNORED):
            verdict = "a rule ignores this shape, so it can never be committed"
            fix = "either unignore the path or stop citing it as retrievable evidence"
            face = "shared"
        elif candidates:
            verdict = "no exact match; closest real files listed"
            fix = "rewrite the citation to one of: " + ", ".join(sorted(set(candidates))[:3])
            face = "this line" if any(c.startswith("trial/") for c in candidates) else "another writer"
        else:
            verdict = "nothing on disk answers this name"
            fix = "the document cites an artifact that is not there - needs a correction note"
            face = "this line" if "trial" in item["cited_by"] or "BLANK" in item["cited_by"] else "unknown"
        tally[verdict] = tally.get(verdict, 0) + 1
        out.append("- %s  [%s]" % (name, item["state"]))
        out.append("    cited by %s | face: %s" % (item["cited_by"], face))
        out.append("    %s" % verdict)
        out.append("    %s" % fix)
    out.append("TALLY %s" % ", ".join("%s=%d" % (k, tally[k]) for k in sorted(tally)))
    mine = sum(1 for item in items)
    out.append("NOTE all %d rows are itemised above; nothing here was added, renamed or deleted."
               % mine)
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for row in out:
        print(row)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
