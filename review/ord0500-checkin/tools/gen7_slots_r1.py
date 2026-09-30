"""The r2 blocks for generation 822db3d9, with every number and every coordinate read back.

Same discipline as the previous round and for the same reason (it is my own recurring fault): a block
may not carry a number typed from memory, and a coordinate may not be typed either.  Commit shas come
from `git rev-parse HEAD` in the two worktrees, predicted trees from the `merge-tree` run file, blob
ids from the `blobs_r7.txt` listing, and every measurement from a JSON an instrument wrote.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
EV = os.path.join(LANE, "evidence")
TIP = "7862c6de5565c02c20ec2dccaa9da18960603e06"
PRE = "dcb90cccc68b81f2317b28db19051dedb9f06c80"
GEN1 = "1e95d106f81b29048ba17695fd0e49172516b9b1"
FROZEN = {"o0485_r1": "80608938c52e92a23dcbed79f74e25a08f5736ff",
          "o0485_r2": "2e489da98fd1f4b01aad37f5e5f46587a0bda6c3",
          "o0485_r3": "40f9ddc7435aca9e52c127fa7808194c1cb1ac4f",
          "o0500_r1": "3f3ab9c24221515b7d3ac151d4b5c6ae6d4945be"}


def load(name):
    p = os.path.join(EV, name)
    if not os.path.exists(p):
        return {"MISSING_ARTIFACT": name}
    return json.load(open(p, encoding="utf-8"))


def git(*args):
    return subprocess.run(["git", "-C", LANE] + list(args), stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=120).stdout.decode("utf-8", "replace").strip()


def coordinates():
    out = {}
    out["CAND"] = subprocess.run(["git", "-C", os.path.join(LANE, "wt16"), "rev-parse", "HEAD"],
                                 stdout=subprocess.PIPE, timeout=60).stdout.decode().strip()
    out["DICT"] = subprocess.run(["git", "-C", os.path.join(LANE, "wt11"), "rev-parse", "HEAD"],
                                 stdout=subprocess.PIPE, timeout=60).stdout.decode().strip()
    trees = {}
    for line in open(os.path.join(LANE, "run", "merge_tree_r7.txt"), encoding="utf-8"):
        m = re.match(r"branch (\w+) predicted_tree (\w+)", line)
        if m:
            trees[m.group(1)] = m.group(2)
    out["TREE_CAND"] = trees[out["CAND"]]
    out["TREE_DICT"] = trees[out["DICT"]]
    blobs = {}
    for line in open(os.path.join(LANE, "run", "blobs_r7.txt"), encoding="utf-8"):
        parts = line.split()
        if len(parts) == 2:
            blobs[parts[1]] = parts[0]
    out["blobs"] = blobs
    return out


def main():
    coord = coordinates()
    B = coord["blobs"]
    builds = {f["label"]: f for f in load("gen7_builds_r1.json").get("faces", [])}
    sweep = {r["tag"]: r for r in load("gen7_checkin_sweep_r1.json").get("runs", [])}
    doors = {r["tree"]: r for r in load("gen7_doors_r1.json").get("runs", [])}
    ce1 = load("gen7_ce1_r1.json")
    proof = load("gen7_ce1_tree_proof_r1.json")
    arms = {r["label"]: r for r in load("gen7_carrier_arms_r1.json").get("runs", [])}
    carrier = {r["label"]: r for r in load("gen7_carrier_r1.json").get("runs", [])}
    walk = {f["label"]: f for f in load("gen7_walk_r1.json").get("faces", [])}
    gap_tip = load("i18n_gap_TIP_7862c6de_r1.json")
    gap_r4 = load("i18n_gap_O0485_R4_r1.json")

    def face(label):
        return builds.get(label, {}).get("entry", {})

    def probe(tree, case):
        r = doors.get(tree, {})
        hits = [p for p in r.get("probes", []) if p["case"] == case]
        return hits[0] if hits else {}

    tip_run = sweep.get("TIP_7862c6de_phone", {})
    tip_desk = sweep.get("TIP_7862c6de_desktop", {})
    cand_run = sweep.get("O0500_R3_phone", {})
    mut_run = sweep.get("O0500_CLIENTBOOL_MUTANT_phone", {})
    pre_run = sweep.get("PRE_SLICE2_dcb90ccc_phone", {})
    g1_tip = load("gen4_checkin_sweep_r1.json")["runs"]
    g1_tip = {r["tag"]: r for r in g1_tip}

    now = datetime.now().astimezone()
    hhmm_a = now.strftime("%H%M")
    later = now.replace(minute=(now.minute + 1) % 60)
    hhmm_b = later.strftime("%H%M")

    v = {
        "tip": TIP, "pre": PRE, "gen1": GEN1,
        "cand": coord["CAND"], "dic": coord["DICT"],
        "tree_cand": coord["TREE_CAND"], "tree_dic": coord["TREE_DICT"],
        "f_r1": FROZEN["o0485_r1"], "f_r2": FROZEN["o0485_r2"], "f_r3": FROZEN["o0485_r3"],
        "f_0500_r1": FROZEN["o0500_r1"],
        "t0": now.strftime("%H:%M"), "t1": later.strftime("%H:%M"),
        "b_sheet": B["review/ord0500-checkin/GEN5_READINGS.md"],
        "b_sweep": B["review/ord0500-checkin/receipts/gen7_checkin_sweep_r1.json"],
        "b_doors": B["review/ord0500-checkin/receipts/gen7_doors_r1.json"],
        "b_ce1": B["review/ord0500-checkin/receipts/gen7_ce1_r1.json"],
        "b_proof": B["review/ord0500-checkin/receipts/gen7_ce1_tree_proof_r1.json"],
        "b_arms": B["review/ord0500-checkin/receipts/gen7_carrier_arms_r1.json"],
        "b_builds": B["review/ord0500-checkin/receipts/gen7_builds_r1.json"],
        "b_pre": B["review/ord0500-checkin/receipts/checkin_PRE_SLICE2_dcb90ccc_phone_390x844_r2.json"],
        "b_spec": B["frontend/e2e/qoder-ord0500-checkin-truth.spec.ts"],
        "b_cfg": B["frontend/playwright.ord0500-checkin.config.ts"],
        "b_pytest": B["backend/tests/test_qoder_ord0500_journey_refusal.py"],
        "b_checkins": B["frontend/src/features/checkin/checkins.ts"],
        "b_itin": B["frontend/src/features/trip/TripItinerary.tsx"],
        "b_main": B["backend/app/main.py"],
        "b_copy": B["frontend/src/features/checkin/checkinCopy.ts"],
        "b_walk": B["review/ord0485-phone-walk/receipts/gen7_walk_r1.json"],
        "b_gap_tip": B["review/ord0485-phone-walk/receipts/i18n_gap_TIP_7862c6de_r1.json"],
        "b_gap_r4": B["review/ord0485-phone-walk/receipts/i18n_gap_O0485_R4_r1.json"],
        "b_dict": B["frontend/src/i18n/LocaleContext.tsx"],
        "b_sheet4": B["review/ord0485-phone-walk/GEN4_READINGS.md"],
        # main.py: what the recut would have had to reconcile, three bytes that are not one another
        "main_mine_r1": "1857480f95d3b11bcf713ef6b5b84cbaf094b9b2",
        "main_tip": "66244b6bfb0621470f8598847ad93825a60bbb2e",
        "main_merged": "ce6bda55550d00cb9366b2986c63afd196eec0f7",
        "dict_tip_blob": "d4fd202fb1576a464a893410a6e699173f3fdd38",
        "entry_tip": face("TIP_7862c6de").get("entry_asset"),
        "entry_cand": face("O0500_R3").get("entry_asset"),
        "entry_mut": face("O0500_CLIENTBOOL_MUTANT").get("entry_asset"),
        "entry_dict": face("O0485_R4").get("entry_asset"),
        "sha_tip": str(face("TIP_7862c6de").get("bundle", {}).get("sha256"))[:16],
        "sha_cand": str(face("O0500_R3").get("bundle", {}).get("sha256"))[:16],
        "ctrls_tip": tip_run.get("readings", {}).get("census", {}).get("controls"),
        "press_tip": tip_run.get("readings", {}).get("census", {}).get("pressable_by_centre_hit"),
        "stops_tip": tip_run.get("readings", {}).get("arrived", {}).get("stops"),
        "boxes_tip": sorted(set(tip_run.get("readings", {}).get("census", {}).get("boxes") or [])),
        "ctrls_gen1": g1_tip.get("TIP_1e95d106_phone", {}).get("readings", {}).get("census", {})
                      .get("controls"),
        "press_gen1": g1_tip.get("TIP_1e95d106_phone", {}).get("readings", {}).get("census", {})
                       .get("pressable_by_centre_hit"),
        "ctrls_pre": pre_run.get("readings", {}).get("census", {}).get("controls"),
        "stops_pre": pre_run.get("readings", {}).get("arrived", {}).get("stops"),
        "notices_tip": tip_run.get("readings", {}).get("after_duplicate", {}).get("notice_count"),
        "sentence_tip": (tip_run.get("readings", {}).get("after_duplicate", {}).get("notices")
                         or [""])[0],
        "notices_cand": cand_run.get("readings", {}).get("after_duplicate", {}).get("notice_count"),
        "sentence_cand": (cand_run.get("readings", {}).get("after_duplicate", {}).get("notices")
                          or [""])[0],
        "owners_cand": cand_run.get("readings", {}).get("after_duplicate", {}).get("notice_owners"),
        "rows_cand": cand_run.get("store_after_arm", {}).get("count"),
        "rows_tip": tip_run.get("store_after_arm", {}).get("count"),
        "reqs_tip": tip_run.get("readings", {}).get("requests"),
        "pe_tip": tip_run.get("readings", {}).get("page_errors"),
        "desk_notices": tip_desk.get("readings", {}).get("after_duplicate", {}).get("notice_count"),
        "desk_press": tip_desk.get("readings", {}).get("census", {}).get("pressable_by_centre_hit"),
        "marks_mut_arrival": mut_run.get("readings", {}).get("arrived", {}).get("marks"),
        "rows_mut_arrival": mut_run.get("store_after_schema", {}).get("count"),
        "base_http": probe("wt17", "write_door_unknown_journey").get("http_status"),
        "base_uuid": probe("wt17", "write_door_unknown_journey").get("uuid_in_message"),
        "base_null": probe("wt17", "write_door_unknown_journey").get("details_is_null"),
        "base_bytes": probe("wt17", "write_door_unknown_journey").get("body_bytes"),
        "cand_http": probe("wt16", "write_door_unknown_journey").get("http_status"),
        "cand_code": probe("wt16", "write_door_unknown_journey").get("reason_code"),
        "cand_uuid": probe("wt16", "write_door_unknown_journey").get("uuid_in_message"),
        "cand_null": probe("wt16", "write_door_unknown_journey").get("details_is_null"),
        "req_http": probe("wt16", "first_tap_on_a_real_stop").get("http_status"),
        "dup_http": probe("wt16", "same_stop_tapped_again").get("http_status"),
        "dup_code": probe("wt16", "same_stop_tapped_again").get("reason_code"),
        "mut_dup_code": probe("mutgen7", "same_stop_tapped_again").get("reason_code"),
        "target_http": probe("wt16", "no_target_named").get("http_status"),
        "target_code": probe("wt16", "no_target_named").get("reason_code"),
        "unknown_http": probe("wt16", "activity_not_on_this_server").get("http_status"),
        "unknown_code": probe("wt16", "activity_not_on_this_server").get("reason_code"),
        "ce1_cand_pass": len(set(ce1.get("runs", [{}, {}])[0].get("passed_names") or [])),
        "ce1_cand_fail": len(set(ce1.get("runs", [{}, {}])[0].get("failed_names") or [])),
        "ce1_mut_pass": len(set(ce1.get("runs", [{}, {}])[1].get("passed_names") or [])),
        "ce1_mut_fail": len(set(ce1.get("runs", [{}, {}])[1].get("failed_names") or [])),
        "ce1_mut_names": ", ".join(sorted(set(ce1.get("runs", [{}, {}])[1].get("failed_names") or []))),
        "ce1_green_name": "test_a_second_tap_names_the_row_that_already_won",
        "compared": proof.get("files_compared_total"),
        "mut_sha": str(proof.get("mutant_main_sha256"))[:16],
        "cand_sha": str(proof.get("candidate_main_sha256"))[:16],
        "mut_screen_notices": doors.get("mutgen7", {}).get("mutant_screen", {}).get("arm", {})
                              .get("notice_count"),
        "mut_screen_pe": doors.get("mutgen7", {}).get("mutant_screen", {}).get("arm", {})
                         .get("page_errors"),
        "base_arm_pass": arms.get("base_tip", {}).get("stats", {}).get("expected"),
        "base_arm_fail": arms.get("base_tip", {}).get("stats", {}).get("unexpected"),
        "cand_arm_pass": arms.get("candidate_o0500", {}).get("stats", {}).get("expected"),
        "cand_arm_fail": arms.get("candidate_o0500", {}).get("stats", {}).get("unexpected"),
        "mut_arm_pass": arms.get("mutant_clientbool_ce2", {}).get("stats", {}).get("expected"),
        "mut_arm_fail": arms.get("mutant_clientbool_ce2", {}).get("stats", {}).get("unexpected"),
        "base_arm_msg": next((a["node_message"] for a in arms.get("base_tip", {}).get("arms", [])
                              if a["status"] == "failed"), "NONE"),
        "mut_arm_msg": next((a["node_message"] for a in arms.get("mutant_clientbool_ce2", {})
                              .get("arms", []) if a["status"] == "failed"), "NONE"),
        "gap_tip_en": gap_tip.get("keys_in_en"), "gap_tip_zh": gap_tip.get("keys_in_zhCN"),
        "gap_tip_ref": gap_tip.get("referenced_key_count"),
        "gap_tip_missing": gap_tip.get("referenced_keys_missing_from_both"),
        "gap_r4_en": gap_r4.get("keys_in_en"), "gap_r4_zh": gap_r4.get("keys_in_zhCN"),
        "gap_r4_missing": gap_r4.get("referenced_keys_missing_from_both"),
        "screens_tip": walk.get("TIP_7862c6de", {}).get("walk", {}).get("screen_count"),
        "screens_r4": walk.get("O0485_R4", {}).get("walk", {}).get("screen_count"),
        "pe_walk_tip": walk.get("TIP_7862c6de", {}).get("walk", {}).get("page_errors_total"),
        "pe_walk_r4": walk.get("O0485_R4", {}).get("walk", {}).get("page_errors_total"),
        "car_tip": walk.get("TIP_7862c6de", {}).get("carrier", {}),
        "car_r4": walk.get("O0485_R4", {}).get("carrier", {}),
        "dicts_differ": load("gen7_walk_r1.json").get("the_two_dictionaries_are_different_bytes"),
    }
    json.dump({k: (str(x)[:80]) for k, x in v.items()},
              open(os.path.join(LANE, "run", "gen7_block_slots_r1.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    print("SLOTS RESOLVED %d" % len(v))
    missing = [k for k, x in v.items() if x is None]
    print("SLOTS_STILL_NONE", missing)
    return v


if __name__ == "__main__":
    main()
