"""CityNexus Visio engine - JSON spec -> native .vsdx via Visio COM, with a
built-in layout/semantics gate. Nothing is reported as done unless the gate
read it back out of the saved file.

Proven shapes of the API on this machine (see se_probe_r6.log / se_probe_r7.log):
  page.Drop(master, pinX, pinY)          works; masters resolved from the
                                         locale-2052 stencils by their Chinese names
  cell.Cells("BeginX").GlueTo(...)       works and is a real glue: moving the shape
                                         moves the connector endpoint
  shape.Cells("LineWeight"/"LinePattern")works; bare "Weight"/"Pattern" DO NOT
  page.Export(png)                       works
  doc.ExportAsFixedFormat(1, pdf, 1, 0)  works
  doc.Pages.Add()                        works (AddAfter does not exist here)

Authoring coordinates are INCHES measured from the TOP-LEFT of an A3 landscape
page; the engine flips Y into Visio's bottom-left system.
"""
from __future__ import annotations

import json
import os
import textwrap
import time

PAGE_W = 16.54   # 420mm
PAGE_H = 11.69   # 297mm
STENCIL_DIR = r"C:\Program Files\Microsoft Office\root\Office16\Visio Content\2052"

# stencil file -> logical key used in specs
STENCILS = {
    "flow": "BASFLO_M.VSSX",
    "basic": "BASIC_M.VSSX",
    "uml": "UUSEME_M.VSSX",
    "cff": "XFUNC_M.VSSX",
    "conn": "CONNEC_M.VSSX",
    "srv": "SERVER_M.VSSX",
}

# node kind -> (stencil key, master name in locale 2052, fallback)
KINDS = {
    "rect":      ("basic", "矩形"),
    "roundrect": ("basic", "圆角矩形"),
    "ellipse":   ("basic", "椭圆形"),
    "cylinder":  ("basic", "圆柱形"),
    "cube":      ("basic", "立方体"),
    "frame":     ("basic", "框架"),
    "process":   ("flow", "流程"),
    "decision":  ("flow", "判定"),
    "terminator": ("flow", "开始/结束"),
    "data":      ("flow", "数据"),
    "database":  ("flow", "数据库"),
    "extdata":   ("flow", "外部数据"),
    "document":  ("flow", "文档"),
    "subprocess": ("flow", "子流程"),
    "onpage":    ("flow", "页面内引用"),
    "offpage":   ("flow", "跨页引用"),
    "actor":     ("uml", "参与者"),
    "usecase":   ("uml", "用例"),
    "subsystem": ("uml", "子系统"),
    "webserver": ("srv", "Web 服务器"),
    "appserver": ("srv", "应用程序服务器"),
    "dbsrv":     ("srv", "数据库服务器"),
    "pool":      ("cff", "泳道列表"),
    "lane":      ("cff", "泳道"),
}

EDGE_KINDS = {
    "include": ("uml", "包含"),
    "extend": ("uml", "扩展"),
    "assoc": ("uml", "关联"),
    "dep": ("uml", "依赖关系"),
    "general": ("uml", "归纳"),
}

# ---- house style -------------------------------------------------------------
PALETTE = {
    # state -> (fill, line)
    "verified":  ("#DCE9F7", "#1F5C99"),
    "built":     ("#FFF2CC", "#BF9000"),
    "planned":   ("#F2F2F2", "#8C8C8C"),
    "external":  ("#E7E1F2", "#6A4C93"),
    "data":      ("#DDEFE4", "#2E7D5B"),
    "agent":     ("#FDE8D8", "#C05A1E"),
    "user":      ("#FFFFFF", "#3A4A5A"),
    "band":      ("#F7F9FC", "#C3CEDD"),
    "laneband":  ("#EEF3FA", "#9FB3CC"),
    "title":     ("#1F3A5F", "#1F3A5F"),
}
BODY_FONT = "Segoe UI"
BODY_SIZE = 9.0
SUB_SIZE = 6.0
TITLE_SIZE = 17.0
SUBTITLE_SIZE = 9.5
LINE_W = "0.017in"
CONN_W = "0.019in"
DASH = "6"      # Line.Pattern: 6 = dash
SOLID = "1"
ARROW_END = "4"   # filled block-ish arrow
ARROW_NONE = "0"

