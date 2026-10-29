"""Control for the census window fix: run the old ruler, the new ruler, and the new ruler made narrow.

Crossing midnight made _cmdr_blocks_landed_census_r301.py select archived blocks by "mtime date == today",
so it re-read one of the blocks this shift reported as INSERTED and still printed a green tail.  Saying that
in prose is a claim; this file makes it an artifact by running three things in one process against one
archive and one ledger:

  1. the ruler as it stood in the parent commit (git show, executed from a scratch file) - expected to count
     fewer blocks than it should, and expected to print no line saying what it left out;
  2. the ruler as it now stands - expected to count every block of the shift;
  3. the ruler with DAYS_BACK forced to 0, i.e. the old "today only" shape expressed in the new code -
     expected to refuse outright, because the new boundary gate names the block it just excluded instead of
     quietly reporting half a sheet.

It ABORTs if the old shape does not under-count, or if the narrow shape fails to refuse: a control that
cannot tell the two apart proves nothing.
"""

import io
import os
import re
import subprocess
import sys
import tempfile
import types

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REF = r"D:/moodle/_qoder_cmdr_ref_20260921"
GOZERO = os.path.join(ROOT, "trial", "results", "20261026_gozero")
REL = "trial/human_walk/_cmdr_blocks_landed_census_r301.py"
RECEIPT = os.path.join(GOZERO, "bw339-census-window-old-vs-new-vs-narrow.txt")
sys.path.insert(0, os.path.join(ROOT, "trial", "human_walk"))

TALLY = re.compile(r"TALLY checked=(\d+) green=(\d+) red=(\d+)")
FAULT = re.compile(r"INSTRUMENT_FAULT (.*)")
HEAD = re.compile(r"^(SESSION \S+ \|.*)$", re.M)
EDGE = re.compile(r"^WINDOW_EDGE (.*)$", re.M)


class Quiet(io.StringIO):
    """Both rulers call sys.stdout.reconfigure() on entry, which a plain StringIO cannot answer."""

    def reconfigure(self, *args, **kwargs):
        return self


def capture(module, receipt):
    box = Quiet()
    real, sys.stdout = sys.stdout, box
    try:
        rc = module.main(receipt=receipt)
    finally:
        sys.stdout = real
    text = box.getvalue()
    tally = TALLY.search(text)
    if not tally:
        raise SystemExit("ABORT the run printed no TALLY line: %r" % text[-200:])
    fault = FAULT.search(text)
    head = HEAD.search(text)
    edge = EDGE.search(text)
    return {"rc": rc, "checked": int(tally.group(1)), "green": int(tally.group(2)),
            "red": int(tally.group(3)),
            "fault": fault.group(1) if fault else "(no instrument-fault line printed)",
            "head": head.group(1) if head else "(no window line printed)",
            "edge": edge.group(1) if edge else None,
            "stretches": len(re.findall(r"^  stretch \d+:", text, re.M)), "text": text}


