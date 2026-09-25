"""Build o290_derive_r3.py from r2 and run it, then run the arbiter's gate on the result.

Only thing ORD-0294 (c) still owed: B2c's PRIMARY control arm must be a tree that has no B2a
idle-convergence in it, at the same user_navs=0 shape.  r2 kept 69fd2f85 (which does converge)
as the primary and added the baseline as a second control, so the pairing was not what the
ruling asks for.  r3 swaps them: baseline 45b0a5e2 becomes the control, and 69fd2f85 - the
tree that converges by cutting the write - is cited as the named secondary control, because it
is the only arm that shows the hazard itself.

`derived_from` is deliberately NOT added: in this ruler it is the exemption channel for shared
sentences, and my sentences are distinct (verified by the gate).  A decorative pointer would
risk exactly the FAKE_OR_INEFFECTIVE finding it is meant to avoid.
"""
import io
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
s = io.open(os.path.join(LANE, "o290_derive_r2.py"), encoding="utf-8").read()


def sub(old, new, count=1):
    global s
    assert s.count(old) == count, ("anchor", old[:60], s.count(old))
    s = s.replace(old, new)


sub('         "B2c_inflight_write_safe_point": ("b2c_restored", "b2c_notrestored")}',
    '         "B2c_inflight_write_safe_point": ("b2c_restored", "b2c_noconvergence")}')
sub('EXTRA_CONTROLS = {"B2c_inflight_write_safe_point": ["b2c_noconvergence"]}',
    'EXTRA_CONTROLS = {"B2c_inflight_write_safe_point": ["b2c_notrestored"]}')
sub('out = {"order": "ORD-0290", "revision": "r2", "verifier"',
    'out = {"order": "ORD-0290", "revision": "r3", "verifier"')
sub('os.path.join(LANE, "o290_derived_r2.json")', 'os.path.join(LANE, "o290_derived_r3.json")')

start = s.index('    else:\n        good = (not pos["reload_cut_the_write"]')
end = s.index("    if not good:")
s = s[:start] + io.open(os.path.join(LANE, "_r3_b2c_branch.py.txt"), encoding="utf-8").read() + s[end:]

io.open(os.path.join(LANE, "o290_derive_r3.py"), "w", encoding="utf-8", newline="").write(s)
import ast
ast.parse(s)
print("o290_derive_r3.py written; r1/r2 untouched:",
      all(os.path.exists(os.path.join(LANE, f)) for f in
          ("o290_derive.py", "o290_derived.json", "o290_derive_r2.py", "o290_derived_r2.json")))
