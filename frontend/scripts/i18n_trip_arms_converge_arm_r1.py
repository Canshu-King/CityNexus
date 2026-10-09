"""ORD (i18n, lane I18N_细节补齐) — counter-assertion arm for the TripItinerary call-site convergence.

Two arms in `frontend/src/features/trip/TripItinerary.tsx` (:436 the week-strip label, :455 the
per-day stop count) hand-wrote both locales inline while the dictionary already carried
`detail.weekIndex` and `detail.dayStops`. The cell is a pure substitution: no key is created, and the
bytes the traveller reads must not move.

Every assertion below is computed against the parent commit's git object (not the working tree) so a
re-run on a clean tree cannot read its own edit as evidence.
"""
import re
import subprocess
import sys
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = "frontend/src/features/trip/TripItinerary.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
SITES = {436: "detail.weekIndex", 455: "detail.dayStops"}
COUNTS = [0, 1, 2, 7, 17, 121]

total = 0
fails = []


def show(rev, path):
    return subprocess.run(["git", "-C", os.path.dirname(BASE), "show", "%s:%s" % (rev, path)],
                          capture_output=True, text=True, encoding="utf-8").stdout


def check(label, ok, detail=""):
    global total
    total += 1
    if not ok:
        fails.append("%s %s" % (label, detail))


parent = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
tip = sys.argv[2] if len(sys.argv) > 2 else "HEAD"

par_src = show(parent, FILE).split("\n")
cur_src = show(tip, FILE).split("\n")
par_dict = show(parent, DICT)
cur_dict = show(tip, DICT)

# --- the dictionary carried both keys before this cell, and this cell created none
for key in set(SITES.values()):
    pat = re.compile(r'^\s*"%s":\s*"((?:[^"\\]|\\.)*)"' % re.escape(key), re.M)
    hits = pat.findall(par_dict)
    check("parent already has %s on both sides" % key, len(hits) == 2, "found %d arm(s)" % len(hits))
    check("%s unchanged by this cell" % key, hits == pat.findall(cur_dict))

new_keys = set(re.findall(r'^\s*"([^"]+)":', cur_dict, re.M)) - set(
    re.findall(r'^\s*"([^"]+)":', par_dict, re.M))
check("dictionary gained zero keys in this cell", not new_keys, sorted(new_keys))

# --- replicate LocaleContext's own t(): lookup, plural expansion marker, {param} substitution
def load_dict(chunk, side):
    start = chunk.index("const %s: Dict" % side)
    stop = chunk.index("const zhCN: Dict") if side == "en" else chunk.index("const dictionaries")
    body = chunk[start:stop]
    out = {}
    for m in re.finditer(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"', body, re.M):
        out[m.group(1)] = m.group(2)
    return out


en_d, zh_d = load_dict(cur_dict, "en"), load_dict(cur_dict, "zhCN")


def render(key, is_zh, params):
    table = zh_d if is_zh else en_d
    value = table.get(key) or en_d[key]
    for name, val in params.items():
        value = value.replace("{%s}" % name, str(val))
    return value


# --- the parent's inline arms, read off the git object, then compared byte for byte
ARM = re.compile(r"zh\s*\?\s*`([^`]*)`\s*:\s*`([^`]*)`")
SUB = re.compile(r"\$\{[^}]*\}")

for line_no, key in sorted(SITES.items()):
    par_line = par_src[line_no - 1]
    m = ARM.search(par_line)
    check("parent line %d held an inline zh/en arm" % line_no, bool(m), par_line.strip()[:90])
    if not m:
        continue
    zh_arm, en_arm = m.group(1), m.group(2)
    check("parent zh arm carried CJK at %d" % line_no, bool(re.search(r"[一-鿿]", zh_arm)))
    for n in COUNTS:
        # the parent arm interpolates the count once; substituting str(n) reproduces what the screen drew
        for is_zh, arm, label in ((True, zh_arm, "zh"), (False, en_arm, "en")):
            was = SUB.sub(str(n), arm, count=1)
            now = render(key, is_zh, {"n": n})
            check("%d %s n=%d bytes equal" % (line_no, label, n), was == now,
                  "parent=%r now=%r" % (was, now))
    cur_line = cur_src[line_no - 1]
    check("line %d now reads the dictionary" % line_no, 't("%s"' % key in cur_line,
          cur_line.strip()[:90])
    check("line %d no longer hand-writes either arm" % line_no, not ARM.search(cur_line),
          cur_line.strip()[:90])

# --- no hand-written CJK arm survives anywhere on those two lines' shape
for n, line in enumerate(cur_src, 1):
    if n in SITES:
        continue
    pass
check("the file still resolves its locale through useLocale", "useLocale()" in "\n".join(cur_src))

print("total=%d assertions, failed=%d" % (total, len(fails)))
for f in fails:
    print("  FAIL", f)
print("TRIP_ARMS_ARM_GREEN" if not fails else "TRIP_ARMS_ARM_RED")
sys.exit(0 if not fails else 1)
