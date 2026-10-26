"""R4.2 proof: the 是-branch loop is a real, correctly-directed connector.

The reviewer's complaint was that the box said 回到第 3 步 while nothing on the
page went back there. `se_visio_cross_check_r1.py` proves the line does not
collide with anything; it does not prove which way the arrow points. This does,
by reading the connector's own ShapeSheet cells and its glue records back out of
the saved file:

  * which two shapes the ends are glued to (page.Connects: FromSheet is the
    connector, ToSheet the glued-to shape), so "it touches 调用地点" is a file
    fact, not a pixel guess;
  * BeginX/BeginY vs EndX/EndY, so the tail sits on 继续调整方案 and the head
    sits on 调用地点与路线工具 - if those were swapped the arrow would point the
    wrong way and the loop would be an undo arrow instead of a retry;
  * EndArrow vs BeginArrow, the cells that decide which end draws the head.

Page coordinates are Visio's own (origin bottom-left, inches), so a shape whose
top edge is 3.14in below the top of a 7.5in page sits at y = 7.5 - 3.14 = 4.36.
"""
import hashlib
import json
import os
import sys
import time

import win32com.client as w

VSDX = (sys.argv[1] if len(sys.argv) > 1 else
        r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Classroom"
        r"\Teacher_02_Agent_User_Flow.vsdx")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "se_r42_loop_proof.json")

# the loop under review, and where each end must land (page inches, y from the
# bottom). Box geometry is in se_teacher_diagrams_r1.py: AW=2.25, AH=0.92,
# AX[2]=5.50, ROW_TOP=1.45, ROW_MID=3.05, DH=1.10.
PAGE_H = 7.5
EXPECT = {
    "tail": {"shape": "t2n7", "x": 6.625, "y": 4.36, "edge": "top"},
    "head": {"shape": "t2n3", "x": 6.625, "y": 5.13, "edge": "bottom"},
}
TOL = 0.03

log_lines = []


def log(msg):
    line = "[%5.1fs] %s" % (time.time() - T0, msg)
    print(line, flush=True)
    log_lines.append(line)


T0 = time.time()
digest_before = hashlib.sha256(open(VSDX, "rb").read()).hexdigest()

app = None
out = {"vsdx": os.path.basename(VSDX), "sha256_16": digest_before[:16],
       "loop": None, "findings": [], "verdict": "NOT-READ"}
