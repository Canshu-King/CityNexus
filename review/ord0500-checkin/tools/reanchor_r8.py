"""ORD-0500 r8: re-anchor the four `main.py` line numbers that my own shipped comment cites.

This is the third time this lane has had to do this, so the rule is now code rather than a
resolution: every number is READ from the checked-out tip's own `backend/app/main.py`, and each one
must (a) carry the text the comment claims and (b) sit inside the footprint door's own route span,
which is located by the route path lines -- not by a remembered offset. If either check fails the
tool aborts and writes nothing, because a re-anchored comment that is quietly wrong is worse than a
stale one.

Only `backend/tests/test_qoder_ord0500_journey_refusal.py` is edited. That file is not referenced by
anything under `frontend/` (re-checked here, because it is the reason no screen reading is retaken),
so the served bundle is unaffected; the claim is verified in the receipt, not asserted in a page.
"""
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
TEST = "backend/tests/test_qoder_ord0500_journey_refusal.py"
MAIN = "backend/app/main.py"
ROUTE_PATH = '"/api/v1/journeys/{journey_id}/checkins",'


def git(*args, cwd=WT):
    p = subprocess.run(["git", "-C", cwd] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=180)
    return p.stdout.decode("utf-8", "replace")


def line_of(lines, needle, label, span=None, want=1):
    hits = [i + 1 for i, l in enumerate(lines) if needle in l]
    all_hits = list(hits)
    if span:
        hits = [h for h in hits if span[0] <= h <= span[1]]
    if len(hits) != want:
        raise SystemExit("ABORT_ANCHOR %s -- %r matched %d lines %s inside span %s (all file hits: %s, "
                         "want %d)" % (label, needle, len(hits), hits, list(span), all_hits, want))
    return hits[0]


Q = chr(96)  # backtick, kept out of the literals so no shell ever sees it

# Each substitution is anchored to the PROSE the citation belongs to, so no remembered number is
# needed and a moved line cannot be "fixed" into the wrong sentence.
PATTERNS = [
    ("require", Q + r"require\(\)" + Q + " helper \\(" + Q + r"backend/app/main\.py:(\d+)" + Q + r"\)"),
    ("lookup", "own table up first \\(" + Q + r"backend/app/main\.py:(\d+)" + Q + r"\)"),
    ("integrity", "catches a race that lookup cannot see \\(" + Q + r":(\d+)" + Q + r"\)"),
    ("caught_by", "adds " + Q + "caught_by: unique_index" + Q + " \\(" + Q + r":(\d+)" + Q + r"\)"),
]
REPL = {
    "require": Q + "require()" + Q + " helper (" + Q + "backend/app/main.py:%d" + Q + ")",
    "lookup": "own table up first (" + Q + "backend/app/main.py:%d" + Q + ")",
    "integrity": "catches a race that lookup cannot see (" + Q + ":%d" + Q + ")",
    "caught_by": "adds " + Q + "caught_by: unique_index" + Q + " (" + Q + ":%d" + Q + ")",
}


def nodigits(s):
    return re.sub(r"\d+", "", s)


def apply(src, anchors):
    """Return (new_src, numbers_replaced_from, count); refuse if the prose would move.

    ABORT_ANCHOR_PHRASE: the shipped comment no longer says the thing this tool anchors on, so the
    number it holds is unknown and replacing nothing would read as a completed re-anchor.
    ABORT_TEXT_CHANGED: a replacement is not the old prose with different digits -- the bug this
    tool itself produced first (a dropped backtick turned `require() into require()` in shipped
    prose), which is why the digits-only rule is a guard and not a comment.
    """
    new_src, replaced_from, n = src, {}, 0
    for label, pat in PATTERNS:
        m = re.search(pat, new_src)
        if not m:
            raise SystemExit("ABORT_ANCHOR_PHRASE %s -- the shipped comment no longer contains the "
                             "phrase this tool anchors on (%r)" % (label, pat[:60]))
        repl = REPL[label] % anchors[label]
        if nodigits(m.group(0)) != nodigits(repl):
            raise SystemExit("ABORT_TEXT_CHANGED %s -- replacement is not the old prose with new "
                             "digits: %r -> %r" % (label, m.group(0), repl))
        replaced_from[label] = int(m.group(1))
        new_src = new_src[:m.start()] + repl + new_src[m.end():]
        n += 1
    return new_src, replaced_from, n


