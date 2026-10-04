# -*- coding: utf-8 -*-
"""One publisher for this lane, with the empty-denominator floor built into the write door.

Why: tonight's static scan of my own writers found 56 entries on the write path where a verdict can pass on an
empty collection, and the live counter-example proved the worst one - a publisher run with an empty file list
returned rc 0 with `new_equal: []` and `all_local_byte_equal: true`, i.e. it called "nothing was published" a
success. The old publishers were hand-copied, so the hole was copied with them. This is the single replacement:
new hands pass a manifest and cannot ask for zero files, cannot skip a missing file, and cannot claim equality
over an empty shelf.

Guards, each one armed (see `publisher_fix_proof_r1.py`):
  EMPTY_MANIFEST   no files requested -> refuse rc 5
  MISSING_FILE   a named file is not on disk -> refuse rc 6, naming it
  NOTHING_ON_SHELF   the slug enumerates zero rows after the run -> refuse rc 7
  BYTE_MISMATCH   server's blob != local blob for any shelf path -> refuse rc 7 (never "assumed equal")

Behaviour kept from the old publishers: only absent paths are written (a published name is never overwritten),
the push goes through the guarded mirror, and after it the branch is re-fetched and every file re-hashed with the
git blob header, so equality is computed against the server's listing.

    python lane_publisher_r1.py --manifest manifest.json          # writes receipts
    python lane_publisher_r1.py --slug evidence/... --files a.py,b.json --message "..." --dry-run
"""
import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import time

REPO = "D:/moodle/CityNexus"
MIR = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\cmdr_git_mirror_r1.py"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")
for _k in ("http_proxy", "https_proxy"):
    ENV[_k] = ""
RC_OK, RC_EMPTY, RC_MISSING, RC_MISMATCH = 0, 5, 6, 7


def blob_of(raw):
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def git(*a):
    r = subprocess.run(["git", "-C", REPO, "-c", "http.proxy=", "-c", "https.proxy="] + list(a),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=1800, env=ENV)
    return r.returncode, (r.stdout or "").strip()


def decide(files, rows, shelf, stage="post"):
    """The verdict function, separated so the arms can drive it without touching any remote.

    `pre` runs before anything is written and can only know two things (nothing asked, a file missing);
    `post` adds the two facts that only exist after a run (the shelf is empty, the bytes disagree). Folding the
    post-stage guards into the pre-check was my first version's own bug: it made every manifest abort as
    NOTHING_ON_SHELF before a single write, so the door could never publish anything - and the arms missed it
    because they tested this function directly instead of the call site. Hence `--dry-run` below.
    """
    refusals = []
    if not files:
        refusals.append({"code": "EMPTY_MANIFEST", "detail": "no files were asked to publish - that is not a pass"})
    for f in files:
        if not os.path.exists(f):
            refusals.append({"code": "MISSING_FILE", "detail": "not on disk: %s" % f})
    if stage == "post":
        if not shelf:
            refusals.append({"code": "NOTHING_ON_SHELF", "detail": "the slug lists no rows after the run"})
        unequal = [s for s in shelf if s["byte_equal"] is False]
        if unequal:
            refusals.append({"code": "BYTE_MISMATCH", "detail": json.dumps([u["path"] for u in unequal])[:200]})
    skipped = [r for r in rows if r.get("refused")]
    code = RC_OK if not refusals else (RC_EMPTY if any(r["code"] == "EMPTY_MANIFEST" for r in refusals) else
                                       RC_MISSING if any(r["code"] == "MISSING_FILE" for r in refusals) else
                                       RC_MISMATCH)
    return {"exit_code": code, "refusals": refusals, "published": len(rows) - len(skipped),
            "already_there": len(skipped), "shelf_rows": len(shelf)}


