"""Engine hardening pass 2:
 - band labels and footnotes left-aligned so the inter-band gap is a clean
   routing channel (a centred label sitting in that gap is what got crossed)
 - a geometric edge rule: an edge may only join shapes in the same band or in
   directly adjacent bands, and same-band edges may not reach over an
   intervening shape. This is what actually prevents "arrow through a box".
"""
import ast
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "se_visio_lib_r1.py")
s = open(P, encoding="utf-8").read()

s = s.replace('''    def _text(self, x_top, y_top, w, text, size=BODY_SIZE, bold=False,
              color="#1B2733", align=0):''',
'''    def _text(self, x_top, y_top, w, text, size=BODY_SIZE, bold=False,
              color="#1B2733", align="0"):''')

s = s.replace('''        self._cell(sh, "VerticalAlign", "1")
        return sh''',
'''        self._cell(sh, "VerticalAlign", "1")
        self._align(sh, align)
        return sh

    def _align(self, sh, mode):
        """mode '0' left / '1' centre, via the Paragraph section."""
        try:
            sh.CellsSRC(4, 0, "Alignment").FormulaU = mode
            return True
        except Exception:
            pass
        try:
            sh.AddSection(4)
            sh.CellsSRC(4, 0, "Alignment").FormulaU = mode
            return True
        except Exception as exc:
            self.notes.append("paragraph alignment skipped (%s)" % type(exc).__name__))
            return False''')

s = s.replace('''            t = self._text(b["x"] + 0.14, b["y"] + 0.06, w - 0.28, label,
                           size=b.get("labelSize", 9.5), bold=True, color="#2A3B4F")''',
'''            t = self._text(b["x"] + 0.14, b["y"] + 0.05, min(w - 0.28, 8.6), label,
                           size=b.get("labelSize", 9.5), bold=True, color="#2A3B4F",
                           align="0")''')

s = s.replace('''        for ln in lines:
            self._text(origin[0], y, width, ln, size=6.6, color="#4C5A66")
            y += 0.155''',
'''        for ln in lines:
            self._text(origin[0], y, width, ln, size=6.6, color="#4C5A66", align="0")
            y += 0.155''')

# ---- geometric edge rule -------------------------------------------------
s = s.replace('''        glued_expected = 2 * len(self.spec["edges"])''',
'''        if self.spec.get("edgeRule", "adjacentBands") == "adjacentBands":
            bands = self.spec.get("bands", [])
            cx = {n["id"]: n["x"] + n["w"] / 2.0 for n in self.spec["nodes"]}
            cy = {n["id"]: n["y"] + n["h"] / 2.0 for n in self.spec["nodes"]}

            def band_of(nid):
                y = cy[nid]
                for bi, b in enumerate(bands):
                    if b["y"] <= y <= b["y"] + b["h"]:
                        return bi
                return None

            for e in self.spec["edges"]:
                a, z = e["from"], e["to"]
                ba, bz = band_of(a), band_of(z)
                if ba is None or bz is None:
                    bad.append("edge %s->%s is not inside any band" % (a, z))
                    continue
                if abs(ba - bz) > 1:
                    bad.append("edge %s->%s jumps %d bands (bands %d->%d): the route "
                               "would cross an intervening layer" % (a, z, abs(ba - bz), ba, bz))
                elif ba == bz and abs(cx[a] - cx[z]) > 3.2:
                    bad.append("same-band edge %s->%s reaches %.1fin across, over the "
                               "shapes in between" % (a, z, abs(cx[a] - cx[z])))
        glued_expected = 2 * len(self.spec["edges"])''')

open(P, "w", encoding="utf-8").write(s)
ast.parse(s)
print("engine hardened, AST OK")
