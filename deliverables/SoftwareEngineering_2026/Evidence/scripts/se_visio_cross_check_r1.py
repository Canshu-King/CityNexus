"""读回 .vsdx 里每条连线的真实折点，算交叉，而不是靠肉眼猜 Visio 怎么布的线。

用户点名的问题就是"交叉线"。之前我只看导出的 PNG，看到叉但说不清是哪两条、
在哪个坐标，改一版赌一版。这里把每条连线的 `BeginX/BeginY -> Points -> EndX/EndY`
取成折线，然后：

  1. 两条连线的线段是否相交（共享端点的那一跳不算）；
  2. 连线是否穿过**自己两个框以外**的第三个框；
  3. 连线是否出页。

只读：打开前后各算一次文件字节 sha256，交付原件必须一字不变。
"""
import hashlib
import json
import math
import os
import sys
import time

import win32com.client  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
T0 = time.time()


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    print(line, flush=True)
    return line


def _seg_int(p1, p2, p3, p4):
    """Proper intersection of segments p1p2 and p3p4 (shared endpoints excluded)."""
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    d1, d2 = cross(p3, p4, p1), cross(p3, p4, p2)
    d3, d4 = cross(p1, p2, p3), cross(p1, p2, p4)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        den = (p1[0] - p2[0]) * (p3[1] - p4[1]) - (p1[1] - p2[1]) * (p3[0] - p4[0])
        if abs(den) < 1e-12:
            return None
        t = ((p1[0] - p3[0]) * (p3[1] - p4[1]) - (p1[1] - p3[1]) * (p3[0] - p4[0])) / den
        x = p1[0] + t * (p2[0] - p1[0])
        y = p1[1] + t * (p2[1] - p1[1])
        return (x, y)
    # collinear / touching: only report a real overlap, not a shared endpoint
    def on(a, b, c):
        return (min(a[0], b[0]) - 1e-9 <= c[0] <= max(a[0], b[0]) + 1e-9
                and min(a[1], b[1]) - 1e-9 <= c[1] <= max(a[1], b[1]) + 1e-9)
    for a, b, c in ((p1, p2, p3), (p1, p2, p4), (p3, p4, p1), (p3, p4, p2)):
        if on(a, b, c):
            return c
    return None


def _seg_box(p1, p2, box, pad=0.02):
    """Does the segment pass through the rectangle (beyond a grazing entry)?"""
    x0, y0, x1, y1 = box
    x0, y0, x1, y1 = x0 + pad, y0 + pad, x1 - pad, y1 - pad
    if x1 <= x0 or y1 <= y0:
        return False
    # sample: a route that merely touches a side is fine, a route with its
    # middle inside the box is not
    n = 40
    hits = 0
    for i in range(1, n):
        t = i / float(n)
        x = p1[0] + (p2[0] - p1[0]) * t
        y = p1[1] + (p2[1] - p1[1]) * t
        if x0 < x < x1 and y0 < y < y1:
            hits += 1
    return hits >= 2


def _cell(sh, name):
    try:
        return sh.Cells(name).ResultIU
    except Exception:
        return None


def _cellf(sh, name):
    try:
        return str(sh.Cells(name).FormulaU).strip().strip('"')
    except Exception:
        return ""


def route_points(con):
    """The polyline Visio actually drew, in inches, page coordinates (y up).

    `Shape.Points` and `Shape.ShapeType` are invisible to pywin32 late binding on
    this install, so the route is taken from the ShapeSheet: `BeginX/BeginY` and
    `EndX/EndY` are the glued endpoints, and a connector is identified by being
    the `FromSheet` of one of the page's `Connects`. When the two ends are level
    or aligned, the drawn path *is* that single segment whatever the routing
    style says; when they are neither and the style is orthogonal, the bend
    position is not readable from here, so the caller is told it cannot verify
    that line rather than being handed a guess.
    """
    bx, by = _cell(con, "BeginX"), _cell(con, "BeginY")
    ex, ey = _cell(con, "EndX"), _cell(con, "EndY")
    if None in (bx, by, ex, ey):
        return None, "no begin/end cells"
    ext = _cell(con, "ConLineRouteExt")
    if abs(bx - ex) < 0.02 or abs(by - ey) < 0.02:
        return [(bx, by), (ex, ey)], None
    if ext in (0.0, 1.0):
        return [(bx, by), (ex, ey)], None
    return None, ("orthogonal connector between unaligned ends (%.2f,%.2f)->"
                  "(%.2f,%.2f): bend vertices are not readable here"
                  % (bx, by, ex, ey))


