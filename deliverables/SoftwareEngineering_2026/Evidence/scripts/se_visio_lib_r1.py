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
import re
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
    "foot":      ("#FFFFFF", "#B9C4D0"),
    "title":     ("#1F3A5F", "#1F3A5F"),
}
BODY_FONT = "Segoe UI"
CJK_FONT = "Microsoft YaHei"
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
        self.cur = spec
        self.spec_nodes = spec.get('nodes', [])
        self.spec_edges = spec.get('edges', [])
        self.spec_bands = spec.get('bands', [])
        self.edge_ids = {}
        self.edge_labels = []
        self.prop_writes = {}
        # Chrome (legend, note blocks, footnotes, parked connector labels) is
        # drawn outside the node grid, so the layout gate has to know where it
        # landed: two of the shipped diagrams had a note block sitting on top of
        # the legend and a parked label dumped in a far corner.
        self.chrome = []
        self.parked = []
        self.band_strips = []
        # where the ink of each node's text actually lies inside its box, so a
        # connector label can be allowed to bridge a border strip without ever
        # being allowed to print over a word
        self.node_text_rects = {}
        self.chrome_by_page = {}
        self._rowcache = {}
        self.page_no = 1
        # a deck sheet is 16:9, a design drawing is A3 landscape: the bounds and
        # the wrap widths must follow the sheet that is actually being drawn
        self.PW = float(spec.get("pageW", PAGE_W))
        self.PH = float(spec.get("pageH", PAGE_H))
        self.min_body = float(spec.get("minBodySize", 0))
        self.prop_failures = []
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
                              ("PageWidth", "%gin" % self.PW),
                              ("PageHeight", "%gin" % self.PH),
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
        return self.PH - y_top - h / 2.0

    @staticmethod
    def _wunit(ch):
        """Width of one glyph in em.

        0.58 em for everything was a Latin-only assumption: a Chinese glyph is
        close to a full em, so a 12-字 label was measured as if it needed the
        room of 12 Latin letters and every Chinese box overflowed while the gate
        still reported it as fitting.
        """
        o = ord(ch)
        if (0x2E80 <= o <= 0x9FFF or 0x3000 <= o <= 0x303F
                or 0xFF00 <= o <= 0xFFEF or 0xAC00 <= o <= 0xD7AF):
            return 1.02
        if ch in " ,.;:()[]{}|/-+&%$#'\"":
            return 0.42
        return 0.58

    def text_width_in(self, text, size_pt):
        return sum(self._wunit(c) for c in str(text)) * size_pt / 72.0

    def _wrap(self, text, width_in, size_pt):
        """Greedy word wrap sized so the text cannot overflow the box.

        The wrap uses a deliberately wider per-character estimate (0.58) than the
        audit rule (0.52): breaking the line one word earlier is free, while a
        line that the checker measures as too long is a visible defect. The two
        estimates disagreeing by design is what keeps the drawn text inside the
        shape it belongs to.
        """
        avail = max(0.30, width_in)
        lines = []
        for para in str(text).split("\n"):
            cur = ""
            for tok in [c for c in re.split(r"(?<=[ \t])|(?<=[，。、；：])"
                                      "|(?=[，。、；：])", para) if c]:
                if self.text_width_in(tok, size_pt) > avail:
                    # a token wider than the box (a Chinese run has no spaces to
                    # break at) is split one glyph at a time
                    if cur:
                        lines.append(cur.strip())
                        cur = ""
                    while tok:
                        take = 0
                        while (take < len(tok) and self.text_width_in(
                                tok[:take + 1], size_pt) <= avail):
                            take += 1
                        take = max(1, take)
                        lines.append(tok[:take])
                        tok = tok[take:]
                    continue
                if not cur:
                    cur = tok
                elif self.text_width_in(cur + tok, size_pt) <= avail:
                    cur += tok
                else:
                    lines.append(cur.strip())
                    cur = tok
            lines.append(cur.strip())
        return [l for l in lines if l] or [""]

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
            self.band_strips.append({"band": b.get("label", "")[:28],
                                     "x": b["x"], "y": b["y"],
                                     "w": min(w, 8.6 + 0.28),
                                     "h": b.get("labelSize", 9.5) / 72.0 * 1.6 + 0.09})
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
        # hideSrc: the reference stays in Shape Data and is not drawn, so a
        # classroom sheet can carry the same provenance without a file path on
        # the projected image
        drawn = None if n.get("hideSrc") else sub
        # a briefing sheet needs smaller type in narrow columns than a design
        # drawing does, so a node may carry its own body size
        bs = float(n.get("size") or self.body_size)
        eff_w = (w - 0.14) * TEXT_FACTOR.get(kind, 1.0)
        lines = self._wrap(main, eff_w, bs)
        txt = "\n".join(lines)
        n_body_lines = len(lines)
        slines = []
        if drawn:
            slines = self._wrap(drawn, eff_w, self.sub_size)
            txt = txt + "\n" + "\n".join(slines)
        sh.Text = txt
        self._cell(sh, "Char.Size", "%gpt" % bs)
        self._cell(sh, "Char.Font", '="%s"' % (self.spec.get("font") or BODY_FONT))
        if drawn:
            try:
                ch = sh.Characters
                ch.Begin = 1
                ch.End = len(txt) - len("\n".join(slines)) - 1
                ch.Size = bs
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
        needed = n_body_lines * (bs * 1.40 / 72.0) + 0.10
        if drawn:
            needed += len(slines) * (self.sub_size * 1.40 / 72.0)
        if not main.strip():
            # a marker shape carries no text, so there is nothing to overflow;
            # measuring an empty string against a narrow box produced a false
            # "usable -0.03in" failure on the briefing sheet
            needed = 0.0
        elif n.get("hideSrc"):
            # the citation is stored, not drawn, so only the body needs room
            needed = n_body_lines * (bs * 1.40 / 72.0) + 0.10
        if needed > h + 1e-6:
            self.problems.append("text overflow: node %s needs %.2fin > box %.2fin"
                                 % (n["id"], needed, h))
        widest = max([self.text_width_in(l, bs) for l in lines] or [0.0]) \
            if main.strip() else 0.0
        est_w = widest
        if main.strip() and est_w > eff_w:
            self.problems.append("text width overflow: node %s needs %.2fin > usable "
                                 "%.2fin (%s box %.2fin)"
                                 % (n["id"], est_w, eff_w, kind, w))
        # the small second line is drawn inside the same box, so it has to clear
        # the same walls; the first version only measured the body text and every
        # citation line in the shipped drawings overflowed its shape
        if drawn and slines and main.strip():
            ws = max(len(l) for l in slines)
            est_ws = ws * (self.sub_size * 0.52 / 72.0)
            if est_ws > eff_w:
                self.problems.append(
                    "citation width overflow: node %s needs %.2fin for %r > usable "
                    "%.2fin (box %.2fin); shorten the citation or widen the shape"
                    % (n["id"], est_ws, max(slines, key=len), eff_w, w))

        # The ink is centred inside the box (VerticalAlign=1, paragraph centre),
        # so its rectangle is derivable: this is what lets a connector label
        # cross a shape's border strip while the gate still refuses to let it
        # print over a word.
        if main.strip():
            ink_h = n_body_lines * (bs * 1.40 / 72.0)
            if drawn and slines:
                ink_h += len(slines) * (self.sub_size * 1.40 / 72.0)
            ink_w = est_w + 0.06
            self.node_text_rects[n["id"]] = {
                "x": n["x"] + max(0.0, (w - ink_w) / 2.0),
                "y": n["y"] + max(0.0, (h - ink_h) / 2.0),
                "w": min(w, ink_w), "h": min(h, ink_h)}

        if sub:
            try:
                self._prop(sh, "SourceRef", sub)
            except Exception:
                pass
        try:
            # belt and braces: if a label is still a hair too wide for its shape,
            # let Visio shrink it rather than let ink cross the border
            self._cell(sh, "ShrinkAutoFit", "1")
        except Exception as exc:
            self.notes.append("ShrinkAutoFit skipped on %s (%s)"
                              % (n["id"], type(exc).__name__))
        self._prop(sh, "State", n.get("state", "verified"))
        self._prop(sh, "NodeId", n["id"])
        sh.BringToFront()
        self.shapes[n["id"]] = sh
        # a spec id may legitimately appear on more than one sheet (a parent use
        # case repeated on the detail page), so the audit map keeps every
        # occurrence instead of letting the last page overwrite the first.
        self.node_ids.setdefault(n["id"], []).append([self.page_no, sh.ID])
        return sh

    def _cellstr(self, cell):
        for attr in ("String", "StrV", "ResultStr"):
            try:
                v = getattr(cell, attr)
            except Exception:
                continue
            if isinstance(v, str):
                return v
        return None

    def _prop_row(self, sh, name):
        """Numeric index of the Shape Data row named `name`, or None."""
        cache = self._rowcache.setdefault(sh.ID, {})
        if name in cache:
            return cache[name]
        try:
            sec = sh.SectionSRC(243)
            n = sec.Count
        except Exception:
            return None
        for i in range(n):
            try:
                row = sec.Row(i)
                nm = getattr(row, "NameString", None) or getattr(row, "Name", None)
            except Exception:
                continue
            if nm == name:
                cache[name] = i
                return i
        return None

    def _prop(self, sh, name, value):
        """Write Shape Data through the qualified cell name and read it back.

        AddNamedRow creates the row; CellsU("Prop.<name>.<cell>") addresses it
        by name because CellsSRC's Row and Column arguments are I4 here. The
        value is read back before returning, so a property that did not land is
        a gate failure rather than a note.
        """
        value = str(value)
        path = "Prop.%s" % name
        try:
            if not sh.SectionExists(243, 0):
                sh.AddSection(243)
            if self._prop_row(sh, name) is None:
                made = None
                for tag in (-1, 0):
                    try:
                        made = sh.AddNamedRow(243, name, tag)
                        break
                    except Exception:
                        continue
                if made is None and self._prop_row(sh, name) is None:
                    raise AssertionError("could not create row %r" % name)
            sh.CellsU(path + ".Label").FormulaU = '"%s"' % name
            sh.CellsU(path + ".Prompt").FormulaU = '"%s"' % name
            sh.CellsU(path + ".Type").FormulaU = "0"
            sh.CellsU(path + ".Value").FormulaU = '"%s"' % value.replace('"', "'")
            cell = sh.CellsU(path + ".Value")
            got = None
            try:
                f = cell.FormulaU
                if isinstance(f, str):
                    got = f[1:-1] if len(f) >= 2 and f[0] == '"' and f[-1] == '"' else f
            except Exception:
                pass
            if got is None:
                try:
                    got = cell.ResultStrU("")
                except Exception:
                    pass
            if got != value:
                raise AssertionError("read back %r, expected %r" % (got, value))
            self.prop_writes.setdefault((self.page_no, sh.ID), {})[name] = got
            return True
        except Exception as exc:
            self.prop_failures.append(
                "shape %s (id %s) property %s: %s: %s"
                % (getattr(sh, "Name", "?"), getattr(sh, "ID", "?"), name,
                   type(exc).__name__, str(exc)[:140]))
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
        # On a teaching sheet a label that has to sit on top of its own box is
        # the exact defect the teacher complained about (the 否 that printed over
        # "需要修改吗？"), so `labelStrict` drops the loose second pass and lets
        # the build fail instead. The engineering drawings keep the old behaviour.
        strict_passes = (True, False) if not self.spec.get("labelStrict") else (True,)
        if e.get("label"):
            size = e.get("labelSize", 7.0)
            txt = e["label"]
            one = min(1.60, max(0.62, len(txt) * size * 0.52 / 72.0))
            if self.spec.get("labelStrict"):
                # the 0.52 em above is a Latin estimate: a Chinese connector
                # label is nearly twice as wide per glyph, so the white backing
                # came out narrower than the text and the extra glyphs spilled
                # onto the neighbouring box
                one = min(2.60, max(0.62, self.text_width_in(txt, size) + 0.14))
            row = size / 72.0 * 1.6
            spot = None
            # a wide single line first; if the corridors are that tight, take a
            # narrower box and let the text wrap over two or three rows instead
            for w, h in ((one, row), (max(0.62, one * 0.62), row * 2),
                         (0.62, row * 3)):
                spot = self._park_spot(e, w, h, strict_passes)
                if spot:
                    w_used, h_used = w, h
                    break
            if spot is None:
                self.problems.append("no clear place for the label %r on %s->%s; "
                                     "the text would sit on a shape or run off the page"
                                     % (txt, e["from"], e["to"]))
            else:
                px, py = spot
                lab = self._text(px, py, w_used, txt, size=size, color="#334D66")
                self._cell(lab, "FillForegnd", _rgb("#FFFFFF"))
                self._cell(lab, "FillPattern", "1")
                self._cell(lab, "FillForegndTrans", "0.35")
                self.parked.append({"kind": "label", "x": px, "y": py,
                                    "w": w_used, "h": h_used,
                                    "for": "%s->%s" % (e["from"], e["to"])})
                self.edge_labels.append(lab.ID)
            self._cell(con, "Char.Size", "%gpt" % size)
            self._cell(con, "Char.Color", _rgb("#334D66"))
            con.Text = ""
            try:
                self._cell(con, "HideText", "1")
            except Exception:
                pass
        self._prop(con, "FlowEdge", "%s->%s" % (e["from"], e["to"]))
        self.edge_ids.setdefault("%s->%s" % (e["from"], e["to"]), []).append(
            [self.page_no, con.ID])
        if e.get("src"):
            self._prop(con, "SourceRef", e["src"])
        self.edge_count += 1
        return con

    # ---------------------------------------------------------------- frame
    def add_title_block(self):
        cur = self.cur
        # The header geometry was written for the A3 engineering sheets; the 16:9
        # briefing sheets are narrower, so a fixed 9.5in x 6.7in id block would
        # hang off the right edge and the audit would never see it (title text is
        # chrome, not a node). Derive both halves from the page width instead.
        if self.PW > 14.0:
            tw, sw, dx, dw = 11.0, 11.6, 9.5, 6.7
        else:
            tw, sw, dx, dw = self.PW - 4.6, self.PW - 4.0, self.PW - 4.35, 4.0
        self._text(0.35, 0.22, tw, cur.get("title", self.spec["title"]),
                   size=TITLE_SIZE, bold=True, color="#12263F", align="0")
        self._text(0.35, 0.62, sw, cur.get("subtitle", self.spec.get("subtitle", "")),
                   size=float(cur.get("subtitleSize",
                                      self.spec.get("subtitleSize", SUBTITLE_SIZE))),
                   color="#3C5068", align="0")
        self._text(dx, 0.26, dw, "%s\n%s" % (
            cur.get("docid", self.spec.get("docid", "")),
            cur.get("revline", self.spec.get("revline", ""))),
            size=8.0, color="#3C5068", align="0")

    def _node_rect(self, nid):
        for n in self.spec_nodes:
            if n["id"] == nid:
                return n
        return None

    @staticmethod
    def _hit(a, b):
        return (a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]
                and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"])

    def _park_spot(self, e, w, h, strict_passes=(True, False)):
        """Where a connector's text can lie without covering anything.

        The first version took the connector's own endpoints, which are still
        0,0 at that moment in a build, so labels were dumped in the corner of
        the sheet. Candidates are now generated from the two shapes the edge
        joins and rejected against every other shape, band label and note block
        on the page; if nothing is clear the build fails instead of shipping
        unreadable text.
        """
        a = self._node_rect(e["from"])
        b = self._node_rect(e["to"])
        if not a or not b:
            return None
        ax, ay = a["x"] + a["w"] / 2.0, a["y"] + a["h"] / 2.0
        bx, by = b["x"] + b["w"] / 2.0, b["y"] + b["h"] / 2.0
        blockers = [n for n in self.spec_nodes
                    if n["id"] not in (e["from"], e["to"])]
        others = list(self.chrome) + list(self.parked) + list(self.band_strips)
        # first pass keeps the label clear of its own two shapes as well; if the
        # link is too short for that, the second pass lets it touch an endpoint but
        # still not cover anything else on the sheet
        if self.spec.get("labelStrict"):
            # A Chinese label is wider than the corridor between two adjacent
            # boxes (用户确认后 measures 1.13in against a 0.55in gap on the
            # overview sheet), so "stay off both shapes" pushed it a whole row
            # away from its own line and the reader could not tell which arrow
            # it belonged to. On a teaching sheet the thing that must never be
            # covered is a word, not a border, so try the positions on the line
            # first - avoiding every shape's ink - and only then fall back to a
            # spot that clears both shapes entirely. A label that may cover its
            # own two shapes' words is never offered: that is the exact defect
            # (「否」 printed over 「需要修改吗？」) labelStrict exists to stop.
            ink = [self.node_text_rects.get(n["id"]) or n for n in self.spec_nodes]
            for avoid in (ink, blockers + [a, b]):
                spot = self._spot_scan(ax, ay, bx, by, w, h, avoid, others)
                if spot:
                    return spot
            return None
        for strict in strict_passes:
            avoid = blockers + ([a, b] if strict else [])
            spot = self._spot_scan(ax, ay, bx, by, w, h, avoid, others)
            if spot:
                return spot
        return None

    def _spot_scan(self, ax, ay, bx, by, w, h, avoid, others):
        # walk the line from one shape to the other, and at each stop try the
        # corridor positions around it; the wider the nudge range, the more
        # likely a label finds a gap between two rows instead of sitting on one
        for frac in (0.5, 0.38, 0.62, 0.28, 0.72, 0.18, 0.82, 0.1, 0.9):
            cx = ax + (bx - ax) * frac
            cy = ay + (by - ay) * frac
            for dy in (0.0, -0.13, 0.13, -0.26, 0.26, -0.40, 0.40, -0.55, 0.55,
                       -0.70, 0.70, -0.88, 0.88):
                for dx in (0.0, -0.30, 0.30, -0.60, 0.60, -0.95, 0.95):
                    x = cx - w / 2.0 + dx
                    y = cy - h / 2.0 + dy
                    if x < 0.18 or y < 0.18:
                        continue
                    if x + w > self.PW - 0.18 or y + h > self.PH - 0.18:
                        continue
                    box = {"x": x, "y": y, "w": w, "h": h}
                    if any(self._hit(box, n) for n in avoid):
                        continue
                    if any(self._hit(box, c) for c in others):
                        continue
                    return x, y
        return None

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
        self.chrome.append({"kind": "legend", "x": x, "y": y - 0.06,
                            "w": 0.42 + max([it.get("w", 3.4) for it in items] or [3.4]),
                            "h": (cy - y) + 0.10})
        return cy

    def add_footnotes(self, lines, origin, width=15.8):
        y = origin[1]
        for ln in lines:
            self._text(origin[0], y, width, ln, size=6.6, color="#4C5A66",
                       align="0")
            y += 0.155
        self.chrome.append({"kind": "footnotes", "x": origin[0], "y": origin[1] - 0.05,
                            "w": width, "h": (y - origin[1]) + 0.05})
        return y

    def add_notes(self, lines, origin, width, size):
        x, y = origin
        # the block's height has to count the lines the text actually wraps into,
        # otherwise the note claims to be four rows tall, prints seven, and lands
        # on whatever sits below it
        rows = sum(max(1, len(self._wrap(ln, width, size))) for ln in lines)
        h = rows * (size * 1.30 / 72.0) + 0.24
        self.chrome.append({"kind": "notes", "x": x - 0.08, "y": y,
                            "w": width + 0.16, "h": h})
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
                # one shape per row, as wide as its own ink. The paragraph
                # alignment cell cannot be reached under this binding (the gate
                # logs "paragraph alignment skipped" for every text box on the
                # sheet), and a full-width box centres each row - which is what
                # made the note block read as right-aligned ragged text.
                self._text(x, cy, max(0.2, self.text_width_in(wl, size)), wl,
                           size=size, color="#33424F", align="0")
                cy += size * 1.30 / 72.0
            cy += 0.03
        return cy

    # ---------------------------------------------------------------- checks
    def rule_chrome(self):
        """Legend, note blocks, footnotes and parked connector labels are not spec
        nodes, so the node overlap rule never looked at them - which is how a note
        block ended up printed over the legend. Everything drawn outside the grid
        must sit inside the sheet, off the shapes, and off each other, and no shape
        may sit under a band's own title."""
        bad = []
        rects = []
        for c in list(self.chrome) + list(self.parked):
            rects.append((c, "%s %s" % (c["kind"], c.get("for", c.get("name", "")))))
        for c, who in rects:
            if c["x"] < 0 or c["y"] < 0 or c["x"] + c["w"] > self.PW or \
                    c["y"] + c["h"] > self.PH:
                bad.append("chrome %s runs off the sheet (%.2f,%.2f %.2fx%.2f)"
                           % (who, c["x"], c["y"], c["w"], c["h"]))
            # a connector's own label may lie across its own two shapes - that is
            # what a label on a short link looks like - but never a third one
            own = set((c.get("for") or "").split("->")) if c.get("for") else set()
            for n in self.spec_nodes:
                if n["id"] in own:
                    continue
                if self._hit(c, n):
                    bad.append("chrome %s covers node %s" % (who, n["id"]))
        if self.spec.get("labelStrict"):
            # the parking pass below is allowed to bridge a border strip, so the
            # invariant has to be stated where it can fail the build: on a
            # teaching sheet no label may print over a word - that is the exact
            # defect (「否」 over 「需要修改吗？」) that labelStrict was born for
            for c, who in rects:
                if c["kind"] != "label":
                    continue
                for nid, ink in sorted(self.node_text_rects.items()):
                    if self._hit(c, ink):
                        bad.append("label %s prints over the text of node %s"
                                   % (who, nid))
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, wa = rects[i]
                b, wb = rects[j]
                if self._hit(a, b):
                    bad.append("chrome %s overlaps chrome %s" % (wa, wb))
        for s in self.band_strips:
            for n in self.spec_nodes:
                if self._hit(s, n):
                    bad.append("band title %r is covered by node %s - the row would "
                               "read as an unlabelled block"
                               % (s["band"], n["id"]))
        # a panel with nothing in it reads as an unfinished box
        for b in self.spec_bands:
            if not b.get("label"):
                continue
            inner = [n for n in self.spec_nodes
                     if n["x"] >= b["x"] - 0.01 and n["y"] >= b["y"] - 0.01
                     and n["x"] + n["w"] <= b["x"] + b["w"] + 0.01
                     and n["y"] + n["h"] <= b["y"] + b["h"] + 0.01]
            covered_by_chrome = [c for c in rects if self._hit(b, dict(c[0]))]
            if not inner and not covered_by_chrome:
                bad.append("band %r holds no shape and no note - it would print as "
                           "an empty dashed box" % b["label"][:40])
        return bad

    def gate(self):
        """Refuse to publish a diagram that fails its own layout/semantics rules."""
        bad = []
        ids = [n["id"] for n in self.spec_nodes]
        if len(set(ids)) != len(ids):
            bad.append("duplicate node ids")
        for n in self.spec_nodes:
            if n["x"] < 0 or n["y"] < 0 or n["x"] + n["w"] > self.PW or                     n["y"] + n["h"] > self.PH:
                bad.append("node %s outside page bounds" % n["id"])
        # real overlap between non-band nodes
        rects = [(n["id"], n["x"], n["y"], n["w"], n["h"]) for n in self.spec_nodes]
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, b = rects[i], rects[j]
                if a[0] in _nolabel(self) or b[0] in _nolabel(self):
                    continue
                ox = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
                oy = min(a[2] + a[4], b[2] + b[4]) - max(a[2], b[2])
                if ox > 0.02 and oy > 0.02:
                    bad.append("overlap %s/%s (%.2fin x %.2fin)" % (a[0], b[0], ox, oy))
        ins = {k: 0 for k in ids}
        outs = {k: 0 for k in ids}
        labels = {}
        for e in self.spec_edges:
            outs[e["from"]] += 1
            ins[e["to"]] += 1
            labels.setdefault((e["from"], e["to"]), []).append(e.get("label", ""))
        for n in self.spec_nodes:
            # a deck sheet is read from across a room or on a tablet: text below
            # the declared body size is a defect even when it fits the box
            if self.min_body and float(n.get("size") or self.body_size) <                     self.min_body and (n.get("text") or "").strip() and                     n.get("role") not in ("foot",):
                bad.append("node %s is set in %gpt, below the %gpt floor this sheet "
                           "declares - it will not read on a tablet"
                           % (n["id"], float(n.get("size") or self.body_size),
                              self.min_body))
            role = n.get("role")
            if role in ("note", "container", "foot"):
                continue
            if self.cur.get("barsOnly"):
                # a bar chart sheet has no connectors by design: every shape is a
                # span of dates, so the flow rules (orphan, start/end, decision
                # branches) do not apply and would refuse a legitimate view
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
                outs_labels = [e.get("label") for e in self.spec_edges if e["from"] == n["id"]]
                if any(not l for l in outs_labels):
                    bad.append("decision %s has an unlabelled branch" % n["id"])
        if getattr(self, "cur", self.spec).get("edgeRule", "shortHop") == "shortHop":
            bad.extend(self.rule_short_hop())
        bad.extend(self.rule_chrome())
        glued_expected = 2 * len(self.spec_edges)
        actual = self.page.Connects.Count
        if actual != glued_expected:
            bad.append("glue count: expected %d got %d" % (glued_expected, actual))
        # Every node owes NodeId + State, plus SourceRef when the spec cites a
        # source for it; every connector owes FlowEdge, plus SourceRef when the
        # spec anchors the edge. On the design drawings every node carries a
        # citation, so this is 3 per node there; a bar-chart sheet legitimately
        # has markers with nothing to cite.
        want_props = (sum(3 if (n.get("src") or "").strip() else 2
                          for n in self.spec_nodes)
                      + len(self.spec_edges)
                      + sum(1 for e in self.spec_edges if e.get("src")))
        got_props = sum(len(v) for k, v in self.prop_writes.items()
                        if k[0] == self.page_no)
        for f in self.prop_failures:
            bad.append("shape data write failed: " + f)
        if got_props < want_props:
            bad.append("shape data written on this page: %d of %d expected "
                       "(3 per node + 1 per connector); the drawing would ship "
                       "without machine-readable source anchors"
                       % (got_props, want_props))
        if self.problems:
            bad.extend(self.problems)
        return {"edges": len(self.spec_edges), "nodes": len(ids),
                "shapeIds": self.node_ids, "edgeIds": self.edge_ids,
                "connects": actual, "expectedConnects": glued_expected,
                "failures": bad, "notes": self.notes,
                "styleIssues": self.style_issues[:40],
                "propsWritten": got_props, "propsExpected": want_props,
                "propFailures": self.prop_failures[:20]}


    def rows(self):
        """Group band rectangles into rows by vertical overlap, then map each
        node id to the row it sits in."""
        bands = self.spec_bands
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
        for n in self.spec_nodes:
            cy = n["y"] + n["h"] / 2.0
            best, bestd = None, 1e9
            for bi, b in enumerate(self.spec_bands):
                if b["y"] - 0.02 <= cy <= b["y"] + b["h"] + 0.02:
                    d = min(abs(cy - b["y"]), abs(cy - (b["y"] + b["h"])))
                    if d < bestd:
                        best, bestd = bi, d
            node_row[n["id"]] = band_of.get(best, -1) if best is not None else -1
        return rows, node_row

    def rule_short_hop(self):
        bad = []
        _rows, nrow = self.rows()
        byid = dict((n["id"], n) for n in self.spec_nodes)
        for e in self.spec_edges:
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
                for m in self.spec_nodes:
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
    def sheets(self):
        sp = self.spec
        if sp.get("sheets"):
            out = []
            for sh in sp["sheets"]:
                d = dict(sh)
                # document-wide settings are inherited unless the page overrides
                for k in ("edgeRule", "overlapExempt", "bodySize", "subSize",
                          "title", "subtitle", "docid", "revline", "minBodySize"):
                    if k not in d and k in sp:
                        d[k] = sp[k]
                out.append(d)
            return out
        one = dict((k, v) for k, v in sp.items() if k != "sheets")
        one["name"] = sp.get("pageName", "Page-1")
        return [one]

    def _page_setup(self, pg):
        for cell, formula in (("PrintPageOrientation", "1"),
                              ("PageWidth", "%gin" % self.PW),
                              ("PageHeight", "%gin" % self.PH),
                              ("RoutingStyle", "1"),
                              ("ConLineJumpCode", "6"),
                              ("ConLineJumpStyle", "0"),
                              ("ConLineJumpSize", "0.09in"),
                              ("WrappingStyle", "1"),
                              ("WrappingDirection", "1")):
            self._cell(pg.PageSheet, cell, formula)

    def _fill_sheet(self, sh, idx):
        self.cur = sh
        self.page = self.doc.Pages.Item(idx + 1)
        self.page_no = idx + 1
        self.chrome = []
        self.parked = []
        self.band_strips = []
        self.node_text_rects = {}
        self.spec_nodes = sh["nodes"]
        self.spec_edges = sh["edges"]
        self.spec_bands = sh.get("bands", [])
        self.add_title_block()
        for band in self.spec_bands:
            self.add_band(band)
        for n in self.spec_nodes:
            self.add_node(n)
        for e in self.spec_edges:
            self.add_edge(e)
        if sh.get("legend"):
            self.add_legend(sh["legend"], sh["legendOrigin"])
        if sh.get("footnotes"):
            self.add_footnotes(sh["footnotes"], sh["footnoteOrigin"])
        if sh.get("notes"):
            self.add_notes(sh["notes"], sh.get("notesOrigin", (0.46, 7.9)),
                           sh.get("notesWidth", 9.0), sh.get("notesSize", 6.4))
        self.chrome_by_page[self.page_no] = (list(self.chrome), list(self.parked),
                                             list(self.band_strips))

    def build(self):
        self.start()
        try:
            sheets = self.sheets()
            self.page.Name = sheets[0].get("name", "Page-1")
            self._page_setup(self.page)
            for sh in sheets[1:]:
                pg = self.doc.Pages.Add()
                pg.Name = sh.get("name", "Page")
                self._page_setup(pg)
            for idx, sh in enumerate(sheets):
                self._fill_sheet(sh, idx)
            return self._publish(sheets)
        finally:
            self.finish()

    def _publish(self, sheets):
        rep = self.gate_all(sheets)
        # A failed run must not leave a fresh gate report next to an older .vsdx:
        # the proof would then audit the shipped drawing against numbers that
        # describe a drawing that was never written.
        target = self.out["gate"]
        if rep["failures"]:
            target = os.path.join(os.path.dirname(self.out["gate"]), "..", "debug",
                                  os.path.basename(self.out["gate"]))
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            json.dump(rep, open(target, "w", encoding="utf-8"),
                      indent=1, ensure_ascii=False)
        except Exception as exc:
            self.notes.append("gate report write failed: %s" % type(exc).__name__)
        if rep["failures"]:
            for key in ("debugPng", "debugPdf"):
                path = self.out.get(key)
                if not path:
                    continue
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    if key == "debugPng":
                        self.doc.Pages.Item(1).Export(path)
                    else:
                        self.doc.ExportAsFixedFormat(1, path, 1, 0)
                except Exception as exc:
                    self.notes.append("debug %s export failed: %s"
                                      % (key, type(exc).__name__))
            raise GateError("%d layout/semantics failure(s); first: %s"
                            % (len(rep["failures"]), rep["failures"][0]))
        self.doc.SaveAs(self.out["vsdx"])
        stem = os.path.splitext(self.out["png"])[0]
        for i in range(1, self.doc.Pages.Count + 1):
            pg = self.doc.Pages.Item(i)
            suffix = "" if self.doc.Pages.Count == 1 else "_p%d" % i
            pg.Export(stem + suffix + ".png")
        if self.doc.Pages.Count > 1:
            # a multi-page drawing used to leave the plain-stem PNG behind as an
            # orphan of the single-page era, so a reader following the README's
            # "previews/<name>.png" got the old picture. Write that name too, as
            # page 1, so every referenced file is current.
            self.doc.Pages.Item(1).Export(stem + ".png")
        self.doc.ExportAsFixedFormat(1, self.out["pdf"], 1, 0)
        return rep

    def gate_all(self, sheets):
        merged = {"failures": [], "notes": [], "styleIssues": [], "pages": [],
                  "propFailures": []}
        keep = (self.spec_nodes, self.spec_edges, self.spec_bands, self.cur, self.page)
        ids, eids = dict(self.node_ids), dict(self.edge_ids)
        for idx, sh in enumerate(sheets):
            self.page = self.doc.Pages.Item(idx + 1)
            self.page_no = idx + 1            # the prop census is filtered by page
            (self.chrome, self.parked, self.band_strips) = \
                self.chrome_by_page.get(self.page_no, ([], [], []))
            self.cur = sh
            self.spec_nodes, self.spec_edges = sh["nodes"], sh["edges"]
            self.spec_bands = sh.get("bands", [])
            one = self.gate()
            merged["failures"] += ["[page %s] %s" % (self.page.Name, f)
                                   for f in one["failures"]]
            merged["propFailures"] += one.get("propFailures", [])
            merged["pages"].append({"name": self.page.Name,
                                    "nodes": one["nodes"], "edges": one["edges"],
                                    "connects": one["connects"],
                                    "expectedConnects": one["expectedConnects"],
                                    "propsWritten": one.get("propsWritten"),
                                    "propsExpected": one.get("propsExpected")})
            merged["notes"] += one.get("notes", [])
            merged["styleIssues"] += one.get("styleIssues", [])
        (self.spec_nodes, self.spec_edges, self.spec_bands, self.cur,
         self.page) = keep
        merged["shapeIds"], merged["edgeIds"] = ids, eids
        for k in ("nodes", "edges", "connects", "expectedConnects",
                  "propsWritten", "propsExpected"):
            merged[k] = sum((p.get(k) or 0) for p in merged["pages"])
        return merged

def _nolabel(builder):
    return set(builder.cur.get("overlapExempt", []))


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
