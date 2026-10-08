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
en_vals = {v: key for key, v in en.items()}
zh_vals = {v: key for key, v in zh.items()}

# EXPANDED slice: remaining status/detail surfaces not done in r1
TARGETS = [
    "components/ProductErrorBoundary.tsx",
    "components/RawFactsPanel.tsx",
    "features/checkin/FootprintPanel.tsx",
    "features/checkin/footprintCopy.ts",
    "features/collections/CollectInto.tsx",
    "features/collections/collectionCopy.ts",
    "features/poster/TripPosterPanel.tsx",
    "features/poster/posterShare.ts",
    "features/pending/PendingSetPanel.tsx",
    "features/pending/pendingSetCopy.ts",
    "features/recovery/RecoveryRequiredPanel.tsx",
    "features/recovery/V14RecoveryTruthPanel.tsx",
    "features/abort/JourneyAbortPanel.tsx",
    "features/abort/journeyAbortCopy.ts",
    "features/estimation/EstimationLadderPanel.tsx",
    "features/estimation/estimationLadderCopy.ts",
    "features/stay/HotelsPanel.tsx",
    "features/stay/stayGenerationDoor.ts",
    "features/checklist/PretripChecklistPanel.tsx",
    "features/trip/ActivityDetail.tsx",
    "features/trip/TripItinerary.tsx",
    "components/CnxMeasuredFacts.tsx",
    "features/progress/journeyProgress.ts",
]

CJK = re.compile(r"[\u4e00-\u9fff]")
PAIR = re.compile(r'(?:zh:\s*"([^"]*)"\s*,\s*en:\s*"([^"]*)"|zh\s*\?\s*[`"]([^`"]*)[`"]\s*:\s*[`"]([^`"]*)[`"])')
# also catch string literal inlined with zh ?
TERN = re.compile(r'zh\s*\?\s*[`"]([^`"]*)[`"]\s*:\s*[`"]([^`"]*)[`"]')

rows = []
for t in TARGETS:
    p = os.path.join(SRC, t)
    if not os.path.exists(p):
        print("MISSING", t)
        continue
    for n, line in enumerate(open(p, encoding="utf-8").read().split("\n"), 1):
        s = line.strip()
        if s.startswith("//") or s.startswith("*") or s.startswith("/*"):
            continue
        if not CJK.search(line):
            continue
        for m in PAIR.finditer(line):
            cn = m.group(1) or m.group(3)
            enstr = m.group(2) or m.group(4)
            if cn:
                rows.append((t, n, cn, enstr, "pair"))
        for m in TERN.finditer(line):
            if not any(m.group(0) in r[4] or True for r in []):
                pass

# dedicated copy modules are local dictionaries -> skip as gaps, record separately
COPY_MODS = [t for t in TARGETS if t.endswith(("Copy.ts", "copy.ts", "footprintRead.ts"))]
print("copy modules (own vocabulary, not dict gaps):", COPY_MODS)

seen = set()
out = []
for t, n, cn, enstr, _ in rows:
    if not CJK.search(cn):
        continue
    sig = (t, n, cn)
    if sig in seen:
        continue
    seen.add(sig)
    out.append({
        "file": t, "line": n, "zh": cn, "en": enstr,
        "zh_in_dict": zh_vals.get(cn),
        "en_in_dict": en_vals.get(enstr),
    })

missing = [o for o in out if not o["zh_in_dict"] or not o["en_in_dict"]]
print("candidate user-visible zh strings (ternary/pair):", len(out))
print("MISSING from dictionary (either side):", len(missing))
json.dump(out, open(os.path.join(BASE, "_pairs2.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
for o in out:
    flag = "MISS" if (not o["zh_in_dict"] or not o["en_in_dict"]) else "ok  "
    print("%s %s:%d zh=%r en=%r" % (flag, o["file"], o["line"], o["zh"][:70], o["en"][:70]))