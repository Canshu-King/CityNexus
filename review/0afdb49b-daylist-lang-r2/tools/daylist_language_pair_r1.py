"""Compare two day-list walk arms by what the dictionary itself says a segment is.

Why not "count latin runs": the plan's activity line is `role · place · role · place`, and the places on
this deployment are English because the provider says so.  A latin run is therefore not the defect -- the
defect is a *routing token* reaching a Chinese screen in its machine form.  So this tool reads the role
table the product already owns (frontend/src/i18n/travelerLabels.ts, ROLE_LABELS) and classifies every
rendered segment by that table: a segment whose normalised form is a key in the table is a routing token,
and it is a LEAK only when what the screen shows is not the table's own Chinese label.  A segment the
table does not know is a place name and stays out of the count -- with its count printed separately, so
"nothing left to fix" can never be claimed on the strength of what this arm cannot see.

No literal verdicts: every number is recomputed from the two evidence files in this run.

argv: python daylist_language_pair_r1.py <before.json> <after.json> <travelerLabels.ts> <out.json>
"""
import json
import os
import re
import sys

ROLE_BLOCK = re.compile(r"const ROLE_LABELS: Record<string, Label> = \{(.*?)\n\};", re.S)
ROLE_ROW = re.compile(r'^\s{2}([A-Z0-9_]+):\s*\{\s*zh:\s*"([^"]*)"\s*,\s*en:\s*"([^"]*)"\s*\}', re.M)


def role_table(ts_path):
    text = open(ts_path, encoding="utf-8").read()
    m = ROLE_BLOCK.search(text)
    if not m:
        raise SystemExit("ABORT_ROLE_TABLE_UNPARSEABLE -- " + ts_path)
    rows = ROLE_ROW.findall(m.group(1))
    if len(rows) < 10:
        raise SystemExit("ABORT_ROLE_TABLE_THIN -- only %d rows parsed, the regex is wrong" % len(rows))
    return {k: {"zh": zh, "en": en} for k, zh, en in rows}


def key_of(segment):
    return re.sub(r"[\s-]+", "_", segment.strip()).upper()


def lines_of(doc):
    out = {}
    for step in doc.get("steps", []):
        for line in (step.get("day_cards") or []) + (step.get("activity_rows") or []):
            txt = (line.get("text") or "").strip()
            if txt:
                out.setdefault(txt, {"site": line.get("site"), "stops": []})["stops"].append(step.get("tag"))
    return out


def classify(texts, table):
    # The table is keyed by the machine token, but the screen shows either that token or the table's own
    # Chinese.  Looking a Chinese label up by its own key finds nothing, which made the first cut of this
    # ruler report translated_segments=0 on an arm whose screen plainly said 入住/过夜/退房.
    by_zh = {v["zh"]: k for k, v in table.items()}
    rows = []
    for txt, meta in sorted(texts.items()):
        segs = []
        for raw in txt.split("·"):
            seg = raw.strip()
            if not seg:
                continue
            hit = table.get(key_of(seg))
            if seg in by_zh:
                kind, label = "ROUTING_TOKEN_IN_CHINESE", seg
            elif hit is None:
                kind, label = "NOT_IN_ROLE_TABLE", None
            elif seg == hit["zh"]:
                kind, label = "ROUTING_TOKEN_IN_CHINESE", hit["zh"]
            elif seg == hit["en"]:
                kind, label = "ROUTING_TOKEN_LEAK", hit["zh"]
            else:
                # a table row whose Chinese is not what rendered, and whose English is not either:
                # counted as a leak because the screen shows something the table does not sanction.
                kind, label = "ROUTING_TOKEN_LEAK", hit["zh"]
            segs.append({"segment": seg, "kind": kind, "table_zh": label,
                         "latin": bool(re.search(r"[A-Za-z]", seg))})
        rows.append({"text": txt, "site": meta["site"], "seen_at_stops": sorted(set(meta["stops"])),
                     "segments": segs,
                     "leaks": [s["segment"] for s in segs if s["kind"] == "ROUTING_TOKEN_LEAK"],
                     "translated": [s["segment"] for s in segs if s["kind"] == "ROUTING_TOKEN_IN_CHINESE"],
                     "unknown": [s["segment"] for s in segs if s["kind"] == "NOT_IN_ROLE_TABLE"]})
    return rows


def main():
    before_p, after_p, labels_p, out_p = sys.argv[1:5]
    table = role_table(labels_p)
    before = json.load(open(before_p, encoding="utf-8"))
    after = json.load(open(after_p, encoding="utf-8"))
    if before.get("schema") != after.get("schema"):
        raise SystemExit("ABORT_ARMS_DIFFERENT_INSTRUMENTS %s vs %s"
                         % (before.get("schema"), after.get("schema")))
    rb = classify(lines_of(before), table)
    ra = classify(lines_of(after), table)

    def agg(rows):
        return {"lines": len(rows),
                "lines_with_leak": sum(1 for r in rows if r["leaks"]),
                "leak_segments": sum(len(r["leaks"]) for r in rows),
                "translated_segments": sum(len(r["translated"]) for r in rows),
                "unknown_segments": sum(len(r["unknown"]) for r in rows)}
    ab, aa = agg(rb), agg(ra)
    doc = {"schema": "CNX_DAYLIST_LANGUAGE_PAIR_R1", "role_table_rows": len(table),
           "instrument_schema": before.get("schema"),
           "base_before": before.get("base"), "base_after": after.get("base"),
           "verdict_before": before.get("verdict"), "verdict_after": after.get("verdict"),
           "before": ab, "after": aa, "rows_before": rb, "rows_after": ra,
           "place_names_still_english": sorted({s["segment"] for r in ra for s in r["segments"]
                                                if s["kind"] == "NOT_IN_ROLE_TABLE" and s["latin"]}),
           "method": "segment classification against ROLE_LABELS parsed from the product source; "
                     "a segment the table does not know is a place name, not a defect claim",
           "not_claimed": "this pair says nothing about whether the place names themselves should be "
                          "localised, and nothing about screens this walk did not reach"}
    if aa["lines"] == 0:
        raise SystemExit("ABORT_AFTER_ARM_EMPTY -- no line rendered, the pair would be vacuous")
    if ab["lines"] == 0:
        raise SystemExit("ABORT_BEFORE_ARM_EMPTY -- no line rendered, the pair would be vacuous")
    json.dump(doc, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    kv = {"role_table_rows": len(table), "before_lines": ab["lines"],
          "before_leak_lines": ab["lines_with_leak"], "before_leak_segments": ab["leak_segments"],
          "after_lines": aa["lines"], "after_leak_lines": aa["lines_with_leak"],
          "after_leak_segments": aa["leak_segments"],
          "after_translated_segments": aa["translated_segments"],
          "after_unknown_segments": aa["unknown_segments"],
          "place_names_still_english": len(doc["place_names_still_english"])}
    print(" ".join("%s=%s" % (k, v) for k, v in sorted(kv.items())))
    for r in rb:
        print("BEFORE-LEAK %s | %s" % (json.dumps(r["leaks"], ensure_ascii=False), r["text"][:88]))
    for r in ra:
        print("AFTER-LEAK %s | %s" % (json.dumps(r["leaks"], ensure_ascii=False), r["text"][:88]))
    for r in ra:
        print("AFTER-LINE %s | %s" % (json.dumps(r["translated"], ensure_ascii=False), r["text"][:88]))


if __name__ == "__main__":
    main()
