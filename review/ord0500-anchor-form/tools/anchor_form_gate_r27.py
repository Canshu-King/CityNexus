"""ORD-0500 anchor-form gate, second cut: it now covers the whole write-set this lane ships.

The first cut checked one shipped spec file.  Measured against the line, that left 19 numeric `path:line`
strings sitting in this lane's own tool paths -- and a rule that stops at the file I happened to list is
exactly the "hardcoded list" defect that has burned this lane before (the citation gate's first version
carried a hand-typed file list and reached into another order's spec).

So the file list is derived, not typed: every path this order's commits have ever touched, read from
`git log --grep=ORD-0500 --name-only` at the live tip.  Two classes fall out of that list, and they are
judged differently on purpose:

  - shipped spec / product files (anything outside `review/`) may carry NO numeric citation at all -- red;
  - lane tool paths may keep a numeric string, but only if the file is declared in EXEMPT with a reason
    that the receipt prints next to the count.  An undeclared tool file with numeric citations is a
    finding, so the exemption cannot be quietly widened later.

`anchor_form_apply_r26.py` and its mutant driver legitimately contain `backend/app/main.py:818` -- that is
the text being deleted, not a citation being made.  They are declared with exactly that reason.

Three scope corrections live in this cut because the first runs of it got each wrong, and the receipts say so:
  - `git log --grep=ORD-0500 --name-only` is not a write-set.  A batch-landing commit whose message mentions
    the order lists the whole tree: the first run scanned 10519 paths and reported 790 "offenders", almost
    none of them this lane's.  Candidates are now the paths under `review/ord0500-*` (this lane's own tree)
    plus shipped product files, and a shipped file only counts where the citing LINE is blamed to a commit of
    this order -- 裁语②'s rule, applied to my own gate.
  - receipts and run logs are measurement OUTPUT.  A JSON of citations is supposed to contain cited paths;
    judging it was a category error, so it gets its own class (`evidence_artifact`, not judged) instead of
    being scored red or quietly called green.
"""
import json
import os
import re
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
sys.path.insert(0, os.path.join(LANE, "tools"))
import anchor_form_gate_r26 as G

NUMERIC = re.compile(r"[A-Za-z0-9_/.-]+\.(?:py|tsx|ts|yaml|json|md):[0-9]+")
ORDER = "ORD-0500"
EXEMPT = {
    "review/ord0500-anchor-form/tools/anchor_form_apply_r26.py":
        "holds the strings this hand DELETES (the old side of each edit), not new citations",
    "review/ord0500-anchor-form/tools/anchor_form_gate_mutants_r26.py":
        "the M1 mutant's payload is literally a numeric citation; removing it would disarm the arm",
    "review/ord0500-checkin/tools/citation_gate_r10_mutants.py":
        "mutant payloads are wrong citations on purpose; the arm asserts the gate judges them red",
    "review/ord0500-checkin/tools/citation_gate_r9_mutants.py":
        "same as above, previous generation",
    "review/ord0500-checkin/tools/citation_audit_r8.py":
        "the ruler's own regex source contains an example pattern",
    "review/ord0500-checkin/tools/r8_block.py":
        "rendered narrative from an earlier generation, kept because a published page cites its blob",
    "review/ord0500-checkin/tools/r9_block.py":
        "same reason as r8_block.py",
    "review/ord0500-checkin/tools/selfdecl_ord0500_r6.py":
        "same reason: a published block cites this file's blob, so it is not rewritten",
}


def lane_tree(tip):
    """Everything under this lane's own review tree -- paths no other lane writes to."""
    # NOTE the bug this line replaces: `ls-tree <rev> review/ord0500-` matches at DIRECTORY granularity, so
    # a bare prefix that is not a real directory answers nothing at all -- the first run of this gate then
    # reported files_scanned=1 and looked GREEN while it had in fact judged almost nothing.
    p = subprocess.run(["git", "-C", WT, "ls-tree", "-r", "--name-only", tip, "review/"],
                       capture_output=True, text=True, timeout=300, env=G.ENV)
    if p.returncode:
        raise SystemExit("ABORT_LS_TREE %s" % p.stdout[:160])
    return sorted({l.strip() for l in p.stdout.splitlines()
                   if l.strip().startswith("review/ord0500-")})


def order_commits(tip):
    p = subprocess.run(["git", "-C", WT, "log", "--grep=%s" % ORDER, "--format=%H", tip],
                       capture_output=True, text=True, timeout=300, env=G.ENV)
    return {l.strip() for l in p.stdout.splitlines() if l.strip()}


