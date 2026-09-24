"""ORD-0290: build the candidate staircase, one dist per commit, B's bytes untouched.

Trees come from `git archive <40-hex>` out of the integration repo (never from B's worktree) and
the four builds are byte-faithful to their commits.  The only edited tree is the deliberate
"next generation" used as the thing to converge ONTO: it is ef277b2 plus one inert line
(window.__cnxNextGenerationMarker) so its hashed bundle name differs.  That substitution is
recorded in the receipt; every measured arm runs against an unmodified tree.
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors='replace')
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
REPO = r"D:\moodle\_qoder_integration_20260919"
ROOT = os.path.join(LANE, "o290")
NM = {"baseline": "45b0a5e281ca", "s1_b2a": "69fd2f85cab2", "s2_b2c": "45a3d56862fc",
      "s3_b2b": "ef277b2da5df"}
COMMITS = {"45b0a5e2": "45b0a5e281ca", "69fd2f85": "69fd2f85cab2",
           "45a3d568": "45a3d56862fc", "ef277b2d": "ef277b2da5df"}
os.makedirs(ROOT, exist_ok=True)
receipt = {"order": "ORD-0290", "purpose": "build staircase for the five-arm derivation",
           "trees": {}, "next_generation_edit": None}


def full(abbrev):
    return subprocess.run(["git", "-C", REPO, "rev-parse", abbrev], capture_output=True,
                          text=True).stdout.strip()


def export(name, sha):
    dst = os.path.join(ROOT, name)
    link = os.path.join(dst, "frontend", "node_modules")
    if os.path.lexists(link):
        # rmdir on a junction unlinks it without walking into the target; rmtree would follow it
        # straight into the shared 427 MB node_modules (the D-7 hazard).
        subprocess.run(["cmd", "/c", "rmdir", link], check=True, capture_output=True)
        assert os.path.isdir(os.path.join(REPO, "frontend", "node_modules", "vite")), "target damaged"
    if os.path.isdir(dst):
        shutil.rmtree(dst)                      # safe now: no link inside
    os.makedirs(dst)
    t = subprocess.run(["git", "-C", REPO, "archive", sha, "frontend"], capture_output=True)
    assert t.returncode == 0, t.stderr[:200]
    subprocess.run(["tar", "-x", "-C", dst], input=t.stdout, check=True)
    r = subprocess.run(["cmd", "/c", "mklink", "/J", link,
                        os.path.join(REPO, "frontend", "node_modules")],
                       capture_output=True)
    assert r.returncode == 0, (r.stdout or b"")[-200:] + (r.stderr or b"")[-200:]
    # the link must actually resolve, or a build would silently fail in a way that looks like the tree
    assert os.path.isfile(os.path.join(link, "vite", "package.json")), "node_modules link does not resolve"
    return dst


def build(name, sha):
    dst = export(name, sha)
    log = os.path.join(ROOT, name + ".build.log")
    with open(log, "wb") as fh:
        rc = subprocess.call('npx vite build', cwd=os.path.join(dst, "frontend"),
                             stdout=fh, stderr=subprocess.STDOUT, shell=True, timeout=900)
    d = os.path.join(dst, "frontend", "dist")
    html = io.open(os.path.join(d, "index.html"), encoding="utf-8").read()
    js = re.search(r"assets/(index-[\w-]+\.js)", html).group(1)
    sw = open(os.path.join(d, "v10-sw.js"), "rb").read()
    sw_text = sw.decode("utf-8", "replace")
    ent = re.findall(r'\{\s*url\s*:\s*"([^"]+)"\s*,\s*revision\s*:\s*(?:"([^"]*)"|(null))\s*\}',
                     sw_text[sw_text.index("precacheAndRoute"):])
    return {"commit": sha, "build_exit": rc, "dist": d, "bundle": js,
            "bundle_bytes": os.path.getsize(os.path.join(d, "assets", js)),
            "bundle_sha256_16": hashlib.sha256(open(os.path.join(d, "assets", js), "rb").read()).hexdigest()[:16],
            "shell_md5": hashlib.md5(open(os.path.join(d, "index.html"), "rb").read()).hexdigest(),
            "worker_sha256_16": hashlib.sha256(sw).hexdigest()[:16],
            "precache_entries": len(ent), "index_html_sha256_16": hashlib.sha256(
                open(os.path.join(d, "index.html"), "rb").read()).hexdigest()[:16]}


for label, ab in NM.items():
    sha = full(ab)
    receipt["trees"][label] = build(label, sha)
    print(label, sha[:12], "->", receipt["trees"][label]["bundle"], flush=True)

# the "next generation": ef277b2 plus ONE inert line, so its hashed name differs
next_sha = full(COMMITS["ef277b2d"])
n = build("next_gen", next_sha)
mp = os.path.join(ROOT, "next_gen", "frontend", "src", "main.tsx")
src = io.open(mp, encoding="utf-8").read()
io.open(mp, "w", encoding="utf-8", newline="").write(
    src + '\nwindow.__cnxNextGenerationMarker = "ORD-0290-next";\n')
shutil.rmtree(os.path.join(ROOT, "next_gen", "frontend", "dist"), ignore_errors=True)
n2 = build("next_gen", next_sha)
n2["marker_line_added"] = "window.__cnxNextGenerationMarker = \"ORD-0290-next\";"
n2["main_tsx_blob_before_edit"] = subprocess.run(["git", "-C", REPO, "rev-parse",
                                                  next_sha + ":frontend/src/main.tsx"],
                                                 capture_output=True, text=True).stdout.strip()
n2["main_tsx_blob_after_edit"] = hashlib.sha1(b"blob %d\0" % len(open(mp, "rb").read())
                                              + open(mp, "rb").read()).hexdigest()
receipt["next_generation_edit"] = n2
print("next_gen ->", n2["bundle"], flush=True)
names = [receipt["trees"][k]["bundle"] for k in NM] + [n2["bundle"]]
receipt["pairwise_distinct"] = len(set(names)) == len(names)
io.open(os.path.join(LANE, "o290_builds.json"), "w", encoding="utf-8").write(
    json.dumps(receipt, ensure_ascii=False, indent=2))
print(json.dumps({"bundles": {k: receipt["trees"][k]["bundle"] for k in NM}, "next": n2["bundle"],
                  "pairwise_distinct": receipt["pairwise_distinct"]}, ensure_ascii=False, indent=1))
