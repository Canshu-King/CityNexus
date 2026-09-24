"""Rebuild ONLY the "next generation" tree: export -> add the marker -> build.

My first pass called the same helper that exports and builds, so the second call re-extracted
the tree from git and silently threw away the marker line - producing a "next generation"
byte-identical to s3_b2b (reported honestly as pairwise_distinct=false).  Order matters here:
the edit must happen after the export and before the build, with no re-export in between.
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
REPO = r"D:\moodle\_qoder_integration_20260919"
ROOT = os.path.join(LANE, "o290")
TIP = subprocess.run(["git", "-C", REPO, "rev-parse", "ef277b2da5df"], capture_output=True,
                     text=True).stdout.strip()
DST = os.path.join(ROOT, "next_gen")
LINK = os.path.join(DST, "frontend", "node_modules")
MARKER = 'window.__cnxNextGenerationMarker = "ORD-0290-next";'

if os.path.lexists(LINK):
    subprocess.run(["cmd", "/c", "rmdir", LINK], check=True, capture_output=True)
    assert os.path.isdir(os.path.join(REPO, "frontend", "node_modules", "vite")), "shared target damaged"
shutil.rmtree(DST, ignore_errors=True)
os.makedirs(DST)
t = subprocess.run(["git", "-C", REPO, "archive", TIP, "frontend"], capture_output=True)
assert t.returncode == 0
subprocess.run(["tar", "-x", "-C", DST], input=t.stdout, check=True)
subprocess.run(["cmd", "/c", "mklink", "/J", LINK, os.path.join(REPO, "frontend", "node_modules")],
               capture_output=True, check=True)
assert os.path.isfile(os.path.join(LINK, "vite", "package.json"))

mp = os.path.join(DST, "frontend", "src", "main.tsx")
blob_before = subprocess.run(["git", "-C", REPO, "rev-parse", TIP + ":frontend/src/main.tsx"],
                             capture_output=True, text=True).stdout.strip()
src = io.open(mp, encoding="utf-8").read()
assert MARKER not in src
io.open(mp, "w", encoding="utf-8", newline="").write(src + "\n// ORD-0290 verifier marker; inert, not on any branch\n" + MARKER + "\n")
data = open(mp, "rb").read()
blob_after = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()

log = os.path.join(ROOT, "next_gen.build.log")
with open(log, "wb") as fh:
    rc = subprocess.call("npx vite build", cwd=os.path.join(DST, "frontend"), stdout=fh,
                         stderr=subprocess.STDOUT, shell=True, timeout=900)
d = os.path.join(DST, "frontend", "dist")
assert rc == 0 and os.path.isfile(os.path.join(d, "index.html")), "build failed rc=%s" % rc
html = io.open(os.path.join(d, "index.html"), encoding="utf-8").read()
js = re.search(r"assets/(index-[\w-]+\.js)", html).group(1)
bundle = open(os.path.join(d, "assets", js), "rb").read()
sw = open(os.path.join(d, "v10-sw.js"), "rb").read()
info = {"commit": TIP, "build_exit": rc, "dist": d, "bundle": js, "bundle_bytes": len(bundle),
        "bundle_sha256_16": hashlib.sha256(bundle).hexdigest()[:16],
        "shell_md5": hashlib.md5(open(os.path.join(d, "index.html"), "rb").read()).hexdigest(),
        "worker_sha256_16": hashlib.sha256(sw).hexdigest()[:16],
        "marker_line_added": MARKER, "main_tsx_blob_before_edit": blob_before,
        "main_tsx_blob_after_edit": blob_after,
        "marker_survives_in_bundle": b"ORD-0290-next" in bundle}
p = os.path.join(LANE, "o290_builds.json")
rec = json.load(io.open(p, encoding="utf-8"))
rec["next_generation_edit"] = info
names = [v["bundle"] for v in rec["trees"].values()] + [info["bundle"]]
rec["pairwise_distinct"] = len(set(names)) == len(names)
json.dump(rec, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps({"bundles": {k: v["bundle"] for k, v in rec["trees"].items()},
                  "next_gen": info["bundle"], "marker_survives_in_bundle": info["marker_survives_in_bundle"],
                  "blob_changed_by_marker": blob_before != blob_after,
                  "pairwise_distinct": rec["pairwise_distinct"]}, ensure_ascii=False, indent=1))
