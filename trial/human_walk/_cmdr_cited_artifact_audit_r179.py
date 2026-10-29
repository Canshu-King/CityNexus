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
# A citation written straight after Chinese punctuation used to be cut at the first non-word
# character, so 'aw39-390-x-2.png' arrived as '-2.png' and was reported as a name no file answers to.
# A cited name now runs to the next delimiter instead.
CITED = re.compile(
    # Longest extension first: with 'ts' ahead of 'tsx' the alternation stopped at 'ts' and every
    # cited .tsx file came back as a .ts name that no file answers to.
    r"[^\s`'\"()（）,，。;：、|]*\.(?:tsx|ts|txt|md|mjs|py|json|png|yml)"
)
# Documents also contain paths that were never meant as evidence citations: shell templates like
# ${DIR}/x.png, globs like */.mjs, and names that start with a dash because a prefix was hyphenated
# in prose. Those are counted apart, so a scanner artefact never inflates the missing-evidence count.
NON_CITATION = re.compile(r"[$<>*{}|]|^-|\S[ -]?[^/\\]*\$\{")
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
        if NON_CITATION.search(os.path.basename(name)):
            states["not-a-citation-template-or-glob"] = states.get("not-a-citation-template-or-glob", 0) + 1
            continue
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
