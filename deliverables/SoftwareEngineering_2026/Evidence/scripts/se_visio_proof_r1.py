"""Standalone proof runner for the four Visio deliverables.

Per diagram, against the shipped .vsdx:
  A open it; census shapes / Connect records / pages
  B prove the wiring: read page.Connects back and show that for every edge in
    the spec there is one connector shape glued to BOTH named shapes. This is a
    direct proof of real glue, not a screenshot claim.
  C move a node and show the connector endpoint follows (best effort - some
    built-in masters protect their position, which is recorded, not hidden)
  D overwrite one node's text, save, close, reopen, read the marker back,
    restore, save, close, reopen, prove the restore landed and the connection
    count is unchanged.
"""
import glob
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import win32com.client as w32                                  # noqa: E402

OUT = os.environ.get("SE_VISIO_OUT",
                     r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Visio")
SPEC_DIR = os.path.join(OUT, "specs")
LOGF = open(os.path.join(HERE, "se_visio_proof.log"), "w", encoding="utf-8", buffering=1)
_t0 = time.time()


def log(m):
    line = "[%6.1fs] %s" % (time.time() - _t0, m)
    LOGF.write(line + "\n")
    LOGF.flush()
    print(line, flush=True)


def clean(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, dict):
        return dict((k, clean(x)) for k, x in v.items())
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
                               "err": "%s: %s" % (type(exc).__name__, str(exc)[:180])}
        return None


def shape_ids(pg):
    """Shape.ID -> details, for every shape on the page. Keyed by ID because
    master-derived shapes share names (many shapes are literally 矩形)."""
    out = {}
    for i in range(1, pg.Shapes.Count + 1):
        sh = pg.Shapes.Item(i)
        try:
            mname = sh.Master.Name if sh.Master is not None else None
        except Exception:
            mname = None
        try:
            props = {}
            for p in ("NodeId", "State", "SourceRef", "FlowEdge"):
                try:
                    props[p] = sh.CellsSRC(243, p, "Value").StrV
                except Exception:
                    props[p] = None
        except Exception:
            props = {}
        out[sh.ID] = {"id": sh.ID, "name": sh.Name, "master": mname, "text": sh.Text,
                      "props": props, "shape": sh}
    return out


