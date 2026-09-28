import json

E = "D:/moodle/_qoder_q_ord0401_evidence/"
tip = json.load(open(E + "hub_reachability_tip-e7286dfd.json", encoding="utf-8"))
cand = json.load(open(E + "hub_reachability_candidate-8b0ea597.json", encoding="utf-8"))


def idx(r):
    return {(a["locale"], a["before_scroll"]["viewport"]["width"]): a for a in r["arms"]}


T, C = idx(tip), idx(cand)
hdr = ("loc", "w", "tip_y", "tip_ctr", "tip_fold", "tip_doc", "cnd_y", "cnd_ctr", "cnd_fold", "cnd_doc",
       "dctr", "wr", "band", "kick", "hitB", "hitA", "anc")
print(f"{hdr[0]:<6}{hdr[1]:>4} | {hdr[2]:>6}{hdr[3]:>8}{hdr[4]:>9}{hdr[5]:>8} | {hdr[6]:>6}{hdr[7]:>8}{hdr[8]:>9}{hdr[9]:>8} | {hdr[10]:>5} {hdr[11]:>6} | {hdr[12]:>5} {hdr[13]:>6} {hdr[14]:>6} {hdr[15]:>6} {hdr[16]:>4}")
for k in sorted(T, key=lambda x: (x[0], x[1])):
    t, c = T[k], C[k]
    tb, cb = t["before_scroll"], c["before_scroll"]
    print(
        f"{k[0]:<6}{k[1]:>4} | {tb['action']['y']:>6}{tb['action_centre']['cy']:>8}{tb['action_px_below_fold']:>9}{tb['document_scroll_height']:>8}"
        f" | {cb['action']['y']:>6}{cb['action_centre']['cy']:>8}{cb['action_px_below_fold']:>9}{cb['document_scroll_height']:>8}"
        f" | {cb['action_centre']['cy'] - tb['action_centre']['cy']:>5} {str(t['api_traffic']['writes']) + '/' + str(c['api_traffic']['writes']):>6}"
        f" | {str(tb['attention_band']['y']):>5} {str(cb['attention_band_kicker']['display']):>6}"
        f" {str(tb['hit_test_matches_action']):>6} {str(c['after_scroll']['hit_test_matches_action']):>6} {len(cb['scrollable_ancestors']):>4}"
    )

print()
for k in sorted(T, key=lambda x: (x[0], x[1])):
    t, c = T[k], C[k]
    tb, cb = t["before_scroll"], c["before_scroll"]
    print(
        k,
        "panel_h", tb["panel"]["h"], "->", cb["panel"]["h"],
        "| note_h", tb["panel_note"] and tb["panel_note"]["h"], "->", cb["panel_note"] and cb["panel_note"]["h"],
        "| empty_row_chars", tb["empty_row"]["text_chars"], "->", cb["empty_row"]["text_chars"], "| empty_text_cand:", repr(cb["empty_row"]["text"][:60]),
        "| dom_order band/panel", cb["dom_order"]["attention_band"], cb["dom_order"]["panel"],
        "| gen", t["generation_assets"], c["generation_assets"],
        "| scroll_doc_px", t["scroll_arm_verdict"]["document_scroll_px"], "->", c["scroll_arm_verdict"]["document_scroll_px"],
        "| kind", c["scroll_arm_verdict"]["scroll_kind"],
        "| count", cb["panel_data_count"],
    )
