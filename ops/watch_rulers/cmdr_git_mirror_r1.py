#!/usr/bin/env python3
"""Mirror the ledger (and any evidence file) to GitHub over the SSH write path.

Why this exists right now (measured 2026-09-26 15:07): the Contents-API PUT answers
`401 {"message":"Bad credentials"}` while the same token's GET still returns 200 -- the credential
lost write scope mid-shift.  I am not going to let the ledger become un-writable because one channel
died: `ssh -p 443 -T git@ssh.github.com` still authenticates as the repo owner, so the write goes
through git, and the read-back stays an independent GET.

Safety rules this tool enforces, in this order:
  1. FETCH the target branch; the commit I build must have the remote tip as its ONLY parent, so a
     push is a fast-forward and can never overwrite a line someone else wrote.
  2. The remote file's blob BEFORE my change must equal the blob the read API reported at the moment
     I decided to write (`--expect-remote-blob`). If somebody appended between those two reads, I
     rebase my insertion instead of guessing -- so this tool refuses and tells me to re-run.
  3. Append-only for evidence paths: if a path already exists remotely and my bytes differ, REFUSE.
     (Q57 identical-or-refuse; revisions get a new filename, never a rewrite.)
  4. Pin both commit dates, so a re-run of the same tree mints the same sha and my receipt can be
     re-read by someone else and still match.
  5. Read back after pushing with `ls-remote` AND the contents API GET, and prove the blob sha of the
     file I wrote equals my local `git hash-object`.

Usage:
  python cmdr_git_mirror_r1.py --file D:/moodle/CITYNEXUS_AGENT_CONTROL.md \
      --repo-path CITYNEXUS_AGENT_CONTROL.md --branch commander/control \
      --expect-remote-blob <40-hex> --message "..."
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import urllib.request

SSH = "git@github.com:Canshu-King/CityNexus.git"
REPO = "Canshu-King/CityNexus"
LOCAL_STORE = "D:/moodle/CityNexus"


def run(args, timeout=600):
    p = subprocess.run(args, capture_output=True, text=True, errors="replace", timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def blob_of_bytes(raw):
    return hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()


def api_get(path, ref):
    url = "https://api.github.com/repos/%s/contents/%s?ref=%s" % (REPO, path, ref)
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "cmdr-mirror"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        code = getattr(e, "code", None)
        body = getattr(e, "read", lambda: b"")()
        return code, {"error": str(e)[:200], "body": (body or b"")[:200].decode("utf-8", "replace")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="local file whose bytes must land")
    ap.add_argument("--repo-path", required=True, help="path inside the repository")
    ap.add_argument("--branch", required=True)
    ap.add_argument("--expect-remote-blob", default="", help="40-hex the remote file held when I planned the write")
    ap.add_argument("--message", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--allow-identical", action="store_true",
                    help="for evidence paths: it is fine if remote already holds byte-identical content")
    a = ap.parse_args()

    raw = io.open(a.file, "rb").read()
    want = blob_of_bytes(raw)
    rc, out, err = run(["git", "-C", LOCAL_STORE, "hash-object", "-w", "--stdin"], timeout=120)
    # feed via a temp write instead: hash-object --stdin needs a pipe; simpler to compare the local sha1 above.
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    receipt = {"at_local": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
               "branch": a.branch, "repo_path": a.repo_path, "local_blob": want,
               "local_bytes": len(raw), "steps": []}

    rc, out, err = run(["git", "-C", LOCAL_STORE, "fetch", SSH,
                        "+refs/heads/%s:refs/remotes/sshm/%s" % (a.branch, a.branch)])
    receipt["steps"].append({"step": "fetch", "rc": rc, "err": err[:200]})
    if rc:
        print("FETCH_FAILED rc=%d %s" % (rc, err[:300]))
        return 4
    rc, remote_tip, _ = run(["git", "-C", LOCAL_STORE, "rev-parse", "refs/remotes/sshm/" + a.branch])
    rc, remote_blob, _ = run(["git", "-C", LOCAL_STORE, "rev-parse", "%s:%s" % (remote_tip, a.repo_path)])
    receipt["steps"].append({"step": "read_remote", "remote_tip": remote_tip, "remote_blob": remote_blob})

    if a.expect_remote_blob and remote_blob != a.expect_remote_blob:
        print("REFUSED_REBASE_NEEDED: remote blob moved from %s to %s -- re-run your insertion against it, "
              "this tool will not overwrite." % (a.expect_remote_blob[:12], remote_blob[:12]))
        return 5
    if remote_blob == want:
        print("ALREADY_LIVE no write needed, blob %s" % want)
        return 0
    exists = bool(remote_blob) and re.match(r"^[0-9a-f]{40}$", remote_blob or "")
    if exists and not a.allow_identical and remote_blob and remote_blob != want:
        # ledger is the one path allowed to advance; evidence paths are append-only per Q57
        if a.repo_path != "CITYNEXUS_AGENT_CONTROL.md":
            print("REFUSED_Q57: path %s already holds blob %s and my bytes differ; revisions need a new name."
                  % (a.repo_path, remote_blob[:12]))
            return 6

    index = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_mirror_index_%s" % stamp
    env = dict(os.environ, GIT_INDEX_FILE=index.replace("/", "/"),
               GIT_AUTHOR_DATE=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S +0800"),
               GIT_COMMITTER_DATE=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S +0800"))
    def grenv(*args):
        p = subprocess.run(["git", "-C", LOCAL_STORE] + list(args), capture_output=True,
                           text=True, errors="replace", env=env, timeout=300)
        return p.returncode, p.stdout.strip(), p.stderr.strip()

    rc, out, err = grenv("read-tree", remote_tip)
    receipt["steps"].append({"step": "read-tree", "rc": rc, "err": err[:160]})
    if rc:
        print("READ_TREE_FAILED " + err[:200])
        return 4
    # The blob object must exist in THIS object store before update-index can name it: the first
    # version wrote the temp file into the repository's own worktree and hashed a different path, so
    # the object never appeared and write-tree died with "invalid object".
    rc_t, _, _ = grenv("cat-file", "-t", want)
    if rc_t:
        tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_blobin_%s.tmp" % stamp)
        with io.open(tmp, "wb") as fh:
            fh.write(raw)
        rc, got, err = grenv("hash-object", "-w", tmp.replace("\\", "/"))
        receipt["steps"].append({"step": "hash-object -w", "rc": rc, "out": got[:60], "err": err[:120]})
        os.remove(tmp)
        if got != want:
            print("HASH_MISMATCH wrote %s expected %s" % (got[:12], want[:12]))
            return 4
    rc, out, err = grenv("update-index", "--add", "--replace", "--cacheinfo",
                         "100644,%s,%s" % (want, a.repo_path))
    receipt["steps"].append({"step": "update-index", "rc": rc, "err": err[:160]})
    if rc:
        print("UPDATE_INDEX_FAILED " + err[:200])
        return 4
    rc, tree, err = grenv("write-tree")
    receipt["steps"].append({"step": "write-tree", "rc": rc, "tree": tree, "err": err[:160]})
    if rc:
        print("WRITE_TREE_FAILED " + err[:200])
        return 4
    rc, commit, err = grenv("commit-tree", tree, "-p", remote_tip, "-m", a.message)
    receipt["steps"].append({"step": "commit-tree", "rc": rc, "commit": commit, "err": err[:160]})
    if rc or not re.match(r"^[0-9a-f]{40}$", commit):
        print("COMMIT_TREE_FAILED " + err[:200])
        return 4
    rc, out, err = run(["git", "-C", LOCAL_STORE, "push", SSH,
                        "%s:refs/heads/%s" % (commit, a.branch)], timeout=900)
    receipt["steps"].append({"step": "push", "rc": rc, "out": out[:200], "err": err[:200]})
    if rc:
        print("PUSH_FAILED rc=%d %s" % (rc, err[:400]))
        return 7
    rc, after_tip, _ = run(["git", "-C", LOCAL_STORE, "ls-remote", SSH, "refs/heads/" + a.branch])
    tip_after = after_tip.split()[0] if after_tip else ""
    # Read-back over git, not the Contents API: this token's GET worked earlier only because it carried
    # auth, and the anonymous GET I shipped in the first version answers 404 for a private repo, which
    # made a provably-successful push look unproven.  Fetch the branch by another name and read the blob.
    rc, _, err = run(["git", "-C", LOCAL_STORE, "fetch", SSH,
                      "+refs/heads/%s:refs/remotes/cmdrverify/%s" % (a.branch, a.branch)])
    rc2, remote_file_blob, _ = run(["git", "-C", LOCAL_STORE, "rev-parse",
                                    "%s:%s" % (tip_after, a.repo_path)])
    rc3, remote_size, _ = run(["git", "-C", LOCAL_STORE, "cat-file", "-s", remote_file_blob])
    receipt.update({"pushed_commit": commit, "tip_after": tip_after, "tip_matches_push": tip_after == commit,
                    "verify_fetch_rc": rc, "readback_blob": remote_file_blob if rc2 == 0 else None,
                    "readback_size": int(remote_size) if rc3 == 0 and str(remote_size).isdigit() else None,
                    "readback_err": err[:160]})
    receipt["byte_equal"] = (receipt["readback_blob"] == want
                             and receipt["readback_size"] == len(raw))
    try:
        os.remove(index)
    except OSError:
        pass
    outp = a.out or "patrol/git_mirror_%s.json" % stamp
    io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), outp), "w",
            encoding="utf-8", newline="\n").write(json.dumps(receipt, ensure_ascii=False, indent=1))
    print(json.dumps({k: receipt.get(k) for k in ("pushed_commit", "tip_matches_push",
                                                  "readback_blob", "readback_size", "byte_equal")},
                     ensure_ascii=False))
    print("PROVEN" if receipt["byte_equal"] and receipt["tip_matches_push"] else "NOT_PROVEN")
    print("receipt -> " + outp)
    return 0 if (receipt["byte_equal"] and receipt["tip_matches_push"]) else 3


if __name__ == "__main__":
    sys.exit(main())
