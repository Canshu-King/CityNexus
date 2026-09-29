"""ORD-0417 lane: a small generic packer -- add local files under new review paths, nothing else.

Written because each delivery so far needed its own packer and every one of them re-implemented the
same three guards.  The guards are the point and are kept:
  1. REFUSE a destination that already exists on the line -- a re-delivery takes a new name;
  2. scan text for value-shaped secrets before hashing (the shared preview's Basic-auth file is never
     opened by anything in this lane; this only rejects anything that looks like a credential);
  3. build the commit in a throwaway index, so the shared dirty working tree and `.git/index` are not
     touched, and hash with `--no-filters` so the bytes that land are the bytes on disk.

The file list comes from a JSON manifest so a follow-up commit never needs a new script:
usage: python ord0417_pack_files_r1.py --line <40-hex> --branch <ref> --manifest <file.json> [--apply]
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
SECRET_PATTERNS = [
    re.compile(rb"Author" + rb"ization[^A-Za-z]{0,3}\s*(Basic|Bearer)\s+[A-Za-z0-9+/=]{8,}"),
    re.compile(rb"(?i)\bBearer\s+[A-Za-z0-9_\-\.]{20,}"),
    re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    re.compile(rb"(?i)(api[_-]?key|secret|passw(or)?d|token)\s*[:=]\s*[\"'][^\"']{8,}[\"']"),
]


def git(*args, env=None):
    r = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} -> rc={r.returncode} {r.stderr.strip()[:200]}")
    return (r.stdout or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--line", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    manifest = json.load(open(args.manifest, encoding="utf-8"))
    adds = manifest["adds"]
    missing = [a["src"] for a in adds if not pathlib.Path(a["src"]).exists()]
    if missing:
        raise SystemExit("REFUSE: sources missing " + json.dumps(missing))
    for a in adds:
        if subprocess.run(["git", "-C", REPO, "cat-file", "-e", f"{args.line}:{a['dst']}"],
                          capture_output=True).returncode == 0:
            raise SystemExit(f"REFUSE: {a['dst']} is already on the line -- pick a new name")
        if not a["dst"].endswith((".png", ".jpg")):
            blob = pathlib.Path(a["src"]).read_bytes()
            hits = [p.pattern for p in SECRET_PATTERNS if p.search(blob)]
            if hits:
                raise SystemExit(f"REFUSE: credential-shaped bytes in {a['dst']}: {hits}")

    idx = tempfile.NamedTemporaryFile(prefix="ord0417pf_", suffix=".idx", delete=False)
    idx.close()
    env = dict(os.environ, GIT_INDEX_FILE=idx.name)
    try:
        subprocess.run(["git", "-C", REPO, "read-tree", args.line], env=env, check=True, capture_output=True)
        rows = []
        for a in adds:
            blob = git("hash-object", "-w", "--no-filters", a["src"])
            subprocess.run(["git", "-C", REPO, "update-index", "--add", "--cacheinfo",
                            f"100644,{blob},{a['dst']}"], env=env, check=True, capture_output=True)
            rows.append({"path": a["dst"], "blob": blob,
                         "bytes": pathlib.Path(a["src"]).stat().st_size})
        tree = subprocess.run(["git", "-C", REPO, "write-tree"], env=env, check=True,
                              capture_output=True, text=True).stdout.strip()
        msg = manifest["message"] + f"\nParent (the line this grafts onto): {args.line}\n"
        commit = git("commit-tree", tree, "-p", args.line, "-m", msg)
        print(json.dumps({"line": args.line, "tree": tree, "commit": commit, "added": rows,
                          "applied": bool(args.apply)}, indent=1))
        if args.apply:
            git("update-ref", args.branch, commit)
            print("ref moved:", args.branch)
    finally:
        os.unlink(idx.name)


if __name__ == "__main__":
    main()
