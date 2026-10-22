"""CellsSRC's Row argument is typed I4 in this type library, so a row NAME is
rejected ("invalid literal for int()"). Address Shape Data rows by index:
AddNamedRow still creates the row with its proper name, but every cell write
uses the numeric row index found by scanning the section.
"""
import ast
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "se_visio_lib_r1.py")
s = open(P, encoding="utf-8").read()

a = s.index("    def _prop(self, sh, name, value):")
b = s.index("    # ---------------------------------------------------------------- edges")
s = s[:a] + '''    def _cellstr(self, cell):
        for attr in ("String", "StrV", "ResultStr"):
            try:
                v = getattr(cell, attr)
            except Exception:
                continue
            if isinstance(v, str):
                return v
        return None

    def _prop_row(self, sh, name):
        """Numeric index of the Shape Data row called `name`, or None."""
        cache = self._rowcache.setdefault(sh.ID, {})
        if name in cache:
            return cache[name]
        for i in range(0, 40):
            try:
                nm = self._cellstr(sh.CellsSRC(243, i, "Name"))
            except Exception:
                continue
            if nm == name:
                cache[name] = i
                return i
        return None

    def _prop(self, sh, name, value):
        """Write Shape Data and prove it by reading the value straight back.

        IVShape.AddNamedRow(visSectionProp=243, RowName, RowTag) creates the
        named row; CellsSRC's row argument is I4 in this type library, so every
        subsequent cell is addressed by the numeric row index found by scanning.
        A property that does not read back is a gate failure, not a note.
        """
        value = str(value)
        try:
            if not sh.SectionExists(243, 0):
                sh.AddSection(243)
            idx = self._prop_row(sh, name)
            if idx is None:
                try:
                    sh.AddNamedRow(243, name, -1)
                except Exception:
                    sh.AddNamedRow(243, name, 0)
                idx = self._prop_row(sh, name)
                if idx is None:
                    raise AssertionError("AddNamedRow did not create row %r" % name)
            sh.CellsSRC(243, idx, "Label").FormulaU = '"%s"' % name
            sh.CellsSRC(243, idx, "Prompt").FormulaU = '"%s"' % name
            sh.CellsSRC(243, idx, "Type").FormulaU = "0"
            sh.CellsSRC(243, idx, "Value").FormulaU = '"%s"' % value.replace('"', "'")
            got = self._cellstr(sh.CellsSRC(243, idx, "Value"))
            if got != value:
                raise AssertionError("row %d read back %r, expected %r" % (idx, got, value))
            self.prop_writes.setdefault(sh.ID, {})[name] = got
            return True
        except Exception as exc:
            self.prop_failures.append(
                "shape %s (id %s) property %s: %s: %s"
                % (getattr(sh, "Name", "?"), getattr(sh, "ID", "?"), name,
                   type(exc).__name__, str(exc)[:140]))
            return False

''' + s[b:]

s = s.replace("        self.prop_writes = {}",
              "        self.prop_writes = {}\n        self._rowcache = {}")
open(P, "w", encoding="utf-8").write(s)
ast.parse(s)
print("_prop now addresses Shape Data rows by index")
