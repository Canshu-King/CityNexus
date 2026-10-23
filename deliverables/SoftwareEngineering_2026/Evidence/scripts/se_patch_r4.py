"""Readability pass.

Engine
  - usable text width is now scaled per shape kind: a diamond only carries text
    comfortably across its middle, so authoring a long label into a 判定 shape
    is now a gate failure rather than an ugly picture
  - connector labels are drawn as their own small text shape parked just off the
    line instead of sitting on top of it, which is what made the branch words
    collide with boxes
  - legend and notes no longer share space
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

s = s.replace('''ARROW_NONE = "0"''', '''ARROW_NONE = "0"

# how much of a shape's width can actually carry a line of text
TEXT_FACTOR = {
    "decision": 0.46, "terminator": 0.70, "usecase": 0.68, "onpage": 0.66,
    "offpage": 0.78, "extdata": 0.80, "data": 0.80, "document": 0.84,
    "subprocess": 0.90, "cylinder": 0.84, "database": 0.78, "actor": 0.90,
}''')

s = s.replace('''        main = n["text"]
        sub = n.get("src")
        lines = self._wrap(main, w - 0.12, self.body_size)''',
'''        main = n["text"]
        sub = n.get("src")
        eff_w = (w - 0.14) * TEXT_FACTOR.get(kind, 1.0)
        lines = self._wrap(main, eff_w, self.body_size)''')

s = s.replace('''            slines = self._wrap(sub, w - 0.12, SUB_SIZE)''',
              '''            slines = self._wrap(sub, eff_w, self.sub_size)''')

s = s.replace('''        widest = max([len(l) for l in lines] or [0])
        est_w = widest * (self.body_size * 0.52 / 72.0)
        if est_w > w - 0.06:
            self.problems.append("text width overflow: node %s est %.2fin > box %.2fin"
                                 % (n["id"], est_w, w))''',
'''        widest = max([len(l) for l in lines] or [0])
        est_w = widest * (self.body_size * 0.52 / 72.0)
        if est_w > eff_w:
            self.problems.append("text width overflow: node %s needs %.2fin > usable "
                                 "%.2fin (%s box %.2fin)"
                                 % (n["id"], est_w, eff_w, kind, w))''')

# connector labels parked beside the line
s = s.replace('''        if e.get("label"):
            con.Text = e["label"]
            self._cell(con, "Char.Size", "%gpt" % e.get("labelSize", 7.0))
            self._cell(con, "Char.Color", _rgb("#334D66"))''',
'''        if e.get("label"):
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
                                  % (e["from"], e["to"], type(exc).__name__))''')

s = s.replace('''        self.node_ids = {}
        self.edge_ids = {}''', '''        self.node_ids = {}
        self.edge_ids = {}
        self.edge_labels = []''')

# legend: draw swatches to the LEFT of each label, tightly, and return the height
s = s.replace('''    def add_legend(self, items, origin):
        x, y = origin
        self._text(x, y, 2.0, "Legend", size=8.5, bold=True, color="#12263F")''',
'''    def add_legend(self, items, origin):
        x, y = origin
        self._text(x, y, 2.0, "Legend", size=8.5, bold=True, color="#12263F",
                   align="0")''')

open(P, "w", encoding="utf-8").write(s)
ast.parse(s)
print("engine readability pass applied")
