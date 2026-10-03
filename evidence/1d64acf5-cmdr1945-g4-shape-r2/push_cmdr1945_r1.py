# -*- coding: utf-8 -*-
"""Publish both reshaped candidates against the tip the commander dispatched twice (19:45 and 19:53).

The 0476 candidate is committed here because the probe left its verified text in the tree; the blob is
re-read from that probe's receipt and the commit is refused if the tree holds anything else. The G4 branch is
pushed by name so its three commits plus the regenerated artifact travel unchanged. Both refs are then read
back from the server and checked against the tip: chain root, foreign paths in the diff, conflict names.
"""
import io
import json
import os
import subprocess

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
REPO = "D:/moodle/CityNexus"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
TIP = "bf4f776b0ba943b88817dfcc0cb3442d75fd9e21"
G4_BRANCH = "review/1d64acf5-ord0296-g4-floor-r4"
D76_BRANCH = "review/1d64acf5-ord0476-response-set-r3"
D76_FILE = "backend/tests/test_qoder_ord0476_checkins.py"
G4_FILE = "backend/tests/test_qoder_ord0296_write_deadline.py"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")
MSG = ("S4-ast-taint CMDR 19:45/19:53 re-dispatch, on the tip named there: the ORD-0476 read door's documented "
       "responses as a named promise plus a named-expansion whitelist, re-measured six states on this "
       "generation - control green, an unnamed legitimate 429 red on the whitelist line, the same 429 named "
       "green, a dropped promised 409 red on the promise line, a named-but-undocumented code red, whole file "
       "11 passed; every mutation reverted and re-hashed, contracts/openapi.yaml byte-identical to the tip, "
       "the four other census sites untouched to the byte. 0 product bytes.")


def git(*a, cwd=WT):
    r = subprocess.run(["git", "-C", cwd, "-c", "http.proxy=", "-c", "https.proxy="] + list(a),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, timeout=1800)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def ls_remote(ref):
    return ((git("ls-remote", "--refs", "origin", ref, cwd=REPO)[1] or "").split() or [None])[0]


def paths_of(rev):
    out = git("diff", "--name-status", TIP, rev, cwd=REPO)[1]
    changed = [(l.split("\t")[0][0], l.split("\t")[-1]) for l in out.splitlines() if l.strip()]
    own = {"backend/tests/test_qoder_ord0296_write_deadline.py", D76_FILE,
           "review/1d64acf5-g4-single-source-shape/g4_single_source_shape_r1.json",
           "review/1d64acf5-g4-single-source-shape/g4_single_source_shape_r2.json"}
    return [p for _s, p in changed if p in own], [(s, p) for _s, p in changed if p not in own]


def record(name, rev):
    chain = int(git("rev-list", "--count", "%s..%s" % (TIP, rev), cwd=REPO)[1])
    root = git("rev-parse", "%s~%d" % (rev, chain), cwd=REPO)[1]
    own, foreign = paths_of(rev)
    mt = [l for l in (git("merge-tree", "--write-tree", "--name-only", TIP, rev, cwd=REPO)[1]
                      or "").splitlines() if l.strip()]
    blobs = {}
    for p in own:
        line = git("ls-tree", "-r", rev, "--", p, cwd=REPO)[1].splitlines()
        blobs[p] = {"server_blob_ls_tree": line[0].split()[2] if line else None}
    return {"ref": name, "sha": rev, "server_sha_ls_remote": ls_remote("refs/heads/" + name),
            "commits_on_tip": chain, "chain_root": root, "chain_root_is_tip": root == TIP,
            "own_paths": own, "foreign_paths_in_diff": foreign,
            "merge_tree": {"tree": mt[0] if mt else None, "conflict_names": max(len(mt) - 1, 0)},
            "blobs": blobs}


def main():
    probe = json.load(io.open(os.path.join(HERE, "ord0476_gate_probe_r3.json"), encoding="utf-8"))
    want = probe["final_test_blob"]
    head = git("rev-parse", "HEAD")[1]
    if head != TIP:
        print("ABORT: the tree is not detached at the dispatched tip:", head)
        return 4
    got = git("hash-object", os.path.join(WT, D76_FILE.replace("/", os.sep)))[1]
    if got != want:
        print("ABORT: the file in the tree is not the six-state-verified text", got)
        return 5
    git("checkout", "-b", D76_BRANCH)
    rc, _o, err = git("add", "--", D76_FILE)
    rc, _o, err = git("commit", "-m", MSG, "--", D76_FILE)
    if rc:
        print("ABORT: commit failed:", err[-300:])
        return 6
    for b in (D76_BRANCH, G4_BRANCH):
        rc, _o, err = git("push", "origin", "refs/heads/%s:refs/heads/%s" % (b, b))
        if rc:
            print("push failed for", b, err[-300:])
            return 8
    d76_sha = git("rev-parse", D76_BRANCH)[1]
    g4_sha = git("rev-parse", G4_BRANCH)[1]
    docs = {"tip": TIP, "candidates": [record(D76_BRANCH, d76_sha), record(G4_BRANCH, g4_sha)],
            "g4_arm_blob_at_candidate": git("rev-parse", "%s:%s" % (g4_sha, G4_FILE), cwd=REPO)[1],
            "d76_arm_blob_at_candidate": git("rev-parse", "%s:%s" % (d76_sha, D76_FILE), cwd=REPO)[1],
            "g4_tip_blob": git("rev-parse", "%s:%s" % (TIP, G4_FILE), cwd=REPO)[1],
            "d76_tip_blob": git("rev-parse", "%s:%s" % (TIP, D76_FILE), cwd=REPO)[1],
            "shape_measured_tip": json.load(io.open(os.path.join(HERE, "g4_shape_probe_r2.json"),
                                                    encoding="utf-8"))["tip"],
            "six_states_measured_tip": probe["tip"]}
    for c in docs["candidates"]:
        c["server_equals_local"] = c["server_sha_ls_remote"] == c["sha"]
    io.open(os.path.join(HERE, "push_cmdr1945_receipt_r1.json"), "w", encoding="utf-8").write(
        json.dumps(docs, ensure_ascii=False, indent=1))
    print(json.dumps([{"ref": c["ref"], "sha": c["sha"][:12], "server_same": c["server_equals_local"],
                       "root_is_tip": c["chain_root_is_tip"], "commits": c["commits_on_tip"],
                       "own": len(c["own_paths"]), "foreign": len(c["foreign_paths_in_diff"]),
                       "conflicts": c["merge_tree"]["conflict_names"]} for c in docs["candidates"]],
                     ensure_ascii=False))
    ok = all(c["server_equals_local"] and c["chain_root_is_tip"] and not c["foreign_paths_in_diff"]
             and not c["merge_tree"]["conflict_names"] for c in docs["candidates"])
    return 0 if ok else 9


raise SystemExit(main())
