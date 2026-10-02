# -*- coding: utf-8 -*-
"""Both candidates that are waiting for the sequencer, re-measured against the tip the night watch named.

Nothing here lands anything: it answers, per candidate, three questions a landing gate would ask - is the
chain root the current tip, does the tip still hold the same bytes for every path the candidate changes,
and does a read-only merge predict any conflict name.
"""
import io
import json
import os
import subprocess

REPO = "D:/moodle/CityNexus"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
TIP = "06ad00b0267c2bef08d4cdcbae2e5a206ded8666"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")
CANDIDATES = {
    "refs/heads/review/1d64acf5-ord0296-g4-floor-r3": "e89b3656e44a1c9c33d6a5ed5c78cf55950f7d85",
    "refs/heads/review/1d64acf5-ord0476-response-set-r2": "5450d4e68ef369cccdd2425c883f82dbaa80db09",
}


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=900)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


OWN = {"backend/tests/test_qoder_ord0296_write_deadline.py",
       "backend/tests/test_qoder_ord0476_checkins.py",
       "review/1d64acf5-g4-single-source-shape/g4_single_source_shape_r1.json"}


def main():
    rows = []
    for ref, sha in CANDIDATES.items():
        rc, ls, _ = git("ls-remote", "--refs", "origin", ref)
        server = ls.split()[0] if ls else None
        status_lines = git("diff", "--name-status", TIP, sha)[1].splitlines()
        changed = [(l.split("\t")[0][0], l.split("\t")[-1]) for l in status_lines if l.strip()]
        mine = [p for s, p in changed if p in OWN]
        foreign = [(s, p) for s, p in changed if p not in OWN]
        chain = int(git("rev-list", "--count", "%s..%s" % (TIP, sha))[1])
        root = git("rev-parse", "%s~%d" % (sha, chain))[1]
        preimage = []
        for p in mine:
            cand_blob = git("ls-tree", "-r", sha, "--", p)[1].split()[2]
            tip_exists = git("cat-file", "-e", "%s:%s" % (TIP, p))[0] == 0
            tip_blob = git("rev-parse", "%s:%s" % (TIP, p))[1] if tip_exists else None
            preimage.append({"path": p, "candidate_blob": cand_blob, "tip_has_the_path": tip_exists,
                             "tip_blob_same_path": tip_blob,
                             "already_on_the_line": tip_blob == cand_blob})
        rc, mt, err = git("merge-tree", "--write-tree", "--name-only", TIP, sha)
        lines = [l for l in mt.splitlines() if l.strip()]
        rows.append({"ref": ref, "sha": sha, "server_sha_ls_remote": server, "server_equals_local": server == sha,
                     "commits_on_tip": chain, "chain_root": root, "chain_root_is_tip": root == TIP,
                     "own_paths_changed": mine, "preimage": preimage,
                     "paths_belonging_to_others_in_the_diff": foreign,
                     "base_is_current_tip": root == TIP,
                     "merge_tree": {"rc": rc, "tree": lines[0] if lines else None,
                                    "conflict_names": len(lines[1:])}})
    doc = {"tip": TIP, "own_paths_declared": sorted(OWN),
           "tip_source": "git ls-remote --refs origin "
           "refs/heads/mirror/integration-frontend-apple-pass1",
           "candidates": rows}
    io.open(os.path.join(HERE, "cmdr0245_landing_prediction_r2.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    for r in rows:
        print(json.dumps({"sha": r["sha"][:12], "server_same": r["server_equals_local"],
                          "root_is_tip": r["chain_root_is_tip"], "commits": r["commits_on_tip"],
                          "own_paths": len(r["own_paths_changed"]),
                          "foreign_paths_in_diff": len(r["paths_belonging_to_others_in_the_diff"]),
                          "already_on_the_line": [p["already_on_the_line"] for p in r["preimage"]],
                          "conflicts": r["merge_tree"]["conflict_names"]}, ensure_ascii=False))


raise SystemExit(main())
