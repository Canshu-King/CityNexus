# -*- coding: utf-8 -*-
"""The two candidates that are still outside the line, re-measured against the tip as it reads NOW.

Read-only: nothing here lands, moves or writes.  Per candidate it answers the three questions a landing gate
asks - is the chain root the current tip, does the tip still hold the same bytes at every path this candidate
changes, and does `git merge-tree --write-tree` predict any conflict name.  The tip is taken from
`git ls-remote` in this run, never from a relayed sentence, and is proved to exist locally with
`git cat-file -e` before any diff is read off it (a bare sha pins nothing until the object is here).
"""
import io
import json
import os
import subprocess
import time

REPO = "D:/moodle/CityNexus"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")
BRANCH = "refs/heads/mirror/integration-frontend-apple-pass1"
CANDIDATES = {
    "refs/heads/review/1d64acf5-ord0296-g4-floor-r5": "3f7cda327038ac02c94ffe5a439048f21bee0a8a",
    "refs/heads/review/1d64acf5-ord0476-response-set-r4": "f9f4b718e86fdee77955f33f94e41ca33ccaff0e",
}
OWN = {"backend/tests/test_qoder_ord0296_write_deadline.py",
       "backend/tests/test_qoder_ord0476_checkins.py",
       "review/1d64acf5-g4-single-source-shape/g4_single_source_shape_r1.json",
       "review/1d64acf5-g4-single-source-shape/g4_single_source_shape_r2.json",
       "review/1d64acf5-g4-single-source-shape/g4_single_source_shape_r3.json"}


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=900)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def local_commit(obj):
    return git("cat-file", "-e", "%s^{commit}" % obj)[0] == 0


def ensure_tip():
    """Read the authoritative sha off the server, then prove that very sha is a local object.  GitHub does not
    answer `fetch origin <sha>`, so the branch is fetched into its remote-tracking name and the sha is compared
    to what that ref resolved to - a bare 40-hex pins nothing until the object is here and equals the read."""
    rc, ls, err = git("ls-remote", "--refs", "origin", BRANCH)
    tip = ls.split()[0] if ls else None
    if not tip:
        raise SystemExit("ABORT: no authoritative tip read from the server (%s)" % err[:200])
    track = "refs/remotes/origin/mirror/integration-frontend-apple-pass1"
    if not local_commit(tip):
        git("fetch", "origin", "+%s:%s" % (BRANCH, track))
    got = git("rev-parse", track)[1]
    if not local_commit(tip) or got != tip:
        raise SystemExit("ABORT: tip %s is not a local commit (tracking ref reads %s); refusing to diff "
                         "against a sha we cannot open" % (tip, got or "NOTHING"))
    return tip


def ensure_candidate(sha):
    if local_commit(sha):
        return
    for ref in CANDIDATES:
        if CANDIDATES[ref] == sha:
            git("fetch", "origin", "+%s:refs/remotes/origin/%s" % (ref, ref.split("/")[-1]))
    if not local_commit(sha):
        raise SystemExit("ABORT: candidate %s is not a local commit - will not predict a landing from "
                         "bytes we cannot read" % sha)


def main():
    tip = ensure_tip()

    rows = []
    for ref, sha in CANDIDATES.items():
        rc, ls2, _ = git("ls-remote", "--refs", "origin", ref)
        server = ls2.split()[0] if ls2 else None
        ensure_candidate(sha)
        status_lines = git("diff", "--name-status", tip, sha)[1].splitlines()
        changed = [(l.split("\t")[0][0], l.split("\t")[-1]) for l in status_lines if l.strip()]
        mine = [p for s, p in changed if p in OWN]
        foreign = [(s, p) for s, p in changed if p not in OWN]
        chain = int(git("rev-list", "--count", "%s..%s" % (tip, sha))[1])
        root = git("rev-parse", "%s~%d" % (sha, chain))[1]
        preimage = []
        for p in mine:
            cand_blob = git("ls-tree", "-r", sha, "--", p)[1].split()[2]
            tip_exists = git("cat-file", "-e", "%s:%s" % (tip, p))[0] == 0
            tip_blob = git("rev-parse", "%s:%s" % (tip, p))[1] if tip_exists else None
            preimage.append({"path": p, "candidate_blob": cand_blob, "tip_has_the_path": tip_exists,
                             "tip_blob_same_path": tip_blob, "already_on_the_line": tip_blob == cand_blob})
        rc, mt, err = git("merge-tree", "--write-tree", "--name-only", tip, sha)
        lines = [l for l in mt.splitlines() if l.strip()]
        rows.append({"ref": ref, "sha": sha, "server_sha_ls_remote": server, "server_equals_local": server == sha,
                     "commits_on_tip": chain, "chain_root": root, "chain_root_is_tip": root == tip,
                     "own_paths_changed": mine, "preimage": preimage,
                     "paths_belonging_to_others_in_the_diff": foreign,
                     "merge_tree": {"rc": rc, "tree": lines[0] if lines else None,
                                    "conflict_names": len(lines) - 1, "raw_tail": lines[1:6],
                                    "clean": rc == 0 and len(lines) == 1}})
    out = {"generated_at_local": time.strftime("%Y-%m-%d %H:%M:%S"), "tip": tip, "tip_source": "git ls-remote --refs origin " + BRANCH,
           "candidates": rows, "previous_generation_tip": "b7bb40ee90619c0febc667394279bd3c8a1d835d",
           "tip_moved_since_previous": None}
    out["tip_moved_since_previous"] = out["previous_generation_tip"] != tip
    n = os.path.join(HERE, "cmdr0130_landing_prediction_r1.json")
    io.open(n, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"tip": tip, "tip_moved": out["tip_moved_since_previous"],
                      "all_clean": all(c["merge_tree"]["clean"] and not c["paths_belonging_to_others_in_the_diff"]
                                       for c in rows),
                      "per": [{"ref": c["ref"].split("/")[-1], "root_is_tip": c["chain_root_is_tip"],
                               "conflicts": c["merge_tree"]["conflict_names"],
                               "foreign": len(c["paths_belonging_to_others_in_the_diff"]),
                               "already_on_the_line_any": any(p["already_on_the_line"] for p in c["preimage"])}
                              for c in rows],
                      "json": os.path.basename(n)}, ensure_ascii=False))


main()
