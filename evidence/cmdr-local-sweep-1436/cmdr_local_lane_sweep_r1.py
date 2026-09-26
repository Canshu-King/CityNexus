#!/usr/bin/env python3
"""Sweep the LOCAL object stores for lane deliveries the GitHub patrol cannot see.

Why this exists (measured 2026-09-26): lane trees named `agent/d-e345b9d6-ord0338` were real and
signed ALL_MET, yet `git ls-remote origin` on GitHub never showed them, so my patrol reported
"0 branch tips not in the line" for hours while the work sat in a local store.  Root cause is a
route fact, not a willingness fact: in `_qoder_d_ord0338_fix` and `_qoder_b_lane_20260923` the
remote named `origin` is the local path `D:/moodle/CityNexus`, and those trees are linked worktrees
of `D:/moodle/_qoder_integration_20260919`, so a push lands in the *integration* store, which my
patrol never looked at.  A commander who only reads GitHub concludes "cold lane, nothing delivered";
the byte-level truth was 11 files away on the same disk.

This tool answers one question per round: which local branch tips are NOT contained in the
authoritative line, newest first.  It is read-only: for-each-ref, merge-base --is-ancestor (whose
answer is the EXIT CODE, read rc, never stdout - that mistake cost me two selftests today), and
log -1.  It never fetches, never pushes, never moves a ref.
"""
import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys

STORES = [
    ("CityNexus", r"D:/moodle/CityNexus"),
    ("integration", r"D:/moodle/_qoder_integration_20260919"),
    ("th_20260918", r"D:/moodle/_qoder_th_20260918"),
]
LINE_BRANCH = "mirror/integration-frontend-apple-pass1"
# branches I or a lane use for plumbing; not deliveries
SKIP = re.compile(r"^(refs/heads/(mirror/|cmdr/|_preflight|qoder-scan)|refs/qoder-scan/)")


def rc_and_out(repo, *args):
    p = subprocess.run(["git", "-C", repo] + list(args),
                       capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=12.0,
                    help="only report branches whose commit is newer than this (noise control)")
    ap.add_argument("--state", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                    "patrol", "local_lane_sweep_state.json"))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    # Resolve the line from the GitHub remote, then make sure the local stores can see it.
    store0 = STORES[0][1]
    rc, raw, err = rc_and_out(store0, "ls-remote", "origin", "refs/heads/" + LINE_BRANCH)
    # ls-remote prints "<sha>\t<ref>": the sha is the FIRST token.  A first draft took [-1],
    # which is the ref name, so the 40-hex guard failed an otherwise correct read.
    fields = raw.split()
    tip = fields[0] if fields else ""
    if rc != 0 or not re.match(r"^[0-9a-f]{40}$", tip):
        print("LINE_READ_FAILED rc=%s out=%r err=%s" % (rc, raw[:80], err[:160]), file=sys.stderr)
        return 4

    seen, new_rows, errors = [], [], []
    for label, repo in STORES:
        if not os.path.isdir(repo):
            errors.append({"store": label, "error": "DIR_MISSING"})
            continue
        rc, out, _ = rc_and_out(repo, "for-each-ref",
                                "--format=%(refname)%09%(objectname)%09%(committerdate:iso8601)%09%(authorname)",
                                "refs/heads", "refs/qoder-scan")
        if rc != 0:
            errors.append({"store": label, "error": "FOR_EACH_REF_RC_%d" % rc})
            continue
        for line in out.splitlines():
            # Tab-delimited: committerdate:iso8601 itself contains spaces ("2026-09-26 13:59:40
            # +0800"), and a first draft split on whitespace, which silently lost the time field and
            # let every four-day-old branch through the --hours filter as "unparseable".
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            ref, sha, when, author = parts[0], parts[1], parts[2], parts[3]
            if SKIP.match(ref) or not re.match(r"^[0-9a-f]{40}$", sha):
                continue
            try:
                d = datetime.datetime.strptime(when[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                d = None
            if d and (datetime.datetime.now() - d).total_seconds() > a.hours * 3600:
                continue
            arc, _, _ = rc_and_out(repo, "merge-base", "--is-ancestor", sha, tip)
            contained = (arc == 0)          # the EXIT CODE is the answer
            _, subj, _ = rc_and_out(repo, "log", "-1", "--format=%s", sha)
            row = {"store": label, "ref": ref, "tip": sha, "committed": when,
                   "author": author, "contained_in_line": contained, "subject": subj[:120]}
            seen.append(row)
            if not contained:
                new_rows.append(row)

    prior = {}
    if os.path.exists(a.state):
        try:
            prior = json.load(io.open(a.state, encoding="utf-8"))
        except Exception:
            prior = {}
    prior_tips = set(prior.get("tips", []))
    first_seen = [r for r in new_rows if r["tip"] not in prior_tips]

    report = {
        "at_local": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "line_tip": tip,
        "branches_scanned": len(seen),
        "not_in_line": new_rows,
        "first_seen_this_round": first_seen,
        "errors": errors,
    }
    io.open(a.state, "w", encoding="utf-8").write(
        json.dumps({"tips": [r["tip"] for r in seen], "at": report["at_local"]},
                   ensure_ascii=False, indent=1))
    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report, ensure_ascii=False, indent=1))
    print("SUMMARY scanned=%d not_in_line=%d first_seen=%d" % (
        len(seen), len(new_rows), len(first_seen)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
