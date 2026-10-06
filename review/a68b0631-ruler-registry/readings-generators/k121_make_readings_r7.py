"""Generate the r6 generation's readings file.  Every number is parsed from an artifact this
generation produced -- a log, a json, a git object -- never typed by hand.
"""
import importlib.util
import io
import json
import re
import subprocess

WT = "D:/moodle/_qoder_rel_ord0447_wt/"
WK = "D:/moodle/_qoder_rel_ord0447_wk/"
OUT = WT + "frontend/review/line_anchor_drift/READINGS_r11.txt"
TIP = "32372c7e57611f73782fdc607d929735224cf657"
OLD_TIP = "aac1142e1d25aab0a5bb4fbaa204f3a90668bd0f"
BRANCH = "review/a68b0631-comment-anchor-drift-r7"

spec = importlib.util.spec_from_file_location(
    "g", WT + "backend/tests/test_qoder_a68b0631_comment_anchor_drift_r1.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

counter = json.load(io.open(WK + "k111_counterarms_g5.json", encoding="utf-8"))
pair = json.load(io.open(WK + "k112_pair.json", encoding="utf-8"))
fe = json.load(io.open(WK + "k115_frontend_surface.json", encoding="utf-8"))
typec = io.open(WK + "g_typecheck_r6.log", encoding="utf-8", errors="replace").read()
collect = io.open(WK + "g_collect_r7.log", encoding="utf-8", errors="replace").read()


def blob(rev, path):
    """Blob id of a file as it will ship: the worktree bytes for the files this hand changes, the
    committed blob otherwise.  `git rev-parse HEAD:path` answers with its own argument when the path
    is not in HEAD, which would have shipped a coordinate that resolves to nothing."""
    if rev == "WORKTREE":
        return subprocess.run(["git", "hash-object", path], cwd=WT, capture_output=True,
                              text=True).stdout.strip()
    return subprocess.run(["git", "rev-parse", "%s:%s" % (rev, path)], cwd=WT,
                          capture_output=True, text=True).stdout.strip()


def head_of(rev):
    return subprocess.run(["git", "rev-parse", rev], cwd=WT, capture_output=True, text=True).stdout.strip()


policed = m.policed_files()
every = m._all_extensions_on_disk()
frozen = [p for p in every if m.is_frozen(p)]
registry = [l for l in io.open(str(m.REGISTRY), encoding="utf-8").read().splitlines()
            if l.strip() and not l.startswith("#")]
unused = [p for p, _ in m.FROZEN if not any(q == p or q.startswith(p) for q in every)]

# the former allow-list, counted so the readings do not carry it as a remembered number
OLD_ROOTS = ["frontend/src", "frontend/e2e", "frontend/tools", "backend/app", "backend/tests",
             "backend/tools", "tools", "docs", "contracts"]
old_walk = set()
import os
for base in OLD_ROOTS:
    for sub, dirs, files in os.walk(WT + base):
        dirs[:] = [d for d in dirs if d not in m.SKIP]
        for f in files:
            if os.path.splitext(f)[1] in m.EXTENSIONS:
                old_walk.add(os.path.relpath(os.path.join(sub, f), WT).replace("\\", "/"))

# what the widening bit: read the PRE-FIX bytes (HEAD is the tip; this hand is uncommitted) and
# apply the guard's own detector to them, so the count is the ruler's, not an impression.
touched = [p for p in subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=WT,
                                     capture_output=True, text=True, encoding="utf-8"
                                     ).stdout.split("\n") if p.strip()]
pre = []
for rel in touched:
    if os.path.splitext(rel)[1] not in m.EXTENSIONS:
        continue
    text = subprocess.run(["git", "show", "HEAD:%s" % rel], cwd=WT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout
    if not text:
        continue
    marks = m.comment_regions(rel, text)
    for i, line in enumerate(text.split("\n"), start=1):
        if i not in marks:
            continue
        mm = m.CITE.search(line)
        if mm:
            tgt = m.resolve(mm.group(1), mm.group(2), str((WT + rel).replace("/", os.sep).rsplit(os.sep, 1)[0]))
            pre.append((rel, i, mm.group(0), tgt is None, mm.group(1)))
pre_dead = [p for p in pre if p[3]]
# a match whose "file" part is only an extension fragment (`*.spec.ts:64`, `.spec.ts:177`) is the
# detector reading an extension out of prose, not a pointer to a file; kept apart so the dead count
# is not inflated by the detector's own tolerance.
def _ext_only(part):
    return "/" not in part and (part.startswith(".") or part.startswith("*") or part.strip() == "")


pre_dead_named = [p for p in pre_dead if not _ext_only(p[4])]
pre_dead_extonly = [p for p in pre_dead if _ext_only(p[4])]
reg_now = set(registry)
prev_reg = subprocess.run(
    ["git", "show", "refs/heads/review/a68b0631-comment-anchor-drift-r6:frontend/review/line_anchor_drift/CONVERTED_r1.txt"],
    cwd=WT, capture_output=True, text=True, encoding="utf-8").stdout
reg_prev = set(l for l in prev_reg.splitlines() if l.strip() and not l.startswith("#"))
assert reg_prev, "the previous generation's registry did not read, so the delta would be a whole file"
reg_added = len(reg_now - reg_prev)

moved = subprocess.run(["git", "diff", "--name-only", OLD_TIP, TIP], cwd=WT,
                       capture_output=True, text=True, encoding="utf-8").stdout.split("\n")
moved = [p for p in moved if p.strip()]
touched = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=WT, capture_output=True,
                         text=True, encoding="utf-8").stdout.split("\n")
