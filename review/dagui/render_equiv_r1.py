import io, os, re, subprocess, sys

SRC = "frontend/src/features/simulation/SimulationPanel.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
LABELS = "frontend/src/i18n/travelerLabels.ts"
BASE_REF = os.environ.get("DAGUI_BASE_REF", "d435cff26d")
OUT = []


def w(line):
    OUT.append(line)
    sys.stdout.write(line + "\n")


def show(path):
    return subprocess.check_output(
        ["git", "show", "%s:%s" % (BASE_REF, path)], text=True, encoding="utf-8"
    )


def dict_value(text, side, key):
    i = text.index("const en: Dict")
    j = text.index("const zhCN: Dict")
    k = text.index("const dictionaries")
    chunk = text[i:j] if side == "en" else text[j:k]
    m = re.search(r'^\s*"%s":\s*"((?:[^"\\]|\\.)*)"' % re.escape(key), chunk, re.M)
    if not m:
        raise AssertionError("key not found %s %s" % (side, key))
    return m.group(1).replace('\\"', '"').replace("\\\\", "\\")


N = "${bookableRead.data.unreadable}"
LISTED = "${listed.length}"
OPEN = "${open.length}"
ID = "${shortId(open[0].id)}"
STATE = "${fixture.state}"
RZH = "${row.blocked.zh}"
REN = "${row.blocked.en}"

K1 = "simulation.readsDidNotAnswerWhichIsNotTheSameAsNoSlot"
K2 = "simulation.theServerAnsweredWithProposalsStillOpenAcceptTheProposalBelowNowPointsAtAcceptingIsWhatChangesThePlan"
K3 = "simulation.theServerProducedProposalsButNoneOfTheItNowListsIsOpenSoAcceptTheProposalWillRefuseAndSayWhyOnItsOwnLine"
K4 = "simulation.now"
K5 = "simulation.thisActionIsUnavailableRightNow"
K6 = "simulation.thePreviousActionHasNotReturnedYet"

# (dict side, key, param->source-expression map, the exact literal that was on the line before)
cases = [
    ("zh", K1, {"n": N}, u'（另有 %s 次没读到，那不是"没有时段"）' % N),
    ("en", K1, {"n": N}, u' (%s reads did not answer, which is not the same as "no slot")' % N),
    ("zh", K2, {"listed": LISTED, "open": OPEN, "id": ID},
     u'服务器回了 %s 份方案，其中 %s 份还开着；下面「接受方案」那一行现在拿的是 %s。接受才会换计划。' % (LISTED, OPEN, ID)),
    ("zh", K3, {"listed": LISTED},
     u'服务器回了方案，但它现在列出的 %s 份里没有还开着的那一份，所以「接受方案」这一行会说不给按——理由在它自己那行。' % LISTED),
    ("en", K2, {"listed": LISTED, "open": OPEN, "id": ID},
     u'The server answered with %s proposals, %s still open; "Accept the proposal" below now points at %s. Accepting is what changes the plan.' % (LISTED, OPEN, ID)),
    ("en", K3, {"listed": LISTED},
     u'The server produced proposals, but none of the %s it now lists is open, so "Accept the proposal" will refuse and say why on its own line.' % LISTED),
    ("zh", K4, {"state": STATE}, u'（现值 %s）' % STATE),
    ("en", K4, {"state": STATE}, u' (now %s)' % STATE),
    ("zh", K5, {"reason": RZH}, u'这个动作现在做不了：%s' % RZH),
    ("zh", K6, {}, u'上一个动作还没回来，先等它。'),
    ("en", K5, {"reason": REN}, u'This action is unavailable right now: %s' % REN),
    ("en", K6, {}, u'The previous action has not returned yet.'),
]

base_src = show(SRC)
now_src = io.open(SRC, encoding="utf-8").read()
now_dict = io.open(DICT, encoding="utf-8").read()

# the two English arms that share K4 with :702 / :718
w("== A. twelve table rows plus two shared english arms: rebuild and byte-compare ==")
mismatch = 0
for side, key, params, expected in cases:
    tmpl = dict_value(now_dict, side, key)
    for name, expr in params.items():
        tmpl = re.sub(r"\{%s\}" % re.escape(name), lambda _m, e=expr: e, tmpl)
    ok = tmpl == expected
    present_in_base = base_src.count(expected)
    if not ok or present_in_base < 1:
        mismatch += 1
        w("FAIL side=%s key=%s rebuilt=%s base_hits=%d" % (side, key, tmpl[:50], present_in_base))
    else:
        w("OK   side=%s key=%s base_hits=%d" % (side, key, present_in_base))

# :701/:717 zh and :702/:718 en use K4 twice each; count the arms actually wired
w("== B. call sites now go through t(), hardcoded literals are gone ==")
for key in (K1, K2, K3, K4, K5, K6):
    w("calls key=%s count=%d" % (key, now_src.count('t("%s"' % key)))
expected_calls = {K1: 2, K2: 2, K3: 2, K4: 4, K5: 2, K6: 2}
bad = [k for k in expected_calls if now_src.count('t("%s"' % k) != expected_calls[k]]
w("call_shape_mismatch=%d" % len(bad))

# the twelve literals must no longer sit inline in the product file
leftover = 0
for side, key, params, expected in cases:
    if expected in now_src:
        leftover += 1
        w("LEFTOVER still inline: %s" % expected[:40])
w("leftover_inline_literals=%d" % leftover)

w("== C. the nine hardcoded UNKNOWN reads now resolve through the existing key ==")
labels = io.open(LABELS, encoding="utf-8").read()
zh_val = re.search(r'^\s*UNKNOWN: \{ zh: "([^"]*)", en: "([^"]*)" \},\s*$',
                   labels.split("const CATEGORY_LABELS")[1].split("};")[0], re.M)
w("existing_key_value_zh=%s en=%s" % (zh_val.group(1), zh_val.group(2)))
w("unknown_reads_count=%d" % now_src.count('?? categoryLabel("UNKNOWN", zh)'))
w("unknown_hardcoded_left=%d" % now_src.count(u'?? "未知"'))
w("base_unknown_hardcoded=%d" % base_src.count(u'?? "未知"'))
w("english_arm_smallcase_unknown_now=%d base=%d"
  % (now_src.count('?? "unknown"'), base_src.count('?? "unknown"')))

w("== D. untouched neighbours (negative controls) ==")
w("different_sentence_at_875_survives=%d" % now_src.count(u'zh: "上一个动作还没回来。",'))
w("base_has_that_sentence=%d" % base_src.count(u'zh: "上一个动作还没回来。",'))
w("product_files_touched_vs_base=%s"
  % subprocess.check_output(
      ["git", "diff", "--name-only", BASE_REF, "--", "frontend/src"],
      text=True, encoding="utf-8").split())

if mismatch or bad or leftover:
    sys.exit(5)
with io.open("review/dagui/render_equiv_r1.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(OUT) + "\n")
w("VERDICT all_equal")
