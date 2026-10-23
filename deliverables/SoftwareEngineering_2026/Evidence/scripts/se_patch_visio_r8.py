"""Shape Data, final form: address the cells by their qualified NAME.

CellsSRC(Section, Row, Column) has both Row and Column typed I4 in this
installed type library, so passing the documented row/cell NAMES raises
"invalid literal for int()". The name-based route that does work is the
qualified cell path through CellsU:

    shape.CellsU("Prop.SourceRef.Label")
    shape.CellsU("Prop.SourceRef.Type")
    shape.CellsU("Prop.SourceRef.Value")

which is also what a person editing the drawing sees in the Shape Sheet.
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
s = s[:a] + '''    def _prop(self, sh, name, value):
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
            got = None
            cell = sh.CellsU(path + ".Value")
            for attr in ("String", "StrV", "ResultStr", "Value"):
                try:
                    got = getattr(cell, attr)
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
                   type(exc).__name__, str(exc)[:140]))
            return False

''' + s[b:]
open(P, "w", encoding="utf-8").write(s)
ast.parse(s)
print("_prop now uses CellsU qualified names")
