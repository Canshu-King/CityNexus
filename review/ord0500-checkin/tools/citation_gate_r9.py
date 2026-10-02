"""ORD-0500 r9: the citation gate -- a shipped comment may not cite a line the tip cannot show.

Why this exists as a door and not as a resolution: this lane re-cut ORD-0500 three times over line
numbers that were true when written and false by the next generation (r5, r6, r8).  `reanchor_r8.py`
fixes them once; it does not *keep* fixing them.  This tool is the arm that runs on every generation
and reddens, over the files this order owns -- and only those, because another lane's judgement file
is not mine to gate.

Three shapes are refused, each with the mutant that proves the refusal bites
(`citation_gate_r9_mutants.py`):

  CITED_LINE_BEYOND_FILE   the target file is shorter than the number cited (the classic drift);
  CITED_LINE_IS_BLANK      the number points at an empty line -- a citation that shows a reader nothing;
  CITED_FILE_ABSENT        the path named does not resolve to a tracked file at all.

Resolution rules are the ones the r8 audit had to learn the hard way: a bare name like `main.py`
resolves only when it is unique after the frozen `review/` checkpoint copies are dropped, because 20
of the 21 tracked paths ending in `/main.py` are those copies and a shipped comment never means them.

Read-only.  It opens files and runs `git ls-files`; it writes nothing outside its own receipt.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
OWNED = ("backend/tests/test_qoder_ord0500_journey_refusal.py",
         "backend/tests/test_qoder_ord0476_checkins.py",
         "frontend/src/features/checkin/checkinCopy.ts",
         "frontend/src/features/checkin/checkins.ts",
         "frontend/src/features/trip/TripItinerary.tsx")
PATH_CIT = re.compile(r"([A-Za-z0-9_./-]+\.(?:py|tsx|ts|yaml|json)):(\d+)")
BARE_CIT = re.compile(r"\(" + chr(96) + r":(\d+)" + chr(96) + r"\)")
RED_CLASSES = ("CITED_FILE_ABSENT", "CITED_LINE_BEYOND_FILE", "CITED_LINE_IS_BLANK",
               "CITED_LINE_CONTENT_MISMATCH", "CITED_PHRASE_GONE_FROM_COMMENT")
# A citation written by another order is reported and NOT judged: my gate reddening because someone
# else reworded their own comment would couple two lanes' builds -- the mistake the first version of
# this gate made by listing `backend/tests/test_qoder_ord0476_checkins.py` as mine.
FOREIGN = "NOT_THIS_LANES_CITATION"


def lane_commits(root):
    """This lane's own commits, read from the log -- the ownership answer, not my memory of it."""
    p = subprocess.run(["git", "-C", root, "log", "--grep=ORD-0500", "--format=%H", "HEAD"],
                       stdout=subprocess.PIPE, timeout=300)
    return {l.strip() for l in p.stdout.decode("utf-8", "replace").splitlines() if l.strip()}


def blame_map(root, rel):
    """{line_number: commit} for one file, from one `git blame --line-porcelain` pass."""
    p = subprocess.run(["git", "-C", root, "blame", "--line-porcelain", "--", rel],
                       stdout=subprocess.PIPE, timeout=300)
    if p.returncode:
        return {}
    out, cur = {}, None
    for line in p.stdout.decode("utf-8", "replace").splitlines():
        m = re.match(r"^([0-9a-f]{40}) (\d+) (\d+)", line)
        if m:
            cur = int(m.group(3))
            out[cur] = m.group(1)
    return out


def owner_index(root, owned, precomputed=None):
    """{file: {line: sha}} plus the lane's commit set.  `precomputed` lets the mutant driver judge a
    scratch copy of the text with the blame taken from the real worktree -- the lines are the same
    bytes, and a scratch directory has no git history to blame."""
    if precomputed is not None:
        return precomputed[0], precomputed[1]
    return {f: blame_map(root, f) for f in owned}, lane_commits(root)

