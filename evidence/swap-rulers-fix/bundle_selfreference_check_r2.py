"""Check that every file the served preview bundle references EXISTS in a lane's snapshot dir.

r2 DELTA (found by running r1 against the live serve dir with no --look, 2026-09-25 08:1x): r1 printed
`checked=0` and still exited 0, and its JSON said `ALL_SELF_REFERENTIAL` -- a green computed over ZERO
roots examined.  r2 prints `roots_actually_measured`, and when that is 0 it writes
`NOT_MEASURED_NO_USABLE_LOOK_ROOTS` and exits 6.  The reading "nothing was measured" must never share an
exit code with "every root is self-referential".

Measured incident (ORD-0276, lane HJ-P3): a lane pointed its "private" surface at
`D:/moodle/_hjp3_fan_sweep_0923/snap_live_dist`, whose `index.html` was a HARD LINK into my served
`D:/moodle/_qoder_preview_20260920/dist/index.html` (same inode 1688849863486668, st_nlink=2).  When the
served generation was swapped at 05:14:35 the shared index started naming `index-CtuiCkKf.js`, a file the
snapshot's own `assets/` never received -> `200 + text/html` at a `.js` URL -> strict MIME check -> React
never mounts -> white page.

This ruler answers the OTHER half of that question, per directory, without a browser:
"if I serve THIS directory, does the file its index.html names exist inside THIS directory?"
A copy-only snapshot with both assets passes (negative control); a snapshot with a fresh index and stale
assets must be reported.  Read-only; writes nothing.

Usage: python bundle_selfreference_check_r1.py --serve <served dist> --look <snapshot dist>...
Exit 0 = every look root is self-referential, 3 = at least one dangling reference (white page waiting).
"""
import argparse
import hashlib
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REF = re.compile(r'(?:src|href)="(/[^"]+)"')


def sha1_of(path):
    data = open(path, "rb").read()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest(), len(data)


def index_refs(dist):
    idx = os.path.join(dist, "index.html")
    if not os.path.isfile(idx):
        return None, []
    raw = open(idx, encoding="utf-8", errors="replace").read()
    return idx, sorted(set(REF.findall(raw)))


def check_one(dist, served_refs=None, served_index=None):
    idx, refs = index_refs(dist)
    rows = {"dist": os.path.abspath(dist), "index_present": idx is not None, "refs": [], "dangling": []}
    for r in refs:
        local = os.path.normpath(os.path.join(dist, r.lstrip("/")))
        exists = os.path.isfile(local)
        row = {"ref": r, "exists_in_this_dir": exists}
        if exists and served_index and r in served_refs:
            # name-match is not byte-match: compare against the served copy of the same URL
            a = sha1_of(local)
            b = sha1_of(os.path.normpath(os.path.join(served_index, "..", r.lstrip("/"))))
            row["same_bytes_as_served"] = a[0] == b[0]
            row["blob_local"] = a[0]
        rows["refs"].append(row)
        if not exists:
            rows["dangling"].append(r)
    rows["verdict"] = "WHITE_PAGE_WAITING" if rows["dangling"] else "SELF_REFERENTIAL"
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", required=True)
    ap.add_argument("--look", action="append", default=[])
    ap.add_argument("--json")
    a = ap.parse_args()
    sidx, srefs = index_refs(a.serve)
    if sidx is None:
        print("SERVED index.html missing - nothing to compare against:", a.serve)
        return 5
    _, sb = sha1_of(sidx)
    print(f"serve={os.path.abspath(a.serve)}  index bytes={sb}  refs={len(srefs)} -> {', '.join(srefs)}")
    out, bad = [], 0
    for d in a.look:
        if not os.path.isdir(d):
            continue
        r = check_one(d, srefs, sidx)
        _, lb = (sha1_of(r["dist"] + os.sep + "index.html") if r["index_present"] else (None, 0))
        shared = (r["index_present"] and os.stat(os.path.join(r["dist"], "index.html")).st_ino
                  == os.stat(sidx).st_ino)
        r["index_shares_inode_with_served"] = bool(shared)
        r["index_bytes"] = lb
        print(f"\nlook={r['dist']}")
        for row in r["refs"]:
            extra = ""
            if "same_bytes_as_served" in row:
                extra = f" same_bytes_as_served={row['same_bytes_as_served']}"
            print("   %-38s exists=%s%s" % (row["ref"], row["exists_in_this_dir"], extra))
        print("   index_shares_inode_with_served=%s  dangling=%d  verdict=%s"
              % (r["index_shares_inode_with_served"], len(r["dangling"]), r["verdict"]))
        if r["dangling"]:
            bad += 1
        out.append(r)
    measured = [r for r in out if r["index_present"]]
    print(f"\nlook_roots_passed_in={len(a.look)} roots_actually_measured={len(measured)} white_page_waiting={bad}")
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"schema": "CNX_BUNDLE_SELFREFERENCE_CHECK_V1", "served_index_bytes": sb,
                       "served_refs": srefs, "roots": out,
                       "overall": ("NOT_MEASURED_NO_USABLE_LOOK_ROOTS" if not measured
                                   else ("SOME_ROOTS_ARE_NOT_SELF_REFERENTIAL" if bad else "ALL_SELF_REFERENTIAL")),
                       "roots_actually_measured": len(measured),
                       "scope": "Filesystem existence + byte equality only. No browser, no MIME assertion "
                                "about a running server; it proves the white page is WAITING, not that a "
                                "surface was observed white."},
                      fh, ensure_ascii=False, indent=1)
        print("wrote", a.json)
    if not measured:
        print("NOT_MEASURED: no --look root with a readable index.html -- this is NOT a pass. "
              "(r1 exited 0 here and printed ALL_SELF_REFERENTIAL over zero roots examined)")
        return 6
    return 3 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
