import re, os, sys, json

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
assert set(en) == set(zh), ("PARITY BREAK",
                            sorted(set(en) ^ set(zh)))
print("PARITY OK: both sides carry the same key set")

new = [k2 for k2 in en if k2.startswith("detail.")]
print("detail.* keys:", len(new))
assert len(new) == 39, len(new)

# every new key must be non-empty on both sides
for key in new:
    assert en.get(key), "empty en: " + key
    assert zh.get(key), "empty zh: " + key
    assert en[key] != key and zh[key] != key
print("all detail.* keys non-empty on both sides")

# values must differ between languages for genuinely translated entries
same = [key for key in new if en[key] == zh[key]]
print("identical en/zh values:", same)

# placeholders must match across sides
PH = re.compile(r"\{(\w+)\}")
for key in new:
    a = sorted(PH.findall(en[key]))
    b = sorted(PH.findall(zh[key]))
    assert a == b, ("placeholder mismatch", key, a, b)
print("placeholder sets match on both sides for every detail.* key")

# the moved values must be exactly what the screens were already showing
EXPECT = {
    "detail.backToItinerary": ("Back to itinerary", "返回行程"),
    "detail.duration": ("Duration", "停留时长"),
    "detail.travelFromPrev": ("Travel from previous stop", "从上一站出发"),
    "detail.openingHours": ("Opening hours", "营业时间"),
    "detail.hoursProvided": ("Provided", "已提供"),
    "detail.hoursProviderText": (" · provider's own text", " · 供应商原文"),
    "detail.hoursNoData": ("Not available", "暂无数据"),
    "detail.category": ("Category", "类型"),
    "detail.activityType": ("Activity type", "活动类型"),
    "detail.location": ("Location", "位置"),
    "detail.noCoordinates": ("No coordinates", "暂无坐标"),
    "detail.showOnMap": ("Show on map", "在地图上查看"),
    "detail.askCopilot": ("Ask Copilot", "问问 Copilot"),
    "detail.nearbyStops": ("Other stops nearby", "附近的其他停靠点"),
    "detail.otherTripStops": ("Other stops on this trip", "这趟行程的其他停靠点"),
    "detail.confirmedProtected": ("Confirmed · protected", "已确认 · 受保护"),
    "detail.viewDetails": ("View details", "查看详情"),
    "detail.detailsChevron": ("Details ›", "详情 ›"),
    "detail.pretripAria": ("Pre-trip checklist", "行前清单"),
    "detail.pretripKicker": ("Before you go", "行前清单"),
    "detail.pretripHeading": ("The two things the server reports as outstanding",
                              "服务端报出的两类待办"),
    "detail.basisPrefix": ("Basis: ", "依据："),
    "detail.anchorPrefix": ("Anchor: ", "锚点："),
    "detail.measuredHttpLabel": ("This device's reading: HTTP", "这台设备看到的回读：HTTP"),
    "detail.measuredContentType": ("Media type read back", "回读的媒体类型"),
    "detail.measuredBytes": ("Octets this device counted", "这台设备数到的字节"),
    "detail.receiptFoldSummary": ("What this device read back, and the server's receipt",
                                  "这台设备量到的回读与服务器回执号"),
    "detail.receiptHttpNone": ("This device's reading: HTTP measured none",
                               "这台设备看到的回读：HTTP 没量到"),
    "detail.receiptLabel": ("server receipt", "服务器回执号"),
    "detail.receiptLabelAbsent": ("no server receipt", "服务器未给回执号"),
    "detail.rawFactsHeading": ("Fields this device measured", "这台设备自己量到的回读字段"),
}
bad = []
for key, (a, b) in EXPECT.items():
    if en.get(key) != a or zh.get(key) != b:
        bad.append((key, en.get(key), zh.get(key)))
assert not bad, bad
print("all %d literal values match the sentences the screens already showed" % len(EXPECT))
print("SELFCHECK_PASS")