def publish(work, slug, files, message, verify_ref, out="", dry=False):
    files = [f for f in files if f.strip()]
    pre = decide(files, [], [], stage="pre")
    if pre["exit_code"] != RC_OK:
        print(json.dumps({"aborted_before_any_write": pre}, ensure_ascii=False))
        return pre["exit_code"]
    if dry:
        print(json.dumps({"dry_run": "the pre-check passed, so the door would write", "files": len(files),
                          "would_publish": [os.path.basename(f) for f in files]}, ensure_ascii=False))
        return RC_OK
    rows = []
    for name in files:
        remote = slug + "/" + name
        raw = io.open(os.path.join(work, name), "rb").read()
        want = blob_of(raw)
        git("fetch", "-q", "origin", "+refs/heads/commander/control:" + verify_ref)
        rc, listing = git("ls-tree", verify_ref, remote)
        if listing and listing.split()[2] == want:
            rows.append({"path": remote, "bytes": len(raw), "byte_equal": True, "refused": "already there, same bytes"})
            continue
        rec = None
        for _try in (1, 2, 3):
            r = subprocess.run([sys.executable, MIR, "--file", os.path.join(work, name), "--repo-path", remote,
                                "--branch", "commander/control", "--allow-identical", "--message", message],
                               capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=1800, env=ENV, cwd=os.path.dirname(MIR))
            for line in ((r.stdout or "") + (r.stderr or "")).splitlines():
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    rec = json.loads(line)
            if r.returncode == 0 and rec and rec.get("byte_equal"):
                break
            time.sleep(3)
        git("fetch", "-q", "origin", "+refs/heads/commander/control:" + verify_ref)
        rc, listing = git("ls-tree", "-r", verify_ref, remote)
        got = listing.split()[2] if listing else None
        rows.append({"path": remote, "bytes": len(raw), "server_blob_ls_tree": got, "byte_equal": got == want})
    git("fetch", "-q", "origin", "+refs/heads/commander/control:" + verify_ref)
    rc, listing = git("ls-tree", "-r", verify_ref, slug + "/")
    shelf = []
    for line in listing.splitlines():
        if not line.strip():
            continue
        _m, typ, b, path = line.split(None, 3)
        if typ != "blob":
            continue
        lp = os.path.join(work, path.rsplit("/", 1)[-1])
        shelf.append({"path": path, "server_blob_ls_tree": b,
                      "byte_equal": blob_of(io.open(lp, "rb").read()) == b if os.path.exists(lp) else None})
    v = decide(files, rows, shelf)
    doc = {"slug": slug, "control_tip_after": git("rev-parse", verify_ref)[1], "files": shelf,
           "this_run": rows, "verdict": v, "generated_at_local": time.strftime("%Y-%m-%d %H:%M:%S")}
    if out:
        io.open(out, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"exit_code": v["exit_code"], "published": v["published"], "already_there": v["already_there"],
                      "shelf_rows": v["shelf_rows"], "refusals": v["refusals"]}, ensure_ascii=False))
    return v["exit_code"]


def main():
    ap = argparse.ArgumentParser(prog="lane_publisher_r2.py")
    ap.add_argument("--manifest", default="")
    ap.add_argument("--work", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--slug", default="")
    ap.add_argument("--files", default="")
    ap.add_argument("--message", default="")
    ap.add_argument("--verify-ref", default="refs/remotes/verify/lane_publisher")
    ap.add_argument("--out", default="")
    ap.add_argument("--decide-only", action="store_true", help="run the verdict function on empty/partial input")
    ap.add_argument("--dry-run", action="store_true", help="run the door up to, but not including, any write")
    a = ap.parse_args()
    if a.decide_only:
        real = os.path.basename(__file__)      # must exist, or the missing-file guard fires first and the
        print(json.dumps({"empty": decide([], [], [], stage="pre"),               # empty-shelf arm proves nothing
                          "missing": decide(["definitely-not-here.py"], [], [{"path": "x", "byte_equal": True}],
                                            stage="post"),
                          "empty_shelf": decide([real], [], [], stage="post"),
                          "valid_manifest_pre": decide([real], [], [], stage="pre")}, ensure_ascii=False))
        return 0
    man = json.load(io.open(a.manifest, encoding="utf-8")) if a.manifest else {}
    slug = a.slug or man.get("slug", "")
    files = [f.strip() for f in a.files.split(",") if f.strip()] or man.get("files", [])
    msg = a.message or man.get("message", "")
    out = a.out or man.get("receipt", "")
    return publish(a.work, slug, files, msg, a.verify_ref, out, dry=a.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
