"""ORD-0571 kuaizhuigong: run the commander's own language-mismatch judgment over two generations.

The judgment (side split, token counter, the four tiers) is lifted from
`_cmdr_dict_lang_mismatch_r2.py` by statement markers and pasted into one function; the only line
this file adds is the return that hands those tiers back. So the tiers below are HIS counters, not a
re-implementation.

It is still only a prediction: pass one runs it on the authoritative tip and must reproduce the
numbers printed in the order block (sentence 21, one word 4, 1237 keys per side). That calibration is
what earns pass two on my branch. The final word stays with his ruler after landing.
"""

import re
import subprocess
import sys

RULER = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_cmdr_dict_lang_mismatch_r2.py"
TREE = "D:/moodle/_qoder_kuaizhuigong_0557"
DICT = "frontend/src/i18n/LocaleContext.tsx"
TIP = "27dbf11d62d072959f3fa7308f68a7b82151ce0a"
LINE_TIP = "6f457321a3b651f193dbe96a424b876285159643"
BRANCH = "HEAD"
MY_KEYS = [
    "main.cityNexusRequestFailed", "main.cityNexusRequestRefusedHttp",
    "main.persistedOperationUpdate", "main.generalRecovery",
    "main.activateAStandingMissionOnceSubsequentCitySignalsCanLaunchRecoveryWithoutANewChatMessage",
    "main.noDominantFailureMode", "main.notEvaluated", "main.validatedActivity",
    "main.noActionableTarget", "main.outcomeEvidence", "main.explicitWins",
    "main.notReported", "main.noUpcomingActivity", "main.noActiveC4",
    "main.notAvailable", "main.verifiedFeasible", "main.notFeasible",
    "main.notPreserved", "main.verifiedEvidenceAttached", "main.evidenceUnavailable",
    "recovery.noDominantMode", "recovery.noneOnThisJourney",
]
PLACEHOLDER = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
HAN = re.compile(r"[一-鿿]")

src = open(RULER, encoding="utf-8").read().split("\n")
SPANS = [
    ("constants", "import re", '"Español"}'),
    ("line_no", "def line_no(", "return body.count"),
    ("judge", "marks = [(i, l)", "return [w for w in ALPHA.findall(v)"),
    ("counters", "zh_nocjk = ", "if CJK.search(v) and v.strip() not in SWITCHER_LABELS]"),
]

OUTER = 4  # one level: the body of the function this copy becomes
indented = []
for label, start, end in SPANS:
    a = next((i for i, l in enumerate(src) if start in l), None)
    if a is None:
        print(f"ABORT copy: span {label} start marker {start!r} not in the ruler")
        sys.exit(1)
    b = next((i for i in range(a, len(src)) if end in src[i]), None)
    if b is None:
        print(f"ABORT copy: span {label} end marker {end!r} not after line {a + 1}")
        sys.exit(1)
    print(f"SPAN {label} = ruler lines {a + 1}-{b + 1}")
    first = src[a]
    base = len(first) - len(first.lstrip(" "))
    for l in src[a:b + 1]:
        if not l.strip():
            indented.append("")
            continue
        orig = len(l) - len(l.lstrip(" "))
        indented.append(" " * (OUTER + max(orig - base, 0)) + l.lstrip(" "))

func_src = "def measure_ref(body, lines):\n" + "\n".join(indented) + (
    "\n    return {\"sides\": sides, \"zh_nocjk\": zh_nocjk, \"zh_eng\": zh_eng,"
    " \"zh_one\": zh_one, \"en_cjk\": en_cjk}\n"
)
ns = {}
exec(compile(func_src, "copied_judgment", "exec"), {"re": re}, ns)
measure_ref = ns["measure_ref"]


def read(ref):
    out = subprocess.run(["git", "-C", TREE, "show", f"{ref}:{DICT}"], capture_output=True)
    if out.returncode:
        print(f"ABORT cannot read {ref}:{DICT} rc={out.returncode}")
        sys.exit(1)
    text = out.stdout.decode("utf-8", "replace")
    return measure_ref(text, text.splitlines())


def tiers(res):
    return dict(en=len(res["sides"]["en"]), zh=len(res["sides"]["zh"]),
                no_cjk=len(res["zh_nocjk"]), zh_eng=len(res["zh_eng"]),
                zh_one=len(res["zh_one"]), en_cjk=len(res["en_cjk"]))


def report(res, label):
    t = tiers(res)
    print("%s EN_KEYS %d | ZH_KEYS %d | ZH_NO_CJK %d | ZH_ENG_SENTENCE %d | ZH_ENG_SINGLE_WORD %d | EN_CJK %d"
          % (label, t["en"], t["zh"], t["no_cjk"], t["zh_eng"], t["zh_one"], t["en_cjk"]))
    zh = res["sides"]["zh"]
    for k, v in sorted(res["zh_eng"]):
        print("  STILL_ENGLISH_SENTENCE %s | %s:%s | 值 %s" % (k, DICT, zh[k][1], v[:56]))
    for k, v in sorted(res["zh_one"]):
        print("  STILL_ENGLISH_ONE_WORD %s | %s:%s | 值 %s" % (k, DICT, zh[k][1], v[:56]))


bad = []
tip = read(TIP)
linetip = read(LINE_TIP)
br = read(BRANCH)
report(tip, "AT_BASE " + TIP[:12])
report(linetip, "AT_LINE " + LINE_TIP[:12])
report(br, "AT_BRANCH")

bt, bl, ba = tiers(tip), tiers(linetip), tiers(br)
for key, want in dict(en=1237, zh=1237, zh_eng=21, zh_one=4).items():
    if bt[key] != want:
        bad.append(f"CALIBRATION copy reads {key}={bt[key]} on the base tip, order block says {want}")
for key in ("en", "zh"):
    if ba[key] != bl[key]:
        bad.append(f"{key} key count moved {bl[key]} -> {ba[key]} vs the line; no key added or dropped")
if not ba["zh_eng"] < bl["zh_eng"]:
    bad.append(f"sentence tier did not drop against the live line: {bl['zh_eng']} -> {ba['zh_eng']}")

for k in MY_KEYS:
    zh_val, zh_line = br["sides"]["zh"][k]
    en_val = linetip["sides"]["en"][k][0]
    if not HAN.search(zh_val):
        bad.append(f"{k} still carries no Chinese character at {DICT}:{zh_line}")
    if sorted(PLACEHOLDER.findall(zh_val)) != sorted(PLACEHOLDER.findall(en_val)):
        bad.append(f"{k} placeholder drift en={en_val!r} zh={zh_val!r}")

print("rows_in_order=%d checked=%d" % (len(MY_KEYS), len(MY_KEYS)))
print("ZH_ENG_SENTENCE tip=%d branch=%d" % (bt["zh_eng"], ba["zh_eng"]))
print("ZH_ENG_SINGLE_WORD tip=%d branch=%d" % (bt["zh_one"], ba["zh_one"]))
for b in bad:
    print("REFUSED " + b)
print("VERDICT=%s" % ("PASS calibrated on the tip; branch clears the 22; placeholders intact; no key added or dropped"
                      if not bad else "ABORT"))
sys.exit(1 if bad else 0)
