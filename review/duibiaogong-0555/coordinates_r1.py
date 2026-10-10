"""Compute every coordinate this lane quotes, from the pushed branch and the authoritative tip.

Nothing here is typed from memory: each line is re-read at run time, so the readout file is the
single place the numbers exist and the ledger block only points at it.
"""

import re
import subprocess

ROOT = "D:/moodle/_qoder_duibiaogong_0555"
TIP = "3bb001aef4e2158dbdc53454ee14d56988f28405"
OUT = ROOT + "/review/duibiaogong-0555/coordinates_readout_r1.txt"
PAIRS = [
    (177, "scene.theExecutionCursor"),
    (178, "scene.theJourneySStart"),
    (179, "scene.theServerGaveNoBasis"),
    (184, "scene.theFrozenEvidenceCarriesAnExpiry"),
    (197, "scene.noFrozenEvidenceOnThisTrip"),
    (198, "scene.noScenarioOnStage"),
]


def sh(argv):
    return subprocess.run(argv, capture_output=True).stdout.decode("utf-8", "replace")


def number(path, needle):
    """Every 1-based line number in the worktree file whose text contains `needle`."""
    hits = []
    for i, ln in enumerate(open(ROOT + path, encoding="utf-8").read().splitlines(), 1):
        if needle in ln:
            hits.append(i)
    return hits


def tip_line(lineno):
    body = sh(["git", "-C", ROOT, "show", "%s:frontend/src/lib/sceneClock.ts" % TIP])
    return body.splitlines()[lineno - 1].strip()


lines = []
lines.append("authoritative tip (ls-remote at write time) = " + sh(
    ["git", "-C", ROOT, "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"]).split("\t")[0].strip())
lines.append("branch heads: dict=%s r1=%s" % (
    sh(["git", "-C", ROOT, "rev-parse", "refs/heads/review/对表工-0555-dict-r1"]).strip(),
    sh(["git", "-C", ROOT, "rev-parse", "refs/heads/review/对表工-0555-r1"]).strip()))
lines.append("")
lines.append("per spot: before-line on tip -> after-line on branch, and the two dictionary sides")
for lineno, key in PAIRS:
    before = "frontend/src/lib/sceneClock.ts:%d" % lineno
    after = number("/frontend/src/lib/sceneClock.ts", 'say("%s")' % key)
    en = number("/frontend/src/i18n/LocaleContext.tsx", '"%s":' % key)
    lines.append("%s -> %s | key %s | en at LocaleContext.tsx:%s | zh at LocaleContext.tsx:%s" % (
        before,
        " ".join("sceneClock.ts:%d" % n for n in after) if after else "NOT_FOUND",
        key,
        en[0] if len(en) > 0 else "NOT_FOUND",
        en[1] if len(en) > 1 else "NOT_FOUND",
    ))
    lines.append("      before text on tip = %s" % tip_line(lineno))

lines.append("")
lines.append("call sites that hand the reader down")
for n in number("/frontend/src/features/simulation/SimulationPanel.tsx", "basisWord(scene"):
    lines.append("      SimulationPanel.tsx:%d = %s" % (n, open(ROOT + "/frontend/src/features/simulation/SimulationPanel.tsx", encoding="utf-8").read().splitlines()[n - 1].strip()))
for n in number("/frontend/src/features/simulation/SimulationPanel.tsx", "evidenceWord(scene"):
    lines.append("      SimulationPanel.tsx:%d = %s" % (n, open(ROOT + "/frontend/src/features/simulation/SimulationPanel.tsx", encoding="utf-8").read().splitlines()[n - 1].strip()))
lines.append("      t already in scope: SimulationPanel.tsx:%d" % number("/frontend/src/features/simulation/SimulationPanel.tsx", "const { locale, t } = useLocale();")[0])

lines.append("")
lines.append("inline pairs left untouched (not in the ORD-0555 table, no spare key invented)")
for n in number("/frontend/src/lib/sceneClock.ts", "zh ?") + number("/frontend/src/lib/sceneClock.ts", "return zh"):
    lines.append("      sceneClock.ts:%d" % n)

lines.append("")
lines.append("dictionary counts, parsed the same way on both states")
for label, rev in (("tip", TIP), ("branch", "HEAD")):
    body = sh(["git", "-C", ROOT, "show", "%s:frontend/src/i18n/LocaleContext.tsx" % rev]) if rev != "HEAD" else open(ROOT + "/frontend/src/i18n/LocaleContext.tsx", encoding="utf-8").read()
    en_start = body.index("const en: Dict = {")
    zh_start = body.index("const zhCN: Dict = {")
    end = body.index("const dictionaries")
    n_en = len(re.findall(r'^\s{2}"([^"]+)":', body[en_start:zh_start], re.M))
    n_zh = len(re.findall(r'^\s{2}"([^"]+)":', body[zh_start:end], re.M))
    dup = [k for k, c in [(k, body[zh_start:end].count('"%s":' % k)) for k in re.findall(r'^\s{2}"([^"]+)":', body[zh_start:end], re.M)] if c > 1]
    lines.append("      %s: en=%d zh=%d duplicate_names_in_zh=%d" % (label, n_en, n_zh, len(set(dup))))

text = "\n".join(lines) + "\n"
open(OUT, "w", encoding="utf-8", newline="\n").write(text)
print(text)
