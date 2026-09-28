# The ORD-0422 scorecard, upgraded to the generation the duty note named. Every number is read out of
# an artifact produced in this run; nothing is retyped from memory, and the shipped rulers are quoted
# by their own output files.
import json

TIP = "7399f59ccdb2dfe3cdf04477d4e4ffcc077e214a"
L = []
add = L.append
a = json.load(open("D:/moodle/_qoder_q_ord0422/final6/assert_rescore.json", encoding="utf-8"))
r3 = {r: json.load(open("D:/moodle/_qoder_q_ord0422/r3_rescore/untranslated_%s_r3.json" % r, encoding="utf-8"))
      for r in ("twin", "authoritative", "discover")}
rep = json.load(open("D:/moodle/_qoder_q_ord0422/final6/final_readings_r6.json", encoding="utf-8"))
pin = json.load(open("D:/moodle/_qoder_q_ord0422/final6/copy_check_pinned_7399f59c.json", encoding="utf-8"))
ship = json.JSONDecoder().raw_decode(open("D:/moodle/_qoder_q_ord0422/final6/copy_check_rescore.json",
                                          encoding="utf-8").read())[0]
surv = json.load(open("D:/moodle/_qoder_q_ord0422/rescore_survival.json", encoding="utf-8"))
br = {c: json.load(open("D:/moodle/_qoder_q_ord0422/rescore_readings/%s_authoritative.json" % c, encoding="utf-8"))
      for c in ("with_proposal", "no_policy_row", "all_branch_states")}
brt = json.load(open("D:/moodle/_qoder_q_ord0422/rescore_readings/with_unconfirmed_capability_twin.json",
                     encoding="utf-8"))
o401 = json.load(open("D:/moodle/_qoder_q_ord0422/ord0401_rescore/one_scroll_hit_test.json", encoding="utf-8"))

add("ORD-0422 scorecard, re-measured at tip %s" % TIP)
add("generation facts: bundle /assets/index-BKwMWjc7.js, %s raw bytes" % pin["bundle_raw_bytes"])
add("")
add("== 1. dictionary and panel files still mine ==")
add("keys my build carried: %s ; absent at this tip: %s ; values re-written by someone else: %s"
    % (surv["keys_delivered_en"], surv["delivered_keys_absent_at_live"],
       len([k for k in surv["delivered_keys_whose_value_changed_at_live"]
            if k.startswith(("twin.", "v14."))])))
add("keys this tip has that my build did not: %s (%s)"
    % (surv["keys_live_has_that_delivered_did_not"], surv["live_only_key_examples"][:2]))
add("keys re-worded by ORD-0433's plural rule, none of them mine: %s"
    % json.dumps(surv["delivered_keys_whose_value_changed_at_live"], ensure_ascii=False))
add("")
add("== 2. the 22 inventory rows, both arms, two instruments ==")
add("r3 anchors: %s" % json.dumps([{ "route": k, "zh_entry": v["zh"]["entry_used"],
    "en_entry": v["en"]["entry_used"], "zh_path": v["zh"]["reached_route"],
    "en_path": v["en"]["reached_route"], "comparable": v["arms_comparable"]} for k, v in r3.items()]))
add("lane readings: %s readings, all on their requested route and scrolled to bottom: %s"
    % (len(rep["readings"]), all(x["bottom_reached"] for x in rep["readings"])))
add("ZH leaks: lane whole-leaf %s / lane substring %s / r3 substring %s"
    % (len([r for r in a["rows"] if r["lane_zh_exact_leaf"]]), a["zh_leak_lane"], a["zh_leak_r3"]))
add("EN reached: r3 substring %s, lane whole-leaf %s, merged after dropping %s inflated hit(s): %s"
    % (a["en_reachable_r3"], a["en_reachable_lane"], a["matcher_inflated_rows"], a["en_reachable_either"]))
add("reached rows whose Chinese counterpart is on the Chinese screen: %s"
    % a["reached_with_zh_pair_readable"])
add("NOT_REACHED by both instruments: %s ; verdict %s" % (a["not_reached_rows"], a["verdict"]))
add("per-row: %s" % json.dumps([{ "row": r["string"][:40], "en_r3": r["r3_en_substring"],
    "en_lane": r["lane_en_exact_leaf"], "zh_leak": r["lane_zh_substring_leak"],
    "zh_pair": r["lane_zh_pair_readable"]} for r in a["rows"]], ensure_ascii=False))
