"""Prove that every file the shift documents cite can actually be retrieved from the repository.

The coordinate gate only inspects ledger blocks, so a report can still cite a receipt that was never
committed, or one that .gitignore swallows (that happened to a .log this shift).  Documents also cite
short names like 'aw39-390-failure-named.png' without a directory, so the check resolves a citation
either by its exact path or by its basename among tracked files, and only calls a citation bad when
no tracked file answers to it at all.  States are reported separately, never merged into one number.
"""

import io
import os
import re
import subprocess
import sys

TREE = r"D:\moodle\_cmdr_rescue_v3_1022"
DOCS = [
    r"trial\results\20261026_GO_FROM_BLANK_REPORT.md",
    r"trial\results\20261027_GO_FROM_BLANK_DELIVERY.md",
    r"trial\results\20261029_COST_UNKNOWN_UNREACHABLE_ANALYSIS.md",
    r"trial\results\20261029_SESSION_RECOVERY_IS_BY_DESIGN.md",
    r"trial\results\20261029_BACKEND_CERTIFICATE_24a342198d.md",
]
CITED = re.compile(r"[\w./\\-]*\.(?:txt|md|py|mjs|json|png|yml|ts|tsx)\b")
RECEIPT = os.path.join(TREE, "trial", "results", "20261026_gozero", "by179-cited-artifact-audit.txt")


def git(*args):
    return subprocess.run(
        ["git", "-C", TREE] + list(args), capture_output=True, text=True, errors="replace"
    ).stdout.split()


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    tip = git("rev-parse", "HEAD")[0]
    tracked = git("ls-files")
    tracked_set = set(tracked)
    by_basename = {}
    for path in tracked:
        by_basename.setdefault(os.path.basename(path), []).append(path)
    untracked = set(git("ls-files", "--others", "--exclude-standard"))
    ignored = set(git("ls-files", "--others", "--ignored", "--exclude-standard"))

    citations = {}
    scanned = 0
    for doc in DOCS:
        path = os.path.join(TREE, doc)
        if not os.path.exists(path):
            continue
        scanned += 1
        text = io.open(path, encoding="utf-8", errors="replace").read()
        for match in CITED.findall(text):
            name = match.replace("\\", "/").lstrip("./")
            if name.startswith("/"):
                continue
            citations.setdefault(name, set()).add(os.path.basename(doc))

    states = {}
    bad = []
    shortened = 0
    for name in sorted(citations):
        if name in tracked_set:
            state = "tracked-at-cited-path"
        elif os.path.basename(name) in by_basename:
            state = "tracked-under-a-different-path"
            shortened += 1
        elif name.replace("/", os.sep) in ignored or os.path.basename(name) in {
            os.path.basename(p) for p in ignored
        }:
            state = "gitignored-so-never-committed"
        elif name.replace("/", os.sep) in untracked or os.path.basename(name) in {
            os.path.basename(p) for p in untracked
        }:
            state = "present-but-untracked"
        else:
            state = "no-file-answers-to-the-name"
        states[state] = states.get(state, 0) + 1
        if state in ("gitignored-so-never-committed", "present-but-untracked", "no-file-answers-to-the-name"):
            bad.append((state, name, sorted(citations[name])))
    lines = [
        "CITED ARTIFACT RETRIEVABILITY AUDIT by179",
        "TIP %s" % tip,
        "DOCS_SCANNED %d" % scanned,
        "TRACKED_FILES_IN_REPO %d" % len(tracked_set),
        "DISTINCT_CITED_NAMES %d" % len(citations),
        "BY_STATE %s" % ", ".join("%s=%d" % item for item in sorted(states.items())),
        "SHORT_FORM_CITATIONS %d (retrievable, but the document names no directory)" % shortened,
        "NOT_RETRIEVABLE %d" % len(bad),
    ]
    for state, name, docs in bad:
        lines.append("  %s  %s  (cited by %s)" % (state, name, ",".join(docs)))
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
