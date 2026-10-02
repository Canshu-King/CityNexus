# -*- coding: utf-8 -*-
"""Publish the reshaped G4 cell plus its shape artifact as the r3 candidate.

The arm's blob is taken from the probe receipt that measured it, not typed here, and the commit is refused
if the tree holds anything other than those two paths. The branch is three commits on the current tip: the
two 18:34 commits re-cut, then this reshape.
"""
import io
import json
import os
import subprocess

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
REPO = "D:/moodle/CityNexus"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
TIP = "06ad00b0267c2bef08d4cdcbae2e5a206ded8666"
BRANCH = "review/1d64acf5-ord0296-g4-floor-r3"
ARM = "backend/tests/test_qoder_ord0296_write_deadline.py"
ART = "review/1d64acf5-g4-single-source-shape/g4_single_source_shape_r1.json"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")
MSG = ("S4-ast-taint CMDR 02:45 line 10, shape as ruled: the single-source exemption stops being granted by "
       "base name and becomes a named path whitelist with one member as shipped. Naming is the only way to "
       "expand it, and a named member must either define `busy_timeout_ms` or state an inline number, so the "
       "table cannot collect leftovers. Measured 8/8 on tip 06ad00b0 with both arms over the same injections: "
       "no-injection green both, `app/db/deep/write_deadline.py` stating 90000 green under the old arm (the "
       "hole) and red under the reshaped one, a named expansion green, a whitelisted-but-empty member red, "
       "the 18:34 sub-floor case red under both, a worker at floor scale red under both, a new 800 ms worker "
       "green under both, family 21 passed. Ships the machine-readable shape artifact beside it. The offenders "
       "cell and the live floor half are unchanged; 0 product bytes.")


def git(*a, cwd=WT):
    r = subprocess.run(["git", "-C", cwd, "-c", "http.proxy=", "-c", "https.proxy="] + list(a),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, timeout=1800)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def main():
    probe = json.load(io.open(os.path.join(HERE, "g4_shape_probe_r1.json"), encoding="utf-8"))
    want = probe["reshaped_arm_blob"]
    got = git("hash-object", os.path.join(WT, ARM.replace("/", os.sep)))[1]
    if got != want:
        print("ABORT: the arm in the tree is not the measured text", got, want)
        return 4
    st = subprocess.run(["git", "-C", WT, "status", "--porcelain"], capture_output=True, text=True,
                        encoding="utf-8", errors="replace", env=ENV, timeout=600)
    lines = [l for l in (st.stdout or "").replace("\r\n", "\n").splitlines() if l.strip()]
    def expand(rel):
        # porcelain reports an untracked directory by name, not the files inside it
        full = os.path.join(WT, rel.replace("/", os.sep))
        if rel.endswith("/") and os.path.isdir(full):
            return sorted(rel + f for f in os.listdir(full))
        return [rel]

    dirty = sorted(x for l in lines for x in expand(l[3:])
                   if not l[3:].startswith(("review/CityNexus", "review/ord")))
    if dirty != sorted([ARM, ART]):
        print("ABORT: the tree holds more than the two paths this hand owns:", dirty)
        return 5
    rc, _o, err = git("add", "--", ARM, ART)
    if rc:
        print("ABORT: git add failed:", err[-200:])
        return 6
    rc, _o, err = git("commit", "-m", MSG, "--", ARM, ART)
    if rc:
        print("ABORT: commit failed:", err[-300:])
        return 7
    sha = git("rev-parse", "HEAD")[1]
    root_parent = git("rev-parse", "HEAD~%d" % int(git("rev-list", "--count", "%s..HEAD" % TIP)[1]))[1]
    rc, _o, err = git("push", "origin", "%s:refs/heads/%s" % (sha, BRANCH))
    if rc:
        print("push failed:", err[-300:])
        return 8
    server = (git("ls-remote", "--refs", "origin", "refs/heads/" + BRANCH, cwd=REPO)[1] or "").split()
    server = server[0] if server else None
    blobs = {}
    for p in (ARM, ART):
        out = git("ls-tree", "-r", server, "--", p, cwd=REPO)[1].splitlines()
        blobs[p] = {"server": out[0].split()[2] if out else None,
                    "local": git("hash-object", os.path.join(WT, p.replace("/", os.sep)))[1]}
        blobs[p]["byte_equal"] = blobs[p]["server"] == blobs[p]["local"]
    diff = git("diff", "--numstat", TIP, server, cwd=REPO)[1]
    doc = {"tip": TIP, "candidate_commit": sha, "chain_root_parent": root_parent,
           "chain_root_parent_is_tip": root_parent == TIP,
           "commits_on_tip": int(git("rev-list", "--count", "%s..HEAD" % TIP)[1]),
           "branch": "refs/heads/" + BRANCH, "server_sha_ls_remote": server,
           "server_equals_pushed": server == sha, "measured_arm_blob": want, "files": blobs,
           "diff_from_tip": diff,
           "product_paths": [l.split("\t")[-1] for l in diff.splitlines()
                             if l.split("\t")[-1].startswith(("backend/app/", "frontend/src/", "contracts/"))]}
    io.open(os.path.join(HERE, "push_g4_floor_r3_receipt_r1.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"sha": sha, "root_is_tip": doc["chain_root_parent_is_tip"],
                      "commits": doc["commits_on_tip"], "server_same": doc["server_equals_pushed"],
                      "blobs_equal": [v["byte_equal"] for v in blobs.values()],
                      "product_paths": doc["product_paths"], "diff": diff.splitlines()},
                     ensure_ascii=False))
    return 0 if (doc["chain_root_parent_is_tip"] and doc["server_equals_pushed"]
                 and all(v["byte_equal"] for v in blobs.values())
                 and not doc["product_paths"]) else 9


raise SystemExit(main())
