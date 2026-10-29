"""bw295: which tree has a refusal statement pasted into that docstring?

bw294 read this shift's own tree (D:/moodle/_cmdr_rescue_v3_1022) and found the refusal only at
746/782/787/789/799, with lines 142/146/147 holding table-name strings.  Lines 141-148 with code
inside the docstring therefore belong to a different tree, and the operator may well be looking at the
classroom or the reference one.  This ruler reads the same relative path across every tree this
project keeps on disk, in one pass, and prints per tree: byte hash, mtime, git head, where the
refusal statements actually sit, what lines 141-148 contain, and whether that file parses.

Read-only.  Nothing here edits any tree.
"""

import ast
import hashlib
import io
import os
import subprocess
import sys

REL = os.path.join("backend", "app", "services.py")
RECEIPT = os.path.join(r"D:/moodle/_cmdr_rescue_v3_1022", "trial", "results", "20261026_gozero",
                       "bw295-services-across-trees.txt")
REFUSAL = "return UNRESOLVED_ACTIVITY_FACTS"
DOCSTRING_MARK = "def _place_has_unresolved_opening"

TREES = [
    ("rescue (this shift)", r"D:/moodle/_cmdr_rescue_v3_1022"),
    ("classroom", r"E:/_cmdr_clean_1028"),
    ("tip", r"E:/_cmdr_tip_113"),
    ("reference", r"D:/moodle/_qoder_cmdr_ref_20260921"),
    ("frozen CityNexus", r"D:/moodle/CityNexus"),
]


def head_of(tree):
    done = subprocess.run(["git", "-C", tree, "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True)
    return done.stdout.strip() or "not a git tree"


def survey(tree, out):
    path = os.path.join(tree, REL)
    if not os.path.exists(path):
        out.append("  NO SUCH FILE in this tree")
        return
    raw = io.open(path, "rb").read()
    text = raw.decode("utf-8", errors="replace")
    lines = text.split("\n")
    hits = [index + 1 for index, row in enumerate(lines) if row.strip() == REFUSAL]
    def_hits = [index + 1 for index, row in enumerate(lines) if row.startswith(DOCSTRING_MARK)]
    try:
        ast.parse(text)
        parsed = "parses"
    except SyntaxError as exc:
        parsed = "SYNTAX_ERROR at line %s" % exc.lineno
    out.append("  bytes=%d sha256=%s mtime=%s head=%s (%s)"
               % (len(raw), hashlib.sha256(raw).hexdigest()[:12],
                  subprocess.run(["git", "-C", tree, "log", "-1", "--format=%ad",
                                  "--date=format:%m-%d %H:%M", "--", REL],
                                 capture_output=True, text=True).stdout.strip()
                  or os.path.getmtime(tree),
                  head_of(tree), parsed))
    out.append("  refusal lines=%s  def lines=%s" % (hits, def_hits))
    inside = [index + 1 for index, row in enumerate(lines[140:148], start=141)
              if row.strip() == REFUSAL]
    out.append("  refusal inside lines 141-148: %s" % (inside or "NONE"))
    out.append("  lines 141-148 verbatim:")
    for index in range(141, min(149, len(lines)) + 1):
        out.append("      %4d| %s" % (index, lines[index - 1][:96]))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = ["services.py ACROSS EVERY TREE ON DISK bw295", "relative path %s" % REL]
    for label, tree in TREES:
        out.append("%s :: %s" % (label, tree))
        survey(tree, out)
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for row in out:
        print(row)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
