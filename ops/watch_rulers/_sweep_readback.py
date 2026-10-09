"""Build the read-back receipt for the published sweep artifact.

The sweep JSON cannot carry its own blob (a blob is computed over the file's bytes), so the independent
read-back lives in a second file that names the first one's coordinates. Numbers here are recomputed from
the local bytes and from git, never typed.
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
REPO = "D:/moodle/CityNexus"
LOCAL = os.path.join(ROOT, sys.argv[1] if len(sys.argv) > 1 else "_q64_sweep_r1.json")
ROUTE = sys.argv[2] if len(sys.argv) > 2 else "evidence/q64-sweep-S1/sweep_r1.json"
OUT = sys.argv[3] if len(sys.argv) > 3 else "_q64_sweep_readback_r1.json"


def run(*a):
    r = subprocess.run(list(a), capture_output=True)
    return r.returncode, r.stdout.decode("utf-8", "replace").strip(), r.stderr.decode("utf-8", "replace").strip()


def blob_of(b):
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


def main():
    raw = io.open(LOCAL, "rb").read()
    local_blob = blob_of(raw)
    rc, local_ho, _ = run("git", "hash-object", LOCAL)
    rc, remote_blob, e1 = run("git", "-C", REPO, "rev-parse", "origin/cmdcontrol:" + ROUTE)
    rc2, remote_bytes, e2 = run("git", "-C", REPO, "cat-file", "-s", remote_blob) if rc == 0 else (1, "", "")
    rc3, commit, _ = run("git", "-C", REPO, "rev-parse", "origin/cmdcontrol")
    doc = json.load(io.open(LOCAL, encoding="utf-8"))
    out = {
     "schema": "CNX_Q64_SWEEP_READBACK_V1",
     "lane": "S1-q64sweep",
     "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
     "generation": doc["generation"],
     "tip_moved": doc["tip_moved"],
     "ruler": doc["ruler"],
     "subject_route": "commander/control:" + ROUTE,
     "subject_blob_expected_from_local_bytes": local_blob,
     "subject_blob_git_hash_object": local_ho,
     "subject_blob_rev_parse": remote_blob,
     "subject_bytes_local": len(raw),
     "subject_bytes_rev_parse": int(remote_bytes) if remote_bytes.isdigit() else None,
     "publish_commit": commit,
     "readback_command": "git -C D:/moodle/CityNexus fetch origin "
                        "refs/heads/commander/control:refs/remotes/origin/cmdcontrol && "
                        "git -C D:/moodle/CityNexus rev-parse origin/cmdcontrol:" + ROUTE,
     "all_four_numbers_equal": None,
     "verdict": None,
     "note": "publish_evidence_gated_r1.py reported BYTE-LEVEL MATCH on its own read-back; this receipt is the "
             "independent second read through a different door (local sha1 over bytes, git hash-object, and "
             "rev-parse of the fetched ref), which is what the acceptance asks for.",
    }
    agree = (local_blob == local_ho == remote_blob and out["subject_bytes_local"] == out["subject_bytes_rev_parse"])
    out["all_four_numbers_equal"] = bool(agree)
    out["verdict"] = "READBACK_CONCORDANT" if agree else "READBACK_DISCORDANT"
    io.open(os.path.join(ROOT, OUT), "w", encoding="utf-8", newline="\n").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print("verdict=%s local=%s ho=%s revparse=%s bytes=%s/%s commit=%s"
          % (out["verdict"], local_blob, local_ho, remote_blob, out["subject_bytes_local"],
             out["subject_bytes_rev_parse"], commit))
    return 0 if agree else 9


if __name__ == "__main__":
    sys.exit(main())
