# -*- coding: utf-8 -*-
"""Prune the draft shelf directory CMDR 18:34 told me to remove - by index plumbing, no checkout.

The ruling was: keep the authoritative directory, delete the draft one, and "after the blob comparison you
execute it yourself". So this script refuses to remove anything it cannot prove is a byte-for-byte
duplicate under the authoritative directory, works on a temporary index (read-tree / update-index /
write-tree) so no working tree and no other lane's path is touched, pushes without force, and enumerates
the whole branch before and after so the only difference it reports is the six paths it was told to drop.
"""
import io
import json
import os
import subprocess

REPO = "D:/moodle/CityNexus"
REF = "refs/heads/commander/control"
LOCAL = "refs/remotes/verify/pruneview"
DRAFT = "evidence/ord0479-0296-anchor-1605"
KEEP = "evidence/ord0479-0296-anchor-1552"
OUT = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors\shelf_prune_r1.json"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")


def git(*a, **kw):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=kw.get("env", ENV), timeout=1800)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def enumerate_branch(ref):
    rc, out, err = git("ls-tree", "-r", ref)
    if rc != 0:
        raise SystemExit("ls-tree failed: " + err[:200])
    rows = {}
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4 and parts[1] == "blob":
            rows[parts[3]] = parts[2]
    return rows


def main():
    idx = os.path.join(REPO, ".git", "qoder_prune_index")
    env = dict(ENV, GIT_INDEX_FILE=idx)
    if os.path.exists(idx):
        os.remove(idx)
    git("fetch", "-q", "origin", "+" + REF + ":" + LOCAL)
    before = enumerate_branch(LOCAL)
    tip = before and git("rev-parse", LOCAL)[1]
    draft = {p: b for p, b in before.items() if p.startswith(DRAFT + "/")}
    keep = {p.rsplit("/", 1)[-1]: b for p, b in before.items() if p.startswith(KEEP + "/")}
    provable = {n: b for n, b in ((p.rsplit("/", 1)[-1], b) for p, b in draft.items())
                if keep.get(n) == b}
    unprovable = sorted(set(p.rsplit("/", 1)[-1] for p in draft) - set(provable))
    if unprovable:
        raise SystemExit("REFUSE: %d draft paths have no byte-identical twin under %s: %s"
                         % (len(unprovable), KEEP, unprovable))
    rc, tree, err = git("read-tree", LOCAL, env=env)
    if rc:
        raise SystemExit("read-tree failed: " + err[:200])
    rc, out, err = git("update-index", "--force-remove", "--",
                       *[p for p in sorted(draft)], env=env)
    if rc:
        raise SystemExit("update-index failed: " + err[:200])
    new_tree = git("write-tree", env=env)[1]
    msg = ("S4-ast-taint, per CMDR 18:34 item 3: drop the draft census directory. Its 6 paths are "
           "byte-identical twins under %s (compared here, not assumed); the authoritative directory and "
           "every other lane's path are untouched. The draft came from my own double run of the publisher."
           % KEEP)
    commit = git("commit-tree", new_tree, "-p", tip, "-m", msg, env=env)[1]
    rc, out, err = git("push", "origin", "%s:%s" % (commit, REF))
    if rc:
        raise SystemExit("push refused (not forced): " + (out + err)[-300:])
    git("update-ref", LOCAL, commit)
    after = enumerate_branch(commit)
    removed = sorted(set(before) - set(after))
    changed = sorted(p for p in set(before) & set(after) if before[p] != after[p])
    added = sorted(set(after) - set(before))
    ok = (set(removed) == set(draft) and not changed and not added)
    doc = {"branch": REF, "tip_before": tip, "commit_after": commit, "draft_dir": DRAFT,
           "kept_dir": KEEP, "draft_paths": sorted(draft), "proven_identical_under_kept": sorted(provable),
           "paths_removed": removed, "paths_changed_elsewhere": changed, "paths_added": changed and [] or added,
           "tree_before_paths": len(before), "tree_after_paths": len(after),
           "only_the_draft_was_touched": ok,
           "method": "read-tree into a temporary index, update-index --force-remove on the six proven paths, "
                     "write-tree, commit-tree parented on the fetched tip, push without force"}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    if os.path.exists(idx):
        os.remove(idx)
    print(json.dumps({"removed": len(removed), "changed": len(changed), "added": len(added),
                      "paths_before": len(before), "paths_after": len(after),
                      "only_draft_touched": ok}, ensure_ascii=False))
    return 0 if ok else 5


raise SystemExit(main())
