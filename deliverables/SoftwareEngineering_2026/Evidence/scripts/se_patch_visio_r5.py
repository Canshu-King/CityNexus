"""Apply the Visio engine fixes for the independent review.

  1. Shape Data: use IVShape.AddNamedRow (the API this type library exposes),
     address cells by row NAME, and read every value back. A property that does
     not read back is now a GATE FAILURE, not a note. The old code called
     SectionSRC(243).AddRow(...), which raised AttributeError on every single
     shape - 535 times across the four drawings - and the build still passed.
  2. Multi-page: a spec may carry `sheets`, so one .vsdx can hold a readable
     overview page and a detailed page. The gate runs per page; PNGs are
     exported per page; the PDF covers the whole document.
"""
import ast
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "se_visio_lib_r1.py")
s = open(P, encoding="utf-8").read()

# ---------------------------------------------------------------- 1. properties
a = s.index("    def _prop(self, sh, name, value):")
b = s.index("    # ---------------------------------------------------------------- edges")
s = s[:a] + '''    def _prop(self, sh, name, value):
        """Write Shape Data and prove it by reading the value straight back.

        IVShape.AddNamedRow(visSectionProp=243, RowName, RowTag) is what this
        installed type library actually exposes. The previous implementation
        used SectionSRC(243).AddRow(...), which is not a member of IVSection
        here, so it raised AttributeError for every shape and the failure was
        being filed as a note while the build still reported success.
        """
        value = str(value)
        try:
            if not sh.SectionExists(243, 0):
                sh.AddSection(243)
            try:
                sh.CellsSRC(243, name, "Value")
            except Exception:
                sh.AddNamedRow(243, name, -1)
            sh.CellsSRC(243, name, "Label").FormulaU = '"%s"' % name
            sh.CellsSRC(243, name, "Prompt").FormulaU = '"%s"' % name
            sh.CellsSRC(243, name, "Type").FormulaU = "0"
            sh.CellsSRC(243, name, "Value").FormulaU = '"%s"' % value.replace('"', "'")
            got = None
            for attr in ("String", "ResultStr", "Value"):
                try:
                    got = getattr(sh.CellsSRC(243, name, "Value"), attr)
                except Exception:
                    continue
                if isinstance(got, str) and got:
                    break
            if got != value:
                raise AssertionError("read back %r, expected %r" % (got, value))
            self.prop_writes.setdefault(sh.ID, {})[name] = got
            return True
        except Exception as exc:
            self.prop_failures.append(
                "shape %s (id %s) property %s: %s: %s"
                % (getattr(sh, "Name", "?"), getattr(sh, "ID", "?"), name,
                   type(exc).__name__, str(exc)[:120]))
            return False

''' + s[b:]

s = s.replace("        self.edge_labels = []",
              "        self.edge_labels = []\n"
              "        self.prop_writes = {}\n"
              "        self.prop_failures = []")

# ---------------------------------------------------------------- 2. gate: shape data is mandatory
s = s.replace('''        if self.problems:
            bad.extend(self.problems)
        return {"edges": len(self.spec["edges"]), "nodes": len(ids),''',
'''        want_props = 3 * len(self.spec_nodes) + len(self.spec_edges)
        got_props = sum(len(v) for v in self.prop_writes.values())
        for f in self.prop_failures:
            bad.append("shape data write failed: " + f)
        if got_props < want_props:
            bad.append("shape data written on this page: %d of %d expected "
                       "(3 per node + 1 per connector); the drawing would ship "
                       "without machine-readable source anchors"
                       % (got_props, want_props))
        if self.problems:
            bad.extend(self.problems)
        return {"edges": len(self.spec_edges), "nodes": len(ids),''')
s = s.replace('''                "styleIssues": self.style_issues[:40]}''',
'''                "styleIssues": self.style_issues[:40],
                "propsWritten": got_props, "propsExpected": want_props,
                "propFailures": self.prop_failures[:20]}''')

# ---------------------------------------------------------------- 3. gate() reads the current sheet
s = s.replace('        ids = [n["id"] for n in self.spec["nodes"]]',
              '        ids = [n["id"] for n in self.spec_nodes]')
s = s.replace('        rects = [(n["id"], n["x"], n["y"], n["w"], n["h"]) for n in self.spec["nodes"]]',
              '        rects = [(n["id"], n["x"], n["y"], n["w"], n["h"]) for n in self.spec_nodes]')
s = s.replace('        for e in self.spec["edges"]:\n            outs[e["from"]] += 1',
              '        for e in self.spec_edges:\n            outs[e["from"]] += 1')
s = s.replace('                outs_labels = [e.get("label") for e in self.spec["edges"] if e["from"] == n["id"]]',
              '                outs_labels = [e.get("label") for e in self.spec_edges if e["from"] == n["id"]]')
