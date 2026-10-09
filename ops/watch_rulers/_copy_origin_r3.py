"""r3: classify the ORIGIN of every English string a zh user actually sees - with EVIDENCE STRENGTH.

What r2 got wrong, and why r3 exists:
  * r2 only recognised QUOTED literals.  `Capability needs` is a JSX TEXT NODE
    (`<h3 className="v8-capability-heading">Capability needs</h3>`), so it fell into UNEXPLAINED even though
    it is the single clearest defect in the set.
  * r2's "template-substring" fallback matched on the FIRST WORD plus "the line contains a backtick".  That
    produced coincidental hits: `Nexus River Cruise Pier` -> V14RecoveryTruthPanel.tsx:174 and
    `Tech Art Center` -> PlanWithAiSheet.tsx:170, both of which are really seed data
    (`data/mock/places.json`).  Because r2 tested the component side FIRST, a coincidence masked the true
    origin - i.e. it would have sent a lane after a non-defect.  Fallback deleted.

r3 records, per string, every occurrence in three strength classes and then picks the origin from the
STRONGEST class only:
  EXACT_QUOTED   `"s"` / `'s'` / `` `s` `` appears verbatim
  JSX_TEXT       `>s<` appears verbatim (rendered text node, no literal involved)
  SUBSTRING      the text appears inside a larger literal (e.g. an interpolated template) - weak, and never
                 allowed to outrank a data-file hit

Origin buckets, in the order the evidence is weighed:
  BARE_COPY_IN_COMPONENT  strong hit in a .tsx/.ts other than the dictionary  => never wired to i18n
  DICTIONARY_LITERAL      strong hit inside i18n/LocaleContext.tsx            => key exists; check the zh side
  DATA_OR_API             hit in data/*.json or backend/**.py                 => English by design (seed names)
  BRAND_WORD              in the shipped brand list                           => stays English on purpose
  UNEXPLAINED             none of the above - printed, never dropped

Read-only.  ASCII summary to stdout; UTF-8 table to a file (this box's console is GBK).
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
SHA = sys.argv[4] if len(sys.argv) > 4 else "8a7665be2061a2f38aa2227f81c57003ca4caacb"
OUTJSON = sys.argv[5] if len(sys.argv) > 5 else r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\_copy_origin_r3.json"

DICT_REL = "i18n/LocaleContext.tsx"
BRAND = {"copilot", "citynexus copilot", "cn / ai", "citynexus"}


def walk(root, exts):
    out = []
    if not os.path.isdir(root):
        return out
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ("node_modules", "dist", ".git")]
        for f in fn:
            if f.endswith(exts):
                out.append(os.path.join(dp, f))
    out.sort()
    return out


src_files = walk(SRC, (".tsx", ".ts"))
data_files = walk(os.path.join(DATAROOT, "data"), (".json",)) + walk(os.path.join(DATAROOT, "backend"), (".py",))
print("source files:", len(src_files), "| data files:", len(data_files), "| sha:", SHA)

corpus = {}
for f in src_files:
    rel = "frontend/src/" + os.path.relpath(f, SRC).replace("\\", "/")
    corpus[rel] = io.open(f, encoding="utf-8", errors="replace").read()
for f in data_files:
    rel = os.path.relpath(f, DATAROOT).replace("\\", "/")
    corpus[rel] = io.open(f, encoding="utf-8", errors="replace").read()

agg = json.load(io.open(AGG, encoding="utf-8"))
allrows = (agg.get("defect") or []) + (agg.get("non_defect") or [])
meta = {e["text"]: e for e in allrows}
strings = sorted({e["text"] for e in allrows if e.get("zh_screens")})
print("distinct strings visible in the zh arm:", len(strings))


def occurrences(needle, body):
    """Return (exact_quoted_lines, jsx_text_lines, substring_lines) for one file body."""
    lines = body.split("\n")
    q, j, s = [], [], []
    pats_q = ['"%s"' % needle, "'%s'" % needle, "`%s`" % needle]
    pats_j = [">%s<" % needle, ">%s</" % needle, ">%s}" % needle]
    for i, ln in enumerate(lines):
        if any(p in ln for p in pats_q):
            q.append(i + 1)
        elif any(p in ln for p in pats_j):
            j.append(i + 1)
        elif needle in ln:
            s.append(i + 1)
    return q, j, s


rows = []
for st in strings:
    ev = {"EXACT_QUOTED": [], "JSX_TEXT": [], "SUBSTRING": []}
    for rel, body in corpus.items():
        if st not in body:
            continue
        q, j, s = occurrences(st, body)
        for kind, ls in (("EXACT_QUOTED", q), ("JSX_TEXT", j), ("SUBSTRING", s)):
            for ln in ls:
                ev[kind].append({"file": rel, "line": ln})

    comp_strong = [h for h in ev["EXACT_QUOTED"] + ev["JSX_TEXT"]
                   if h["file"].startswith("frontend/src/") and h["file"] != "frontend/src/" + DICT_REL]
    dict_strong = [h for h in ev["EXACT_QUOTED"] + ev["JSX_TEXT"]
                   if h["file"] == "frontend/src/" + DICT_REL]
    data_hits = [h for h in ev["EXACT_QUOTED"] + ev["JSX_TEXT"] + ev["SUBSTRING"]
                 if not h["file"].startswith("frontend/src/")]
    comp_weak = [h for h in ev["SUBSTRING"]
                 if h["file"].startswith("frontend/src/") and h["file"] != "frontend/src/" + DICT_REL]

    if st.strip().lower() in BRAND:
        bucket = "BRAND_WORD"
    elif comp_strong:
        bucket = "BARE_COPY_IN_COMPONENT"
    elif dict_strong:
        bucket = "DICTIONARY_LITERAL"
    elif data_hits:
        bucket = "DATA_OR_API"
    elif comp_weak:
        bucket = "SUBSTRING_ONLY_IN_COMPONENT"
    else:
        bucket = "UNEXPLAINED"

    m = meta.get(st, {})
    rows.append({
        "text": st,
        "bucket": bucket,
        "r1_shape_bucket": m.get("bucket"),
        "zh_screens": m.get("zh_screens") or [],
        "evidence_strength_used": ("EXACT_QUOTED" if any(h in ev["EXACT_QUOTED"] for h in
                                                          (comp_strong or dict_strong or data_hits))
                                   else "JSX_TEXT" if (comp_strong or dict_strong) else
                                   "SUBSTRING" if data_hits else "NONE"),
        "component_strong": comp_strong[:6],
        "component_strong_count": len(comp_strong),
        "dictionary_strong": dict_strong[:4],
        "data": data_hits[:6],
        "data_count": len(data_hits),
        "component_substring_only": comp_weak[:4],
    })

order = {"BARE_COPY_IN_COMPONENT": 0, "SUBSTRING_ONLY_IN_COMPONENT": 1, "DICTIONARY_LITERAL": 2,
         "DATA_OR_API": 3, "BRAND_WORD": 4, "UNEXPLAINED": 5}
rows.sort(key=lambda r: (order[r["bucket"]], -len(r["zh_screens"]), r["text"]))
counts = {}
for r in rows:
    counts[r["bucket"]] = counts.get(r["bucket"], 0) + 1

# per-file grouping of the real defect bucket, so the order can name the files a lane must touch
by_file = {}
for r in rows:
    if r["bucket"] not in ("BARE_COPY_IN_COMPONENT", "SUBSTRING_ONLY_IN_COMPONENT"):
        continue
    for h in r["component_strong"] or r["component_substring_only"]:
        by_file.setdefault(h["file"], []).append({"text": r["text"], "line": h["line"],
                                                  "strength": "strong" if h in r["component_strong"] else "substring"})

res = {
    "generated_by": "_copy_origin_r3.py",
    "authoritative_sha": SHA,
    "input_aggregate": os.path.basename(AGG),
    "source_tree": SRC,
    "distinct_zh_visible_strings": len(strings),
    "counts": counts,
    "defect_by_file": {k: v for k, v in sorted(by_file.items(), key=lambda kv: -len(kv[1]))},
    "rows": rows,
    "verdict": ("HARDCODED_COPY_ON_ZH_SCREENS" if counts.get("BARE_COPY_IN_COMPONENT")
                else "NO_HARDCODED_COPY_ON_ZH_SCREENS"),
}
with io.open(OUTJSON, "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=1)

lines = ["COPY ORIGIN r3 - where each English string on a zh screen comes from (evidence-strength aware)",
         "authoritative sha: %s" % SHA,
         "source tree: %s" % SRC,
         "distinct strings visible in the zh arm: %d" % len(strings),
         "counts: %s" % json.dumps(counts, ensure_ascii=False), ""]
for b in ("BARE_COPY_IN_COMPONENT", "SUBSTRING_ONLY_IN_COMPONENT", "DICTIONARY_LITERAL",
          "DATA_OR_API", "BRAND_WORD", "UNEXPLAINED"):
    sel = [r for r in rows if r["bucket"] == b]
    lines.append("== %s: %d ==" % (b, len(sel)))
    for r in sel:
        lines.append("  %r" % r["text"])
        lines.append("      zh screens (%d): %s" % (len(r["zh_screens"]), ",".join(r["zh_screens"]) or "-"))
        for h in (r["component_strong"] or r["component_substring_only"] or r["dictionary_strong"]
                  or r["data"])[:3]:
            lines.append("      at %s:%s" % (h["file"], h["line"]))
    lines.append("")
lines.append("== defect grouped by file (what a lane must touch) ==")
for k, v in res["defect_by_file"].items():
    lines.append("  %s  (%d strings)" % (k, len(v)))
    for e in v:
        lines.append("      line %s [%s] %r" % (e["line"], e["strength"], e["text"]))
lines.append("")
lines.append("VERDICT " + res["verdict"])
TXT = OUTJSON.replace(".json", ".txt")
with io.open(TXT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

print("counts:", json.dumps(counts, ensure_ascii=False))
print("defect files:", len(res["defect_by_file"]))
for k, v in list(res["defect_by_file"].items())[:8]:
    print("  %-58s %d" % (k, len(v)))
print("VERDICT", res["verdict"])
print("wrote", OUTJSON, os.path.getsize(OUTJSON), "B")
print("wrote", TXT, os.path.getsize(TXT), "B")
