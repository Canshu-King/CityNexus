import io
import json

SRC = r"D:/moodle/_qoder_lane_S4_0926/work/ord0391_census.tsv"
OUT = r"D:/moodle/_qoder_lane_S4_0926/work/ord0391/tier_b_rows.json"
raw = io.open(SRC, encoding="utf-8").read().splitlines()
hdr = raw[9].split("\t")
ti, fi, ffi, si = (hdr.index("tier"), hdr.index("file:line"), hdr.index("fields"),
                   hdr.index("source_line_text"))
rows = []
for line in raw[10:]:
    f = line.split("\t")
    if len(f) <= ti or f[ti].strip() != "b":
        continue
    path, num = f[fi].rsplit(":", 1)
    rows.append({"file": path, "line": int(num), "fields": f[ffi],
                 "interp_before": f[si].count("${") if len(f) > si else 0,
                 "why": f[hdr.index("why")] if len(f) > hdr.index("why") else ""})
# the two V8Experience rows are HELD, not fixed: the standing rule from ORD-0343 is that a further
# change to V8Experience.tsx is reported before it is made, and this order did not lift that rule.
for r in rows:
    if r["file"].endswith("app/V8Experience.tsx"):
        r["held_reason"] = ("ORD-0343 standing rule: V8Experience.tsx is reported-before-touched; the "
                            "order named the row but did not lift the rule, so it is delivered HELD "
                            "with the exact edit I would make")
json.dump(rows, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("tier_b rows", len(rows), "held", len([r for r in rows if "held_reason" in r]),
      "files", len({r["file"] for r in rows}))