def load_old(sha):
    source = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (sha, REL)],
                            capture_output=True, text=True, encoding="utf-8", check=True).stdout
    if "stamp != today" not in source:
        raise SystemExit("ABORT the parent copy of the ruler does not carry the day filter being reported "
                         "on, so this control would not be testing the shape it claims to test")
    if "WINDOW_EDGE" in source:
        raise SystemExit("ABORT the parent copy already prints its boundary, so it is not the shape under "
                         "test")
    box = tempfile.mkdtemp()
    path = os.path.join(box, "old_census_r301.py")
    io.open(path, "w", encoding="utf-8", newline="\n").write(source)
    module = types.ModuleType("old_census_r301")
    module.__file__ = path
    module.__dict__["__name__"] = "old_census_r301"
    exec(compile(source, path, "exec"), module.__dict__)
    return module


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import _cmdr_blocks_landed_census_r301 as new

    sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD~1"],
                         capture_output=True, text=True, check=True).stdout.strip()
    head = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    for obj in (sha, head):
        if subprocess.run(["git", "-C", ROOT, "cat-file", "-t", obj], capture_output=True, text=True,
                          check=True).stdout.strip() != "commit":
            raise SystemExit("ABORT %s is not a commit object" % obj[:12])

    box = tempfile.mkdtemp()
    old = capture(load_old(sha), os.path.join(box, "old_receipt.txt"))
    today = capture(new, os.path.join(box, "today_receipt.txt"))

    new.DAYS_BACK = 0
    narrow_refused = ""
    narrow = None
    try:
        narrow = capture(new, os.path.join(box, "narrow_receipt.txt"))
    except SystemExit as error:
        narrow_refused = str(error)
    new.DAYS_BACK = 1

    if old["checked"] >= today["checked"]:
        raise SystemExit("ABORT the old shape counted %d and the new one %d - the control shows no "
                         "difference, so nothing here has been proven"
                         % (old["checked"], today["checked"]))
    if today["red"] or today["rc"] != 0:
        raise SystemExit("ABORT the current census is not clean: %d of %d read RED (rc=%d)"
                         % (today["red"], today["checked"], today["rc"]))
    if not (old["red"] == 0 and old["rc"] == 0):
        raise SystemExit("ABORT the old shape did not print a green tail on its short sheet (red=%d rc=%d),"
                         " so the description of the fault being controlled for is wrong"
                         % (old["red"], old["rc"]))
    if old["edge"] is not None:
        raise SystemExit("ABORT the old shape does name its excluded block (%r) - then it was not blind to "
                         "the loss" % old["edge"][:60])
    if narrow is not None or "outside the window" not in narrow_refused:
        raise SystemExit("ABORT the today-only window did not refuse (%s) - the boundary gate does not bite,"
                         " so the widened window is unverified"
                         % ("it answered checked=%d" % narrow["checked"] if narrow else "no message"))

    out = ["CENSUS WINDOW CONTROL bw339 - old ruler vs new ruler vs the new ruler narrowed back",
           "one archive, one ledger, one process; the two sheets below are the same files read twice",
           "rulers: old generation %s, current generation %s (both commits, retrievable with"
           " git cat-file -t)" % (sha, head),
           "",
           "OLD SHAPE (mtime date == today)",
           "  %s" % old["head"],
           "  TALLY checked=%d green=%d red=%d rc=%d" % (old["checked"], old["green"], old["red"], old["rc"]),
           "  it names no excluded block: %s" % ("true - no WINDOW_EDGE line exists in its output"
                                                 if old["edge"] is None else "FALSE, see the control above"),
           "  it prints no stretch line either: %d" % old["stretches"],
           "  instrument-fault line: %s" % old["fault"],
           "  so it closed the sheet green while counting %d block(s) of the shift" % old["checked"],
           "",
           "NEW SHAPE (today plus the day before)",
           "  %s" % today["head"],
           "  TALLY checked=%d green=%d red=%d rc=%d" % (today["checked"], today["green"],
                                                        today["red"], today["rc"]),
           "  %s" % ("WINDOW_EDGE " + today["edge"]),
           "  stretches printed inside the window: %d" % today["stretches"],
           "  instrument-fault line: %s" % today["fault"],
           "",
           "NARROW (new code, DAYS_BACK forced to 0 - the old shape expressed in the new code)",
           "  refused, verbatim: %s" % narrow_refused.split("\n")[0].strip(),
           "",
           "WHAT THIS PROVES: the short sheet is a property of the filter, not of the ledger. The same"
           " archive read %d blocks under the day filter and %d under the two-day one, against %s, in one"
           " process - so nothing between the two counts was caused by a ledger that changed."
           % (old["checked"], today["checked"], new.gate.LEDGER),
           "WHAT IT DOES NOT PROVE: the 00:1x printout itself. That run wrote the shipped receipt and was"
           " overwritten by the fixed one, so its only surviving trace is this session's transcript; the"
           " OLD SHAPE rows above are the same filter re-run against the same archive, which is why they"
           " can be quoted as a measurement and the 00:1x printout cannot.",
           "",
           "TALLY old_checked=%d new_checked=%d delta=%d narrow_refusals=1"
           % (old["checked"], today["checked"], today["checked"] - old["checked"]),
           "GENERATION %s" % head,
           ""]
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out))
    back = io.open(RECEIPT, encoding="utf-8").read()
    if TALLY.search(back) is None or head not in back:
        raise SystemExit("ABORT the control receipt does not carry its own tally or its generation")
    for row in out:
        print(row)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
