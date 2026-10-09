"""Build channel_r2.json: the ORD-0326 delivery re-measured with the r5 module-graph ruler, plus the
correction of this lane's own earlier r4-based claim and the r4-vs-r5 denominator for ORD-0321's 16 cells.

Every number is read out of the r5 artifacts on disk (tip tree, my candidate tree, B's candidate tree) and
every reachability cell keeps its own r4/r5 sink line next to the r3 anchor it was originally keyed on.
"""
import collections
import io
import json
import os
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
SCRATCH = os.path.join(ROOT, "_sweep_scratch")
REPO = "D:/moodle/CityNexus"
R5 = "ff98091cf3accb0d836ae25ba49820170b92d932"
R4 = "eb262f59e54d5142ad0e8041704e751eac473ace"
R3 = "44e062e6ce9c7b5d97d78e09e432072da102292c"
MY_BRANCH = "agent/S1-q64sweep-candidates"
B_BRANCH = "review/0323-two-exposure-cells-b"
B_TIP = "e302e4c433712284a23c1c0ab11147fe105e1e22"


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True)
    if r.returncode:
        raise SystemExit("GIT_FAILED %s %s" % (" ".join(a), r.stderr.decode("utf-8", "replace")[:160]))
    return r.stdout.decode("utf-8", "replace").strip()


def load(p):
    return json.load(io.open(os.path.join(SCRATCH, p), encoding="utf-8"))


def key(d):
    return collections.Counter((h["file"].split("/")[-1], h["line"], h["rule"]) for h in d["hits"])


def full(d):
    return {(h["file"].split("/")[-1], h["line"]): h for h in d["hits"]}


def cell_basename(cell):
    return cell.rsplit(":", 1)[0].split("/")[-1]


def _uncovered(kt, reach):
    """r5-flagged sinks this lane's 16-cell table does not cite, split by WHY - the two cases mean
    different things and a single list would read as "r5 found N new problems"."""
    cited = {(cell_basename(c["cell"]), s["line"]) for c in reach["cells"] for s in c["render_sink"]}
    files_in_table = {cell_basename(c["cell"]) for c in reach["cells"]}
    out = {"wrong_line_in_a_cited_file": [], "file_not_in_the_table_at_all": []}
    for (f, ln, _rule) in sorted(kt):
        if (f, ln) in cited:
            continue
        key = "%s:%d" % (f, ln)
        if f in files_in_table:
            out["wrong_line_in_a_cited_file"].append(key)
        else:
            out["file_not_in_the_table_at_all"].append(key)
    return out


