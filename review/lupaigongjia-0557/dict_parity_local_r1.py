# -*- coding: utf-8 -*-
"""路牌工甲: the dictionary two-sided parity check, run against a file on disk.

Same judgment as the commander's `_cmdr_dict_parity_tip_r1.py` (which is pinned to the live
ref and cannot be pointed at a candidate branch), applied to a working-tree file so a lane can
check its own bytes before asking for a landing. It aborts when the two dictionary halves cannot
be found - "did not count" is never reported as "no defect".
"""

from __future__ import print_function

import re
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "frontend/src/i18n/LocaleContext.tsx"
KEY = re.compile(r'^\s*"([a-z][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+)+)"\s*:')
BOUND = re.compile(r'^\s*(?:const|export const)\s+\w*(en|zh|zhCN|cn)\w*\s*[:=]')

lines = open(PATH, encoding="utf-8").read().splitlines()
bounds = [(i + 1, m.group(1)) for i, line in enumerate(lines) for m in [BOUND.match(line)] if m]
if len(bounds) != 2:
    print("ABORT BOUNDS %d -- 读不出两块字典边界，不据此说「没有缺陷」" % len(bounds))
    sys.exit(3)

first, second = bounds[0][0], bounds[1][0]
en_keys = {}
zh_keys = {}
for i, line in enumerate(lines, 1):
    m = KEY.match(line)
    if not m:
        continue
    if first <= i < second:
        en_keys.setdefault(m.group(1), []).append(i)
    elif i >= second:
        zh_keys.setdefault(m.group(1), []).append(i)

both = sorted(set(en_keys) & set(zh_keys))
once = sorted(set(en_keys) ^ set(zh_keys))
multi = sorted(k for k, v in list(en_keys.items()) + list(zh_keys.items()) if len(v) > 1)

print("FILE %s lines=%d" % (PATH, len(lines)))
print("BOUNDS 2 en:%d,zh:%d" % (first, second))
print("KEYS_TOTAL %d" % len(set(en_keys) | set(zh_keys)))
print("KEYS_BOTH %d" % len(both))
print("KEYS_ONE_SIDED %d" % len(once))
for k in once[:10]:
    print("ONE_SIDED %s" % k)
print("KEYS_MULTI %d" % len(multi))
for k in multi[:10]:
    print("MULTI %s at %s" % (k, (en_keys.get(k, []) + zh_keys.get(k, []))[:4]))

probe = sys.argv[2] if len(sys.argv) > 2 else None
if probe:
    print("PROBE %s en=%s zh=%s" % (probe, en_keys.get(probe, []), zh_keys.get(probe, [])))