# how much of a shape's width can actually carry a line of text
TEXT_FACTOR = {
    "decision": 0.46, "terminator": 0.70, "usecase": 0.68, "onpage": 0.66,
    "offpage": 0.78, "extdata": 0.80, "data": 0.80, "document": 0.84,
    "subprocess": 0.90, "cylinder": 0.84, "database": 0.78, "actor": 0.90,
}


def _rgb(hexstr):
    h = hexstr.lstrip("#")
    return "RGB(%d,%d,%d)" % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


class GateError(Exception):
    pass


class Builder:
    def __init__(self, spec, out_paths, log):
        self.spec = spec
        self.body_size = float(spec.get("bodySize", BODY_SIZE))
        self.sub_size = float(spec.get("subSize", SUB_SIZE))
        self.out = out_paths
        self.log = log
        self.problems = []
        self.notes = []
        self.style_issues = []
        self.vis = None
        self.doc = None
        self.page = None
        self.shapes = {}
        self.stencils = {}
        self.node_ids = {}
        self.edge_ids = {}
        self.edge_labels = []
        self.edge_count = 0

    # ---------------------------------------------------------------- lifecycle
    def start(self):
        import win32com.client as w32

        self.vis = w32.DispatchEx("Visio.Application")
        # A modal "save changes?" prompt behind an invisible application is how a
        # COM build hangs forever, so suppress prompts before touching anything.
        for prop, val in (("Visible", False), ("AlertResponse", 7), ("ScreenUpdating", 0)):
            try:
                setattr(self.vis, prop, val)
            except Exception as exc:
                self.notes.append("vis.%s not settable (%s)" % (prop, type(exc).__name__))
        self.doc = self.vis.Documents.Add("")
        self.page = self.doc.Pages.Item(1)
        self.page.Name = self.spec.get("pageName", "Page-1")
        for cell, formula in (("PrintPageOrientation", "1"),
                              ("PageWidth", "420mm"),
                              ("PageHeight", "297mm"),
                              ("PrintFitLayerPages", "0")):
            self._cell(self.page.PageSheet, cell, formula)
        for key, fname in STENCILS.items():
            path = os.path.join(STENCIL_DIR, fname)
            if not os.path.exists(path):
                self.problems.append("stencil missing: %s" % fname)
                continue
            self.stencils[key] = self.vis.Documents.OpenEx(path, 16)
        return self

    def finish(self):
        for sd in list(self.stencils.values()):
            try:
                sd.Saved = True
                sd.Close()
            except Exception:
                pass
        try:
            self.doc.Saved = True
            self.doc.Close()
        except Exception:
            pass
        try:
            self.vis.Quit()
        except Exception:
            pass

    # ---------------------------------------------------------------- helpers
    def _cell(self, shape, name, formula):
        try:
            setattr(shape.Cells(name), "FormulaU", formula)
            return True
        except Exception as exc:
            self.style_issues.append("cell %s <- %r failed: %s" % (name, formula, type(exc).__name__))
            return False

    def _cellget(self, shape, name):
        try:
            return shape.Cells(name).ResultIU
        except Exception:
            return None

    def _master(self, stencil_key, master_name):
        sd = self.stencils.get(stencil_key)
        if sd is None:
            return None
        for i in range(1, sd.Masters.Count + 1):
            if sd.Masters.Item(i).Name == master_name:
                return sd.Masters.Item(i)
        return None

    def _flip_y(self, y_top, h):
        return PAGE_H - y_top - h / 2.0

    def _wrap(self, text, width_in, size_pt):
        """Greedy word wrap sized so the text cannot overflow the box."""
        cpl = max(6, int(width_in * 72.0 / (size_pt * 0.52)))
        lines = []
        for para in str(text).split("\n"):
            lines.extend(textwrap.wrap(para, cpl) or [""])
        return lines

    # ---------------------------------------------------------------- nodes
    def add_band(self, b):
        w, h = b["w"], b["h"]
        sh = self.page.DrawRectangle(b["x"], self._flip_y(b["y"], h) - h / 2.0,
                                     b["x"] + w, self._flip_y(b["y"], h) + h / 2.0)
        state = b.get("state", "band")
        fill, line = PALETTE[state]
        self._cell(sh, "FillForegnd", _rgb(fill))
        self._cell(sh, "LineColor", _rgb(line))
        self._cell(sh, "LineWeight", "0.011in")
        self._cell(sh, "LinePattern", b.get("dash", SOLID))
        self._cell(sh, "FillPattern", "1")
        label = b.get("label", "")
        if label:
            t = self._text(b["x"] + 0.14, b["y"] + 0.05, min(w - 0.28, 8.6), label,
                           size=b.get("labelSize", 9.5), bold=True, color="#2A3B4F",
                           align="0")
            t.BringToFront()
        sh.SendToBack()
        return sh

    def _text(self, x_top, y_top, w, text, size=BODY_SIZE, bold=False,
              color="#1B2733", align="1"):
        sh = self.page.DrawRectangle(x_top, self._flip_y(y_top, size / 72.0 * 1.6),
                                     x_top + w, self._flip_y(y_top, size / 72.0 * 1.6)
                                     + size / 72.0 * 1.6)
        sh.Text = text
        self._cell(sh, "FillPattern", "0")
        self._cell(sh, "LinePattern", "0")
        self._cell(sh, "Char.Size", "%gpt" % size)
        self._cell(sh, "Char.Color", _rgb(color))
        if bold:
            self._cell(sh, "Char.Style", "1")
        self._cell(sh, "LeftMargin", "0in")
        self._cell(sh, "RightMargin", "0in")
        self._cell(sh, "TopMargin", "0in")
        self._cell(sh, "BottomMargin", "0in")
        self._cell(sh, "VerticalAlign", "1")
        self._align(sh, align)
        return sh

    def _align(self, sh, mode):
        """mode "0" left, "1" centre - set on the Paragraph section."""
        for attempt_fn in (
            lambda: setattr(sh.CellsSRC(4, 0, "Alignment"), "FormulaU", mode),
            lambda: (sh.AddSection(4),
                     setattr(sh.CellsSRC(4, 0, "Alignment"), "FormulaU", mode)),
        ):
            try:
                attempt_fn()
                return True
            except Exception:
                continue
        self.notes.append("paragraph alignment skipped")
        return False

    def add_node(self, n):
        kind = n["kind"]
        if kind not in KINDS:
            raise GateError("unknown node kind %r" % kind)
        skey, mname = KINDS[kind]
        w, h = n["w"], n["h"]
        pin_x = n["x"] + w / 2.0
        pin_y = self._flip_y(n["y"], h)
        master = None if n.get("plain") else self._master(skey, mname)
        if master is None:
            self.problems.append("master %r (%s) unavailable; rectangle used for %s"
                                 % (mname, skey, n["id"]))
            sh = self.page.DrawRectangle(n["x"], pin_y - h / 2.0, n["x"] + w, pin_y + h / 2.0)
        else:
            sh = self.page.Drop(master, pin_x, pin_y)
        self._cell(sh, "Width", "%gin" % w)
        self._cell(sh, "Height", "%gin" % h)
        self._cell(sh, "PinX", "%gin" % pin_x)
        self._cell(sh, "PinY", "%gin" % pin_y)
        self._cell(sh, "LocPinX", "Width*0.5")
        self._cell(sh, "LocPinY", "Height*0.5")

        fill, line = PALETTE[n.get("state", "verified")]
        self._cell(sh, "FillForegnd", _rgb(fill))
        self._cell(sh, "LineColor", _rgb(line))
        self._cell(sh, "LineWeight", LINE_W)
        self._cell(sh, "LinePattern", DASH if n.get("state") == "planned" else SOLID)
        if kind in ("roundrect", "rect"):
            self._cell(sh, "Rounding", "0.045in")
        self._cell(sh, "VerticalAlign", "1")
        for m in ("LeftMargin", "RightMargin"):
            self._cell(sh, m, "0.05in")
        for m in ("TopMargin", "BottomMargin"):
            self._cell(sh, m, "0.03in")

        main = n["text"]
        sub = n.get("src")
        eff_w = (w - 0.14) * TEXT_FACTOR.get(kind, 1.0)
        lines = self._wrap(main, eff_w, self.body_size)
        txt = "\n".join(lines)
        n_body_lines = len(lines)
        if sub:
            slines = self._wrap(sub, w - 0.12, self.sub_size)
            txt = txt + "\n" + "\n".join(slines)
        sh.Text = txt
        self._cell(sh, "Char.Size", "%gpt" % self.body_size)
        self._cell(sh, "Char.Font", '="%s"' % BODY_FONT)
        if sub:
            try:
                ch = sh.Characters
                ch.Begin = 1
                ch.End = len(txt) - len("\n".join(slines)) - 1
                ch.Size = self.body_size
                try:
                    ch.Style = 1
                except Exception:
                    pass
                ch.Begin = len(txt) - len("\n".join(slines))
                ch.End = len(txt)
                ch.Size = self.sub_size
                try:
                    ch.Color = self.vis.GetColorCell("#5A6B7D")
                except Exception:
                    pass
            except Exception as exc:
                self.notes.append("per-run font sizing skipped on %s (%s)"
                                  % (n["id"], type(exc).__name__))
        needed = n_body_lines * (self.body_size * 1.40 / 72.0) + 0.10
        if sub:
            needed += len(slines) * (self.sub_size * 1.40 / 72.0)
        if needed > h + 1e-6:
            self.problems.append("text overflow: node %s needs %.2fin > box %.2fin"
                                 % (n["id"], needed, h))
        widest = max([len(l) for l in lines] or [0])
        est_w = widest * (self.body_size * 0.52 / 72.0)
        if est_w > eff_w:
            self.problems.append("text width overflow: node %s needs %.2fin > usable "
                                 "%.2fin (%s box %.2fin)"
                                 % (n["id"], est_w, eff_w, kind, w))

        if sub:
            try:
                self._prop(sh, "SourceRef", sub)
            except Exception:
                pass
        self._prop(sh, "State", n.get("state", "verified"))
        self._prop(sh, "NodeId", n["id"])
        sh.BringToFront()
        self.shapes[n["id"]] = sh
        self.node_ids[n["id"]] = sh.ID
        return sh

    def _prop(self, sh, name, value):
        """Store a machine-readable custom property so the drawing can be audited
        shape by shape inside Visio. Non-fatal: a refused row is a note, not a red."""
        try:
            if not sh.SectionExists(243, 0):
                sh.AddSection(243)
            sec = sh.SectionSRC(243)
            try:
                n = sec.Count
            except Exception:
                n = 0
            have = []
            try:
                have = [sec.RowName(i) for i in range(n)]
            except Exception:
                have = []
            if name not in have:
                sec.AddRow(1)
                try:
                    sec.RowName(sec.Count - 1, name)
                except Exception:
                    sec.RowName(n, name)
            row = name
            try:
                sh.CellsSRC(243, row, "Label").FormulaU = '"%s"' % name
                sh.CellsSRC(243, row, "Type").FormulaU = "0"
            except Exception:
                pass
            sh.CellsSRC(243, row, "Value").FormulaU = '"%s"' % str(value).replace('"', "'")
            return True
        except Exception as exc:
            self.notes.append("custom property %s skipped (%s)"
                              % (name, type(exc).__name__))
            return False

    # ---------------------------------------------------------------- edges
    def add_edge(self, e):
        a = self.shapes.get(e["from"])
        b = self.shapes.get(e["to"])
        if a is None or b is None:
            raise GateError("edge endpoint unknown: %r" % (e,))
        kind = e.get("kind", "conn")
        if kind in EDGE_KINDS:
            skey, mname = EDGE_KINDS[kind]
            m = self._master(skey, mname)
            con = self.page.Drop(m, 0.0, 0.0) if m else self.page.Drop(
                self.vis.ConnectorToolDataObject, 0.0, 0.0)
        else:
            con = self.page.Drop(self.vis.ConnectorToolDataObject, 0.0, 0.0)
        glued = 0
        for side, target in (("BeginX", a), ("EndX", b)):
            try:
                con.Cells(side).GlueTo(target.Cells("PinX"))
                glued += 1
            except Exception as exc:
                self.problems.append("glue %s of %s->%s failed: %s"
                                     % (side, e["from"], e["to"], type(exc).__name__))
        if glued != 2:
            self.problems.append("edge %s->%s is not fully glued (%d/2)"
                                 % (e["from"], e["to"], glued))
        state = e.get("state", "verified")
        fill, line = PALETTE.get(state, PALETTE["verified"])
        self._cell(con, "LineColor", _rgb("#3B4A5A" if state != "planned" else "#9AA5B1"))
        self._cell(con, "LineWeight", CONN_W)
        self._cell(con, "LinePattern", DASH if state == "planned" else SOLID)
        self._cell(con, "EndArrow", e.get("endArrow", ARROW_END))
        self._cell(con, "BeginArrow", e.get("beginArrow", ARROW_NONE))
        self._cell(con, "EndArrowSize", e.get("arrowSize", "2"))
        if e.get("route") == "straight":
            self._cell(con, "ConLineRouteExt", "1")
        elif e.get("route") == "orthogonal":
            self._cell(con, "ConLineRouteExt", "2")
        if e.get("label"):
            con.Text = e["label"]
            self._cell(con, "Char.Size", "%gpt" % e.get("labelSize", 7.0))
            self._cell(con, "Char.Color", _rgb("#334D66"))
            self._cell(con, "HideTextLine", "0")
            try:
                bx = (con.Cells("BeginX").ResultIU + con.Cells("EndX").ResultIU) / 2.0
                by = (con.Cells("BeginY").ResultIU + con.Cells("EndY").ResultIU) / 2.0
                lab = self._text(bx - 0.55, PAGE_H - by - 0.02, 1.10, e["label"],
                                 size=e.get("labelSize", 7.0), color="#334D66")
                self._cell(lab, "FillForegnd", _rgb("#FFFFFF"))
                self._cell(lab, "FillPattern", "1")
                self._cell(lab, "FillForegndTrans", "0.55")
                con.Text = ""
                self._cell(con, "HideText", "1")
                self.edge_labels.append(lab.ID)
            except Exception as exc:
                self.notes.append("parked label skipped on %s->%s (%s)"
                                  % (e["from"], e["to"], type(exc).__name__))
        self._prop(con, "FlowEdge", "%s->%s" % (e["from"], e["to"]))
        self.edge_ids["%s->%s" % (e["from"], e["to"])] = con.ID
        if e.get("src"):
            self._prop(con, "SourceRef", e["src"])
        self.edge_count += 1
        return con

    # ---------------------------------------------------------------- frame
    def add_title_block(self):
        self._text(0.35, 0.22, 11.0, self.spec["title"], size=TITLE_SIZE,
                   bold=True, color="#12263F")
        self._text(0.35, 0.62, 11.6, self.spec.get("subtitle", ""),
                   size=SUBTITLE_SIZE, color="#3C5068")
        self._text(9.5, 0.26, 6.7, "%s\n%s" % (self.spec.get("docid", ""),
                                              self.spec.get("revline", "")),
                   size=8.0, color="#3C5068")

    def add_legend(self, items, origin):
        x, y = origin
        self._text(x, y, 2.0, "Legend", size=8.5, bold=True, color="#12263F",
                   align="0")
        cy = y + 0.20
        for it in items:
            fill, line = PALETTE.get(it["state"], PALETTE["verified"])
            sw = self.page.DrawRectangle(x, self._flip_y(cy, 0.15) - 0.075,
                                         x + 0.34, self._flip_y(cy, 0.15) + 0.075)
            self._cell(sw, "FillForegnd", _rgb(fill))
            self._cell(sw, "LineColor", _rgb(line))
            self._cell(sw, "LineWeight", "0.013in")
            self._cell(sw, "LinePattern", DASH if it["state"] == "planned" else SOLID)
            self._cell(sw, "Rounding", "0.03in")
            self._text(x + 0.42, cy - 0.02, it.get("w", 3.4), it["text"], size=7.2,
                       color="#22323F")
            cy += 0.235
        return cy

    def add_footnotes(self, lines, origin, width=15.8):
        y = origin[1]
        for ln in lines:
            self._text(origin[0], y, width, ln, size=6.6, color="#4C5A66",
                       align="0")
            y += 0.155
        return y

    def add_notes(self, lines, origin, width, size):
        x, y = origin
        h = 0.155 * len(lines) + 0.22
        bg = self.page.DrawRectangle(x - 0.08, self._flip_y(y, h) - h / 2.0,
                                    x + width + 0.08, self._flip_y(y, h) + h / 2.0)
        self._cell(bg, "FillForegnd", _rgb("#FBFCFE"))
        self._cell(bg, "LineColor", _rgb("#C3CEDD"))
        self._cell(bg, "LineWeight", "0.010in")
        self._cell(bg, "LinePattern", SOLID)
        self._cell(bg, "Rounding", "0.05in")
        bg.SendToBack()
        cy = y + 0.10
        for ln in lines:
            wrapped = self._wrap(ln, width, size)
            for wl in wrapped:
                self._text(x, cy, width, wl, size=size, color="#33424F", align="0")
                cy += size * 1.30 / 72.0
            cy += 0.03
        return cy

    # ---------------------------------------------------------------- checks
    def gate(self):
        """Refuse to publish a diagram that fails its own layout/semantics rules."""
        bad = []
        ids = [n["id"] for n in self.spec["nodes"]]
        if len(set(ids)) != len(ids):
            bad.append("duplicate node ids")
        for n in self.spec["nodes"]:
            if n["x"] < 0 or n["y"] < 0 or n["x"] + n["w"] > PAGE_W or n["y"] + n["h"] > PAGE_H:
                bad.append("node %s outside page bounds" % n["id"])
        # real overlap between non-band nodes
        rects = [(n["id"], n["x"], n["y"], n["w"], n["h"]) for n in self.spec["nodes"]]
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, b = rects[i], rects[j]
                if a[0] in _nolabel(self.spec) or b[0] in _nolabel(self.spec):
                    continue
                ox = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
                oy = min(a[2] + a[4], b[2] + b[4]) - max(a[2], b[2])
                if ox > 0.02 and oy > 0.02:
                    bad.append("overlap %s/%s (%.2fin x %.2fin)" % (a[0], b[0], ox, oy))
        ins = {k: 0 for k in ids}
        outs = {k: 0 for k in ids}
        labels = {}
        for e in self.spec["edges"]:
            outs[e["from"]] += 1
            ins[e["to"]] += 1
            labels.setdefault((e["from"], e["to"]), []).append(e.get("label", ""))
        for n in self.spec["nodes"]:
            role = n.get("role")
            if role in ("note", "container"):
                continue
            if ins[n["id"]] == 0 and outs[n["id"]] == 0:
                bad.append("orphan node %s has no connection at all" % n["id"])
            if role == "start" and ins[n["id"]] > 0:
                bad.append("node %s is a start but has an incoming edge" % n["id"])
            if role == "end" and outs[n["id"]] > 0:
                bad.append("node %s is an end but still has an outgoing edge" % n["id"])
            if role not in ("start", "end") and n["kind"] in ("terminator",):
                bad.append("terminator %s needs role=start or role=end" % n["id"])
            if n["kind"] == "decision":
                k = outs[n["id"]]
                if k < 2:
                    bad.append("decision %s has only %d outgoing branch(es)" % (n["id"], k))
                outs_labels = [e.get("label") for e in self.spec["edges"] if e["from"] == n["id"]]
                if any(not l for l in outs_labels):
                    bad.append("decision %s has an unlabelled branch" % n["id"])
        if self.spec.get("edgeRule", "shortHop") == "shortHop":
            bad.extend(self.rule_short_hop())
        glued_expected = 2 * len(self.spec["edges"])
        actual = self.page.Connects.Count
        if actual != glued_expected:
            bad.append("glue count: expected %d got %d" % (glued_expected, actual))
        if self.problems:
            bad.extend(self.problems)
        return {"edges": len(self.spec["edges"]), "nodes": len(ids),
                "shapeIds": self.node_ids, "edgeIds": self.edge_ids,
                "connects": actual, "expectedConnects": glued_expected,
                "failures": bad, "notes": self.notes,
                "styleIssues": self.style_issues[:40]}


    def rows(self):
        """Group band rectangles into rows by vertical overlap, then map each
        node id to the row it sits in."""
        bands = self.spec.get("bands", [])
        ivs = sorted([(b["y"], b["y"] + b["h"], i) for i, b in enumerate(bands)])
        groups = []
        for lo, hi, i in ivs:
            placed = False
            for g in groups:
                if lo < g["hi"] - 0.02 and hi > g["lo"] + 0.02:
                    g["lo"] = min(g["lo"], lo)
                    g["hi"] = max(g["hi"], hi)
                    g["members"].append(i)
                    placed = True
                    break
            if not placed:
                groups.append({"lo": lo, "hi": hi, "members": [i]})
        for g in groups:                      # merge transitively-overlapping
            for h in groups:
                if g is not h and h["lo"] < g["hi"] - 0.02 and h["hi"] > g["lo"] + 0.02:
                    g["lo"] = min(g["lo"], h["lo"])
                    g["hi"] = max(g["hi"], h["hi"])
                    g["members"].extend(h["members"])
        rows = []
        for g in groups:
            g["lo"] = min(g["lo"], g["hi"])
        for g in sorted(groups, key=lambda x: x["lo"]):
            if rows and abs(rows[-1]["lo"] - g["lo"]) < 0.02:
                continue
            rows.append(g)
        band_of = {}
        for ri, g in enumerate(rows):
            for bi in set(g["members"]):
                band_of[bi] = ri
        node_row = {}
        for n in self.spec["nodes"]:
            cy = n["y"] + n["h"] / 2.0
            best, bestd = None, 1e9
            for bi, b in enumerate(self.spec.get("bands", [])):
                if b["y"] - 0.02 <= cy <= b["y"] + b["h"] + 0.02:
                    d = min(abs(cy - b["y"]), abs(cy - (b["y"] + b["h"])))
                    if d < bestd:
                        best, bestd = bi, d
            node_row[n["id"]] = band_of.get(best, -1) if best is not None else -1
        return rows, node_row

    def rule_short_hop(self):
        bad = []
        _rows, nrow = self.rows()
        byid = dict((n["id"], n) for n in self.spec["nodes"])
        for e in self.spec["edges"]:
            a, z = e["from"], e["to"]
            na, nz = byid[a], byid[z]
            ra, rz = nrow[a], nrow[z]
            if ra < 0 or rz < 0:
                bad.append("edge %s->%s: a shape is not inside any band" % (a, z))
                continue
            if abs(ra - rz) > 1:
                bad.append("edge %s->%s jumps %d bands - it would have to be routed "
                           "over an intervening layer" % (a, z, abs(ra - rz)))
                continue
            ax0, ax1 = na["x"], na["x"] + na["w"]
            zx0, zx1 = nz["x"], nz["x"] + nz["w"]
            gap = max(ax0, zx0) - min(ax1, zx1)
            if ra == rz:
                lo, hi = sorted((min(ax0, ax1), min(zx0, zx1))), sorted((max(ax0, ax1), max(zx0, zx1)))
                x_lo = min(ax0, zx0)
                x_hi = max(ax1, zx1)
                for m in self.spec["nodes"]:
                    if m["id"] in (a, z) or nrow[m["id"]] != ra:
                        continue
                    mx0, mx1 = m["x"], m["x"] + m["w"]
                    if mx0 > x_lo + 0.05 and mx1 < x_hi - 0.05:
                        bad.append("same-band edge %s->%s reaches over shape %s"
                                   % (a, z, m["id"]))
            elif gap > 0.70:
                bad.append("edge %s->%s has a %.2fin horizontal gap with no overlap; "
                           "the route would cut across its neighbours" % (a, z, gap))
        return bad

    # ---------------------------------------------------------------- publish
    def build(self):
        self.start()
        try:
            self.add_title_block()
            for b in self.spec.get("bands", []):
                self.add_band(b)
            for n in self.spec["nodes"]:
                self.add_node(n)
            for e in self.spec["edges"]:
                self.add_edge(e)
            if self.spec.get("legend"):
                self.add_legend(self.spec["legend"], self.spec["legendOrigin"])
            if self.spec.get("footnotes"):
                self.add_footnotes(self.spec["footnotes"], self.spec["footnoteOrigin"])
            if self.spec.get("notes"):
                self.add_notes(self.spec["notes"], self.spec.get("notesOrigin", (0.46, 7.9)),
                               self.spec.get("notesWidth", 9.0),
                               self.spec.get("notesSize", 6.4))
            report = self.gate()
            json.dump(report, open(self.out["gate"], "w", encoding="utf-8"),
                      indent=1, ensure_ascii=False)
            if report["failures"]:
                # a failing diagram still gets a debug preview so the layout can be
                # fixed by eye - but no file is written into the deliverable folder
                for suffix, cell in (("png", "debugPng"), ("pdf", "debugPdf")):
                    path = self.out.get(cell)
                    if not path:
                        continue
                    try:
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        if suffix == "png":
                            self.page.Export(path)
                        else:
                            self.doc.ExportAsFixedFormat(1, path, 1, 0)
                    except Exception as exc:
                        self.notes.append("debug %s export failed: %s" % (suffix, type(exc).__name__))
                raise GateError("%d layout/semantics failure(s); first: %s"
                                % (len(report["failures"]), report["failures"][0]))
            self.doc.SaveAs(self.out["vsdx"])
            self.page.Export(self.out["png"])
            self.doc.ExportAsFixedFormat(1, self.out["pdf"], 1, 0)
            return report
        finally:
            self.finish()


def _nolabel(spec):
    return set(spec.get("overlapExempt", []))


def build_diagram(spec, out_dir, log):
    stem = os.path.splitext(os.path.basename(spec["file"]))[0]
    paths = {
        "vsdx": os.path.join(out_dir, spec["file"]),
        "png": os.path.join(out_dir, "previews", stem + ".png"),
        "pdf": os.path.join(out_dir, "previews", stem + ".pdf"),
        "gate": os.path.join(out_dir, "previews", stem + ".gate.json"),
    }
    for p in paths.values():
        d = os.path.dirname(p)
        if d:
            os.makedirs(d, exist_ok=True)
        if os.path.exists(p):
            os.remove(p)
    t0 = time.time()
    b = Builder(spec, paths, log)
    rep = b.build()
    sizes = {k.split("_")[-1]: (os.path.getsize(v) if os.path.exists(v) else 0)
             for k, v in paths.items() if k != "gate"}
    log("  gate ok: nodes=%d edges=%d connects=%d in %.1fs; files=%s"
        % (rep["nodes"], rep["edges"], rep["connects"], time.time() - t0, sizes))
    return rep, paths
