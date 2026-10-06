"""ORD-0538 · Q64 exposure: does this round's frontend put anything new on screen?

The ruler is the commander's own (`ui_exposure_taint_ast_r7b.cjs`), so nothing here restates its
verdict: it runs over a `git archive` snapshot of `frontend/src` for two revisions, and the only
claim made below is the measured count for each side plus the files the round moves between them.

Run after the candidate is committed: `python ord0538_exposure_r1.py`.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
WT = r"D:/moodle/_qoder_newlane_ord0444_20260929/wt2"
SC = r"D:/moodle/_qoder_newlane_ord0444_20260929/scratch"
RULER = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/ui_exposure_taint_ast_r7b.cjs"
BASE_REV = "514b397f96f3b5165b24865f4a544ab6f8020084"
OUT = os.path.join(SC, "ord0538_exposure_514b397f.json")
ENV = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(k, None)


def git(*a):
    return subprocess.run(["git", "-C", WT] + list(a), capture_output=True, env=ENV)


def snapshot(rev, dest):
    """`git archive` rather than a checkout: the worktree belongs to the running stack."""
    p = git("archive", rev, "frontend/src")
    assert p.returncode == 0, p.stderr[:200]
    io.open(os.path.join(dest, "src.tar"), "wb").write(p.stdout)
    q = subprocess.run(["tar", "-xf", "src.tar"], cwd=dest, capture_output=True, env=ENV)
    assert q.returncode == 0, q.stderr[:200]
    return os.path.getsize(os.path.join(dest, "src.tar"))


out = {"ruler_path": RULER, "ruler_bytes_sha1_local": None, "sides": {}}
h = subprocess.run(["certutil", "-hashfile", RULER, "SHA1"], capture_output=True, text=True,
                   errors="replace")
for line in (h.stdout or "").splitlines():
    if len(line.strip()) == 40:
        out["ruler_bytes_sha1_local"] = line.strip().lower()
out["head"] = git("rev-parse", "HEAD").stdout.decode("utf-8", "replace").strip()
out["base_is_ancestor_of_head"] = git("merge-base", "--is-ancestor", BASE_REV, "HEAD").returncode == 0

for label, rev in (("base", BASE_REV), ("candidate", out["head"])):
    d = tempfile.mkdtemp(prefix="ord0538_exp_")
    try:
        snapshot(rev, d)
        r = subprocess.run(["node", RULER, "--tree", os.path.join(d, "frontend", "src"),
                            "--out", os.path.join(d, "rep.json")],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=ENV, timeout=900)
        rep = {}
        p = os.path.join(d, "rep.json")
        if os.path.exists(p):
            rep = json.loads(io.open(p, encoding="utf-8").read())
        out["sides"][label] = {"rev": rev, "exit": r.returncode,
                               "report_head": (r.stdout or "")[-400:],
                               "report": rep}
    finally:
        shutil.rmtree(d, ignore_errors=True)

b, c = out["sides"]["base"]["report"], out["sides"]["candidate"]["report"]
# The claim is the delta of what the ruler counts, whatever it calls those counts internally; both
# raw reports are kept in this file so nothing here has to be taken on trust.
out["same_shape"] = sorted(b.keys()) == sorted(c.keys())
out["base_top_level_keys"] = sorted(b.keys())
out["candidate_top_level_keys"] = sorted(c.keys())
dest = OUT
io.open(dest, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print("WROTE", dest, os.path.getsize(dest), "bytes")
print("base", out["sides"]["base"]["exit"], "candidate", out["sides"]["candidate"]["exit"],
      "ancestor", out["base_is_ancestor_of_head"])
for side in ("base", "candidate"):
    rep = out["sides"][side]["report"]
    for k in out["base_top_level_keys"]:
        v = rep.get(k)
        print("  %-10s %-28s %s" % (side, k, json.dumps(v, ensure_ascii=False)[:160]))
