"""Re-read every block this session reported as INSERTED and say which ones actually landed.

The applier printed INSERTED for the #359 block while the ledger held zero hits, so a reported
insertion is not proof of delivery.  Now that the landing gate exists, the same family of claims gets
re-checked: for each archived block carrying this session's flower name, the gate is run again and any
RED is named.

Selftest: the census must also be able to call a title that nobody ever posted RED, otherwise a whole
sheet of GREENs would mean nothing.

The window is a run of days, not a calendar day: crossing midnight must not drop the hours logged before
it, so a block counts while its archive stamp falls on today or yesterday.  A gap cutoff alone was tried
and it cut the shift in two at a real five-and-a-half hour break, which is a rest, not a new session -
so the receipt also prints every stretch wider than STRETCH_MINUTES, with the block counts on both sides,
instead of pretending the shift ran without a pause.  The first excluded block is named too: a boundary
with no visible neighbour on the far side is not a boundary.

Line one also carries the tally's own line number and its three counts, and after the file lands the
receipt is re-read to prove that pointer hits.  This sheet is re-run after every landing, so every other
line number in it moves and a block citing one of them cites a snapshot - block #375 did exactly that and
needed an erratum.  Cite line one.

Exit codes: 0 every block landed, 7 some claim has no ledger hit, 8 every single block read RED at once.
That third one is not a delivery verdict - rc=8 fired once when the landing gate grew a second return
value and this census was still comparing a tuple to zero.  A uniformly red sheet is an instrument fault,
so it is called out separately instead of being reported as lost work.
"""

import datetime
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "trial", "human_walk"))

import _cmdr_ledger_landing_check_r300 as gate  # noqa: E402

PROCESSED = gate.PROCESSED
SESSION = "494abfd7"
DAYS_BACK = 1
STRETCH_MINUTES = 60
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw301-this-sessions-blocks-landed.txt")


def flat(text):
    """One receipt line per reading: a wrapped value would move every line number under it.

    The self-anchor on line one is arithmetic over this list, so a gate print that itself
    spans lines silently shifts the tally away from the pointer that claims to name it.
    """
    return " ".join(text.split())


def heading_of(path):
    for line in io.open(path, encoding="utf-8", errors="replace").read().split("\n"):
        if line.startswith("### "):
            return line[4:].strip()
    return ""


def archived():
    """Every archived block of this flower name, newest first, stamped to the second."""
    rows = []
    for name in os.listdir(PROCESSED):
        if not name.startswith(SESSION) or ".inserted_" not in name:
            continue
        path = os.path.join(PROCESSED, name)
        rows.append((os.path.getmtime(path), name, heading_of(path)))
    rows.sort(key=lambda row: row[0], reverse=True)
    if not rows:
        raise SystemExit("ABORT no archived block carries this session's name - nothing to re-read")
    return rows


def session_window(rows):
    """Blocks whose archive stamp lands on today or the day before, plus the first one left outside."""
    now = datetime.datetime.now()
    days = {(now - datetime.timedelta(days=offset)).date() for offset in range(0, DAYS_BACK + 1)}
    kept = [row for row in rows if datetime.date.fromtimestamp(row[0]) in days]
    if not kept:
        raise SystemExit("ABORT the %s-day window holds zero archived blocks - the boundary is wrong, "
                         "widen DAYS_BACK before believing an empty sheet" % (DAYS_BACK + 1))
    excluded = rows[len(kept)] if len(kept) < len(rows) else None
    if excluded is not None:
        older_day = datetime.date.fromtimestamp(excluded[0])
        oldest_kept = min(datetime.date.fromtimestamp(row[0]) for row in kept)
        if (oldest_kept - older_day).days <= 1:
            raise SystemExit("ABORT the block just outside the window (%s, %s) sits a day away from the "
                             "oldest kept block (%s) - that reads like a shift cut in half, widen "
                             "DAYS_BACK before trusting this count"
                             % (excluded[1], older_day, oldest_kept))
    return kept, excluded


def stretches(rows):
    """Runs of blocks separated by less than STRETCH_MINUTES, newest first, so a pause stays visible."""
    runs = [[rows[0]]]
    for newer, older in zip(rows, rows[1:]):
        if (newer[0] - older[0]) / 60.0 > STRETCH_MINUTES:
            runs.append([older])
        else:
            runs[-1].append(older)
    return runs


def stamp_of(seconds):
    return datetime.datetime.fromtimestamp(seconds).strftime("%m-%d %H:%M:%S")


