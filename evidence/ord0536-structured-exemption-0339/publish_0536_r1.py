# -*- coding: utf-8 -*-
"""Publish the ORD-0536 evidence, one append-only path each, with a per-file read-back.

What this set is: three `git archive` exports read by three generations of the same ruler family, the
selftest of the new generation, the three counterexamples each really run against a mutant copy, and the
instruments that made them.  The delivered byte change itself is one new file on the review branch and is
cited by commit, not copied here.
"""
import io
import json
import os
import re
import subprocess
import sys
import time

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0536"
REF = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
REPO = "D:/moodle/CityNexus"
MIR = os.path.join(REF, "cmdr_git_mirror_r1.py")
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")
STAMP = os.environ.get("CNX_PUBLISH_STAMP", "0339")
SLUG = "evidence/ord0536-structured-exemption-" + STAMP
MSG = ("S4-ast-taint ORD-0536: the exposure ruler's structured exemption revision (r8) measured against the "
       "two published generations on three export trees, its both-direction selftest, and three counterexamples "
       "that each really ran. 0 bytes of this is product code beyond the one ruler file on the review branch.")
FILES = [
    "generation_reconciliation_r1.json", "report_r1.txt", "door_view_r1.json",
    "counterexamples_r1.json", "st_r8_full.json", "rec_r8_tip_7862c6de.json",
    "rec_r8_cmdr_side_candidate.json", "rec_r7b_cmdr_side_candidate.json",
    "export_sizes_r1.json", "commit_msg_r1.txt",
    "reconcile_r1.py", "report_r1.py", "counterexamples_r1.py", "block_0536_r1.py",
    "bus_post_0536_r1.py", "publish_0536_r1.py",
]


def git(*args):
    r = subprocess.run(["git", "-C", REPO, "-c", "http.proxy=", "-c", "https.proxy="] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
                       env=ENV)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def blob_of(path):
    rc, out, err = git("hash-object", "-w", path.replace("\\", "/"))
    assert re.fullmatch(r"[0-9a-f]{40}", out), (path, out, err)
    return out


def put(name, slug):
    local = os.path.join(WORK, name)
    remote = slug + "/" + name
    row = {"path": remote, "bytes": os.path.getsize(local), "local_blob": blob_of(local)}
    rec = None
    for attempt in (1, 2, 3):
        r = subprocess.run([sys.executable, MIR, "--file", local, "--repo-path", remote,
                            "--branch", "commander/control", "--allow-identical", "--message", MSG],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=1800, env=ENV, cwd=REF)
        out = (r.stdout or "") + (r.stderr or "")
        rec = None
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                # the mirror prints exactly this record; the keys are named here rather than guessed at
                rec = json.loads(line)
        if r.returncode == 0 and rec and rec.get("byte_equal"):
            break
        row.setdefault("attempts", []).append({"attempt": attempt, "rc": r.returncode,
                                              "rec": rec, "tail": out.strip()[-240:]})
        time.sleep(3)
    row.update({"server_readback_blob": (rec or {}).get("readback_blob"),
                "server_readback_bytes": (rec or {}).get("readback_size"),
                "byte_equal": (rec or {}).get("byte_equal"),
                "tip_matches_push": (rec or {}).get("tip_matches_push"),
                "pushed_commit": (rec or {}).get("pushed_commit")})
    return row


def sibling_dir_check(slug, other):
    """The same bytes were dropped into an earlier dir this round; say whether they are the same blobs."""
    rows = []
    for n in FILES:
        base = blob_of(os.path.join(WORK, n))
        rc, out, err = git("ls-tree", "-r", "--name-only", "refs/remotes/verify/cc", other + "/" + n)
        present = bool(out.strip())
        if present:
            rc2, sha, _ = git("ls-tree", "refs/remotes/verify/cc", other + "/" + n)
            sha = sha.split()[2] if len(sha.split()) >= 3 else None
            rows.append({"path": other + "/" + n, "blob": sha, "same_bytes_as_here": sha == base})
        else:
            rows.append({"path": other + "/" + n, "present": False})
    return {"other_dir": other, "rows": rows,
            "all_same_blobs": all(r.get("same_bytes_as_here") for r in rows) if rows else None}


def main():
    rows = [put(n, SLUG) for n in FILES]
    receipt = {"slug": SLUG, "branch": "commander/control", "files": rows,
               "all_byte_equal": all(r["byte_equal"] for r in rows),
               "retried_paths": [r["path"].split("/")[-1] for r in rows if "attempts" in r]}
    io.open(os.path.join(WORK, "publish_receipt_r1.json"), "w", encoding="utf-8").write(
        json.dumps(receipt, ensure_ascii=False, indent=1))
    print(json.dumps(receipt, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
