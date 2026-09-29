"""Is the cell lost, or re-filed? Compare hits UNION attributed_in_fold across generations.

`cells_total` counts `hits` only. A cell the ruler reads and then exonerates through an attribution anchor
lives in `attributed_in_fold` instead, so a generation difference of "12 vs 11" is only a lost ability if the
missing one is absent from BOTH lists. This computes the union per generation, takes the differences against
the door-pinned r7b in both directions, and names where each cell is filed in each generation.
"""
import io
import json
import os
import subprocess
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
REF = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
GENS = ["r7b", "r7b1", "r7b4"]
ANCHOR = "r7b"
TARGET = "RecoveryRequiredPanel.tsx"


def key(file_name, line, rule):
    return "%s:%s|%s" % (str(file_name).replace("\\", "/").split("/")[-1], line, rule)


def load(tag):
    d = json.load(io.open(os.path.join(WORK, "table_ui_exposure_taint_ast_%s.json" % tag), encoding="utf-8"))
    hits = {}
    for h in d.get("hits", []):
        hits[key(h["file"], h["line"], h.get("rule"))] = {
            "filed": "hits", "cell_id": h.get("cell_id"),
            "sink_shape": (h.get("structural") or {}).get("sink_shape")}
    folded = {}
    for f in d.get("attributed_in_fold", []):
        k = key(f["file"], f.get("file_line"), f.get("rule"))
        folded[k] = {"filed": "attributed_in_fold", "anchor_field": f.get("attribution_anchor_field"),
                     "anchor_line": f.get("attribution_anchor_line"),
                     "fold_container": f.get("fold_container"),
                     "fold_container_line": f.get("fold_container_line"),
                     "snippet": f.get("snippet")}
    both = {}
    for k, v in list(hits.items()) + list(folded.items()):
        both.setdefault(k, []).append(v)
    return d, hits, folded, both


def main():
    out = {"generations": {}, "union_keys": {}, "per_generation_union_size": {}}
    store = {}
    for tag in GENS:
        d, hits, folded, both = load(tag)
        out["generations"][tag] = {
            "cells_total_reported": d.get("cells_total"), "hits": len(hits),
            "attributed_in_fold_count": d.get("attributed_in_fold_count"),
            "fold_without_anchor_count": d.get("fold_without_anchor_count"),
            "contract_exempted_count": d.get("contract_exempted_count"),
            "contract_blocked_count": d.get("contract_blocked_count"),
            "parse_diagnostics_total": d.get("parse_diagnostics_total"),
            "ruler_blob": d["ruler"].get("blob") or d["ruler"].get("computed_blob"),
            "union_size": len(both)}
        store[tag] = both
        for k in both:
            out["union_keys"].setdefault(k, {})[tag] = [v["filed"] for v in both[k]]
    a = set(store[ANCHOR])
    out["differences_against_the_door_pinned_r7b"] = []
    for tag in GENS:
        if tag == ANCHOR:
            continue
        s = set(store[tag])
        out["differences_against_the_door_pinned_r7b"].append({
            "generation": tag, "union_lost": sorted(a - s), "union_gained": sorted(s - a),
            "union_equal": a == s,
            "refiled_differently": {k: out["union_keys"][k] for k in sorted(a | s)
                                    if len(set(tuple(v) for v in out["union_keys"][k].values())) > 1}})
    target_keys = sorted(k for k in store[ANCHOR] if k.startswith(TARGET))
    out["recovery_panel_cells_by_generation"] = {k: {tag: store[tag].get(k) for tag in GENS}
                                                 for k in target_keys}
    st = subprocess.run(["node", os.path.join(REF, "ui_exposure_taint_ast_r7b4.cjs"), "--selftest"],
                        capture_output=True, timeout=1800,
                        env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    txt = (st.stdout or b"").decode("utf-8", "replace")
    doc = None
    try:
        doc = json.loads(txt)
    except ValueError:
        pass
    arms = (doc or {}).get("selftest", {}).get("arms") or (doc or {}).get("arms") or []
    out["r7b4_selftest"] = {"exit": st.returncode, "verdict": (doc or {}).get("verdict"),
                            "arms_total": len(arms),
                            "arms_failed": [a.get("name") for a in arms if a.get("pass") is False],
                            "r7b1_arms": sorted([a.get("name") for a in arms
                                                 if str(a.get("name", "")).startswith("R7B1")])}
    out["reading"] = (
        "no ability lost: hits UNION attributed_in_fold is the same set in every generation read here; "
        "the cell the ORD-0448 block called missing is read by r7b1 and r7b4 and filed in "
        "attributed_in_fold with its anchor named"
        if all(x["union_equal"] for x in out["differences_against_the_door_pinned_r7b"])
        else "something IS lost: the union differs; name it before writing any repair")
    io.open(os.path.join(WORK, "no_lost_ability_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: out[k] for k in ("generations", "differences_against_the_door_pinned_r7b",
                                          "r7b4_selftest", "reading")}, ensure_ascii=False, indent=1)[:3000])
    print("recovery keys:", json.dumps(out["recovery_panel_cells_by_generation"],
                                       ensure_ascii=False)[:900])
    return 0


if __name__ == "__main__":
    sys.exit(main())
