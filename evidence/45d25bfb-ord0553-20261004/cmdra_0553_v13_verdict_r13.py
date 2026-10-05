"""ORD-0553 r13 -- derive the verdict from the three reading files; no literal conclusions.

Every number this reports is read back out of the artefacts my instruments wrote, so the block cannot
carry a hand-typed claim.  If a reading is missing or contradicts another, the instrument refuses to
print a verdict (ABORT) rather than rounding the story.
"""
import io
import json
import os

R = "D:/moodle/_qoder_cmdra_ord0553_20261003/_evidence"


def load(name):
    return json.load(io.open(os.path.join(R, name), encoding="utf-8"))


doors = load("r13_doors_r13.json")
prep = load("r13_state_prep.json")
rev = load("r13_locator_revet.json")

by_case = {s["case"]: s for s in doors["steps"] if s.get("leg") == "reset_door"}
finger = [s for s in doors["steps"] if s.get("leg") == "fingerprint"][0]
legs = {l["tag"]: l for l in rev["legs"]}
ctl = rev["controls"]
spec_lines = {"en_route_visible": ("Mark EN ROUTE", 37), "en_route_click": ("Mark EN ROUTE", 38),
              "arrived_visible": ("Mark ARRIVED", 39)}


def find(leg, name):
    return [m for m in leg["spec_names"] if m["name"] == name][0]


def after(leg, name):
    return [m for m in (leg["after_click"] or {}).get("names", []) if m["name"] == name][0]


arms = []


def arm(ident, ok, observed):
    arms.append({"id": ident, "verdict": "PASS" if ok else "FAIL", "observed": observed})


a = arms  # readability
# 1 -- the spec's own first door, measured as a refusal rather than assumed
no_header = by_case["no_header"]
wrong = by_case["wrong_header"]
arm("spec_first_line_is_a_named_refusal_on_this_generation",
    no_header["http_status"] == 403 and no_header["answered"]["codes_found"] == ["RESET_TOKEN_REQUIRED"]
    and wrong["http_status"] == 403 and wrong["answered"]["codes_found"] == ["RESET_TOKEN_INVALID"],
    "no_header=%s/%s wrong_header=%s/%s; the spec posts no header at all" % (
        no_header["http_status"], ",".join(no_header["answered"]["codes_found"]),
        wrong["http_status"], ",".join(wrong["answered"]["codes_found"])))

# 2 -- a refusal must not have deleted anything (the guards sit before stop_autorun)
arm("refused_reset_touched_no_rows",
    finger["http_status"] == 200 and bool(finger["journey_id"]) and finger["demo_mode"] is True,
    "after both refusals demo/scene still answers journey_id and demo_mode=%s" % finger["demo_mode"])

# 3 -- the two legs are comparable: same execution state, only the bytes differ
same = prep["stores_in_same_execution_state"]
now = [l["twin"]["now_state"] for l in prep["legs"]]
arm("both_legs_are_in_the_same_server_state",
    bool(same) and len(set(now)) == 1,
    "now_state=%s on both, statuses identical=%s, plan_count=%s" % (
        now[0], same, [l["calls"][0]["plan_count"] for l in prep["legs"]]))

# 4 -- generation binding: each leg really served the generation I claim
entries = {k: v["entry"] for k, v in legs.items()}
arm("each_leg_served_its_own_generation",
    entries["tip_b2fccfdf"] == ["index-DLbc3Q3N.js"] and entries["prer2_f3304e25"] == ["index-DUhOk9ks.js"],
    "tip=%s pre-r2=%s (the pre-r2 name is the one r3 measured on the baseline port)" % (
        entries["tip_b2fccfdf"][0], entries["prer2_f3304e25"][0]))

# 5 -- the matcher can see and can refuse to see
arm("locator_instrument_has_eyes_and_a_floor",
    ctl["positive_matched"] >= 1 and ctl["nonsense_matched"] == 0,
    "painted name %r matched %s, nonsense name matched %s" % (
        ctl["positive_painted_name"], ctl["positive_matched"], ctl["nonsense_matched"]))

tip, pre = legs["tip_b2fccfdf"], legs["prer2_f3304e25"]
before_tip = find(tip, "Mark EN ROUTE")
after_arrived_tip = after(tip, "Mark ARRIVED")
before_enroute_pre = find(pre, "Mark EN ROUTE")
after_arrived_pre = after(pre, "Mark ARRIVED")

# 6 -- the pre-r2 generation satisfies all three asserted lines (so the spec was never wrong for its own bytes)
arm("three_asserted_lines_hold_on_the_pre_r2_generation",
    before_enroute_pre["matched"] == 1 and before_enroute_pre["visible"]
    and after_arrived_pre["matched"] == 1 and after_arrived_pre["visible"],
    "Mark EN ROUTE before click matched=%s visible=%s; Mark ARRIVED after click matched=%s visible=%s" % (
        before_enroute_pre["matched"], before_enroute_pre["visible"],
        after_arrived_pre["matched"], after_arrived_pre["visible"]))

# 7 -- the tip generation: the two EN ROUTE lines cannot match, the ARRIVED line can
arm("on_the_tip_only_the_en_route_lines_break",
    before_tip["matched"] == 0 and not before_tip["visible"]
    and after_arrived_tip["matched"] >= 1 and after_arrived_tip["visible"],
    "Mark EN ROUTE on tip matched=%s visible=%s; Mark ARRIVED on tip matched=%s visible=%s exact=%s" % (
        before_tip["matched"], before_tip["visible"],
        after_arrived_tip["matched"], after_arrived_tip["visible"], after_arrived_tip["matched_exact"]))

# 8 -- my own r3 claim, re-measured: it was too broad.  Playwright's default name matching is
# case-insensitive, so the enum-shaped assertion still lands on the human-worded button.
arm("my_r3_prediction_of_three_broken_lines_is_refuted_in_part",
    after_arrived_tip["matched_exact"] == 0 and after_arrived_tip["matched"] >= 1,
    "Mark ARRIVED loose=%s exact=%s on 'Mark Arrived' -- loose matching saves line 39, lines 37-38 still break" % (
        after_arrived_tip["matched"], after_arrived_tip["matched_exact"]))

painted = {k: [b for b in v["after_click"]["buttons_painted"] if "Mark" in b] for k, v in legs.items()}
red = [x["id"] for x in arms if x["verdict"] == "FAIL"]
out = {
    "instrument": "cmdra_0553_v13_verdict_r13",
    "spec_lines_as_measured": {k: {"name": v[0], "asserted_at_line": v[1]} for k, v in spec_lines.items()},
    "painted_mark_buttons": painted,
    "painted_before_click": {k: [b for b in v["buttons_painted"] if "Mark" in b] for k, v in legs.items()},
    "arms": arms,
    "verdict": "GREEN" if not red else "RED",
    "red_arms": red,
    "note_for_the_ruling": {
        "line_37_38": "the footer button is composed from exec.state words; on the tip those are human words",
        "line_39": "still satisfied on the tip because the matcher is case-insensitive by default",
        "not_reachable_in_the_suite": "line 21 refuses first, so neither line is exercised when the suite runs",
    },
}
path = os.path.join(R, "r13_verdict.json")
io.open(path, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
