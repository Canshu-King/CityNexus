"""Audit every `path:line` citation that sits in shipped source comments on this tip.

Receipts and ledgers are excluded: a receipt is a dated record of the generation it was taken on, so
a number that has since moved there is history, not a live claim.  A comment inside shipped source is
a live claim -- a reader goes to that line expecting the thing the sentence says, and if the line has
drifted the comment is a defect of the same family this lane has now hit three times (ORD-0500 r5 and
r6 both re-cut for exactly this).

The tool does NOT decide whether a citation is correct prose: it prints the referenced line's actual
text next to the sentence that cites it, so the judgement is made against a reading and never against a
remembered number.  `mechanically_red` is the purely mechanical half -- a line the target file does not
have, or a target file that is absent -- and a bare `` `:NNN` `` is resolved against the last path
named before it, in reading order, because that is how a reader resolves it.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
# shipped source only: the product trees and the specs, never the review/ evidence folder
SCOPE = ("backend/app", "backend/tests", "frontend/src", "contracts")
PATH_CIT = re.compile(r"([A-Za-z0-9_./-]+\.(?:py|tsx|ts|yaml|json)):(\d+)")
BARE_CIT = re.compile(r"\(" + chr(96) + r":(\d+)" + chr(96) + r"\)")


def git_ls():
    p = subprocess.run(["git", "-C", WT, "grep", "-l", "--", *SCOPE],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    return p.stdout.decode("utf-8", "replace").splitlines()


def tracked():
    """Every tracked path, so a comment that writes `schemas.py:221` or `app/db/models.py:483` -- a
    path relative to `backend/`, which is where that spec was written from -- still resolves."""
    p = subprocess.run(["git", "-C", WT, "ls-files"], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=180)
    return [l.strip() for l in p.stdout.decode("utf-8", "replace").splitlines() if l.strip()]


ALL_TRACKED = [t for t in tracked() if not t.startswith("review/")]
# `review/` holds frozen checkpoint copies of the whole product tree, and 20 of the 21 paths ending in
# `/main.py` are those copies.  A shipped comment cites the live path, so the checkpoint copies are not
# candidates -- leaving them in makes every bare-name citation "ambiguous" and hides the real findings.


def resolve(path):
    """(resolved_path_or_None, how) -- exact, then unique suffix against the tracked list."""
    if os.path.exists(os.path.join(WT, path)):
        return path, "exact"
    cands = [t for t in ALL_TRACKED if t == path or t.endswith("/" + path)]
    if len(cands) == 1:
        return cands[0], "unique-suffix"
    if len(cands) > 1:
        return None, "AMBIGUOUS(%d)" % len(cands)
    return None, "no-tracked-match"


def lane_files():
    """This lane's own shipped paths: every non-`review/` path touched by a commit this HEAD carries
    that names the order.  Derived from the log, so a re-cut does not leave a remembered list behind."""
    shas = subprocess.run(["git", "-C", WT, "log", "--format=%H", "--grep=ORD-0500", "HEAD"],
                          stdout=subprocess.PIPE, timeout=180).stdout.decode("utf-8", "replace")
    names = set()
    for sha in shas.split():
        p = subprocess.run(["git", "-C", WT, "show", "--name-only", "--format=", sha],
                           stdout=subprocess.PIPE, timeout=180)
        for l in p.stdout.decode("utf-8", "replace").splitlines():
            l = l.strip()
            if l and not l.startswith("review/") and not l.startswith("tools/"):
                names.add(l)
    return sorted(names)


MINE = lane_files()


def main():
    tip = subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"],
                         stdout=subprocess.PIPE, timeout=120).stdout.decode().strip()
    files = [f for f in git_ls() if re.search(r"\.(py|tsx|ts)$", f)]
    cache, rows = {}, []

    def target_lines(path):
        if path not in cache:
            cache[path] = open(os.path.join(WT, path), encoding="utf-8",
                               errors="replace").read().splitlines()
        return cache[path]

    def record(cited_by, line_text, path, num, target_repr, bare):
        row = {"cited_by": cited_by, "target": target_repr, "line": num, "bare": bare,
               "citing_sentence": line_text.strip()[:150]}
        resolved, how = (resolve(path) if path else (None, "ORPHAN_BARE"))
        row["resolution"] = how
        if resolved is None:
            row.update({"file_exists": False, "line_exists": False,
                        "verdict": "UNRESOLVED_PATH" if path else "ORPHAN_BARE"})
        else:
            tgt = target_lines(resolved)
            in_range = num <= len(tgt)
            text = tgt[num - 1].strip()[:110] if in_range else None
            row.update({"file_exists": True, "resolved_path": resolved, "lines_in_target": len(tgt),
                        "line_exists": in_range, "target_text": text,
                        "verdict": ("OK" if in_range and text else
                                    ("BLANK_LINE_CITED" if in_range else "LINE_BEYOND_FILE"))})
        rows.append(row)

    for f in files:
        p = os.path.join(WT, f)
        text = open(p, encoding="utf-8", errors="replace").read()
        last_path = None
        for ln, line in enumerate(text.splitlines(), 1):
            toks = sorted([(m.start(), "path", m) for m in PATH_CIT.finditer(line)] +
                          [(m.start(), "bare", m) for m in BARE_CIT.finditer(line)])
            if not toks:
                continue
            for _, kind, m in toks:
                if kind == "path":
                    path, num = m.group(1), int(m.group(2))
                    if path == f:
                        last_path = path
                        continue          # a comment naming its own file is not a citation to check
                    record("%s:%d" % (f, ln), line, path, num, path, False)
                    last_path = path
                else:
                    num = int(m.group(1))
                    repr_ = (last_path + " (bare)") if last_path else "NO PATH BEFORE THIS BARE"
                    record("%s:%d" % (f, ln), line, last_path, num, repr_, True)

    red = [r for r in rows if r["verdict"] != "OK"]
    tally = {}
    for r in rows:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    mine = [r for r in rows if r["cited_by"].split(":")[0] in MINE]
    out = {"tool": "citation_audit_r8", "took_local": datetime.now().astimezone().isoformat(),
           "tip": tip, "scope": list(SCOPE), "files_scanned": len(files),
           "citations_found": len(rows), "verdict_tally": tally,
           "mechanically_red": len(red), "this_lanes_own_files": sorted(MINE),
           "citations_in_this_lanes_files": len(mine),
           "red_detail": red, "rows": rows}
    path = os.path.join(LANE, "evidence", "citation_audit_r8.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("files_scanned=%d citations=%d tally=%s" % (len(files), len(rows),
                                                      json.dumps(tally, sort_keys=True)))
    print("--- every citation that is not OK, and every citation inside this lane's own files ---")
    shown = []
    for r in rows:
        if r["verdict"] != "OK" or r in mine:
            shown.append(r)
            print("%-4s %s | %s -> %s %s" % (r["verdict"][:4], r["cited_by"], r["target"],
                                              r["line"], json.dumps(r.get("target_text"),
                                                                    ensure_ascii=False)[:72]))
            print("     by: %s" % r["citing_sentence"][:112])
    print("shown=%d" % len(shown))
    print("WROTE " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