# The fourth shape is the one this order has actually been re-cut for, three times: the cited line
# exists and is not blank, it just no longer says the thing the sentence claims.  A number can be in
# range and still be a lie, so the sentence itself carries a content expectation.
#
# These four are not typed from memory: `main()` re-reads the r8 receipt and aborts if any expectation
# here disagrees with what that instrument measured (`pin_agrees_with_receipt`), so the list cannot
# drift away from the artifact that justified it.
EXPECT = (
    {"file": "backend/tests/test_qoder_ord0500_journey_refusal.py", "label": "require",
     "target": "backend/app/main.py", "phrase": "helper (" + chr(96) + "backend/app/main.py:",
     "must_contain": "def require("},
    {"file": "backend/tests/test_qoder_ord0500_journey_refusal.py", "label": "lookup",
     "target": "backend/app/main.py", "phrase": "own table up first (" + chr(96) + "backend/app/main.py:",
     "must_contain": "existing = session.scalars("},
    {"file": "backend/tests/test_qoder_ord0500_journey_refusal.py", "label": "integrity",
     "target": "backend/app/main.py", "phrase": "catches a race that lookup cannot see (" + chr(96) + ":",
     "must_contain": "except IntegrityError as exc:"},
    {"file": "backend/tests/test_qoder_ord0500_journey_refusal.py", "label": "caught_by",
     "target": "backend/app/main.py", "phrase": "adds " + chr(96) + "caught_by: unique_index"
     + chr(96) + " (" + chr(96) + ":", "must_contain": '"caught_by": "unique_index"'},
)
PIN_RECEIPT = os.path.join("review", "ord0500-checkin", "receipts", "reanchor_r8.json")

NUM_AT_PHRASE = "(%s)(\\d+)"


def content_checks(root, read_of):
    """Each expectation: find the number the sentence cites, then open that line and read it.

    A citation is only worth what its sentence claims it for, so the claim is the test: the line must
    still carry the fragment the comment says it carries.  `CITED_PHRASE_GONE_FROM_COMMENT` is a red
    too -- a reworded sentence silently drops the expectation, and a gate that quietly stops checking
    is worse than no gate.
    """
    rows = []
    for item in EXPECT:
        fp = os.path.join(root, item["file"])
        if not os.path.exists(fp):
            continue
        text = open(fp, encoding="utf-8", errors="replace").read()
        m = re.search(re.escape(item["phrase"]) + r"(\d+)", text)
        if not m:
            rows.append({"cited_by": item["file"], "target": item["target"], "line": None,
                         "verdict": "CITED_PHRASE_GONE_FROM_COMMENT",
                         "why": "the sentence this expectation hangs on is no longer in the comment",
                         "citing_sentence": item["phrase"][:90]})
            continue
        num = int(m.group(1))
        tl = read_of(item["target"])
        line_text = tl[num - 1].strip() if num <= len(tl) else None
        if line_text is None:
            rows.append({"cited_by": "%s:%d" % (item["file"], text[:m.start()].count(NL) + 1),
                         "target": item["target"], "line": num, "verdict": "CITED_LINE_BEYOND_FILE",
                         "lines_in_target": len(tl)})
        elif item["must_contain"] not in line_text:
            rows.append({"cited_by": "%s:%d" % (item["file"], text[:m.start()].count(NL) + 1),
                         "target": item["target"], "line": num,
                         "verdict": "CITED_LINE_CONTENT_MISMATCH",
                         "expected_to_contain": item["must_contain"],
                         "line_says": line_text[:110],
                         "citing_sentence": text.splitlines()[text[:m.start()].count(NL)][:110]})
        else:
            rows.append({"cited_by": "%s:%d" % (item["file"], text[:m.start()].count(NL) + 1),
                         "target": item["target"], "line": num, "verdict": "OK",
                         "pinned": item["label"], "target_text": line_text[:80]})
    return rows


def pin_agrees_with_receipt(root):
    """The expectations above must be what the r8 instrument actually read, or they are just my word."""
    for cand in (os.path.join(root, PIN_RECEIPT),
                 os.path.join(LANE, "evidence", "reanchor_r8.json")):
        if os.path.exists(cand):
            rec = json.load(open(cand, encoding="utf-8"))
            vt = rec.get("verified_texts") or {}
            return all(item["must_contain"] in vt.get(item["label"], "") for item in EXPECT), cand, vt
    return False, "NO_RECEIPT", {}
NL = chr(10)


def git(*args, cwd=WT):
    p = subprocess.run(["git", "-C", cwd] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=300)
    return p.stdout.decode("utf-8", "replace")


def tracked_live():
    """Tracked paths with the frozen checkpoint trees removed -- a shipped comment cites the live tree."""
    return [t for t in git("ls-files").splitlines() if t.strip()
            and not t.startswith("review/")]


