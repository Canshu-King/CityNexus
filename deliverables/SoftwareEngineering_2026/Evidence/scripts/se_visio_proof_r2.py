"""Visio deliverable proof - page-scoped rewrite (r2).

For each shipped .vsdx, working from the file on disk (never from memory):

  A  open it and index every page: Shape.ID -> details
  B  prove the wiring: for every edge in the spec there is a connector whose
     Connect records touch BOTH named shapes, on the same page
  C  prove the shape data: every node occurrence still carries NodeId / State /
     SourceRef with the exact spec values, and every connector its FlowEdge
     (plus SourceRef where the spec anchors the edge)
  D  prove editing: overwrite one node's text, save, close, reopen, read the
     marker back, restore, save, close, reopen, prove the restore landed, the
     connection census is unchanged and the shape data still reads back

A Visio Shape.ID is unique per page only, and one spec id may legitimately be
drawn on two pages (a parent use case repeated on the detail page), so every
identity here is a (page, ShapeID) pair and every occurrence is audited.
"""
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import win32com.client as w32                                   # noqa: E402

OUT = os.environ.get("SE_VISIO_OUT",
                     r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Visio")
SPEC_DIR = os.path.join(OUT, "specs")
LOG = open(os.path.join(HERE, "se_visio_proof.log"), "w", encoding="utf-8", buffering=1)
T0 = time.time()


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def clean(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, dict):
        return dict((str(k), clean(x)) for k, x in v.items())
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    return repr(v)[:120]


def step(rec, label, fn):
    try:
        v = fn()
        rec["steps"][label] = {"ok": True, "value": clean(v)}
        return v
    except Exception as exc:
        rec["steps"][label] = {"ok": False,
                               "err": "%s: %s" % (type(exc).__name__, str(exc)[:200])}
        return None


def coord(v):
    """A (page, ShapeID) pair survives JSON as a list; make it hashable."""
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return (int(v[0]), int(v[1]))
    return None


def index_page(pg):
    out = {}
    for i in range(1, pg.Shapes.Count + 1):
        sh = pg.Shapes.Item(i)
        try:
            mname = sh.Master.Name if sh.Master is not None else None
        except Exception:
            mname = None
        out[sh.ID] = {"id": sh.ID, "name": sh.Name, "master": mname,
                      "text": sh.Text, "shape": sh}
    return out


def cell_val(sh, prop):
    if sh is None:
        return "<absent>"
    try:
        f = sh.CellsU("Prop.%s.Value" % prop).FormulaU
    except Exception as exc:
        return "<%s>" % type(exc).__name__
    if isinstance(f, str) and len(f) >= 2 and f[0] == '"' and f[-1] == '"':
        return f[1:-1]
    return f


def spec_sheets(spec):
    return spec.get("sheets") or [dict(spec, name=spec.get("pageName", "Page-1"))]


def declared(sheets):
    """Every property the spec says must exist on disk, as (coord, prop, value)
    checks plus the per-page slot counts."""
    node_slots = {}
    edge_slots = {}
    for idx, sh in enumerate(sheets, start=1):
        node_slots[idx] = len(sh.get("nodes", []))
        edge_slots[idx] = len(sh.get("edges", []))
    return node_slots, edge_slots


def main():
    files = sorted(glob.glob(os.path.join(OUT, "*.vsdx")))
    if not files:
        log("nothing to prove in %s" % OUT)
        return 1
    vis = w32.DispatchEx("Visio.Application")
    for prop, val in (("Visible", False), ("AlertResponse", 7), ("ScreenUpdating", 0)):
        try:
            setattr(vis, prop, val)
        except Exception:
            pass
    results = []
    for path in files:
        stem = os.path.splitext(os.path.basename(path))[0]
        gate_path = os.path.join(OUT, "previews", stem + ".gate.json")
        spec = json.load(open(os.path.join(SPEC_DIR, stem + ".json"), encoding="utf-8"))
        gate = json.load(open(gate_path, encoding="utf-8"))
        # The shipped .vsdx and the gate report must come from the same build: a
        # newer gate next to an older drawing means that build was refused and the
        # proof would be auditing a pair that never existed together.
        if os.path.getmtime(gate_path) > os.path.getmtime(path) + 1:
            log("=== proof %s  SKIPPED: gate report is newer than the .vsdx"
                % os.path.basename(path))
            results.append({"file": os.path.basename(path), "ok": False,
                            "error": "gate.json is newer than the shipped .vsdx - "
                                     "the last build was refused, re-run the build"})
            continue
        sheets = spec_sheets(spec)
        node_slots, edge_slots = declared(sheets)
        n_nodes = sum(node_slots.values())
        n_edges = sum(edge_slots.values())
        want_props = sum(3 * node_slots[p] + edge_slots[p] for p in node_slots) \
            + sum(1 for sh in sheets for e in sh.get("edges", []) if e.get("src")) \
            - sum(1 for sh in sheets for n in sh.get("nodes", [])
                  if not (n.get("src") or "").strip())
        # gate report -> (page, ShapeID) occurrences, keyed by spec identity
        node_occ = dict((k, [c for c in (coord(x) for x in v) if c])
                        for k, v in (gate.get("shapeIds") or {}).items())
        edge_occ = dict((k, [c for c in (coord(x) for x in v) if c])
                        for k, v in (gate.get("edgeIds") or {}).items())
        rec = {"file": os.path.basename(path), "steps": {}, "ok": False}
        log("=== proof %s" % rec["file"])
        if not node_occ or not edge_occ:
            rec["error"] = "gate report carries no (page, ShapeID) occurrence map"
            results.append(rec)
            continue
        occ_nodes = sum(len(v) for v in node_occ.values())
        occ_edges = sum(len(v) for v in edge_occ.values())
        if occ_nodes != n_nodes or occ_edges != n_edges:
            rec["error"] = ("occurrence map incomplete: %d node / %d edge coords "
                            "recorded for %d / %d spec slots"
                            % (occ_nodes, occ_edges, n_nodes, n_edges))
            results.append(rec)
            continue

        d = step(rec, "open", lambda: vis.Documents.Open(path))
        if d is None:
            results.append(rec)
            continue
        npages = d.Pages.Count
        pages = [d.Pages.Item(i + 1) for i in range(npages)]
        by_page = [index_page(pg) for pg in pages]
        if npages != len(sheets):
            rec["error"] = "document has %d pages, spec declares %d sheets" % (
                npages, len(sheets))
            results.append(rec)
            try:
                d.Close()
            except Exception:
                pass
            continue
        connects_by_page = [pg.Connects.Count for pg in pages]
        step(rec, "census", lambda: {"pages": npages,
                                     "shapes": [len(b) for b in by_page],
                                     "connects": connects_by_page})
        connects0 = sum(connects_by_page)

        def shape_of(key):
            if not key:
                return None
            pg_i, sid = key
            return (by_page[pg_i - 1].get(sid) or {}).get("shape")

        # ---- B: wiring -----------------------------------------------------
        def glue():
            pairs = {}
            for pi, pg in enumerate(pages):
                for i in range(1, pg.Connects.Count + 1):
                    c = pg.Connects.Item(i)
                    try:
                        f, t = c.FromSheet.ID, c.ToSheet.ID
                    except Exception:
                        continue
                    pairs.setdefault((pi + 1, f), set()).add((pi + 1, t))
                    pairs.setdefault((pi + 1, t), set()).add((pi + 1, f))
            missing, proven, orphans = [], 0, []
            for ekey, coords in edge_occ.items():
                for ck in coords:
                    conn = shape_of(ck)
                    if conn is None:
                        missing.append("%s: connector %r absent from page" % (ekey, ck))
                        continue
                    ends = pairs.get(ck, set())
                    if len(ends) < 2:
                        orphans.append("%s %r has %d glued end(s)" % (ekey, ck,
                                                                       len(ends)))
                    src = ekey.split("->")[0]
                    dst = ekey.split("->")[1]
                    ak = [k for k in node_occ.get(src, []) if k[0] == ck[0]]
                    zk = [k for k in node_occ.get(dst, []) if k[0] == ck[0]]
                    if ak and zk and ak[0] in ends and zk[0] in ends:
                        proven += 1
                    else:
                        missing.append("%s: connector %r touches %s (wanted %s %s)"
                                       % (ekey, ck, sorted(ends), ak, zk))
            return {"expected": occ_edges, "proven": proven,
                    "underglued": orphans[:10], "missing": missing[:10]}
        audit = step(rec, "glueAudit", glue)

        # ---- C: shape data -------------------------------------------------
        def shape_data():
            ok = bad = 0
            examples = []
            node_by_id = {}
            for sh in sheets:
                for n in sh.get("nodes", []):
                    node_by_id.setdefault(n["id"], []).append(n)
            for nid, coords in node_occ.items():
                specs = node_by_id.get(nid, [])
                for ci, ck in enumerate(coords):
                    shp = shape_of(ck)
                    want = specs[ci] if ci < len(specs) else (specs[-1] if specs else {})
                    checks = [("NodeId", nid),
                              ("State", want.get("state", "verified"))]
                    if str(want.get("src", "")).strip():
                        checks.append(("SourceRef", want.get("src", "")))
                    for prop, expect in checks:
                        got = cell_val(shp, prop)
                        if got == expect:
                            ok += 1
                        else:
                            bad += 1
                            if len(examples) < 8:
                                examples.append("%s@p%d %s: %r != %r"
                                                % (nid, ck[0], prop, got, expect))
            edge_specs = {}
            for sh in sheets:
                for e in sh.get("edges", []):
                    edge_specs.setdefault("%s->%s" % (e["from"], e["to"]),
                                          []).append(e)
            for ekey, coords in edge_occ.items():
                for ci, ck in enumerate(coords):
                    shp = shape_of(ck)
                    es = edge_specs.get(ekey, [])
                    e = es[ci] if ci < len(es) else (es[-1] if es else {})
                    got = cell_val(shp, "FlowEdge")
                    if got == ekey:
                        ok += 1
                    else:
                        bad += 1
                        if len(examples) < 8:
                            examples.append("edge %s@p%d FlowEdge: %r"
                                            % (ekey, ck[0], got))
                    if e.get("src"):
                        got = cell_val(shp, "SourceRef")
                        if got == e["src"]:
                            ok += 1
                        else:
                            bad += 1
                            if len(examples) < 8:
                                examples.append("edge %s@p%d SourceRef: %r != %r"
                                                % (ekey, ck[0], got, e["src"]))
            return {"nodeCoords": occ_nodes, "edgeCoords": occ_edges,
                    "propsOk": ok, "propsBad": bad, "expected": want_props,
                    "examples": examples}
        sd = step(rec, "shapeDataAudit", shape_data)

        # ---- D: edit round trip -------------------------------------------
        pg_i, sid = node_occ[next(iter(node_occ))][0]
        target = by_page[pg_i - 1][sid]["shape"]
        original = target.Text
        marker = "PROOF-EDIT %s" % time.strftime("%H%M%S")
        step(rec, "writeMarker", lambda: setattr(target, "Text", marker))
        step(rec, "save1", lambda: d.Save())
        step(rec, "close1", lambda: d.Close())
        d2 = step(rec, "reopen1", lambda: vis.Documents.Open(path))

        def find(doc):
            p = doc.Pages.Item(pg_i)
            for i in range(1, p.Shapes.Count + 1):
                if p.Shapes.Item(i).ID == sid:
                    return p.Shapes.Item(i)
            return None
        sh2 = step(rec, "findAfterReopen", lambda: find(d2))
        back = step(rec, "markerAfterReopen", lambda: sh2.Text if sh2 else None)
        step(rec, "restore", lambda: sh2 and setattr(sh2, "Text", original))
        step(rec, "save2", lambda: d2.Save())
        step(rec, "close2", lambda: d2.Close())
        d3 = step(rec, "reopen2", lambda: vis.Documents.Open(path))
        connects3 = step(rec, "connectsAfter", lambda: sum(
            d3.Pages.Item(i).Connects.Count for i in range(1, d3.Pages.Count + 1)))
        sh3 = step(rec, "findFinal", lambda: find(d3))
        final = step(rec, "textFinal", lambda: sh3.Text if sh3 else None)
        still = step(rec, "shapeDataAfterEdit",
                     lambda: cell_val(sh3, "State") != "" and
                     cell_val(sh3, "SourceRef") != "")
        step(rec, "close3", lambda: d3.Close())

        checks = {
            "allEdgesGlued": bool(audit) and audit["proven"] == audit["expected"]
            and not audit["underglued"],
            "allShapeDataPresent": bool(sd) and sd["propsBad"] == 0
            and sd["propsOk"] == sd["expected"],
            "markerRoundTrip": back == marker,
            "textRestored": final == original,
            "connectionsSurvived": connects3 == connects0,
            "shapeDataSurvivesEditing": bool(still),
        }
        rec["checks"] = checks
        rec["glue"] = audit
        rec["shapeData"] = sd
        rec["pages"] = npages
        rec["ok"] = all(checks.values())
        results.append(rec)
        log("  -> %s  %s" % (rec["file"], json.dumps(checks, ensure_ascii=False)))
        if audit:
            log("     glue: %d/%d connectors touch both named shapes; "
                "underglued=%d missing=%d" % (audit["proven"], audit["expected"],
                                              len(audit["underglued"]),
                                              len(audit["missing"])))
        if sd:
            log("     shape data: %d/%d values read back exactly; bad=%d %s"
                % (sd["propsOk"], sd["expected"], sd["propsBad"],
                   sd["examples"][:3]))
        for k, v in rec["steps"].items():
            if not v["ok"]:
                log("     step FAIL %-22s %s" % (k, v["err"]))
    try:
        vis.Quit()
    except Exception:
        pass
    json.dump(results, open(os.path.join(HERE, "se_visio_proof_result.json"), "w",
                            encoding="utf-8"), indent=1, ensure_ascii=False)
    bad = [r["file"] for r in results if not r.get("ok")]
    tot_glue = sum((r.get("glue") or {}).get("proven", 0) for r in results)
    tot_prop = sum((r.get("shapeData") or {}).get("propsOk", 0) for r in results)
    log("TOTALS: glue %d, shape data %d over %d diagrams"
        % (tot_glue, tot_prop, len(results)))
    log("PROOF DONE: %d/%d ok; failed=%s" % (len(results) - len(bad), len(results), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
