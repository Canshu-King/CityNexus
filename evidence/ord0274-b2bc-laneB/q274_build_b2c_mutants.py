"""Build the two B2c counter-arm generations, then restore the source byte-exactly.

B2c's contract has two halves, and each needs an arm that is FORBIDDEN to pass:

  eager  - "write in flight, reload anyway" (the shape before this candidate's guard): reloads the document
           while a non-idempotent request is still open, which is the 腰斩 the criterion names.
  manual - "wait for the quiet point, then make the traveller navigate again": marks the handover pending
           and never reloads on its own.  A deferral that costs the user a navigation is the other way to
           fail the same sentence.

Each mutant is only an arm if its BYTES actually moved: the Q20 judge compares `content_fingerprint`
against the candidate build, and an identical fingerprint means my patch was a no-op and the arm proves
nothing (that trap bit the first version of this lane's gen2 build, which shipped a comment).
Source is restored in a finally block and re-hashed; the run refuses to report anything while
`frontend/src` is dirty.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
SRC = LANE / "frontend" / "src" / "main.tsx"
CAND = LANE / "frontend" / "dist_0274sw"

GUARD_BLOCK = '''    if (hasNonIdempotentRequestInFlight()) {
      sessionStorage.setItem(serviceWorkerPendingHandoverKey, "pending");
      window.dispatchEvent(new CustomEvent("citynexus:generation-handover-pending"));
    }
    onNonIdempotentRequestsQuiet(() => {
      sessionStorage.removeItem(serviceWorkerPendingHandoverKey);
      window.location.reload();
    });
'''
MUTANTS = {
    "dist_0274b2c_eager": (GUARD_BLOCK, '''    /* COUNTER-ARM eager: reload the instant a new worker takes control, whatever is in flight. */
    window.location.reload();
'''),
    "dist_0274b2c_manual": (GUARD_BLOCK, '''    /* COUNTER-ARM manual: name the pending handover, but never converge on its own. */
    sessionStorage.setItem(serviceWorkerPendingHandoverKey, "pending");
    window.dispatchEvent(new CustomEvent("citynexus:generation-handover-pending"));
'''),
}



# `vite build` reads the working tree, so these builders refuse a dirty src: someone else's uncommitted code
# must never end up inside a bundle I claim to have measured.  While this lane's own fix is still
# uncommitted, the operator names the exact path(s) allowed to be dirty and the builder asserts the dirty
# set is a subset of that - it does not switch the guard off.
ALLOWED_DIRTY = {p.strip() for p in os.environ.get("CNX_ALLOW_DIRTY", "").split(",") if p.strip()}


def dirty_violation(state: str) -> str | None:
    paths = {ln.split(None, 1)[1].strip() for ln in state.splitlines() if ln.strip()}
    if not paths:
        return None
    if paths <= ALLOWED_DIRTY:
        return None
    return f"dirty={sorted(paths)} allowed={sorted(ALLOWED_DIRTY)}"


def dirty() -> str:
    r = subprocess.run(["git", "status", "--porcelain", "frontend/src"], cwd=str(LANE),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "").strip()


def build(out_dir: str) -> dict:
    b = subprocess.run(["node", "node_modules/vite/bin/vite.js", "build", "--outDir", out_dir],
                       cwd=str(LANE / "frontend"), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    return {"rc": b.returncode,
            "tail": [ln for ln in (b.stdout or b.stderr).splitlines() if ln.strip()][-2:]}


def main() -> int:
    sys.path.insert(0, str(SPIKE))
    import q274_gen_identity as ident
    bad = dirty_violation(dirty())
    if bad:
        print("ABORT: the working tree is dirtier than what this run is allowed to build:", bad)
        return 2
    original = SRC.read_bytes()
    base_text = original.decode("utf-8")
    if GUARD_BLOCK not in base_text:
        raise SystemExit("ABORT: the B2c guard block is not present verbatim - refusing to patch blind")
    cand = ident.disk_identity("candidate", CAND)
    ident.refuse_if_unusable(cand, "candidate host")
    results = {}
    try:
        for name, (needle, repl) in MUTANTS.items():
            patched = base_text.replace(needle, repl, 1)
            if patched == base_text:
                raise SystemExit(f"ABORT: mutant {name} would not change anything")
            SRC.write_text(patched, encoding="utf-8", newline="\n")
            results[name] = build(name)
            print(f"  built {name}: {results[name]}")
    finally:
        SRC.write_bytes(original)
    restored = hashlib.sha256(SRC.read_bytes()).hexdigest() == hashlib.sha256(original).hexdigest()
    print("restored byte-exact:", restored, "| src dirty now:", repr(dirty()))
    ok = restored and not dirty_violation(dirty()) and all(r["rc"] == 0 for r in results.values())
    for name in MUTANTS:
        d = LANE / "frontend" / name
        if not d.is_dir():
            print(f"  {name}: NO DIST")
            ok = False
            continue
        g = ident.disk_identity(name, d)
        moved = g["content_fingerprint"] != cand["content_fingerprint"]
        print(f'  {name:22s} verdict={g["generation_verdict"]} bytes_moved_vs_candidate={moved} '
              f'content={g["content_fingerprint"][:12]} entry={list(g["per_script"])}')
        if g["generation_verdict"] != "GREEN" or not moved:
            ok = False
    print("verdict:", "COUNTER_ARMS_BUILT" if ok else "COUNTER_ARMS_NOT_USABLE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
