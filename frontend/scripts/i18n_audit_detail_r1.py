import re, os, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "src")
LOC = os.path.join(SRC, "i18n", "LocaleContext.tsx")

src = open(LOC, encoding="utf-8").read()
i = src.index("const en: Dict")
j = src.index("const zhCN: Dict")
k = src.index("const dictionaries")

KEY = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')


def load(chunk):
    d = {}
    for line in chunk.split("\n"):
        s = line.strip()
        if s.startswith("//") or s.startswith("*"):
            continue
        m = KEY.match(line)
        if m:
            d[m.group(1)] = m.group(2)
    return d


en = load(src[i:j])
zh = load(src[j:k])
print("en keys:", len(en), " zh keys:", len(zh))
print("zh-only:", sorted(set(zh) - set(en))[:20])
print("en-only:", sorted(set(en) - set(zh))[:20])

en_vals = {v for v in en.values() if v}
zh_vals = {v for v in zh.values() if v}

# my slice: detail pages + status pages
TARGETS = [
    "features/trip/ActivityDetail.tsx",
    "features/trip/TripItinerary.tsx",
    "features/trip/SpendPanel.tsx",
    "features/progress/journeyProgress.ts",
    "features/recovery/V14RecoveryTruthPanel.tsx",
    "features/inbox/JourneyInboxWorkbench.tsx",
    "features/checkin/FootprintPanel.tsx",
    "features/checklist/PretripChecklistPanel.tsx",
    "features/collections/CollectInto.tsx",
    "components/CnxMeasuredFacts.tsx",
    "components/ProductErrorBoundary.tsx",
    "components/RawFactsPanel.tsx",
    "components/PoiCandidateCard.tsx",
    "features/poster/TripPosterPanel.tsx",
    "features/pending/PendingSetPanel.tsx",
    "features/progress/journeyProgress.ts",
]

CJK = re.compile(r"[\u4e00-\u9fff]")
# a ternary arm: zh ? "cn" : "en"  possibly multiline
TERN = re.compile(
    r'\?\s*\n?\s*`?"([^"`]*)"`?\s*\n?\s*:\s*\n?\s*`?"([^"`]*)"`?',
    re.S,
)

report = []
for t in TARGETS:
    p = os.path.join(SRC, t)
    if not os.path.exists(p):
        print("MISSING FILE", t)
        continue
    lines = open(p, encoding="utf-8").read().split("\n")
    for n, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("//") or s.startswith("*") or s.startswith("/*"):
            continue
        if not CJK.search(line):
            continue
        report.append((t, n, line.rstrip()))

print("\n=== CJK lines in slice files:", len(report))
json.dump(report, open(os.path.join(BASE, "_audit_lines.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
for t, n, line in report:
    print("%s:%d | %s" % (t, n, line.strip()[:150]))