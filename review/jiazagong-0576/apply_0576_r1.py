# -*- coding: utf-8 -*-
"""ORD-0576 batch one, lane 加闸工 -- TripItinerary.tsx: eight traveller-visible literals.

Seven of the eight already exist in the dictionary byte-identically on BOTH sides, so this round
re-points them at those keys instead of minting synonyms (the commander ruled 维持复用 and voided
same-text duplicate keys). The eighth -- the disrupted-stop fallback word -- has no equal-value key on
either side, so it is the only new key, and it joins the family the file already reads from.

Every old block must match exactly once; any other count aborts before a byte is written."""

import io
import re
import sys

WT = r"D:\moodle\_jz_0576\wt\frontend\src"
PROD = WT + r"\features\trip\TripItinerary.tsx"
DICT = WT + r"\i18n\LocaleContext.tsx"

EDITS = [
    (PROD,
     '''      ? zh
        ? "AI 帮我规划（要先有地点）"
        : "Plan my trip with AI (needs places first)"
      : zh
        ? "AI 帮我规划"
        : "Plan my trip with AI";''',
     '''      ? t("itinerary.planWithAiNeedsPlaces")
      : t("itinerary.planWithAi");'''),
    (PROD,
     '''                ? zh
                  ? "这一版方案里还没有站点被排在某一天上。补上站点，这一屏就按天把它们列出来。"
                  : "No stop in this plan sits on a day yet. Add stops and this screen lists them day by day."
                : zh
                  ? "这个行程还没有选定的方案。先让 AI 帮你规划，选定方案后这里会显示逐日安排。"
                  : "This trip has no chosen plan yet. Ask the AI to plan it, then pick a plan and the day-by-day itinerary appears here."''',
     '''                ? t("itinerary.emptyPlanNoDays")
                : t("itinerary.emptyNoPlan")'''),
    (PROD,
     '''                ? zh
                  ? "正在向服务器回读这座城有多少地点…"
                  : "Reading back from the server how many places this city holds…"''',
     '''                ? t("itinerary.emptyReadingPlaces")'''),
    (PROD,
     '''              ? zh
                ? "天数未知"
                : "length unknown"
              : zh''',
     '''              ? t("itinerary.lengthUnknown")
              : zh'''),
    (PROD,
     '''            {zh
              ? "逐日安排。已确认的预订会被标记为受保护。"
              : "Day by day. Confirmed bookings are marked as protected."}''',
     '''            {t("itinerary.dayByDay")}'''),
    (PROD,
     '''                            : zh
                              ? "受影响"
                              : "Affected"}''',
     '''                            : t("itinerary.stopDisrupted")}'''),
]

# the one genuinely new key, inserted at the end of the itinerary family on both sides, same order
DICT_EDITS = [
    ('  "itinerary.dayByDay": "Day by day. Confirmed bookings are marked as protected.",',
     '  "itinerary.dayByDay": "Day by day. Confirmed bookings are marked as protected.",\n  "itinerary.stopDisrupted": "Affected",'),
    ('  "itinerary.dayByDay": "逐日安排。已确认的预订会被标记为受保护。",',
     '  "itinerary.dayByDay": "逐日安排。已确认的预订会被标记为受保护。",\n  "itinerary.stopDisrupted": "受影响",'),
]

texts = {}
for path, old, _new in EDITS:
    src = texts.get(path) or io.open(path, encoding="utf-8", newline="").read()
    n = src.count(old)
    if n != 1:
        raise SystemExit("ABORT product anchor matched %d times in %s :: %r" % (n, path, old[:60]))
    texts[path] = src
dsrc = io.open(DICT, encoding="utf-8", newline="").read()
for old, _new in DICT_EDITS:
    n = dsrc.count(old)
    if n != 1:
        raise SystemExit("ABORT dictionary anchor matched %d times :: %r" % (n, old[:60]))

for path, old, new in EDITS:
    texts[path] = texts[path].replace(old, new, 1)
    print("re-pointed %s" % old.strip().splitlines()[0][:58])
for old, new in DICT_EDITS:
    dsrc = dsrc.replace(old, new, 1)
    print("dictionary row added: %s" % new.splitlines()[1].strip()[:58])

for path, src in texts.items():
    io.open(path, "w", encoding="utf-8", newline="").write(src)
io.open(DICT, "w", encoding="utf-8", newline="").write(dsrc)

left = io.open(PROD, encoding="utf-8", newline="").read()
for probe in ("AI 帮我规划", "这一版方案里还没有站点", "正在向服务器回读这座城", "天数未知", "逐日安排。已确认", "受影响"):
    if probe in left:
        raise SystemExit("ABORT literal still present in the product file: " + probe)
print("all eight literals gone from the product face; templated rows left for the next round: %d"
      % len(re.findall(r"zh\s*\n?\s*?\? *`", left)))