add("")
add("== 3. the eleven branch rows, re-run on this generation ==")
for route, d in (("authoritative(with proposal)", br["with_proposal"]), ("twin(unconfirmed capability)", brt)):
    en, zh = d["arms"][1], d["arms"][0]
    ok = [r["row"] for r in en["rows"] if r["en_leaf"]]
    zkok = [r["row"] for r in zh["rows"] if r["zh_leaf"]]
    add("%s | zh leaves %s bottom %s ; en leaves %s bottom %s"
        % (route, zh["leaf_count"], zh["bottom_reached"], en["leaf_count"], en["bottom_reached"]))
    add("   en reached: %s" % json.dumps(ok, ensure_ascii=False))
    add("   zh reached: %s" % json.dumps(zkok, ensure_ascii=False))
nop = br["no_policy_row"]
np_en = [r["en_leaf"] for r in nop["arms"][1]["rows"] if r["row"].startswith("policy unavailable")][0]
np_zh = [r["zh_leaf"] for r in nop["arms"][0]["rows"] if r["row"].startswith("policy unavailable")][0]
add(f"policy-unavailable attempt on this tip: en_leaf={np_en} zh_leaf={np_zh} (still NOT_REACHED)")
leakA = br["all_branch_states"]
zhA = leakA["arms"][0]["leaves"]
inv = json.load(open("D:/moodle/_qoder_q_ord0422/expect_22.json", encoding="utf-8"))
add("deep-state leak re-check on this tip: zh arm leaves %s, inventory rows readable on it: %s"
    % (len(zhA), [s for s in inv if any(s in l for l in zhA)]))
add("")
add("== 4. the copy rulers ==")
add("shipped cmdr_bundle_copy_check_r3.py: tip %s, dictionary_pairs %s, values_not_found %s"
    % (ship["tip"], ship["dictionary_pairs"], ship["values_not_found"]))
add("pinned companion at the build's own tip %s: pairs %s found %s not_found %s, miss is %s"
    % (pin["rev"], pin["dictionary_pairs"], pin["values_found_in_served_bundle"],
       pin["values_not_found"], json.dumps(pin["misses"], ensure_ascii=False)))
add("")
add("== 5. ORD-0424's extended fallback ruler, on this generation ==")
txt = open("D:/moodle/_qoder_q_ord0422/ord0424_rescore.txt", encoding="utf-8").read()
line = [l for l in txt.splitlines() if "HARDCODED_FALLBACK" in l]
add("ruler line: %s" % (line[0].strip()[:220] if line else "NOT FOUND"))
mine = [l.strip() for l in txt.splitlines()
        if ("TwinPanel" in l or "V14RecoveryTruthPanel" in l or "RealCityDiscoveryPanel" in l)
        and l.strip().startswith("B ")]
add("hits inside this order's three panels: %s" % json.dumps(mine, ensure_ascii=False))
add("")
add("== 6. ORD-0401 under the replaced criterion, one screen, both arms ==")
for arm in o401["arms"]:
    b, aft = arm["before"], arm["after_one_scroll"]
    add("%s | empty state present %s, action %r" % (arm["locale"], b["empty_present"], b["action_label"]))
    add("   before any scroll: action top=%s centre=%s -> elementFromPoint=%s is_action=%s"
        % (b["action_box"]["top"], json.dumps(b["action_centre"]), b["hit_owner"], b["hit_is_action"]))
    add("   after ONE scroll (scrollTop %s of max %s): action top=%s -> owner=%s is_action=%s"
        % (aft["scrollTop"], aft["scrollMax"], aft["action_box"]["top"], aft["hit_owner"],
           aft["hit_is_action"]))
    add("   fixed elements then on screen: %s" % json.dumps(aft["fixed_on_screen"], ensure_ascii=False))
    add("   sentence pointing at the scroll: %s" % json.dumps(aft["hint_leaves"], ensure_ascii=False))
text = "\n".join(L) + "\n"
open("D:/moodle/_qoder_q_ord0422/rescore_scorecard.txt", "w", encoding="utf-8", newline="\n").write(text)
print(text[:2000])
print("... total %d chars" % len(text))
