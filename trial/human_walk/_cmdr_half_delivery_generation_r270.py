"""bw270: for every imported-but-untracked pair, say which version already carries the import.

HEAD  -> the committed authoritative line is already broken
index -> the staged version carries it, so the next commit breaks the line
work-tree only -> nobody has asked git to ship it yet

This decides whether the half-delivery is an accident waiting to be committed or a defect
already published.  Read-only: git show and git status only.
"""

import io
import os
import re
import subprocess
import sys

TREE = r"D:\moodle\_cmdr_rescue_v3_1022"
RECEIPT = os.path.join(TREE, "trial", "results", "20261026_gozero",
                       "bw270-half-delivery-generation.txt")


def git_show(rev, path):
    res = subprocess.run(["git", "-C", TREE, "show", "%s:%s" % (rev, path)],
                         capture_output=True, text=True, errors="replace")
    return res.stdout if res.returncode == 0 else None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    census = io.open(os.path.join(TREE, "trial", "results", "20261026_gozero",
                                  "bw267-imported-but-untracked.txt"),
                     encoding="utf-8").read().splitlines()
    pairs = []
    importer = None
    for line in census:
        if line.startswith("  ") and "-> " not in line and line.strip().endswith(".tsx"):
            importer = line.strip()
        elif "-> " in line and importer:
            spec = re.search(r"imports\s+(\S+)", line).group(1)
            missing = line.split("->")[1].split("[")[0].strip()
            pairs.append((importer, spec, missing))
            importer = None

    rows = []
    for importer, spec, missing in sorted(set(pairs)):
        head_text = git_show("HEAD", importer)
        index_text = git_show("", importer)
        work_text = io.open(os.path.join(TREE, importer), encoding="utf-8",
                            errors="replace").read()
        quote = '"%s"' % spec
        rows.append((importer, spec, missing,
                     quote in (head_text or ""),
                     quote in (index_text or ""),
                     quote in work_text))

    in_head = [r for r in rows if r[3]]
    in_index_only = [r for r in rows if not r[3] and r[4]]
    work_only = [r for r in rows if not r[3] and not r[4]]
    lines = [
        "WHICH VERSION ALREADY CARRIES THE IMPORT bw270",
        "PAIRS %d" % len(rows),
        "ALREADY_IN_HEAD %d (the committed line cannot resolve these modules)" % len(in_head),
        "IN_INDEX_NOT_HEAD %d (the next commit would break the line)" % len(in_index_only),
        "WORK_TREE_ONLY %d (nothing published yet)" % len(work_only),
    ]
    for label, group in (("ALREADY_IN_HEAD", in_head),
                         ("IN_INDEX_NOT_HEAD", in_index_only),
                         ("WORK_TREE_ONLY", work_only)):
        lines.append(label)
        for importer, spec, missing, head, index, work in group:
            lines.append("  %-52s %-34s missing=%s head=%s index=%s work=%s"
                         % (importer, spec, missing, head, index, work))
    lines.append("DISTINCT_MISSING_MODULES %d"
                 % len(set(r[2] for r in rows)))
    for missing in sorted(set(r[2] for r in rows)):
        lines.append("  %s" % missing)
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
