"""Sweep driver: invokes the Q64 r2 ruler as a subprocess on every frontend .ts/.tsx file at the tip.

Does not import the ruler and does not reimplement its patterns. Aggregates the per-run JSON
artifacts the ruler itself wrote, so every count in the deliverable is derived from artifacts.
"""
import io
import json
import os
import subprocess
import sys

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
SCRATCH = os.path.join(ROOT, "_sweep_scratch")
RULER = os.path.join(ROOT, "ui_exposure_field_check_r2.py")
REPO = "D:/moodle/CityNexus"


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True)
    if r.returncode:
        raise SystemExit("GIT_FAILED %s %s" % (" ".join(a), r.stderr.decode("utf-8", "replace")[:200]))
    return r.stdout.decode("utf-8", "replace").strip()


def main():
    tip = sys.argv[1]
    ruler = os.path.join(ROOT, sys.argv[2]) if len(sys.argv) > 2 else RULER
    tag = sys.argv[3] if len(sys.argv) > 3 else "r2"
    ROUTE = sys.argv[4]
    listing = [ln.strip() for ln in io.open(os.path.join(ROOT, "_sweep_scratch_filelist.txt"), encoding="utf-8")
               if ln.strip()]
    files = []
    all_hits = []
    failed = []
    for i, path in enumerate(listing):
        blob = git("rev-parse", "%s:%s" % (tip, path))
        size = int(git("cat-file", "-s", blob))
        out = os.path.join(SCRATCH, "run_%s_%03d.json" % (tag, i))
        if os.path.exists(out):
            os.remove(out)
        cmd = [sys.executable, "-X", "utf8", ruler, "--ref", tip, "--path", path, "--out", out]
        proc = subprocess.run(cmd, capture_output=True)
        entry = {"path": path, "blob": blob, "bytes": size, "exit": proc.returncode,
                 "artifact": os.path.basename(out), "n_hits": None, "verdict": None, "label_ok": False}
        if proc.returncode != 0 or not os.path.exists(out):
            entry["error"] = proc.stderr.decode("utf-8", "replace")[:200]
            failed.append(path)
            files.append(entry)
            continue
        d = json.load(io.open(out, encoding="utf-8"))
        want_label = "%s:%s" % (tip[:12], path)
        entry["label_ok"] = (d.get("targets_scanned") == [want_label])
        if not entry["label_ok"]:
            failed.append(path)
        entry["n_hits"] = len(d["hits"])
        entry["verdict"] = d["verdict"]
        for h in d["hits"]:
            all_hits.append({
                "path": path,
                "blob": blob,
                "line": h["line"],
                "rule": h["rule"],
                "snippet": h["snippet"][:120],
                "taint_chain": h.get("taint_chain"),
                "run_artifact": os.path.basename(out),
            })
        files.append(entry)
    agg = {
        "schema": "CNX_Q64_SWEEP_AGGREGATE_V1",
        "tip": tip,
        "tip_short": tip[:12],
        "ruler": git("rev-parse", "%s:%s" % ("origin/commander/control", ROUTE)),
        "ruler_route": ROUTE,
        "ruler_local_git_hash": subprocess.run(["git", "hash-object", ruler], capture_output=True,
                                               cwd=ROOT).stdout.decode().strip(),
        "ruler_local_basename": os.path.basename(ruler),
        "files_scanned": len(files),
        "files_failed": len(failed),
        "failed_paths": failed,
        "bytes_total": sum(f["bytes"] for f in files),
        "hits_total": len(all_hits),
        "files_with_hits": len(set(h["path"] for h in all_hits)),
        "per_rule": {r: sum(1 for h in all_hits if h["rule"] == r)
                     for r in sorted(set(h["rule"] for h in all_hits))},
        "files": files,
        "hits": all_hits,
    }
    io.open(os.path.join(SCRATCH, "aggregate_%s.json" % tag), "w", encoding="utf-8", newline="\n").write(
        json.dumps(agg, ensure_ascii=False, indent=1))
    print("files=%d failed=%d hits=%d files_with_hits=%d bytes=%d ruler=%s"
          % (agg["files_scanned"], agg["files_failed"], agg["hits_total"],
             agg["files_with_hits"], agg["bytes_total"], agg["ruler"]))
    print("per_rule=%s" % json.dumps(agg["per_rule"]))
    return 0 if not failed else 5


if __name__ == "__main__":
    sys.exit(main())
