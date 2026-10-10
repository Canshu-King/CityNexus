import io, re, subprocess, sys

SRC = "frontend/src/features/simulation/SimulationPanel.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
BASE_REF = "996f1b7588580a14fbbdec5301a6e4a7b70c93e4"
OUT = []
LOG = "review/dagui2/equiv_inline_r1.txt"


def w(s):
    OUT.append(s)
    sys.stdout.write(s + "\n")


def show(ref, path):
    return subprocess.check_output(["git", "show", "%s:%s" % (ref, path)],
                                   text=True, encoding="utf-8")


def dict_value(text, side, key):
    i = text.index("const en: Dict")
    j = text.index("const zhCN: Dict")
    k = text.index("const dictionaries")
    chunk = text[i:j] if side == "en" else text[j:k]
    m = re.search(r'^\s*"%s":\s*"((?:[^"\\]|\\.)*)"' % re.escape(key), chunk, re.M)
    if not m:
        raise AssertionError("missing key %s on %s side" % (key, side))
    return m.group(1).replace('\\"', '"')


base = show(BASE_REF, SRC)
now = io.open(SRC, encoding="utf-8", newline="").read()
dict_now = io.open(DICT, encoding="utf-8", newline="").read()

cases = [
    (783, "simulation.closeStage", u"收起舞台", "Close the stage"),
    (831, "simulation.onStage", u"台上行程", "On stage"),
    (835, "simulation.sceneWindow", u"场景窗口", "Scene window"),
]

w("== A. dictionary value vs the literal that was on the line before ==")
bad = 0
for ln, key, zh_lit, en_lit in cases:
    bl = base.split("\n")[ln - 1]
    zh_ok = dict_value(dict_now, "zh", key) == zh_lit
    en_ok = dict_value(dict_now, "en", key) == en_lit
    in_base = (u'zh ? "%s" : "%s"' % (zh_lit, en_lit)) in bl
    if not (zh_ok and en_ok and in_base):
        bad += 1
        w("FAIL line=%d key=%s zh=%d en=%d base_inline_form=%d" %
          (ln, key, int(zh_ok), int(en_ok), int(in_base)))
    else:
        w("OK   line=%d key=%s zh=%s en=%s" % (ln, key, zh_lit, en_lit))

w("== B. call sites and leftovers ==")
for ln, key, zh_lit, en_lit in cases:
    now_line = now.split("\n")[ln - 1]
    w("line=%d now=%s calls=%d leftover=%d" %
      (ln, now_line.strip()[:60], now.count('t("%s")' % key),
       now.count(u'zh ? "%s" : "%s"' % (zh_lit, en_lit))))
call_bad = [k for _, k, _, _ in cases if now.count('t("%s")' % k) != 1]
left_bad = [k for _, k, z, e in cases if now.count(u'zh ? "%s" : "%s"' % (z, e)) != 0]
w("call_missing=%d leftover_present=%d" % (len(call_bad), len(left_bad)))

w("== C. neighbours that must not have moved ==")
w("other_arms_still_inline_base=%d now=%d" %
  (len(re.findall(r'zh \? "', base)), len(re.findall(r'zh \? "', now))))
w("files_touched_vs_base=%s" % subprocess.check_output(
    ["git", "diff", "--name-only", BASE_REF, "--", "frontend/src"],
    text=True, encoding="utf-8").split())

if bad or call_bad or left_bad:
    io.open(LOG, "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    sys.exit(5)
io.open(LOG, "w", encoding="utf-8").write("\n".join(OUT) + "\n")
w("VERDICT all_equal")
