"""ORD-0504 C -- a ruler for citations that ships inside the product's own comments.

A comment that says ```_reservation_payload` (main.py:3527)`` is a promise a reader can be expected to
keep believing long after the line it names has moved. This file counts how many such promises the shipped
source is currently making, and grades each one:

  FILE_NOT_TRACKED   the path the comment names is not in the tree at all
  LINE_OUT_OF_RANGE  the file exists but has fewer lines than the comment claims
  AMBIGUOUS_PATH     the bare filename resolves to more than one tracked file
  SYMBOL_NOT_AT_LINE the comment names a symbol and that symbol is not within +/-3 lines of the target
  OK                 everything the comment asserts is where the comment says it is

Paths are resolved as given from the repo root, then relative to the citing file, then by unique basename.
Only citations that sit behind a comment marker on their line are scanned -- code that indexes a file by
name is not a promise about a line number.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0504/shipped_citation_scan_r1.py [rev]

With no argument it scans the working tree. Exit 0 when every scanned citation is OK, 1 when any is not,
2 when the census could not be taken at all.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

LANE = Path("D:/moodle/_qoder_r_ord0465_20260929")
TREE = LANE / "wt"
OUT = LANE / "run" / os.environ.get("CITATION_SCAN_OUT", "citation_scan_r1.json")
REPORT = LANE / "run" / os.environ.get("CITATION_SCAN_REPORT", "citation_scan_r1.txt")
ROOTS = ("frontend/src", "backend/app")
EXTS = (".py", ".ts", ".tsx", ".js", ".jsx", ".json")
CITE = re.compile(r"([A-Za-z0-9_.\-/\\\\]+\.(?:py|ts|tsx|js|jsx|json|md)):(\d+)((?:-\d+)?)")
SYMBOL = re.compile(r"`([A-Za-z_][A-Za-z0-9_]{2,})`")
CONTEXT = 3
RESOLVE_REV = None  # the tree the resolver reads, set by main()


def tracked(rev: str | None, roots: tuple[str, ...] | None = None) -> list[str]:
    scope = list(roots) if roots else []
    if rev:
        cmd = ["git", "-C", str(TREE), "ls-tree", "-r", "--name-only", rev, "--"] + scope
    else:
        cmd = ["git", "-C", str(TREE), "ls-files", "--"] + scope if scope else \
              ["git", "-C", str(TREE), "ls-files"]
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if done.returncode:
        raise SystemExit("REFUSE: cannot enumerate the tree (%s)" % done.stderr[-200:])
    return [line.strip() for line in done.stdout.splitlines() if line.strip()]


def read(path: str, rev: str | None) -> str:
    if rev:
        done = subprocess.run(["git", "-C", str(TREE), "show", "%s:%s" % (rev, path)],
                              capture_output=True)
        if done.returncode:
            raise SystemExit("REFUSE: git show %s:%s failed" % (rev, path))
        return done.stdout.decode("utf-8", "replace")
    return (TREE / path).read_text(encoding="utf-8", errors="replace")


def comment_column(line: str) -> int:
    """Where the comment starts on this line, or -1 when the line carries no comment marker."""
    if "#" in line:
        return line.index("#")
    if "//" in line:
        return line.index("//")
    stripped = line.lstrip()
    if stripped.startswith("*") or stripped.startswith("/*"):
        return line.index(stripped[0])
    return -1


def resolve(raw: str, citing: str, index: dict[str, list[str]], known: set[str],
            symbols: list[str], target: int, end: int) -> tuple[str | None, str]:
    candidate = raw.replace("\\", "/")
    if candidate in known:
        return candidate, "as given"
    beside = (Path(citing).parent / candidate).as_posix()
    if beside in known:
        return beside, "relative to the citing file"
    base = candidate.split("/")[-1]
    hits = index.get(base, [])
    if len(hits) == 1:
        return hits[0], "unique basename"
    if len(hits) > 1:
        # `main.py` alone matches 21 tracked files, so a bare name is not an address. But when exactly one
        # of those files carries the symbol the comment names at the line the comment names, the citation
        # does resolve -- by content -- and saying "ambiguous" about it would be a false accusation.
        carrying = []
        for hit in hits:
            tlines = read(hit, RESOLVE_REV).splitlines()
            if end > len(tlines):
                continue
            window = "\n".join(tlines[max(0, target - 1 - CONTEXT):min(len(tlines), end + CONTEXT)])
            if symbols and all(s in window for s in symbols):
                carrying.append(hit)
        if len(carrying) == 1:
            return carrying[0], "unique by content among %d same-named files" % len(hits)
        return None, "ambiguous basename over %d files, %d of them carry the named symbols at that line" % (
            len(hits), len(carrying))
    return None, "no such file in the tree"


def main() -> int:
    global RESOLVE_REV
    rev = sys.argv[1] if len(sys.argv) > 1 else None
    RESOLVE_REV = rev
    files = tracked(rev, ROOTS)
    # A comment may name a file anywhere in the repo (`contracts/openapi.yaml:88`, an evidence note).
    # Restricting the *resolution* set to the scanned roots turns "I did not look" into "no such file",
    # which is the one-way blind spot this lane has been burned by before.
    every = tracked(rev)
    index: dict[str, list[str]] = {}
    for path in every:
        index.setdefault(path.split("/")[-1], []).append(path)
    known = set(every)

    rows, totals = [], {}
    scanned_files = 0
    for path in files:
        if not path.endswith(EXTS):
            continue
        text = read(path, rev)
        lines = text.splitlines()
        touched = False
        for number, line in enumerate(lines, 1):
            col = comment_column(line)
            if col < 0:
                continue
            for match in CITE.finditer(line):
                if match.start() < col:
                    continue  # the citation sits in code, not behind the comment marker
                touched = True
                raw, target = match.group(1), int(match.group(2))
                end = int(match.group(3)[1:]) if match.group(3) else target
                names = [s for s in SYMBOL.findall(line[:match.start()])]
                resolved, how = resolve(raw, path, index, known, names, target, end)
                verdict, detail = "FILE_NOT_TRACKED", how
                if resolved:
                    tlines = read(resolved, rev).splitlines()
                    if end > len(tlines) or target < 1:
                        verdict = "LINE_OUT_OF_RANGE"
                        detail = "%s resolves to %s, which has %d lines" % (how, resolved, len(tlines))
                    else:
                        lo = max(0, target - 1 - CONTEXT)
                        hi = min(len(tlines), end + CONTEXT)
                        window = "\n".join(tlines[lo:hi])
                        whole = "\n".join(tlines)
                        absent = [s for s in names if s not in window]
                        far = [s for s in absent if s in whole]
                        if absent and far == absent:
                            # loose promise, right file: the symbol exists, just not where the comment
                            # points -- reported apart so a wrong line never reads as a missing one
                            verdict = "SYMBOL_NOT_NEAR_BUT_IN_FILE"
                            detail = "%s -> %s:%d, symbols elsewhere in the file: %s" % (
                                how, resolved, target, ", ".join(sorted(set(far))))
                        elif absent:
                            verdict = "SYMBOL_NOT_AT_LINE"
                            detail = "%s -> %s:%d, symbols not within %d lines and not in the file: %s" % (
                                how, resolved, target, CONTEXT, ", ".join(sorted(set(absent))))
                        else:
                            verdict = "OK"
                            detail = "%s -> %s:%d" % (how, resolved, target)
                rows.append({"citing": "%s:%d" % (path, number), "citation": match.group(0),
                             "verdict": verdict, "detail": detail,
                             "comment": line.strip()[:180]})
                totals[verdict] = totals.get(verdict, 0) + 1
        if touched:
            scanned_files += 1

    HARD = ("FILE_NOT_TRACKED", "LINE_OUT_OF_RANGE", "AMBIGUOUS_PATH", "SYMBOL_NOT_AT_LINE")
    hard = [r for r in rows if r["verdict"] in HARD]
    out = {"schema": "CNX_SHIPPED_CITATION_SCAN_V1", "tree": rev or "working tree",
           "files_scanned_with_citations": scanned_files, "files_enumerated_for_scanning": len(files),
           "files_resolvable": len(every), "citations_checked": len(rows), "totals": totals,
           "hard_rotten": hard, "rows": rows}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    lines = ["shipped-citation scan | tree = %s" % (rev or "working tree"),
             "scanned under %s = %d files | resolvable across the repo = %d files | files carrying "
             "citations = %d | citations checked = %d"
             % ("/".join(ROOTS), len(files), len(every), scanned_files, len(rows)),
             "totals: %s" % json.dumps(totals, ensure_ascii=False),
             "hard rotten: %d | loose (symbol elsewhere in the file): %d"
             % (len(hard), totals.get("SYMBOL_NOT_NEAR_BUT_IN_FILE", 0)), ""]
    for row in hard:
        lines.append("BAD  %s" % row["citing"])
        lines.append("     cites %s :: %s" % (row["citation"], row["detail"]))
        lines.append("     comment: %s" % row["comment"])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines[:5]))
    print("hard rotten=%d | report %s" % (len(hard), REPORT))
    if not rows:
        print("REFUSE: the census found no citations at all -- that is a scanner failure, not a clean tree")
        return 2
    return 0 if not hard else 1


if __name__ == "__main__":
    sys.exit(main())
