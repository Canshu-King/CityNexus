"""Derive claim_coordinate_check_r6.py from r4e - ORD-0371.

Why: tonight 25 of 26 lane delivery blocks were refused at the ledger door by `NUMBER_WITHOUT_COORDINATE`,
and reading the refused lines shows most of them DO cite their witness - as a bare committed path
(`review/ord0388-readouts/RULER_R2.txt`, `tests/test_contract.py`, `lib/failureAttribution.ts:414`-style
lists whose head has the `:line` and whose tails do not). r4e's DURABLE only honours `path:line`, and its
own docstring already admits that a `path:line` is *not retrievable after a rewrite* while a committed path
resolving to a blob in the authoritative tree IS. So the gap is not "the lanes are sloppy", it is that the
one voucher the ruler accepts is the weaker kind.

This is a tightening in one direction and an opening in another, and I want both on the record:
  + a bare path counts only when `git ls-tree` at the authoritative ref says that file is really in the tree
    (r4e cannot check that about anything);
  + it must sit on the SAME LINE as the number - stricter than r4e's 200-character window;
  + it does NOT unlock the DIMENSION / DISCIPLINE_ZERO exemptions, which stay paid for by a strong receipt
    (blob / issuecomment / refs/heads / run id), so prose cannot buy itself out of the gate by naming files.

Mechanics: exact single-match anchors, ast.parse before writing, refuses if r6 already exists.
"""
from __future__ import annotations

import ast
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "claim_coordinate_check_r4e.py")
DST = os.path.join(HERE, "claim_coordinate_check_r6.py")

NEW_BLOCK = '''
# ---- r6 (ORD-0371): a bare committed path, resolvable in the authoritative tree, is a coordinate ----
# r4e's own docstring says `path:line` is deliberately not a strong receipt because it is not retrievable
# after a rewrite. A committed path with no line number is *more* retrievable than that - `git ls-tree`
# either has the file at the authoritative ref or it does not - so it is admitted as a coordinate, under two
# conditions stricter than the DURABLE window it supplements: same LINE as the number (not +-200 chars), and
# never as payment for the DIMENSION / DISCIPLINE_ZERO classes, which still require a strong receipt.
import os as _os
import subprocess as _sp

TREE_REF_DEFAULT = "refs/remotes/origin/mirror/integration-frontend-apple-pass1"
# The authoritative branch lives on GitHub and is fetched as a remote-tracking ref here; `refs/heads/mirror/...`
# does not exist in the local repo, so trying only that made the arm fail closed on a perfectly good tree
# (measured on the first run of q43_r6_selftest_r1: `ls-tree rc 128: fatal: Not a valid object name`).
TREE_REF_CANDIDATES = (TREE_REF_DEFAULT, "refs/heads/mirror/integration-frontend-apple-pass1")
REPO_DEFAULT = _os.environ.get("CNX_Q43_REPO", "D:/moodle/CityNexus")
COMMITTED_PATH = re.compile(
    r"[A-Za-z0-9_.\\-/\\\\]+\\.(?:py|ts|tsx|js|mjs|json|yaml|yml|c|css|html|md|txt|tsv|csv|"
    r"png|jpg|svg|sh|bat|ps1|sql|lock|toml)\\b", re.IGNORECASE)
_PATH_PREFIX_TRIES = ("backend/", "frontend/", "frontend/src/", "scripts/", "tools/",
                      "contracts/", "review/", "evidence/", "data/", "app/")
_tree = {"configured": False, "available": False, "ref": None, "why": "arm not configured",
         "set": None, "by_basename": None, "paths": 0}


def configure_tree(ref=None, repo=None):
    """Index the authoritative tree. Fail CLOSED: when this cannot run, committed paths vouch nothing and
    the block keeps refusing exactly as r4e would, with the reason printed by main()."""
    repo = repo or REPO_DEFAULT
    candidates = [ref] if ref else list(TREE_REF_CANDIDATES)
    tried, picked = [], None
    for cand in candidates:
        tried.append(cand)
        chk = _sp.run(["git", "-C", repo, "rev-parse", "--verify", "--quiet", cand],
                      capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if chk.returncode == 0 and (chk.stdout or "").strip():
            picked = cand
            break
    if not picked:
        _tree.update({"configured": True, "available": False, "ref": ref,
                      "why": "no candidate ref resolves: %s" % tried})
        return _tree
    _tree.update({"configured": True, "ref": picked, "set": None, "by_basename": None})
    try:
        out = _sp.run(["git", "-C", repo or REPO_DEFAULT, "ls-tree", "-r", "--name-only", _tree["ref"]],
                      capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    except Exception as exc:
        _tree.update({"available": False, "why": "git raised: %s" % str(exc)[:120]})
        return _tree
    if out.returncode != 0:
        _tree.update({"available": False,
                      "why": "ls-tree rc %d: %s" % (out.returncode, (out.stderr or "").strip()[:120])})
        return _tree
    paths = [p.strip() for p in (out.stdout or "").splitlines() if p.strip()]
    by_bn = {}
    for p in paths:
        by_bn.setdefault(p.rsplit("/", 1)[-1].lower(), []).append(p)
    _tree.update({"available": bool(paths), "why": "ok" if paths else "empty tree listing",
                  "set": set(p.lower() for p in paths), "by_basename": by_bn, "paths": len(paths)})
    return _tree


def resolve_committed_path(tok):
    """Full tree path vouching this token, or None. Ambiguity refuses rather than guessing."""
    if not _tree.get("available"):
        return None
    cand = tok.replace("\\\\", "/").strip("/").lower()
    if not cand:
        return None
    st = _tree["set"]
    if cand in st:
        return cand
    for pref in _PATH_PREFIX_TRIES:
        if pref + cand in st:
            return pref + cand
    basename = cand.rsplit("/", 1)[-1]
    hits = _tree["by_basename"].get(basename, [])
    tail = cand if "/" not in cand else cand
    exact = [h for h in hits if h.lower() == tail or h.lower().endswith("/" + tail)]
    if len(exact) == 1:
        return exact[0]
    return None


def committed_path_on_this_line(text, pos):
    """Search only the line holding the claim - the strictness that pays for accepting a bare path."""
    lo = text.rfind("\\n", 0, pos) + 1
    hi = text.find("\\n", pos)
    line = text[lo:hi if hi != -1 else len(text)]
    for m in COMMITTED_PATH.finditer(line):
        r = resolve_committed_path(m.group(0))
        if r:
            return r
    return None
'''

