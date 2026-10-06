"""Aggregate every `_untranslated_*_r1.json` receipt into one inventory, and SPLIT the strings into
"looks like copy" vs "looks like brand/data/id/locale-switcher".

Why this exists: the first aggregation died with `UnicodeEncodeError: 'gbk' codec` after printing 6 of
13 distinct strings - a GBK console cannot take the CJK/`·` bytes these receipts carry.  So this run
writes its table to a UTF-8 FILE and only prints an ASCII progress line to stdout.

Why the split matters: a bare "visible ASCII leaf" is not by itself a defect.  `Copilot` is a brand name,
`Tech Art Center` is a place name that came out of the data, `place-river-cruise` is an id, ` CN / AI` is a
locale switcher.  Those must stay English.  What counts is prose - sentences and headings that a zh user is
meant to read.  The classifier is deliberately narrow and every one of its rules is printed next to the
string so a human can overrule it.
"""
import io
import json
import os
import re
import sys
import glob

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_untranslated_aggregate_r3.json")
TXT = os.path.join(HERE, "_untranslated_aggregate_r3.txt")

CJK = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\u3400-\u4dbf]")

# Brand names we ship on purpose.
BRAND = {"copilot", "citynexus", "citynexus copilot", "cn", "ai", "cn / ai", "osm", "openstreetmap"}


def classify(s):
    """Return (bucket, rule) for one visible ASCII string."""
    t = s.strip()
    low = t.lower()
    if low in BRAND:
        return "BRAND", "exact brand word"
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", low):
        return "ID_LIKE", "kebab-case token"
    if "·" in t and not re.search(r"\b(is|are|the|no|not|needs|from|of)\b", low):
        return "DATA_TAGS", "middle-dot separated tag list"
    if len(t.split()) <= 2 and not t.endswith(".") and not re.search(r"\b(is|are|needs|never|from)\b", low):
        return "SHORT_LABEL_OR_DATA", "1-2 words, no sentence verb"
    if re.search(r"\b(is|are|was|were|needs|never|not|no|must|can|will|from|the)\b", low) or t.endswith("."):
        return "PROSE", "sentence shape (verb/article/terminal period)"
    return "UNCLEAR", "no rule matched"


def load(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


rows = []
# r3 reads the r2 receipts (scroll-union instrument).  r1's receipts under-counted: r1 filtered on
# `top < innerHeight` and never scrolled, so anything below the fold was invisible to it.
files = sorted(glob.glob(os.path.join(HERE, "_untranslated_*", "untranslated_*_r2.json")))
print("receipt files found:", len(files))
for f in files:
    # the screen name lives in the FILE name (13 receipts share the `_untranslated_all/` directory),
    # so deriving it from the directory collapsed all 13 into one screen named "all".
    base = os.path.basename(f)
    screen = re.sub(r"^untranslated_", "", base)
    screen = re.sub(r"_r\d+\.json$", "", screen)
    d = load(f)
    route_in_receipt = d.get("route")
    if route_in_receipt:
        screen = str(route_in_receipt).strip("/").replace("/", "-") or screen
    for arm in ("zh", "en"):
        a = d.get(arm) or {}
        # the receipt's leaf list is called `ascii_prose` (r1 instrument), not `items`
        for item in a.get("ascii_prose") or a.get("items") or []:
            rows.append({
                "screen": screen,
                "arm": arm,
                "text": item.get("text", ""),
                "tag": item.get("tag", ""),
                "testid": item.get("testid"),
                "cls": item.get("class"),
            })
print("raw leaf rows:", len(rows))

agg = {}
for r in rows:
    key = r["text"]
    b, rule = classify(key)
    e = agg.setdefault(key, {"text": key, "bucket": b, "rule": rule, "zh_screens": [], "en_screens": [],
                             "tags": sorted({r["tag"] for r in rows if r["text"] == key})})
    if r["arm"] == "zh":
        if r["screen"] not in e["zh_screens"]:
            e["zh_screens"].append(r["screen"])
    else:
        if r["screen"] not in e["en_screens"]:
            e["en_screens"].append(r["screen"])

# The defect class: a string that is PROSE (or an unclear sentence-ish thing) and still on screen in the zh arm.
defect = [e for e in agg.values() if e["bucket"] in ("PROSE", "UNCLEAR") and e["zh_screens"]]
defect.sort(key=lambda e: (-len(e["zh_screens"]), e["text"]))
nondefect = [e for e in agg.values() if e not in defect]
nondefect.sort(key=lambda e: (e["bucket"], -len(e["zh_screens"])))

per_screen_zh = {}
for r in rows:
    if r["arm"] != "zh":
        continue
    b, _ = classify(r["text"])
    if b in ("PROSE", "UNCLEAR"):
        per_screen_zh[r["screen"]] = per_screen_zh.get(r["screen"], 0) + 1

res = {
    "generated_by": "_untranslated_aggregate_r3.py",
    "instrument": "_untranslated_scan_r2.js (scroll-union; r1 under-counted below-the-fold leaves)",
    "receipt_files": [os.path.relpath(f, HERE) for f in files],
    "screens_covered": sorted({r["screen"] for r in rows}),
    "raw_leaf_rows": len(rows),
    "distinct_strings": len(agg),
    "defect_strings_zh_prose": len(defect),
    "non_defect_strings": len(nondefect),
    "defect": defect,
    "non_defect": nondefect,
    "zh_prose_leaves_per_screen": per_screen_zh,
    "verdict": ("ZH_SCREENS_CARRY_ENGLISH_PROSE" if defect else "NO_ENGLISH_PROSE_ON_ZH_SCREENS"),
}
with io.open(OUT, "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=1)

lines = []
lines.append("UNTRANSLATED-COPY AGGREGATE  (r2, UTF-8 file output)")
lines.append("screens covered (%d): %s" % (len(res["screens_covered"]), ", ".join(res["screens_covered"])))
lines.append("raw leaf rows %d | distinct strings %d" % (res["raw_leaf_rows"], res["distinct_strings"]))
lines.append("")
lines.append("== DEFECT CANDIDATES: English PROSE still rendered in the zh arm (%d distinct) ==" % len(defect))
for e in defect:
    lines.append("  [%s] tag=%s zh_screens=%s" % (e["bucket"], ",".join(e["tags"]), ",".join(e["zh_screens"])))
    lines.append("      %r   (rule: %s)" % (e["text"], e["rule"]))
lines.append("")
lines.append("== NOT A DEFECT (brand / data / id / locale switcher) ==")
for e in nondefect:
    lines.append("  [%s] zh=%d en=%d  %r  (rule: %s)" % (e["bucket"], len(e["zh_screens"]),
                                                        len(e["en_screens"]), e["text"], e["rule"]))
lines.append("")
lines.append("== zh prose-leaf counts per screen ==")
for k in sorted(per_screen_zh, key=lambda x: -per_screen_zh[x]):
    lines.append("  %-16s %d" % (k, per_screen_zh[k]))
lines.append("")
lines.append("VERDICT " + res["verdict"])
with io.open(TXT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

print("wrote", OUT, os.path.getsize(OUT), "B")
print("wrote", TXT, os.path.getsize(TXT), "B")
print("screens", len(res["screens_covered"]), "| distinct", res["distinct_strings"],
      "| zh prose defects", res["defect_strings_zh_prose"], "| verdict", res["verdict"])