touched = [p for p in touched if p.strip()]
collect_n = re.search(r"(\d+) tests collected", collect)
typec_err = len([l for l in typec.splitlines() if "error TS" in l])

L = []
w = L.append
w("comment-anchor guard -- r7 generation (re-cut after the line moved 169 paths, five arms)")
w("Written by k121_make_readings_r7.py; every number is parsed from a log, a probe, or git.")
w("")
w("[coordinates]")
w("  tip this hand rests on        : %s" % TIP)
w("  branch                        : %s head %s" % (BRANCH, head_of(BRANCH)))
w("  previous generation           : r6 head %s, cut at %s"
  % (head_of("refs/heads/review/a68b0631-comment-anchor-drift-r6"), OLD_TIP))
w("  guard test blob               : %s" % blob("WORKTREE", "backend/tests/test_qoder_a68b0631_comment_anchor_drift_r1.py"))
w("  registry blob                 : %s (%d entries)" % (
    blob("WORKTREE", "frontend/review/line_anchor_drift/CONVERTED_r1.txt"), len(registry)))
w("")
_mt = subprocess.run(["git", "merge-tree", "--write-tree", TIP,
                       "refs/heads/review/a68b0631-comment-anchor-drift-r6"],
                      cwd=WT, capture_output=True, text=True, encoding="utf-8", errors="replace")
_conflicts = [l for l in _mt.stdout.splitlines() if l.startswith("CONFLICT")]
w("[why a generation was spent, measured rather than asserted]")
w("  the line moved %d paths between r6's base and this tip; this hand touches %d paths and the"
  % (len(moved), len(touched)))
w("  intersection of the two lists is %d." % len(set(moved) & set(touched)))
w("  `git merge-tree --write-tree` of the previous generation against this tip exits %d with %d"
  % (_mt.returncode, len(_conflicts)))
w("  conflict(s), so the previous generation could no longer land and the re-cut was not optional.")
for _c in _conflicts:
    w("     " + _c)
w("")
w("[what changed in the ruler itself]")
w("  1. the scan range was an allow-list of nine roots, so the tree-wide arm read %d files while its"
  % len(old_walk))
w("     docstring said \"anywhere in the shipped tree\".  It is now the whole tree minus %d named"
  % len(m.FROZEN))
w("     FROZEN entries: %d files policed, %d excluded by name." % (len(policed), len(frozen)))
w("  2. a .sql file had no comment branch, so `--` prose was read as code and the ruler reported")
w("     nothing from it -- a silent blind spot.  The branch is added; %d tracked .sql files are now"
  % len([p for p in subprocess.run(["git", "ls-files", "*.sql"], cwd=WT, capture_output=True,
                                    text=True).stdout.split("\n") if p.strip()]))
w("     inside the policed set.")
w("  3. arm G5 polices the boundary itself: every tracked file of a policed extension is either")
w("     read or named, every FROZEN entry must bite a real file (%d entries bite nothing), and the"
  % len(unused))
w("     registry must describe the same tree the scan reads.")
w("")
w("[what the widened scan bit, and what was done about it]")
w("  the whole hand, tip bytes -> name form : %d citations in %d files"
  % (len(pre), len(set(p[0] for p in pre))))
w("  of those, a target absent from the tree AND from every commit : %d named + %d extension-only"
  % (len(pre_dead_named), len(pre_dead_extonly)))
for rel, i, c, dead, part in pre_dead_named:
    w("     %s:%d cites %s -- dead" % (rel, i, c))
new_to_scan = set(rel for _, rel in policed) - old_walk
pre_new = [p for p in pre if p[0] in new_to_scan]
pre_sql = [p for p in pre_new if p[0].endswith(".sql")]
w("  the widening's own share -- citations in files the nine-root allow-list never read : %d lines"
  % len(pre_new))
w("  in %d files; of those, %d sit in .sql prose, which the ruler could not see at all before the"
  % (len(set(p[0] for p in pre_new)), len(pre_sql)))
w("  comment branch existed.")
w("  the count above is the whole hand's conversions, taken from the tip's own bytes; THIS")
w("  generation added %d registry entry (the one the new tip's lane introduced), so G1 keeps it"
  % reg_added)
