import io, sys

P = r"D:/moodle/_qoder_pinggong_0557_dict/frontend/src/i18n/LocaleContext.tsx"
EN_ANCHOR = '  "shell.reservationReviewFields": "This cannot become a commitment yet'
ZH_ANCHOR = '  "shell.reservationReviewFields": "这条还不能成为承诺'

EN_KEYS = [
    ("main.cityNexusRequestFailed", "CityNexus request failed"),
    ("main.cityNexusRequestRefusedHttp", "CityNexus request refused (HTTP {status})"),
    ("main.persistedOperationUpdate", "Persisted operation update"),
    ("main.generalRecovery", "general recovery"),
    ("main.activateAStandingMissionOnceSubsequentCitySignalsCanLaunchRecoveryWithoutANewChatMessage",
     "Activate a standing mission once; subsequent city signals can launch recovery without a new chat message."),
    ("main.noDominantFailureMode", "No dominant failure mode"),
    ("main.notEvaluated", "not evaluated"),
    ("main.validatedActivity", "validated Activity"),
    ("main.noActionableTarget", "no actionable target"),
    ("main.outcomeEvidence", "outcome evidence"),
    ("main.explicitWins", "explicit wins"),
    ("main.notReported", "not reported"),
    ("main.noUpcomingActivity", "no upcoming activity"),
    ("main.noActiveC4", "No active C4"),
    ("main.notAvailable", "not available"),
    ("main.verifiedFeasible", "verified feasible"),
    ("main.notFeasible", "not feasible"),
    ("main.notPreserved", "not preserved"),
    ("main.verifiedEvidenceAttached", "verified evidence attached"),
    ("main.evidenceUnavailable", "evidence unavailable"),
]
ZH_KEYS = [
    ("main.unnamedCommitmentServerGaveNoName", "未命名承诺 · 服务器没给名字"),
]

src = io.open(P, encoding="utf-8").read()
lines = src.split("\n")


def esc(v):
    return v.replace("\\", "\\\\").replace('"', '\\"')


def insert_after(anchor_prefix, keys, label):
    idx = [i for i, s in enumerate(lines) if s.startswith(anchor_prefix)]
    if len(idx) != 1:
        sys.exit("ABORT anchor %s hits=%d" % (label, len(idx)))
    for k, v in keys:
        if any(s.startswith('  "%s":' % k) for s in lines):
            sys.exit("ABORT key already present: %s" % k)
    at = idx[0] + 1
    new = ['  "%s": "%s",' % (k, esc(v)) for k, v in keys]
    lines[at:at] = new
    print("inserted %d into %s after line %d" % (len(new), label, idx[0] + 1))
    return at


en_at = insert_after(EN_ANCHOR, EN_KEYS, "en")
zh_at = insert_after(ZH_ANCHOR, ZH_KEYS, "zh")

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("TOTAL_KEYS_INSERTED=%d" % (len(EN_KEYS) + len(ZH_KEYS)))
print("en_block_first_line=%d zh_block_first_line=%d" % (en_at + 1, zh_at + 1))
