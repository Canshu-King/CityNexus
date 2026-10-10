import io, re, subprocess

WT = r"D:/moodle/_qoder_pinggong_0557"
PROD = WT + "/frontend/src/main.tsx"
DICT_LOCAL = r"D:/moodle/_qoder_pinggong_0557_dict/frontend/src/i18n/LocaleContext.tsx"
OUT = WT + "/review/pinggong-0557/batch1_coords_r1.txt"

KEYS = [
    (170, "main.cityNexusRequestFailed"),
    (171, "main.cityNexusRequestRefusedHttp"),
    (566, "main.persistedOperationUpdate"),
    (1111, "main.generalRecovery"),
    (1154, "main.activateAStandingMissionOnceSubsequentCitySignalsCanLaunchRecoveryWithoutANewChatMessage"),
    (1218, "main.noDominantFailureMode"),
    (1415, "main.notEvaluated"),
    (1423, "main.validatedActivity"),
]

prod = io.open(PROD, encoding="utf-8").read().split("\n")
dictl = io.open(DICT_LOCAL, encoding="utf-8").read().split("\n")

tip = subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
parent = subprocess.run(["git", "-C", WT, "rev-parse", "HEAD~1"], capture_output=True, text=True).stdout.strip()
import subprocess as _sp

L = ["# batch1 coordinates, read at branch tip %s (parent %s)" % (tip, parent)]
for before_line, key in KEYS:
    hits = [i + 1 for i, s in enumerate(prod) if 't("%s"' % key in s]
    en_h = [i + 1 for i, s in enumerate(dictl) if s.startswith('  "%s":' % key)]
    L.append("key %s" % key)
    L.append("   routed_at main.tsx:%s   dict_line LocaleContext.tsx:%s" % (
        ",".join(str(h) for h in hits), ",".join(str(h) for h in en_h)))
    for h in hits:
        L.append("   body L%d| %s" % (h, prod[h - 1].strip()[:170]))
    for h in en_h:
        L.append("   dict L%d| %s" % (h, dictl[h - 1].strip()[:170]))

L.append("en object first key line / zh object first key line:")
en_first = next(i for i, s in enumerate(dictl) if s.startswith("const en: Dict"))
zh_first = next(i for i, s in enumerate(dictl) if s.startswith("const zhCN: Dict"))
L.append("   LocaleContext.tsx:%d is 'const en: Dict = {'" % (en_first + 1))
L.append("   LocaleContext.tsx:%d is 'const zhCN: Dict = {'" % (zh_first + 1))
io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("WROTE", OUT, len(L))