def resolve(path, live, root=None):
    root = root or WT
    if os.path.exists(os.path.join(root, path)):
        return path, "exact"
    cands = [t for t in live if t == path or t.endswith("/" + path)]
    if len(cands) == 1:
        return cands[0], "unique-suffix"
    return None, ("AMBIGUOUS(%d)" % len(cands) if cands else "no-tracked-match")


def check(text, live, read_of, self_path, root=None):
    """Walk one file's citations in reading order; a bare `:NNN` continues the last named path."""
    rows, last = [], None
    for ln, line in enumerate(text.splitlines(), 1):
        toks = sorted([(m.start(), "path", m) for m in PATH_CIT.finditer(line)] +
                      [(m.start(), "bare", m) for m in BARE_CIT.finditer(line)])
        for _, kind, m in toks:
            if kind == "path":
                path, num = m.group(1), int(m.group(2))
                if path == self_path:
                    last = path
                    continue
                last = path
            else:
                path, num = last, int(m.group(1))
                if path is None:
                    rows.append({"cited_by": "%s:%d" % (self_path, ln), "line": num,
                                 "verdict": "CITED_FILE_ABSENT", "why": "no path before this bare number"})
                    continue
            target, how = resolve(path, live, root)
            if target is None:
                rows.append({"cited_by": "%s:%d" % (self_path, ln), "target": path, "line": num,
                             "resolution": how, "verdict": "CITED_FILE_ABSENT",
                             "citing_sentence": line.strip()[:120]})
                continue
            tl = read_of(target)
            if num > len(tl):
                rows.append({"cited_by": "%s:%d" % (self_path, ln), "target": target, "line": num,
                             "lines_in_target": len(tl), "verdict": "CITED_LINE_BEYOND_FILE",
                             "citing_sentence": line.strip()[:120]})
            elif not tl[num - 1].strip():
                rows.append({"cited_by": "%s:%d" % (self_path, ln), "target": target, "line": num,
                             "lines_in_target": len(tl), "verdict": "CITED_LINE_IS_BLANK",
                             "citing_sentence": line.strip()[:120]})
            else:
                rows.append({"cited_by": "%s:%d" % (self_path, ln), "target": target, "line": num,
                             "verdict": "OK", "target_text": tl[num - 1].strip()[:80]})
    return rows


def mark_ownership(rows, owners, mine):
    """Tag each row with the commit that wrote the citing line, and whether that commit is this lane's.

    This is what makes the gate honest about its own scope: a row is only *judged* when the sentence
    carrying the citation was written by a commit this order owns.  The blame is read from the real
    worktree once and reused, so judging a scratch copy of identical bytes does not change the answer.
    """
    for r in rows:
        src = r["cited_by"].split(":")
        rel, ln = src[0], (int(src[1]) if len(src) > 1 and src[1].isdigit() else None)
        sha = (owners.get(rel) or {}).get(ln) if ln else None
        r["owner_commit"] = sha
        r["owner_is_this_lane"] = (sha in mine) if sha else None
    return rows


def lane_write_set(root):
    """What to look at: every non-`review/`, non-`tools/` source path this order's own commits have
    touched -- computed from the log, because a hand-typed list is how the first version of this gate
    ended up carrying another order's spec.  Shared hot files are included on purpose: the per-citation
    blame filter below decides what gets *judged*, and this set only decides where to look.
    """
    shas = lane_commits(root)
    names = set()
    for sha in sorted(shas):
        p = subprocess.run(["git", "-C", root, "show", "--name-only", "--format=", sha],
                           stdout=subprocess.PIPE, timeout=300)
        for l in p.stdout.decode("utf-8", "replace").splitlines():
            l = l.strip()
            if l and not l.startswith(("review/", "tools/")) and re.search(
                    r"\.(py|tsx|ts|yaml|json)$", l):
                names.add(l)
    return sorted(names)


