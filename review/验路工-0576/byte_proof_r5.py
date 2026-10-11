# -*- coding: utf-8 -*-
"""Byte proof for ORD-0576 batch r3: dictionary values must equal, character for character,
the literals this batch removed from LiveRecovery, and the pair must be gone from the component.

The pairs here are written across several lines in the source, so the proof matches on the
literal strings themselves rather than on one-line `zh ? "…" : "…"` text.
Exits non-zero on any mismatch; a key on only one side, or a lookup returning nothing, is a
failure - never a zero.
"""

from __future__ import annotations

import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
BASE = sys.argv[2] if len(sys.argv) > 2 else "dde393326935dce66c7e7bd88cdab69af3e53985"
CANDIDATE = sys.argv[1] if len(sys.argv) > 1 else "HEAD"

COMPONENT = "frontend/src/features/execution/LiveRecovery.tsx"
DICTIONARY = "frontend/src/i18n/LocaleContext.tsx"
PAIRS = [
    ("live.acknowledgedStillOpen",
     "已知晓，仍待处理：你已经看过这些变化，但还没有选定新的安排。",
     "Seen, still open: you have seen these changes but have not chosen a new arrangement yet."),
    ("live.confirmedUnchanged",
     "已确认的预订和到达/离开时间保持不变。",
     "Confirmed bookings and your arrival/departure stay unchanged."),
    ("live.confirmedAffected",
     "注意：部分已确认内容会受影响。",
     "Note: some confirmed items are affected."),
]
ENTRY = re.compile(r'^\s*"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)",?\s*$')


def blob(ref, path):
    out = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (ref, path)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if out.returncode != 0:
        raise SystemExit("READ_FAIL %s:%s :: %s"
                         % (ref, path, out.stderr.decode("utf-8", "replace")[:120]))
    return out.stdout.decode("utf-8")


def dictionary_rows(ref):
    found = {}
    for number, line in enumerate(blob(ref, DICTIONARY).splitlines(), 1):
        m = ENTRY.match(line)
        if m:
            found.setdefault(m.group(1), []).append((number, m.group(2)))
    return found


def main() -> int:
    base_component = blob(BASE, COMPONENT)
    cand_component = blob(CANDIDATE, COMPONENT)
    rows = dictionary_rows(CANDIDATE)
    failures = []
    for key, zh, en in PAIRS:
        for side, value in (("zh", zh), ("en", en)):
            if '"%s"' % value not in base_component:
                failures.append("%s %s: the base component does not hold the literal this batch claims to remove" % (key, side))
            if '"%s"' % value in cand_component:
                failures.append("%s %s: the candidate still renders the inline literal" % (key, side))
        if 't("%s")' % key not in cand_component:
            failures.append("%s: the candidate does not read the key" % key)
        got = rows.get(key, [])
        if len(got) != 2:
            failures.append("%s: expected the key on both dictionary sides, found %d" % (key, len(got)))
            continue
        en_side, zh_side = got[0][1], got[1][1]
        if en_side != en:
            failures.append("%s en side differs: %r != %r" % (key, en_side, en))
        if zh_side != zh:
            failures.append("%s zh side differs: %r != %r" % (key, zh_side, zh))
        print("SIDES %s -> %d:%s %d:%s" % (key, got[0][0], got[0][1][:40], got[1][0], got[1][1][:40]))
    for f in failures:
        print("FAIL %s" % f)
    print("keys_checked=%d keys_reading_t_in_candidate=%d"
          % (len(PAIRS), sum(1 for k, _, _ in PAIRS if 't("%s")' % k in cand_component)))
    if failures:
        print("FAILED")
        return 1
    print("PROVEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
