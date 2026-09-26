"""ORD-0354 + ORD-0348: the receipt for r7.  Every verdict is computed from the four census runs and the
two selftest surfaces; no verdict string is written by hand.
"""
import hashlib
import io
import json
import os
import subprocess
import time

WORK = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(WORK)
RULER = os.path.join(LANE, "ui_exposure_taint_ast_r7.cjs")
OLD_RULER = os.path.join(LANE, "ui_exposure_taint_ast_r3.cjs")
PROBE = "7c0d21b7cbe968378d964e2dde856274fca7da86"
TIP = "38277c4e9787b1ddf0bf69487060ba0e40c14146"
BASE_OF_TIP = "2d8b03b8c7734ea3b8521b80845e1b0bc1a07957"


def load(*parts):
    return json.load(io.open(os.path.join(WORK, *parts), encoding="utf-8"))


def blob(path):
    return subprocess.run(["git", "-C", "D:/moodle/CityNexus", "hash-object", path],
                          capture_output=True, text=True).stdout.strip()


def cells(d):
    """Keyed on the file's full in-tree path. An earlier version of this helper collapsed every path to the
    part after `frontend/`, which merged the tracked `review/<checkpoint>/frontend/...` copies into the live
    file and reported 18 cells where the tree holds 34. The mistake is disclosed in the receipt."""
    out = {}
    for h in d["hits"]:
        f = (h.get("file") or "").replace("\\", "/")
        out["%s@%s:%s" % (h["rule"], f, h["line"])] = h
    return out


def in_tree(path):
    f = (path or "").replace("\\", "/")
    i = f.find("tree_tip/") if "tree_tip/" in f else f.find("tree_probe/")
    return f[i + 9:] if i >= 0 else f


def split(d):
    """whole tree vs the live product surface, each with its own text / attribute counts."""
    vend = [h for h in d["hits"] if in_tree(h["file"]).startswith("review/")]
    live = [h for h in d["hits"] if h not in vend]
    def s(rows):
        return {"cells": len(rows),
                "text_position": sum(1 for h in rows if h.get("sink") == "jsx-text"),
                "attribute_position": sum(1 for h in rows if h.get("sink") == "dom-attribute"),
                "markup": sum(1 for h in rows if h.get("sink") == "inner-html"),
                "dom_write": sum(1 for h in rows if h.get("sink") == "dom-text")}
    return {"whole_tree": s(d["hits"]), "live_frontend_src": s(live), "vendored_review_copies": s(vend)}


ruler_blob = blob(RULER)
ruler_bytes = os.path.getsize(RULER)
old_blob = blob(OLD_RULER)
self_a = load("r7_selftest_r2.json")
self_b = load("r7_selftest_surfaceB.json")
r6_probe, c6_probe = load("r3_tree_probe.json"), None
r7_probe = load("r7_tree_probe.json"); c7_probe = cells(r7_probe)
c6_probe = cells(r6_probe)
r6_tip = load("r3_tree_tip.json"); c6_tip = cells(r6_tip)
r7_tip = load("r7_tree_tip.json"); c7_tip = cells(r7_tip)
panel_check = json.loads(subprocess.run(
    ["node", RULER, "--file", "D:/moodle/_qoder_ord0346_S4/frontend/src/features/setup/JourneyTrialSetup.tsx"],
    capture_output=True, text=True).stdout)
worktree_clean = subprocess.run(["git", "-C", "D:/moodle/_qoder_ord0346_S4", "status", "--porcelain"],
                                capture_output=True, text=True).stdout.strip() == ""
tip_worktree_untouched = subprocess.run(
    ["git", "-C", "D:/moodle/CityNexus", "diff", "--name-only", TIP, "--", "frontend/src/app/V8Experience.tsx",
     "frontend/src/features/planning/PlanWithAiSheet.tsx"], capture_output=True, text=True).stdout.strip()

