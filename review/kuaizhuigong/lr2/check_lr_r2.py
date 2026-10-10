"""ORD-0557 kuaizhuigong r2: the three live keys must close the gap that is now on users' screens.

Three generations are compared, all read from git, none typed by hand:
  BEFORE = 996f1b75..., the tip before my product bytes landed; the three lines still carry literals.
  CALLS  = 2c3de134..., the authoritative line now; those three lines read t(key).
  KEYS   = this merged dict branch; both sides of the dictionary must hold the exact words.

Any mismatch exits 1 with what it actually saw.
"""

import re
import subprocess
import sys

TREE = "D:/moodle/_qoder_kuaizhuigong_0557"
BEFORE = "996f1b7588580a14fbbdec5301a6e4a7b70c93e4"
CALLS = "2c3de1342a42d671386483247775313669f31dd8"
KEYS = "HEAD"
PROD = "frontend/src/features/execution/LiveRecovery.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
ROWS = [248, 261, 269]


def show(ref, path):
    out = subprocess.run(
        ["git", "-C", TREE, "show", f"{ref}:{path}"],
        capture_output=True, check=True,
    ).stdout.decode("utf-8")
    return out.splitlines()


before_lines = show(BEFORE, PROD)
call_lines = show(CALLS, PROD)
dict_lines = show(KEYS, DICT)

failures = []
report = []

# dictionary: every key name -> list of (line, value), in file order (en block first, zh block second)
values = {}
for idx, text in enumerate(dict_lines, start=1):
    m = re.match(r'\s*"([a-zA-Z0-9_.]+)": "(.*)",\s*$', text)
    if m:
        values.setdefault(m.group(1), []).append((idx, m.group(2)))

for line_no in ROWS:
    old = before_lines[line_no - 1]
    mo = re.search(r'zh \? "(.*?)" : "(.*?)"', old)
    if not mo:
        failures.append(f"BEFORE {PROD}:{line_no} has no zh/en literal pair: {old!r}")
        continue
    old_zh, old_en = mo.group(1), mo.group(2)

    now = call_lines[line_no - 1]
    mc = re.search(r't\("([a-zA-Z0-9_.]+)"\)', now)
    if not mc:
        failures.append(f"CALLS {PROD}:{line_no} does not read a key: {now!r}")
        continue
    key = mc.group(1)

    hits = values.get(key, [])
    if len(hits) != 2:
        failures.append(f"{key}: dictionary holds {len(hits)} entries on this branch, need exactly 2 (one per side)")
        continue
    (en_line, en_value), (zh_line, zh_value) = hits
    if en_value != old_en:
        failures.append(f"{key} en side differs from what the screen printed before: dict {en_value!r} vs tip {old_en!r}")
        continue
    if zh_value != old_zh:
        failures.append(f"{key} zh side differs from what the screen printed before: dict {zh_value!r} vs tip {old_zh!r}")
        continue

    report.append(
        f"OK {key}: BEFORE {PROD}:{line_no} printed zh={old_zh!r} en={old_en!r}; "
        f"the line now reads t(\"{key}\") at CALLS {PROD}:{line_no}; "
        f"this branch holds it verbatim at {DICT}:{en_line} (en) and {DICT}:{zh_line} (zh)"
    )

# and no fourth read site of these three keys may exist that I did not cover
extra = [idx for idx, text in enumerate(call_lines, start=1)
         if re.search(r't\("live\.(tripUpdated|serverUnreachable|remindLaterOk)"\)', text)]
if sorted(extra) != sorted(ROWS):
    failures.append(f"read sites on the line are {extra}, expected {ROWS}")

print(f"rows_checked={len(ROWS)} passed={len(report)} failed={len(failures)} read_sites_on_line={len(extra)}")
for line in report:
    print(line)
for line in failures:
    print(line)

if failures or len(report) != len(ROWS):
    print("VERDICT=REFUSED")
    sys.exit(1)
print("VERDICT=PASS three bare keys on the line are closed by this branch, both languages verbatim")
