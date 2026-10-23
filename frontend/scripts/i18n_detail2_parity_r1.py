import re, os, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOC = os.path.join(BASE, "src", "i18n", "LocaleContext.tsx")
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


en, zh = load(src[i:j]), load(src[j:k])
print("en keys:", len(en), "zh keys:", len(zh))
assert set(en) == set(zh), ("PARITY BREAK", sorted(set(en) ^ set(zh)))
print("PARITY OK: both sides carry the same key set")

PH = re.compile(r"\{(\w+)\}")
for section in ("detail.", "itinerary."):
    keys = [k2 for k2 in en if k2.startswith(section)]
    for key in keys:
        assert en.get(key), "empty en: " + key
        assert zh.get(key), "empty zh: " + key
        a = sorted(PH.findall(en[key]))
        b = sorted(PH.findall(zh[key]))
        assert a == b, ("placeholder mismatch", key, a, b)
    print("%s keys: %d, all non-empty, placeholders matched" % (section, len(keys)))

# literal-value match for the itinerary sentences (the strings the screens already showed)
EXPECT = {
    "itinerary.importPrompt": ("Import places for this trip", "去导入这趟的地点"),
    "itinerary.planWithAiNeedsPlaces": ("Plan my trip with AI (needs places first)",
                                        "AI 帮我规划（要先有地点）"),
    "itinerary.planWithAi": ("Plan my trip with AI", "AI 帮我规划"),
    "itinerary.emptyTitle": ("No itinerary yet", "还没有可看的安排"),
    "itinerary.emptyPlanNoDays": ("No stop in this plan sits on a day yet. Add stops and they will be listed day by day.",
                                   "这一版方案里还没有站点被排在某一天上。补上站点，就能按天看到安排。"),
    "itinerary.emptyNoPlan": ("This trip has no chosen plan yet. Ask the AI to plan it, then pick a plan.",
                              "这个行程还没有选定的方案。先让 AI 帮你规划，选定之后就能按天看。"),
    "itinerary.emptyReadingPlaces": ("Reading back from the server how many places this city holds…",
                                     "正在向服务器回读这座城有多少地点…"),
    "itinerary.lengthUnknown": ("length unknown", "天数未知"),
    "itinerary.dayByDay": ("Day by day. Confirmed bookings are marked as protected.",
                           "逐日安排。已确认的预订会被标记为受保护。"),
}
bad = [(key, en.get(key), zh.get(key)) for key, (a, b) in EXPECT.items()
       if en.get(key) != a or zh.get(key) != b]
assert not bad, bad
print("all %d itinerary literal values match the sentences the screens already showed" % len(EXPECT))
print("SELFCHECK_PASS")