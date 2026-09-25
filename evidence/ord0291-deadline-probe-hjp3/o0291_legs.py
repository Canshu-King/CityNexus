"""ORD-0291 (3): name the legs the constant does NOT reach, from the authoritative tree's own bytes.

Search space, declared (R-SCHEMA-02): every .ts/.tsx file under <tree>/frontend/src, pattern `fetch(`;
a call site is read together with the 7 lines that follow it, because the init object is what carries the
method.  Coverage: NOT EXHAUSTIVE - a request made through a helper whose body is not matched by this
pattern, or a method built from a variable, is invisible to it.  Two-way self-test at the bottom: the same
regex must match the deadline sentence and must NOT match the progress counter, so a "no card" reading here
cannot be a matcher that simply never fires.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

TREE = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'D:/moodle/_qoder_wt_45b0a5e')
SRC = TREE / 'frontend' / 'src'
OUT = pathlib.Path('D:/moodle/_hjp3_0291_0925/legs_out_of_range.json')

files = sorted(p for p in SRC.rglob('*') if p.suffix in ('.ts', '.tsx') and p.is_file())
sites = []
for p in files:
    lines = p.read_text(encoding='utf-8', errors='replace').splitlines()
    for i, line in enumerate(lines):
        for m in re.finditer(r'\bfetch\(', line):
            window = ' '.join(lines[i:i + 8])
            mm = re.search(r'method:\s*[`"\']([A-Za-z]+)[`"\']', window)
            method = mm.group(1).upper() if mm else ('GET' if 'method:' not in window else 'VARIABLE')
            sites.append({
                'file': str(p.relative_to(TREE)).replace('\\', '/'), 'line': i + 1,
                'col': m.start() + 1, 'method': method,
                'is_write': method not in ('GET', 'HEAD'),
                'carries_signal': bool(re.search(r'signal[:,)]|signal\b', window)),
                'carries_timer': bool(re.search(r'setTimeout|AbortSignal\.timeout|deadline', window, re.I)),
                'through_deadline_wrapper': bool(re.search(r'fetchWithReadDeadline', window)),
                'idempotency_key_header': bool(re.search(r'Idempotency-Key', window)),
            })

wrapper_calls = []
for p in files:
    txt = p.read_text(encoding='utf-8', errors='replace')
    for m in re.finditer(r'fetchWithReadDeadline\(', txt):
        line_no = txt[:m.start()].count('\n') + 1
        window = ' '.join(txt.splitlines()[line_no - 1:line_no + 7])
        mm = re.search(r'method:\s*[`"\']([A-Za-z]+)[`"\']', window)
        wrapper_calls.append({'file': str(p.relative_to(TREE)).replace('\\', '/'), 'line': line_no,
                              'method': mm.group(1).upper() if mm else 'DEFAULT(GET)'})

writes = [s for s in sites if s['is_write']]
report = {
    'tree': str(TREE), 'search_space': '<tree>/frontend/src/**/*.ts,tsx, pattern \\bfetch\\(',
    'files_scanned': len(files), 'fetch_call_sites': len(sites),
    'write_call_sites': len(writes),
    'write_sites_with_signal': sum(1 for s in writes if s['carries_signal']),
    'write_sites_with_timer': sum(1 for s in writes if s['carries_timer']),
    'write_sites_named': writes,
    'fetchWithReadDeadline_call_sites': wrapper_calls,
    'wrapper_definition': None,
    'coverage': 'NOT EXHAUSTIVE - a write issued through a helper that does not literally call `fetch(`, '
                'or a method taken from a variable, is not seen by this scan',
}
rd = SRC / 'lib' / 'readDeadline.ts'
if rd.exists():
    txt = rd.read_text(encoding='utf-8')
    gate = [i + 1 for i, l in enumerate(txt.splitlines()) if 'method !== "GET"' in l]
    const = [i + 1 for i, l in enumerate(txt.splitlines()) if 'READ_DEADLINE_MS =' in l]
    report['wrapper_definition'] = {'file': 'frontend/src/lib/readDeadline.ts',
                                    'constant_lines': const, 'method_gate_lines': gate,
                                    'constant_text': [l for l in txt.splitlines() if 'READ_DEADLINE_MS =' in l]}

# two-way self-test of the deadline matcher used by the browser instrument
DEADLINE = '等了 12 秒，这台服务器一个字也没回答'
COUNTER = '发出请求，等待模型返回 · 已等待 31 秒'
RX = re.compile(r'等了\s*\d+\s*秒|No answer from this server in')
report['regex_selftest'] = {
    'matches_deadline_sentence': bool(RX.search(DEADLINE)),
    'matches_progress_counter': bool(RX.search(COUNTER)),
    'verdict': 'SELFTEST_OK' if (RX.search(DEADLINE) and not RX.search(COUNTER)) else 'SELFTEST_BROKEN',
}
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'write_sites_named'}, ensure_ascii=False, indent=1))
