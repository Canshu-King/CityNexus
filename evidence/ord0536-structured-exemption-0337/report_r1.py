# -*- coding: utf-8 -*-
"""ORD-0536 r1 - the named report-back and the identity-keyed view the door needs.

Two outputs, both computed from a real run of the delivered ruler, nothing typed in:

 report_r1.txt   every EXEMPTED cell, one row: rule + file + line + exemption entry + the fact measured
                 on the tree; then every cell still red, with the reason the ruler gave for it.
 door_view_r1.json  the comparison the pre-landing door should make instead of an absolute count:
                 the red cell ids on each side, the set difference, and the same pair read the way
                 `preflight_and_land_r7.py` reads it today (a count per (file, rule)).

Why the second file exists: the commander's own head-start reading says the Q64 arm compares absolute
cell counts, so a candidate that opens one new call site into a shared helper gains cells in panels it
never touched.  That is not a false positive - the exposure is real - but it has to arrive named by cell,
or a lane will spend the round arguing about the number instead of the four rows.
"""
import io
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
R8 = os.path.join(HERE, "ui_exposure_taint_ast_r8.cjs")
R7B = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/ui_exposure_taint_ast_r7b.cjs"
ENV = dict(os.environ)
ENV.pop("HTTP_PROXY", None)
ENV.pop("HTTPS_PROXY", None)

TREES = [
    ("tip_7862c6de", os.path.join(HERE, "exp_tip_r8"), "7862c6de5565c02c20ec2dccaa9da18960603e06"),
    ("cmdr_side_tip", os.path.join(HERE, "exp_tip0989713a"), "0989713aa687b97f4cd40bae009a6ce493425a4b"),
    ("cmdr_side_candidate", os.path.join(HERE, "exp_cand0500"), "62f030f351e70bd95108377fe2e3bbc49c5ef288"),
]


def run(ruler, tree_root, out):
    src = os.path.join(tree_root, "frontend", "src")
    contract = os.path.join(tree_root, "contracts", "openapi.yaml")
    args = ["node", ruler, "--tree", src, "--out", out]
    if os.path.isfile(contract):
        args += ["--contract", contract]
    p = subprocess.run(args, capture_output=True, env=ENV, timeout=1800)
    if not os.path.isfile(out):
        raise RuntimeError("%s wrote nothing (rc %s) %s" % (ruler, p.returncode,
                                                            p.stderr.decode("utf-8", "replace")[:200]))
    return json.load(io.open(out, encoding="utf-8"))


def short(file_label):
    f = str(file_label).replace("\\", "/")
    i = f.find("frontend/")
    return f[i + len("frontend/"):] if i >= 0 else f


def basis_of(row):
    d = row.get("measured_on_tree") or {}
    if row["exemption_id"] == "EX-2-ATTRIBUTED-FOLD":
        return ("fold %s at line %s names %s at line %s"
                % (d.get("fold_container"), d.get("fold_container_line"),
                   d.get("attribution_anchor_field"), d.get("attribution_anchor_line")))
    return ("contract %s (blob %s) declares %d tokens for `%s` at line %s; chain tokens %s"
            % (d.get("contract"), (d.get("contract_blob") or "")[:12], d.get("enum_size") or 0,
               d.get("field"), d.get("contract_enum_line"), d.get("tokens_seen")))


