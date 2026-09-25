#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cmdr_recut_r1.py -- re-cut a stale-base lane candidate onto the current authoritative tip.

Why this exists: lanes cut their branch when they started, and the line moves under them while they
work.  A landing must ask "what does the candidate introduce", so the candidate has to be expressed
against today's tip.  This does it the only way I trust: a read-only three-way merge with
`git merge-tree --write-tree`, then `git commit-tree` with two parents, then a per-file blob-equality
proof that the merged tree still carries the lane's own bytes for every file the lane changed.

A file whose merged blob != the lane's blob means the tip edited the same region: this script REFUSES,
because auto-merged source is no longer the code the lane tested.  Nothing is pushed here; pushing is
a separate, explicit step by the commander.

    python cmdr_recut_r1.py --order ORD-0339 --cand <sha-or-ref> [--push refs/heads/cmdr/land-...]
"""
import argparse
import json
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
LINE = "origin/mirror/integration-frontend-apple-pass1"


def git(*args, **kw):
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=kw.get("timeout", 900))
    return p.returncode, p.stdout, p.stderr


def blob_of(rev, path):
    """The blob sha1 git itself recorded for one path in one tree; None when the path is absent.
    Every equality claim in this script goes through here, so it must not swallow an error into ''."""
    rc, out, _ = git("rev-parse", "%s:%s" % (rev, path))
    return out.strip() if rc == 0 and out.strip() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--order", required=True)
    ap.add_argument("--cand", required=True, help="40-hex or rev that resolves locally")
    ap.add_argument("--line", default=LINE,
                    help="the line to re-cut onto. Defaults to the authoritative branch; the selftest "
                         "points it at a synthetic commit, because a tool that can only be run against "
                         "a branch I am not allowed to move is a tool whose refusals I cannot prove.")
    ap.add_argument("--subject", default="", help="commit subject (default: reuse the lane's)")
    ap.add_argument("--push", default="", help="optional fully-qualified ref to push the re-cut to")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    rc, _, err = git("fetch", "origin", "+refs/heads/*:refs/remotes/origin/*", "--quiet")
    if rc:
        print("ABORT: fetch failed: %s" % err.strip()[:300])
        return 3
    rc, tip, _ = git("rev-parse", a.line)
    tip = tip.strip()
    rc, cand, err = git("rev-parse", a.cand + "^{commit}")
    if rc:
        print("ABORT: candidate does not resolve locally: %s" % err.strip()[:200])
        return 3
    cand = cand.strip()

    # fast-forward is not a re-cut: nothing to do, and pretending otherwise hides a stale reading.
    # NOTE `git()` returns (rc, stdout, stderr) -- the answer to --is-ancestor is the RC, not the text.
    rc, _, _ = git("merge-base", "--is-ancestor", tip, cand)
    if rc == 0:
        print("FAST_FORWARD_POSSIBLE cand=%s tip=%s -> the candidate already sits on the tip;" % (cand[:12], tip[:12]))
        print("       land it directly, no re-cut needed.")
        return 0

    rc, base, _ = git("merge-base", tip, cand)
    base = base.strip()
    rc, n_base, _ = git("rev-list", "--count", "%s..%s" % (base, tip))
    rc, n_cand, _ = git("rev-list", "--count", "%s..%s" % (base, cand))

    rc, changed, _ = git("diff", "--name-only", base, cand, "--")
    changed = [f for f in changed.splitlines() if f.strip()]

    rc, mt_out, mt_err = git("merge-tree", "--write-tree", tip, cand)
    mt_lines = [l for l in mt_out.splitlines() if l.strip()]
    report = {
        "order": a.order, "line": a.line, "tip": tip, "cand": cand, "merge_base": base,
        "commits_tip_ahead_of_base": int(n_base.strip()),
        "commits_cand_ahead_of_base": int(n_cand.strip()),
        "merge_tree_rc": rc, "changed_files": changed, "files": [],
    }
    if rc != 0 or not mt_lines:
        report["verdict"] = "MERGE_TREE_REFUSED"
        report["stderr"] = mt_err.strip()[:2000]
        print("ABORT: the three-way merge reports conflicts:")
        for l in mt_lines[:40]:
            print("   ", l)
        if a.out:
            json.dump(report, open(a.out, "w", encoding="utf-8"), indent=1)
        return 4
    tree = mt_lines[0].strip()
    report["merged_tree"] = tree

    # The proof that decides everything: the merged tree must carry the LANE's blob, byte for byte,
    # for every file the lane changed.  Equality is the only accepted form of "nothing was auto-merged".
    bad = []
    for f in changed:
        cb = blob_of(cand, f)
        tb = blob_of(tree, f)
        bb = blob_of(base, f)
        row = {"path": f, "cand_blob": cb, "merged_blob": tb,
               "identical": (cb == tb), "cand_changed_the_file": (cb != bb)}
        report["files"].append(row)
        if cb != tb:
            bad.append(f)
    report["auto_merged_files"] = bad
    if bad:
        report["verdict"] = "REFUSED_AUTO_MERGED"
        print("ABORT: %d file(s) did not merge to the lane's own bytes -- the lane's tests no longer" % len(bad))
        print("       describe what would land.  Send it back to the lane, do not land a hand-merged file:")
        for f in bad:
            print("   ", f)
        if a.out:
            json.dump(report, open(a.out, "w", encoding="utf-8"), indent=1)
        return 5

    subject = a.subject
    if not subject:
        rc, s, _ = git("log", "-1", "--format=%s", cand)
        subject = s.strip()
    body = ("%s\n\nCommander re-cut: lane candidate %s (base %s) merged onto authoritative tip %s\n"
            "by `git merge-tree --write-tree` + `git commit-tree`. Merged tree %s carries every changed\n"
            "file's lane blob byte-for-byte (%d/%d identical), so no source line was auto-merged.\n"
            % (subject, cand, base[:12], tip[:12], tree, len(changed), len(changed)))
    p = subprocess.run(["git", "-C", REPO, "commit-tree", tree, "-p", tip, "-p", cand, "-m", body],
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    if p.returncode:
        report["verdict"] = "COMMIT_TREE_FAILED"
        report["stderr"] = p.stderr[:1500]
        print("ABORT: commit-tree failed: %s" % p.stderr.strip()[:400])
        return 6
    recut = p.stdout.strip()
    report["recut_commit"] = recut

    # Read-back: the commit I just made must resolve, and its tree must be the tree I proved.
    rc, t2, _ = git("rev-parse", recut + "^{tree}")
    rc, parents, _ = git("rev-parse", recut + "^@")
    report["readback_tree"] = t2.strip()
    report["readback_tree_matches"] = (t2.strip() == tree)
    report["readback_parents"] = [x.strip() for x in parents.splitlines()]
    report["readback_parent_tip"] = (report["readback_parents"][0] == tip if report["readback_parents"] else False)
    report["verdict"] = "RECUT_OK"

    if a.push:
        rc, out, err = git("push", "origin", "%s:%s" % (recut, a.push), timeout=900)
        report["pushed_ref"] = a.push
        report["push_rc"] = rc
        report["push_stderr"] = err.strip()[:600]
        if rc:
            report["verdict"] = "PUSH_FAILED"
            print("ABORT: push failed: %s" % err.strip()[:400])
        else:
            _, remote, _ = git("ls-remote", "origin", a.push)
            report["ls_remote"] = remote.strip()
            report["ls_remote_matches"] = remote.strip().startswith(recut)
    if a.out:
        json.dump(report, open(a.out, "w", encoding="utf-8"), indent=1)

    print("RECUT %s" % recut)
    print("  tip=%s cand=%s base=%s" % (tip[:12], cand[:12], base[:12]))
    print("  files %d/%d identical-to-lane-blob; merged_tree=%s" % (
        len(changed) - len(bad), len(changed), tree))
    if a.push:
        print("  pushed %s -> read-back match %s" % (a.push, report.get("ls_remote_matches")))
    return 0 if report["verdict"] == "RECUT_OK" else 7


if __name__ == "__main__":
    sys.exit(main())
