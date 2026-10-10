"""Undo my own misplaced log append (20:13) - the same block already lives in the real log.

live_checks/PATROL_LOG.md is a different, older file; my log_round.py pointed at it by mistake and appended
3037 B there. The identical block was then written to patrol/PATROL_LOG.md (the 359 KB one). This script
verifies the block is present in the real log BEFORE truncating the stray copy, so nothing is lost - it only
removes bytes I added minutes ago to the wrong file. No other file is touched.
"""
import io
import os

STRAY = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\PATROL_LOG.md"
REAL = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\patrol\PATROL_LOG.md"
MARK = "## 轮 75 · 2026-09-28"

s = io.open(STRAY, encoding="utf-8").read()
r = io.open(REAL, encoding="utf-8").read()
# two different files, proven by size: if they were the same file (junction/hardlink), the stray copy could
# not be ~5 KB while the real one is ~360 KB. Guard anyway so a surprise aborts before any write.
ssz, rsz = os.path.getsize(STRAY), os.path.getsize(REAL)
print("stray=%d B  real=%d B" % (ssz, rsz))
assert rsz > 300000, "the real log is not the big one (%d B) - refusing to touch anything" % rsz
assert ssz < 20000, "the stray file is unexpectedly large (%d B) - stop and look" % ssz
i = s.find(MARK)
assert i > 0, "MARK not found in the stray file - refusing to touch anything"
block = s[i:]
print("stray file=%d B  block starts at char %d  block=%d B" % (len(s.encode("utf-8")), i, len(block.encode("utf-8"))))
# The real log got its own 轮 75 entry seconds later, so the two blocks are NOT byte-identical (the header
# carries the clock). The guard is therefore: the same numbered entry exists in the real log AND its body
# carries the same measured counts, so removing the stray copy loses no fact.
real_lines = [l for l in r.splitlines() if l.startswith(MARK)]
print("real log entries with this header=%d" % len(real_lines))
assert len(real_lines) == 1, "轮 75 in the real log is not exactly one entry - do not touch the stray copy"
j = r.find(MARK)
real_block = r[j:]
keys = ["5869413510", "2690a3f7eb0b817a882212854ad906bfc8703e2d"]
shared = [k for k in keys if k in block and k in real_block]
print("shared markers present in BOTH copies=%s" % shared)
assert len(shared) == len(keys), "the real log's entry is missing %s - keep the stray copy" % (
    [k for k in keys if k not in real_block])
kept = s[:i].rstrip("\n") + "\n"
io.open(STRAY, "w", encoding="utf-8", newline="\n").write(kept)
after = io.open(STRAY, encoding="utf-8").read()
print("stray after=%d B  removed=%d B  real log=%d B  real still has 轮 75=%s"
      % (len(after.encode("utf-8")), len(s.encode("utf-8")) - len(after.encode("utf-8")),
         len(io.open(REAL, "rb").read()), len([l for l in io.open(REAL, encoding="utf-8").read().splitlines()
                                               if l.startswith(MARK)])))
