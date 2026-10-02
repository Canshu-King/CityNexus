# -*- coding: utf-8 -*-
"""Re-land the G4 floor fix on top of the first candidate, so both commits stay reachable.

The first candidate carried one predicate too many: a second rule with the same condition as `unsourced`
can never fire, and probe P2 proved which arm actually catches the worker-at-scale case. Removing it after
publishing means the branch must keep the earlier commit as an ancestor rather than replace it, so the blob
already cited on the shelf stays reachable and the diff against the base is still one test file.
"""
import io
import json
import os
import subprocess
import sys

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
REPO = "D:/moodle/CityNexus"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
BASE = "e7ff7938ea41c5ac69afb1172acc4625159c7911"
FIRST = "2a648d7c09de1e6c19c8c368ef2657d811c78545"
BRANCH = "review/1d64acf5-ord0296-g4-floor-r1"
ARM = "backend/tests/test_qoder_ord0296_write_deadline.py"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")
MSG = ("S4-ast-taint CMDR 18:34, second commit on the same candidate: drop the predicate I had added "
       "alongside `unsourced`. Same condition, so it could never fire - probe P2 (90000 ms in a worker "
       "file) is caught by `unsourced` at the older line, which is what the run record attributes. What "
       "stays is the one new rule: a file that already asks write_deadline or settings for the wait may "
       "state no inline busy_timeout number at any size. Test bytes only; 0 product bytes.")


def git(*a, cwd=WT):
    r = subprocess.run(["git", "-C", cwd, "-c", "http.proxy=", "-c", "https.proxy="] + list(a),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, timeout=1800)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def main():
    final = io.open(os.path.join(WT, ARM.replace("/", os.sep)), encoding="utf-8").read()
    if "worker_at_or_above_floor" in final:
        print("ABORT: the duplicate predicate is still in the file")
        return 4
    io.open(os.path.join(HERE, "arm_final_r2.txt"), "w", encoding="utf-8", newline="\n").write(final)
    rc, _o, err = git("checkout", "--", ARM)
    if rc:
        print("ABORT: could not clean the file:", err[:200])
        return 5
    rc, _o, err = git("checkout", "--detach", FIRST)
    if rc:
        print("ABORT: cannot check out the first candidate:", err[:200])
        return 6
    io.open(os.path.join(WT, ARM.replace("/", os.sep)), "w", encoding="utf-8",
            newline="\n").write(final)
    rc, _o, err = git("add", "--", ARM)
    rc, cout, err = git("commit", "-m", MSG, "--", ARM)
    if rc:
        print("commit failed:", (out if (out := ("" or "")) else "") + err[-300:])
        return 7
    sha = git("rev-parse", "HEAD")[1]
    parent = git("rev-parse", "HEAD^")[1]
    rc, _o, err = git("push", "origin", "%s:refs/heads/%s" % (sha, BRANCH))
    if rc:
        print("push failed:", err[-300:])
        return 8
    rc, ls, _ = git("ls-remote", "--refs", "origin", "refs/heads/" + BRANCH, cwd=REPO)
    server_sha = ls.split()[0] if ls else None
    rc, diff, _ = git("diff", "--numstat", BASE, sha, cwd=REPO)
    blobs = {}
    for f in [ARM]:
        rc, o1, _e = git("ls-tree", "-r", server_sha or sha, "--", f, cwd=REPO)
        blob = o1.split()[2] if o1 else None
        local = git("hash-object", os.path.join(WT, f.replace("/", os.sep)))[1]
        blobs[f] = {"server_blob_ls_tree": blob, "local_hash_object": local,
                    "byte_equal": blob is not None and blob == local}
    doc = {"base": BASE, "first_candidate": FIRST, "candidate_commit": sha, "parent": parent,
           "parent_is_first_candidate": parent == FIRST, "ancestor_of_candidate": FIRST in
           git("rev-list", sha)[1].split(), "branch": "refs/heads/" + BRANCH,
           "server_sha_ls_remote": server_sha, "server_sha_equals_pushed": server_sha == sha,
           "diff_from_base": diff, "files": blobs, "message": MSG,
           "why_a_second_commit": "the first candidate is already cited by blob on the shelf; replacing it "
                                  "would leave that citation pointing at nothing, so the removal is a "
                                  "child commit and the branch diff against the base is still one file"}
    io.open(os.path.join(HERE, "land_g4_floor_receipt_r2.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"sha": sha, "parent_ok": doc["parent_is_first_candidate"],
                      "first_reachable": doc["ancestor_of_candidate"],
                      "server_same": doc["server_sha_equals_pushed"],
                      "blob_equal": [v["byte_equal"] for v in blobs.values()]}, ensure_ascii=False))
    return 0 if (doc["parent_is_first_candidate"] and doc["server_sha_equals_pushed"]
                 and all(v["byte_equal"] for v in blobs.values())) else 9


raise SystemExit(main())
