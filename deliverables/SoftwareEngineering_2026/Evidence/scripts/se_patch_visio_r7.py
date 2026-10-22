"""Finish the Shape Data fix with the API the type library really offers.

  IVShape.AddNamedRow(Section:I2, RowName:BSTR, RowTag:I2) -> I2
      it RETURNS the new row index; the previous attempt threw that away and
      then looked for a "Name" cell, which does not exist - a row's name lives
      on IVRow, not in a cell.
  IVSection.Count / IVSection.Row(i) -> IVRow.NameString
      that is how existing rows (for example ones inherited from the master)
      are found.
"""
import ast
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "se_visio_lib_r1.py")
s = open(P, encoding="utf-8").read()

a = s.index("    def _prop_row(self, sh, name):")
b = s.index("    def _prop(self, sh, name, value):")
s = s[:a] + '''    def _prop_row(self, sh, name):
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

''' + s[b:]

s = s.replace('''            idx = self._prop_row(sh, name)
            if idx is None:
                try:
                    sh.AddNamedRow(243, name, -1)
                except Exception:
                    sh.AddNamedRow(243, name, 0)
                idx = self._prop_row(sh, name)
                if idx is None:
                    raise AssertionError("AddNamedRow did not create row %r" % name)''',
'''            idx = self._prop_row(sh, name)
            if idx is None:
                made = None
                for tag in (-1, 0):
                    try:
                        made = sh.AddNamedRow(243, name, tag)
                        break
                    except Exception:
                        continue
                if made is None:
                    raise AssertionError("AddNamedRow raised for %r" % name)
                idx = int(made)
                self._rowcache.setdefault(sh.ID, {})[name] = idx
                again = self._prop_row(sh, name)
                if again is not None:
                    idx = again''')
open(P, "w", encoding="utf-8").write(s)
ast.parse(s)
print("AddNamedRow return value + IVRow.NameString lookup wired in")
