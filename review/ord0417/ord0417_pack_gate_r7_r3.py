"""ORD-0417 lane: publish the r7 gate re-run receipts as a review candidate (r3).

r3 vs r2: same two rules (refuse a name already on the line, scan for value-shaped secrets) and a new file set -- this pack carries the 17-arm gate re-run on the r7 branch, its attribution control, and the probe that named why a control was lost.  r2 vs r1, in one sentence: r1 shipped 16 files in one commit and could only ever ship all 16; this
version takes `--only <substring>` so a follow-up commit can add one receipt on top of the branch it
already made, and it ships itself under a NEW name rather than overwriting r1's blob -- the published
instrument has to be the one that ran, and an add/add of the same path would have been refused (that
refusal is the point of rule 1 below, so I did not carve an exception for myself).

Why a dedicated packer: the order's product bytes are already on the authoritative line, so this
branch carries evidence and instruments only.  `ord0417_commit_r1.py` is built to ship the four
product paths out of a source export; those directories are gone now (snap dismantled), and bending
it to a different file set would hide what is actually being added.  Two rules are enforced here
rather than remembered:

  1. REFUSE a name that already exists on the line -- a review candidate may not be an overwrite.
  2. Scan every text file for value-shaped secrets before hashing it.  The auth口令 for the shared
     preview lives in `D:/moodle/_qoder_preview_20260920/run/preview_auth.txt`; this script never
     opens that file, and it rejects anything that looks like a credential rather than trusting intent.

Everything is assembled in a throwaway index (`.git/index`, i.e. the shared dirty working tree, is
never opened) and `--no-filters` keeps the bytes that get hashed identical to the bytes on disk.

usage: python ord0417_pack_snap_geom_r1.py --line <40-hex> --branch <ref> [--apply]
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

REPO = r"D:/moodle/CityNexus"
BASE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
EVID = BASE / "evidence" / "geom_snap_tip35326e62"
RUN = BASE / "run"
GATE = BASE / "evidence" / "gate_pack_r7"

# (source on disk, destination path on the line)
ADDS = [
    (GATE / "GATE_R7_ARMS_R25.json", "review/ord0417/GATE_R7_ARMS_R25.json"),
    (GATE / "GATE_R7_LIST_ARMS_R25.txt", "review/ord0417/GATE_R7_LIST_ARMS_R25.txt"),
    (GATE / "GATE_R7_RED_414EN_RUNS_R1.txt", "review/ord0417/GATE_R7_RED_414EN_RUNS_R1.txt"),
    (GATE / "GATE_R7_ATTRIBUTION_414EN_R1.json", "review/ord0417/GATE_R7_ATTRIBUTION_414EN_R1.json"),
    (GATE / "GATE_R7_PILLPROBE_414EN_R1.json", "review/ord0417/GATE_R7_PILLPROBE_414EN_R1.json"),
    (GATE / "GATE_R7_PILLPROBE_SPEC_R1.ts.txt", "review/ord0417/GATE_R7_PILLPROBE_SPEC_R1.ts.txt"),
    (GATE / "GATE_R20_GEOMETRY_ROWS_R1.json", "review/ord0417/GATE_R20_GEOMETRY_ROWS_R1.json"),
    (RUN / "ord0417_gate_arm_report_r1.py", "review/ord0417/ord0417_gate_arm_report_r1.py"),
    (RUN / "ord0417_make_pill_probe_r3.py", "review/ord0417/ord0417_make_pill_probe_r3.py"),
    (RUN / "ord0417_build_gate_pack_r7_r1.py", "review/ord0417/ord0417_build_gate_pack_r7_r1.py"),
    (RUN / "ord0417_pack_gate_r7_r3.py", "review/ord0417/ord0417_pack_gate_r7_r3.py"),
]

# value-shaped, not keyword-shaped: the earlier scan caught its own regex source and a base64-looking
# example inside a comment, which taught nothing.  These only fire on something that has the SHAPE of
# a secret.
SECRET_PATTERNS = [
    re.compile(rb"Authorization[^A-Za-z]{0,3}\s*(Basic|Bearer)\s+[A-Za-z0-9+/=]{8,}"),
    re.compile(rb"(?i)\bBearer\s+[A-Za-z0-9_\-\.]{20,}"),
    re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    re.compile(rb"(?i)(api[_-]?key|secret|passw(or)?d|token)\s*[:=]\s*[\"'][^\"']{8,}[\"']"),
]


def git(*args, capture=True):
    r = subprocess.run(["git", "-C", REPO, "-c", "core.autocrlf=false", *args],
                       capture_output=capture, text=True)
    if r.returncode != 0 and capture:
        raise SystemExit(f"git {' '.join(args)} -> rc={r.returncode} {r.stderr.strip()[:200]}")
    return (r.stdout or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--line", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", default="",
                    help="substring filter on the destination path, for a follow-up commit")
    args = ap.parse_args()

    adds = [x for x in ADDS if args.only in x[1]] if args.only else ADDS
    if not adds:
        raise SystemExit(f"REFUSE: --only {args.only!r} selected nothing")
    missing = [str(s) for s, _ in adds if not s.exists()]
    if missing:
        raise SystemExit("REFUSE: sources missing " + json_line(missing))

    collisions = []
    for _, dst in adds:
        rc = subprocess.run(["git", "-C", REPO, "cat-file", "-e", f"{args.line}:{dst}"],
                            capture_output=True).returncode
        if rc == 0:
            collisions.append(dst)
    if collisions:
        raise SystemExit("REFUSE: name already on the line (would overwrite) " + json_line(collisions))

    # Calibrate before judging anything: a detector that cannot say "yes" to a real-shaped credential
    # is decoration, and one that fires on its own source would block every pack that ships it (this
    # lane was stopped by exactly that once).  Both halves run here, and the pack aborts if either fails.
    synthetic = ("Author" + "ization: Basic " + "Q05EUk1PQ0tZVkFMVUU0" + "5NiI").encode("ascii")  # concatenated so the bait is not itself a match
    fired = [p.pattern for p in SECRET_PATTERNS if p.search(synthetic)]
    if not fired:
        raise SystemExit("REFUSE: credential scan does not fire on a synthetic header -- not calibrated")
    own = pathlib.Path(__file__).read_bytes()
    self_hits = [p.pattern for p in SECRET_PATTERNS if p.search(own)]
    if self_hits:
        raise SystemExit(f"REFUSE: scan matches its own source, would block every pack: {self_hits}")

    for src, dst in adds:
        if dst.endswith(".png"):
            continue
        blob = src.read_bytes()
        hits = [p.pattern for p in SECRET_PATTERNS if p.search(blob)]
        if hits:
            raise SystemExit(f"REFUSE: credential-shaped bytes in {dst} matching {hits}")

    idx = tempfile.NamedTemporaryFile(prefix="ord0417snap_", suffix=".idx", delete=False)
    idx.close()
    env = dict(os.environ, GIT_INDEX_FILE=idx.name)
    try:
        subprocess.run(["git", "-C", REPO, "read-tree", args.line], env=env, check=True,
                       capture_output=True)
        entries = []
        for src, dst in adds:
            sha = git("hash-object", "-w", "--no-filters", str(src))
            mode = "100644"
            subprocess.run(["git", "-C", REPO, "update-index", "--add", "--cacheinfo",
                            f"{mode},{sha},{dst}"], env=env, check=True, capture_output=True)
            entries.append((dst, sha, src.stat().st_size))
        tree = subprocess.run(["git", "-C", REPO, "write-tree"], env=env, check=True,
                              capture_output=True, text=True).stdout.strip()
        msg = ("ORD-0417 evidence: the 17-arm gate re-run on review/R-ord0417-tap-names-stop-r7\n"
               "\n"
               "The subject names the branch, not a short sha -- the generation is the commit this\n"
               f"branch grafts onto, {args.line}, and that is the parent recorded on the object.\n"
               "\n"
               "Contents: the per-arm receipt joined against the `--list` denominator (so the count is\n"
               "not arguable later), the trimmed result lines of four runs -- first pass, quiet re-run\n"
               "of the red arm, the same arm with only this order's painted cell deleted from\n"
               "MapPanel.tsx, and a probe copy that names which reachability predicate flipped -- plus\n"
               "the previous generation's geometry rows, which is what shows the red is new at this\n"
               "generation rather than something this order shipped.  Instruments ship with the\n"
               "readings so they can be re-taken.\n")
        commit = git("commit-tree", tree, "-p", args.line, "-m", msg)
        print(json.dumps({
            "line_parent": args.line, "tree": tree, "commit": commit,
            "added": [{"path": d, "blob": s, "bytes": n} for d, s, n in entries],
            "collisions_refused": len(collisions), "applied": bool(args.apply),
        }, indent=1))
        if args.apply:
            git("update-ref", args.branch, commit)
            print("ref moved:", args.branch)
    finally:
        os.unlink(idx.name)


def json_line(items):
    import json
    return json.dumps(items, ensure_ascii=False)


if __name__ == "__main__":
    main()
