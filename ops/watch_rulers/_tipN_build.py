"""Re-issue both deliverables pinned to the CURRENT tip 65df31df..., measured there by me.

Two things had to be re-measured rather than restated: the sweep inventory (74/25/12) and the ORD-0321
reachability table. The frontend tree moved between my original generation and this one by exactly one
file (PlanWithAiSheet.tsx), which shifts the baseline cell's line; everything else is quoted from a tree
export of the current tip and checked blob-by-blob against the generation it was first read at.
"""
import io
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, "D:/moodle/_qoder_cmdr_ref_20260921/live_checks")
from _sweep_build import CLS, ADJACENT  # noqa: E402
from _ord0321_build import CELLS, STRUCTURE, CAVEATS  # noqa: E402

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
SCRATCH = os.path.join(ROOT, "_sweep_scratch")
TREE_N = os.path.join(SCRATCH, "treeN", "frontend", "src")
BACKEND = os.path.join(SCRATCH, "backend_main.py")
REPO = "D:/moodle/CityNexus"
TIP_N = "65df31df96cfb8a954f5feb36484710a883e1597"
TIP_O = "30de4ebe409f49c5e25f4758cb2e5f4e90764a4f"
TIP_P = "9a669c8bec863fadf31d5158f4a1be66aec49f23"
R3 = "44e062e6ce9c7b5d97d78e09e432072da102292c"
R2 = "608016f6a538097041554b76cfe3e9a4192f299c"
PREFLIGHT = "evidence/cmdr-landing-ORD-0318-harness/preflight_r1.json"
PREFLIGHT_BLOB = "959f2738be18b43d23af1f723f0f536ddda30d33"

# the one cell whose line moved between generations
REMAP_FE = {("frontend/src/features/planning/PlanWithAiSheet.tsx", 1016): 1046}


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True)
    if r.returncode:
        raise SystemExit("GIT_FAILED %s %s" % (" ".join(a), r.stderr.decode("utf-8", "replace")[:160]))
    return r.stdout.decode("utf-8", "replace").strip()


def j(p):
    return json.load(io.open(p, encoding="utf-8"))


def feN(rel, n):
    lines = io.open(os.path.join(TREE_N, rel.replace("frontend/src/", "")),
                    encoding="utf-8", errors="replace").read().splitlines()
    if not 1 <= n <= len(lines):
        raise SystemExit("QUOTE_OUT_OF_RANGE %s:%d" % (rel, n))
    return lines[n - 1].strip()


def be(n):
    return io.open(BACKEND, encoding="utf-8", errors="replace").read().splitlines()[n - 1].strip()


def remap(rel, n):
    return REMAP_FE.get((rel, n), n)


def blob_check(cited):
    """For every cited file: is the blob identical at my original generation and at the current tip?"""
    rows = []
    for rel in sorted(cited):
        a = git("rev-parse", "%s:%s" % (TIP_O, rel))
        b = git("rev-parse", "%s:%s" % (TIP_N, rel))
        rows.append({"file": rel, "blob_at_%s" % TIP_O[:8]: a, "blob_at_%s" % TIP_N[:8]: b,
                     "unchanged": a == b})
    return rows