ANCHORS = [
    ('VERSION = "Q43_r4e"', 'VERSION = "Q43_r6"'),
    ("WINDOW = 200\n", "WINDOW = 200\n" + NEW_BLOCK),
    ("""    m = DURABLE.search(window)
    if m:
        return True, m.group(0)[:60], []
    notes = []""",
     """    m = DURABLE.search(window)
    if m:
        return True, m.group(0)[:60], []
    cp = committed_path_on_this_line(text, pos)
    if cp:
        return True, "committed_path=" + cp[:70], []
    notes = []"""),
    ('    ap.add_argument("--text")\n',
     '    ap.add_argument("--text")\n    ap.add_argument("--tree", default=None,\n'
     '                    help="ref whose tree commits paths must resolve in (default: authoritative line)")\n'
     '    ap.add_argument("--repo", default=None)\n'),
    ("""    raw = open(a.text, "rb").read()
    text = raw.decode("utf-8", errors="replace")
    claims, findings, exempt = scan(text)""",
     """    raw = open(a.text, "rb").read()
    text = raw.decode("utf-8", errors="replace")
    st = configure_tree(a.tree, a.repo)
    print("committed_path arm: %s ref=%s paths=%s | %s"
          % ("ON" if st["available"] else "OFF(fail-closed, r4e behaviour)",
             st["ref"], st["paths"], st["why"]))
    claims, findings, exempt = scan(text)"""),
]


def main():
    if os.path.exists(DST):
        print("REFUSED: %s already exists - revisions go to a new filename (Q57)" % DST, file=sys.stderr)
        return 3
    src = open(SRC, encoding="utf-8").read()
    out = src
    report = []
    for i, (old, new) in enumerate(ANCHORS, 1):
        n = out.count(old)
        if n != 1:
            print("ABORT anchor %d matched %d times (needs exactly 1): %r" % (i, n, old[:70]), file=sys.stderr)
            return 4
        out = out.replace(old, new, 1)
        report.append({"anchor": i, "matched": n})
    try:
        ast.parse(out)
    except SyntaxError as exc:
        print("ABORT: derived file does not parse: %s" % exc, file=sys.stderr)
        return 5
    with open(DST, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    back = open(DST, encoding="utf-8").read()
    print(json_report(report, src, out, back))
    return 0


def json_report(report, src, out, back):
    import json
    return json.dumps({"source": SRC, "derived": DST, "anchors": report,
                       "src_lines": src.count("\n") + 1, "out_lines": out.count("\n") + 1,
                       "written_bytes": len(back.encode("utf-8")),
                       "readback_identical_to_memory": back == out,
                       "version_in_derived": "Q43_r6" in back,
                       "arm_functions_present": all(k in back for k in
                                                    ("configure_tree", "resolve_committed_path",
                                                     "committed_path_on_this_line"))},
                      ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())