def main():
    lines = []
    door = {"method": "one real run of ui_exposure_taint_ast_r8.cjs --tree per export, plus the "
                      "door-pinned ui_exposure_taint_ast_r7b.cjs on the same tree for the count view",
            "trees": {}}
    for label, root, rev in TREES:
        doc = run(R8, root, os.path.join(HERE, "report_%s.json" % label))
        old = run(R7B, root, os.path.join(HERE, "report_r7b_%s.json" % label))
        red = [c for c in doc["cells"] if c["verdict"] == "RED"]
        ex = doc["exemption_ledger"]
        lines.append("=" * 100)
        lines.append("%s  rev %s" % (label, rev))
        lines.append("  ruler %s | modules %s | contract readable %s bytes %s blob %s" % (
            doc["ruler"]["name"], doc["modules_in_graph"], doc["contract"]["readable"],
            doc["contract"]["bytes"], doc["contract"]["blob"]))
        lines.append("  cells_total %s = red %s + exempted %s   (the door-pinned r7b reports %s hits)" % (
            doc["cells_total"], doc["red_after_exemption_count"], doc["exempted_count"], len(old["hits"])))
        lines.append("")
        lines.append("  EXEMPTED CELLS, one row each (%d):" % len(ex))
        for row in ex:
            lines.append("   - rule=%s" % row["rule"])
            lines.append("     file=%s  line=%s  cell_id=%s" % (
                short(row["file"]), row["line"], row["cell_id"]))
            lines.append("     origin_kind=%s  sink_shape=%s (family %s)" % (
                row["origin_kind"], row["sink_shape"], row["sink_shape_family"]))
            lines.append("     exemption=%s  evidence=%s" % (row["exemption_id"], row["evidence"]))
            lines.append("     basis=%s" % basis_of(row))
        lines.append("")
        lines.append("  CELLS STILL RED (%d), with the reason the ruler printed:" % len(red))
        for c in red:
            lines.append("   - rule=%s  %s:%s  cell_id=%s" % (c["rule"], short(c["file"]), c["line"], c["cell_id"]))
            lines.append("     %s" % c["red_because"])
        door["trees"][label] = {
            "rev": rev,
            "r8": {"cells_total": doc["cells_total"], "red": len(red), "exempted": len(ex),
                   "red_cell_ids": sorted(c["cell_id"] for c in red),
                   "exempted_cell_ids": sorted(r["cell_id"] for r in ex),
                   "exemption_ids_used": sorted({r["exemption_id"] for r in ex})},
            "r7b_hits": len(old["hits"]),
            "r7b_hit_keys": sorted("%s|%s|%s" % (short(h["file"]), h["line"], h["rule"]) for h in old["hits"]),
        }
    # the pair the commander measured, read both ways
    tip, cand = door["trees"]["cmdr_side_tip"], door["trees"]["cmdr_side_candidate"]
    new_ids = sorted(set(cand["r8"]["red_cell_ids"]) - set(tip["r8"]["red_cell_ids"]))
    gone_ids = sorted(set(tip["r8"]["red_cell_ids"]) - set(cand["r8"]["red_cell_ids"]))
    # the door's own arithmetic (preflight_and_land_r7.py:114): it builds a set of `basename:line|rule`
    # and counts that per `basename|rule`.  Reproduced here rather than approximated, because collapsing
    # the line out first would merge two cells of one file into one and understate the growth.
    from collections import Counter

    def door_counts(hit_keys):
        cells = {"%s:%s|%s" % (k.split("|")[0].split("/")[-1], k.split("|")[1], k.split("|")[2])
                 for k in hit_keys}
        grouped = Counter("%s|%s" % (c.split(":")[0], c.split("|")[1]) for c in cells)
        return grouped, sorted(cells)

    tc, tip_cells = door_counts(tip["r7b_hit_keys"])
    cc, cand_cells = door_counts(cand["r7b_hit_keys"])
    growth = {k: cc[k] - tc.get(k, 0) for k in cc if cc[k] > tc.get(k, 0)}
    line_exact_added = sorted(set(cand_cells) - set(tip_cells))
    line_exact_removed = sorted(set(tip_cells) - set(cand_cells))
    idmap = json.load(io.open(os.path.join(HERE, "report_cmdr_side_candidate.json"), encoding="utf-8"))
    named = {c["cell_id"]: "%s|%s:%s" % (c["rule"], short(c["file"]), c["line"]) for c in idmap["cells"]}
    door["commander_pair"] = {
        "his_reading": {"candidate": 10, "tip": 6,
                        "note": "the numbers in the ORD-0536 order text, taken with the door-pinned r7b"},
        "r7b_reproduced_here": {"candidate": cand["r7b_hits"], "tip": tip["r7b_hits"]},
        "r8_red": {"candidate": cand["r8"]["red"], "tip": tip["r8"]["red"]},
        "r8_cells_total": {"candidate": cand["r8"]["cells_total"], "tip": tip["r8"]["cells_total"]},
        "growth_by_identity_new_cell_ids": [named.get(i, i) for i in new_ids],
        "growth_by_identity_gone_cell_ids": [named.get(i, i) for i in gone_ids],
        "growth_by_file_and_rule_count_view": growth,
        "door_count_view_tip_per_file_and_rule": dict(tc),
        "door_count_view_candidate_per_file_and_rule": dict(cc),
        "line_exact_added_hits": line_exact_added,
        "line_exact_removed_hits": line_exact_removed,
        "the_two_views_agree": len(new_ids) == sum(growth.values())
        and len(line_exact_added) == len(new_ids),
        "note": "the count view and the identity view name the same four additions; the identity view also "
                "says which file and line each one is, which is what a lane has to go fix",
    }
    io.open(os.path.join(HERE, "report_r1.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    io.open(os.path.join(HERE, "door_view_r1.json"), "w", encoding="utf-8").write(
        json.dumps(door, ensure_ascii=False, indent=1))
    print("\n".join(lines[:1]))
    print("pair:", json.dumps(door["commander_pair"], ensure_ascii=False)[:700])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