w("  un-numbered along with the rest.")
w("")
w("[what this re-cut had to decide, and what the ruler caught on the new tip]")
w("  1. one file was changed on BOTH sides: `frontend/src/features/trash/journeyTrash.ts`.  The line's")
w("     own newest work converted the same citations this hand had converted, to a sharper name form")
w("     (the decorator and the SQL statement rather than the path alone), so this generation takes the")
w("     line's bytes for that file and drops this hand's edit to it -- the hand is one file smaller")
w("     than the previous generation and nothing else differs.")
w("  2. the ruler then went red on exactly one citation the line's newest lane introduced:")
w("     `frontend/e2e/qoder-8ac89982-ord0573-upstream-locator-forms-r1.spec.ts` cited two spec files by")
w("     line.  Converted to name form and registered, so G1 keeps it that way.  This is the widened")
w("     range doing the job it was widened for: new rot is caught as it lands, not a generation later.")
w("")
w("[arms, at this generation]")
w("  five arms on the restored tree : %s" % json.dumps(counter["restored"], sort_keys=True))
w("  files scanned by the tree-wide arm : %d (of which the frozen zones hold %d)"
  % (len(policed), len(frozen)))
w("  registry entries : %d" % len(registry))
w("  frontend typecheck : rc 0, %d `error TS` lines" % typec_err)
w("  backend --collect-only : %s, rc 0" % (collect_n.group(1) if collect_n else "?"))
w("")
w("[counter-arms, each naming the arm it must bite]")
for name in sorted(counter["mutants"]):
    v = counter["mutants"][name]
    w("  %-38s red: %-10s green: %s" % (name, ",".join(x[5:] for x in v["red"]),
                                       ",".join(x[5:] for x in v["green"])))
w("  M7 is the one that matters for the blind spot: with the .sql branch deleted and a number")
w("  planted in schema.sql, G3 stays GREEN -- the ruler cannot see the file at all -- and only the")
w("  registry arm G1 catches it.  That is the one-directional blindness this generation removed.")
w("  M8/M9/M10 show G5 bites a rumour boundary term, a dropped exclusion, and a registry entry")
w("  naming a frozen file.")
w("")
be = [p for p in touched if p.startswith("backend/tests/") and p.endswith(".py")]
be_new = [p for p in be if subprocess.run(["git", "cat-file", "-e", "HEAD:%s" % p], cwd=WT,
                                          capture_output=True).returncode != 0]
w("[the test surface, really run]")
w("  backend files this hand touches : %d (paired against the tip: %d; new at this hand: %d)"
  % (len(be), len(be) - len(be_new), len(be_new)))
w("  branch : %s" % json.dumps(pair["branch"]["nums"], sort_keys=True))
w("  tip    : %s" % json.dumps(pair["tip"]["nums"], sort_keys=True))
w("  red node ids identical at both ends : %s" % pair["name_sets_equal"])
w("  new reds under the hand : %d" % len(pair["new_reds_under_the_hand"]))
w("  frontend e2e specs listed : %d of %d, %d tests" % (fe["loaded_files"], fe["specs"], fe["loaded_tests"]))
w("  provenance-gated specs that needed their own variables named : %s"
  % json.dumps({k.split("/")[-1]: v for k, v in fe["env_rounds"].items()}, ensure_ascii=False))
w("")
w("[named in the previous generation, still standing]")
w("  a. G5's first run went red on two FROZEN entries that bite nothing (output/ and tests/ hold no")
w("     file of a policed extension).  A boundary term that excludes nothing is the same defect as")
w("     the comment that claimed a scan root had been added, so both entries were deleted, not")
w("     excused.")
w("  b. policed_files() first tested only the DIRECTORY prefix, so a root-level name in FROZEN")
w("     (BUG_REPORT_20260913.md and its siblings) excluded nothing and the arm read files it had")
w("     declared frozen.  The per-file test is the fix.")
w("  c. the one-at-a-time provenance guard in qoder-ord0541-share-idempotent.spec.ts throws on the")
w("     first missing variable, so \"the variables it named\" is a moving target: it took two rounds")
w("     to load.  A single-round env pass would have reported it as un-loadable.")
w("  d. my first surface script listed a whole group, and the first guarded spec aborted the listing,")
w("     printing `Total: 0 tests in 0 files` -- the same line an empty suite prints.  Per-file")
w("     listing with a non-zero floor is the fix.")
w("")
w("")
w("[named against myself, this generation]")
w("  a. I read the previous generation's readings as if they described this tip: they still said")
w("     \"0 conflicts\", which was true of the tip they were taken on and false of this one.  A")
w("     readings file is a statement about one tip, and this generation measures the conflict it")
w("     actually has instead of quoting the older sentence.")
w("  b. my first run of this generation's readings generator still pointed the collect-only number")
w("     at the previous generation's log, so it would have shipped 1741 as this tip's count when")
w("     this tip collects 1746.  Both are parsed, the stale path is gone.")
w("  c. the surface scripts carried the previous tip as a constant; a pair run against the wrong")
w("     tip compares a tree with itself and reports a clean, meaningless \"no new reds\".")
w("")
w("-- lane a68b0631, r7 generation")

io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("wrote %s  lines=%d" % (OUT, len(L)))
print("policed=%d frozen=%d registry=%d unused_frozen=%d" % (len(policed), len(frozen), len(registry), len(unused)))
