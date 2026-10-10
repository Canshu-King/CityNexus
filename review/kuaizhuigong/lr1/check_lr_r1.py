"""ORD-0557 kuaizhuigong: prove the three LiveRecovery fallbacks moved without moving a word.

Door logic: every assertion is evaluated against bytes read from git at two coordinates. If any
check fails this exits 1 and prints what it actually saw, so nothing downstream gets a green light
from a number that was not measured.
"""

import re
import subprocess
import sys

TREE = "D:/moodle/_qoder_kuaizhuigong_0557"
TIP = "996f1b7588580a14fbbdec5301a6e4a7b70c93e4"
PROD = "review/快锥工-0557-liverecovery-r1"
DICT = "review/快锥工-0557-liverecovery-dict-r1"
PROD_FILE = "frontend/src/features/execution/LiveRecovery.tsx"
DICT_FILE = "frontend/src/i18n/LocaleContext.tsx"

# tip line number, key name, the draft's own suggested english
ROWS = [
    (248, "live.tripUpdated"),
    (261, "live.serverUnreachable"),
    (269, "live.remindLaterOk"),
]


def show(ref, path):
    out = subprocess.run(
        ["git", "-C", TREE, "show", f"{ref}:{path}"],
        capture_output=True, check=True,
    ).stdout.decode("utf-8")
    return out.splitlines()


def literal_pair(line):
    m = re.search(r'zh \? "(.*?)" : "(.*?)"', line)
    if not m:
        return None
    return m.group(1), m.group(2)


def dict_value(lines, key, want_chinese):
    hits = []
    for idx, text in enumerate(lines, start=1):
        m = re.search(r'"' + re.escape(key) + r'": "(.*)",', text)
        if m:
            hits.append((idx, m.group(1)))
    if len(hits) != 2:
        print(f"FAIL {key}: expected the key on both sides, found {len(hits)} hits: {hits}")
        return None, None
    en, zh = hits[0], hits[1]
    return ("en", en[0], en[1]), ("zh", zh[0], zh[1])


tip_lines = show(TIP, PROD_FILE)
prod_lines = show(PROD, PROD_FILE)
dict_lines = show(DICT, DICT_FILE)

report = []
failures = []

for tip_line_no, key in ROWS:
    raw = tip_lines[tip_line_no - 1]
    pair = literal_pair(raw)
    if pair is None:
        failures.append(f"{PROD_FILE}:{tip_line_no} does not carry a zh/en literal pair: {raw!r}")
        continue
    tip_zh, tip_en = pair

    # the key must exist on both sides of the dictionary branch, exactly two hits
    en_site = None
    zh_site = None
    for idx, text in enumerate(dict_lines, start=1):
        m = re.search(r'"' + re.escape(key) + r'": "(.*)",', text)
        if m:
            if zh_site is None:
                zh_site = (idx, m.group(1))
            else:
                en_site = (idx, m.group(1))
    if en_site is None:
        failures.append(f"{key}: only one side found in {DICT_FILE}, need both")
        continue
    # the dictionary lists english first then chinese, so first hit is the en block
    en_pair, zh_pair = dict_value(dict_lines, key, True)
    if en_pair is None:
        failures.append(f"{key}: dictionary side could not be resolved")
        continue
    (en_tag, en_line, en_value), (zh_tag, zh_line, zh_value) = en_pair, zh_pair

    # the product branch must now read the key instead of the literal
    moved = [idx for idx, text in enumerate(prod_lines, start=1) if f't("{key}")' in text]
    if len(moved) != 1:
        failures.append(f"{key}: expected exactly one read site on {PROD}, found {moved}")
        continue
    if re.search(r'zh \? "' + re.escape(tip_zh), prod_lines[moved[0] - 1]):
        failures.append(f"{key}: the literal is still on the read line {moved[0]}")
        continue

    if en_value != tip_en:
        failures.append(f"{key} en side moved: tip printed {tip_en!r} dict holds {en_value!r}")
        continue
    if zh_value != tip_zh:
        failures.append(f"{key} zh side moved: tip printed {tip_zh!r} dict holds {zh_value!r}")
        continue

    report.append(
        f"OK {key}: tip {PROD_FILE}:{tip_line_no} carried zh={tip_zh!r} en={tip_en!r}; "
        f"dict reads them back verbatim at {DICT_FILE}:{en_line} (en) and {DICT_FILE}:{zh_line} (zh); "
        f"read site is now {PROD_FILE}:{moved[0]}"
    )

print(f"rows_in_draft={len(ROWS)} checked={len(report)} failed={len(failures)}")
for line in report:
    print(line)
for line in failures:
    print(line)

if failures or len(report) != len(ROWS):
    print("VERDICT=REFUSED")
    sys.exit(1)
print("VERDICT=PASS all three keys carry the exact words the tip printed, in both languages")