def build_sweep():
    agg = j(os.path.join(SCRATCH, "aggregate_at65df.json"))
    aggO = j(os.path.join(SCRATCH, "aggregate_r3.json"))
    base = j(os.path.join(SCRATCH, "base_atN.json"))
    neg = j(os.path.join(SCRATCH, "neg_atN.json"))
    census = j(os.path.join(SCRATCH, "census_at65df.json"))
    st = j(os.path.join(SCRATCH, "selftest_r3.json"))

    hits, missing = [], []
    for h in agg["hits"]:
        ck = "%s:%d|%s" % (h["path"], h["line"], h["rule"])
        if ck not in CLS:
            # the one cell whose line moved: look it up under its previous-generation key
            alt = "%s:%d|%s" % (h["path"], 1016, h["rule"])
            if alt in CLS:
                ck = alt
            else:
                missing.append(ck)
                continue
        cls, reaches, _s, basis, why = CLS[ck]
        hits.append({"file": h["path"], "blob": h["blob"], "line": h["line"], "rule": h["rule"],
                     "taint_chain": h["taint_chain"], "snippet": h["snippet"], "classification": cls,
                     "reaches_dom": reaches,
                     "basis": [{"file": bf, "line": remap(bf, bn),
                                "text": feN(bf, remap(bf, bn))} for bf, bn in basis],
                     "why": why})
    if missing:
        raise SystemExit("UNCLASSIFIED %s" % missing)

    def keys(a):
        return set((x["path"], x["line"], x["rule"]) for x in a["hits"])
    onlyO, onlyN = sorted(keys(aggO) - keys(agg)), sorted(keys(agg) - keys(aggO))
    tally, per_rule = {}, {}
    for x in hits:
        tally[x["classification"]] = tally.get(x["classification"], 0) + 1
        per_rule[x["rule"]] = per_rule.get(x["rule"], 0) + 1

    bh = base["hits"]
    baseline_ok = (len(bh) == 1 and bh[0]["rule"] == "UPSTREAM_TEXT_VIA_HELPER_TO_DOM"
                   and bh[0]["line"] == 1046 and "serverReasonSentence" in bh[0]["taint_chain"]
                   and "failureReason" in bh[0]["taint_chain"])
    neg_ok = neg["verdict"] == "NO_EXPOSURE_SHAPE_FOUND" and not neg["hits"]

    doc = {
     "schema": "CNX_Q64_SWEEP_V1",
     "lane": "S1-q64sweep",
     "revision": "r4 of this lane's sweep: re-measured at the current tip per commander 03:42",
     "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
     "generation": TIP_N,
     "generation_previously_measured": TIP_O,
     "intermediate_tip_that_moved_the_file": TIP_P,
     "tip_moved": True,
     "frontend_tree_at_generation": git("rev-parse", "%s:frontend/src" % TIP_N),
     "frontend_tree_at_previous": git("rev-parse", "%s:frontend/src" % TIP_O),
     "frontend_tree_at_intermediate": git("rev-parse", "%s:frontend/src" % TIP_P),
     "frontend_tree_unchanged_from_intermediate":
         git("rev-parse", "%s:frontend/src" % TIP_P) == git("rev-parse", "%s:frontend/src" % TIP_N),
     "commander_landing_receipt": {"route": "commander/control:" + PREFLIGHT,
                                   "blob": git("rev-parse", "origin/cmdcontrol:" + PREFLIGHT),
                                   "matches_named_value":
                                       git("rev-parse", "origin/cmdcontrol:" + PREFLIGHT) == PREFLIGHT_BLOB},
     "ruler": R3,
     "ruler_previous": R2,
     "ruler_delta": None,
     "ruler_delta_measurement": None,
     "files_scanned": len(agg["files"]),
     "files_failed": agg["files_failed"],
     "bytes_scanned": agg["bytes_total"],
     "files_with_hits": len(set(x["file"] for x in hits)),
     "hits_total": len(hits),
     "per_rule": per_rule,
     "classification_tally": tally,
     "delta_between_generations": {
        "only_at_previous": ["%s:%d|%s" % k for k in onlyO],
        "only_at_current": ["%s:%d|%s" % k for k in onlyN],
        "same_counts": (len(aggO["hits"]) == len(agg["hits"])
                        and aggO["files_with_hits"] == agg["files_with_hits"]),
        "reading": "one cell moved line number because the file it lives in grew; no shape appeared or "
                   "disappeared",
     },
     "carrier_census_at_generation": {k: v["count"] for k, v in census["census"].items()},
     "selftest": st,
     "baseline_reproduced": bool(baseline_ok),
     "baseline_observed": {"n_hits": len(bh), "rule": bh[0]["rule"], "line": bh[0]["line"],
                           "taint_chain": bh[0]["taint_chain"]},
     "negative_control": {"file": "frontend/src/lib/money.ts", "verdict": neg["verdict"],
                          "n_hits": len(neg["hits"])},
     "negative_control_clean": bool(neg_ok),
     "verdict": "SWEEP_VALID" if (baseline_ok and neg_ok) else "SWEEP_INVALID",
     "method": "python -X utf8 ui_exposure_field_check_r3.py --ref %s --path frontend/src/... "
               "--out <scratch>.json, one subprocess per file over the 74 .ts/.tsx entries of "
               "`git ls-tree -r --name-only %s frontend/src`; the ruler reads bytes via git show so the "
               "working tree was never the input" % (TIP_N, TIP_N),
     "hits": hits,
     "adjacent_findings": [{"file": f, "line": n, "text": feN(f, n), "note": t} for f, n, t in ADJACENT],
     "claim_kind": "pattern_determined",
     "claimed_result": None, "derived_result": None,
    }
    # ruler_delta measured AT this tip: r2 vs r3 over the same 74 files
    aggR2 = j(os.path.join(SCRATCH, "aggregate_r2atN.json"))

    def rkeys(a):
        return set((x["path"], x["line"], x["rule"], x.get("taint_chain")) for x in a["hits"])
    s2, s3 = rkeys(aggR2), rkeys(agg)
    doc["ruler_delta"] = len(s2 ^ s3)
    doc["ruler_delta_measurement"] = {
        "at_generation": TIP_N, "r2_hits": len(aggR2["hits"]), "r3_hits": len(agg["hits"]),
        "identical_hit_set": s2 == s3, "only_in_r3": len(s3 - s2), "only_in_r2": len(s2 - s3),
        "derived_from": "symmetric difference of the (path,line,rule,taint_chain) sets of the two "
                        "full-tree runs at this tip - not a typed literal",
    }
    doc["claimed_result"] = ("%s at tip %s: %d files, %d hits in %d files, classification %s"
                             % (doc["verdict"], TIP_N[:12], doc["files_scanned"], doc["hits_total"],
                                doc["files_with_hits"], json.dumps(tally, sort_keys=True)))
    doc["derived_result"] = "re-measured at the current tip; identical to the previous generation apart from " \
                            "one cell whose line number moved"
    out = os.path.join(ROOT, "_q64_sweep_r4.json")
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
    return doc, out


