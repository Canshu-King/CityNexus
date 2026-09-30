"""ORD-0510: what the two rulers see before and after the 收藏 entry, on the same tip.

This is the measurement ORD-0444's ruling turns on: that ruling says the exposure ruler counts the
*import edge*, not the class, which is why the collection copy lives in the feature instead of in
`frontend/src/lib/displayVocabulary.ts`.  ORD-0510 adds a new import edge -- `features/trip` now pulls
`features/collections` -- so the claim "this order's growth is zero" has to be re-measured on these
bytes rather than inherited from the previous round.  Same for the copy-tier ruler: this order adds
sentences, and a sentence that duplicates a dictionary key is a different defect from one that does not.

Compared per generation, on two trees that differ only by this delivery:
  * the door-pinned ruler and the newest one -- cell sets, `cells_total`, and whether anything appeared;
  * `tools/cnx_copy_tiers_r1.py` as it stands on the tip -- its HARDCODED_FALLBACK row list.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0510"
REF = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
NUL = chr(0).encode()
TREES = {"before_tip_be0ff": os.path.join(WORK, "tip_be0ff", "frontend"),
         "after_ord0510": r"D:\moodle\_qoder_lane_S4_0926\wt0510\frontend"}
GENS = [("r7b", "ui_exposure_taint_ast_r7b.cjs"), ("r7b4", "ui_exposure_taint_ast_r7b4.cjs")]
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"


def blob_of(path):
    raw = io.open(path, "rb").read()
    return hashlib.sha1(b"blob %d" % len(raw) + NUL + raw).hexdigest(), len(raw)


def run_ruler(name, tree, out):
    r = subprocess.run(["node", os.path.join(REF, name), "--tree", tree, "--out", out],
                       capture_output=True, timeout=1800, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert os.path.isfile(out), "rc=%s %s" % (r.returncode, r.stderr[:300])
    return json.load(io.open(out, encoding="utf-8"))


def cells(doc, key):
    out = set()
    for rec in doc.get(key, []):
        line = rec.get("line")
        if line is None:
            line = rec.get("file_line")
        out.add("%s:%s|%s" % (rec.get("file"), line, rec.get("rule")))
    return out


ROW = re.compile(r"\s+([AB]) (T\d) \[([A-Z_]+) *\] (.+?):(\d+) (.*)  <-")


def main():
    out = {"trees": TREES, "rulers": {}, "exposure": {}, "copy_ruler": {}}
    for tag, name in GENS:
        b, n = blob_of(os.path.join(REF, name))
        out["rulers"][tag] = {"file": name, "blob": b, "bytes": n}
    for tag, name in GENS:
        side = {}
        for label, tree in TREES.items():
            js = os.path.join(WORK, "exp_%s_%s.json" % (label, tag))
            doc = run_ruler(name, tree, js)
            hits, fold = cells(doc, "hits"), cells(doc, "attributed_in_fold")
            side[label] = {"receipt": os.path.basename(js), "cells_total_reported": doc.get("cells_total"),
                           "hits": len(hits), "fold": len(fold), "union": len(hits | fold),
                           "parse_diagnostics_total": doc.get("parse_diagnostics_total"),
                           "_u": hits | fold}
        a, b = side["before_tip_be0ff"], side["after_ord0510"]
        out["exposure"][tag] = {
            "before": {k: v for k, v in a.items() if k != "_u"},
            "after": {k: v for k, v in b.items() if k != "_u"},
            "appeared": sorted(b["_u"] - a["_u"]),
            "disappeared": sorted(a["_u"] - b["_u"]),
            "union_equal": a["_u"] == b["_u"],
        }
    ruler_src = subprocess.run(["git", "-C", r"D:/moodle/CityNexus", "show",
                                "be0ffee216c7d24e48652427d290da848a9195cf:tools/cnx_copy_tiers_r1.py"],
                               capture_output=True, timeout=600)
    assert ruler_src.returncode == 0, ruler_src.stderr[:200]
    path = os.path.join(WORK, "cnx_copy_tiers_r1_tip.py")
    io.open(path, "wb").write(ruler_src.stdout)
    out["copy_ruler"]["ruler"] = {"path": "tools/cnx_copy_tiers_r1.py at the tip",
                                  "blob": blob_of(path)[0], "bytes": os.path.getsize(path)}
    rows = {}
    for label, tree in TREES.items():
        txt = os.path.join(WORK, "copy_%s.txt" % label)
        r = subprocess.run([PY, path, "--i18n", os.path.join(tree, "src", "i18n", "LocaleContext.tsx"),
                            "--src", os.path.join(tree, "src"), "--list-fallbacks"],
                           capture_output=True, timeout=1200, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        io.open(txt, "wb").write(r.stdout)
        got = []
        for line in io.open(txt, encoding="utf-8", errors="replace"):
            m = ROW.match(line)
            if m:
                got.append((m.group(1) + m.group(2), m.group(3).strip(),
                            os.path.basename(m.group(4)), m.group(6).strip()))
        rows[label] = got
        out["copy_ruler"][label] = {"exit": r.returncode, "rows": len(got), "report": os.path.basename(txt)}
    out["copy_ruler"]["rows_equal_modulo_nothing"] = rows["before_tip_be0ff"] == rows["after_ord0510"]
    out["copy_ruler"]["appeared"] = [list(x) for x in
                                     set(rows["after_ord0510"]) - set(rows["before_tip_be0ff"])]
    out["copy_ruler"]["disappeared"] = [list(x) for x in
                                        set(rows["before_tip_be0ff"]) - set(rows["after_ord0510"])]
    io.open(os.path.join(WORK, "rulers_before_after_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    for tag in out["exposure"]:
        e = out["exposure"][tag]
        print("%s union %s->%s equal=%s appeared=%d disappeared=%d"
              % (tag, e["before"]["union"], e["after"]["union"], e["union_equal"],
                 len(e["appeared"]), len(e["disappeared"])))
        for x in (e["appeared"] + e["disappeared"])[:4]:
            print("    %s" % x)
    print("copy rows %s->%s equal=%s appeared=%s" % (
        out["copy_ruler"]["before_tip_be0ff"]["rows"], out["copy_ruler"]["after_ord0510"]["rows"],
        out["copy_ruler"]["rows_equal_modulo_nothing"], out["copy_ruler"]["appeared"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
