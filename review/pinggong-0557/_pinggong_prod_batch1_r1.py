import io, re, sys

P = r"D:/moodle/_qoder_pinggong_0557/frontend/src/main.tsx"
lines = io.open(P, encoding="utf-8").read().split("\n")

# each op: (1-based line, old substring, new substring)
OPS = [
    (40, 'import { LocaleProvider } from "./i18n/LocaleContext";',
         'import { LocaleProvider, useT } from "./i18n/LocaleContext";'),
    (160, 'function errorNote(error: unknown): ErrorNote {',
          'function errorNote(\n  error: unknown,\n  t: (key: string, params?: Record<string, string | number>) => string,\n): ErrorNote {'),
    (170, '? "CityNexus request failed"',
          '? t("main.cityNexusRequestFailed")'),
    (171, ': `CityNexus request refused (HTTP ${status})`,',
          ': t("main.cityNexusRequestRefusedHttp", { status }),'),
    (566, 'summary: payload.summary ?? "Persisted operation update",',
          'summary: payload.summary ?? t("main.persistedOperationUpdate"),'),
    (1111, '{mission.objective_codes.join(" \u00b7 ") || "general recovery"}',
           '{mission.objective_codes.join(" \u00b7 ") || t("main.generalRecovery")}'),
    (1154, '"Activate a standing mission once; subsequent city signals can launch recovery without a new chat message."}',
           't("main.activateAStandingMissionOnceSubsequentCitySignalsCanLaunchRecoveryWithoutANewChatMessage")}'),
    (1218, '|| "No dominant failure mode"}',
           '|| t("main.noDominantFailureMode")}'),
    (1415, '{serverDecision ?? "not evaluated"}',
           '{serverDecision ?? t("main.notEvaluated")}'),
    (1423, '(impactResolution.maturity_stage ?? "validated Activity")',
           '(impactResolution.maturity_stage ?? t("main.validatedActivity"))'),
]

for no, old, new in OPS:
    i = no - 1
    if old not in lines[i]:
        sys.exit("ABORT line %d does not hold expected bytes: %r" % (no, lines[i][:120]))
    if lines[i].count(old) != 1:
        sys.exit("ABORT line %d holds %d copies of the needle" % (no, lines[i].count(old)))
    lines[i] = lines[i].replace(old, new, 1)
    print("ok %d" % no)

# inject useT() as the first statement of LegacyApp (line 176 is the signature)
if lines[175].strip() != "function LegacyApp() {":
    sys.exit("ABORT LegacyApp signature moved: %r" % lines[175])
lines.insert(176, "  const t = useT();")
print("ok inserted useT at line 177")

# errorNote call sites: every occurrence after the LegacyApp head gets `, t`
pat = re.compile(r"errorNote\(([^()]*)\)")
n = 0
for i in range(177, len(lines)):
    if "errorNote(" in lines[i]:
        new = pat.sub(lambda m: "errorNote(%s, t)" % m.group(1), lines[i])
        if new != lines[i]:
            lines[i] = new
            n += 1
            print("call site %d" % (i + 1))
print("CALL_SITES_PATCHED=%d" % n)

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("WROTE main.tsx")
