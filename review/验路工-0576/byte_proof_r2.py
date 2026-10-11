# -*- coding: utf-8 -*-
"""Byte proof for ORD-0576 batch two: the dictionary values must equal, character for
character, the literals this batch removed from LiveRecovery on the base commit.

Exits non-zero on any mismatch. A key found on only one side, or a lookup that returns
nothing, is a failure - never a zero.
"""

from __future__ import annotations

import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
BASE = "69810d1896af51a22129e21d886f30aaae227a3c"
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
        inline = 'zh ? "%s" : "%s"' % (zh, en)
        if inline not in base_component:
            failures.append("%s: base component does not hold the pair this batch claims to remove" % key)
        if inline in cand_component:
            failures.append("%s: candidate still renders the inline pair" % key)
        if 't("%s")' % key not in cand_component:
            failures.append("%s: candidate does not read the key" % key)
        got = rows.get(key, [])
        if len(got) != 2:
            failures.append("%s: expected the key on both dictionary sides, found %d" % (key, len(got)))
            continue
        en_side, zh_side = got[0][1], got[1][1]
        if en_side != en:
            failures.append("%s en side differs: %r != %r" % (key, en_side, en))
        if zh_side != zh:
            failures.append("%s zh side differs: %r != %r" % (key, zh_side, zh))
    print("PROVEN" if not failures else "FAILED")
    print("keys_checked=%d keys_reading_t_in_candidate=%d"
          % (len(PAIRS), sum(1 for k, _, _ in PAIRS if 't("%s")' % k in cand_component)))
    for key, _zh, _en in PAIRS:
        print("SIDES %s -> %s" % (key, " ".join("%d:%s" % (n, v) for n, v in rows.get(key, []))))
    for line in failures:
        print("FAIL " + line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
