"""R5 follow-up: widen the Task Name column on the EN classroom twin.

The EN display names are longer than the Chinese ones and wrap to three lines,
so the frozen zh view's name-column width only shows ~8 of the 11 summary rows
on the first screen. This resizes ONE column (Name -> 32 chars) on the EN copy
with the positional TableEditEx form the R4.1 round measured on this install
(named arguments are silently dropped under pywin32 late binding). The chart
half narrows accordingly and the December tail of the timescale clips - every
bar ends 2026-10-23, so nothing readable is lost.

Verification is the same standard as the build: plan digests before/after,
65x10 field fidelity against the fact source, task/link/assignment counts, and
a fresh window screenshot judged by eye.
"""
import hashlib
import json
import os
import shutil
import sys
import time

import win32com.client as w32

HERE = os.path.dirname(os.path.abspath(__file__))
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
SRC = os.path.join(DEL, "Classroom", "Teacher_03_Project_Overview_R4_EN.mpp")
FACT = os.path.join(DEL, "Microsoft_Project",
                    "CityNexus_Software_Engineering_Plan.mpp")
LOG = open(os.path.join(HERE, "se_r43_en_table_r1.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()

WIDE = 32  # chars; the R4.1 probe measured Name at 32 before it settled lower
COPY_NAME = "课堂总览"  # the view's registered table name, rebuilt here
TABLE = "\u8bfe\u5802\u603b\u89c8"  # 课堂总览 - the table the R4.1 build applied


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def sha(p, n=64):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


before = sha(SRC)
os.chmod(SRC, 0o644)
log("EN mpp before %s (%d bytes)" % (before[:16], os.path.getsize(SRC)))

# gencache early binding: named COM arguments are honoured
try:
    mp = w32.gencache.EnsureDispatch("MSProject.Application")
except Exception:
    mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
import atexit


def bye():
    try:
        mp.FileCloseEx(0)
    except Exception:
        pass
    try:
        mp.Quit()
    except Exception:
        pass


atexit.register(bye)
mp.FileOpen(SRC)
q = mp.ActiveProject

n_tasks = q.Tasks.Count
n_links = sum(len([x for x in str(q.Tasks.Item(i).Predecessors or "").split(",")
                   if x.strip()]) for i in range(1, n_tasks + 1))
n_assign = sum(q.Tasks.Item(i).Assignments.Count for i in range(1, n_tasks + 1))
log("before: tasks=%d links=%d assignments=%d" % (n_tasks, n_links, n_assign))

# The saved view references a "课堂总览" table definition that no longer
# exists in the file (R4.1 built it in probe intermediates only), so ANY
# table edit dies with "无法显示视图...该表已被删除". Rebuild that definition
# first - a copy of 项, exactly what the R4.1 probe created - then resize on
# the copy and apply it, which also re-points the view at a live table.
# Positional form measured in R4.1 (se_r41_r2.py): 20 args, named args are
# silently dropped on this install.
# Early binding (typelib makepy): named arguments are honoured for real.
# Late binding silently drops them, which is how the R4.1 named-args trap
# happened; the type-lib signature for TableEditEx is
# (Name, TaskTable, Create, OverwriteExisting, NewName, FieldName, NewFieldName,
#  Title, Width, Align, ShowInMenu, LockFirstColumn, DateFormat, RowHeight,
#  ColumnPosition, AlignTitle, HeaderAutoRowHeightAdjustment, HeaderTextWrap,
#  WrapText, ShowAddNewColumn).
def te(**kw):
    return mp.TableEditEx(**kw)

def te_pos(args):
    return mp.TableEditEx(*args)

make_r = None
try:
    make_r = te(Name=TABLE, TaskTable=True, Create=True, NewName=COPY_NAME,
                ShowInMenu=True, ShowAddNewColumn=False)
    log("create via named args -> %s" % make_r)
except Exception as exc:
    log("named create failed (%s: %s); positional fallback"
        % (type(exc).__name__, str(exc).splitlines()[0][:80]))
if make_r is None:
    make_r = te_pos([TABLE, True, True, False, COPY_NAME, "", "", "", 0, 0,
                     True, False, 1, 2, -1, 1, True, True, True, False])
    log("create via positional -> %s" % make_r)

resize_r = None
for fld in ("Name", "任务名称"):
    try:
        resize_r = te(Name=COPY_NAME, TaskTable=True, FieldName=fld, Width=WIDE)
        log("resize %r -> %s" % (fld, resize_r))
        if resize_r:
            break
    except Exception as exc:
        log("resize %r ERR %s %s" % (fld, type(exc).__name__,
                                     str(exc).splitlines()[0][:80]))
resize_r = resize_r or te_pos([COPY_NAME, True, False, False, "", "Name", "",
                               "", WIDE, 0, True, False, 1, 2, -1, 1, True,
                               True, True, False])
log("resize positional fallback -> %s" % resize_r)

r2 = mp.TableApply(COPY_NAME)
log("TableApply -> %s" % r2)
if not (make_r and resize_r and r2):
    log("REFUSED: one of the table steps reported failure; no save")
    mp.FileCloseEx(0)
    mp.Quit()
    sys.exit(1)

mp.CalculateAll()
mp.FileSave()
log("saved (%d bytes)" % os.path.getsize(SRC))
mp.FileCloseEx(0)
mp.Quit()
time.sleep(1.0)

# ---- read back from disk and audit
mp2 = w32.DispatchEx("MSProject.Application")
mp2.Visible = False
mp2.DisplayAlerts = 0
mp2.FileOpen(SRC, True)
q2 = mp2.ActiveProject
n_tasks2 = q2.Tasks.Count
n_links2 = sum(len([x for x in str(q2.Tasks.Item(i).Predecessors or "").split(",")
                    if x.strip()]) for i in range(1, n_tasks2 + 1))
n_assign2 = sum(q2.Tasks.Item(i).Assignments.Count for i in range(1, n_tasks2 + 1))
mp2.FileCloseEx(0)
mp2.Quit()
ok = (n_tasks2, n_links2, n_assign2) == (n_tasks, n_links, n_assign)
log("after: tasks=%d links=%d assignments=%d (unchanged=%s)"
    % (n_tasks2, n_links2, n_assign2, ok))
json.dump({"beforeSha": before[:16], "afterSha": sha(SRC, 16),
           "nameWidth": WIDE, "table": COPY_NAME,
           "structureUnchanged": ok,
           "tasks": [n_tasks, n_tasks2], "links": [n_links, n_links2],
           "assignments": [n_assign, n_assign2]},
          open(os.path.join(HERE, "se_r43_en_table_r1.json"), "w",
               encoding="utf-8"), indent=1)
if not ok:
    log("REFUSED: structure changed by the table edit - restore from git")
    sys.exit(1)
log("EN TABLE RESIZE OK - run fidelity + eye next")
LOG.close()
sys.exit(0)
