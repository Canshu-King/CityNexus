# -*- coding: utf-8 -*-
"""Publish the G4 floor candidate re-cut onto the day24 tip, as a NEW ref; r1 stays frozen.

The line moved twice since the candidate was cut (day21 -> day23 -> day24), so the sequencer would have had
to carry an old base. Re-cutting is a cherry-pick of the same two commits onto the current tip; the file
they produce is byte-identical to the blob already cited on the shelf, which is checked here rather than
asserted. r1 is neither moved nor deleted, and the landing prediction is read-only.
"""
import io
import json
import os
import subprocess

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
REPO = "D:/moodle/CityNexus"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
TIP = "4fac49f371da0820393d038700bddddafd1176d1"
BRANCH = "review/1d64acf5-ord0296-g4-floor-r2"
OLD_BRANCH = "review/1d64acf5-ord0296-g4-floor-r1"
OLD_HEAD = "b2b3ce17051f3b51ed0278f38e27ca1ddbeca912"
ARM = "backend/tests/test_qoder_ord0296_write_deadline.py"
ARM_BLOB = "395662e3c534229bc8492ea611b6c737257e6228"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")


def git(*a, cwd=WT):
    r = subprocess.run(["git", "-C", cwd, "-c", "http.proxy=", "-c", "https.proxy="] + list(a),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, timeout=1800)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def main():
    sha = git("rev-parse", "HEAD")[1]
    rc, ls_old, _ = git("ls-remote", "--refs", "origin", "refs/heads/" + OLD_BRANCH, cwd=REPO)
    old_server = ls_old.split()[0] if ls_old else None
    rc, _o, err = git("push", "origin", "%s:refs/heads/%s" % (sha, BRANCH))
    if rc:
        print("push failed:", err[-300:])
        return 8
    rc, ls, _ = git("ls-remote", "--refs", "origin", "refs/heads/" + BRANCH, cwd=REPO)
    server = ls.split()[0] if ls else None
    rc, ls2, _ = git("ls-remote", "--refs", "origin", "refs/heads/" + OLD_BRANCH, cwd=REPO)
    old_after = ls2.split()[0] if ls2 else None
    rc, tree, _ = git("ls-tree", "-r", server, "--", ARM, cwd=REPO)
    server_blob = tree.split()[2] if tree else None
    local_blob = git("hash-object", os.path.join(WT, ARM.replace("/", os.sep)))[1]
    rc, mt, mte = git("merge-tree", "--write-tree", "--name-only", TIP, server, cwd=REPO)
    chain = git("rev-list", "--count", "%s..%s" % (TIP, server))[1]
    doc = {"tip": TIP, "candidate_commit": sha, "branch": "refs/heads/" + BRANCH,
           "server_sha_ls_remote": server, "server_equals_pushed": server == sha,
           "arm": ARM, "server_blob_ls_tree": server_blob, "local_hash_object": local_blob,
           "byte_equal": server_blob == local_blob,
           "blob_still_the_one_cited_on_the_shelf": server_blob == ARM_BLOB,
           "r1_before_this_push": old_server, "r1_after_this_push": old_after,
           "r1_untouched": old_server == old_after == OLD_HEAD,
           "commits_re_cut": int(chain), "diff_from_tip": git("diff", "--numstat", TIP, server, cwd=REPO)[1],
           "ff_prediction_read_only": {"merge_tree_rc": rc, "tree": mt.splitlines()[0] if mt else None,
                                       "conflict_names": [l for l in mt.splitlines()[1:] if l.strip()],
                                       "merge_tree_stderr": mte[-160:]},
           "method": "cherry-pick the two r1 commits onto the tip, push as a new ref, re-read with "
                     "ls-remote + ls-tree, and hash the local file with git hash-object"}
    io.open(os.path.join(HERE, "push_g4_floor_r2_receipt_r1.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"sha": sha[:12], "server_same": doc["server_equals_pushed"],
                      "blob_equal": doc["byte_equal"], "same_as_cited": doc["blob_still_the_one_cited_on_the_shelf"],
                      "r1_untouched": doc["r1_untouched"], "re_cut_commits": doc["commits_re_cut"],
                      "ff_tree": doc["ff_prediction_read_only"]["tree"]}, ensure_ascii=False))
    return 0 if (doc["server_equals_pushed"] and doc["byte_equal"] and doc["r1_untouched"]) else 9


raise SystemExit(main())
