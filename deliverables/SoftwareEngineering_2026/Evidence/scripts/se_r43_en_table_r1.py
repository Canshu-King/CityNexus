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

# positional form measured in R4.1 (se_r41_r2.py):
# (Name, TaskTable, Create, OverwriteExisting, NewName, FieldName, NewFieldName,
#  Title, Width, Align, LockFirstColumn, DateFormat, RowHeight, AlignTitle,
#  AlignTitleIcon, HideInMenu, ShowInMenu, ShowAddNewColumn, ?, ?)
r = mp.TableEditEx(TABLE, True, False, False, "", "Name", "", "", WIDE,
                   0, True, 1, 2, -1, 1, True, True, True, False)
log("TableEditEx resize Name -> %s" % r)
r2 = mp.TableApply(TABLE)
log("TableApply -> %s" % r2)
if not (r and r2):
    log("REFUSED: table edit did not report success; file left as opened")
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
           "nameWidth": WIDE, "table": TABLE,
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
