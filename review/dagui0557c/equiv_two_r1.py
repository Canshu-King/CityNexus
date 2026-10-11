import io, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = "frontend/src/features/simulation/SimulationPanel.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
TIP = io.open(os.path.join(ROOT, "review", "dagui0557c", "tip_live.txt"), encoding="utf-8").read().strip()
OUT = os.path.join(ROOT, "review", "dagui0557c", "equiv_two_r1.txt")
Q = chr(34)
rows = []


def show(ref, path):
    return subprocess.check_output(["git", "-C", ROOT, "show", "%s:%s" % (ref, path)],
                                   text=True, encoding="utf-8").split("\n")


def dict_value(text, side, key):
    i = text.index("const en: Dict")
    j = text.index("const zhCN: Dict")
    k = text.index("const dictionaries")
    import re
    chunk = text[i:j] if side == "en" else text[j:k]
    m = re.search(r'^\s*"%s":\s*"((?:[^"\\]|\\.)*)"' % re.escape(key), chunk, re.M)
    return m.group(1) if m else None


base = show(TIP, SRC)
mine = show("HEAD", SRC)
dbase = "\n".join(show(TIP, DICT))
dmine = "\n".join(show("HEAD", DICT))

pairs = [
    (839, "simulation.basis", u"依据", "Basis"),
    (845, "simulation.evidence", u"证据", "Evidence"),
]

rows.append("TIP=%s" % TIP)
rows.append("== A. the row before and after, both re-read from objects ==")
bad = 0
for n, key, zh_lit, en_lit in pairs:
    before_line = base[n - 1].strip()
    after_line = mine[n - 1].strip()
    want_before = u"<dt>{zh ? %s%s%s : %s%s%s}</dt>" % (Q, zh_lit, Q, Q, en_lit, Q)
    want_after = u"<dt>{t(%s%s%s)}</dt>" % (Q, key, Q)
    ok = (before_line == want_before and after_line == want_after
          and dict_value(dmine, "zh", key) == zh_lit
          and dict_value(dmine, "en", key) == en_lit)
    if not ok:
        bad += 1
    rows.append("%s line=%d before=%s after=%s zh_value=%s en_value=%s" % (
        "OK  " if ok else "FAIL", n, before_line[:46], after_line[:44],
        dict_value(dmine, "zh", key), dict_value(dmine, "en", key)))

rows.append("== B. whole-file counts (the shape that was being moved) ==")
cbs = Q + "? "
rows.append("inline_zh_ternary_form: tip=%d mine=%d" %
            (sum(1 for l in base if (Q + "? ") in l or ("zh ? " + Q) in l),
             sum(1 for l in mine if (Q + "? ") in l or ("zh ? " + Q) in l)))
rows.append("call_sites_simulation: tip=%d mine=%d" %
            (sum(1 for l in base if "t(" + Q + "simulation." in l),
             sum(1 for l in mine if "t(" + Q + "simulation." in l)))
rows.append("keys_in_dictionary: tip=%d mine=%d" %
            (dbase.count(Q + "simulation."), dmine.count(Q + "simulation.")))
leftover = 0
for n, key, zh_lit, en_lit in pairs:
    leftover += sum(1 for l in mine if (u"zh ? " + Q + zh_lit) in l)
rows.append("two_literals_still_inline_in_mine=%d" % leftover)

rows.append("== C. changed files against the tip ==")
rows.append(subprocess.check_output(["git", "-C", ROOT, "diff", "--name-only", TIP, "HEAD"],
                                    text=True, encoding="utf-8").strip().replace("\n", " | "))

verdict = "VERDICT=%s" % ("all_equal" if bad == 0 else "%d_MISMATCH" % bad)
rows.append(verdict)
io.open(OUT, "w", encoding="utf-8").write("\n".join(rows) + "\n")
sys.stdout.write("\n".join(rows) + "\n")
sys.exit(0 if bad == 0 else 5)
