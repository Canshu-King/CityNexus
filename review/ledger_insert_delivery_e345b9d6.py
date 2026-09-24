"""Insert this lane's #2e delivery block into `## DELIVERIES` of the control ledger.

Newest-first: the block goes directly under the `## DELIVERIES` heading, before whoever is currently
first.  Nothing else is touched, and that is proven rather than asserted -- the script re-reads the
file immediately before writing, refuses if the anchor is not unique, and verifies that deleting its
own block reproduces the original bytes with the original sha256.

The timestamp inside the block is stamped from the clock at write time; a hand-typed minute is how a
ledger line becomes an hour off.
"""

import datetime
import hashlib
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

LEDGER = "D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
BLOCK = "D:/moodle/_qoder_d_lane_20260923/review/ledger_block_e345b9d6_2e.md"
HEADING = "## DELIVERIES（车道交付登记处 · 追加，不改别人的块）"
TIME_TOKEN = "@2026-09-25 03:1x+08"


def read(path: str) -> str:
    # Universal newlines would silently turn the agreed LF ledger into CRLF on Windows.
    return open(path, encoding="utf-8", newline="").read()


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    original = read(LEDGER)
    block = read(BLOCK).replace("\r\n", "\n").strip() + "\n\n"

    now = datetime.datetime.now().astimezone()
    stamp = now.strftime("%Y-%m-%d %H:%M%z")
    if TIME_TOKEN not in block:
        print(f"ABORT: the block no longer carries its own time token {TIME_TOKEN!r}")
        return 2
    block = block.replace(TIME_TOKEN, f"@{stamp[:16]}{stamp[19:]}", 1)

    if original.count(HEADING) != 1:
        print(f"ABORT: the DELIVERIES heading is not unique ({original.count(HEADING)} hits)")
        return 3
    if block.strip() in original:
        print("ALREADY THERE: this exact block is already in the ledger -- nothing written")
        return 0

    head_at = original.index(HEADING)
    tail_start = original.index("\n### ", head_at) + 1  # first existing delivery block
    new_text = original[:tail_start] + block + original[tail_start:]

    # Nothing-but-my-block, checked three ways.
    ok_prefix = new_text[:tail_start] == original[:tail_start]
    ok_suffix = new_text[tail_start + len(block) :] == original[tail_start:]
    ok_reversible = new_text.replace(block, "", 1) == original
    crlf_delta = new_text.count("\r\n") - original.count("\r\n")
    if not (ok_prefix and ok_suffix and ok_reversible):
        print(
            f"ABORT: insertion is not a pure insert (prefix={ok_prefix} suffix={ok_suffix} "
            f"reversible={ok_reversible})"
        )
        return 4
    if crlf_delta:
        print(f"ABORT: this write would add {crlf_delta} CRLF pairs to an LF ledger")
        return 5

    # Last look: the ledger is rewritten by other lanes while I am composing.
    if read(LEDGER) != original:
        print("ABORT: the ledger changed between read and write -- re-run to re-measure offsets")
        return 6

    with open(LEDGER, "w", encoding="utf-8", newline="") as fh:
        fh.write(new_text)

    after = read(LEDGER)
    print(f"inserted at line {after[:tail_start].count(chr(10)) + 2}")
    print(f"block bytes={len(block.encode('utf-8'))} sha256[:16]={sha(block)} stamped={stamp}")
    print(f"ledger bytes {len(original.encode('utf-8'))} -> {len(after.encode('utf-8'))} (+{len(block.encode('utf-8'))})")
    print(f"ledger sha256[:16] {sha(original)} -> {sha(after)}")
    print(f"lines {original.count(chr(10))} -> {after.count(chr(10))} (+{block.count(chr(10))})")
    print(f"pure_insert={ok_prefix and ok_suffix} reversible_delete_yields_original={after.replace(block, '', 1) == original}")
    print(f"crlf_delta={crlf_delta} (ledger keeps LF)")
    return 0 if after.replace(block, "", 1) == original else 7


if __name__ == "__main__":
    sys.exit(main())
