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

TARGETS = [
    "features/trip/ActivityDetail.tsx",
    "features/trip/TripItinerary.tsx",
    "features/trip/SpendPanel.tsx",
    "features/progress/journeyProgress.ts",
    "features/recovery/V14RecoveryTruthPanel.tsx",
    "features/checklist/PretripChecklistPanel.tsx",
    "components/CnxMeasuredFacts.tsx",
    "components/ProductErrorBoundary.tsx",
    "components/RawFactsPanel.tsx",
]

CJK = re.compile(r"[\u4e00-\u9fff]")
# zh/en pair literal: { zh: "cn", en: "en" }  or  zh: "cn", en: "en"
PAIR = re.compile(r'zh:\s*"([^"]*)"\s*,\s*en:\s*"([^"]*)"')
# ternary arms on one line: zh ? "cn" : "en"  (or backticks)
TERN1 = re.compile(r'zh\s*\?\s*[`"]([^`"]*)[`"]\s*:\s*[`"]([^`"]*)[`"]')

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
            rows.append((t, n, m.group(1), m.group(2)))
        for m in TERN1.finditer(line):
            rows.append((t, n, m.group(1), m.group(2)))

seen = set()
out = []
for t, n, cn, enstr in rows:
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

print("candidate user-visible zh strings:", len(out))
missing = [o for o in out if not o["zh_in_dict"] or not o["en_in_dict"]]
print("MISSING from dictionary (either side):", len(missing))
json.dump(out, open(os.path.join(BASE, "_pairs.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
for o in out:
    flag = "MISS" if (not o["zh_in_dict"] or not o["en_in_dict"]) else "ok  "
    print("%s %s:%d zh=%r en=%r" % (flag, o["file"], o["line"], o["zh"][:60], o["en"][:60]))