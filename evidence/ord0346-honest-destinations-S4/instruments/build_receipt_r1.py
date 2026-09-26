"""ORD-0346 S4: the receipt.  Every verdict below is computed from an artefact in this directory.

No string in a `verdict` position is written by hand: each one is derived here from the reading, the
panel evidence, or the ruler output it cites, so a claim stops being printed when the artefact that
earned it stops agreeing.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import time

WORK = os.path.dirname(os.path.abspath(__file__))
RULER = os.path.join(os.path.dirname(WORK), "ui_exposure_taint_ast_r3.cjs")
TREE = "D:/moodle/_qoder_ord0346_S4"
BRANCH = "review/S4-ord0346-honest-cities"
COMMIT = "021898bb8d15f0075077a04b87b151b2ee6790a2"
GEN = "c740f45d68f337c460a1a43b995162689d0110af"
BORROWED_PORTS = [8000, 4173, 4174, 4185, 4193, 4411, 4781, 4782, 8464, 8474, 8476, 8494, 8499, 8693]


def artifact(*parts):
    return json.load(io.open(os.path.join(WORK, *parts), encoding="utf-8"))


def sha1_of_bytes(path):
    return hashlib.sha1(io.open(path, "rb").read()).hexdigest()


def blob_at(commit, path_in_repo):
    return subprocess.run(["git", "-C", TREE, "rev-parse", "%s:%s" % (commit, path_in_repo)],
                          capture_output=True, text=True).stdout.strip()


def cells(ruler_output):
    return {"%s@%s:%s" % (h.get("rule"), (h.get("file") or "").replace("\\", "/").split("/")[-1],
                          h.get("line")) for h in (ruler_output.get("hits") or [])}


def count_specs(node, found=None):
    found = 0 if found is None else found
    if isinstance(node, dict):
        if "specs" in node and isinstance(node["specs"], list):
            found += len(node["specs"])
        for value in node.values():
            found = count_specs(value, found)
    elif isinstance(node, list):
        for value in node:
            found = count_specs(value, found)
    return found


facts = artifact("fact_sheet_r1.json")
reading = artifact("capability_reading_r1.json")
ruler_before = artifact("ruler_before_r1.json")
ruler_after = artifact("ruler_after_r1.json")
ruler_pair = artifact("ruler_control_pair_r1.json")
tree_before = artifact("ruler_tree_before.json")
tree_after = artifact("ruler_tree_after.json")
panel_zh = artifact("evidence", "ord0346", "panel-zh-read.json")["panel"]
panel_en = artifact("evidence", "ord0346", "panel-en-read.json")["panel"]
panel_unread = artifact("evidence", "ord0346", "panel-unread.json")["panel"]
before_text = artifact("evidence_before", "ui-overnight", "wizard-supported.json")
after_text = artifact("evidence", "ui-overnight", "wizard-supported.json")
e2e_proofs = artifact("e2e_run_proofs_085647.json")
report = artifact("report-all-arms.json")

measured = facts["measured_against_the_server"]
difference = facts["set_difference"]
row = lambda panel, spelling: next(r for r in panel["rows"] if r["spelling"] == spelling)
groups_of = lambda panel: {r["spelling"]: r["group"] for r in panel["rows"]}

beijing, tokyo, xiamen = (row(panel_zh, name) for name in ("北京", "东京", "厦门"))

# The words the capability route is allowed to emit, read out of the generation's own source.
capability_py = subprocess.run(["git", "-C", TREE, "show", "%s:backend/app/anywhere_capability.py" % GEN],
                               capture_output=True, text=True).stdout
allowed_tokens = set()
for name in ("CAPABILITY_STATES", "COVERAGE_STATES"):
    allowed_tokens |= set(re.findall(r'"([A-Z_]+)"', re.search(r"^%s = \(([^)]*)\)" % name, capability_py, re.M).group(1)))
allowed_tokens |= set(re.findall(r'^(?:REASON_|ACTION_)[A-Z_]+ = "([A-Z_]+)"', capability_py, re.M))
on_screen_tokens = sorted({str(token) for panel in (panel_zh, panel_en) for row_ in panel["rows"]
                           for token in (row_["capability"], row_["reasonCode"], row_["action"]) if token})
new_tokens = [token for token in on_screen_tokens if token not in allowed_tokens]

numstat = subprocess.run(["git", "-C", TREE, "diff", "--numstat", "%s..%s" % (GEN, COMMIT)],
                         capture_output=True, text=True).stdout.strip().splitlines()
diff_rows = [{"path": parts[2], "added_lines": int(parts[0]), "removed_lines": int(parts[1])}
             for line in numstat for parts in [line.split("\t")]]

ports_used = [reading["server"]["port"], e2e_proofs["backend_port"], e2e_proofs["frontend_port"]]

R = {
    "schema": "CNX_CMDR_S4_ORD0346_RECEIPT_V1",
    "order": "ORD-0346",
    "lane": "S4-ast-taint (1d64acf5)",
    "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "generation_pinned": GEN,
    "delivered_branch": BRANCH,
    "delivered_commit": COMMIT,
    "delivered_blobs": {d["path"]: blob_at(COMMIT, d["path"]) for d in diff_rows},
    "change_footprint": {
        "files": diff_rows,
        "total_added_lines": sum(d["added_lines"] for d in diff_rows),
        "total_removed_lines": sum(d["removed_lines"] for d in diff_rows),
    },

    "requirement_1_facts": {
        "asked": "the screen's data source and every route/field it reads, named to file:line, plus a real reading for the 11-vs-8 difference",
        "screen_file": facts["screen"]["file"],
        "control_at_line": facts["screen"]["control_line"],
        "list_rendered_at_lines": facts["screen"]["list_rendered_at"],
        "data_source": facts["screen"]["source_table"],
        "derived_list": facts["screen"]["derived_list"],
        "routes_read_before_this_change": facts["screen"]["routes_read_by_the_screen_before_this_change"],
        "server_vocabulary_table": facts["server_side"]["vocabulary_table"],
        "capability_route": facts["server_side"]["capability_route"],
        "identity_field": facts["server_side"]["identity_field"],
        "resolver_seam": facts["server_side"]["resolver_seam"],
        "advertised_spellings_zh": difference["advertised_zh"],
        "advertised_count": difference["advertised_zh_spellings"],
        "backend_vocabulary_count": facts["server_side"]["vocabulary_codes"],
        "in_both": difference["in_both"],
        "in_both_count": difference["in_both_count"],
        "advertised_but_absent_from_the_backend_vocabulary": difference["advertised_but_not_in_the_backend_vocabulary"],
        "in_the_backend_vocabulary_but_not_advertised": difference["in_the_backend_vocabulary_but_not_advertised"],
        "server_named": measured["named_by_the_server"],
        "server_unnamed": measured["not_named"],
        "capability_READY": measured["capability_READY"],
        "reading_artifact": "capability_reading_r1.json",
        "fact_sheet_artifact": "fact_sheet_r1.json",
        "verdict_derivation": {
            "advertised_minus_absent_equals_intersection": difference["advertised_zh_spellings"]
            - len(difference["advertised_but_not_in_the_backend_vocabulary"]) == difference["in_both_count"],
            "the_server_agrees_with_the_vocabulary_intersection": sorted(measured["named_by_the_server"])
            == sorted(difference["in_both"]),
            "the_unnamed_are_exactly_the_absent": sorted(measured["not_named"])
            == sorted(difference["advertised_but_not_in_the_backend_vocabulary"]),
            "the_screen_read_no_route_at_all": facts["screen"]["routes_read_by_the_screen_before_this_change"] == [],
            "the_control_and_the_list_are_named_to_lines": bool(facts["screen"]["control_line"])
            and bool(facts["screen"]["list_rendered_at"]),
        },
    },

    "requirement_2_three_groups": {
        "asked": "group the screen by server capability, existing vocabulary only, no new word list",
        "groups_rendered": [g["key"] for g in panel_zh["groups"]],
        "group_titles": {g["key"]: g["title"] for g in panel_zh["groups"]},
        "group_rules_printed_on_screen": {g["key"]: g["rule"] for g in panel_zh["groups"]},
        "membership": groups_of(panel_zh),
        "counts_per_group": {key: sum(1 for value in groups_of(panel_zh).values() if value == key)
                             for key in ("supported", "needs_lookup", "unknown")},
        "server_tokens_used_on_screen": on_screen_tokens,
        "tokens_the_route_never_emits": new_tokens,
        "tokens_the_route_may_emit": sorted(allowed_tokens),
        "verdict_derivation": {
            "three_groups_in_the_named_order": [g["key"] for g in panel_zh["groups"]]
            == ["supported", "needs_lookup", "unknown"],
            "every_offered_name_is_placed": len(panel_zh["rows"]) == difference["advertised_zh_spellings"],
            "each_group_names_its_own_rule_on_screen": all(g["rule"].strip() for g in panel_zh["groups"]),
            "no_new_word_list": new_tokens == [],
            "all_three_groups_are_populated_or_say_so": all(
                sum(1 for value in groups_of(panel_zh).values() if value == key) > 0
                or any(g["key"] == key and g["empty"] for g in panel_zh["groups"])
                for key in ("supported", "needs_lookup", "unknown")),
        },
        "judgement_call_for_the_commander": (
            "「已支持」is implemented as the server's READY verdict, or a canonical identity with catalogue rows "
            "behind it; with the shipped demo seed that is 北京, and the seven vocabulary-only names fall to "
            "未知或无数据.  A READY-only reading of the same heading is measured too: capability_READY is %s, so under "
            "that rule the first group would print 「这一轮没有名字落在这一组。」.  Every row carries the server's own "
            "token beside it, so the heading is checkable name by name." % json.dumps(measured["capability_READY"])),
    },

    "requirement_3_identity_column": {
        "asked": "no unresolved:<hash>-shaped placeholder in the identity column; a named 还没有身份 instead",
        "server_identity_values_seen": facts["identity_column"]["identity_values_seen"],
        "server_pending_key_values_seen": facts["identity_column"]["destination_pending_key_values_seen"],
        "placeholder_shaped_values_anywhere_in_the_answers": facts["identity_column"]["the_values_that_matched"],
        "at_paths": facts["identity_column"]["the_paths_that_matched"],
        "identity_fields_holding_a_placeholder": facts["identity_column"]["identity_fields_holding_any_of_them"],
        "identity_attributes_on_screen": sorted({str(r["identityAttr"]) for r in panel_zh["rows"]}),
        "unnamed_rows_identity_text": sorted({r["identityText"] for r in panel_zh["rows"] if r["identityAttr"] is None}),
        "placeholder_shaped_attributes_on_screen": [
            r["spelling"] for r in panel_zh["rows"] if r["identityAttr"] is not None
            and (not re.match(r"^CN-[A-Z][A-Z_]+$", r["identityAttr"])
                 or re.search(r"unresolved|pending:|pend-|digest|sha1|sha256|hash", r["identityAttr"], re.I))],
        "verdict_derivation": {
            "no_identity_field_carried_a_placeholder_shape": facts["identity_column"]["identity_fields_holding_any_of_them"] == [],
            "every_unnamed_row_says_the_one_named_words": len(sorted(
                {r["identityText"] for r in panel_zh["rows"] if r["identityAttr"] is None})) == 1,
            "nothing_placeholder_shaped_reached_the_dom": [
                r["spelling"] for r in panel_zh["rows"] if r["identityAttr"] is not None
                and not re.match(r"^CN-[A-Z][A-Z_]+$", r["identityAttr"])] == [],
            "a_read_that_never_landed_claims_no_identity": sorted({r["identityText"] for r in panel_unread["rows"]})
            == ["身份还没读到"],
        },
        "found_but_not_mine": (
            'frontend/src/app/V8Experience.tsx:2651 writes data-place-id={row.placeId ?? "unresolved"} on the hub\'s '
            "dropped-candidate row: the same placeholder shape in a machine-readable identity slot, on a screen this "
            "order does not cover, in a file lane D last edited at c1bea4c2 and where the Q64/Q67 split is still open. "
            "Reported for a ruling; not changed here."),
    },

    "requirement_4_two_way_readings": {
        "asked": "one genuinely supported city and one unsupported city, each verified in both directions",
        "supported_leg": {"name": beijing["spelling"], "group": beijing["group"], "identity": beijing["identityAttr"],
                          "server_fields": beijing["fieldsText"], "verdict_line": beijing["verdictText"]},
        "unsupported_leg": {"name": tokyo["spelling"], "group": tokyo["group"],
                            "identity_attribute": tokyo["identityAttr"], "identity_line": tokyo["identityText"],
                            "server_fields": tokyo["fieldsText"]},
        "middle_case": {"name": xiamen["spelling"], "group": xiamen["group"], "identity_line": xiamen["identityText"],
                        "verdict_line": xiamen["verdictText"]},
        "english_membership": groups_of(panel_en),
        "before_panel_text": before_text["list"],
        "after_panel_text_head": after_text["list"],
        "negative_control_reads_that_never_landed": {
            "rows": len(panel_unread["rows"]),
            "claiming_an_answer": sum(1 for r in panel_unread["rows"] if r["answered"] == "yes"),
            "placed_in_supported": [r["spelling"] for r in panel_unread["rows"] if r["group"] == "supported"],
            "supported_group_says": panel_unread["groups"][0]["empty"],
            "device_cause_shown": sorted({r["fieldsText"] for r in panel_unread["rows"]}),
        },
        "verdict_derivation": {
            "the_supported_city_is_not_listed_as_unknown": beijing["group"] == "supported",
            "the_supported_city_identity_is_the_servers_own": beijing["identityAttr"]
            == measured["per_name"]["北京"]["canonical_destination_id"],
            "the_unsupported_city_cannot_claim_supported": tokyo["group"] != "supported",
            "the_unsupported_city_is_where_the_server_puts_it": tokyo["group"] == "needs_lookup"
            and measured["per_name"]["东京"]["capability"] == "UNAVAILABLE",
            "the_supported_group_does_not_contain_the_unsupported_name": tokyo["spelling"] not in
            [r["spelling"] for r in panel_zh["rows"] if r["group"] == "supported"],
            "english_and_chinese_partition_the_same_way": {
                {"Beijing": "北京", "Tokyo": "东京", "Xiamen": "厦门", "Shanghai": "上海", "Tianjin": "天津",
                 "Guangzhou": "广州", "Shenzhen": "深圳", "Chengdu": "成都", "Hangzhou": "杭州",
                 "Fuzhou": "福州", "Singapore": "新加坡"}[name]: group
                for name, group in groups_of(panel_en).items()} == groups_of(panel_zh),
            "a_failed_read_places_nothing_in_the_supported_group": [
                r["spelling"] for r in panel_unread["rows"] if r["group"] == "supported"] == [],
            "the_before_state_carried_no_server_word": all(
                token not in before_text["list"] for token in
                ("HYDRATABLE", "READY", "NO_CANONICAL_IDENTITY", "COVERAGE_INCOMPLETE")),
        },
    },

    "requirement_5_isolation": {
        "asked": "no demo/reset, no _live.db / _preview.db, own port and own sqlite",
        "database_url_named_by_this_lane": reading["server"]["database_url_named_by_this_lane"],
        "how_the_data_got_there": reading["server"]["how_the_data_got_there"],
        "reading_port": reading["server"]["port"],
        "e2e_backend_port": e2e_proofs["backend_port"],
        "e2e_frontend_port": e2e_proofs["frontend_port"],
        "resolver_seam": reading["server"]["resolver_seam"],
        "photon_tripwire": reading["server"]["photon_tripwire"],
        "store_identity_probe": reading["ownership"]["marker_probe"],
        "launcher_process_id": reading["ownership"]["launcher_process_id"],
        "listener_process_id": reading["ownership"]["listener_process_id"],
        "listener_parent_process_id": reading["ownership"]["listener_identity"]["parent_process_id"],
        "listener_command_line": reading["ownership"]["listener_identity"]["command_line"],
        "e2e_listener_after_teardown": e2e_proofs["listener_after_teardown"],
        "e2e_store_identity": e2e_proofs["store_identity"],
        "shared_stores_touched": [],
        "demo_reset_called": False,
        "e2e_guard_refusal_kept_not_worked_around": "e2e_guard_refusal_r1.txt",
        "verdict_derivation": {
            "the_database_is_inside_this_lane's_directory": "_qoder_lane_S4_0926"
            in reading["server"]["database_url_named_by_this_lane"],
            "no_shared_store_is_named_in_the_reading": not any(
                name in json.dumps(reading) for name in ("_live.db", "_preview.db")),
            "the_listener_was_reading_this_lanes_file": reading["ownership"]["marker_probe"]["marker_ids_returned"]
            == [reading["ownership"]["marker_probe"]["marker_id_expected"]],
            "an_absent_code_returned_nothing": reading["ownership"]["marker_probe"]["absent_rows"] == 0,
            "the_e2e_run_proved_the_same_way": e2e_proofs["store_identity"]["marker_id_returned"]
            == [e2e_proofs["store_identity"]["marker_id_expected"]],
            "no_borrowed_port_appears": all(port not in BORROWED_PORTS for port in ports_used),
            "the_backend_was_gone_after_teardown": e2e_proofs["listener_after_teardown"] is None,
            "the_listener_was_this_runs_child": str(reading["ownership"]["launcher_process_id"])
            == str(reading["ownership"]["listener_identity"]["parent_process_id"]),
        },
    },

    "ruler_gate_r6": {
        "instrument": RULER.replace("\\", "/"),
        "instrument_bytes": os.path.getsize(RULER),
        "instrument_blob": "6a251d3a6bea70329e06581384a81d5ef54c96a6",
        "instrument_sha1_of_bytes_not_a_blob": sha1_of_bytes(RULER),
        "per_file_before": {"cells": sorted(cells(ruler_before)), "scope": ruler_before["scope"]},
        "per_file_after": {"cells": sorted(cells(ruler_after)), "scope": ruler_after["scope"]},
        "instrument_alive_in_the_same_run": {"cells": sorted(cells(ruler_pair)),
                                             "files_scanned": ruler_pair.get("files_scanned"),
                                             "targets": [f.split("/")[-1] for f in ruler_pair.get("targets_scanned", [])]},
        "module_graph_before_cells": len(cells(tree_before)),
        "module_graph_after_cells": len(cells(tree_after)),
        "module_graph_only_after": sorted(cells(tree_after) - cells(tree_before)),
        "module_graph_only_before": sorted(cells(tree_before) - cells(tree_after)),
        "scope_note": ruler_after.get("scope_note"),
        "verdict_derivation": {
            "per_file_added_no_cell": len(cells(ruler_after) - cells(ruler_before)) == 0,
            "graph_added_no_cell": len(cells(tree_after) - cells(tree_before)) == 0,
            "graph_lost_no_cell": len(cells(tree_before) - cells(tree_after)) == 0,
            "the_control_run_still_reports_cells": len(cells(ruler_pair)) > 0,
        },
    },

    "gates_run_on_the_delivered_bytes": {
        "typecheck_check": "exit 0 (node node_modules/typescript/bin/tsc -p tsconfig.check.json --noEmit)",
        "typecheck_all": "exit 0 (node node_modules/typescript/bin/tsc -p tsconfig.typecheck.json --noEmit)",
        "playwright_specs_in_the_run": count_specs(report.get("suites", [])),
        "playwright_stats": report.get("stats"),
        "this_order's_spec": "frontend/e2e/qoder-ord0346-honest-destinations.spec.ts (3 arms)",
        "existing_wizard_gates_re_run": ["e2e/qoder-wizard-city-copy.spec.ts (ORD-0060, 3 tests)",
                                         "e2e/qoder-wizard-advanced-is-tappable.spec.ts (ORD-0261/ORD-0264, 2 tests)"],
        "lane_config": "frontend/playwright.ord0346-S4.config.ts",
    },

    "self_faults_and_corrections": [
        "the receipt's first build printed NOT_MET for two requirements because two of its own derivations were "
        "written wrong, not because the screen failed: one looked a group key up in a spelling-keyed map (so it "
        "could never be true), and the other compared the English partition to the Chinese one without translating "
        "the names across. Both are fixed here and the broken first build was not overwritten.",
        "the identity-column structural check first carried a bare `sha` alternative, which matched CN-SHANGHAI and "
        "reddened a valid identity: the instrument was wrong, not the product. Fixed in the spec (the digest words "
        "are now named in full); the failing first run is left in the evidence rather than hidden.",
        "the first attempt at the reading set CITYNEXUS_E2E_RUN_ID, and the product's own guard "
        "(`backend/app/db/session.py:21-45`) refused to boot an identified run on a database that already existed. "
        "The refusal is published as e2e_guard_refusal_r1.txt; the store is identified by the marker-row probe instead.",
        "db_marker_r1.py first called secrets.uuid4(), which does not exist; it failed before writing anything and "
        "was rerun with uuid.uuid4().",
    ],

    "not_measured": [
        "the phone itself: every reading here is on loopback at 390x844 emulation. Functional readings are valid "
        "there; latency readings are not, and no latency number is claimed.",
        "a partial read (some names answered, some not): the code merges per name and the arms cover all-answered "
        "and none-answered only.",
    ],

    "claim_kind": "reading_determined",
    "claimed_result": None,
    "derived_result": None,
    "requirements": {},
}

for key in ("requirement_1_facts", "requirement_2_three_groups", "requirement_3_identity_column",
            "requirement_4_two_way_readings", "requirement_5_isolation", "ruler_gate_r6"):
    derivation = R[key]["verdict_derivation"]
    assert all(isinstance(value, bool) for value in derivation.values()), key
    R[key]["verdict"] = "MET" if all(derivation.values()) else "NOT_MET"
    R[key]["verdict_derivation"] = derivation
R["requirements"] = {key: R[key]["verdict"] for key in
                     ("requirement_1_facts", "requirement_2_three_groups", "requirement_3_identity_column",
                      "requirement_4_two_way_readings", "requirement_5_isolation")}
R["requirements"]["ruler_gate_r6"] = R["ruler_gate_r6"]["verdict"]
counts = R["requirement_2_three_groups"]["counts_per_group"]
R["claimed_result"] = (
    "branch %s @ %s: panel groups %s (supported/needs_lookup/unknown); the server named %d of the %d advertised "
    "names, %d unnamed, %d READY; ruler r6 added %d cells per-file and %d in module-graph mode; requirements %s"
    % (BRANCH, COMMIT[:8], "/".join(str(counts[key]) for key in ("supported", "needs_lookup", "unknown")),
       len(measured["named_by_the_server"]), difference["advertised_zh_spellings"],
       len(measured["not_named"]), len(measured["capability_READY"]),
       len(cells(ruler_after) - cells(ruler_before)), len(cells(tree_after) - cells(tree_before)),
       json.dumps(R["requirements"])))

path = os.path.join(WORK, "receipt_r1.json")
json.dump(R, io.open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({"requirements": R["requirements"],
                  "new_tokens": new_tokens,
                  "ports": ports_used}, ensure_ascii=False))
print(R["claimed_result"])
print("wrote", path, os.path.getsize(path), "bytes")
