"""ORD-0477 lane: the ledger-inbox write door, one step generalized from the ORD-0417 guard.

Why a new file instead of editing `run/ord0417_block_guard_r1.py`: that instrument's own definition
line (`:33`, the 120-second tolerance) is quoted in a block that is already in the ledger, and moving
code under a published citation is how a coordinate stops resolving.  This copy keeps the three
refusals byte-for-byte and widens one thing that was too narrow for reuse:

  the "already delivered" scan of the ledger matched only `### ORD-0417 · 车道 8ac89982`, so an
  ORD-0477 re-delivery would have been caught only by the `_processed` copies.  The filter is now
  `### ORD-<digits> · 车道 8ac89982`, which is what the rule always meant: *my* headers, whichever
  order they belong to.

The three refusals, unchanged in meaning:
  1. the header's clock time must be the wall clock at write time (±120 s) -- no stamp copied out of
     a relayed message;
  2. the destination may not already exist with different bytes -- that overwrite is what made the
     double insert possible;
  3. the exact header line may not already appear in the ledger or in any `_processed` copy -- a
     corrected block takes a new filename, a new time, and names what it supersedes.

usage: python ord0477_block_guard_r1.py <out path> [--from <prepared text>]   (or stdin)
       python ord0477_block_guard_r1.py --selftest
"""
import datetime
import glob
import hashlib
import io
import os
import re
import sys
import unicodedata

LEDGER = r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:/moodle/_qoder_ledger_inbox"
PROCESSED = os.path.join(INBOX, "_processed")
TOLERANCE_S = 120
MY_HEADERS = re.compile(r"^### ORD-\d+ · 车道 8ac89982")


def now_local():
    return datetime.datetime.now().astimezone()


def header_of(text):
    first = text.split("\n", 1)[0].strip()
    if not first.startswith("### "):
        raise SystemExit("REFUSE: first line is not a `### ` block header")
    return first


def parse_header_time(header):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})", header)
    if not m:
        raise SystemExit("REFUSE: header carries no `YYYY-MM-DD HH:MM+08` stamp")
    y, mo, d, h, mi = (int(x) for x in m.groups())
    try:
        return datetime.datetime(y, mo, d, h, mi)
    except ValueError as e:
        raise SystemExit(f"REFUSE: header stamp is not a real date/time: {e}")


def seen_headers():
    """Every `### ` header sitting in `_processed`, plus my own headers currently in the ledger."""
    out = {}
    for path in glob.glob(os.path.join(PROCESSED, "*")):
        try:
            head = io.open(path, encoding="utf-8", errors="replace").readline().strip()
        except OSError:
            continue
        if head.startswith("### "):
            out.setdefault(head, []).append(os.path.basename(path))
    if os.path.exists(LEDGER):
        for line in io.open(LEDGER, encoding="utf-8", errors="replace"):
            line = line.strip()
            if MY_HEADERS.match(line):
                out.setdefault(line, []).append("ledger")
    return out


def write_block(out_path, text):
    header = header_of(text)
    stamp = parse_header_time(header)
    delta = abs((now_local().replace(tzinfo=None) - stamp).total_seconds())
    if delta > TOLERANCE_S:
        raise SystemExit(
            f"REFUSE: header says {stamp:%F %H:%M} but the clock is {now_local():%F %H:%M} "
            f"({int(delta)} s apart) -- stamp from the clock, not from the relayed message"
        )
    if os.path.exists(out_path):
        old = io.open(out_path, encoding="utf-8", errors="replace").read()
        if old != text:
            raise SystemExit(
                f"REFUSE: {os.path.basename(out_path)} already exists with different bytes; "
                "re-delivery takes a new filename"
            )
    hits = {
        k: v
        for k, v in seen_headers().items()
        if unicodedata.normalize("NFC", k) == unicodedata.normalize("NFC", header)
    }
    if hits:
        raise SystemExit(
            f"REFUSE: this exact header was already delivered ({list(hits.values())[0]}); "
            "a corrected block must carry a new time and name what it supersedes"
        )
    io.open(out_path, "w", encoding="utf-8", newline=chr(10)).write(text)
    print(
        os.path.basename(out_path),
        len(text.encode("utf-8")),
        "bytes",
        "sha1",
        hashlib.sha1(text.encode("utf-8")).hexdigest(),
        "->",
        out_path,
    )
    return 0


def selftest():
    """Each refusal must fire FOR ITS OWN REASON, isolated from the other two."""
    global PROCESSED
    ok = []
    real_processed = PROCESSED
    stamp_now = f"{now_local():%F %H:%M}+08"
    header_prefix = "### ORD-0477 · 车道 8ac89982 · selftest"

    # rule 1: a stamp hours old, on header text nobody has delivered
    stale = f"### ORD-0477 · 车道 8ac89982 · selftest stale · {now_local() - datetime.timedelta(hours=3):%F %H:%M}+08\n\nbody\n"
    try:
        write_block(os.path.join(INBOX, "selftest477_should_not_exist.md"), stale)
        ok.append(("stale-clock refusal", "DID NOT FIRE"))
    except SystemExit as e:
        ok.append(("stale-clock refusal", ("fired: " + str(e))[:100]))

    # rule 3: a header already sitting in `_processed`, stamped at the CURRENT minute so rule 1
    # cannot fire first; the fixture prefix is ORD-0477 to prove the widened ledger filter is not
    # what carries this case
    tmp = r"D:/moodle/_qoder_b_ord0417_20260928/evidence/_selftest477_fixture"
    os.makedirs(tmp, exist_ok=True)
    dup_header = f"{header_prefix} dup · {stamp_now}"
    io.open(os.path.join(tmp, "fixture.md"), "w", encoding="utf-8", newline=chr(10)).write(
        dup_header + "\n\nearlier body\n"
    )
    PROCESSED = tmp
    try:
        write_block(os.path.join(INBOX, "selftest477_should_not_exist.md"), dup_header + "\n\nnew body\n")
        ok.append(("duplicate-header refusal", "DID NOT FIRE"))
    except SystemExit as e:
        ok.append(("duplicate-header refusal", ("fired: " + str(e))[:100]))
    PROCESSED = real_processed

    # rule 2: same filename, different bytes
    fresh = f"{header_prefix} fresh · {stamp_now}\n\nbody\n"
    fp = os.path.join(INBOX, "selftest477_guard.md")
    write_block(fp, fresh)
    try:
        write_block(fp, fresh.replace("body", "body two"))
        ok.append(("different-bytes refusal", "DID NOT FIRE"))
    except SystemExit as e:
        ok.append(("different-bytes refusal", ("fired: " + str(e))[:100]))
    os.remove(fp)
    import shutil

    shutil.rmtree(tmp, ignore_errors=True)
    for name, result in ok:
        print(f"{name}: {result}")
    stray = [p for p in os.listdir(INBOX) if "selftest477" in p]
    print("inbox residue after selftest:", stray)
    return 1 if any("DID NOT FIRE" in r for _, r in ok) or stray else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--from" in sys.argv:
        src = sys.argv[sys.argv.index("--from") + 1]
        text = io.open(src, encoding="utf-8").read()
    else:
        text = sys.stdin.buffer.read().decode("utf-8")
    sys.exit(write_block(sys.argv[1], text))
