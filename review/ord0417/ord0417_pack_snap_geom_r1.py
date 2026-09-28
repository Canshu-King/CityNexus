"""ORD-0417 lane: publish the snap-generation geometry receipts as a review candidate.

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

# (source on disk, destination path on the line)
ADDS = [
    (EVID / "SNAP_TIP_zh.census.json", "review/ord0417/GEOM_SNAP_TIP_35326E62_ZH_R2.json"),
    (EVID / "SNAP_TIP_en.census.json", "review/ord0417/GEOM_SNAP_TIP_35326E62_EN_R2.json"),
    (EVID / "SNAP_CTRL_zh.census.json", "review/ord0417/GEOM_SNAP_CTRL_35326E62_ZH_R2.json"),
    (EVID / "SNAP_CTRL_en.census.json", "review/ord0417/GEOM_SNAP_CTRL_35326E62_EN_R2.json"),
    (EVID / "PAIR_R1.json", "review/ord0417/GEOM_SNAP_35326E62_PAIR_R1.json"),
    (EVID / "table_and_verdict.txt", "review/ord0417/GEOM_SNAP_35326E62_TABLE_VERDICT_R1.txt"),
    (BASE / "evidence" / "snap_tip35326e62_port_ownership_before.json",
     "review/ord0417/PORT_OWNERSHIP_SNAP_35326E62_R1.txt"),
    (BASE / "evidence" / "snap_tip35326e62_port_ownership_ctrl.json",
     "review/ord0417/PORT_OWNERSHIP_SNAP_CTRL_35326E62_R1.txt"),
    (EVID / "SNAP_TIP_zh_390x844.png", "review/ord0417/GEOM_SNAP_TIP_35326E62_ZH_390x844_R1.png"),
    (EVID / "SNAP_CTRL_zh_390x844.png", "review/ord0417/GEOM_SNAP_CTRL_35326E62_ZH_390x844_R1.png"),
    (RUN / "ord0417_geometry_census_r2.js", "review/ord0417/ord0417_geometry_census_r2.js"),
    (RUN / "ord0417_census_table_r1.py", "review/ord0417/ord0417_census_table_r1.py"),
    (RUN / "ord0417_census_pair_r1.py", "review/ord0417/ord0417_census_pair_r1.py"),
    (RUN / "ord0417_snap_db_copy_r1.py", "review/ord0417/ord0417_snap_db_copy_r1.py"),
    (RUN / "ord0417_snap_port_ownership_r1.py", "review/ord0417/ord0417_snap_port_ownership_r1.py"),
    (RUN / "ord0417_pack_snap_geom_r1.py", "review/ord0417/ord0417_pack_snap_geom_r1.py"),
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
    args = ap.parse_args()

    missing = [str(s) for s, _ in ADDS if not s.exists()]
    if missing:
        raise SystemExit("REFUSE: sources missing " + json_line(missing))

    collisions = []
    for _, dst in ADDS:
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

    for src, dst in ADDS:
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
        for src, dst in ADDS:
            sha = git("hash-object", "-w", "--no-filters", str(src))
            mode = "100644"
            subprocess.run(["git", "-C", REPO, "update-index", "--add", "--cacheinfo",
                            f"{mode},{sha},{dst}"], env=env, check=True, capture_output=True)
            entries.append((dst, sha, src.stat().st_size))
        tree = subprocess.run(["git", "-C", REPO, "write-tree"], env=env, check=True,
                              capture_output=True, text=True).stdout.strip()
        msg = ("ORD-0417 evidence: product-level geometry census on a snap of the line\n"
               "\n"
               "Subject line names no short sha on purpose -- the generation is the commit this branch\n"
               f"grafts onto, {args.line}, and the file names in this pack carry it too.\n"
               "\n"
               "The order's own gate measures reachability inside the Playwright run.  This pack is the\n"
               "same 768 px ruler taken on a bundle built straight from that tip's bytes, plus a control\n"
               "bundle with only the painted cell cut out of MapPanel.tsx (the dictionary value stays in\n"
               "both, so the control removes the sentence and nothing else).  Eight shape x arm runs per\n"
               "generation, one receipt per arm, and both dimensions of the new cell: its box and the\n"
               "client rects of a Range over its contents, because wrapping is only observable in the\n"
               "second one.  Instruments ship with the readings so they can be re-taken.\n")
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