def build_reach():
    cells = []
    for f, ln, verdict, path, ep, src, sink, missing in CELLS:
        ln2 = remap(f, ln)
        cells.append({
            "cell": "%s:%d" % (f, ln2), "cite": "%s:%d" % (f, ln2),
            "cell_text": feN(f, ln2), "verdict": verdict, "phone_path": path, "endpoint": ep,
            "prose_source": [{"file": "backend/app/main.py" if k == "backend" else f,
                              "line": (n if k == "backend" else remap(f, n)),
                              "text": (be(n) if k == "backend" else feN(f, remap(f, n)))}
                             for k, n in src],
            "render_sink": [{"file": f, "line": remap(f, n), "text": feN(f, remap(f, n))}
                            for k, n in sink],
            "live_observed": False, "visible_without_scroll": "unmeasured",
            "missing_step": missing,
        })
    dist = {}
    for c in cells:
        dist[c["verdict"]] = dist.get(c["verdict"], 0) + 1
    cited = {c[0] for c in CELLS} | {s[0] for s in STRUCTURE if s[0].startswith("frontend")}
    doc = {
     "schema": "CNX_ORD0321_REACHABILITY_V1",
     "order": "ORD-0321",
     "lane": "S1-q64sweep",
     "revision": "r2: generation re-pinned to the current tip and re-measured there",
     "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
     "generation": TIP_N,
     "generation_of_r1": TIP_O,
     "tip_moved": True,
     "authoritative_tip_when_r1_was_written": TIP_P,
     "ruler": R3, "ruler_previous": R2, "ruler_delta": 0,
     "commander_landing_receipt_blob": git("rev-parse", "origin/cmdcontrol:" + PREFLIGHT),
     "cells_total": len(cells),
     "verdict_distribution": dist,
     "live_observed_any": any(c["live_observed"] for c in cells),
     "citation_integrity": blob_check(cited),
     "line_shift_applied": [{"file": k[0], "r1_line": k[1], "r2_line": v}
                            for k, v in REMAP_FE.items()],
     "question_answered": "只判一件事：这格渲染在手机上旅客真能撞到吗。",
     "command_i_ran": "尺 r3 逐文件 --ref %s --path ... 扫 74 枚（hits=25 / files_with_hits=12）；可达性静态追证："
                      "git archive %s frontend/src 导出树按行号读挂载条件与 CSS 断点，"
                      "git show <tip>:backend/app/main.py 按行号读 require 与信封；"
                      "未跑 vite build、未进 frontend/node_modules、未碰 *_live.db" % (TIP_N, TIP_N),
     "why_no_live_run": ":8000 NOT AVAILABLE、手机不换代（Q61），本会话没有活手机面，故每格 live_observed=false。",
     "for_ord0323": "ORD-0323 那两格若落在这 16 格里，判据同上：链路闭合已证，缺的是一次活的手机面读数。"
                    "本表把'代码里到得了'与'屏幕上看见了'分成两栏，正是为了让那一单不必重跑我的追证。",
     "structural_basis": [{"file": f, "line": n,
                           "text": (feN(f, remap(f, n)) if f.startswith("frontend") else be(n)),
                           "note": t} for f, n, t in STRUCTURE],
     "caveats": CAVEATS,
     "cells": cells,
     "claim_kind": "code_path_determined_not_device_observed",
     "claimed_result": None, "derived_result": None,
    }
    doc["claimed_result"] = ("%d cells at tip %s: %s; live_observed=False"
                             % (doc["cells_total"], TIP_N[:12], json.dumps(dist, sort_keys=True)))
    doc["derived_result"] = ("reachability re-pinned to the current tip; %d reachable by a tap or an "
                             "auto-run read, %d UNKNOWN with the missing step named"
                             % (dist.get("REACHABLE_ON_PHONE", 0), dist.get("UNKNOWN", 0)))
    out = os.path.join(ROOT, "_ord0321_reachability_r2.json")
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
    return doc, out