def main(receipt=RECEIPT) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows, excluded = session_window(archived())
    out = ["BLOCKS THIS SESSION REPORTED AS INSERTED - RE-READ AGAINST THE LEDGER bw301",
           "LEDGER %s" % gate.LEDGER,
           "SESSION %s | window = today and the %d day(s) before it, %s .. %s = %d blocks"
           % (SESSION, DAYS_BACK, stamp_of(rows[-1][0]), stamp_of(rows[0][0]), len(rows))]
    for index, run in enumerate(stretches(rows), start=1):
        out.append("  stretch %d: %s .. %s = %d blocks"
                   % (index, stamp_of(run[-1][0]), stamp_of(run[0][0]), len(run)))
    if excluded is None:
        out.append("WINDOW_EDGE no older block exists at all - the window is the whole archive")
    else:
        out.append("WINDOW_EDGE first block excluded: %s  (%s)" % (excluded[1], stamp_of(excluded[0])))
    red = []
    for seconds, name, heading in rows:
        out.append("  %s  (archived %s)" % (name, stamp_of(seconds)))
        out.append("      heading %r" % heading[:90])
        printed = io.StringIO()
        real, sys.stdout = sys.stdout, printed
        try:
            rc, _hinted = gate.check(heading)
        finally:
            sys.stdout = real
        verdict = "GREEN" if rc == 0 else "RED"
        out.append("      gate: %s  %s" % (verdict, flat(printed.getvalue())))
        if rc != 0:
            red.append((name, heading))

    # negative control: a title nobody posted must read RED, or every GREEN above is hollow
    bogus = "这张标题从未进过任何账本_zzz_control"
    printed = io.StringIO()
    real, sys.stdout = sys.stdout, printed
    try:
        bogus_rc, _bogus_hinted = gate.check(bogus)
    finally:
        sys.stdout = real
    bites = bogus_rc == 7
    out.append("NEGATIVE_CONTROL unseen title reads %s (%s)"
               % ("RED as required" if bites else "GREEN - the gate is blind",
                  flat(printed.getvalue())))
    # line one carries the tally's own line number: this receipt is re-run after every landing, so every
    # other line number under it moves and a block that cites one of them cites a snapshot.
    tally_line = len(out) + 1
    out[0] = ("BLOCKS THIS SESSION REPORTED AS INSERTED - RE-READ AGAINST THE LEDGER bw301"
              " | STABLE_ANCHOR line 1 | TALLY_LINE %d | checked %d green %d red %d"
              % (tally_line, len(rows), len(rows) - len(red), len(red)))
    out.append("TALLY checked=%d green=%d red=%d" % (len(rows), len(rows) - len(red), len(red)))
    if red:
        out.append("BLOCKS THAT DID NOT LAND (re-insert required):")
        for name, heading in red:
            out.append("  %s  %r" % (name, heading[:80]))
    else:
        out.append("BLOCKS_THAT_DID_NOT_LAND none")
    verdict_ok = bites and not red
    # every block red at once is the shape a broken call produces, not the shape of lost work:
    # this census read all rows RED for exactly that reason once (the gate grew a second return value)
    fault = bool(rows) and len(red) == len(rows)
    out.append("VERDICT %s" % ("every block this session claimed as delivered is in the ledger, and "
                               "the gate can still see a red" if verdict_ok else
                               "see the RED rows above - a reported insertion without a ledger hit"))
    out.append("INSTRUMENT_FAULT %s"
               % ("YES - all %d blocks read RED at once, which is what a broken call looks like; run "
                  "the gate standalone (its --selftest and one real --title) before re-inserting "
                  "anything" % len(rows) if fault
                  else "no - %d of %d blocks read RED%s"
                       % (len(red), len(rows),
                          ", nothing to chase" if not red else
                          ", and each red above is an individual claim to chase")))
    io.open(receipt, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    landed = io.open(receipt, encoding="utf-8", errors="replace").read().split("\n")
    anchor = re.search(r"TALLY_LINE (\d+) \| checked (\d+) green (\d+) red (\d+)", landed[0])
    if not anchor:
        raise SystemExit("ABORT line one of the receipt lost the self-anchor blocks are told to cite")
    pointed = landed[int(anchor.group(1)) - 1]
    if pointed != "TALLY checked=%s green=%s red=%s" % anchor.groups()[1:]:
        raise SystemExit("ABORT the self-anchor on line one points at %r instead of at its own tally"
                         % pointed[:70])
    print("STABLE_ANCHOR line 1 -> line %s reads %s" % (anchor.group(1), pointed))
    for row in out:
        print(row)
    print("WROTE %s" % receipt)
    return 8 if fault else (0 if verdict_ok else 7)


def selftest():
    """The fault sentinel has to bite, or a real loss would read the same as a broken call."""
    import tempfile
    rows, _excluded = session_window(archived())
    box = tempfile.mkdtemp()
    empty = os.path.join(box, "empty_ledger.md")
    io.open(empty, "w", encoding="utf-8").write("# a ledger that holds nothing\n")
    real_ledger = gate.LEDGER
    try:
        gate.LEDGER = empty
        rc = main(receipt=os.path.join(box, "selftest_receipt.txt"))
    finally:
        gate.LEDGER = real_ledger
    if rc != 8:
        print("SELFTEST_RED with an empty ledger every block must read RED and the census must "
              "answer 8 (instrument fault), but it answered %d" % rc)
        return 10
    print("SELFTEST_OK with the ledger swapped for an empty file all %d archived blocks read RED at "
          "once and the census answered 8 (instrument fault) instead of reporting lost work"
          % len(rows))
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    sys.exit(main())
