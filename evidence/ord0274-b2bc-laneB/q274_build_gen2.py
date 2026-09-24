"""Build a byte-different NEXT generation that carries no behavioural change, then restore the source.

The measurement I need is three generations deep: a client already running the fixed code, facing a new
generation.

First version of this file inserted a COMMENT line and the result was a rename-only pair: esbuild strips
comments, so gen1 and gen2 shipped the SAME entry bytes under different names. The Q20 byte judge caught it
(`content_fingerprint` equal), which is precisely the failure Q20 was written to prevent.  So the marker is
now a real statement that survives minification and touches no product behaviour: it writes a tag onto
`window`, which the product never reads, and which the probe can read back as "which generation is actually
executing" without consulting a filename.

The source is restored in a finally-block and verified byte-for-byte, and the restored state is printed
before anything else is reported, so a crash here cannot leave the lane dirty.  The build only counts as a
generation if the Q20 judge says its bytes moved; a name change is not accepted.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
SRC = LANE / "frontend" / "src" / "main.tsx"
GEN1 = LANE / "frontend" / "dist_0274sw"
GEN2 = LANE / "frontend" / "dist_0274gen2b"
ANCHOR = "const MAX_AUTOMATIC_CONVERGENCE_PER_SESSION = 2;"
MARKER = '\nwindow.__cnxGenerationTag = "gen2-standin";\n'


# `vite build` reads the working tree, so this builder refuses a dirty src: someone else's uncommitted code
# must never end up inside a bundle I claim to have measured.  While this lane's own fix is still
# uncommitted, the operator names the exact path(s) allowed to be dirty and the builder asserts the dirty
# set is a subset of that - it does not switch the guard off.
ALLOWED_DIRTY = {q.strip() for q in os.environ.get("CNX_ALLOW_DIRTY", "").split(",") if q.strip()}


def dirty_violation(state: str) -> str | None:
    paths = {ln.split(None, 1)[1].strip() for ln in state.splitlines() if ln.strip()}
    if not paths or paths <= ALLOWED_DIRTY:
        return None
    return f"dirty={sorted(paths)} allowed={sorted(ALLOWED_DIRTY)}"


def src_dirty_state() -> str:
    r = subprocess.run(["git", "status", "--porcelain", "frontend/src"], cwd=str(LANE),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "").strip()


def main() -> int:
    # `vite build` reads the working tree, so a dirty src here would put someone else's code in my bundle.
    bad = dirty_violation(src_dirty_state())
    if bad:
        print("ABORT: the working tree is dirtier than what this run is allowed to build:", bad)
        return 2
    before = hashlib.sha256(SRC.read_bytes()).hexdigest()
    text = SRC.read_text(encoding="utf-8")
    if ANCHOR not in text:
        raise SystemExit("ABORT: anchor constant missing - refusing to edit blind")
    built = None
    try:
        SRC.write_text(text.replace(ANCHOR, ANCHOR + MARKER, 1), encoding="utf-8", newline="\n")
        b = subprocess.run(["node", "node_modules/vite/bin/vite.js", "build", "--outDir", GEN2.name],
                           cwd=str(LANE / "frontend"), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=900)
        built = {"rc": b.returncode,
                 "tail": [ln for ln in (b.stdout or b.stderr).splitlines() if ln.strip()][-3:]}
    finally:
        SRC.write_text(text, encoding="utf-8", newline="\n")
    after = hashlib.sha256(SRC.read_bytes()).hexdigest()
    dirty = src_dirty_state()
    print("restored byte-exact:", after == before, "| frontend/src still dirty:", repr(dirty))
    print("build:", built)
    if not (after == before and built and built["rc"] == 0):
        return 1

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import q274_gen_identity as ident
    g1 = ident.disk_identity("gen1-candidate", GEN1)
    g2 = ident.disk_identity("gen2-standin", GEN2)
    for g in (g1, g2):
        ident.refuse_if_unusable(g, "generation host for the swap arm")
    print(f'  gen1 scripts={list(g1["per_script"])} '
          f'content={g1["content_fingerprint"][:16]} sw={g1["sw_bytes"] and g1["sw_bytes"]["sha256"][:12]}')
    print(f'  gen2 scripts={list(g2["per_script"])} '
          f'content={g2["content_fingerprint"][:16]} sw={g2["sw_bytes"] and g2["sw_bytes"]["sha256"][:12]}')
    moved = g1["content_fingerprint"] != g2["content_fingerprint"]
    print("  bytes moved (not just renamed):", moved)
    marker_in = {r: ("gen2-standin" in (GEN2 / r.lstrip("/")).read_text(encoding="utf-8", errors="replace"))
                 for r in g2["per_script"]}
    print("  marker statement survived minification:", marker_in)
    return 0 if (moved and any(marker_in.values())) else 1


if __name__ == "__main__":
    raise SystemExit(main())