def main():
    files = sorted(glob.glob(os.path.join(OUT, "*.vsdx")))
    if not files:
        log("no vsdx found in %s" % OUT)
        return 1
    vis = w32.DispatchEx("Visio.Application")
    for prop, val in (("Visible", False), ("AlertResponse", 7), ("ScreenUpdating", 0)):
        try:
            setattr(vis, prop, val)
        except Exception:
            pass
    out = []
    for path in files:
        stem = os.path.splitext(os.path.basename(path))[0]
        spec = json.load(open(os.path.join(SPEC_DIR, stem + ".json"), encoding="utf-8"))
        rec = {"file": os.path.basename(path), "steps": {}, "ok": False}
        log("=== proof %s" % rec["file"])

        d = step(rec, "open", lambda: vis.Documents.Open(path))
        if d is None:
            out.append(rec)
            continue
        pages = []
        info = {}
        npages = step(rec, "pageCount", lambda: d.Pages.Count) or 1
        by_page = {}
        for pi in range(1, npages + 1):
            pgx = d.Pages.Item(pi)
            sub = step(rec, "index_p%d" % pi, lambda g=pgx: shape_ids(g)) or {}
            by_page[pi] = sub
            info.update(sub)
            pages.append(pgx)
        pg = pages[0]
        def live(key):
            """key is (page, ShapeID) as recorded by the builder."""
            pg_i, sid = key
            return (by_page.get(pg_i) or {}).get(sid, {}).get("shape")

        live_all = {}
        for pi, d_ in by_page.items():
            for k, v in d_.items():
                live_all[(pi, k)] = v["shape"]

        connects0 = step(rec, "connects0", lambda: sum(p.Connects.Count for p in pages))

        # ---- B: prove every spec edge is really glued to both named shapes.
        # The builder recorded Shape.ID for every node and every connector; Shape.ID
        # survives save/reopen, so this is a check against the file on disk.
        gate = json.load(open(os.path.join(OUT, "previews", stem + ".gate.json"),
                              encoding="utf-8"))
        node_ids = gate.get("shapeIds") or {}
        edge_ids = gate.get("edgeIds") or {}

        def glue_audit():
            if not node_ids or not edge_ids:
                return {"expected": len(spec["edges"]), "proven": 0,
                        "missing": ["the shipped gate report carries no shape id map"]}
            live = live_all
            pairs = {}
            for pi in range(1, npages + 1):
                for i in range(1, pages[pi - 1].Connects.Count + 1):
                    c = pages[pi - 1].Connects.Item(i)
                    try:
                        f, tt = c.FromSheet.ID, c.ToSheet.ID
                    except Exception:
                        continue
                    pairs.setdefault(f, set()).add(tt)
                    pairs.setdefault(tt, set()).add(f)
            missing, proven = [], 0
            for e in spec["edges"]:
                key = "%s->%s" % (e["from"], e["to"])
                cid = edge_ids.get(key)
                conn = live(cid) if cid else None
                if conn is None:
                    missing.append("%s: connector (page %s, id %s) is not in the file"
                                   % (key, cid[0] if cid else "?", cid[1] if cid else "?"))
                    continue
                ends = pairs.get(cid[1], set())
                ak, zk = node_ids.get(e["from"]), node_ids.get(e["to"])
                a, z = ak[1] if ak else None, zk[1] if zk else None
                if a in ends and z in ends:
                    proven += 1
                else:
                    missing.append("%s: connector %d touches %s, expected %s and %s"
                                   % (key, cid, sorted(ends), a, z))
            return {"expected": nedges, "proven": proven, "nodes": nnodes,
                    "missing": missing[:12]}
        audit = step(rec, "glueAudit", glue_audit)

        # ---- B2: every node must still carry its three Shape Data rows and
        #      every connector its FlowEdge, read out of the file on disk
        def shape_data_audit():
            live = dict((pg.Shapes.Item(i).ID, pg.Shapes.Item(i))
                        for i in range(1, pg.Shapes.Count + 1))
            need = {}
            for nid, key in node_ids.items():
                need.setdefault(key, []).append(("NodeId", nid))
                need[key].append(("State", None))
                need[key].append(("SourceRef", None))
            for ekey, key in edge_ids.items():
                need.setdefault(key, []).append(("FlowEdge", ekey))
            ok = miss = 0
            examples = []
            for (pg_i, sid), props in need.items():
                sh = (by_page.get(pg_i) or {}).get(sid, {}).get("shape")
                if sh is None:
                    miss += len(props)
                    examples.append("page %s shape id %s absent" % (pg_i, sid))
                    continue
                for cell, expect in props:
                    try:
                        f = sh.CellsU("Prop.%s.Value" % cell).FormulaU
                    except Exception as exc:
                        miss += 1
                        if len(examples) < 6:
                            examples.append("id %s Prop.%s: %s" % (sid, cell,
                                                                   type(exc).__name__))
                        continue
                # read the values back and compare where a value is known
                good = True
                for cell, expect in props:
                    try:
                        f = sh.CellsU("Prop.%s.Value" % cell).FormulaU
                    except Exception:
                        good = False
                        break
                    val = f[1:-1] if len(f) >= 2 and f[0] == '"' and f[-1] == '"' else f
                    if expect is not None and val != expect:
                        good = False
                        if len(examples) < 6:
                            examples.append("id %s Prop.%s = %r, expected %r"
                                            % (sid, cell, val[:40], expect))
                        break
                    if expect is None and not val:
                        good = False
                        if len(examples) < 6:
                            examples.append("id %s Prop.%s is empty" % (sid, cell))
                        break
                if good:
                    ok += len(props)
                else:
                    miss += len(props)
            total = sum(len(v) for v in need.values())
            return {"shapes": len(need), "propsOk": ok, "propsTotal": total,
                    "pages": npages,
                    "propsMissing": miss, "examples": examples[:6]}
        sd = step(rec, "shapeDataAudit", shape_data_audit)

        # ---- C: move a node, watch the endpoint follow (best effort)
        def move_proof():
            pairs = {}
            for pi in range(1, npages + 1):
                for i in range(1, pages[pi - 1].Connects.Count + 1):
                    c = pages[pi - 1].Connects.Item(i)
                    try:
                        f, tt = c.FromSheet.ID, c.ToSheet.ID
                    except Exception:
                        continue
                    pairs.setdefault(f, set()).add(tt)
                    pairs.setdefault(tt, set()).add(f)
            live = live_all
            for key, cid in edge_ids.items():
                conn = live(cid)
                if conn is None:
                    continue
                ends = [x for x in
                        ((by_page.get(cid[0]) or {}).get(s, {}).get("shape")
                         for s in sorted(pairs.get(cid[1], set())))
                        if x is not None]
                wanted = set(v[1] for v in node_ids.values())
                ends = [x for x in ends if x.ID in wanted]
                if not ends:
                    continue
                node = ends[0]
                before = round(conn.Cells("BeginY").ResultIU, 4)
                try:
                    node.Cells("PinY").FormulaU = "=PinY+0.3in"
                except Exception as exc:
                    return {"edge": key, "blocked": "%s (position protected by the master)"
                            % type(exc).__name__}
                after = round(conn.Cells("BeginY").ResultIU, 4)
                node.Cells("PinY").FormulaU = "=PinY-0.3in"
                back = round(node.Cells("PinY").ResultIU, 4)
                return {"edge": key, "nodePinY": [before, back],
                        "connBeginY": [before, after],
                        "followed": abs(after - before) > 0.05,
                        "restored": abs(back - before) < 0.01}
            return {"blocked": "no connector with a movable node endpoint"}

        step(rec, "moveProof", move_proof)

        # ---- D: text edit -> save -> close -> reopen -> read -> restore
        wanted_ids = set(v[1] for v in node_ids.values())
        target = None
        for k, v in info.items():
            if v["id"] in wanted_ids and v.get("master"):
                target = v
                break
        if target is None:
            target = list(info.values())[0]
        tid, original = target["id"], target["text"]
        node_page_of = lambda sid: next((k[0] for k, _v in node_ids.items()
                                         if k[1] == sid), 1)
        marker = "PROOF-EDIT %s" % time.strftime("%H%M%S")
        step(rec, "writeMarker", lambda: setattr(target["shape"], "Text", marker))
        step(rec, "save1", lambda: d.Save())
        step(rec, "close1", lambda: d.Close())
        d2 = step(rec, "reopen1", lambda: vis.Documents.Open(path))

        def find_shape(doc, want):
            p = doc.Pages.Item(1)
            for i in range(1, p.Shapes.Count + 1):
                if p.Shapes.Item(i).ID == want:
                    return p.Shapes.Item(i)
            return None
        tpg = node_page_of(tid)

        def find_shape2(doc, want):
            p = doc.Pages.Item(tpg)
            for i in range(1, p.Shapes.Count + 1):
                if p.Shapes.Item(i).ID == want:
                    return p.Shapes.Item(i)
            return None
        sh2 = step(rec, "findAfterReopen", lambda: find_shape2(d2, tid))
        back = step(rec, "markerAfterReopen", lambda: sh2.Text if sh2 else None)
        step(rec, "restore", lambda: sh2 and setattr(sh2, "Text", original))
        step(rec, "save2", lambda: d2.Save())
        step(rec, "close2", lambda: d2.Close())
        d3 = step(rec, "reopen2", lambda: vis.Documents.Open(path))
        connects3 = step(rec, "connectsAfter", lambda: sum(
            d3.Pages.Item(i).Connects.Count for i in range(1, d3.Pages.Count + 1)))
        sh3 = step(rec, "findFinal", lambda: find_shape2(d3, tid))
        final = step(rec, "textFinal", lambda: sh3.Text if sh3 else None)
        step(rec, "close3", lambda: d3.Close())

        checks = {
            "allEdgesGlued": bool(audit) and audit["proven"] == audit["expected"],
            "allShapeDataPresent": bool(sd) and sd["propsMissing"] == 0
            and sd["propsOk"] == sd["propsTotal"],
            "markerRoundTrip": back == marker,
            "textRestored": final == original,
            "connectionsSurvived": connects3 == connects0,
        }
        rec["checks"] = checks
        rec["glue"] = audit
        rec["ok"] = all(checks.values())
        out.append(rec)
        log("  -> %s  %s" % (rec["file"], json.dumps(checks, ensure_ascii=False)))
        if audit:
            log("     glue: %d/%d edges proven to both endpoints; missing=%s"
                % (audit["proven"], audit["expected"], audit["missing"][:4]))
        if sd:
            log("     shape data: %d/%d property values read back over %d shapes; missing=%d %s"
                % (sd["propsOk"], sd["propsTotal"], sd["shapes"],
                   sd["propsMissing"], sd["examples"][:3]))
        mp = rec["steps"].get("moveProof", {})
        log("     move: %s" % json.dumps(mp.get("value"), ensure_ascii=False))
        for k, v in rec["steps"].items():
            if not v["ok"]:
                log("     step FAIL %-20s %s" % (k, v["err"]))
    try:
        vis.Quit()
    except Exception:
        pass
    json.dump(out, open(os.path.join(HERE, "se_visio_proof_result.json"), "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False)
    bad = [r["file"] for r in out if not r["ok"]]
    log("PROOF DONE: %d/%d ok; failed=%s" % (len(out) - len(bad), len(out), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
