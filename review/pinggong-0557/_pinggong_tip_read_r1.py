import io, os, subprocess, sys

WT = r"D:/moodle/_qoder_pinggong_0557"
MAINS = os.path.join(WT, "frontend", "src", "main.tsx")
LOC = os.path.join(WT, "frontend", "src", "i18n", "LocaleContext.tsx")
OUT = os.path.join(WT, "review", "pinggong-0557", "tip_readout_r1.txt")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

tip = subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
remote = subprocess.run(
    ["git", "-C", WT, "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
    capture_output=True, text=True).stdout.split()[0]

lines = io.open(MAINS, encoding="utf-8").read().splitlines()
loc = io.open(LOC, encoding="utf-8").read().splitlines()

targets = [
    (170, "CityNexus request failed"),
    (171, "CityNexus request refused (HTTP"),
    (566, "Persisted operation update"),
    (1111, "general recovery"),
    (1154, "Activate a standing mission once"),
    (1218, "No dominant failure mode"),
    (1415, "not evaluated"),
    (1423, "validated Activity"),
    (1424, "no actionable target"),
    (1475, "outcome evidence"),
    (1487, "explicit wins"),
    (1545, "not reported"),
    (1547, "no upcoming activity"),
    (1551, "No active C4"),
    (1560, "not available"),
    (1595, "未命名承诺"),
    (1646, "verified feasible"),
    (1646, "not feasible"),
    (1680, "not preserved"),
    (1682, "verified evidence attached"),
    (1683, "evidence unavailable"),
]

b = []
b.append("_fbkeys draft line | needle | hits in main.tsx at tip | file:line")
b.append("tip_local=%s tip_remote=%s main.tsx_lines=%d LocaleContext_lines=%d" % (
    tip, remote, len(lines), len(loc)))
for dl, needle in targets:
    hits = [i + 1 for i, s in enumerate(lines) if needle in s]
    b.append("draft:%d | %s | hits=%s | first=%s:%d" % (
        dl, needle, ",".join(str(h) for h in hits), "main.tsx", hits[0] if hits else -1))
    for h in hits[:3]:
        b.append("      L%d| %s" % (h, lines[h - 1].strip()[:150]))

b.append("ANCHORS shell.reservationReviewFields in LocaleContext.tsx:")
for i, s in enumerate(loc):
    if "shell.reservationReviewFields" in s:
        b.append("      L%d| %s" % (i + 1, s.strip()[:150]))

b.append("useT / LocaleProvider import lines in main.tsx:")
for i, s in enumerate(lines):
    if "useT" in s or "LocaleProvider" in s or "useLocale" in s:
        b.append("      L%d| %s" % (i + 1, s.strip()[:150]))

b.append("errorNote module-scope:")
for i, s in enumerate(lines):
    if "errorNote" in s:
        b.append("      L%d| %s" % (i + 1, s.strip()[:150]))

io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(b) + "\n")
print("WROTE", OUT, "lines=", len(b))
