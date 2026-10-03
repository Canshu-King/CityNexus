"""ORD-0500 r17: run the Q64 exposure ruler over BOTH sides of this order's product change, in one run.

Why a dedicated pair tool: the receipts from r14 carry no ruler revision.  The commander has issued
r7b -> r7b1 -> r7b3 -> r7b4 since, and r7b4's own header says a per-file count is neither an upper nor a
lower bound on `--tree`, so "the two sides agree" means nothing unless it says WHICH ruler answered.
This records the ruler's path, its blob in the cmdr ref, and its size next to both outputs.

The tree is swapped to the base blobs for one run and restored, byte-verified, afterwards -- the same
discipline build_faces_r6.py uses, because a swapped tree left behind would poison every later reading
in this worktree (and did once, in another lane).  It refuses to start on a dirty worktree.

Usage: python exposure_pair_r17.py     (env: R17_BASE_TIP, R17_GEN)
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
EV = os.path.join(LANE, "evidence")
RUN = os.path.join(LANE, "run")
RULER_DIR = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
RULER = os.environ.get("R17_RULER") or "ui_exposure_taint_ast_r7b4.cjs"
NODE = os.environ.get("CNX_PHONE_NODE", r"C:/Program Files/nodejs/node.exe")
SCAN = "frontend/src"
GEN = os.environ.get("R17_GEN") or "r17"
BASE = os.environ.get("R17_BASE_TIP") or ""


def git(*args):
    p = subprocess.run(["git", "-C", WT] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=300)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def blob_of(rev, path):
    rc, out = git("rev-parse", "%s:%s" % (rev, path))
    return out if rc == 0 else None


def what_changed(base):
    """The paths this pair is allowed to swap, and the two revisions it compares.

    Default mode -- `merge-base..HEAD`: the paths THIS ref changed since it forked from the line.  Never
    typed, and never a plain `tip..HEAD` diff, because that would also list everything other lanes landed
    since my fork and swapping THAT would revert their work inside this shared worktree.

    Explicit mode (`R17_PATHS="a b"` with `R17_CAND_REV=<sha>`): needed once the ruled deletion has
    landed.  This ref then carries no product difference at all, so a merge-base-derived pair would
    compare a tip with itself; the deletion is still the question, so the pair runs between the two
    commits that actually hold it -- the same two the faces were built from.  Both revs are verified to
    exist and every named path on both, and nothing outside the list is ever touched or restored.
    """
    explicit = (os.environ.get("R17_PATHS") or "").split()
    cand = os.environ.get("R17_CAND_REV") or "HEAD"
    if explicit:
        for rev in (base, cand):
            if git("rev-parse", "--verify", "-q", "%s^{commit}" % rev)[0] != 0:
                raise SystemExit("ABORT_REV_MISSING " + rev)
        for p in explicit:
            if blob_of(base, p) is None or blob_of(cand, p) is None:
                raise SystemExit("ABORT_PATH_NOT_ON_BOTH_REVS " + p)
        return {"mode": "explicit_revs", "base_rev": base, "candidate_rev": cand,
                "paths": sorted(set(explicit)), "merge_base": "NOT_APPLICABLE"}
    rc, mb = git("merge-base", base, "HEAD")
    mb = (mb or "").strip()
    if rc or not re.fullmatch(r"[0-9a-f]{40}", mb):
        raise SystemExit("ABORT_NO_MERGE_BASE %s vs HEAD: %s" % (base[:12], mb[:120]))
    rc, out = git("diff", "--name-only", "%s..HEAD" % mb)
    if rc:
        raise SystemExit("ABORT_DIFF %s" % out[:200])
    paths = [l.strip() for l in out.splitlines() if l.strip()
             and not l.strip().startswith("review/")]
    if not paths:
        raise SystemExit("ABORT_NO_PRODUCT_PATHS between fork %s and HEAD -- nothing to compare"
                         % mb[:12])
    bad = [p for p in paths if blob_of(base, p) is None]
    if bad:
        raise SystemExit("ABORT_PATH_NOT_ON_BASE %s" % bad)
    return {"merge_base": mb, "paths": paths}


def run_ruler(out_name):
    dest = os.path.join(EV, out_name)
    log = os.path.join(RUN, "r17_exposure_%s.txt" % out_name.replace(".json", ""))
    p = subprocess.run([NODE, os.path.join(RULER_DIR, RULER), "--tree", SCAN, "--out", dest],
                       cwd=WT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1800)
    open(log, "wb").write(p.stdout)
    if p.returncode != 0:
        raise SystemExit("ABORT_RULER rc=%s %s" % (p.returncode, p.stdout.decode("utf-8", "replace")[:220]))
    if not os.path.exists(dest):
        raise SystemExit("ABORT_RULER_NO_OUTPUT " + dest)
    d = json.load(open(dest, encoding="utf-8"))
    d["_lane_meta"] = {"ruler": RULER, "ruler_bytes": os.path.getsize(os.path.join(RULER_DIR, RULER)),
                       "ruler_sha1_of_local_bytes": hashlib.sha1(open(
                           os.path.join(RULER_DIR, RULER), "rb").read()).hexdigest(),
                       "scan": SCAN, "ran_local": datetime.now().astimezone().isoformat(
                           timespec="seconds")}
    json.dump(d, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    return d


def summary(d):
    return {"cells_total": d.get("cells_total"), "hits": len(d.get("hits") or []),
            "hit_set": sorted("%s:%s" % (h.get("file"), h.get("line")) for h in (d.get("hits") or [])),
            "unresolved_import_count": d.get("unresolved_import_count"),
            "parse_diagnostics_total": d.get("parse_diagnostics_total"),
            "claim_kind": d.get("claim_kind"), "scope": d.get("scope")}


def main():
    if not BASE:
        raise SystemExit("ABORT_NO_BASE_TIP -- set R17_BASE_TIP to the tip the candidate is measured on")
    rc, listed = git("ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1")
    live = (re.search(r"([0-9a-f]{40})", listed or "")).group(1) if listed else None
    if not live:
        raise SystemExit("ABORT_NO_LIVE_TIP")
    rc, dirty = git("status", "--porcelain")
    if dirty.strip():
        raise SystemExit("ABORT_UNCOMMITTED_CANDIDATE " + dirty[:300])
    head = git("rev-parse", "HEAD")[1]
    changed = what_changed(BASE)
    paths = changed["paths"]
    explicit = changed.get("mode") == "explicit_revs"
    cand_rev = changed.get("candidate_rev", "HEAD")
    if explicit:
        # comparing two historical commits is only about THIS delivery if the ref carries the same bytes
        # as the candidate side; if it does not, the pair would be measuring somebody else's change
        if not all(blob_of(cand_rev, p) == blob_of("HEAD", p) for p in paths):
            raise SystemExit("ABORT_CANDIDATE_REV_NOT_THIS_REF %s differs from HEAD for %s"
                             % (cand_rev[:12], [p for p in paths
                                                if blob_of(cand_rev, p) != blob_of("HEAD", p)]))
    elif live != BASE:
        raise SystemExit("ABORT_BASE_MOVED the ruler pair was asked for base %s but the line answers %s "
                         "-- re-cut before measuring" % (BASE, live))
    want = {p: blob_of("HEAD", p) for p in paths}
    out = {"tool": "exposure_pair_%s" % GEN, "took_local": datetime.now().astimezone().isoformat(
        timespec="seconds"), "live_tip": live, "candidate_head": head, "base_tip": BASE,
        "mode": changed.get("mode", "merge_base"), "candidate_rev": cand_rev,
        "merge_base": changed["merge_base"], "swapped_paths": paths, "ruler": RULER, "sides": {}}
    # candidate first (the tree is already the candidate), then base, then restore and verify
    out["sides"]["candidate"] = summary(run_ruler("exposure_%s_cand.json" % GEN))
    rc, got = git("checkout", BASE, "--", *paths)
    if rc:
        raise SystemExit("ABORT_SWAP %s" % got[:200])
    try:
        out["sides"]["base"] = summary(run_ruler("exposure_%s_base.json" % GEN))
    finally:
        rc2, back = git("checkout", "HEAD", "--", *paths)
        now = {p: blob_of("HEAD", p) for p in paths}
        rc3, dirty_after = git("status", "--porcelain")
        out["restore"] = {"checkout_rc": rc2, "every_path_matches_the_commit": now == want,
                          "worktree_clean_after_restore": not dirty_after.strip(),
                          "mismatches": sorted(p for p in want if want[p] != now.get(p))}
        if rc2 or now != want:
            raise SystemExit("ABORT_RESTORE_FAILED %s %s" % (back[:160], out["restore"]))
    c, b = out["sides"]["candidate"], out["sides"]["base"]
    out["parity"] = {"cells_total_equal": c["cells_total"] == b["cells_total"],
                     "hit_set_equal": c["hit_set"] == b["hit_set"],
                     "unresolved_equal": c["unresolved_import_count"] == b["unresolved_import_count"],
                     "diagnostics_equal": c["parse_diagnostics_total"] == b["parse_diagnostics_total"]}
    dest = os.path.join(EV, "exposure_pair_%s.json" % GEN)
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps({"ruler": RULER, "swapped": len(paths), "parity": out["parity"],
                      "candidate_cells": c["cells_total"], "base_cells": b["cells_total"],
                      "restore_clean": out["restore"]["worktree_clean_after_restore"],
                      "receipt": os.path.basename(dest)}, indent=2, ensure_ascii=False))
    return 0 if out["parity"]["hit_set_equal"] else 1


if __name__ == "__main__":
    sys.exit(main())
