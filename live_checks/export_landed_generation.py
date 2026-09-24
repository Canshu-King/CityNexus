"""Download one commit's tarball from GitHub and extract the lanes' working surfaces, read-only.

Used to re-verify a LANDED generation with my own hands instead of quoting someone else's reading:
`--sha` is exported with `git archive` semantics via the codeload tarball, then I run the gate's own
reverify tool against it.  Everything lands under _qoder_cmdr_ref_20260921/tmp_landcheck_<sha12>/ and is
deleted by the caller; nothing here touches a database, a branch, or another lane's tree.
"""
import io
import json
import os
import subprocess
import sys
import tarfile
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
REPO = "Canshu-King/CityNexus"
KEEP = ("backend", "data", "contracts", "tools")     # the sparse set a backend gate needs; excluding any
# of these manufactures fake reds (measured twice already this project)


def main():
    sha = sys.argv[1]
    dest = os.path.join(HERE_ROOT, f"tmp_landcheck_{sha[:12]}")
    os.makedirs(dest, exist_ok=True)
    url = f"https://codeload.github.com/{REPO}/tar.gz/{sha}"
    tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok,
                                               "User-Agent": "commander-landcheck"})
    with urllib.request.urlopen(req, timeout=600) as r:
        blob = r.read()
    print(f"tarball {len(blob):,} B from codeload (http 200)")
    names = []
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        for m in tf.getmembers():
            parts = m.name.split("/")
            if len(parts) < 2 or parts[1] not in KEEP:
                continue
            try:
                tf.extract(m, dest, filter="data")     # 3.12+
            except TypeError:
                tf.extract(m, dest)                    # this box also runs 3.10, which has no filter kwarg
            names.append(m.name)
    root = os.path.join(dest, os.listdir(dest)[0]) if len(os.listdir(dest)) == 1 else dest
    backend = os.path.join(root, "backend")
    gate = os.path.join(backend, "tests", "test_qoder_ord0272_continuation.py")
    print(f"extracted {len(names)} entries -> root={root}")
    print(f"  backend present: {os.path.isdir(backend)}  gate file present: {os.path.isfile(gate)}")
    print(f"  tests collected dir exists: {os.path.isdir(os.path.join(backend, 'tests'))}")
    json.dump({"sha": sha, "root": root, "backend": backend, "entries": len(names)},
              io.open(os.path.join(HERE_ROOT, f"landcheck_{sha[:12]}.json"), "w", encoding="utf-8"), indent=1)
    print("MANIFEST", os.path.join(HERE_ROOT, f"landcheck_{sha[:12]}.json"))


HERE_ROOT = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    main()