def read_anchors(lines):
    """(anchors, span) read out of a checked-out `backend/app/main.py`; nothing here is remembered.

    The door's own route span is the two decorated checkin routes, POST first: the span runs from the
    POST path line to the line before the next route path line, so nothing downstream can be mistaken
    for it.  Each anchor must be unique inside that span, or the tool refuses rather than citing the
    first `except IntegrityError` in the file.
    """
    path_lines = [i + 1 for i, l in enumerate(lines) if l.strip() == ROUTE_PATH]
    if len(path_lines) < 2:
        raise SystemExit("ABORT_ROUTE_SPAN route path line found %s times: %s"
                         % (len(path_lines), path_lines))
    if lines[path_lines[0] - 2].strip() != "@app.post(":
        raise SystemExit("ABORT_ROUTE_SPAN the first path line is not under an @app.post( -- line %d "
                         "reads %r" % (path_lines[0] - 1, lines[path_lines[0] - 2]))
    span = (path_lines[0], path_lines[1] - 1)
    anchors = {
        "require": line_of(lines, "def require(session: Session, model: type", "shared require() helper"),
        "lookup": line_of(lines, "existing = session.scalars(", "door's own duplicate lookup", span),
        "integrity": line_of(lines, "except IntegrityError as exc:", "index catch branch", span),
        "caught_by": line_of(lines, '"caught_by": "unique_index"', "caught_by marker", span),
    }
    return anchors, span


# The selftest driver (`tools/reanchor_r8_selftest.py`) splices a deliberately broken entry into
# REPL below and re-execs this support region in a scratch namespace, so the guard's own text lives
# in one place instead of being retyped by hand into a replica.  Nothing here runs on import.
SELFTEST_CUT = "# SELFTEST-SUPPORT-ENDS-HERE"
# Spelled by concatenation: a contiguous "def main():" here would be found by the search below and
# truncate the support region mid-line.
MAIN_MARK = "def " + "main():"
_src = open(os.path.abspath(__file__), encoding="utf-8").read()
_cut_at = _src.index(SELFTEST_CUT)
_support = _src[:_cut_at]
_main_at = _src.index(MAIN_MARK, _cut_at)
REPL_SRC_LINES = (_support + _src[_cut_at:_main_at]).splitlines()


# SELFTEST-SUPPORT-ENDS-HERE
def main():
    tip = git("rev-parse", "HEAD").strip()
    lines = open(os.path.join(WT, MAIN), encoding="utf-8").read().splitlines()

    anchors, span = read_anchors(lines)

    src = open(os.path.join(WT, TEST), encoding="utf-8", newline="").read()
    new_src, replaced_from, n = apply(src, anchors)

    # The numbers being replaced must actually have been wrong, or this edit is theatre.
    stale = sorted(lab for lab, val in replaced_from.items() if val != anchors[lab])
    if not stale:
        raise SystemExit("ABORT_NOTHING_STALE every cited number already matches the tip anchors %s "
                         "-- nothing to re-anchor" % anchors)
    try:
        ast.parse(new_src)
    except SyntaxError as exc:
        raise SystemExit("ABORT_SYNTAX after replacement: %s" % exc)
    open(os.path.join(WT, TEST), "w", encoding="utf-8", newline="").write(new_src)

    # The reason no screen reading is retaken: this file is outside the front-end module graph.
    hits = git("grep", "-l", "test_qoder_ord0500_journey_refusal", "--", "frontend").strip()
    inside = [h for h in hits.splitlines() if h.strip()]
    after = sorted({int(x) for x in re.findall(r"main\.py:(\d+)", new_src)}
                   | {int(x) for x in re.findall(r"`:(\d+)`", new_src)})
    out = {"tool": "reanchor_r8", "took_local": datetime.now().astimezone().isoformat(),
           "tip": tip, "main_lines": len(lines), "route_span": list(span),
           "route_span_basis": "the two lines whose text is %s; the span is the POST body up to the "
                               "next route path line" % ROUTE_PATH,
           "anchors": anchors,
           "verified_texts": {lab: lines[num - 1].strip()[:90] for lab, num in anchors.items()},
           "replacements_applied": n, "numbers_replaced_from": replaced_from,
           "were_stale": stale, "numbers_now_cited": after,
           "frontend_files_referencing_the_test": inside,
           "bundle_cannot_change_because": "the only edited path is under backend/tests/, and no "
                                          "file under frontend/ references it",
           "sha256_after": hashlib.sha256(new_src.encode("utf-8")).hexdigest()[:16]}
    path = os.path.join(LANE, "evidence", "reanchor_r8.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print("WROTE " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
