# -*- coding: utf-8 -*-
"""Re-cut the one-gate judgement change onto the day25 tip and publish it as -r2.

The tree already holds the final file from the probe run; this writes nothing new. The commit is made on a
detached tip so the candidate is a single child of the current authoritative line (fast-forward by
construction), and it is pushed under a name of its own because it belongs to a different ruling than the
G4 floor candidate. Read-back is ls-remote plus ls-tree against a local hash-object.
"""
import io
import json
import os
import subprocess

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
REPO = "D:/moodle/CityNexus"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
TIP = "06ad00b0267c2bef08d4cdcbae2e5a206ded8666"
BRANCH = "review/1d64acf5-ord0476-response-set-r2"
TEST = "backend/tests/test_qoder_ord0476_checkins.py"
FINAL_BLOB = json.load(io.open(os.path.join(HERE, "ord0476_gate_probe_r2.json"), encoding="utf-8"))["final_test_blob"]
ARM = "test_the_contract_declares_both_doors_and_no_control_they_lack"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")
MSG = ("S4-ast-taint CMDR 01:24 裁①, one gate only: the ORD-0476 read door's documented responses stop being "
       "a whole-set equality and become a named promise plus a named-expansion whitelist "
       "(backend/tests/test_qoder_ord0476_checkins.py). Six states measured on the day24 tip - control green, "
       "an unnamed 429 red on the whitelist line, the same 429 named green, a dropped 409 red on the promise "
       "line, a whitelisted-but-undocumented code red, whole file 11 passed; every mutation reverted and "
       "re-hashed, contracts/openapi.yaml byte-identical to the tip. The other five drift-prone sites the "
       "census named are untouched: four files unchanged to the byte and the fifth line identical. "
       "0 product bytes.")


def git(*a, cwd=WT):
    r = subprocess.run(["git", "-C", cwd, "-c", "http.proxy=", "-c", "https.proxy="] + list(a),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, timeout=1800)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def main():
    local = git("hash-object", os.path.join(WT, TEST.replace("/", os.sep)))[1]
    if local != FINAL_BLOB:
        print("ABORT: the file in the tree is not the six-state-verified text", local)
        return 4
    rc, _o, err = git("add", "--", TEST)
    if rc:
        print("ABORT: git add failed:", err[-200:])
        return 5
    rc, _o, err = git("commit", "-m", MSG, "--", TEST)
    if rc:
        print("ABORT: commit failed:", err[-300:])
        return 6
    sha = git("rev-parse", "HEAD")[1]
    parent = git("rev-parse", "HEAD^")[1]
    rc, _o, err = git("push", "origin", "%s:refs/heads/%s" % (sha, BRANCH))
    if rc:
        print("push failed:", err[-300:])
        return 8
    rc, ls, _ = git("ls-remote", "--refs", "origin", "refs/heads/" + BRANCH, cwd=REPO)
    server = ls.split()[0] if ls else None
    tree_line = git("ls-tree", "-r", server, "--", TEST, cwd=REPO)[1].splitlines()
    server_blob = tree_line[0].split()[2] if tree_line else None
    mt = git("merge-tree", "--write-tree", "--name-only", TIP, server, cwd=REPO)[1]
    doc = {"tip": TIP, "candidate_commit": sha, "parent": parent, "parent_is_tip": parent == TIP,
           "branch": "refs/heads/" + BRANCH, "server_sha_ls_remote": server,
           "server_equals_pushed": server == sha, "arm": ARM, "test_file": TEST,
           "final_test_blob": local,
           "server_blob_ls_tree": server_blob,
           "diff_from_tip": git("diff", "--numstat", TIP, server, cwd=REPO)[1],
           "product_paths_in_diff": [l.split("\t")[-1] for l in
                                     git("diff", "--name-only", TIP, server, cwd=REPO)[1].splitlines()
                                     if not l.startswith("backend/tests/")],
           "ff_prediction_read_only": mt.splitlines()[0] if mt else None,
           "message": MSG}
    io.open(os.path.join(HERE, "push_ord0476_gate_receipt_r2.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"sha": sha, "parent_is_tip": doc["parent_is_tip"],
                      "server_same": doc["server_equals_pushed"],
                      "blob_equal": server_blob == doc["final_test_blob"],
                      "diff": doc["diff_from_tip"], "non_test_paths": doc["product_paths_in_diff"]},
                     ensure_ascii=False))
    return 0 if (doc["parent_is_tip"] and doc["server_equals_pushed"] and server_blob == local
                 and not doc["product_paths_in_diff"]) else 9


raise SystemExit(main())
