"""ORD-0504 r5 -- a ruler for the shape that made the land gate report RECUT_ABORT.

`git merge-tree --write-tree` exits 0 on candidates the sequeucer then refuses, because an exit code
only answers "is there a textual conflict", not "how much of this file did the candidate touch". This
counts the second thing: lines are aligned with `difflib.SequenceMatcher` after stripping a trailing
CR from each, so

  * a row that matches once the CR is gone but differs byte-for-byte is an **ending-only rewrite** --
    churn on a row the candidate never edited, which a three-way merge cannot attribute to a hunk; and
  * `lines_added` / `lines_removed` say how much the candidate really brings.

A candidate whose ending-only rewrites are 0 can be re-hung onto the tip without reconciling; one
carrying them will keep being refused no matter how many times it is rebased.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0504/merge_shape_r5.py [rev-to-compare-against]

With no argument it compares against the tip this generation was cut on.
"""
from __future__ import annotations

import difflib
import json
import subprocess
import sys
from pathlib import Path

TREE = Path("D:/moodle/_qoder_r_ord0465_20260929/wt")
TIP = "569b8472b134e5562ef396e38681870b9c26536a"
OUT = TREE / "review" / "ord0504" / "merge_shape_r5.json"
PRODUCT_PREFIXES = ("frontend/", "backend/", "contracts/")


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=TREE, capture_output=True).stdout


def blob(rev: str, path: str):
    r = subprocess.run(["git", "show", "%s:%s" % (rev, path)], cwd=TREE, capture_output=True)
    return None if r.returncode else r.stdout


def scan(rev: str, path: str):
    mine = blob("HEAD", path)
    theirs = blob(rev, path)
    if theirs is None:
        return {"state": "new file on this side"}
    a, b = theirs.split(b"\n"), mine.split(b"\n")
    matcher = difflib.SequenceMatcher(None, [x.rstrip(b"\r") for x in a], [x.rstrip(b"\r") for x in b],
                                      autojunk=False)
    flipped = added = removed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            flipped += sum(1 for k in range(i2 - i1) if a[i1 + k] != b[j1 + k])
        elif tag == "replace":
            added += j2 - j1
            removed += i2 - i1
        elif tag == "insert":
            added += j2 - j1
        elif tag == "delete":
            removed += i2 - i1
    return {
        "state": "present on both sides",
        "ending_only_rewrites": flipped,
        "lines_added": added,
        "lines_removed": removed,
        "crlf_theirs": theirs.count(b"\r\n"),
        "crlf_mine": mine.count(b"\r\n"),
        "bare_lf_theirs": sum(1 for l in a if l and not l.endswith(b"\r")),
        "bare_lf_mine": sum(1 for l in b if l and not l.endswith(b"\r")),
    }


def main() -> int:
    rev = sys.argv[1] if len(sys.argv) > 1 else TIP
    touched = [f for f in git("diff", "--name-only", rev, "HEAD").decode("utf-8", "replace").splitlines() if f]
    product = [f for f in touched if f.startswith(PRODUCT_PREFIXES)]
    report = {
        "compared_against": rev,
        "tip_ref": "refs/heads/mirror/integration-frontend-apple-pass1",
        "head_under_test": git("rev-parse", "HEAD").decode().strip(),
        "files_vs_that_rev": len(touched),
        "product_files": len(product),
        "verdict_rule": "a candidate lands without reconciling when every product file reports 0 ending-only rewrites",
        "scans": {path: scan(rev, path) for path in product},
    }
    dirty = [p for p, s in report["scans"].items() if s.get("ending_only_rewrites")]
    report["files_with_ending_churn"] = dirty
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for path, s in report["scans"].items():
        print(path, s)
    print("files_with_ending_churn:", dirty or "none")
    return 1 if dirty else 0


if __name__ == "__main__":
    sys.exit(main())
