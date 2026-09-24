"""Find external HARD LINKS into a served dist directory - the mechanism behind a white page.

Measured incident (2026-09-25 05:14:35 -> 05:49): lane HJ-P3 keeps a "private" snapshot
`D:/moodle/_hjp3_fan_sweep_0923/snap_live_dist/` whose `index.html` shared inode
1688849863486668 (st_nlink=2) with the SERVED `D:/moodle/_qoder_preview_20260920/dist/index.html`.
A legitimate generation swap rewrote the served index (asset ChOTTCvB -> CtuiCkKf), and because the
snapshot's index was the SAME FILE, it started referencing an asset its own `assets/` dir never
received -> the surface answered `200 + text/html` at a `.js` URL -> strict MIME check -> React never
mounted -> white page.  The in-service retention rule (union old assets BEFORE switching index)
protected the served tree; it cannot protect a directory that hard-links into it.

So: before any swap, ask "does anything outside my dist point INTO my dist?".  Answer by inode, not
by name - a copy is invisible to this test and must stay invisible (that is the negative control).

Usage:
  python dist_hardlink_scan.py --serve <served dist dir> [--look <dir to inspect for twins>]...
  python dist_hardlink_scan.py --selftest
Exit 0 = CLEAN, 3 = EXTERNAL_HARDLINK_REFS (refuse the swap), 4 = selftest failure, 5 = usage error.
"""
import argparse
import hashlib
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCAN_SUFFIXES = (".html", ".js", ".css", ".json", ".webmanifest", ".svg", ".txt")


