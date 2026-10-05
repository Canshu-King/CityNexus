"""Print the identity of every file this hand is about to publish, computed from the bytes, before the push.

Why this exists as its own artifact: the block will say "the emitter and the voucher are now citable from
the line".  That sentence is only checkable if each file's blob id was recorded the same way git computes
it (LF-normalised, sha1 of the content) -- a remembered or hand-typed id is exactly the failure this lane
has now self-reported three times.  The publisher recomputes ids anyway, so this receipt is the *pre*-push
statement; the post-push list is read back from the ref by the same command the block quotes.
"""
import hashlib
import json
import os
import subprocess

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
MAN = os.path.join(LANE, "run", "vouch_r1_manifest.json")
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"
SUB = "review/fleet-rescan-vouch-r1"


def git(*args, **kw):
    # capture_output=True and input= are mutually exclusive in subprocess.run; the publisher this
    # mirrors passes the pipes itself so a blob can be fed over stdin.
    stdin = kw.pop("input", None)
    p = subprocess.run(["git", "-C", WT] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=300, env=ENV, input=stdin, **kw)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def main():
    files = json.load(open(MAN, encoding="utf-8"))
    out = {"files": [], "git_sha1_of_content_matches_blob": True}
    for rel, _group in [tuple(x) for x in files]:
        path = os.path.join(LANE, rel)
        if rel == "run/vouch_r1_identities.json":
            # this receipt's own id cannot be inside itself -- the bytes it hashes are the bytes this
            # command writes, so the honest statement is "absent at read time", not a guessed sha.
            out["files"].append({"rel": rel, "status": "absent_at_read_time"})
            continue
        if not os.path.exists(path):
            raise SystemExit("ABORT_ARTIFACT_MISSING " + rel)
        raw = open(path, "rb").read()
        lf = raw.replace(b"\r\n", b"\n")
        rc, hashout = git("hash-object", "-w", "-t", "blob", "--stdin", input=lf)
        if rc:
            raise SystemExit("ABORT_HASH_OBJECT " + rel)
        blob = hashout.strip()
        local = hashlib.sha1(b"blob %d\0" % len(lf) + lf).hexdigest()
        rec = {"rel": rel, "raw_bytes": len(raw), "lf_bytes": len(lf), "blob": blob,
               "crlf": raw.count(b"\r\n"), "local_git_sha1": local, "blob_equals_local": blob == local}
        if blob != local:
            out["git_sha1_of_content_matches_blob"] = False
        out["files"].append(rec)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if not out["git_sha1_of_content_matches_blob"]:
        raise SystemExit("ABORT_IDENTITY_MISMATCH")


if __name__ == "__main__":
    main()