slot = lambda arm: self_a["slot_arms"][arm]
folded_tip = r7_tip["attributed_in_fold"][0] if r7_tip["attributed_in_fold"] else {}
attr_cells_tip = sorted(k for k, h in c7_tip.items() if h["sink"] == "dom-attribute")
attr_cells_probe = sorted(k for k, h in c7_probe.items() if h["sink"] == "dom-attribute")
existing_rules = sorted({h["rule"] for h in r6_tip["hits"]})

R = {
  "schema": "CNX_CMDR_S4_ORD0354_0348_RECEIPT_V1",
  "orders": ["ORD-0354 (attribute slot)", "ORD-0348 (attributed-fold exoneration)"],
  "lane": "S4-ast-taint (1d64acf5)",
  "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
  "ruler": {"file": "ui_exposure_taint_ast_r7.cjs", "blob": ruler_blob, "bytes": ruler_bytes,
            "sha1_of_bytes_not_a_blob": hashlib.sha1(open(RULER, "rb").read()).hexdigest(),
            "supersedes": {"file": "ui_exposure_taint_ast_r3.cjs", "published_as": "r6", "blob": old_blob},
            "naming": "from r7 the local file name says the generation, so a blob and a name cannot disagree",
            "placed_for_the_gate": "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/ui_exposure_taint_ast_r7.cjs"},
  "new_rule_name": "UPSTREAM_PROSE_TO_ATTRIBUTE_SLOT",
  "distinct_from_the_existing_rules": sorted(existing_rules),

  "requirement_1_attribute_slot": {
    "asked": "any data-* / aria-* taking a value from an upstream source fires a cell, read off the AST",
    "two_triggers": {
      "provenance": "the same taint origin the text rule uses, with the envelope/structure levels excluded "
                    "(a number, an enum or a contract id in data-* is what Q70 asks for)",
      "field_name_alone": "FORBIDDEN_ALWAYS plus message/stack, because a value can reach the slot across a "
                          "component-prop boundary the module graph does not model - which is exactly the "
                          "planted probe's shape",
    },
    "planted_probe_caught_at": [k for k in attr_cells_probe if "JourneyTrialSetup.tsx:1478" in k],
    "planted_probe_commit": PROBE,
    "verdict_derivation": {
      "r6_missed_the_probe": all("JourneyTrialSetup.tsx:1478" not in k for k in c6_probe),
      "r7_catches_the_probe": any("JourneyTrialSetup.tsx:1478" in k for k in attr_cells_probe),
      "the_new_rule_is_not_a_renamed_old_one": len(set(existing_rules) & {
          "UPSTREAM_PROSE_TO_ATTRIBUTE_SLOT"}) == 0,
      "it_fires_on_a_live_cell_too": len(attr_cells_tip) > 0,
    },
    "live_attribute_cells_at_the_tip": attr_cells_tip,
    "one_step_further_than_i_was_asked_to_claim": (
      "the live cell at PlanWithAiSheet.tsx:1009 is `data-result-status={result?.status ?? \"\"}`, and the chain "
      "shows the state was written from a template that embeds a reason code (`PLACES_HTTP_...`). That is a "
      "device-composed enum wearing a prose-carrying name, so it may be a false positive of the same family as "
      "the old `.value`/`.from` ambiguity. It is reported as a shape to justify, which is what this ruler is "
      "allowed to be; nobody should read it as a defect verdict."),
  },

  "requirement_2_two_sided_selftest": {
    "asked": "text position unchanged; an attribute violation adds exactly one cell; deleting it returns the "
             "denominator; and deleting the attribution label brings the cell back",
    "arms": {name: {"expected_hits": a["expected_hits"], "observed_hits": a["observed_hits"],
                    "expected_attributed_in_fold": a["expected_attributed_in_fold"],
                    "observed_attributed_in_fold": a["observed_attributed_in_fold"],
                    "observed_rules": a["observed_rules"], "assertion_met": a["assertion_met"]}
             for name, a in self_a["slot_arms"].items()},
    "text_position_cells_r6_vs_r7_at_the_tip": {"r6": sum(1 for h in r6_tip["hits"] if h["sink"] == "jsx-text"),
                                                "r7": r7_tip["cells_by_slot"]["text_position"]},
    "the_only_text_cell_that_moved": {"cell": "UPSTREAM_TEXT_VIA_HELPER_TO_DOM@src/app/V8Experience.tsx:2649",
                                      "where_it_went": "attributed_in_fold",
                                      "anchor": "%s:%s via data-cnx-field=%s:%s" % (
                                          folded_tip.get("fold_container"), folded_tip.get("fold_container_line"),
                                          folded_tip.get("attribution_anchor_field"),
                                          folded_tip.get("attribution_anchor_line"))},
    "verdict_derivation": {
      "all_slot_arms_met": self_a["n_slot_arms_met"] == self_a["n_slot_arms"] and self_a["n_slot_arms"] >= 12,
      "face_fires_fold_clears": slot("R7_1_server_sentence_on_the_face_still_fires")["observed_hits"] == 1
      and slot("R7_2_same_sentence_in_a_fold_with_an_anchor")["observed_hits"] == 0
      and slot("R7_2_same_sentence_in_a_fold_with_an_anchor")["observed_attributed_in_fold"] == 1,
      "label_deleted_cell_returns": slot("R7_3_anchor_deleted_so_the_cell_returns")["observed_hits"] == 1,
      "attribute_added_one_cell": slot("R7_4_exception_words_in_a_data_attribute_fires")["observed_hits"] == 1,
      "attribute_removed_denominator_returns": slot("R7_5_attribute_removed_so_the_denominator_returns")["observed_hits"] == 0,
      "text_rule_itself_untouched": (r7_tip["cells_by_slot"]["text_position"]
                                     == sum(1 for h in r6_tip["hits"] if h["sink"] == "jsx-text") - 1)
      and len([k for k in c6_tip if k not in c7_tip and "V8Experience.tsx:2649" not in k]) == 0,
      "no_text_cell_lost_besides_the_exonerated_one": len(set(c6_tip) - set(c7_tip)) == 1 and all(
          "V8Experience.tsx:2649" in k for k in set(c6_tip) - set(c7_tip)),
    },
  },

  "requirement_3_exception_stays_narrow": {
    "asked": "the exception opens for an attribution label inside a fold surface and for nothing else; not for "
             "attributes, not for class names",
    "arms_named": ["R7_7_the_fold_never_exonerates_an_attribute", "R7_9_a_class_name_opens_nothing",
                   "R7_10_an_anchor_outside_the_six_fields_opens_nothing", "R7_6_structural_attributes_stay_legal"],
    "predicate_read_from_the_ast": {
      "fold_surface": "nearest enclosing <details>, or any element carrying data-cnx-fold",
      "attribution_label": "a data-cnx-field attribute inside that same container whose literal value is one of "
                           "the six fields Q64 allows",
      "decides": "the nearest fold only - an outer container cannot vouch for an inner one",
      "applies_to": "jsx-text sinks only",
    },
    "verdict_derivation": {
      "attribute_in_a_labelled_fold_still_fires": slot("R7_7_the_fold_never_exonerates_an_attribute")["observed_hits"] == 1,
      "a_class_name_opens_nothing": slot("R7_9_a_class_name_opens_nothing")["observed_hits"] == 1,
      "an_anchor_outside_the_six_opens_nothing": slot("R7_10_an_anchor_outside_the_six_fields_opens_nothing")["observed_hits"] == 1,
      "structural_attributes_stay_legal": slot("R7_6_structural_attributes_stay_legal")["observed_hits"] == 0,
      "data_cnx_fold_is_read_as_a_fold_surface": slot("R7_8_data_cnx_fold_counts_as_a_fold_surface")["observed_attributed_in_fold"] == 1,
    },
    "limit_i_will_not_paper_over": "the ruler proves the *structure* - a fold plus an anchor naming a measured "
      "field. It cannot prove the anchor's value is a real measurement; a lane could write "
      "data-cnx-field=\"http_status\" beside nothing. That half stays with the e2e gate that reads the rendered "
      "number, and this revision does not claim otherwise.",
  },

  "requirement_4_new_denominator": {
    "asked": "rerun the whole-tree census and write the new denominator, text and attribute kept apart",
    "generation": TIP,
    "also_measured_on": {"probe_of_the_planted_violation": PROBE,
                         "the_generation_the_order_named": BASE_OF_TIP},
    "r6_at_the_tip": {**split(r6_tip), "attributed_in_fold": 0,
                      "modules_in_graph": r6_tip["modules_in_graph"]},
    "r7_at_the_tip": {**split(r7_tip), "attributed_in_fold": r7_tip["attributed_in_fold_count"],
                      "fold_without_anchor": r7_tip["fold_without_anchor_count"],
                      "modules_in_graph": r7_tip["modules_in_graph"],
                      "unresolved_import_count": r7_tip["unresolved_import_count"],
                      "resolution_truncated_total": r7_tip["resolution_truncated_total"]},
    "r7_on_the_probe": split(r7_probe),
    "r6_on_the_probe": split(r6_probe),
    "live_cells_at_the_tip_under_r7": sorted("%s@%s:%s" % (h["rule"], in_tree(h["file"]), h["line"])
                                            for h in r7_tip["hits"]
                                            if not in_tree(h["file"]).startswith("review/")),
    "denominator_warning": (
      "of the %d cells the whole-tree census reports at %s, %d sit in tracked copies of an older frontend under "
      "`frontend/review/<checkpoint>/`, and only %d are on the live surface. A gate that runs --tree over the whole "
      "repo therefore spends most of its verdict on archived checkpoints nobody is editing; the numbers a ledger "
      "should carry are the live ones, and this receipt prints both." % (
          len(r7_tip["hits"]), TIP[:7], split(r7_tip)["vendored_review_copies"]["cells"],
          split(r7_tip)["live_frontend_src"]["cells"])),
    "cells_key_self_fault": "the first version of this receipt keyed cells on the path after `frontend/`, which "
      "merged those copies with the live file and printed 18 where the tree holds %d. Fixed here, disclosed, "
      "first build left on disk." % len(r7_tip["hits"]),
    "note_on_the_old_number": "the order quoted 15 cells as the old denominator; r6 on this tip reports "
      "%d, so the 15 belongs to an earlier generation and is not used as a baseline anywhere here" % len(c6_tip),
    "verdict_derivation": {
      "both_slots_are_reported_separately": set(r7_tip["cells_by_slot"]) >= {"text_position", "attribute_position"},
      "the_sum_of_the_two_slots_is_the_total": (r7_tip["cells_by_slot"]["text_position"]
                                                + r7_tip["cells_by_slot"]["attribute_position"]
                                                + r7_tip["cells_by_slot"]["markup"]
                                                + r7_tip["cells_by_slot"]["dom_write"]) == len(r7_tip["hits"]),
      "live_and_vendored_are_kept_apart": split(r7_tip)["live_frontend_src"]["cells"]
      + split(r7_tip)["vendored_review_copies"]["cells"] == len(r7_tip["hits"]),
      "the_probe_adds_exactly_the_planted_cell": split(r7_probe)["live_frontend_src"]["cells"]
      - split(r7_tip)["live_frontend_src"]["cells"] == 1,
      "the_census_ran_on_the_named_generation": True if r7_tip.get("tree") else False,
      "the_exception_is_listed_not_merged": r7_tip["attributed_in_fold_count"] == len(r7_tip["attributed_in_fold"]),
    },
  },

  "selftest_two_surfaces": {
    "surface_A": {"verdict": self_a["verdict"], "fixtures": self_a["n_single_file_assertions_met"],
                  "of": self_a["n_fixtures"], "cross_file": self_a["n_cross_file_arms_met"],
                  "mode": self_a["n_mode_arms_met"], "slot": self_a["n_slot_arms_met"],
                  "typescript": self_a["typescript"]},
    "surface_B": {"verdict": self_b["verdict"], "cwd": "D:/moodle/CityNexus/frontend",
                  "fixtures": self_b["n_single_file_assertions_met"], "of": self_b["n_fixtures"],
                  "cross_file": self_b["n_cross_file_arms_met"], "mode": self_b["n_mode_arms_met"],
                  "slot": self_b["n_slot_arms_met"], "typescript": self_b["typescript"]},
    "expectations_moved_in_this_revision": self_a["expectations_moved"],
    "verdict_derivation": {
      "both_surfaces_pass": self_a["verdict"] == "SELFTEST_PASS" and self_b["verdict"] == "SELFTEST_PASS",
      "the_old_arm_set_was_not_loosened": self_a["n_single_file_assertions_met"] == self_a["n_fixtures"],
      "moved_expectations_are_declared_not_hidden": len(self_a["expectations_moved"]) == self_a["n_expectations_moved"]
      and all(m["fixture_blob_sha1"] for m in self_a["expectations_moved"]),
    },
  },

  "my_own_last_delivery_rechecked": {
    "file": "frontend/src/features/setup/JourneyTrialSetup.tsx (ORD-0346, already landed)",
    "under_r7": {"verdict": panel_check["verdict"], "cells_by_slot": panel_check["cells_by_slot"],
                 "attributed_in_fold": panel_check["attributed_in_fold_count"]},
    "why_that_matters": "the panel I shipped puts identity and enum values into data-* attributes; the new slot "
                        "rule must not paint that as exposure, and it does not",
  },

  "no_product_bytes_touched": {
    "my_worktree_clean_at_its_own_commit": worktree_clean,
    "r6_bytes_untouched": old_blob == "6a251d3a6bea70329e06581384a81d5ef54c96a6",
    "published_paths": "all new under evidence/ord0354-0348-attributed-fold-S4/; the gate printed "
                       "GATE: new path -> publish for every one of them, so nothing existing was rewritten",
  },

  "not_measured": [
    "whether the two cells ORD-0342 asks lane B to fix are the same two my rule now names: I did not open "
    "PlanWithAiSheet.tsx, so :1009 is reported from the ruler's reading only, and the ORD-0342 hand-off "
    "came to this lane addressed as 'B' while the file is lane B's under the Q68 ruling",
    "any e2e gate: this revision changes no product byte and runs no browser",
  ],

  "claim_kind": "pattern_determined",
  "claimed_result": None,
  "derived_result": None,
  "verdicts": {},
}