s = s.replace('        for n in self.spec["nodes"]:\n            role = n.get("role")',
              '        for n in self.spec_nodes:\n            role = n.get("role")')
s = s.replace('            bands = self.spec.get("bands", [])',
              '            bands = self.spec_bands')
s = s.replace('''            for n in self.spec["nodes"]:
                cx[n["id"]]''', '''            for n in self.spec_nodes:
                cx[n["id"]]''')
s = s.replace('''            for n in self.spec["nodes"]:
                cy[n["id"]]''', '''            for n in self.spec_nodes:
                cy[n["id"]]''')
s = s.replace('        if self.spec.get("edgeRule", "shortHop") == "shortHop":',
              '        if getattr(self, "cur", self.spec).get("edgeRule", "shortHop") == "shortHop":')
s = s.replace('        glued_expected = 2 * len(self.spec["edges"])',
              '        glued_expected = 2 * len(self.spec_edges)')
s = s.replace('        return set(spec.get("overlapExempt", []))',
              '        return set(self.cur.get("overlapExempt", []))')
s = s.replace('''        for i in range(len(rects)):''', '''        for i in range(len(rects)):''')
s = s.replace('''                if a[0] in _nolabel(self.spec) or b[0] in _nolabel(self.spec):''',
              '''                if a[0] in _nolabel(self) or b[0] in _nolabel(self):''')
s = s.replace('''def _nolabel(spec):
    return set(spec.get("overlapExempt", []))''',
'''def _nolabel(builder):
    return set(builder.cur.get("overlapExempt", []))''')

# title block reads the current sheet
s = s.replace('''    def add_title_block(self):
        self._text(0.35, 0.22, 11.0, self.spec["title"], size=TITLE_SIZE,
                   bold=True, color="#12263F")
        self._text(0.35, 0.62, 11.6, self.spec.get("subtitle", ""),
                   size=SUBTITLE_SIZE, color="#3C5068")
        self._text(9.5, 0.26, 6.7, "%s\\n%s" % (self.spec.get("docid", ""),
                                              self.spec.get("revline", "")),
                   size=8.0, color="#3C5068")''',
'''    def add_title_block(self):
        cur = self.cur
        self._text(0.35, 0.22, 11.0, cur.get("title", self.spec["title"]),
                   size=TITLE_SIZE, bold=True, color="#12263F", align="0")
        self._text(0.35, 0.62, 11.6, cur.get("subtitle", self.spec.get("subtitle", "")),
                   size=SUBTITLE_SIZE, color="#3C5068", align="0")
        self._text(9.5, 0.26, 6.7, "%s\\n%s" % (
            cur.get("docid", self.spec.get("docid", "")),
            cur.get("revline", self.spec.get("revline", ""))),
            size=8.0, color="#3C5068", align="0")''')

# ---------------------------------------------------------------- 4. multi-page publish
a = s.index("    # ---------------------------------------------------------------- publish")
b = s.index("def _nolabel(builder):")
s = s[:a] + '''    # ---------------------------------------------------------------- publish
    def sheets(self):
        sp = self.spec
        if sp.get("sheets"):
            return [dict(sh) for sh in sp["sheets"]]
        one = dict((k, v) for k, v in sp.items() if k != "sheets")
        one["name"] = sp.get("pageName", "Page-1")
        return [one]

    def _page_setup(self, pg):
        for cell, formula in (("PrintPageOrientation", "1"),
                              ("PageWidth", "420mm"),
                              ("PageHeight", "297mm"),
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
        json.dump(rep, open(self.out["gate"], "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)
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
        self.doc.ExportAsFixedFormat(1, self.out["pdf"], 1, 0)
        return rep

    def gate_all(self, sheets):
        merged = {"failures": [], "notes": [], "styleIssues": [], "pages": [],
                  "propFailures": []}
        keep = (self.spec_nodes, self.spec_edges, self.spec_bands, self.cur, self.page)
        ids, eids = dict(self.node_ids), dict(self.edge_ids)
        for idx, sh in enumerate(sheets):
            self.page = self.doc.Pages.Item(idx + 1)
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

''' + s[b:]

# defaults so gate() never sees unset attributes
s = s.replace("        self.node_ids = {}",
              "        self.node_ids = {}\n        self.cur = spec\n"
              "        self.spec_nodes = spec.get('nodes', [])\n"
              "        self.spec_edges = spec.get('edges', [])\n"
              "        self.spec_bands = spec.get('bands', [])")

open(P, "w", encoding="utf-8").write(s)
ast.parse(s)
print("visio engine patched: AddNamedRow shape data + per-page gate + multi-page publish")
