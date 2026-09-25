"""ORD-0297: build the two generations this cell must be measured on, from the LANDED line only.

Everything comes out of `git archive <40-hex>` of a tip I read externally and stored in
`o297_ref_tip_read.json` -- never from another lane's worktree, and never reusing the candidate-tip
dists I built for ORD-0290 (the order says, in terms, "别再用候选代读数代替本代").

  landed       = 5c4608ce, the generation the authoritative line reached (frontend bytes identical to
                 6d041dcc, which is a backend-only jump -- proven by the compare API, stored next to this)
  landed_next  = the same tree plus ONE inert line so its hashed bundle name differs; this is the
                 generation to converge onto, and its before/after blob ids are recorded so the edit is
                 auditable and the shipped code is otherwise byte-faithful.

node_modules is reached through a junction; the junction is unlinked with `rmdir` before any rmtree,
because `shutil.rmtree` follows junctions straight into the shared 427 MB tree (hazard D-7).
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
ROOT = os.path.join(LANE, "o297")
ORDERED = "5c4608cede6cb7bd5f3ac7e704bfee379ca47abc"
MARKER = "window.__cnxNextGenerationMarker = \"ORD-0297-next\";"


def git(*a, **kw):
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True, **kw)


def full(abbrev):
    out = git("rev-parse", abbrev).stdout.strip()
    assert re.fullmatch(r"[0-9a-f]{40}", out), "cannot resolve " + abbrev
    return out


def export(name, sha, paths=("frontend",)):
    dst = os.path.join(ROOT, name)
    link = os.path.join(dst, "frontend", "node_modules")
    if "frontend" not in paths:
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        os.makedirs(dst)
        t = subprocess.run(["git", "-C", REPO, "archive", sha] + list(paths), capture_output=True)
        assert t.returncode == 0, (t.stderr or b"")[:200]
        u = subprocess.run(["tar", "-x", "-C", dst], input=t.stdout, capture_output=True)
        assert u.returncode == 0 and os.path.isdir(os.path.join(dst, "backend")), "backend export failed"
        return dst
    if os.path.lexists(link):
        subprocess.run(["cmd", "/c", "rmdir", link], check=True, capture_output=True)
        assert os.path.isdir(os.path.join(REPO, "frontend", "node_modules", "vite")), "shared target damaged"
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    # bytes, never text: a decoded git-archive stream untars to an empty tree, which is how this
    # export silently produced a directory with no frontend/ in it
    t = subprocess.run(["git", "-C", REPO, "archive", sha] + list(paths), capture_output=True)
    assert t.returncode == 0, (t.stderr or b"")[:200]
    assert len(t.stdout) > 10000, "git archive returned %d bytes -- nothing to extract" % len(t.stdout)
    u = subprocess.run(["tar", "-x", "-C", dst], input=t.stdout, capture_output=True)
    assert u.returncode == 0, (u.stderr or b"")[:200]
    assert os.path.isdir(os.path.join(dst, "frontend")) or os.path.isdir(os.path.join(dst, "backend")),         "extracted tree has neither frontend/ nor backend/"
    r = subprocess.run(["cmd", "/c", "mklink", "/J", link,
                        os.path.join(REPO, "frontend", "node_modules")], capture_output=True)
    assert r.returncode == 0, (r.stderr or b"")[-200:]
    assert os.path.isfile(os.path.join(link, "vite", "package.json")), "junction does not resolve"
    return dst


def build(name, sha, reexport=True):
    # reexport=False exists because the earlier version of this file rebuilt landed_next through
    # export() and silently discarded the marker line it had just written -- producing two generations
    # with the same hashed bundle name (that is exactly the "not separable" failure the asserts catch)
    dst = export(name, sha) if reexport else os.path.join(ROOT, name)
    log = os.path.join(ROOT, name + ".build.log")
    with open(log, "wb") as fh:
        rc = subprocess.call("npx vite build", cwd=os.path.join(dst, "frontend"),
                             stdout=fh, stderr=subprocess.STDOUT, shell=True, timeout=900)
    d = os.path.join(dst, "frontend", "dist")
    html = io.open(os.path.join(d, "index.html"), encoding="utf-8").read()
    js = re.search(r"assets/(index-[\w-]+\.js)", html).group(1)
    raw = open(os.path.join(d, "assets", js), "rb").read()
    sw = open(os.path.join(d, "v10-sw.js"), "rb").read()
    return {"commit": sha, "build_exit": rc, "dist": d, "bundle": js, "bundle_bytes": len(raw),
            "bundle_sha256_16": hashlib.sha256(raw).hexdigest()[:16],
            "shell_md5": hashlib.md5(open(os.path.join(d, "index.html"), "rb").read()).hexdigest(),
            "worker_sha256_16": hashlib.sha256(sw).hexdigest()[:16],
            "marker_in_served_bundle": MARKER.split("=")[0].strip() in raw.decode("utf-8", "replace")}


def main():
    assert os.path.isdir(os.path.join(REPO, ".git")), REPO
    sha = full(ORDERED)
    rec = {"order": "ORD-0297", "built_at": time_str(),
           "ref_tip_read_file": "o297_ref_tip_read.json",
           "ordered_tip": sha, "trees": {}}
    rec["trees"]["landed"] = build("landed", sha)
    print("landed", sha[:12], "->", rec["trees"]["landed"]["bundle"], flush=True)
    assert rec["trees"]["landed"]["build_exit"] == 0, "vite build failed"

    n = build("landed_next", sha)
    mp = os.path.join(ROOT, "landed_next", "frontend", "src", "main.tsx")
    src = io.open(mp, encoding="utf-8", newline="").read()
    assert MARKER not in src
    before = hashlib.sha1(b"blob %d\0" % len(src.encode("utf-8")) + src.encode("utf-8")).hexdigest()
    io.open(mp, "w", encoding="utf-8", newline="").write(src + "\n// ORD-0297 verifier marker; inert, not on any branch\n" + MARKER + "\n")
    new_src = io.open(mp, encoding="utf-8").read()
    after = hashlib.sha1(b"blob %d\0" % len(new_src.encode("utf-8")) + new_src.encode("utf-8")).hexdigest()
    git_blob = git("rev-parse", sha + ":frontend/src/main.tsx").stdout.strip()
    shutil.rmtree(os.path.join(ROOT, "landed_next", "frontend", "dist"), ignore_errors=True)
    n2 = build("landed_next", sha, reexport=False)
    n2["marker_line_added"] = MARKER
    n2["main_tsx_committed_blob"] = git_blob
    n2["main_tsx_blob_before_edit"] = before
    n2["main_tsx_blob_after_edit"] = after
    n2["only_change_is_the_marker_line"] = new_src.startswith(src) and new_src.endswith(MARKER + "\n")
    rec["trees"]["landed_next"] = n2
    print("landed_next ->", n2["bundle"], "marker_survives=", n2["marker_in_served_bundle"], flush=True)

    names = [rec["trees"][k]["bundle"] for k in ("landed", "landed_next")]
    rec["pairwise_distinct"] = len(set(names)) == len(names)
    rec["shell_md5_distinct"] = rec["trees"]["landed"]["shell_md5"] != rec["trees"]["landed_next"]["shell_md5"]
    rec["backend_trees"] = {}
    for label, ab in (("ordered_backend", ORDERED), ("landed_backend", "6d041dcce11d05f28a55abadd40717f321b4db38")):
        s = full(ab)
        d = export(label, s, ("backend", "data", "contracts", "tools"))
        rec["backend_trees"][label] = {"commit": s, "backend_dir": os.path.join(d, "backend"),
                                       "has_main": os.path.isfile(os.path.join(d, "backend", "app", "main.py"))}
    io.open(os.path.join(LANE, "o297_builds.json"), "w", encoding="utf-8").write(
        json.dumps(rec, ensure_ascii=False, indent=2))
    print(json.dumps({"bundles": {k: rec["trees"][k]["bundle"] for k in rec["trees"]},
                      "pairwise_distinct": rec["pairwise_distinct"],
                      "shell_md5_distinct": rec["shell_md5_distinct"],
                      "marker_survives_in_bundle": rec["trees"]["landed_next"]["marker_in_served_bundle"],
                      "only_change_is_marker": rec["trees"]["landed_next"]["only_change_is_the_marker_line"],
                      "backend_trees": {k: v["commit"][:12] for k, v in rec["backend_trees"].items()}},
                     ensure_ascii=False, indent=1))
    assert rec["pairwise_distinct"] and rec["shell_md5_distinct"], "the two generations are not separable"


def time_str():
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


if __name__ == "__main__":
    main()
