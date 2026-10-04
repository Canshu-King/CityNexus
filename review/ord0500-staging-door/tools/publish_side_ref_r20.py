"""Publish this hand's instrument as its own review ref, without touching ORD-0500 r19.

Why a side ref: r19 is sitting in front of the commander waiting to be landed, and advancing a ref
somebody is about to merge is how heads get swapped under a reviewer.  The door code is a separate
deliverable, so it gets a separate ref -- and because the block has to cite it with coordinates that
`git cat-file -t` answers, the files have to be objects in the line's own store, not lane-local bytes.

The commit is built from a temporary index on top of the live tip (read live, never remembered), so the
diff against the tip is exactly the instrument files: zero product paths.  Nothing is written into the
worktree, so the tree the r19 landing reads stays byte-for-byte what it was.
"""
import json
import os
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
MY_REF = os.environ.get("PUBLISH_REF") or "refs/heads/review/0afdb49b-ord0500-staging-door-r1"
SUB = os.environ.get("PUBLISH_SUB") or "review/ord0500-staging-door"
DEFAULT_FILES = [("tools/stage_door_r20.py", "tools"), ("tools/stage_door_r20_mutants.py", "tools"),
                 ("tools/stage_door_r20_receipt.py", "tools"),
                 ("evidence/stage_door_r20.json", "evidence"),
                 ("evidence/stage_door_r20_mutants.json", "evidence"),
                 ("run/r20_STAGING_RED.json", "run"), ("run/r20_forced_red.txt", "run"),
                 ("run/r20_green_control.txt", "run"), ("run/commit_r20_door_msg.txt", "run")]
if os.environ.get("PUBLISH_MANIFEST"):
    FILES = [tuple(x) for x in json.load(open(os.path.join(LANE, os.environ["PUBLISH_MANIFEST"]),
                                              encoding="utf-8"))]
else:
    FILES = DEFAULT_FILES
MSG_FILE = os.environ.get("PUBLISH_MSG") or "run/commit_r20_door_msg.txt"
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"
IDX = os.path.join(LANE, "run", os.environ.get("PUBLISH_INDEX") or "r20_door.tmp_index")


def git(*args, **kw):
    env = kw.pop("env", None) or ENV
    p = subprocess.run(["git", "-C", WT] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=600, env=env, **kw)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def lf_blob(path):
    """Normalise to LF on the way in: .gitattributes pins *.py eol=lf, and a CRLF copy makes the
    worktree read dirty right after the add -- which has burned this lane before."""
    data = open(os.path.join(LANE, path), "rb").read().replace(b"\r\n", b"\n")
    rc, out = git("hash-object", "-w", "-t", "blob", "--stdin", input=data)
    if rc:
        raise SystemExit("ABORT_HASH_OBJECT %s %s" % (path, out[:160]))
    return out.strip()


def main():
    rc, out = git("ls-remote", "--refs", "origin", MY_REF)
    if out.strip():
        raise SystemExit("ABORT_REF_NOT_FREE %s already answers %s" % (MY_REF, out.split()[0]))
    rc, out = git("ls-remote", "--refs", "origin", TIP_REF)
    tip = out.split()[0]
    if len(tip) != 40:
        raise SystemExit("ABORT_NO_TIP " + out[:160])

    if os.path.exists(IDX):
        os.remove(IDX)
    env = dict(ENV)
    env["GIT_INDEX_FILE"] = IDX
    rc, out = git("read-tree", tip, env=env)
    if rc:
        raise SystemExit("ABORT_READ_TREE " + out[:200])
    blobs = {}
    for rel, group in FILES:
        if not os.path.exists(os.path.join(LANE, rel)):
            raise SystemExit("ABORT_MISSING_ARTIFACT " + rel)
        blobs["%s/%s/%s" % (SUB, group, os.path.basename(rel))] = lf_blob(rel)
    for path, blob in sorted(blobs.items()):
        rc, out = git("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, path), env=env)
        if rc:
            raise SystemExit("ABORT_UPDATE_INDEX %s %s" % (path, out[:160]))
    rc, tree = git("write-tree", env=env)
    tree = tree.strip()
    rc, msg = git("commit-tree", tree, "-p", tip, "-F", os.path.join(LANE, MSG_FILE))
    if rc:
        raise SystemExit("ABORT_COMMIT_TREE " + msg[:200])
    commit = msg.strip()
    rc, out = git("diff", "--name-only", "%s..%s" % (tip, commit))
    touched = [l.strip() for l in out.splitlines() if l.strip()]
    product = [p for p in touched if not p.startswith("review/")]
    if product:
        raise SystemExit("ABORT_STRAY_PRODUCT_PATHS " + json.dumps(product, ensure_ascii=False))
    # CMDR-0925-2128 says landed instrument paths are not rewritten, and a page that already cited a
    # receipt's blob loses its recomputation entry if the same path changes under it -- so publishing
    # over bytes that are already on the line is refused here, in the tool that does the push.
    overwrite = []
    for path in sorted(blobs):
        # `cat-file -e` answers existence; `rev-parse --quiet` leaks its own error text into stdout, which
        # is how this arm first mis-read an absent path as a collision.
        rce, _ = git("cat-file", "-e", "%s:%s" % (tip, path))
        if rce:
            continue
        rco, cur = git("rev-parse", "%s:%s" % (tip, path))
        if cur.strip() and cur.strip() != blobs[path]:
            overwrite.append({"path": path, "on_line": cur.strip(), "mine": blobs[path]})
    if overwrite and not os.environ.get("PUBLISH_ALLOW_OVERWRITE"):
        raise SystemExit("ABORT_OVERWRITES_LANDED_BYTES %s -- give these a generation name instead of "
                         "replacing them on the line" % json.dumps(overwrite, ensure_ascii=False)[:400])
    rc, out = git("push", "origin", "%s:%s" % (commit, MY_REF))
    if rc:
        raise SystemExit("ABORT_PUSH " + out[:300])
    rc, back = git("ls-remote", "--refs", "origin", MY_REF)
    got = back.split()[0] if back.strip() else "NOT_READ_BACK"
    rc, listed = git("ls-tree", "-r", "--name-only", commit)
    # every cited coordinate must resolve: prove it here rather than letting the block quote a sha that
    # the ledger gate (or the commander) cannot cat-file
    for path, blob in sorted(blobs.items()):
        rc, kind = git("cat-file", "-t", blob)
        if kind.strip() != "blob":
            raise SystemExit("ABORT_BLOB_NOT_RESOLVABLE %s %s" % (path, blob))
    print(json.dumps({"tip_parent": tip, "commit": commit, "tree": tree, "ref": MY_REF,
                      "read_back": got, "commit_equals_read_back": got == commit,
                      "paths": len(touched), "product_paths": product,
                      "blobs": blobs, "in_commit": sorted(x.strip() for x in listed.splitlines())},
                     indent=2, ensure_ascii=False))
    os.path.exists(IDX) and os.remove(IDX)


if __name__ == "__main__":
    main()