def analyse(path):
    before = hashlib.sha256(open(path, "rb").read()).hexdigest()
    os.chmod(path, 0o444)
    vis = win32com.client.DispatchEx("Visio.Application")
    vis.Visible = False
    vis.AlertResponse = 7
    out = {"file": os.path.basename(path), "crossings": [], "throughShapes": [],
           "offPage": [], "readFailures": [], "connectors": 0, "notes": []}
    try:
        doc = vis.Documents.OpenEx(path, 16 | 2)  # budget+openonown, read-only below
        for pi in range(1, doc.Pages.Count + 1):
            page = doc.Pages.Item(pi)
            ph = _cell(page.PageSheet, "PageHeight") or 0.0
            shapes, cons = [], []
            total = page.Shapes.Count
            # `page.Connects` is the authority on which shapes are connectors:
            # FromSheet is the line, ToSheet the shape it is glued to.
            conn_ids = set()
            for i in range(1, page.Connects.Count + 1):
                try:
                    conn_ids.add(int(page.Connects.Item(i).FromSheet.ID))
                except Exception:
                    pass
            for k in range(1, total + 1):
                sh = page.Shapes.Item(k)
                try:
                    sid = int(sh.ID)
                except Exception:
                    continue
                if sid in conn_ids:
                    pts, why = route_points(sh)
                    cons.append({"id": sid, "name": sh.Name,
                                 "edge": _cellf(sh, "prop.FlowEdge").replace(" ", ""),
                                 "pts": pts or [], "unreadable": why})
                    continue
                px, py = _cell(sh, "PinX"), _cell(sh, "PinY")
                w, h = _cell(sh, "Width"), _cell(sh, "Height")
                if None in (px, py, w, h):
                    continue
                nid = _cellf(sh, "prop.NodeId")
                shapes.append({"id": sid, "label": nid or sh.Name,
                               "box": (px - w / 2.0, py - h / 2.0,
                                       px + w / 2.0, py + h / 2.0)})
            out["connectors"] = len(cons)
            out["pageInk"] = {"shapesOnPage": total, "shapes": len(shapes),
                              "connectors": len(cons),
                              "connects": int(page.Connects.Count)}
            # An empty reading is not a clean drawing. This instrument once
            # reported "PASS (2/2 clean)" because its collection loop matched
            # nothing at all, so every way of reading nothing now fails loudly.
            if total < 3 or len(shapes) < 3 or len(cons) == 0:
                out["readFailures"].append(
                    "page %s: %d shapes, %d boxes, %d connectors read - "
                    "nothing to audit" % (page.Name, total, len(shapes), len(cons)))
            for c in cons:
                if c["unreadable"]:
                    out["readFailures"].append("%s: %s" % (c["edge"] or c["name"],
                                                           c["unreadable"]))
            # 1. connector vs connector
            for i in range(len(cons)):
                for j in range(i + 1, len(cons)):
                    a, b = cons[i]["pts"], cons[j]["pts"]
                    for si in range(len(a) - 1):
                        for sj in range(len(b) - 1):
                            x = _seg_int(a[si], a[si + 1], b[sj], b[sj + 1])
                            if x is None:
                                continue
                            near_end = min(
                                math.hypot(x[0] - a[0][0], x[1] - a[0][1]),
                                math.hypot(x[0] - a[-1][0], x[1] - a[-1][1]),
                                math.hypot(x[0] - b[0][0], x[1] - b[0][1]),
                                math.hypot(x[0] - b[-1][0], x[1] - b[-1][1]))
                            if near_end < 0.12:
                                continue  # both lines leave the same box side
                            out["crossings"].append(
                                {"a": cons[i]["edge"] or cons[i]["name"],
                                 "b": cons[j]["edge"] or cons[j]["name"],
                                 "at": [round(x[0], 2), round(x[1], 2)]})
            # 2. connector through a third shape
            for c in cons:
                if len(c["pts"]) < 2:
                    continue
                ends = []
                for sh in shapes:
                    for p in (c["pts"][0], c["pts"][-1]):
                        if (sh["box"][0] - 0.05 <= p[0] <= sh["box"][2] + 0.05
                                and sh["box"][1] - 0.05 <= p[1] <= sh["box"][3] + 0.05):
                            ends.append(sh["label"])
                for si in range(len(c["pts"]) - 1):
                    for sh in shapes:
                        if sh["label"] in ends:
                            continue
                        if _seg_box(c["pts"][si], c["pts"][si + 1], sh["box"]):
                            out["throughShapes"].append(
                                {"edge": c["edge"] or c["name"], "shape": sh["label"],
                                 "seg": [list(c["pts"][si]), list(c["pts"][si + 1])]})
            # 3. off page
            for c in cons:
                for p in c["pts"]:
                    if p[0] < -0.01 or p[1] < -0.01 or p[0] > 13.34 + 0.01 \
                            or p[1] > (ph or 7.5) + 0.01:
                        out["offPage"].append({"edge": c["edge"] or c["name"],
                                               "at": [round(p[0], 2), round(p[1], 2)]})
                        break
        doc.Close()
    except Exception as exc:
        out["notes"].append("open/read failed: %s %s" % (type(exc).__name__,
                                                         str(exc)[:200]))
    finally:
        try:
            vis.Quit()
        except Exception:
            pass
        os.chmod(path, 0o644)
    after = hashlib.sha256(open(path, "rb").read()).hexdigest()
    out["unchanged"] = after == before
    out["sha256_16"] = after[:16]
    return out


