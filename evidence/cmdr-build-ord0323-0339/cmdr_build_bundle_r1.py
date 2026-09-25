"""Build the phone-served bundle from an authoritative generation, read-only against the repo.

Why an export instead of `npm run build` in D:/moodle/CityNexus: vite reads the WORKING tree, and the
working tree is shared with lanes that legitimately have `frontend/src` dirty.  Building there would put
another lane's unfinished bytes on the phone.  So the bundle is built from `git archive <tip>` and the
only thing borrowed from the repo is `node_modules` (a junction, never copied, never deleted through).

usage: python cmdr_build_bundle_r1.py --sha <40-hex> [--out LOGDIR]
"""
import argparse
import json
import os
import subprocess
import sys
import time

REPO = "D:/moodle/CityNexus"
ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"


def sh(cmd, cwd=None, timeout=1800, shell=False):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, shell=shell)
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", required=True)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    tag = a.tag or a.sha[:7]
    out_dir = os.path.join(ROOT, "_build_%s" % tag)
    fe = os.path.join(out_dir, "frontend")
    log = {"sha": a.sha, "tag": tag, "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "steps": []}

    rc, tree, _ = sh(["git", "-C", REPO, "rev-parse", a.sha + "^{tree}"])
    tree = tree.strip()
    log["live_tree"] = tree
    assert tree, "no tree for %s" % a.sha

    if os.path.isdir(out_dir):
        # A previous build's junction must be dropped with plain rmdir, never recursively, or the shared
        # node_modules of the real repo goes with it (worktree junction hazard, recorded).
        nm = os.path.join(fe, "node_modules")
        if os.path.isdir(nm):
            rc, _, err = sh(["cmd", "/c", "rmdir", nm.replace("/", "\\")], timeout=180)
            log["steps"].append({"step": "drop_old_junction", "rc": rc, "err": err.strip()[:200]})
        rc, _, err = sh(["cmd", "/c", "rmdir", "/s", "/q", out_dir.replace("/", "\\")], timeout=600)
        log["steps"].append({"step": "clean_old_export", "rc": rc, "err": err.strip()[:200]})
        if os.path.isdir(nm):
            raise SystemExit("ABORT: the junction survived rmdir, so the export cannot be swept with /s "
                             "without deleting the repo's real node_modules. Fix %s by hand." % nm)
    os.makedirs(out_dir, exist_ok=True)

    p = subprocess.run("git -C %s archive %s frontend | tar -x -C %s" % (REPO, a.sha, out_dir),
                       shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=900)
    log["steps"].append({"step": "archive", "rc": p.returncode, "err": (p.stderr or "").strip()[:300]})
    assert p.returncode == 0, "git archive failed"

    # The export must carry the very bytes the tip holds, or the build proves nothing about the line.
    # Both sides go through git's own hash-object: recomputing a blob sha1 in Python after reading the
    # file as TEXT silently disagrees with the repo under CRLF, which reads as a false alarm.
    proved = {}
    for rel in ["frontend/package.json", "frontend/vite.config.ts",
                "frontend/src/features/planning/PlanWithAiSheet.tsx",
                "frontend/src/components/ProductErrorBoundary.tsx",
                "frontend/src/features/inbox/JourneyInboxWorkbench.tsx",
                "frontend/src/features/setup/JourneyTrialSetup.tsx"]:
        _, want, _ = sh(["git", "-C", REPO, "rev-parse", "%s:%s" % (a.sha, rel)])
        path = os.path.join(out_dir, rel.replace("/", os.sep))
        _, have, _ = sh(["git", "-C", REPO, "hash-object", "--no-filters", path.replace("/", "\\")]) \
            if os.path.isfile(path) else ("", "", "")
        want, have = want.strip(), (have or "").strip()
        proved[rel] = {"export_blob": have or None, "tip_blob": want or None,
                       "identical": bool(want) and want == have}
    log["export_blob_equality"] = proved
    assert all(v["identical"] for v in proved.values()), (
        "export does not carry the tip's bytes: %s"
        % [k for k, v in proved.items() if not v["identical"]])

    nm = os.path.join(fe, "node_modules")
    rc, _, err = sh(["cmd", "/c", "mklink", "/J", nm.replace("/", "\\"),
                     "D:\\moodle\\CityNexus\\frontend\\node_modules"], timeout=300)
    log["steps"].append({"step": "junction_node_modules", "rc": rc, "out": err.strip()[:200]})
    assert os.path.isdir(nm), "junction not made"

    t0 = time.time()
    rc, so, se = sh(["npm", "run", "build"], cwd=fe, timeout=2400, shell=True)
    log["steps"].append({"step": "vite_build", "rc": rc, "secs": round(time.time() - t0, 1),
                         "tail": (so + se).strip().splitlines()[-14:]})
    dist = os.path.join(fe, "dist")
    idx = os.path.join(dist, "index.html")
    log["build"] = {"dist_exists": os.path.isdir(dist), "index_exists": os.path.isfile(idx)}
    if os.path.isfile(idx):
        import re
        html = open(idx, encoding="utf-8").read()
        log["build"]["asset_refs"] = re.findall(r'(?:src|href)="(/assets/[^"]+)"', html)
        log["build"]["index_bytes"] = len(html.encode("utf-8"))
    with open(os.path.join(ROOT, "_build_%s_info.json" % tag), "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=1)
    print("BUILD rc=%s dist=%s index=%s assets=%s" % (
        log["steps"][-1]["rc"] if rc else 0, log["build"]["dist_exists"], log["build"]["index_exists"],
        len(log["build"].get("asset_refs", []))))
    print("out=%s" % os.path.join(ROOT, "_build_%s_info.json" % tag))
    return 0 if rc == 0 and log["build"]["index_exists"] else 1


if __name__ == "__main__":
    sys.exit(main())
