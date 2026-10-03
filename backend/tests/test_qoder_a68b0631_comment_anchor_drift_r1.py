"""Shipped guard for the comment-anchor drift order (rel lane a68b0631).

Two claims, both machine-checkable and neither one a judgement call:

  G1  every citation this lane un-numbered stays un-numbered.  The registry names file and line; if a
      line number is written back into that comment, this test goes red -- which is the counterexample
      the order asked for, kept live rather than demonstrated once in a block.
  G2  no citation anywhere in the shipped tree points at a file that does not exist, or at a line
      beyond the end of a file that does.  Those are unambiguously dead whatever the prose meant.

G2 deliberately does not try to decide whether a still-in-range line number "means" the right thing:
only the range check and the registry are asserted, so the guard can never manufacture a false green
by guessing at intent.
"""
import json
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "frontend" / "review" / "line_anchor_drift" / "CONVERTED_r1.txt"
CITE = re.compile(r"([A-Za-z0-9_./\\-]{0,80})\.(tsx|ts|py|cjs|mjs|js|json|yaml|yml|md|css|sql):(\d{1,6})(?:-\d{1,6})?")
COMMENT = re.compile(r"^\s*(//|\*|/\*|#|##|-|\s*\*/)")
SCAN_ROOTS = ["frontend/src", "frontend/e2e", "frontend/tools", "backend/app", "backend/tests",
              "backend/tools", "tools", "docs"]
SKIP = {"node_modules", ".git", "dist", "data", "test-results", ".venv", "__pycache__"}
EXTENSIONS = {".ts", ".tsx", ".py", ".js", ".cjs", ".mjs", ".md", ".css", ".sql", ".yaml", ".yml"}


def read_lines(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").split("\n")
    except OSError:
        return None


def resolve(part, ext, caller_dir):
    joined = (part or "") + "." + ext
    for cand in (os.path.normpath(os.path.join(caller_dir, joined)),
                 os.path.normpath(os.path.join(str(ROOT / "frontend"), joined)),
                 os.path.normpath(os.path.join(str(ROOT), joined))):
        if os.path.isfile(cand):
            return Path(cand)
    tail = (part.split("/")[-1] if part else "") + "." + ext
    for base in SCAN_ROOTS:
        for sub, dirs, files in os.walk(ROOT / base):
            dirs[:] = [d for d in dirs if d not in SKIP]
            if tail in files:
                return Path(sub) / tail
    return None


def test_G1_unnumbered_citations_stay_unnumbered():
    assert REGISTRY.is_file(), "the converted-citation registry is missing, so G1 has nothing to police"
    entries = [l for l in REGISTRY.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    assert len(entries) > 0, "the registry is empty"
    bad = []
    for entry in entries:
        rel, _, frag = entry.partition("	")
        lines = read_lines(ROOT / rel)
        if lines is None:
            bad.append("%s disappeared" % rel)
            continue
        hits = [i for i, l in enumerate(lines) if frag[:60] in l]
        if not hits:
            bad.append("%s no longer carries the converted comment %r, so the registry needs updating" % (rel, frag[:40]))
            continue
        for i in hits:
            m = CITE.search(lines[i])
            if m:
                bad.append("%s regained a line number: %s" % (rel, m.group(0)))
    assert not bad, "converted citations were re-numbered; a line anchor silently starts describing "                     "the wrong entry once the file moves: %s" % bad[:6]


def test_G2_no_dead_line_citation_survives_in_the_shipped_tree():
    dead = []
    for base in SCAN_ROOTS:
        if not (ROOT / base).is_dir():
            continue
        for sub, dirs, files in os.walk(ROOT / base):
            dirs[:] = [d for d in dirs if d not in SKIP]
            for f in files:
                if os.path.splitext(f)[1] not in EXTENSIONS:
                    continue
                path = Path(sub) / f
                lines = read_lines(path) or []
                for i, line in enumerate(lines):
                    if not COMMENT.match(line):
                        continue
                    for m in CITE.finditer(line):
                        target = resolve(m.group(1), m.group(2), sub)
                        n = int(m.group(3))
                        if target is None:
                            dead.append("%s:%d cites %s which is not in the tree" % (
                                path.relative_to(ROOT), i + 1, m.group(0)))
                            continue
                        tl = read_lines(target) or []
                        if n > len(tl):
                            dead.append("%s:%d cites %s beyond its %d lines" % (
                                path.relative_to(ROOT), i + 1, m.group(0), len(tl)))
    assert not dead, "dead line citations are back (%d found): %s" % (len(dead), dead[:8])
