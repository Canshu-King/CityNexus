"""Construct the NEXT generation at the artifact layer, for the ORD-0274 convergence measurement.

A comment cannot do it (esbuild strips comments, so the bundle hash stayed identical) and changing product
code to make a test artifact would defeat the test. What a real deploy changes, viewed by the worker, is
the asset graph: the module filename and the precache manifest entry. So I copy gen1 and rewrite exactly
those - same bytes inside, different name - which is the minimum difference that makes "a new generation
arrived" observable to the browser.

This file fabricates nothing about the RESULT: it only prepares a second generation. Whether the open
document converges is still measured by the probe, on a real browser, against a real swap.
"""
from __future__ import annotations

import pathlib
import re
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FRONT = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend")
SRC = FRONT / "dist_0274sw"
DST = FRONT / "dist_0274sw_gen2"
FAKE = "index-0274gen2"


def module_name(root: pathlib.Path):
    html = (root / "index.html").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"/assets/(index-[A-Za-z0-9_-]+)\.js", html)
    return m.group(1) if m else None


def main() -> int:
    if not SRC.is_dir():
        raise SystemExit(f"ABORT: no gen1 dist at {SRC}")
    old = module_name(SRC)
    if not old:
        raise SystemExit("ABORT: cannot find the module name in gen1's index.html")
    shutil.rmtree(DST, ignore_errors=True)
    shutil.copytree(SRC, DST)
    changed = []
    for p in sorted(DST.rglob("*")):
        if not p.is_file() or p.suffix not in (".html", ".js", ".webmanifest", ".css"):
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        if old in t:
            p.write_text(t.replace(old, FAKE), encoding="utf-8", newline="\n")
            changed.append(p.relative_to(DST).as_posix())
    (DST / "assets" / f"{old}.js").rename(DST / "assets" / f"{FAKE}.js")
    # A real deploy also rewrites index.html, and Workbox skips re-downloading an entry whose hand-written
    # revision is unchanged - leaving it alone would make the "new" worker keep serving the old shell,
    # which is my artifact's bug and not a product finding.
    sw = DST / "v10-sw.js"
    t = sw.read_text(encoding="utf-8", errors="replace")
    rotated = []

    def bump(m):
        url, rev = m.group(1), m.group(2)
        if url in ("index.html",) or url.endswith(".html"):
            rotated.append({"url": url, "from": rev, "to": FAKE[:16]})
            return '{url:"%s",revision:"%s"}' % (url, FAKE[:16])
        return m.group(0)

    t2 = re.sub(r'\{url:"([^"]+)",revision:"([0-9a-f]{8,})"\}', bump, t)
    sw.write_text(t2, encoding="utf-8", newline="\n")
    print("revisions rotated:", rotated)
    new = module_name(DST)
    print("gen1 module:", old)
    print("gen2 module:", new)
    print("references rewritten in:", changed)
    print("bytes inside identical apart from the name:",
          (DST / "assets" / f"{FAKE}.js").read_bytes() == (SRC / "assets" / f"{old}.js").read_bytes())
    return 0 if new == FAKE else 1


if __name__ == "__main__":
    raise SystemExit(main())
