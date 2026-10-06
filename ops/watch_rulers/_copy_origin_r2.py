"""r2: classify the ORIGIN of every English string that a zh user actually sees.

r1 scanned the source for "looks like English prose" and got 1200 hits in 69 files.  That number is useless
and I am not going to hand it to a lane: 289 of the hits are inside `i18n/LocaleContext.tsx`, which is the
EN dictionary - English there is correct by definition.  A source-side shape scan cannot tell "English
string in the en dictionary" from "English string rendered at a zh user", which is the only thing that is a
defect.

So r2 inverts it.  The truth of "what the zh user sees" comes from the RENDERED receipts
(`_untranslated_aggregate_r2.json`, 14 screens, zh arm).  For each distinct string in that arm this script
answers one question - where does it come from - and proves the answer with a coordinate:

  BARE_LITERAL_IN_COMPONENT  found as a literal in a .tsx/.ts OTHER than the dictionary
                             => never wired to i18n.  This is the product defect.
  DICTIONARY_LITERAL         found inside `i18n/LocaleContext.tsx`
                             => the key exists; either the component did not call t(), or the zh dictionary
                                has no counterpart.  Reported separately, not merged with the above.
  DATA_OR_API                not found in frontend/src at all, but found in the seed data
                             (`data/mock/*.json` or `backend/app/services.py`)
                             => English by design; a zh catalogue is a data question, not an i18n bug.
  UNEXPLAINED                in none of the three.  Printed, never silently dropped.

Read-only.  ASCII summary to stdout; UTF-8 table to a file (this box's console is GBK and a `·` in a matched
literal killed an earlier run).
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AGG = sys.argv[1] if len(sys.argv) > 1 else r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\_untranslated_aggregate_r2.json"
SRC = sys.argv[2] if len(sys.argv) > 2 else r"D:\moodle\_qoder_cmdr_scan_8a7665be\frontend\src"
DATAROOT = sys.argv[3] if len(sys.argv) > 3 else r"D:\moodle\_qoder_cmdr_scan_8a7665be"
OUTJSON = sys.argv[4] if len(sys.argv) > 4 else r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\_copy_origin_r2.json"

DICT_REL = "i18n/LocaleContext.tsx"


def walk(root, exts):
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ("node_modules", "dist", ".git")]
        for f in fn:
            if f.endswith(exts):
                out.append(os.path.join(dp, f))
    out.sort()
    return out


src_files = walk(SRC, (".tsx", ".ts"))
# the seed-data side is `data/` (json) plus the demo itinerary literals in `backend/app/services.py`.
# Both were exported at the SAME sha as frontend/src, so a DATA_OR_API verdict is provable, not assumed.
data_files = walk(os.path.join(DATAROOT, "data"), (".json",)) + walk(os.path.join(DATAROOT, "backend"), (".py",))
print("source files:", len(src_files), "| data files considered:", len(data_files))

src_text = {}
for f in src_files:
    rel = os.path.relpath(f, SRC).replace("\\", "/")
    src_text[rel] = io.open(f, encoding="utf-8", errors="replace").read()

data_text = {}
for f in data_files:
    try:
        data_text[os.path.relpath(f, DATAROOT).replace("\\", "/")] = io.open(f, encoding="utf-8", errors="replace").read()
    except OSError as e:
        print("  data file unreadable:", f, e)

agg = json.load(io.open(AGG, encoding="utf-8"))
strings = sorted({e["text"] for e in (agg.get("defect") or []) + (agg.get("non_defect") or [])
                  if e.get("zh_screens")})
meta = {e["text"]: e for e in (agg.get("defect") or []) + (agg.get("non_defect") or [])}
print("distinct strings seen in the zh arm:", len(strings))


def find_literal(needle, texts):
    """Return [(relpath, line, quoted_form)] for every literal in `texts` equal to needle."""
    hits = []
    forms = ['"%s"', "'%s'", "`%s`"]
    for rel, body in texts.items():
        lines = body.split("\n")
        for i, ln in enumerate(lines):
            for form in forms:
                cand = form % needle
                if cand in ln:
                    hits.append({"file": rel, "line": i + 1, "form": cand})
        # interpolated templates: `${n} hard need(s) ...` will not match an exact literal,
        # so also try the literal's own text as a substring of a template literal
        if not hits and "`" in body and needle:
            head = needle.split(" ")[0]
            for i, ln in enumerate(lines):
                if "`" in ln and head in ln and len(needle.split(" ")) > 2:
                    hits.append({"file": rel, "line": i + 1, "form": "template-substring(%s)" % head})
    return hits


rows = []
for s in strings:
    comp = {k: v for k, v in src_text.items() if k != DICT_REL}
    in_comp = find_literal(s, comp)
    in_dict = find_literal(s, {DICT_REL: src_text.get(DICT_REL, "")}) if DICT_REL in src_text else []
    in_data = []
    for f, body in data_text.items():
        if s and s in body:
            ln = next((i + 1 for i, l in enumerate(body.split("\n")) if s in l), None)
            in_data.append({"file": f, "line": ln})
    if in_comp:
        bucket = "BARE_LITERAL_IN_COMPONENT"
    elif in_dict:
        bucket = "DICTIONARY_LITERAL"
    elif in_data:
        bucket = "DATA_OR_API"
    else:
        bucket = "UNEXPLAINED"
    m = meta.get(s, {})
    rows.append({
        "text": s,
        "bucket": bucket,
        "r1_bucket": m.get("bucket"),
        "zh_screens": m.get("zh_screens") or [],
        "component_hits": in_comp[:6],
        "component_hit_count": len(in_comp),
        "dictionary_hits": in_dict[:4],
        "data_hits": in_data[:4],
    })

order = {"BARE_LITERAL_IN_COMPONENT": 0, "DICTIONARY_LITERAL": 1, "DATA_OR_API": 2, "UNEXPLAINED": 3}
rows.sort(key=lambda r: (order[r["bucket"]], r["text"]))
counts = {}
for r in rows:
    counts[r["bucket"]] = counts.get(r["bucket"], 0) + 1

res = {
    "generated_by": "_copy_origin_r2.py",
    "input_aggregate": os.path.basename(AGG),
    "source_tree": SRC,
    "distinct_zh_visible_strings": len(strings),
    "counts": counts,
    "rows": rows,
    "verdict": ("HARDCODED_COPY_ON_ZH_SCREENS" if counts.get("BARE_LITERAL_IN_COMPONENT") else
                "NO_HARDCODED_COPY_ON_ZH_SCREENS"),
}
with io.open(OUTJSON, "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=1)

lines = ["COPY ORIGIN r2 - where each English string on a zh screen comes from",
         "source tree: %s" % SRC,
         "distinct strings visible in the zh arm: %d" % len(strings), ""]
for b in ("BARE_LITERAL_IN_COMPONENT", "DICTIONARY_LITERAL", "DATA_OR_API", "UNEXPLAINED"):
    lines.append("== %s: %d ==" % (b, counts.get(b, 0)))
    for r in rows:
        if r["bucket"] != b:
            continue
        lines.append("  %r" % r["text"])
        lines.append("      zh screens: %s | r1 said: %s" % (",".join(r["zh_screens"]) or "-", r["r1_bucket"]))
        for h in (r["component_hits"] or r["dictionary_hits"] or r["data_hits"])[:3]:
            lines.append("      at %s:%s" % (h.get("file"), h.get("line")))
    lines.append("")
lines.append("VERDICT " + res["verdict"])
TXT = OUTJSON.replace(".json", ".txt")
with io.open(TXT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

print("counts:", json.dumps(counts, ensure_ascii=False))
print("VERDICT", res["verdict"])
print("wrote", OUTJSON, os.path.getsize(OUTJSON), "B")
print("wrote", TXT, os.path.getsize(TXT), "B")