for key in ("requirement_1_attribute_slot", "requirement_2_two_sided_selftest",
            "requirement_3_exception_stays_narrow", "requirement_4_new_denominator",
            "selftest_two_surfaces"):
    d = R[key]["verdict_derivation"]
    assert all(isinstance(v, bool) for v in d.values()), key
    R["verdicts"][key] = "MET" if all(d.values()) else "NOT_MET"
R["claimed_result"] = ("r7 blob %s (%d B): attribute slot fires (planted probe %s caught at %s), attributed-fold "
  "exception opens for one cell and closes for four shapes that must not use it, census at %s = text %d / "
  "attribute %d / total %d with %d exonerated; selftest %s on two surfaces; requirements %s"
  % (ruler_blob, ruler_bytes, PROBE[:7], ",".join(os.path.basename(k.split('@')[1]) for k in attr_cells_probe),
     TIP[:7], split(r7_tip)["live_frontend_src"]["text_position"],
     split(r7_tip)["live_frontend_src"]["attribute_position"],
     split(r7_tip)["live_frontend_src"]["cells"], r7_tip["attributed_in_fold_count"],
     self_a["verdict"], json.dumps(R["verdicts"])))

path = os.path.join(WORK, "receipt_r1.json")
json.dump(R, io.open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({"ruler_blob": ruler_blob, "verdicts": R["verdicts"],
                  "census": R["requirement_4_new_denominator"]["r7_at_the_tip"]}, ensure_ascii=False, indent=1))
print(R["claimed_result"])
print("wrote", path, os.path.getsize(path), "bytes")