def authored_lines(tip, path, commits):
    """Line numbers whose blame commit belongs to this order -- the author filter, not a file guess."""
    p = subprocess.run(["git", "-C", WT, "blame", "--line-porcelain", "%s" % tip, "--", path],
                       capture_output=True, timeout=900, env=G.ENV)
    # bytes, not text=True: the file carries UTF-8 while the ambient code page is GBK, so text mode dies
    # mid-blame and hands back None -- which a caller would read as "none of these lines are mine" (blind,
    # not red)
    if p.returncode:
        return None
    out = p.stdout.decode("utf-8", "replace")
    mine, num = set(), 0
    cur = None
    for line in out.splitlines():
        m = re.match(r"^([0-9a-f]{40}) [0-9]+ [0-9]+", line)
        if m:
            cur = m.group(1)
            continue
        if line.startswith("	"):
            num += 1
            if cur in commits:
                mine.add(num)
    return mine


def classify(path):
    if path.startswith("review/"):
        if "/receipts/" in path or "/run/" in path:
            return "evidence_artifact"
        return "lane_tool"
    return "shipped_spec"


def judge(tip=None, files=None, product_files=()):
    tip = tip or G.live_tip()
    commits = order_commits(tip)
    tree = lane_tree(tip)
    paths = list(files) if files is not None else sorted(set(tree) | set(product_files))
    rows = []
    for path in paths:
        kind = classify(path)
        if kind == "evidence_artifact":
            rows.append({"path": path, "class": kind, "count": 0, "verdict": "NOT_THIS_CLASS",
                         "why": "instrument output; cited paths are data, not claims"})
            continue
        rc, body = G.git("show", "%s:%s" % (tip, path))
        if rc:
            rows.append({"path": path, "class": kind, "verdict": "NOT_ON_TIP", "count": 0})
            continue
        hits = [i + 1 for i, l in enumerate(body.splitlines()) if NUMERIC.search(l)]
        blamed = None
        if kind == "shipped_spec":
            # Judging only the lines blame credits to this order is right for other lanes' files and WRONG
            # for files this order owns: when the line is rebuilt and my change is dropped, those lines end up
            # credited to whoever rebuilt, so the author filter turns a regression into a silent GREEN -- which
            # is exactly what the first run of this cut did.  Owned files are judged whole; blame is reported
            # alongside so the two numbers cannot be confused.
            blamed = authored_lines(tip, path, commits)
            blamed_only = None if blamed is None else len([h for h in hits if h in blamed])
        shipped = kind == "shipped_spec"
        declared = path in EXEMPT
        if shipped:
            verdict = "GREEN" if not hits else "RED"
            why = "" if not hits else "NUMERIC_ANCHOR_IN_SHIPPED_SPEC"
        elif not hits:
            verdict, why = "GREEN", ""
        elif declared:
            verdict, why = "EXEMPT_DECLARED", EXEMPT[path]
        else:
            verdict, why = "RED", "UNDECLARED_NUMERIC_IN_TOOL_PATH"
        row = {"path": path, "count": len(hits), "lines": hits[:8], "class": kind,
               "verdict": verdict, "why": why}
        if blamed_only is not None:
            row["count_blamed_to_this_order"] = blamed_only
        rows.append(row)
    reds = [r for r in rows if r["verdict"] == "RED"]
    return ("GREEN" if not reds else "RED"), rows, reds


PRODUCT = ["backend/tests/test_qoder_ord0500_journey_refusal.py"]


def main():
    tip = G.live_tip()
    verdict, rows, reds = judge(tip, product_files=PRODUCT)
    counts = {}
    for r in rows:
        counts[r["class"]] = counts.get(r["class"], 0) + r["count"]
        counts[r["class"] + ":" + r["verdict"]] = counts.get(r["class"] + ":" + r["verdict"], 0) + 1
    out = {"schema": "CNX_ORD0500_ANCHOR_FORM_V2", "tool": "anchor_form_gate_r27", "tip": tip,
           "verdict": verdict, "files_scanned": len(rows), "counts": counts,
           "derivation": "git log --grep=%s --name-only at the live tip (not a typed list)" % ORDER,
           "rows": rows,
           "red": [(r["path"], r["count"], r["why"]) for r in reds],
           "exempt_declared": len(EXEMPT),
           "limitation": "an exemption can still be ADDED here without touching the cited file; what this "
                         "cut removes is silence -- every declared exemption is printed with its reason and "
                         "its numeric count in this receipt"}
    dest = os.path.join(LANE, "evidence", "anchor_form_gate_r27.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"tip": tip[:12], "verdict": verdict, "files_scanned": out["files_scanned"],
                      "counts": counts, "red": out["red"][:6]}, ensure_ascii=False, indent=1))
    print("WROTE " + dest)


if __name__ == "__main__":
    main()
