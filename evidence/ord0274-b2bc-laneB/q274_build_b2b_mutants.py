"""Build the two B2b counter-arm generations AS SWAP TARGETS, one variable each, then restore the source.

B2b's sentence is "reload 后 step 与逐值都回来".  The code that RESTORES the trip is the code the document
lands on, i.e. the incoming generation - so the mutant has to be the swap TARGET.  The first version of this
file built them as clients and the judge read MET on both: the healthy incoming generation restored the draft
perfectly and the mutation never ran on the path being judged.  (The B2c arms are the opposite: the handover
DECISION is made by the leaving document, so those mutants stay clients.)

Its two forbidden shapes, named by the commander:

  step_only    only the step survives, the values do not -> the fields fall back to defaults.
               RED because a restored step over empty inputs is half a record.
  step_forced  the values survive but the screen is forced back to step 1.
               RED because the traveller loses their place while keeping their words.

Every target also carries a `window.__cnxGenerationTag` statement so the probe can tell, from the bytes that
actually executed, that it landed in THIS generation - and each mutant is patched from the pristine in-memory
bytes and restored in its own `finally`, because the first version re-read the file inside the loop and the
second mutant inherited the first one's cut (both arms then shipped the same compound cut and returned
byte-for-byte identical readings).  `shipped_shape` reads the built bundle, not my intention.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
CAND = LANE / "frontend" / "dist_0274sw"
SETUP = LANE / "frontend" / "src" / "features" / "setup" / "JourneyTrialSetup.tsx"
MAIN = LANE / "frontend" / "src" / "main.tsx"

MAIN_ANCHOR = "const MAX_AUTOMATIC_CONVERGENCE_PER_SESSION = 2;"
WRITE_BLOCK = '''function writeStoredTrial(step: number, draft: unknown): void {
  try {
    localStorage.setItem(TRIAL_DRAFT_KEY, JSON.stringify({ step, draft }));'''
READ_LINE = '''    const step = parsed.step === 2 || parsed.step === 3 ? parsed.step : 1;
    /* Accept a stored value only when it has the same shape as the default it replaces.'''

# arm -> (patches, shape that MUST be visible in the shipped bytes, generation tag it advertises)
MUTANTS = {
    "dist_0274b2b_steponly_t": {
        "tag": "b2b-steponly",
        "patches": [
            (MAIN, MAIN_ANCHOR, MAIN_ANCHOR + '\nwindow.__cnxGenerationTag = "b2b-steponly";\n'),
            (SETUP, WRITE_BLOCK,
             '''function writeStoredTrial(step: number, draft: unknown): void {
  try {
    /* COUNTER-ARM step_only: persist the step and drop the values. */
    localStorage.setItem(TRIAL_DRAFT_KEY, JSON.stringify({ step }));'''),
        ],
        "shape": {"write_drops_draft": True, "write_keeps_pair": False, "read_ternary_intact": True},
    },
    "dist_0274b2b_stepforced_t": {
        "tag": "b2b-stepforced",
        "patches": [
            (MAIN, MAIN_ANCHOR, MAIN_ANCHOR + '\nwindow.__cnxGenerationTag = "b2b-stepforced";\n'),
            (SETUP, READ_LINE,
             '''    const step = 1 as const;
    /* COUNTER-ARM step_forced: the values come back, the place in the wizard does not. */
    /* Accept a stored value only when it has the same shape as the default it replaces.'''),
        ],
        "shape": {"write_drops_draft": False, "write_keeps_pair": True, "read_ternary_intact": False},
    },
}

# `vite build` reads the working tree, so this builder refuses a dirty src: someone else's uncommitted code
# must never end up inside a bundle I claim to have measured.  While this lane's own fix is still uncommitted,
# the operator names the exact path(s) allowed to be dirty and the builder asserts the dirty set is a subset
# of that - it does not switch the guard off.
ALLOWED_DIRTY = {q.strip() for q in os.environ.get("CNX_ALLOW_DIRTY", "").split(",") if q.strip()}


def dirty_violation(state: str) -> str | None:
    paths = {ln.split(None, 1)[1].strip() for ln in state.splitlines() if ln.strip()}
    if not paths or paths <= ALLOWED_DIRTY:
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


def shipped_shape(name: str, tag: str) -> dict:
    """What the built bundle carries: does the writer keep the {step, draft} pair, does the reader keep the
    `parsed.step === 2 || 3` ternary, and is this generation's own tag inside the executed bytes?
    """
    files = sorted((LANE / "frontend" / name / "assets").glob("index-*.js"))
    if not files:
        return {"error": "no entry bundle"}
    raw = files[0].read_bytes()
    t = raw.decode("utf-8", "replace")
    writes = [m.group(1) for m in re.finditer(
        r"""localStorage\.setItem\([\w$]+,\s*JSON\.stringify\(\{([^)]*?)\}\)""", t)]
    pair = [w for w in writes if "draft" in w and "step" in w]
    drop = [w for w in writes if "step" in w and "draft" not in w]
    return {"bundle": files[0].name, "bundle_sha256": hashlib.sha256(raw).hexdigest(),
            "draft_writes_found": len(writes),
            "write_keeps_pair": bool(pair), "write_drops_draft": bool(drop) and not pair,
            "read_ternary_intact": bool(re.search(r"\.step===2\|\|\s*[\w$]+\.step===3", t)),
            "advertises_tag": f'"{tag}"' in t}


def main() -> int:
    sys.path.insert(0, str(SPIKE))
    import q274_gen_identity as ident
    bad = dirty_violation(dirty())
    if bad:
        print("ABORT: the working tree is dirtier than what this run is allowed to build:", bad)
        return 2
    pristine = {p: p.read_bytes() for p in {tgt for m in MUTANTS.values() for (tgt, _n, _r) in m["patches"]}}
    cand = ident.disk_identity("candidate", CAND)
    ident.refuse_if_unusable(cand, "candidate client")
    results, shapes = {}, {}
    try:
        for name, spec in MUTANTS.items():
            try:
                for target, needle, repl in spec["patches"]:
                    text = pristine[target].decode("utf-8")
                    if needle not in text:
                        raise SystemExit(f"ABORT: {name}: anchor not present verbatim in {target.name}")
                    if text.replace(needle, repl, 1) == text:
                        raise SystemExit(f"ABORT: {name} would not change anything")
                    target.write_text(text.replace(needle, repl, 1), encoding="utf-8", newline="\n")
                results[name] = build(name)
            finally:
                for t, b in pristine.items():
                    t.write_bytes(b)          # restore before the next mutant, not after the last one
            shapes[name] = shipped_shape(name, spec["tag"])
            print(f"  built {name}: {results[name]}")
            print(f"    shipped: {json.dumps(shapes[name], ensure_ascii=False)[:220]}")
    finally:
        for t, b in pristine.items():
            t.write_bytes(b)
    restored = all(hashlib.sha256(t.read_bytes()).hexdigest() == hashlib.sha256(b).hexdigest()
                   for t, b in pristine.items())
    print("restored byte-exact:", restored, "| src now:", repr(dirty()))
    ok = restored and not dirty_violation(dirty()) and all(r["rc"] == 0 for r in results.values())
    rows = {}
    for name, spec in MUTANTS.items():
        got, want = shapes.get(name) or {}, dict(spec["shape"], advertises_tag=True)
        mism = {k: (got.get(k), v) for k, v in want.items() if got.get(k) is not v}
        d = LANE / "frontend" / name
        g = ident.disk_identity(name, d) if d.is_dir() else None
        moved = bool(g and g["content_fingerprint"] != cand["content_fingerprint"])
        print(f'  {name:28s} verdict={g and g["generation_verdict"]} bytes_moved_vs_candidate={moved} '
              f'shape_ok={not mism} content={g and g["content_fingerprint"][:12]}')
        if mism:
            print(f"    SHAPE MISMATCH: {json.dumps(mism)}")
        rows[name] = {"tag": spec["tag"], "declared": spec["shape"], "shipped": got,
                      "shape_mismatch": mism, "generation": g, "build": results.get(name)}
        if mism or not moved or not g or g["generation_verdict"] != "GREEN":
            ok = False
    print("verdict:", "B2B_TARGET_ARMS_BUILT" if ok else "B2B_TARGET_ARMS_NOT_USABLE")
    p = WORK / "ord0274_b2b_mutant_shapes.json"
    p.write_text(json.dumps({"built_as": "swap TARGET generations (the restoring code is the incoming one)",
                             "candidate_client": {"dir": CAND.name, "content_fingerprint": cand["content_fingerprint"]},
                             "arms": rows, "all_shapes_match_declaration": ok},
                            ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print("->", p.name)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