def run_gate(root=None, live=None, owned=None, owners=None, mine=None):
    """The gate itself.  `root` defaults to this lane's worktree and `live` to its tracked list; the
    mutant driver passes a scratch `root` with the SAME tracked list, so a copied-out tree is still
    judged against the real repository rather than against whatever happens to sit in the scratch dir.
    Dropping one path from `live` is how CITED_FILE_ABSENT gets proved without inventing a file.
    """
    root = root or WT
    owned = list(owned) if owned else lane_write_set(root or WT)
    missing_fallback = [f for f in OWNED if f not in owned]
    if os.path.exists(os.path.join(root, ".git")):
        tip = git("rev-parse", "HEAD", cwd=root).strip()
        branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=root).strip()
    else:
        tip, branch = "NOT_A_GIT_TREE", "NOT_A_GIT_TREE"
    if live is None:
        live = [t for t in git("ls-files", cwd=root).splitlines() if t.strip()
                and not t.startswith("review/")]
    cache = {}

    def read_of(p):
        if p not in cache:
            cache[p] = open(os.path.join(root, p), encoding="utf-8",
                            errors="replace").read().splitlines()
        return cache[p]

    if owners is None or mine is None:
        # blame comes from the real worktree even when the text being judged is a scratch copy
        owners, mine = owner_index(WT, owned)
    rows = []
    for f in owned:
        fp = os.path.join(root, f)
        if not os.path.exists(fp):
            rows.append({"cited_by": f, "verdict": "CITED_FILE_ABSENT",
                         "why": "this order owns the file but the tree does not carry it"})
            continue
        rows += check(open(fp, encoding="utf-8", errors="replace").read(), live,
                      read_of, f, root)
    rows += content_checks(root, read_of)
    rows = mark_ownership(rows, owners, mine)
    for r in rows:
        r["mechanical_verdict"] = r["verdict"]
        if r.get("owner_is_this_lane") is False:
            r["verdict"] = FOREIGN
            r["why"] = "the sentence carrying this citation was written by commit %s, which this " \
                       "order does not own" % str(r.get("owner_commit"))[:12]
    gated = [r for r in rows if r["verdict"] != FOREIGN]
    red = [r for r in gated if r["verdict"] in RED_CLASSES]
    agree, pin_src, _vt = pin_agrees_with_receipt(root)
    return {"tool": os.environ.get("CITATION_GATE_TOOL") or "citation_gate_r9", "took_local": datetime.now().astimezone().isoformat(
        timespec="seconds"), "tree": root, "tip": tip, "branch": branch,
        "files_scanned": len(owned),
        "live_tracked_paths": len(live),
        "citations_seen": len(rows), "citations_judged": len(gated),
        "citations_declined": len(rows) - len(gated),
        "citation_lines_judged": len({r["cited_by"] for r in gated if not r.get("pinned")}),
        "judged_files": len({r["cited_by"].split(":")[0] for r in gated}),
        "mechanical_rows": sum(1 for r in gated if not r.get("pinned")),
        "pin_rows": sum(1 for r in gated if r.get("pinned")),
        "lane_commits_in_set": len(mine),
        "foreign_files_seen": sorted({r["cited_by"].split(":")[0] for r in rows
                                      if r["verdict"] == FOREIGN}),
        "verdict": ("GREEN" if not red and gated and agree else
                    ("RED" if (red or not agree) else "ABORT_EMPTY")),
        "red_total": len(red), "red_detail": red,
        "expectations": [{"label": e["label"], "must_contain": e["must_contain"]} for e in EXPECT],
        "expectations_agree_with_r8_receipt": agree, "pin_receipt_read_from": pin_src,
        "pinned_citations": sum(1 for r in gated if r.get("pinned")),
        "verdict_tally": {k: sum(1 for r in rows if r["verdict"] == k)
                          for k in ("OK", FOREIGN) + RED_CLASSES},
        "rows": rows}


def main():
    res = run_gate()
    # one file per generation: a receipt an earlier page already cited must not be rewritten
    dest = os.path.join(LANE, "evidence",
                       os.environ.get("CITATION_GATE_OUT") or "citation_gate_r9.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    json.dump(res, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("verdict=%s citations=%s red=%s tally=%s tip=%s" % (
        res["verdict"], res["citations_seen"], res["red_total"],
        json.dumps(res["verdict_tally"]), res["tip"][:12]))
    for r in res["red_detail"]:
        print("  RED %s -> %s %s | %s" % (r["cited_by"], r.get("target"), r["line"],
                                          r["citing_sentence"][:90]))
    print("WROTE " + dest)
    return 0 if res["verdict"] == "GREEN" else 3


if __name__ == "__main__":
    sys.exit(main())