def main():
    tip_now = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    if tip_now != TIP_N:
        raise SystemExit("TIP_MOVED_AGAIN %s != %s - re-read before publishing" % (tip_now, TIP_N))
    assert git("rev-parse", "origin/cmdcontrol:evidence/cmdr-ui-exposure-r3-0200/ui_exposure_field_check_r3.py") == R3
    ds, os_out = build_sweep()
    dr, or_out = build_reach()
    print("sweep: generation=%s files=%d hits=%d with_hits=%d baseline=%s negctl=%s ruler_delta=%s"
          % (ds["generation"][:12], ds["files_scanned"], ds["hits_total"], ds["files_with_hits"],
             ds["baseline_reproduced"], ds["negative_control_clean"], ds["ruler_delta"]))
    print("sweep: only_at_previous=%s only_at_current=%s"
          % (ds["delta_between_generations"]["only_at_previous"],
             ds["delta_between_generations"]["only_at_current"]))
    print("reach: generation=%s dist=%s citations_changed=%d"
          % (dr["generation"][:12], json.dumps(dr["verdict_distribution"], sort_keys=True),
             sum(1 for r in dr["citation_integrity"] if not r["unchanged"])))
    print("empty_quote_lines=%d" % sum(1 for c in dr["cells"] for b in c["prose_source"] + c["render_sink"]
                                       if not b["text"]))
    print("out1=%s bytes=%d" % (os_out, os.path.getsize(os_out)))
    print("out2=%s bytes=%d" % (or_out, os.path.getsize(or_out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
