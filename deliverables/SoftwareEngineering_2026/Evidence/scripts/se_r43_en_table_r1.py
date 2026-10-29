"""EN classroom mpp: widen the Task Name column to 32 chars.

WHAT ACTUALLY WORKED (this exact sequence produced the shipped bytes,
sha256/16 5eb7b1e7122c7fc6, verified 0-difference by se_r43_fidelity_en_r1.py):

  1. TableApply("<live table>")   -- the saved Gantt view registered a
     "课堂总览" table that does not exist in the file (R4.1 created it only
     in probe intermediates), so EVERY TableEditEx first died with
     "该表已被删除". Applying the live standard table re-points the view and
     heals the reference.
  2. TableEditEx(Name="<live table>", TaskTable=True, FieldName="Name",
     Width=32) under EARLY binding (gencache.EnsureDispatch) -- named
     arguments are honoured; late binding drops them silently.
  3. TableApply again, CalculateAll, FileSave.

The create-the-missing-table path ("TableEditEx(Create=True, NewName=课堂
总览)") was tried first and fails with "名称出错" -- Project refuses to
reuse the name the dangling view references. It is kept below in comments
for the record, not executed.

The earlier commit of this script showed the failed create-path version;
that was misleading evidence, fixed 2026-10-29 08:40.
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
CHR10 = chr(10)
COPY_NAME = "课堂总览"  # the view's registered table name, rebuilt here
TABLE = "\u8bfe\u5802\u603b\u89c8"  # 课堂总览 - the table the R4.1 build applied





def dl(t):
    try:
        v = t.Deadline
        return dstr(v) if v else ""
    except Exception:
        return ""
def dstr(v):
    try:
        return v.strftime("%Y-%m-%d")
    except Exception:
        return str(v)[:10]
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
TABLE_LIVE = "项"  # the standard table that exists and backs the view

r1 = mp.TableApply(TABLE_LIVE)
log("TableApply live table (heals the dangling view reference) -> %s" % r1)
r2 = mp.TableEditEx(Name=TABLE_LIVE, TaskTable=True, FieldName="Name",
                    Width=WIDE)
log("TableEditEx resize Name=32 -> %s" % r2)
r3 = mp.TableApply(TABLE_LIVE)
log("TableApply -> %s" % r3)
if not (r1 and r2 and r3):
    log("REFUSED: a step reported failure; no save")
    mp.FileCloseEx(0)
    mp.Quit()
    sys.exit(1)


# ---- R7 addendum: the plan's own M1-M8 names are Chinese (R4 only renamed
# M9-M13); the EN twin carries the English mirror of each, keeping the
# Chinese original in the row notes. Dates/deadlines untouched.
M1_TO_8_EN = {
    "M1": "M1 Topic and scope confirmed",
    "M2": "M2 Requirements baseline draft",
    "M3": "M3 Architecture design complete",
    "M4": "M4 Backend trunk running end to end",
    "M5": "M5 Providers integrated",
    "M6": "M6 Agent verified in the field",
    "M7": "M7 Frontend wired to the backend",
    "M8": "M8 Integration line stable",
}
renamed_m18 = 0
for i in range(1, q.Tasks.Count + 1):
    t = q.Tasks.Item(i)
    if t.Milestone:
        nm = str(t.Name).strip()
        tag = nm.split()[0] if nm else ""
        if tag in M1_TO_8_EN and M1_TO_8_EN[tag] != nm:
            old = str(t.Name)
            t.Notes = "Classroom display name (EN): " + str(M1_TO_8_EN[tag]) + CHR10
            t.Notes = t.Notes + "Chinese plan name: " + old + CHR10
            t.Notes = t.Notes + "WBS " + str(t.WBS) + "; plan date " + dstr(t.Start) + ", deadline " + (dl(t) or "none") + "."
            t.Name = M1_TO_8_EN[tag]
            renamed_m18 += 1
log("M1-M8 renamed to EN: %d" % renamed_m18)

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