try:
    app = w.DispatchEx("Visio.Application")
    app.Visible = False
    try:
        app.AlertResponse = 1
    except Exception:
        pass
    doc = app.Documents.OpenEx(VSDX, 16 | 2)
    try:
        # an earlier run of this reader died before Close() and Visio answered the
        # save prompt with AlertResponse=1, rewriting the delivered file: a read
        # tool must not be able to do that, so mark it clean on the way in
        doc.Saved = True
    except Exception:
        pass
    page = doc.Pages(1)

    # `page.Connects` is the glue authority: FromSheet is the line, ToSheet the
    # shape an end is stuck to. A connector whose two records name t2n7 and t2n3
    # is physically attached to both boxes, which is what "real connector" means.
    conn_ids = set()
    glued = {}
    for i in range(1, page.Connects.Count + 1):
        c = page.Connects.Item(i)
        fid = int(c.FromSheet.ID)
        conn_ids.add(fid)
        glued.setdefault(fid, []).append(int(c.ToSheet.ID))

    # Node and edge identity lives in Shape Data, not in Shape.Name: the builder
    # writes prop.NodeId on every box and prop.FlowEdge ("t2n7 -> t2n3") on every
    # connector, which is also what `se_visio_cross_check_r1.py` reads.
    # CellsIU / ResultStr are the two accessors this build answers to under late
    # binding (`Cells(...).ResultU` raises AttributeError - same finding as
    # `se_visio_cross_check_r1.py:_cell`).
    def num(sh, name):
        try:
            return float(sh.Cells(name).ResultIU)
        except Exception:
            return None

    def txt(sh, name):
        try:
            return str(sh.Cells(name).FormulaU).strip().strip('"')
        except Exception:
            return ""

    def node_id(sh):
        return txt(sh, "prop.NodeId").strip()

    def flow_edge(sh):
        return txt(sh, "prop.FlowEdge").strip()

    by_id = {}
    for i in range(1, page.Shapes.Count + 1):
        s = page.Shapes.Item(i)
        by_id[int(s.ID)] = s

    target = None
    for i in range(1, page.Shapes.Count + 1):
        s = page.Shapes.Item(i)
        sid = int(s.ID)
        if sid not in conn_ids:
            continue
        names = [node_id(by_id[v]) if v in by_id else "" for v in glued.get(sid, [])]
        if "t2n7" in names and "t2n3" in names:
            target = s
            break
    if target is None:
        out["findings"].append(
            "no connector glued to both t2n7 and t2n3 - the loop is not in the "
            "file (Connects read %d records over %d shapes)"
            % (page.Connects.Count, page.Shapes.Count))
    else:
        raw = dict((k, num(target, k)) for k in
                   ("BeginX", "BeginY", "EndX", "EndY"))
        if None in raw.values():
            out["findings"].append("end points unreadable: %s" % raw)
            raise RuntimeError("end points unreadable, see findings")
        ends_read = {"begin": (round(raw["BeginX"], 3), round(raw["BeginY"], 3)),
                     "end": (round(raw["EndX"], 3), round(raw["EndY"], 3))}
        glue_ids = glued.get(int(target.ID), [])
        glue_names = sorted(node_id(by_id[v]) if v in by_id else "?"
                            for v in glue_ids)
        out["loop"] = {
            "connectorName": target.Name,
            "flowEdge": flow_edge(target),
            "gluedTo": glue_names,
            "ends": ends_read,
            "routeExt": txt(target, "ConLineRouteExt"),
            "beginArrow": txt(target, "BeginArrow"),
            "endArrow": txt(target, "EndArrow"),
            "arrowSize": txt(target, "EndArrowSize"),
        }

        # which end carries the head, and does that end sit on 调用地点与路线工具
        head_end, tail_end = ("end", "begin")
        hx, hy = ends_read[head_end]
        tx, ty = ends_read[tail_end]
        ea, ba = num(target, "EndArrow"), num(target, "BeginArrow")
        out["loop"]["endArrowValue"] = ea
        out["loop"]["beginArrowValue"] = ba
        if ea in (None, 0.0):
            out["findings"].append("EndArrow reads %r - the head end draws no "
                                   "arrow at all" % ea)
        if ba not in (None, 0.0):
            out["findings"].append("BeginArrow reads %r - the tail carries a head "
                                   "too, so the arrow points both ways" % ba)
        for want, (x, y) in ((EXPECT["head"], (hx, hy)), (EXPECT["tail"], (tx, ty))):
            dx, dy = abs(x - want["x"]), abs(y - want["y"])
            if dx > TOL or dy > TOL:
                out["findings"].append(
                    "%s end is at (%.3f,%.3f), expected (%.3f,%.3f) on the %s of %s "
                    "- off by %.3f/%.3f in"
                    % (want["shape"], x, y, want["x"], want["y"], want["edge"],
                       want["shape"], dx, dy))
        if glue_names != sorted([EXPECT["tail"]["shape"], EXPECT["head"]["shape"]]):
            out["findings"].append("glue set is %s, expected ['t2n3', 't2n7']"
                                   % glue_names)
        if not out["findings"]:
            out["verdict"] = ("LOOP_OK: connector %s is glued to both boxes, its "
                              "tail sits on 继续调整方案 top edge (%.3f,%.3f) and its "
                              "arrow head enters 调用地点与路线工具 bottom edge "
                              "(%.3f,%.3f); EndArrow=%s, BeginArrow=%s"
                              % (target.Name, tx, ty, hx, hy,
                                 out["loop"]["endArrow"], out["loop"]["beginArrow"]))
    doc.Close()
except Exception as exc:
    out["findings"].append("open/read failed: %s: %s" % (type(exc).__name__, exc))
finally:
    if app is not None:
        try:
            app.Quit()
        except Exception:
            pass

digest_after = hashlib.sha256(open(VSDX, "rb").read()).hexdigest()
out["unchanged"] = digest_after == digest_before
if not out["unchanged"]:
    out["findings"].append("the audit rewrote the file - digest changed")

json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
log("%s %s" % (out["verdict"], "; ".join(out["findings"])[:400] or "-"))
log("wrote %s" % OUT)
sys.exit(0 if out["verdict"].startswith("LOOP_OK") and out["unchanged"] else 1)
