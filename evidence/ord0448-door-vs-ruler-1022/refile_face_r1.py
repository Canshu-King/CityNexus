"""Measure the face the door cannot see: adding a provenance label moves a cell out of `hits`, so `cells_total` falls.

The ruler's own arms say a shipped-shape cell is `hits 0 / folded 1` beside a provenance label and `hits 1 /
folded 0` with that label deleted. That is an *expectation* in the ruler's selftest. This turns it into a
measurement the door can be judged against: one directory, one file name, two spellings of the same element,
read with the door-pinned ruler and with the newest one, and the number the door would print (`cells_total`,
which is what its growth arm compares) reported next to the number that does not move (hits + folded).
"""
import hashlib
import io
import json
import os
import subprocess
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
REF = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
FX = os.path.join(WORK, "_refile_fx")
NUL = chr(0).encode()
def ruler_server_prefix():
    """Lift `R7_SERVER` out of the ruler's own bytes by running THAT text in node, so the poison source in my
    fixture is byte-for-byte the one the ruler's acceptance arms use, not my paraphrase of it."""
    src = io.open(os.path.join(REF, "ui_exposure_taint_ast_r7b4.cjs"), encoding="utf-8").read()
    stmt = src[src.index("const R7_SERVER"):src.index("const R7_EXC")].strip()
    script = os.path.join(WORK, "_lift_r7_server.cjs")
    io.open(script, "w", encoding="utf-8", newline="\n").write(
        stmt + chr(10) + "process.stdout.write(JSON.stringify(R7_SERVER));" + chr(10))
    r = subprocess.run(["node", script], capture_output=True, timeout=300,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr[:200]
    os.remove(script)
    return json.loads(r.stdout.decode("utf-8"))


BODY = 'export function X({ notice }: { notice: { quote: string | null; field: string } }) {\n' \
       '  const sentence = serverReasonSentence(body);\n' \
       '  return <details data-testid="recovery-technical"><summary>x</summary>'
TAIL = '<code data-testid="recovery-reason"' \
       '{...(notice.field ? { "data-cnx-field": notice.field } : {})}>{sentence}</code></details>;\n}\n'
LABEL = '<span data-testid="recovery-detail-kind">{notice.field === "server" ? t("recovery.serverReason")' \
        ' : t("recovery.deviceReason")}</span>'
GENS = [("r7b", "ui_exposure_taint_ast_r7b.cjs"), ("r7b4", "ui_exposure_taint_ast_r7b4.cjs")]


def blob_of(path):
    raw = io.open(path, "rb").read()
    return hashlib.sha1(b"blob %d" % len(raw) + NUL + raw).hexdigest()


def run(name, js):
    r = subprocess.run(["node", os.path.join(REF, name), "--tree", FX, "--out", js],
                       capture_output=True, timeout=900,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert os.path.isfile(js), "rc=%s %s" % (r.returncode, r.stderr[:200])
    return json.load(io.open(js, encoding="utf-8"))


def counts(doc):
    hits = len(doc.get("hits", []))
    folded = len(doc.get("attributed_in_fold", []))
    return {"cells_total_reported": doc.get("cells_total"), "hits": hits,
            "attributed_in_fold_count": folded, "union": hits + folded,
            "parse_diagnostics_total": doc.get("parse_diagnostics_total")}


def main():
    pre = ruler_server_prefix()
    with_label = pre + BODY + LABEL + TAIL
    no_label = pre + BODY + TAIL
    out = {"fixtures": {"server_prefix_taken_from": "ui_exposure_taint_ast_r7b4.cjs const R7_SERVER",
                        "server_prefix_bytes": len(pre.encode("utf-8")),
                        "with_label_bytes": len(with_label.encode("utf-8")),
                        "no_label_bytes": len(no_label.encode("utf-8")),
                        "difference": "only the provenance-label <span> is added or removed"},
           "door_pinned_ruler_blob": blob_of(os.path.join(REF, "ui_exposure_taint_ast_r7b.cjs")),
           "results": {}}
    for label, src in (("with_provenance_label", with_label), ("label_deleted", no_label)):
        if os.path.isdir(FX):
            subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", FX], timeout=300)
        os.makedirs(FX, exist_ok=True)
        io.open(os.path.join(FX, "Probe.tsx"), "w", encoding="utf-8", newline="\n").write(src)
        for tag, name in GENS:
            js = os.path.join(WORK, "refile_%s_%s.json" % (label, tag))
            out["results"]["%s/%s" % (label, tag)] = counts(run(name, js))
    k = out["results"]
    out["the_door_number_moves_by_adding_a_label"] = {
        "r7b": {"with": k["with_provenance_label/r7b"]["cells_total_reported"],
                "without": k["label_deleted/r7b"]["cells_total_reported"]},
        "r7b4": {"with": k["with_provenance_label/r7b4"]["cells_total_reported"],
                 "without": k["label_deleted/r7b4"]["cells_total_reported"]}}
    out["union_stays"] = {
        "r7b": {"with": k["with_provenance_label/r7b"]["union"],
                "without": k["label_deleted/r7b"]["union"]},
        "r7b4": {"with": k["with_provenance_label/r7b4"]["union"],
                 "without": k["label_deleted/r7b4"]["union"]}}
    m = out["the_door_number_moves_by_adding_a_label"]
    u = out["union_stays"]
    out["per_generation"] = {
        t: {"door_number_drops_when_a_label_is_added": m[t]["with"] < m[t]["without"],
            "cells_total_with_label": m[t]["with"], "cells_total_without_label": m[t]["without"],
            "union_with_label": u[t]["with"], "union_without_label": u[t]["without"],
            "union_unchanged": u[t]["with"] == u[t]["without"]} for t in ("r7b", "r7b4")}
    moved = [t for t in ("r7b", "r7b4") if out["per_generation"][t]["door_number_drops_when_a_label_is_added"]]
    out["reading"] = (
        "measured per generation: %s. Under %s a same-file edit that only adds the provenance-label <span> "
        "takes `cells_total` (the number the door's growth arm compares) from %s to %s while the union of hits "
        "and attributed_in_fold stays at %s -- the screen keeps every byte of wording. Under the door-pinned "
        "r7b the same edit moves nothing (its cells_total stays %s), because that generation honours no spread "
        "anchor, so the fold stays unanchored and the cell stays a hit. The re-filing face is therefore a "
        "property of the newer rulers: it appears the moment the door's pin moves there, which is exactly the "
        "move the ORD-0448 r7b5 repair would have made."
        % (json.dumps(out["per_generation"], ensure_ascii=False), "r7b4" if "r7b4" in moved else "(none)",
           m.get("r7b4", {}).get("without"), m.get("r7b4", {}).get("with"), u.get("r7b4", {}).get("with"),
           m.get("r7b", {}).get("with")))
    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", FX], timeout=300)
    io.open(os.path.join(WORK, "refile_face_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
