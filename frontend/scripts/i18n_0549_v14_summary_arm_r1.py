"""ORD-0549 (lane i18n / 补齐细节页词典键) — counter-assertion arm for V14RecoveryTruthPanel:192.

The fold's summary hand-wrote both locale arms while the dictionary already carried
`hub.continuationTechnicalDetail` on both sides. This cell is a read-path substitution only: no key
is created or edited, and the bytes on screen must not move.

Assertions are computed against the parent commit's git object (`git show <父>:…`), never the working
tree, so a re-run on a clean tree cannot read its own edit as evidence.

Usage: python i18n_0549_v14_summary_arm_r1.py <parent-sha> <candidate-sha>
"""
import re
import subprocess
import sys
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PANEL = "frontend/src/features/recovery/V14RecoveryTruthPanel.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
LINE = 192
KEY = "hub.continuationTechnicalDetail"
TESTID = "v14-recovery-technical-toggle"

total = 0
fails = []


def show(rev, path):
    r = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, path)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, "cannot read %s:%s" % (rev, path)
    return r.stdout


def check(label, ok, detail=""):
    global total
    total += 1
    if not ok:
        fails.append("%s  %s" % (label, detail))


if len(sys.argv) < 3:
    print("need <parent-sha> <candidate-sha>")
    sys.exit(2)
parent, cand = sys.argv[1], sys.argv[2]

par = show(parent, PANEL).split("\n")
cur = show(cand, PANEL).split("\n")
par_dict = show(parent, DICT)
cur_dict = show(cand, DICT)

# --- before: the cited line really did hand-write both arms (so the control is not vacuous)
ARM = re.compile(r'zh\s*\?\s*"([^"]*)"\s*:\s*"([^"]*)"')
m = ARM.search(par[LINE - 1])
check("parent line %d held an inline zh/en arm" % LINE, bool(m), par[LINE - 1].strip()[:100])
if m:
    par_zh, par_en = m.group(1), m.group(2)
    check("parent zh arm carried CJK", bool(re.search(r"[一-鿿]", par_zh)), repr(par_zh))
else:
    par_zh = par_en = None

# --- the dictionary carried this key on both sides BEFORE this cell, and the cell created nothing
def arms_of(chunk, key):
    out = []
    for side in ("en", "zhCN"):
        start = chunk.index("const %s: Dict" % side)
        stop = chunk.index("const zhCN: Dict") if side == "en" else chunk.index("const dictionaries")
        mm = re.search(r'^\s*"%s":\s*"((?:[^"\\]|\\.)*)"' % re.escape(key),
                       chunk[start:stop], re.M)
        out.append(mm.group(1) if mm else None)
    return out[1], out[0]  # (zh, en)


par_zh_key, par_en_key = arms_of(par_dict, KEY)
cur_zh_key, cur_en_key = arms_of(cur_dict, KEY)
check("key %s existed on both sides in the parent" % KEY,
      bool(par_zh_key) and bool(par_en_key), repr((par_zh_key, par_en_key)))
check("this cell did not edit the key's arms",
      (par_zh_key, par_en_key) == (cur_zh_key, cur_en_key))

new_keys = set(re.findall(r'^\s*"([^"]+)":', cur_dict, re.M)) - set(
    re.findall(r'^\s"([^"]+)":', cur_dict, re.M))
new_keys = {k for k in re.findall(r'^\s*"([^"]+)":', cur_dict, re.M)
             if not re.search(r'^\s*"%s":' % re.escape(k), par_dict, re.M)}
check("dictionary gained zero keys in this cell", not new_keys, sorted(new_keys))
check("dictionary lost zero keys in this cell",
      len(re.findall(r'^\s*"[^"]+":', cur_dict, re.M)) ==
      len(re.findall(r'^\s*"[^"]+":', par_dict, re.M)))

# --- screen bytes: the key's own two arms equal exactly what the line used to hand-write
if m:
    check("zh bytes unchanged", cur_zh_key == par_zh, "parent=%r key=%r" % (par_zh, cur_zh_key))
    check("en bytes unchanged", cur_en_key == par_en, "parent=%r key=%r" % (par_en, cur_en_key))

# --- after: the cited line reads the key and no longer hand-writes either arm
check("line %d now reads the named key" % LINE, 't("%s")' % KEY in cur[LINE - 1],
      cur[LINE - 1].strip()[:100])
check("line %d no longer contains 'zh ?'" % LINE, "zh ?" not in cur[LINE - 1],
      cur[LINE - 1].strip()[:100])
check("the screen's 'zh ?' count went to zero",
      sum(1 for l in cur if "zh ?" in l) == 0,
      "now %d" % sum(1 for l in cur if "zh ?" in l))

# --- the fold's own anchors and structure survive (Q70: one element per contract field)
check("summary testid still present once",
      sum(1 for l in cur if TESTID in l) == sum(1 for l in par if TESTID in l))
check("details fold still present",
      'data-testid="v14-recovery-technical"' in "\n".join(cur))
check("the locale flag is still wired to the measured-facts child",
      "zh={zh}" in "\n".join(cur))
check("t is in scope on this screen", "const t = useT();" in "\n".join(cur))

print("total=%d assertions, failed=%d" % (total, len(fails)))
for f in fails:
    print("  FAIL", f)
print("V14_SUMMARY_ARM_GREEN" if not fails else "V14_SUMMARY_ARM_RED")
sys.exit(0 if not fails else 1)
