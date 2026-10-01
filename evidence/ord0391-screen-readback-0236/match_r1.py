# -*- coding: utf-8 -*-
"""ORD-0391 screen read-back - match each reworded source line against what a screen actually painted.

The judge is the one the order is about: the line shows a number, and every number on it has to be
introduced by a field name on the same rendered line. So a row counts as read back only when a rendered
text node carries the sentence's own static opening, and the reading then reports the verbatim node text
and whether each quantity inside it is named.
"""
import io
import json
import os
import re
import unicodedata

HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord0391"
TIP = "5a4cdbd26d4a58d6ed6b277480e766ac08b15ded"

targets = json.load(io.open(os.path.join(os.path.dirname(HERE), "ord0391_targets_r1.json"), encoding="utf-8"))
walk = json.load(io.open(os.path.join(HERE, "walk_r1.json"), encoding="utf-8"))


def norm(s):
    s = unicodedata.normalize("NFC", s or "")
    return re.sub(r"\s+", " ", s).strip()


def stem_of(line_src):
    """The static opening of the template literal, up to the first interpolation."""
    m = re.search(r"[\"'`]([^\"'`]*?)\$\{", line_src)
    if not m:
        m = re.search(r"[\"'`]([^\"'`]{8,})[\"'`]", line_src)
        body = m.group(1) if m else ""
    else:
        body = m.group(1)
    return norm(body)


def quantities(line_src):
    """Which field names the reworded line introduces - the thing being verified on screen."""
    return sorted(set(re.findall(r"\b(http_status|content_type|elapsed_ms|bytes|request_id)\b", line_src)))


rows = []
for t in targets["rows"]:
    stem = stem_of(t["added_at_head"])
    fields = quantities(t["added_at_head"])
    hit = None
    for st in walk["states"]:
        for node in (st.get("read") or {}).get("textNodes") or []:
            n = norm(node)
            if stem and n.startswith(stem):
                hit = {"state": st["name"], "scenario": st["scenario"], "locale": st["locale"],
                       "cached": st["cached"], "rendered": n,
                       "node_chars": len(n)}
                break
        if hit:
            break
    named = []
    if hit:
        for f in fields:
            named.append({"field": f, "named_on_screen": bool(re.search(re.escape(f) + r"\s*=", hit["rendered"]))})
    rows.append({
        "file": t["file"], "line_at_tip": t["line_at_tip"], "gone_from_tip": t["gone_from_tip"],
        "stem_used": stem, "fields_required_by_the_line": fields,
        "verdict": "OFF_TIP" if t["gone_from_tip"] else ("ON_SCREEN" if hit else "NOT_SEEN_IN_ANY_STATE"),
        "reading": hit, "field_naming_on_screen": named,
    })

tally = {}
for r in rows:
    tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
# a negative claim has to print its denominator: which states were walked, and what each one painted
states_summary = [{"state": s["name"], "failure_view": s.get("failure_view"),
                   "journey_status": [x["status"] for x in s.get("journey_responses") or []],
                   "text_nodes": len((s.get("read") or {}).get("textNodes") or [])}
                  for s in walk["states"]]
out = {"tip": targets["tip"], "walk_base": walk["base"], "route": walk["states"][0].get("route"),
       "states_walked": walk["states_walked"], "tally": tally, "rows": rows,
       "states_summary": states_summary,
       "judge": "a row is ON_SCREEN only when a rendered text node starts with that line's own static "
                "opening; the reading reports the node verbatim, and field_naming_on_screen says whether "
                "each quantity the line carries is introduced by its field name on the screen"}
io.open(os.path.join(HERE, "match_r1.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps({"rows": len(rows), "tally": tally, "states_walked": walk["states_walked"]},
                 ensure_ascii=False))
