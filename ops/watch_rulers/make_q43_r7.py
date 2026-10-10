"""Derive claim_coordinate_check_r7.py from r6 - ORD-0371 second half.

Measured, not assumed (receipt `_q43_r6_refusal_diag_r1.json`, 5948 B): r6's committed-path arm flipped only
1 of 31 pending blocks, so I read the 130 remaining NUMBER_WITHOUT_COORDINATE findings instead of shipping
another voucher. They split two ways:

  instrument false positives - tokens that are not quantity claims at all:
    `127` in `--host 127.0.0.1`        -> part of an IPv4 literal
    `0,145,522,44` in `框 [0,145,522,44]` -> a bracketed data array (a verbatim screen/DOM reading)
    `8138 的监听 pid 9984`               -> a port and a process id written in prose, not a count
  genuine refusals that stay red, on purpose:
    `73 处` beside only a gauge cell name   - the cell name is not retrievable, `tools/cnx_copy_tiers_r1.py` is
    `（404）` with no status word nearby    - `http_status=404` is the shape the gate asks for
    `16623` as "the ledger's line 16623"   - needs `ledger path:16623`

r7 recognises the first group as *classes* (so they land in the printed exempt buckets and never as silent
skips), and touches nothing about how real counts are judged. Anchors are exact single matches, ast.parse
gates the write, and a separate two-way tester (q43_r7_selftest_r1.py) proves each new class still refuses
when the literal context is absent.
"""
from __future__ import annotations

import ast
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "claim_coordinate_check_r6.py")
DST = os.path.join(HERE, "claim_coordinate_check_r7.py")

HELPER = '''
# ---- r7 (ORD-0371): recognise tokens that are not quantity claims ------------------------------
# Every one of these is a CLASS that gets printed in the exempt buckets, not a silent skip - a lane reading
# "exempt: IP_PART 1, PORT 2" can see what was discounted. None of them fires on a counted noun: `命中 145 个`
# next to an array literal still refuses (asserted both ways in q43_r7_selftest_r1.py).
IP_QUAD = re.compile(r"\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}")
PID_WORDS = re.compile(r"\\b(?:pid|ppid|processid|进程号|进程)\\b|CommandLine", re.I)
PORT_WORDS = re.compile(r"\\b(?:port|端口|监听|listen|listening|LISTENING)\\b")


def literal_class(text, start, end):
    """(class, why) when this digit run is a piece of a literal rather than a count of things."""
    near = text[max(0, start - 12):min(len(text), end + 12)]
    if IP_QUAD.search(near):
        return "IP_PART", "digits inside an IPv4 literal"
    lo = text.rfind("[", 0, start)
    hi = text.find("]", end)
    if lo != -1 and hi != -1 and hi - lo <= 60 and "," in text[lo:hi]:
        return "ARRAY_LITERAL", "digits inside a bracketed data array [a,b,c]"
    ctx = text[max(0, start - 40):min(len(text), end + 40)]
    if PID_WORDS.search(ctx):
        return "PID", "process id next to a pid/CommandLine word"
    if PORT_WORDS.search(ctx):
        return "PORT", "port number next to a port/listening word (prose form, not `:NNNN`)"
    return None, None


'''

ANCHORS = [
    ('VERSION = "Q43_r6"', 'VERSION = "Q43_r7"'),
    ("def unit_of(text, start, end):", HELPER + "def unit_of(text, start, end):"),
    ("""    return None, "no class matched\"""",
     """    cls, why = literal_class(text, start, end)
    if cls:
        return cls, why
    return None, "no class matched\""""),
]


def main():
    if os.path.exists(DST):
        print("REFUSED: %s already exists - revisions go to a new filename (Q57)" % DST, file=sys.stderr)
        return 3
    src = open(SRC, encoding="utf-8").read()
    out = src
    report = []
    for i, (old, new) in enumerate(ANCHORS, 1):
        n = out.count(old)
        if n != 1:
            print("ABORT anchor %d matched %d times (needs exactly 1): %r" % (i, n, old[:60]), file=sys.stderr)
            return 4
        out = out.replace(old, new, 1)
        report.append({"anchor": i, "matched": n})
    try:
        ast.parse(out)
    except SyntaxError as exc:
        print("ABORT: derived file does not parse: %s" % exc, file=sys.stderr)
        return 5
    with open(DST, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    back = open(DST, encoding="utf-8").read()
    print(json.dumps({"source": SRC, "derived": DST, "anchors": report,
                      "src_lines": src.count("\n") + 1, "out_lines": out.count("\n") + 1,
                      "written_bytes": len(back.encode("utf-8")),
                      "readback_identical_to_memory": back == out,
                      "version_in_derived": "Q43_r7" in back,
                      "helper_present": all(k in back for k in ("literal_class", "IP_QUAD", "PID_WORDS"))},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
