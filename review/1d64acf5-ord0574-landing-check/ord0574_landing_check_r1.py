# -*- coding: utf-8 -*-
"""ORD-0574 landing check: are the r2 candidates on the authoritative line, and is anyone running them?

Read-only: it reads the tree at the tip and the hook's own trail file, then publishes the readings.
It does not edit the trail, the tools, or any ref on the authoritative line.
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
MAIN = r"D:\moodle\CityNexus"
HERE = os.path.dirname(os.path.abspath(__file__))
TRAIL = r"D:\moodle\_mirror_sync\trail.jsonl"
REF = "review/1d64acf5-ord0574-landing-check-r1"
PREFIX = "review/1d64acf5-ord0574-landing-check/"
FILES = ["ord0574_landing_check_r1.py", "beat_trail_read_r1.txt", "landing_check_flat_r1.tsv"]

WANT = {
    "tools/cnx_ledger_mirror_sync_check_r2.py": "3c5040a4fa9b4656cf1caed4665fb927bcac6e70",
    "tools/cnx_ledger_mirror_sync_hook_r2.py": "c3a5f51f117d54539bfa757ddc96281955334424",
    "tools/cnx_ledger_mirror_sync_check_r1.py": "5d0ca99076de5c11e9906acadc9c03ed1a3b8e6e",
    "tools/cnx_ledger_mirror_sync_hook_r1.py": "18f51ebc995a1a496a5b6b5d7947d73f9ba818d3",
}


def clean_env():
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        e.pop(k, None)
    e["GIT_TERMINAL_PROMPT"] = "0"
    return e


def git(repo, *a, **kw):
    p = subprocess.run(["git", "-C", repo] + list(a), capture_output=True, env=clean_env(),
                       timeout=kw.get("timeout", 900))
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def git_blob(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main():
    R = {}
    rc, out, err = git(MAIN, "ls-remote", "--refs", "origin",
                       "refs/heads/mirror/integration-frontend-apple-pass1")
    tip = out.split()[0]
    R["tip"] = tip
    frc, fout, ferr = git(MAIN, "fetch", "-q", "origin", "mirror/integration-frontend-apple-pass1")
    R["fetch_rc"] = frc

    present = {}
    for path, want in WANT.items():
        rc, out, err = git(MAIN, "ls-tree", tip, "--", path)
        fields = out.split()
        got = fields[2] if len(fields) >= 3 else None
        present[path] = {"want": want, "got": got, "matches": got == want,
                         "cat_file_type": git(MAIN, "cat-file", "-t", got)[1].strip() if got else None}
    R["present"] = present
    if not all(v["matches"] for v in present.values()):
        raise SystemExit("ABORT: at least one published blob is not the one on the line")

    # is the cadence running anything, and which generation?  The trail is the observable.
    if not os.path.exists(TRAIL):
        raise SystemExit("ABORT: no trail file - I would be guessing about the beat")
    rows = [json.loads(l) for l in io.open(TRAIL, encoding="utf-8").read().splitlines() if l.strip()]
    R["trail_lines"] = len(rows)
    R["trail_last_at"] = rows[-1].get("at")
    R["trail_last_tool"] = rows[-1].get("tool")
    R["trail_last_hook"] = rows[-1].get("hook")
    R["trail_tools_seen"] = sorted({r.get("tool") for r in rows})
    R["trail_hooks_seen"] = sorted({r.get("hook") for r in rows})
    txt = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
    io.open(os.path.join(HERE, "beat_trail_read_r1.txt"), "w", encoding="utf-8", newline="\n").write(txt)
    R["trail_copied_bytes"] = len(txt.encode("utf-8"))
    R["r2_ever_named_in_trail"] = any("r2" in (r.get("tool") or "") for r in rows)

    rc, out, err = git(WT, "ls-remote", "--refs", "origin", "refs/heads/" + REF)
    if out.strip():
        raise SystemExit("ref exists; refusing to move a published ref")
    rows_flat = []
    rows_flat.append(("tip", tip))
    for path in sorted(WANT):
        rows_flat.append(("on_line_" + path.split("/")[-1], present[path]["got"]))
    rows_flat.append(("trail_lines", R["trail_lines"]))
    rows_flat.append(("trail_last_at", R["trail_last_at"]))
    rows_flat.append(("trail_last_tool", R["trail_last_tool"]))
    rows_flat.append(("trail_last_hook", R["trail_last_hook"]))
    rows_flat.append(("trail_tools_seen", "|".join(R["trail_tools_seen"])))
    rows_flat.append(("trail_hooks_seen", "|".join(R["trail_hooks_seen"])))
    rows_flat.append(("r2_ever_named_in_trail", R["r2_ever_named_in_trail"]))
    flat = os.path.join(HERE, "landing_check_flat_r1.tsv")
    with io.open(flat, "w", encoding="utf-8", newline="\n") as fh:
        for i, (k, v) in enumerate(rows_flat, start=1):
            fh.write("%d\t%s\t%s\n" % (i, k, v))

    blobs = []
    for f in FILES:
        p_ = os.path.join(HERE, f)
        if not os.path.isfile(p_):
            raise SystemExit("ABORT: %s missing" % f)
        data = io.open(p_, "rb").read()
        pr = subprocess.run(["git", "-C", WT, "hash-object", "-w", "--stdin"], input=data,
                            capture_output=True, env=clean_env(), timeout=300)
        blobs.append({"file": f, "bytes": len(data), "git_blob": pr.stdout.decode().strip()})
    R["blobs"] = blobs

    fd, idx = tempfile.mkstemp(prefix="s4land_")
    os.close(fd)
    env = clean_env()
    env["GIT_INDEX_FILE"] = idx
    try:
        steps = [["read-tree", tip]] + [["update-index", "--add", "--cacheinfo",
                                         "100644,%s,%s" % (b["git_blob"], PREFIX + b["file"])] for b in blobs]
        for args in steps:
            pr = subprocess.run(["git", "-C", WT] + args, capture_output=True, env=env, timeout=300)
            if pr.returncode:
                raise SystemExit("plumbing %s rc %d" % (args[0], pr.returncode))
        tree = subprocess.run(["git", "-C", WT, "write-tree"], capture_output=True, env=env,
                              timeout=300).stdout.decode().strip()
        sha = subprocess.run(["git", "-C", WT, "commit-tree", tree, "-p", tip, "-m",
                              "ORD-0574 landing check: both r2 blobs are on the line byte-equal and the r1 "
                              "blobs are untouched; the beat trail is copied verbatim as the evidence of who "
                              "is actually being run\n"], capture_output=True, env=env,
                             timeout=300).stdout.decode().strip()
        R["tree"], R["commit"] = tree, sha
    finally:
        os.unlink(idx)
    rc, a, err = git(WT, "ls-tree", "-r", "--name-only", tip)
    rc2, b, err = git(WT, "ls-tree", "-r", "--name-only", sha)
    sa, sb = set(a.splitlines()), set(b.splitlines())
    R["tip_entries"], R["commit_entries"] = len(sa), len(sb)
    R["added"], R["deleted"] = sorted(sb - sa), sorted(sa - sb)
    if R["deleted"]:
        raise SystemExit("ABORT: deletes paths")

    prc, pout, perr = git(WT, "push", "origin", "%s:refs/heads/%s" % (sha, REF), timeout=900)
    R["push_rc"] = prc
    if prc != 0:
        raise SystemExit("ABORT: push rc %d" % prc)
    rc, out, err = git(WT, "ls-remote", "--refs", "origin", "refs/heads/" + REF)
    R["readback"] = out.strip()
    if sha not in out:
        raise SystemExit("ABORT: readback mismatch")
    frc2, f2, fe = git(MAIN, "fetch", "--depth=1", "origin",
                       "+refs/heads/%s:refs/s4probe/ord0574_landing" % REF, timeout=900)
    R["resolvable"] = [{"obj": o, "t": git(MAIN, "cat-file", "-t", o)[1].strip()}
                       for o in [x["git_blob"] for x in blobs] + [sha, tree, tip]]
    bad = [x for x in R["resolvable"] if x["t"] not in ("blob", "commit", "tree")]
    if bad:
        raise SystemExit("ABORT: not cat-file-able %s" % json.dumps(bad))

    io.open(os.path.join(HERE, "ord0574_landing_check_r1.json"), "w", encoding="utf-8",
            newline="\n").write(json.dumps(R, ensure_ascii=False, indent=1))
    print(json.dumps({k: R[k] for k in ("tip", "commit", "tree", "push_rc", "readback",
                                        "trail_lines", "trail_last_at", "trail_last_tool",
                                        "trail_last_hook", "r2_ever_named_in_trail",
                                        "added", "deleted")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
