import io, re, sys, json

PROD = r"D:/moodle/_qoder_pinggong_0557/frontend/src/main.tsx"
DICT = r"D:/moodle/_qoder_pinggong_0557_dict/frontend/src/i18n/LocaleContext.tsx"
OUT = r"D:/moodle/_qoder_pinggong_0557/review/pinggong-0557/i18n_gate_r1.txt"

# blessed table: line-in-tip -> (key, the literal that was on screen before)
TABLE = [
    (170, "main.cityNexusRequestFailed", "CityNexus request failed"),
    (171, "main.cityNexusRequestRefusedHttp", "CityNexus request refused (HTTP {status})"),
    (566, "main.persistedOperationUpdate", "Persisted operation update"),
    (1111, "main.generalRecovery", "general recovery"),
    (1154, "main.activateAStandingMissionOnceSubsequentCitySignalsCanLaunchRecoveryWithoutANewChatMessage",
     "Activate a standing mission once; subsequent city signals can launch recovery without a new chat message."),
    (1218, "main.noDominantFailureMode", "No dominant failure mode"),
    (1415, "main.notEvaluated", "not evaluated"),
    (1423, "main.validatedActivity", "validated Activity"),
    (1424, "main.noActionableTarget", "no actionable target"),
    (1475, "main.outcomeEvidence", "outcome evidence"),
    (1487, "main.explicitWins", "explicit wins"),
    (1545, "main.notReported", "not reported"),
    (1547, "main.noUpcomingActivity", "no upcoming activity"),
    (1551, "main.noActiveC4", "No active C4"),
    (1560, "main.notAvailable", "not available"),
    (1595, "main.unnamedCommitmentServerGaveNoName", "未命名承诺 · 服务器没给名字"),
    (1646, "main.verifiedFeasible", "verified feasible"),
    (1646, "main.notFeasible", "not feasible"),
    (1680, "main.notPreserved", "not preserved"),
    (1682, "main.verifiedEvidenceAttached", "verified evidence attached"),
    (1683, "main.evidenceUnavailable", "evidence unavailable"),
]

dl = io.open(DICT, encoding="utf-8").read().split("\n")


def block(start_marker):
    i = next(k for k, s in enumerate(dl) if s.startswith(start_marker))
    j = next(k for k, s in enumerate(dl[i + 1:], i + 1) if s == "};")
    out = {}
    for s in dl[i + 1:j]:
        m = re.match(r'^  "(.+?)": "(.*)",$', s)
        if m:
            out[m.group(1)] = m.group(2).replace('\\"', '"')
    return out, i + 1, j


en, en_from, en_to = block("const en: Dict = {")
zh, zh_from, zh_to = block("const zhCN: Dict = {")

prod = io.open(PROD, encoding="utf-8").read()
called = set(re.findall(r't\("(main\.[A-Za-z0-9]+)"', prod))


def resolve(key, locale_dict):
    # mirrors LocaleContext.tsx:2538-2548: locale dict, else en, else the key itself
    return locale_dict.get(key) or en.get(key) or key


def render(value, params):
    for k, v in params.items():
        value = value.replace("{%s}" % k, str(v))
    return value


L = ["# i18n equivalent gate for ORD-0557 main.tsx (judgement mirrors LocaleContext.tsx:2538)"]
L.append("en_block_keys=%d zh_block_keys=%d main_keys_called=%d" % (len(en), len(zh), len(called)))
L.append("en object spans LocaleContext.tsx:%d..%d, zh object spans LocaleContext.tsx:%d..%d" % (
    en_from, en_to, zh_from, zh_to))
bad = 0
pending = 0
rows = []
for line, key, old in TABLE:
    params = {"status": 503} if "{status}" in old else {}
    want = render(old, params)
    got_en = render(resolve(key, en), params)
    got_zh = render(resolve(key, zh), params)
    routed = key in called
    if not routed:
        pending += 1
        verdict = "PENDING-NOT-ROUTED"
    elif got_en == want and got_zh == want:
        verdict = "PASS"
    else:
        verdict = "FAIL"
        bad += 1
    rows.append((line, key, verdict))
    L.append("line %d | key %s | en_equal=%s zh_equal=%s | %s" % (
        line, key, got_en == want, got_zh == want, verdict))
    if verdict != "PASS":
        L.append("    want=%r" % want)
        L.append("    en=%r" % got_en)
        L.append("    zh=%r" % got_zh)

orphans = sorted(k for k in called if k not in en and k not in zh)
L.append("CALLED_BUT_ABSENT_IN_DICT=%s" % (orphans or "none"))
L.append("PASS=%d FAIL=%d PENDING=%d TOTAL=%d" % (
    sum(1 for _, _, v in rows if v == "PASS"), bad, pending, len(rows)))
io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("\n".join(L[-4:]))
sys.exit(0 if bad == 0 and not orphans else 1)