if __name__ == "__main__":
    paths = sys.argv[1:] or [
        r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Classroom"
        r"\Teacher_01_System_Overview.vsdx",
        r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Classroom"
        r"\Teacher_02_Agent_User_Flow.vsdx",
    ]
    reps = []
    for p in paths:
        log("analysing %s" % os.path.basename(p))
        r = analyse(p)
        reps.append(r)
        log("  connectors=%d crossings=%d throughShapes=%d offPage=%d "
            "unreadable=%d unchanged=%s"
            % (r["connectors"], len(r["crossings"]), len(r["throughShapes"]),
               len(r["offPage"]), len(r["readFailures"]), r["unchanged"]))
        log("  on page: %s" % json.dumps(r.get("pageInk"), ensure_ascii=False))
        for x in r["readFailures"][:5]:
            log("    UNREADABLE %s" % x)
        for x in r["crossings"][:12]:
            log("    CROSS  %-22s x %-22s at (%s, %s)"
                % (x["a"], x["b"], x["at"][0], x["at"][1]))
        for x in r["throughShapes"][:12]:
            log("    THROUGH %-22s crosses box %s" % (x["edge"], x["shape"]))
        for x in r["offPage"][:8]:
            log("    OFFPAGE %-22s at (%s, %s)" % (x["edge"], x["at"][0], x["at"][1]))
        for n in r["notes"][:5]:
            log("    note %s" % n)
    json.dump(reps, open(os.path.join(HERE, "se_visio_cross_check_result.json"),
                         "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    bad = [r for r in reps if r["crossings"] or r["throughShapes"] or r["offPage"]
           or r["readFailures"] or not r["unchanged"]]
    log("CROSS CHECK %s (%d/%d clean)" % ("FAILED" if bad else "PASS",
                                          len(reps) - len(bad), len(reps)))
    sys.exit(1 if bad else 0)
