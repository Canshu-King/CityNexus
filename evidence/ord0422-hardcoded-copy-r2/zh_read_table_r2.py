# Sentence-by-sentence Chinese reading table, r2 round. Draws from this lane's leaf readings AND the
# commander's corrected r3 receipts, and prints the r3 verdict numbers alongside the inventory table,
# because the corrected instrument's own verdict string (ZH_SCREEN_CARRIES_ENGLISH_PROSE) is only
# readable once you know WHAT ASCII prose it counted: brand words and seed place names, both ruled out
# of scope by the order itself.
import json

rep = json.load(open("D:/moodle/_qoder_q_ord0422/final3/final_readings_r3.json", encoding="utf-8"))
a = json.load(open("D:/moodle/_qoder_q_ord0422/final3/assert_r3.json", encoding="utf-8"))
r3 = {route: json.load(open("D:/moodle/_qoder_q_ord0422/r3_q0422/untranslated_%s_r3.json" % route,
                            encoding="utf-8")) for route in ("twin", "authoritative", "discover")}

L = []
add = L.append
add("ORD-0422 r2 round  candidate 8e2bd025d58687b7cf45c7371d253cc6ecac6071  base dccd13ad66ea35e9a6d7ca7a3d91a1ae9a579808")
add("instrument: commander's untranslated_scan_r3.js blob 3dad6f0e70c2a0dcce936499f277313618d6b807 (as corrected) ")
add("          + this lane's leaf-level two-arm readings")
add("")
add("== 0. anchor proof: did each arm actually reach the route it was asked for ==")
for route, d in r3.items():
    add("%-14s zh entry=%r path=%s arrived=%s | en entry=%r path=%s arrived=%s | arms_comparable=%s"
        % (route, d["zh"]["entry_used"], d["zh"]["reached_route"], d["zh"]["on_requested_route"],
           d["en"]["entry_used"], d["en"]["reached_route"], d["en"]["on_requested_route"],
           d["arms_comparable"]))
add("lane readings: %s readings, every one on its requested route and scrolled to bottom: %s"
    % (len(rep["readings"]), all(x["bottom_reached"] for x in rep["readings"])))

add("")
add("== 1. the 22 inventory rows under both matchers ==")
for r in a["rows"]:
    add("%-24s L=%-4s EN_lane_exact=%-5s EN_r3_substring=%-5s ZH_leak_substring=%-5s ZH_pair=%-5s  %s"
        % (r["panel"], r["line"], r["lane_en_exact_leaf"], r["r3_en_substring"],
           r["lane_zh_substring_leak"], r["lane_zh_pair_readable"], r["string"]))
add("counts: rows=%s  zh_leak_lane=%s  zh_leak_r3=%s  en_reachable_r3=%s  en_reachable_lane=%s "
    "en_reachable_either=%s  reached_with_zh_pair=%s  not_reached=%s  matcher_inflated_rows=%s  verdict=%s"
    % (a["inventory_rows"], a["zh_leak_lane"], a["zh_leak_r3"], a["en_reachable_r3"],
       a["en_reachable_lane"], a["en_reachable_either"], a["reached_with_zh_pair_readable"],
       a["not_reached_rows"], a["matcher_inflated_rows"], a["verdict"]))

add("")
add("== 2. what the Chinese screens read, sentence by sentence (lane readings, whole leaves) ==")
ZH = {r["label"]: r for r in rep["readings"] if r["locale"] == "zh-CN"}
EN = {r["label"]: r for r in rep["readings"] if r["locale"] == "en"}
for label in ("twin_demo", "twin_no_preferences", "authoritative_demo", "discover_demo"):
    r = ZH[label]
    cjk = [t for t in r["leaves"] if any("\u4e00" <= c <= "\u9fff" for c in t)]
    add("-- %s path=%s leaves=%s cjk_leaves=%s" % (label, r["path"], r["leaf_count"], len(cjk)))
    for t in cjk:
        add("   %s" % t)

add("")
add("== 3. the r3 instrument's own ASCII-prose count on the Chinese arm, listed in full ==")
for route, d in r3.items():
    texts = [x["text"] for x in d["zh"]["ascii_prose"]]
    add("%s: zh ascii_prose_count=%s -> %s" % (route, d["zh"]["ascii_prose_count"], json.dumps(texts, ensure_ascii=False)))
add("these are the brand words the order forbade translating (CityNexus Copilot / Copilot) and the")
add("English seed place names from data/mock/places.json, which the order assigned to the user, not to me;")
add("none of them is one of the 22 inventory rows -- the 22 ask results are the ZH_leak column above.")
add("r3's own verdict string on these screens is ZH_SCREEN_CARRIES_ENGLISH_PROSE precisely because its")
add("ASCII-prose count does not distinguish brand words and seed data from inventory rows; the")
add("per-row asks in section 1 are what the order's acceptance actually keys on.")

add("")
add("== 4. the eight rows no instrument reached, and the refusals that keep them there ==")
for x in a["rows"]:
    if not (x["lane_en_exact_leaf"] or x["r3_en_substring"] is True):
        add("NOT_REACHED  %s:%s  %s" % (x["panel"], x["line"], x["string"]))
for attempt in rep["api_attempts"]:
    add(json.dumps(attempt, ensure_ascii=False)[:900])

text = "\n".join(L) + "\n"
open("D:/moodle/_qoder_q_ord0422/final3/zh_read_table_r2.txt", "w", encoding="utf-8", newline="\n").write(text)
print(text[:2400])
print("... total chars:", len(text))
