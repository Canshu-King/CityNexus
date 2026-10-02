"""ORD-0500 r6: build the two faces this order is judged on, from one tree, and prove the tree back.

A second worktree would need its own node_modules (a hardlink copy that must be link-broken before
anything is written, and a junction that `worktree remove --force` would follow).  This order's base
and candidate differ in nine paths and nothing else, so the swap is done in THIS worktree:
check out the parent's bytes for exactly those nine, typecheck and build the base face, then check
out the commit's bytes again and prove every one of the nine matches the commit blob-by-blob,
hash-object-by-hash-object, with a clean `git status`.  Both faces get their entry asset name read
back out of the built index.html rather than from the name I hoped for.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
FRONTEND = os.path.join(WT, "frontend")
NODE = os.environ.get("CNX_PHONE_NODE", r"C:/Program Files/nodejs/node.exe")
# the generation is not baked in: a re-cut must re-measure without renaming the instrument, so the
# base comes from the environment and the labels are derived from it
BASE = os.environ.get("R6_BASE_TIP") or "dc9dc10fa769bd8c4f3712d9be0dacc2d54d29d5"
BASE_LABEL = "TIP_" + BASE[:8]
BASE_OUT = os.path.join(LANE, "faces/tip_" + BASE[:8])
CAND_LABEL = os.environ.get("R6_CAND_LABEL") or "O0500_R7"
# The swapped paths are COMPUTED from this ref's own write-set against the base tip, not typed.  A
# typed list is the same defect class as the citation lists that kept rotting: r14 deleted a
# dictionary row in a file the hard-coded nine did not contain, so both faces built from the same
# content and came out byte-identical, and the only tell was `clean_after_restore` coming back false.
BASE_TIP = os.environ.get("R6_BASE_TIP") or ""
WATCHED = ["backend/app/main.py", "contracts/openapi.yaml",
           "frontend/src/features/checkin/checkins.ts",
           "frontend/src/features/checkin/checkinCopy.ts",
           "frontend/src/features/checkin/footprint.css",
           "frontend/src/features/trip/TripItinerary.tsx",
           "backend/tests/test_qoder_ord0500_journey_refusal.py",
           "frontend/e2e/qoder-ord0500-checkin-truth.spec.ts",
           "frontend/playwright.ord0500-checkin.config.ts"]


def write_set():
    """Every non-`review/` path this ref changes against the base tip -- what the faces must differ on."""
    if not BASE_TIP:
        raise SystemExit("ABORT_NO_BASE_TIP -- set R6_BASE_TIP to the tip the candidate is measured on")
    rc, out = git("diff", "--name-only", "%s..HEAD" % BASE_TIP)
    if rc != 0:
        raise SystemExit("ABORT_WRITE_SET %s %s" % (rc, out[:200]))
    paths = sorted({l.strip() for l in out.splitlines() if l.strip()
                    and not l.startswith("review/")})
    if not paths:
        raise SystemExit("ABORT_EMPTY_WRITE_SET against %s -- there is no candidate to build" % BASE_TIP)
    missing = [p for p in WATCHED if p not in paths and git("rev-parse", "--verify", "--quiet",
                                                            "HEAD:%s" % p)[0] == 0
               and git("rev-parse", "--verify", "--quiet", "%s:%s" % (BASE_TIP, p))[0] == 0
               and git("rev-parse", "HEAD:%s" % p)[1] != git("rev-parse", "%s:%s" % (BASE_TIP, p))[1]]
    return paths, missing


PATHS, WATCHED_NOT_IN_WRITE_SET = [], []   # filled by main(): swap_to() reads the module global


def git(*args):
    p = subprocess.run(["git", "-C", WT] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=180)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def env_clean():
    e = {k: v for k, v in os.environ.items()
         if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY", "DEEPSEEK_API_KEY")}
    return e


def sha(path):
    b = open(path, "rb").read()
    return {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
            "local_sha1": hashlib.sha1(b).hexdigest()}


def state_of(rev):
    return {p: git("rev-parse", "--verify", "--quiet", "%s:%s" % (rev, p))[1] for p in PATHS}


def swap_to(rev):
    """Put the worktree at `rev` for exactly the nine paths.  Paths the revision does not carry (this
    order adds three files) are removed from index and worktree, so the base face really is the base
    tree and not the base tree plus my new modules.

    Refuses on a swapped path that is dirty.  `checkout HEAD -- <path>` is how the candidate face is
    restored, and with uncommitted edits in one of those paths it silently throws them away -- which it
    did on ORD-0500 r14: both faces built byte-identical and the only tell was `clean_after_restore`
    being false.  A candidate that is not committed has no face, so commit first.
    """
    index = {}
    for p in PATHS:
        rc, blob = git("rev-parse", "--verify", "--quiet", "%s:%s" % (rev, p))
        if rc == 0 and re.fullmatch(r"[0-9a-f]{40}", blob):
            r2, out = git("checkout", rev, "--", p)
            if r2 != 0:
                raise SystemExit("ABORT_SWAP %s %s %s" % (rev, p, out[:160]))
            index[p] = git("rev-parse", ":%s" % p)[1]
        else:
            r2, out = git("rm", "-f", "--quiet", "--", p)
            if r2 != 0 and os.path.exists(os.path.join(WT, p)):
                raise SystemExit("ABORT_REMOVE %s %s %s" % (rev, p, out[:160]))
            index[p] = "ABSENT_AT_%s" % rev[:12]
    return index


def worktree_hashes():
    return {p: git("hash-object", p)[1] for p in PATHS}


def typecheck_and_build(label, outdir):
    entry = {"label": label, "out_dir": outdir}
    os.makedirs(outdir, exist_ok=True)
    for cfg in ("tsconfig.check.json", "tsconfig.typecheck.json"):
        p = subprocess.run([NODE, "node_modules/typescript/bin/tsc", "-p", cfg, "--noEmit"],
                           cwd=FRONTEND, env=env_clean(), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=900)
        text = p.stdout.decode("utf-8", "replace")
        log = "run/r6_tsc_%s_%s.txt" % (label, cfg.replace(".json", ""))
        open(os.path.join(LANE, log), "w", encoding="utf-8").write(text)
        entry[cfg] = {"exit": p.returncode, "diagnostics_bytes": len(text.encode("utf-8")),
                      "head": text[:300], "log": log}
    p = subprocess.run([NODE, "node_modules/vite/bin/vite.js", "build", "--outDir", outdir,
                        "--emptyOutDir"], cwd=FRONTEND, env=env_clean(),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1800)
    text = p.stdout.decode("utf-8", "replace")
    log = "run/r6_build_%s.txt" % label
    open(os.path.join(LANE, log), "w", encoding="utf-8").write(text)
    entry["build"] = {"exit": p.returncode, "log": log,
                      "built_line": [l for l in text.splitlines() if "built in" in l][:1]}
    html = os.path.join(outdir, "index.html")
    if os.path.exists(html):
        t = open(html, encoding="utf-8").read()
        m = re.search(r'src="/assets/(index-[\w\-]+\.js)', t)
        css = re.search(r'href="/assets/(index-[\w\-]+\.css)', t)
        js = os.path.join(outdir, "assets", m.group(1)) if m else None
        entry["entry"] = {"entry_asset": m.group(1) if m else None,
                          "css_asset": css.group(1) if css else None,
                          "index": sha(html),
                          "bundle": sha(js) if js and os.path.exists(js) else None}
    return entry


def main():
    global PATHS, WATCHED_NOT_IN_WRITE_SET
    PATHS, WATCHED_NOT_IN_WRITE_SET = write_set()
    # checked ONCE, before any swap: swap_to() deliberately stages and un-stages these paths, so a
    # guard inside it would fire on its own work (the first version of this guard aborted mid-run and
    # left the tree at the base content).  What must be clean is the tree at the moment we start.
    rc, dirty = git("status", "--porcelain")
    if rc == 0 and dirty.strip():
        raise SystemExit("ABORT_UNCOMMITTED_CANDIDATE -- the worktree is dirty, so the candidate face "
                         "would be built from HEAD and silently drop the edit being measured: %s"
                         % dirty.strip()[:400])
    head = git("rev-parse", "HEAD")[1]
    report = {"tool": "build_faces_r6", "took_local": datetime.now().astimezone().isoformat(),
              "candidate_commit": head, "base_commit": BASE, "swapped_paths": len(PATHS),
              "faces": []}

    report["base_label"] = BASE_LABEL
    report["candidate_label"] = CAND_LABEL
    cand_index = swap_to(head)
    report["candidate_worktree_clean"] = git("status", "--porcelain")[1] == ""
    report["faces"].append(typecheck_and_build(CAND_LABEL,
                                               os.path.join(LANE, "faces/" + CAND_LABEL.lower())))

    base_index = swap_to(BASE)
    report["base_index_differs_from_candidate"] = sum(
        1 for p in PATHS if base_index[p] != cand_index[p])
    report["base_absent_paths"] = [p for p in PATHS if str(base_index[p]).startswith("ABSENT_AT_")]
    report["faces"].append(typecheck_and_build(BASE_LABEL, BASE_OUT))

    after = swap_to(head)
    restored = {p: {"commit_blob": git("rev-parse", "%s:%s" % (head, p))[1],
                    "index_blob": after[p], "worktree_blob": worktree_hashes()[p]} for p in PATHS}
    report["restore"] = {
        "every_path_matches_the_commit": all(
            v["commit_blob"] == v["index_blob"] == v["worktree_blob"] for v in restored.values()),
        "mismatches": [p for p, v in restored.items()
                       if not v["commit_blob"] == v["index_blob"] == v["worktree_blob"]],
        "worktree_clean_after_restore": git("status", "--porcelain")[1] == "",
        "detail": restored,
    }
    path = os.path.join(LANE, "evidence", "build_faces_r6.json")
    json.dump(report, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for f in report["faces"]:
        print("%s tsc=%s/%s build=%s entry=%s css=%s" % (
            f["label"], f.get("tsconfig.check.json", {}).get("exit"),
            f.get("tsconfig.typecheck.json", {}).get("exit"), f["build"]["exit"],
            (f.get("entry") or {}).get("entry_asset"), (f.get("entry") or {}).get("css_asset")),
            flush=True)
    print(json.dumps({k: v for k, v in report.items() if k != "faces"}, indent=2, ensure_ascii=False))
    print("WROTE " + path)
    return 0 if report["restore"]["every_path_matches_the_commit"] else 1


if __name__ == "__main__":
    sys.exit(main())