def dist_files(root):
    """(path, ino, nlink, size, blob-sha1) for every scannable file under root."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in sorted(filenames):
            if not fn.endswith(SCAN_SUFFIXES):
                continue
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
                data = open(p, "rb").read()
            except OSError:
                continue
            out.append({"path": os.path.abspath(p), "ino": st.st_ino, "nlink": st.st_nlink,
                        "size": len(data),
                        "sha1": hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()})
    return out


def scan(serve_root, look_roots):
    """Report every served file that has a twin outside serve_root sharing its inode."""
    served = dist_files(serve_root)
    served_root = os.path.abspath(serve_root)
    by_ino = {}
    for e in served:
        by_ino.setdefault(e["ino"], []).append(e)
    hits = []
    for lr in look_roots:
        if not os.path.isdir(lr):
            continue
        for e in dist_files(lr):
            if os.path.abspath(e["path"]).startswith(served_root + os.sep):
                continue                      # inside the served tree: its own business
            if e["nlink"] < 2:
                continue                      # a copy can never be a twin: negative control holds
            for s in by_ino.get(e["ino"], ()):
                if s["path"] != e["path"]:
                    hits.append({"served": s["path"], "external": e["path"], "ino": e["ino"],
                                 "nlink": e["nlink"], "served_size": s["size"],
                                 "external_size": e["size"], "same_bytes": s["sha1"] == e["sha1"]})
    # a served file whose own nlink > 1 but whose twin is not in look_roots is still a hazard:
    # we cannot name the twin, so say exactly that rather than calling it clean.
    unnamed = [{"served": s["path"], "ino": s["ino"], "nlink": s["nlink"]}
               for s in served if s["nlink"] > 1]
    unnamed = [u for u in unnamed if not any(h["served"] == u["served"] for h in hits)]
    return {"serve_root": served_root, "look_roots": [os.path.abspath(x) for x in look_roots],
            "served_files": len(served), "hits": hits, "unlinked_twins_unnamed": unnamed,
            "verdict": "EXTERNAL_HARDLINK_REFS" if (hits or unnamed) else "NO_EXTERNAL_HARDLINK_REFS"}


def selftest():
    """Two-way: a hard-linked twin MUST be found; a copied twin must NOT be (and a clean dir is clean).

    r1 shipped this selftest with two fixture bugs (found by running it: 3/5).  H3 reused the served
    tree that H1 had just hard-linked, so `unnamed` was legitimately non-empty and the "clean copy"
    expectation was measuring the wrong tree; H5 put its lonely file OUTSIDE the served dist, so the
    scan correctly never saw it.  Both are fixed by giving each arm its own tree instead of by
    loosening a judgement - the judge is unchanged from r1.
    """
    import shutil
    import tempfile
    results = []

    def check(name, ok, detail=""):
        results.append((name, bool(ok), detail))
        print(f"{'GREEN' if ok else 'RED  '}  {name}  {detail}")

    def make_serve(root):
        d = os.path.join(root, "dist")
        os.makedirs(os.path.join(d, "assets"), exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write('<html><script src="/assets/index-AAA.js"></script></html>\n')
        with open(os.path.join(d, "assets", "index-AAA.js"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("console.log(1)\n")
        return d

    tmp = tempfile.mkdtemp(prefix="cnx_hl_selftest_")
    try:
        # ---- arm 1: a hard-linked snapshot twin is a hit
        serve = make_serve(os.path.join(tmp, "arm1"))
        snap_hl = os.path.join(tmp, "laneA", "snap_hardlink")
        os.makedirs(os.path.join(snap_hl, "assets"), exist_ok=True)
        os.link(os.path.join(serve, "index.html"), os.path.join(snap_hl, "index.html"))
        os.link(os.path.join(serve, "assets", "index-AAA.js"), os.path.join(snap_hl, "assets", "index-AAA.js"))
        r_hit = scan(serve, [snap_hl])
        check("H1_hardlinked_twin_is_found",
              len(r_hit["hits"]) == 2 and any(h["external"].startswith(snap_hl) for h in r_hit["hits"]),
              f"hits={len(r_hit['hits'])} verdict={r_hit['verdict']}")
        check("H2_hardlink_hit_shares_inode_and_bytes",
              all(h["same_bytes"] and h["nlink"] >= 2 for h in r_hit["hits"]),
              "every hit must prove nlink>=2 and equal sha1")

        # ---- arm 2 (negative control): its OWN tree, nothing hard-linked anywhere
        serve_cp = make_serve(os.path.join(tmp, "arm2"))
        snap_cp = os.path.join(tmp, "laneB", "snap_copy")
        os.makedirs(os.path.join(snap_cp, "assets"), exist_ok=True)
        shutil.copy2(os.path.join(serve_cp, "index.html"), os.path.join(snap_cp, "index.html"))
        shutil.copy2(os.path.join(serve_cp, "assets", "index-AAA.js"), os.path.join(snap_cp, "assets", "index-AAA.js"))
        r_cp = scan(serve_cp, [snap_cp])
        check("H3_copied_twin_is_NOT_a_hit_negative_control",
              r_cp["verdict"] == "NO_EXTERNAL_HARDLINK_REFS" and not r_cp["hits"]
              and not r_cp["unlinked_twins_unnamed"],
              f"verdict={r_cp['verdict']} hits={len(r_cp['hits'])} unnamed={len(r_cp['unlinked_twins_unnamed'])}")

        # ---- arm 3: breaking the links must take the first tree clean (two-way again)
        os.remove(os.path.join(snap_hl, "index.html"))
        os.remove(os.path.join(snap_hl, "assets", "index-AAA.js"))
        r_after = scan(serve, [snap_hl, snap_cp])
        check("H4_after_unlinking_the_twin_the_scan_goes_clean",
              r_after["verdict"] == "NO_EXTERNAL_HARDLINK_REFS", f"verdict={r_after['verdict']}")

        # ---- arm 4: nlink>1 with a partner outside every --look root is refused, not clean
        lonely = os.path.join(serve, "lonely.json")          # INSIDE the served dist
        with open(lonely, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("{}\n")
        hidden = os.path.join(tmp, "hidden_partner.json")    # outside every look root
        os.link(lonely, hidden)
        r_un = scan(serve, [snap_cp])
        check("H5_nlink_gt1_with_unscanned_partner_is_refused_not_clean",
              r_un["verdict"] == "EXTERNAL_HARDLINK_REFS" and len(r_un["unlinked_twins_unnamed"]) == 1
              and r_un["unlinked_twins_unnamed"][0]["served"] == os.path.abspath(lonely),
              f"unnamed={len(r_un['unlinked_twins_unnamed'])} verdict={r_un['verdict']}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    green = sum(1 for _, ok, _ in results if ok)
    print(f"\nSELFTEST {green}/{len(results)} " + ("ALL_GREEN" if green == len(results) else "HAS_RED"))
    return 0 if green == len(results) else 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve")
    ap.add_argument("--look", action="append", default=[])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.serve or not os.path.isdir(a.serve):
        print("usage: --serve <dist dir> [--look <dir>]... | --selftest", file=sys.stderr)
        return 5
    r = scan(a.serve, a.look)
    print(f"serve_root={r['serve_root']}")
    print(f"served_files={r['served_files']}  look_roots={len(r['look_roots'])}  "
          f"hits={len(r['hits'])}  unnamed={len(r['unlinked_twins_unnamed'])}")
    for h in r["hits"]:
        print(f"  HARDLINK  served={h['served']}  <->  external={h['external']}")
        print(f"           ino={h['ino']} nlink={h['nlink']} same_bytes={h['same_bytes']}")
    for u in r["unlinked_twins_unnamed"]:
        print(f"  UNNAMED   served={u['served']} ino={u['ino']} nlink={u['nlink']} "
              f"(partner outside every --look root: cannot name it, so this is NOT clean)")
    print("VERDICT:", r["verdict"])
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            import json
            json.dump(r, fh, ensure_ascii=False, indent=1)
        print("wrote", a.json)
    return 3 if r["verdict"] == "EXTERNAL_HARDLINK_REFS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
