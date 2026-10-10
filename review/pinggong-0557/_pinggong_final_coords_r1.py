import io, re, subprocess

WT = r"D:/moodle/_qoder_pinggong_0557"
PROD = WT + "/frontend/src/main.tsx"
DICT = r"D:/moodle/_qoder_pinggong_0557_dict/frontend/src/i18n/LocaleContext.tsx"
OUT = WT + "/review/pinggong-0557/final_coords_r1.txt"
BASE = "d435cff26df752908a8a3a58d5c61f9f5c23f40c"

TABLE = [
    ("main.cityNexusRequestFailed", "CityNexus request failed"),
    ("main.cityNexusRequestRefusedHttp", "CityNexus request refused (HTTP"),
    ("main.persistedOperationUpdate", "Persisted operation update"),
    ("main.generalRecovery", "general recovery"),
    ("main.activateAStandingMissionOnceSubsequentCitySignalsCanLaunchRecoveryWithoutANewChatMessage",
     "Activate a standing mission once"),
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
    ("main.unnamedCommitmentServerGaveNoName", "未命名承诺"),
    ("main.verifiedFeasible", "verified feasible"),
    ("main.notFeasible", "not feasible"),
    ("main.notPreserved", "not preserved"),
    ("main.verifiedEvidenceAttached", "verified evidence attached"),
    ("main.evidenceUnavailable", "evidence unavailable"),
]

prod = io.open(PROD, encoding="utf-8").read().split("\n")
dictl = io.open(DICT, encoding="utf-8").read().split("\n")
base_main = subprocess.run(["git", "-C", WT, "show", "%s:frontend/src/main.tsx" % BASE],
                           capture_output=True).stdout.decode("utf-8").split("\n")

en_i = next(i for i, s in enumerate(dictl) if s.startswith("const en: Dict = {"))
en_j = next(i for i, s in enumerate(dictl[en_i + 1:], en_i + 1) if s == "};")
zh_i = next(i for i, s in enumerate(dictl) if s.startswith("const zhCN: Dict = {"))
zh_j = next(i for i, s in enumerate(dictl[zh_i + 1:], zh_i + 1) if s == "};")

L = ["# all 21 coordinates at branch tip %s on landing base %s" % (
    subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), BASE)]
L.append("en object LocaleContext.tsx:%d..%d  zh object LocaleContext.tsx:%d..%d" % (
    en_i + 1, en_j + 1, zh_i + 1, zh_j + 1))
missed = 0
for key, needle in TABLE:
    routed = [i + 1 for i, s in enumerate(prod) if 't("%s"' % key in s]
    before = [i + 1 for i, s in enumerate(base_main) if needle in s]
    en_h = [i + 1 for i in range(en_i, en_j) if dictl[i].startswith('  "%s":' % key)]
    zh_h = [i + 1 for i in range(zh_i, zh_j) if dictl[i].startswith('  "%s":' % key)]
    if not routed or not before:
        missed += 1
    L.append("key %s | routed main.tsx:%s | was_on_base main.tsx:%s | en LocaleContext.tsx:%s | zh LocaleContext.tsx:%s" % (
        key, ",".join(map(str, routed)) or "NONE", ",".join(map(str, before)) or "NONE",
        ",".join(map(str, en_h)) or "absent", ",".join(map(str, zh_h)) or "absent"))
L.append("ROWS_WITH_MISSING_ROUT_OR_MISSING_BASE=%d out of %d" % (missed, len(TABLE)))
io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("WROTE", OUT, len(L), "missed=", missed)
