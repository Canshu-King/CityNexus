import os
import sys

import win32com.client as w32

path = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Visio\01_CityNexus_System_Architecture.vsdx"
vis = w32.DispatchEx("Visio.Application")
for p, v in (("Visible", False), ("AlertResponse", 7)):
    try:
        setattr(vis, p, v)
    except Exception:
        pass
d = vis.Documents.Open(path)
pg = d.Pages.Item(1)
print("shapes", pg.Shapes.Count, "connects", pg.Connects.Count)
shown = 0
for i in range(1, pg.Shapes.Count + 1):
    sh = pg.Shapes.Item(i)
    try:
        mname = sh.Master.Name if sh.Master is not None else None
    except Exception:
        mname = None
    if mname is None or sh.Connects.Count == 0:
        continue
    print("---- shape", i, sh.Name, "id", sh.ID, "master", mname,
          "connects", sh.Connects.Count, "text", repr(sh.Text[:40]))
    for sec in (243,):
        try:
            print("   sectionExists(243) =", sh.SectionExists(sec, 0))
        except Exception as exc:
            print("   SectionExists raised", type(exc).__name__)
        try:
            rows = sh.RowsCount(sec)
        except Exception as exc:
            rows = "raised %s" % type(exc).__name__
        print("   RowsCount(243) =", rows)
        if isinstance(rows, int):
            for r in range(1, rows + 1):
                for cell in ("Name", "Label", "Value", "Type"):
                    try:
                        print("      row %d cell %s = %r" % (r, cell, sh.CellsSRC(sec, r, cell).String))
                    except Exception as exc:
                        print("      row %d cell %s raised %s" % (r, cell, type(exc).__name__))
                        break
                try:
                    print("      byName Value = %r" % sh.CellsSRC(sec, r, "Value").ResultStr)
                except Exception as exc:
                    print("      byName Value raised %s" % type(exc).__name__)
    shown += 1
    if shown >= 2:
        break
print("=== Connects ===")
for i in range(1, min(pg.Connects.Count, 6) + 1):
    c = pg.Connects.Item(i)
    try:
        print("  conn", i, "from", c.FromSheet.Name, c.FromSheet.ID, "to", c.ToSheet.Name, c.ToSheet.ID)
    except Exception as exc:
        print("  conn", i, "raised", type(exc).__name__, str(exc)[:80])
d.Saved = True
d.Close()
vis.Quit()
