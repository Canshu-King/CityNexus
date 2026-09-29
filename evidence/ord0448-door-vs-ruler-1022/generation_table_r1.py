"""Which cell is read by which ruler generation -- the table this order asks the repair to ship with.

The ORD-0448 loss is a generation difference, not a tree difference: on one identical export of one commit,
r7b reports `RecoveryRequiredPanel.tsx:...|UPSTREAM_TEXT_VIA_HELPER_TO_DOM` and r7b1/r7b4 do not. A repair
that only proves the cell comes back would still leave the reader unable to tell which of the OTHER cells the
new generation sees or loses, so this script reads every generation it is pointed at over the SAME export and
writes the per-cell provenance table: one row per cell key, one column per generation, plus the set
differences in both directions against the door-pinned r7b.

Usage: python generation_table_r1.py <rev> [generation-file ...]
Defaults to the tip the watch read at 11:44 and the four published generations.
"""
import glob
import hashlib
import io
import json
import os
import subprocess
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
REF = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
REPO = "D:/moodle/CityNexus"
NUL = chr(0).encode()
DEFAULT_REV = "c6a0ef6fdb5ca830c67720e43b8d59bc508ab0ef"
DEFAULT_GENS = ["ui_exposure_taint_ast_r7b.cjs", "ui_exposure_taint_ast_r7b1.cjs",
                "ui_exposure_taint_ast_r7b4.cjs"]
EXPORT = os.path.join(WORK, "_table_export")
# what the door pins, so a table that disagrees with the door is read as the door's, not as mine
DOOR_PINNED = "d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2"


def blob_of(path):
    raw = io.open(path, "rb").read()
    return hashlib.sha1(b"blob %d" % len(raw) + NUL + raw).hexdigest(), len(raw)


def extract(rev):
    if os.path.isdir(EXPORT):
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", EXPORT], timeout=600)
    os.makedirs(EXPORT, exist_ok=True)
    r = subprocess.run("git -C %s archive %s frontend/src | tar -x -C %s" %
                       (REPO, rev, EXPORT.replace("\\", "/")),
                       shell=True, capture_output=True, timeout=900)
    assert r.returncode == 0, r.stderr[:300]
    return len(glob.glob(os.path.join(EXPORT, "frontend", "src", "**", "*.ts*"), recursive=True))


def read_gen(name, base):
    path = os.path.join(REF, name)
    got, size = blob_of(path)
    js = os.path.join(WORK, "table_%s.json" % name.replace(".cjs", ""))
    r = subprocess.run(["node", path, "--tree", base, "--out", js], capture_output=True, timeout=1800,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert os.path.isfile(js), "ruler %s wrote no output rc=%s %s" % (
        name, r.returncode, r.stderr[:200].decode("utf-8", "replace"))
    doc = json.load(io.open(js, encoding="utf-8"))
    cells = {}
    for h in doc.get("hits", []):
        base_name = str(h["file"]).replace("\\", "/").split("/")[-1]
        cells["%s:%s|%s" % (base_name, h["line"], h.get("rule"))] = {
            "cell_id": h.get("cell_id"),
            "sink_shape": (h.get("structural") or {}).get("sink_shape")}
    return {"file": name, "bytes": size, "blob": got, "cells_total_reported": doc.get("cells_total"),
            "verdict": doc.get("verdict"), "parse_diagnostics_total": doc.get("parse_diagnostics_total"),
            "cells": cells}


def main():
    rev = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REV
    gens = sys.argv[2:] or DEFAULT_GENS
    tsx = extract(rev)
    base = os.path.join(EXPORT, "frontend", "src")
    out = {"rev": rev, "tsx_files": tsx, "door_pinned_ruler_blob": DOOR_PINNED, "generations": []}
    runs = []
    for name in gens:
        g = read_gen(name, base)
        out["generations"].append({k: v for k, v in g.items() if k != "cells"})
        runs.append(g)
    anchor = [g for g in runs if g["blob"] == DOOR_PINNED]
    out["anchor_is_the_door_pinned_ruler"] = bool(anchor)
    if not anchor:
        out["error"] = "no generation in this run is the blob the door pins; table is not door-comparable"
    else:
        a = anchor[0]
        table = {}
        for key in sorted(set(a["cells"]) | set().union(*[set(g["cells"]) for g in runs])):
            row = {"cell": key, "in_door_pinned": key in a["cells"]}
            for g in runs:
                row[g["file"]] = (g["cells"].get(key) or {}).get("cell_id") or "MISSING"
            table[key] = row
            for g in runs:
                if key in g["cells"] and key in a["cells"]:
                    row["cell_id_agrees_with_door_pinned_" + g["file"]] = (
                        g["cells"][key]["cell_id"] == a["cells"][key]["cell_id"])
        out["per_cell_provenance"] = table
        out["lost_from_newer_than_the_door_pinned_ruler"] = {
            g["file"]: sorted(set(a["cells"]) - set(g["cells"])) for g in runs if g is not a}
        out["only_the_door_pinned_ruler_misses"] = {
            g["file"]: sorted(set(g["cells"]) - set(a["cells"])) for g in runs if g is not a}
    io.open(os.path.join(WORK, "generation_table_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in out.items()
                      if k in ("rev", "tsx_files", "anchor_is_the_door_pinned_ruler",
                               "generations", "lost_from_newer_than_the_door_pinned_ruler",
                               "only_the_door_pinned_ruler_misses", "error")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
