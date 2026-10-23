"""Consolidated engine patch + diagram-01 replacement.

Engine changes
  1. band labels and footnotes are left-aligned, so the gap between two bands
     stays a clean routing channel instead of being sat on by a centred label
  2. a real layout rule replaces guesswork: an edge may only be
       - a same-row hop between neighbouring shapes, or
       - a hop between directly adjacent rows whose boxes overlap (or nearly)
     Anything else would have to be routed over another shape, so the build
     refuses instead of shipping a picture with arrows through boxes.
  3. specs can carry a `notes` block rendered as a plain text panel.
"""
import ast
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "se_visio_lib_r1.py")
s = open(P, encoding="utf-8").read()

# ---- 1: alignment --------------------------------------------------------
if 'def _align' not in s:
    s = s.replace('''        self._cell(sh, "VerticalAlign", "1")
        return sh''', '''        self._cell(sh, "VerticalAlign", "1")
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
        return False''')
s = s.replace('''    def _text(self, x_top, y_top, w, text, size=BODY_SIZE, bold=False,
              color="#1B2733", align=0):''',
              '''    def _text(self, x_top, y_top, w, text, size=BODY_SIZE, bold=False,
              color="#1B2733", align="1"):''')
s = s.replace('''            t = self._text(b["x"] + 0.14, b["y"] + 0.06, w - 0.28, label,
                           size=b.get("labelSize", 9.5), bold=True, color="#2A3B4F")''',
              '''            t = self._text(b["x"] + 0.14, b["y"] + 0.05, min(w - 0.28, 8.6), label,
                           size=b.get("labelSize", 9.5), bold=True, color="#2A3B4F",
                           align="0")''')
s = s.replace('''            self._text(origin[0], y, width, ln, size=6.6, color="#4C5A66")''',
              '''            self._text(origin[0], y, width, ln, size=6.6, color="#4C5A66",
                       align="0")''')

# ---- 2: the layout rule --------------------------------------------------
RULE = '''        if self.spec.get("edgeRule", "shortHop") == "shortHop":
            bad.extend(self.rule_short_hop())
'''
anchor = '        glued_expected = 2 * len(self.spec["edges"])'
s = re.sub(r'        if self\.spec\.get\("edgeRule".*?\n(?=        glued_expected)', '', s, flags=re.S)
s = s.replace(anchor, RULE + anchor, 1)

METHOD = '''
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

'''
s = s.replace("    # ---------------------------------------------------------------- publish", METHOD + "    # ---------------------------------------------------------------- publish")

# ---- 3: notes panel ------------------------------------------------------
s = s.replace('''            if self.spec.get("footnotes"):
                self.add_footnotes(self.spec["footnotes"], self.spec["footnoteOrigin"])''',
'''            if self.spec.get("footnotes"):
                self.add_footnotes(self.spec["footnotes"], self.spec["footnoteOrigin"])
            if self.spec.get("notes"):
                self.add_notes(self.spec["notes"], self.spec.get("notesOrigin", (0.46, 7.9)),
                               self.spec.get("notesWidth", 9.0),
                               self.spec.get("notesSize", 6.4))''')
s = s.replace('''    # ---------------------------------------------------------------- checks''',
'''    def add_notes(self, lines, origin, width, size):
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

    # ---------------------------------------------------------------- checks''')
open(P, "w", encoding="utf-8").write(s)
ast.parse(s)
print("engine: alignment + shortHop rule + notes panel installed")

# ---- diagram 01 ----------------------------------------------------------
P2 = os.path.join(HERE, "se_visio_specs_r1.py")
t = open(P2, encoding="utf-8").read()
i = t.index("# ==========================================================================  01")
j = t.index("# ==========================================================================  02")
body = open(os.path.join(HERE, "_spec01_body.py"), encoding="utf-8").read()
t = t[:i] + body + t[j:]
open(P2, "w", encoding="utf-8").write(t)
ast.parse(t)
print("spec 01 replaced with the 5-row / 7-band layout")
