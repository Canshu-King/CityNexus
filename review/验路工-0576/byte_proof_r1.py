# -*- coding: utf-8 -*-
"""Byte proof for ORD-0576 batch one: the dictionary values must equal, character for
character, the literals this batch removed from the component on the base commit.

Exits non-zero on any mismatch, and never reports "missing" as "equal": a lookup that
returns nothing is an assertion failure, not a zero.
"""

from __future__ import annotations

import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
BASE = "0d0eca62ef8b7345bff48f6a30b1bf628e8124e0"
CANDIDATE = sys.argv[1] if len(sys.argv) > 1 else "HEAD"

COMPONENT = "frontend/src/features/execution/LiveRecovery.tsx"
DICTIONARY = "frontend/src/i18n/LocaleContext.tsx"
PAIRS = [
    ("live.inProgress", "正在进行", "In progress"),
    ("live.tripRightNow", "现在的行程", "Your trip right now"),
    ("live.whatHappened", "发生了什么", "What happened"),
]
ENTRY = re.compile(r'^\s*"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)",?\s*$')


def blob(ref, path):
    out = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (ref, path)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if out.returncode != 0:
        raise SystemExit("READ_FAIL %s:%s :: %s" % (ref, path, out.stderr.decode("utf-8", "replace")[:120]))
    return out.stdout.decode("utf-8")


def dictionary_values(ref):
    text = blob(ref, DICTIONARY)
    values = {}
    for number, line in enumerate(text.splitlines(), 1):
        m = ENTRY.match(line)
        if m:
            values.setdefault(m.group(1), []).append((number, m.group(2)))
    return values


def main() -> int:
    base_component = blob(BASE, COMPONENT)
    cand_component = blob(CANDIDATE, COMPONENT)
    values = dictionary_values(CANDIDATE)
    failures = []
    for key, zh, en in PAIRS:
        inline = '%s ? "%s" : "%s"' % ("zh", zh, en)
        if inline not in base_component:
            failures.append("%s: the base component does not contain the literal pair this batch claims to remove" % key)
        if inline in cand_component:
            failures.append("%s: the candidate still renders the inline pair" % key)
        if 't("%s")' % key not in cand_component:
            failures.append("%s: the candidate does not read the key" % key)
        rows = values.get(key, [])
        got = [value for _, value in rows]
        where = " ".join("%d:%s" % (n, v) for n, v in rows)
        if len(got) != 2:
            failures.append("%s: expected the key on both dictionary sides, found %d" % (key, len(got)))
            continue
        zh_side, en_side = got[1], got[0]
        if zh_side != zh:
            failures.append("%s zh side differs: %r != %r" % (key, zh_side, zh))
        if en_side != en:
            failures.append("%s en side differs: %r != %r" % (key, en_side, en))
    print("PROVEN" if not failures else "FAILED")
    print("keys_checked=%d keys_reading_t_in_candidate=%d"
          % (len(PAIRS), sum(1 for k, _, _ in PAIRS if 't("%s")' % k in cand_component)))
    for key, _zh, _en in PAIRS:
        print("SIDES %s -> %s" % (key, " ".join(
            "%d:%s" % (n, v) for n, v in values.get(key, []))))
    for line in failures:
        print("FAIL " + line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
