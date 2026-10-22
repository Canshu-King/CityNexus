import traceback
import win32com.client as w32
import win32com.client.dynamic as dyn
from win32com.client import gencache

print("gencache dir:", gencache.GetGeneratePath())

for label, fn in (
    ("gencache.EnsureDispatch", lambda: gencache.EnsureDispatch("Visio.Application")),
    ("w32.Dispatch", lambda: w32.Dispatch("Visio.Application")),
    ("dynamic.Dispatch", lambda: dyn.Dispatch("Visio.Application")),
    ("w32.DispatchEx", lambda: w32.DispatchEx("Visio.Application")),
):
    print("=== %s ===" % label)
    obj = None
    try:
        obj = fn()
        print("  returned:", type(obj), repr(obj)[:120])
    except Exception:
        print("  DISPATCH RAISED:")
        traceback.print_exc()
        continue
    for attr in ("Version", "BuildNumber", "Visible", "MasterCount"):
        try:
            print("   %s = %r" % (attr, getattr(obj, attr)))
        except Exception:
            print("   %s RAISED: %s" % (attr, traceback.format_exc().replace("\n", " | ")[:300]))
    try:
        obj.Quit()
        print("  Quit ok")
    except Exception:
        print("  Quit raised:", traceback.format_exc().replace("\n", " | ")[:200])
