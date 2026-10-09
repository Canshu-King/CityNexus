"""Sweep the whole frontend tree with the r4 AST ruler at the current tip.

Same discipline as the r2/r3 driver: invoke the published ruler as a subprocess once per file, never import
it, never reimplement its patterns. Unlike the r3 sweep this one keeps r4's own `sink` field and
per_file counters, because the point of re-measuring is the sink-bound denominator r4 introduced.
"""
import io
import json
import os
import subprocess
import sys

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
SCRATCH = os.path.join(ROOT, "_sweep_scratch")
AGG_OUT = os.path.join(SCRATCH, "aggregate_%s.json" % (sys.argv[5] if len(sys.argv) > 5 else "r4"))
RULER = os.path.join(ROOT, sys.argv[2] if len(sys.argv) > 2 else "ui_exposure_taint_ast_r1.cjs")
REPO = "D:/moodle/CityNexus"
R4_BLOB = sys.argv[3] if len(sys.argv) > 3 else "eb262f59e54d5142ad0e8041704e751eac473ace"


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True)
    if r.returncode:
        raise SystemExit("GIT_FAILED %s %s" % (" ".join(a), r.stderr.decode("utf-8", "replace")[:160]))
    return r.stdout.decode("utf-8", "replace").strip()


def main():
    tip = sys.argv[1]
    listing = [ln.strip() for ln in io.open(os.path.join(ROOT, "_sweep_scratch_filelist.txt"),
                                            encoding="utf-8") if ln.strip()]
    assert git("rev-parse", "origin/cmdcontrol:" + (sys.argv[4] if len(sys.argv) > 4 else "evidence/ord0322-ast-taint-S4/ui_exposure_taint_ast_r1.cjs")) == R4_BLOB
    assert git("hash-object", RULER) == R4_BLOB, "local ruler bytes differ from the published blob"
    files, hits, failed = [], [], []
    for i, path in enumerate(listing):
        blob = git("rev-parse", "%s:%s" % (tip, path))
        out = os.path.join(SCRATCH, "run%s_%03d.json" % (sys.argv[5] if len(sys.argv) > 5 else "r4", i))
        if os.path.exists(out):
            os.remove(out)
        p = subprocess.run(["node", RULER, "--ref", tip, "--path", path, "--out", out], capture_output=True)
        if p.returncode or not os.path.exists(out):
            failed.append(path)
            files.append({"path": path, "exit": p.returncode, "n_hits": None})
            continue
        d = json.load(io.open(out, encoding="utf-8"))
        pf = (d.get("per_file") or [{}])[0]
        graph = pf.get("graph") or {}
        files.append({"path": path, "blob": blob, "artifact": os.path.basename(out),
                      "n_hits": len(d["hits"]), "verdict": d["verdict"],
                      "sinks": graph.get("sinks"), "bindings": graph.get("bindings"),
                      "functions": graph.get("functions"), "call_sites": graph.get("call_sites"),
                      "depth_cut_lookups": pf.get("depth_cut_lookups"),
                      "parse_diagnostics": pf.get("parse_diagnostics")})
        for h in d["hits"]:
            hits.append({"path": path, "blob": blob, "line": h["line"], "rule": h["rule"],
                         "sink": h.get("sink"), "snippet": (h.get("snippet") or "")[:120],
                         "taint_chain": h.get("taint_chain")})
    agg = {
        "schema": "CNX_Q64_R4_SWEEP_AGGREGATE_V1",
        "tip": tip, "ruler": R4_BLOB,
        "files_scanned": len(files), "files_failed": len(failed), "failed_paths": failed,
        "hits_total": len(hits),
        "files_with_hits": len(set(h["path"] for h in hits)),
        "per_rule": {r: sum(1 for h in hits if h["rule"] == r)
                     for r in sorted(set(h["rule"] for h in hits))},
        "sinks_distinct": len(set((h["path"], h["line"]) for h in hits)),
        "sink_kinds": {k: sum(1 for h in hits if (h.get("sink") or "unknown") == k)
                       for k in sorted(set((h.get("sink") or "unknown") for h in hits))},
        "files_with_sinks": sum(1 for f in files if (f.get("sinks") or 0) > 0),
        "hit_files_with_zero_sinks":
            sorted({h["path"] for h in hits} & {f["path"] for f in files if (f.get("sinks") or 0) == 0}),
        "depth_cut_lookups_sum_over_files": sum(f.get("depth_cut_lookups") or 0 for f in files),
        "resolution_depth_cap_seen": None,
        "files": files, "hits": hits,
    }
    caps = [json.load(io.open(os.path.join(SCRATCH, f["artifact"]), encoding="utf-8")).get("resolution_depth_cap")
            for f in files if f.get("artifact")]
    agg["resolution_depth_cap_seen"] = sorted({str(c) for c in caps})
    io.open(os.path.join(SCRATCH, AGG_OUT), "w", encoding="utf-8", newline="\n").write(
        json.dumps(agg, ensure_ascii=False, indent=1))
    print("files=%d failed=%d hits=%d files_with_hits=%d distinct_sinks=%d"
          % (agg["files_scanned"], agg["files_failed"], agg["hits_total"], agg["files_with_hits"],
             agg["sinks_distinct"]))
    print("per_rule=%s" % json.dumps(agg["per_rule"], sort_keys=True))
    print("sink_kinds=%s" % json.dumps(agg["sink_kinds"], sort_keys=True))
    print("hit_files_with_zero_sinks=%s depth_cut_sum=%s cap=%s"
          % (agg["hit_files_with_zero_sinks"], agg["depth_cut_lookups_sum_over_files"],
             agg["resolution_depth_cap_seen"]))
    return 0 if not failed else 5


if __name__ == "__main__":
    sys.exit(main())
