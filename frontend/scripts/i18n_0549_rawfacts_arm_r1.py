"""ORD-0549 (lane i18n / 补齐细节页词典键) — counter-assertion arm for RawFactsPanel's label.

The component hand-wrote both locale arms for its heading while the dictionary already carried
`detail.rawFactsHeading` on both sides. The cell is a read-path substitution plus the one hook line
the component needed; no key is created or edited, and the bytes on screen must not move.

The cited line shifts when the import and the hook are added, so nothing here pins an absolute line
number: the parent's arm is found by content, and the candidate's call is found by the key name.

Usage: python i18n_0549_rawfacts_arm_r1.py <parent-sha> <candidate-sha>
"""
import re
import subprocess
import sys
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PANEL = "frontend/src/components/RawFactsPanel.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
KEY = "detail.rawFactsHeading"
ZH_TEXT = "这台设备自己量到的回读字段"
EN_TEXT = "Fields this device measured"
TESTID = "cnx-raw-facts-label"

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

par = show(parent, PANEL)
cur = show(cand, PANEL)
par_dict = show(parent, DICT)
cur_dict = show(cand, DICT)

# --- parent really hand-wrote this exact pair (content-found, not line-pinned)
ARM = re.compile(r'zh\s*\?\s*"([^"]*)"\s*:\s*"([^"]*)"')
par_arms = [m.groups() for m in ARM.finditer(par) if ZH_TEXT in m.group(1)]
check("parent hand-wrote this heading in both arms", len(par_arms) == 1, par_arms)
check("parent's two arms are the strings the order names",
      par_arms and par_arms[0] == (ZH_TEXT, EN_TEXT), par_arms[:1])

# --- dictionary carried the key before, and this cell neither added nor changed anything
def arms_of(chunk, key):
    out = {}
    for side in ("en", "zhCN"):
        start = chunk.index("const %s: Dict" % side)
        stop = chunk.index("const zhCN: Dict") if side == "en" else chunk.index("const dictionaries")
        mm = re.search(r'^\s*"%s":\s*"((?:[^"\\]|\\.)*)"' % re.escape(key),
                       chunk[start:stop], re.M)
        out[side] = mm.group(1) if mm else None
    return out


pk, ck = arms_of(par_dict, KEY), arms_of(cur_dict, KEY)
check("key existed on both sides in the parent", bool(pk["en"]) and bool(pk["zhCN"]), pk)
check("this cell did not edit the key", pk == ck, "%s -> %s" % (pk, ck))
par_keys = set(re.findall(r'^\s*"([^"]+)":', par_dict, re.M))
cur_keys = set(re.findall(r'^\s*"([^"]+)":', cur_dict, re.M))
check("dictionary gained zero keys", not (cur_keys - par_keys), sorted(cur_keys - par_keys))
check("dictionary lost zero keys", not (par_keys - cur_keys), sorted(par_keys - cur_keys))

# --- bytes on screen do not move
check("zh arm equals what the component used to write", ck["zhCN"] == ZH_TEXT, repr(ck["zhCN"]))
check("en arm equals what the component used to write", ck["en"] == EN_TEXT, repr(ck["en"]))

# --- after: reads the key, hand-writes nothing
check("candidate calls the key", 't("%s")' % KEY in cur)
check("candidate has no 'zh ?' left on this heading",
      not any(ZH_TEXT in a for a, b in [m.groups() for m in ARM.finditer(cur)]))
check("candidate's file-wide 'zh ?' count is zero", "zh ?" not in cur,
      [l.strip()[:80] for l in cur.split("\n") if "zh ?" in l])

# --- the hook is wired the way the rest of the tree wires it, and the locale flag survives
check("useT imported from the shared context",
      bool(re.search(r'import \{[^}]*useT[^}]*\} from "\.\./i18n/LocaleContext"', cur)))
check("useT called inside the component", "const t = useT();" in cur)
check("the zh prop is still declared and still consumed",
      cur.count("zh: boolean") == 1 and re.search(r"receiptLabel\(facts\.receipt\.present, zh\)", cur),
      "signature or call-site churn would mean this lane touched someone else's radius")
check("the component's exported name is unchanged",
      "export function RawFactsPanel(" in cur)

# --- the anchors the landed gates read must not move
check("label testid preserved",
      cur.count(TESTID) == par.count(TESTID) and cur.count(TESTID) >= 1,
      "%d vs %d" % (cur.count(TESTID), par.count(TESTID)))

# --- ORD-0533's judgment on this file: every key it calls resolves on both sides
called = set(re.findall(r'\bt\("([^"]+)"\)', cur))
en_set = set(re.findall(r'^\s*"([^"]+)":',
                        cur_dict[cur_dict.index("const en: Dict"):cur_dict.index("const zhCN: Dict")], re.M))
zh_set = set(re.findall(r'^\s*"([^"]+)":',
                        cur_dict[cur_dict.index("const zhCN: Dict"):cur_dict.index("const dictionaries")], re.M))
unresolved = sorted(k for k in called if k not in en_set or k not in zh_set)
check("every key this file calls exists on both sides", not unresolved, unresolved)
print("  file calls %d distinct keys, all resolving on both sides" % len(called))

print("total=%d assertions, failed=%d" % (total, len(fails)))
for f in fails:
    print("  FAIL", f)
print("RAWFACTS_ARM_GREEN" if not fails else "RAWFACTS_ARM_RED")
sys.exit(0 if not fails else 1)