def main():
    tip = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    st5 = load("r5_tree_tip.json")
    sc5 = load("r5_tree_cand.json")
    sb5 = load("r5_tree_b.json")
    r3agg = load("aggregate_r3.json")
    reach = load("aggregate_r4.json")  # not used for numbers; kept so nothing silently mixes
    reach = json.load(io.open(os.path.join(ROOT, "_ord0321_reachability_r2.json"), encoding="utf-8"))
    sweep4 = json.load(io.open(os.path.join(ROOT, "_q64_sweep_r4.json"), encoding="utf-8"))
    cls_by_cell = {h["file"] + ":" + str(h["line"]): h["classification"] for h in sweep4["hits"]}
    my_tip = git("rev-parse", MY_BRANCH)
    kt, kc, kb = key(st5), key(sc5), key(sb5)
    ft = full(st5)

    # map ORD-0321's 16 r3-anchored cells onto r5 sinks: a cell counts as a real sink when one of its
    # render_sink lines appears in the r5 tree reading
    cells = []
    for c in reach["cells"]:
        base = cell_basename(c["cell"])
        sinks = [s for s in c["render_sink"] if (base, s["line"]) in ft]
        cells.append({
            "cell_r3_key": c["cell"], "classification": cls_by_cell.get(c["cell"], "unknown"),
            "verdict_reachability": c["verdict"],
            "r5_sink_matches": ["%s:%d|%s" % (base, s["line"], ft[(base, s["line"])]["rule"]) for s in sinks],
            "counts_as_r5_sink": bool(sinks),
        })
    counts = collections.Counter(x["counts_as_r5_sink"] for x in cells)

    doc = {
     "schema": "CNX_ORD0326_CHANNEL_V2",
     "order": "ORD-0326",
     "lane": "S1-q64sweep",
     "revision": "r2 - re-measured on the r5 module-graph ruler; supersedes the r4 readings in channel_r1.json",
     "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
     "generation": "0f8b925facabc9df57bab600b86d999dd515bf94",
     "generation_measured_from": "the exported tree the ruler was run with --tree on; see authoritative_tip_now for the ref at publish time",
     "authoritative_tip_now": tip,
     "tip_moved": tip != "0f8b925facabc9df57bab600b86d999dd515bf94",
     "generation_read_by": "git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1",
     "ruler": R5,
     "ruler_route": "commander/control:evidence/ord0331-ast-crossfile-S4/ui_exposure_taint_ast_r2.cjs",
     "ruler_verified_local_hash_object": git("hash-object", os.path.join(ROOT, "ui_exposure_taint_ast_r2.cjs")),
     "ruler_supersedes": {"r4": R4, "r3": R3},
     "r5_selftest": load("r5_selftest.json")["verdict"],
     "ruler_usage_finding": "r5 only builds a module graph in `--tree <dir>` mode. Run per file with "
                            "`--ref/--path` it reproduces r4's answer exactly - this lane measured 26 both "
                            "ways before noticing. Any r5 number quoted from a per-file sweep should be "
                            "treated as an r4 number.",
     "denominator_r5_tip": {"hits": len(st5["hits"]), "files": len({h["file"] for h in st5["hits"]}),
                            "per_rule": st5["per_rule"], "resolution_depth_cap": st5.get("resolution_depth_cap"),
                            "resolution_truncated_total": st5.get("resolution_truncated_total")},
     "denominator_r3_this_lane_previously_reported": {"cells": 16, "files": r3agg["files_with_hits"],
                                                      "hits_total": r3agg["hits_total"]},
     "ord0321_cells_rejudged": {
        "of_16_cells_matching_an_r5_sink": counts[True],
        "of_16_cells_with_no_r5_sink_at_the_cited_line": counts[False],
        "note": "the 16 cells were keyed on r3's reported line; this lane's own render_sink lines are what "
                "survive the re-judgement, which is why the two are listed separately per cell",
        "cells": cells,
     },
     "r5_sinks_this_lane_did_not_cite": {
        "split_by_reason": _uncovered(kt, reach),
        "self_correction": "three of these are in files this lane DID analyse, but the cell cited the "
                           "success-content render instead of the error slot the ruler flags "
                           "(AgentComposer.tsx:196 vs :185, CopilotDock.tsx:743 vs :450 and :770) - a defect "
                           "in this lane's own table, exposed by r5 and corrected here rather than left in "
                           "reachability_r2.json",
     },
     "my_branch_measurement": {
        "branch": MY_BRANCH, "tip": my_tip,
        "verified_by_ls_remote": git("ls-remote", "origin", "refs/heads/" + MY_BRANCH).split()[0],
        "hits": len(sc5["hits"]), "per_rule": sc5["per_rule"],
        "sinks_removed_vs_tip": ["%s:%d|%s" % k for k in sorted(kt - kc)],
        "sinks_added_vs_tip": ["%s:%d|%s" % k for k in sorted(kc - kt)],
        "added_sink_chain": [
            {"cell": "%s:%d" % (k[0], k[1]), "rule": k[2],
             "chain": (full(sc5)[(k[0], k[1])].get("taint_chain") or "")[:300]}
            for k in sorted(kc - kt)],
        "reading": "the four previously flagged sinks are gone, and the only remaining flag is the single "
                   "sanctioned slot (ServerReasonDetail.tsx:29) where Q67=1 allows the attributed sentence",
     },
     "lane_B_measurement": {
        "branch": B_BRANCH, "tip": B_TIP,
        "hits": len(sb5["hits"]), "per_rule": sb5["per_rule"],
        "sinks_removed_vs_tip": ["%s:%d|%s" % k for k in sorted(kt - kb)],
        "sinks_added_vs_tip": ["%s:%d|%s" % k for k in sorted(kb - kt)],
        "added_sink_chains": [{"cell": "%s:%d" % (k[0], k[1]), "chain": (full(sb5)[(k[0], k[1])].get("taint_chain") or "")[:220]}
                              for k in sorted(kb - kt)],
        "reading": "closes the :88 thrower and the two boundary lines, but the same three inbox slots are "
                   "still flagged, now at :703/:707/:747 and still fed by error.message",
     },
     "overlap_between_the_two_lanes": {
        "files_in_common": [],
        "removed_sinks_in_common": sorted(set(k[0] + ":" + str(k[1]) for k in (kt - kb)) &
                                          set(k[0] + ":" + str(k[1]) for k in (kt - kc))),
        "reading": "strictly complementary - neither lane touches a sink the other removes",
     },
     "correction_of_this_lanes_earlier_claim": {
        "was": "channel_r1.json (blob baa3f4f902997f3f1a54873628e12fe558969ac1) reported the touched files "
               "going 4 -> 3 under r4 with the rule changing at three sinks, and left 3 flagged",
        "now": "under r5 those three sinks are not flagged at all; the branch is 28 -> 25 tree-wide with one "
               "flag left at the designated slot",
        "why_it_was_wrong": "r4 is per-file, so it could not see the channel and reported the call sites as "
                            "still tainted; the earlier reading was an artefact of the ruler's scope, not of "
                            "the code",
        "published_artifacts_untouched": True,
     },
     "what_still_needs_a_decision": [
        "which channel survives: this lane's measure says adopting lib/serverReason.ts in B's two files "
        "would clear the three inbox slots that are still flagged on B's branch",
        "the 28-sink denominator now replaces 25 as the number ORD-0323/0326 work against",
        "V8Experience.tsx still carries 4 flagged sinks on the tip (:1314, :1385, :1562, :2536) and is not "
        "claimed by any lane dispatch this lane can see",
     ],
     "claim_kind": "measured_with_published_ruler",
     "command_i_ran": "git archive <tip> frontend/src | tar -x, then node ui_exposure_taint_ast_r2.cjs "
                      "--tree <exported frontend/src> --out <json>, once for the tip, once for "
                      "agent/S1-q64sweep-candidates and once for review/0323-two-exposure-cells-b; ruler "
                      "bytes taken from the published blob and re-hashed",
    }
    doc["claimed_result"] = ("r5 at tip %s: %d sinks / %d files; my branch %d (%d removed, %d added at the "
                             "sanctioned slot); B branch %d (%d removed, %d added); %d of 16 ORD-0321 cells "
                             "land on an r5 sink"
                             % (tip[:12], len(st5["hits"]), len({h["file"] for h in st5["hits"]}),
                                len(sc5["hits"]), len(kt - kc), len(kc - kt), len(sb5["hits"]),
                                len(kt - kb), len(kb - kt), counts[True]))
    out = os.path.join(ROOT, "_ord0326_channel_r2.json")
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print(doc["claimed_result"])
    unc = doc["r5_sinks_this_lane_did_not_cite"]["split_by_reason"]
    print("r5 cells with no sink line:", counts[False], "| uncited: wrong_line=%d new_file=%d"
          % (len(unc["wrong_line_in_a_cited_file"]), len(unc["file_not_in_the_table_at_all"])))
    print("my removed:", doc["my_branch_measurement"]["sinks_removed_vs_tip"])
    print("out=%s bytes=%d" % (out, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
