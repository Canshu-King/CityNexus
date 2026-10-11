# -*- coding: utf-8 -*-
"""Byte proof for the three keys of ORD-0576 batch two, re-taken on a new generation.

Same shape as byte_proof_r5.py: match on the literal strings themselves (the pairs are written
across lines), require the base to hold them, the candidate to have dropped them, the key to be
read in the component, and the dictionary to carry both sides with byte-identical values.
"""

from __future__ import annotations

import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
BASE = sys.argv[2] if len(sys.argv) > 2 else "8890f22fe37af40d2919db352be47043b1ea6162"
CANDIDATE = sys.argv[1] if len(sys.argv) > 1 else "HEAD"

COMPONENT = "frontend/src/features/execution/LiveRecovery.tsx"
DICTIONARY = "frontend/src/i18n/LocaleContext.tsx"
PAIRS = [
    ("live.adjustTodayOnly", "仅调整今天", "Adjust today only"),
    ("live.remindMeLater", "稍后提醒", "Remind me later"),
    ("live.nothingToDecide", "当前没有需要你决定的调整。", "There is nothing for you to decide right now."),
]
ENTRY = re.compile(r'^\s*"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)",?\s*$')


def blob(ref, path):
    out = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (ref, path)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if out.returncode != 0:
        raise SystemExit("READ_FAIL %s:%s :: %s" % (ref, path, out.stderr.decode("utf-8", "replace")[:120]))
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
                failures.append("%s %s: base does not hold the literal this batch removes" % (key, side))
            if '"%s"' % value in cand_component:
                failures.append("%s %s: candidate still renders the inline literal" % (key, side))
        if 't("%s")' % key not in cand_component:
            failures.append("%s: candidate does not read the key" % key)
        got = rows.get(key, [])
        if len(got) != 2:
            failures.append("%s: expected the key on both dictionary sides, found %d" % (key, len(got)))
            continue
        if got[0][1] != en or got[1][1] != zh:
            failures.append("%s: dictionary values are not byte-identical: %r %r" % (key, got[0][1], got[1][1]))
        print("SIDES %s -> %d:%s %d:%s" % (key, got[0][0], got[0][1][:36], got[1][0], got[1][1][:36]))
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
