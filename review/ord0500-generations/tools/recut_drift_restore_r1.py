"""Prove the recut is parent-only after a same-name instrument run overwrote the local copy of one artifact.

`evidence/anchor_form_spec_r26.json` is written by the spec runner every time it runs, so tonight's newer
reading replaced the bytes the published anchor-form ref carries.  A "re-parent" that hashes local files would
have quietly shipped the newer reading under the old hand's name -- the guard refused, and this file records
the three blobs so the refusal is checkable rather than trusted.
"""
import json
import os
import subprocess

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
REL = "evidence/anchor_form_spec_r26.json"
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def run(*args):
    return subprocess.run(["git", "-C", WT] + list(args), capture_output=True, timeout=300, env=ENV)


def main():
    r4 = run("ls-remote", "--refs", "origin",
             "refs/heads/review/newlane-ord0500-phone-anchor-form-r4").stdout.split()[0].decode()
    sr = run("ls-remote", "--refs", "origin",
             "refs/heads/review/0afdb49b-ord0500-spec-run-r1").stdout.split()[0].decode()
    b_r4 = run("rev-parse", "%s:review/ord0500-anchor-form/%s" % (r4, REL)).stdout.decode().strip()
    b_sr = run("rev-parse", "%s:review/ord0500-spec-run/%s" % (sr, REL)).stdout.decode().strip()
    body = run("cat-file", "blob", b_r4).stdout
    open(os.path.join(LANE, REL), "wb").write(body.replace(b"\r\n", b"\n"))
    local = open(os.path.join(LANE, REL), "rb").read()
    b_local = subprocess.run(["git", "-C", WT, "hash-object", "-w", "-t", "blob", "--stdin"],
                             capture_output=True, input=local, env=ENV).stdout.decode().strip()
    out = {"drift_found_because": "the same instrument ran again tonight and wrote over the local copy",
           "r4_ref": r4, "r4_carries_blob": b_r4,
           "newer_reading_on": {"ref_head": sr, "path": "review/ord0500-spec-run/" + REL, "blob": b_sr},
           "restored_local_file_bytes": len(local), "local_lf_blob_now": b_local,
           "local_equals_r4": b_local == b_r4, "newer_copy_still_published_untouched": b_sr != b_r4}
    dest = os.path.join(LANE, "run", "recut_drift_note_r1.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))
    if not out["local_equals_r4"]:
        raise SystemExit("ABORT_RESTORE_DID_NOT_MATCH_THE_REF")
    print("WROTE " + dest)


if __name__ == "__main__":
    main()
