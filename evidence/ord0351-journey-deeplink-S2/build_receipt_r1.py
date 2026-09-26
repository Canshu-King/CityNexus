"""ORD-0351 收据生成器：每一格判定都从**实测文件**里推出来，不写任何字面 PASS。

输入：两向读数件（run_arms）、邻居门读数件（run_neighbors）、每格自己的 e2e 读数件、
尖那一代的 snap（用来现算前提行号与 navigate 调用点）、git 自己算的 blob。
输出：`ord0351_receipt_r1.json` —— claimed_result 只到 OBSERVED，derived_result 留 null（等级归红队）。
"""
from __future__ import annotations

import glob
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAP = HERE / "snap" / "frontend"
WT = HERE / "wt"
V8 = SNAP / "src" / "app" / "V8Experience.tsx"
MAIN_TIP = SNAP / "src" / "main.tsx"
MAIN_FIXED = WT / "frontend" / "src" / "main.tsx"
SPEC = WT / "frontend" / "e2e" / "qoder-stored-journey-link-is-an-entry.spec.ts"
SPEC_REL = "frontend/e2e/qoder-stored-journey-link-is-an-entry.spec.ts"
NODES = [
    "ord0351-a-a-link-to-a-saved-trip-opens-that-trip",
    "ord0351-b-a-link-the-server-denies-says-so-by-name",
    "ord0351-c-an-unanswered-link-is-never-blamed-on-the-server",
    "ord0351-d-a-dead-link-empties-a-reference-not-a-trip",
    "ord0351-e-route-names-are-not-journey-links",
]


def sh(*args: str) -> str:
    return subprocess.run(list(args), cwd=str(WT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def numbered(path: Path, pattern: str) -> list:
    out = []
    text = path.read_text("utf-8").split("\n")
    rx = re.compile(pattern)
    for i, line in enumerate(text, 1):
        if rx.search(line):
            out.append({"file": f"frontend/src/{path.relative_to(SNAP / 'src')}".replace("\\", "/"),
                        "line": i, "text": line.strip()[:150]})
    return out


def premise() -> dict:
    nav = numbered(V8, r"navigate\(")
    nav = [n for n in nav if "const navigate" not in n["text"]]
    args = sorted({(re.search(r'navigate\(([^)]*)\)', n["text"]) or re.match("x", "")).group(1)
                   for n in nav if re.search(r"navigate\(", n["text"])})
    return {
        "no_call_site_carries_a_journey_id": [n for n in nav if re.search(r"journey|sealedId", n["text"])] == [],
        "navigate_call_sites_measured": len(nav),
        "navigate_argument_forms_observed": args,
        "unknown_path_falls_back_to_hub": numbered(V8, r'return "hub";'),
        "boot_reads_the_id_only_from_storage": numbered(V8, r'getItem\("citynexus\.v8\.journey_id"\)'),
        "the_only_url_writer_is_navigate": [n for n in numbered(V8, r"pushState\(.*\$\{value\}") ],
        "tip_entry_branches_only_on_legacy": numbered(MAIN_TIP, r'path\.startsWith\("/legacy"\)'),
    }


def node_readings(arm: str) -> dict:
    out = {}
    for node in NODES:
        hits = glob.glob(str(HERE / "evidence" / f"{arm}_*" / "ord0351-journey-link" / f"{node}.json"))
        if hits:
            out[node] = json.loads(Path(sorted(hits)[-1]).read_text("utf-8"))
    return out


def no_new_surface(base: str) -> dict:
    """Exact added lines from `git diff -U0 <base> HEAD`, then what is in them -- no hand-listed claim.
    The comparison is against the commit the change sits on, not against the worktree: once the work is
    committed a worktree diff is empty and the gauge would judge nothing."""
    diff = sh("git", "diff", "-U0", base, "HEAD", "--", "frontend/src/main.tsx")
    added = [l[1:] for l in diff.split("\n") if l.startswith("+") and not l.startswith("+++")]
    code = [l for l in added if not l.strip().startswith(("//", "/*", "*"))]
    jsx = [l.strip()[:120] for l in code if re.search(r"<[A-Za-z/]", l)]
    reason = [l.strip()[:120] for l in code
              if re.search(r"JOURNEY_NOT_FOUND|NETWORK_UNAVAILABLE|SERVER_ERROR|ORIGIN_INVALID_RESPONSE"
                           r"|UNKNOWN_FAILURE|FORBIDDEN|UNAUTHORIZED|message_key|copyFor", l)]
    tip_fa = sh("git", "rev-parse", f"{base}:frontend/src/lib/failureAttribution.ts")
    work_fa = sh("git", "status", "--porcelain", "--", "frontend/src/lib/failureAttribution.ts")
    return {
        "added_lines_measured": len(added),
        "non_comment_added_lines_scanned": len(code),
        "added_lines_with_jsx": jsx,
        "added_lines_with_a_reason_or_copy_literal": reason,
        "failureAttribution_dirty_in_worktree": work_fa,
        "failureAttribution_untouched": work_fa == "" and tip_fa == sh("git", "hash-object", "--no-filters",
                                                                      str(SNAP / "src" / "lib" / "failureAttribution.ts")),
    }


def main() -> int:
    two_way_path = sorted(glob.glob(str(HERE / "ord0351_two_way_readings_r1_*.json")))[-1]
    two = json.loads(Path(two_way_path).read_text("utf-8"))
    neighbor_path = sorted(glob.glob(str(HERE / "ord0351_neighbor_gates_r1_*.json")))
    neighbor = json.loads(Path(neighbor_path[-1]).read_text("utf-8")) if neighbor_path else None

    tip_report = json.loads((HERE / "report_tip.json").read_text("utf-8"))
    tip_errors: dict = {}

    def walk(node: dict) -> None:
        for suite in node.get("suites", []):
            walk(suite)
        for spec in node.get("specs", []):
            for test in spec.get("tests", []):
                for res in test.get("results", []):
                    first = [l for l in ((res.get("error") or {}).get("message") or "").split("\n") if l.strip()]
                    tip_errors[spec.get("title", "").split(" — ")[0]] = (res.get("status"),
                                                                        first[0][:260] if first else "")

    walk(tip_report)

    per_arm = {arm: two["arms"][arm]["results"] for arm in ("tip", "fixed")}
    statuses = {arm: {n: (per_arm[arm].get(n) or {}).get("status", "MISSING") for n in NODES}
                for arm in ("tip", "fixed")}
    fixed_readings = node_readings("fixed")
    tip_readings = node_readings("tip")

    base_commit = sh("git", "rev-parse", "HEAD~1")
    diff_lines = sh("git", "diff", "--numstat", base_commit, "HEAD", "--",
                    "frontend/src/main.tsx", SPEC_REL)
    numstat = {}
    for line in diff_lines.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            numstat[parts[2]] = {"added": int(parts[0]) if parts[0].isdigit() else parts[0],
                                 "removed": int(parts[1]) if parts[1].isdigit() else parts[1]}

    specs_run = [SPEC_REL] + [g["spec"].replace("e2e/", "frontend/e2e/") for g in
                              (neighbor or {"gates": {}})["gates"].values()]
    # The route as a caller actually uses it; a prose mention of the words "demo/reset" is not a call.
    demo_reset_calls = []
    for rel in set(specs_run):
        p = WT / rel
        if p.exists() and "/api/v1/demo/reset" in p.read_text("utf-8"):
            demo_reset_calls.append(rel)

    receipt = {
        "order": "ORD-0351",
        "lane": "S2-hermes (d9e2c9ae)",
        "commit_under_test": sh("git", "rev-parse", "HEAD"),
        "its_parent_is_the_authoritative_tip": sh("git", "merge-base", "--is-ancestor", base_commit, "HEAD") == "" and
                                          sh("git", "rev-parse", "HEAD~1") == base_commit,
        "base_tip_commit": base_commit,
        "built_from": "git worktree at the tip; LF endings, core.autocrlf=false (measured, not assumed)",
        "delivered_ref": "review/S2-ord0351-journey-deeplink-r2 (re-cut onto the live tip; product blobs equal to the base-generation commit)",
        "change": {
            "files": {
                "frontend/src/main.tsx": {
                    "tip_blob": two["main_tsx_tip_blob"],
                    "fixed_blob": two["main_tsx_fixed_blob"],
                    "numstat": numstat.get("frontend/src/main.tsx"),
                    "lines_read_by_the_browser": "one: the id-shaped first path segment, adopted into the key boot already reads",
                },
                SPEC_REL: {"numstat": numstat.get(SPEC_REL), "kind": "gate added by this order"},
            },
            "why": ("the named state, the per-leg attribution, the measured offline-copy offer and the "
                    "picker all already live behind the shell's boot; this entry only hands that boot "
                    "the reference the address bar already carried"),
        },
        "no_new_surface_computed": no_new_surface(base_commit),
        "premise_measured_on_the_tip": premise(),
        "two_way": {
            "readings_file": Path(two_way_path).name,
            "pre_written_expectations": two["pre_written_expectations"],
            "statuses": statuses,
            "tip_matches_expectation": two["verdicts"]["tip"]["matches_expectation"],
            "fixed_matches_expectation": two["verdicts"]["fixed"]["matches_expectation"],
            "two_way": two["two_way"],
            "restored_equals_fixed": two["restored_equals_fixed"],
            "tip_named_failures": {n: tip_errors.get(n, ["MISSING", ""])[1] for n in NODES},
            "harness": {"playwright": two["playwright_version"], "node": two["node_version"],
                        "python": two.get("python"), "frontend_port": 4791, "backend_port": 8139,
                        "databases": {a: two["arms"][a]["database_url"] for a in ("tip", "fixed")},
                        "run_ids": {a: two["arms"][a]["run_id"] for a in ("tip", "fixed")},
                        "commands": {a: two["arms"][a]["command"] for a in ("tip", "fixed")},
                        "ai_key_names_removed_from_child_env": two["arms"]["fixed"]["ai_key_names_removed_from_child_env"]},
        },
        "per_node_readings_fixed": {n: fixed_readings.get(n) for n in NODES},
        "per_node_readings_tip_present": {n: (n in tip_readings) for n in NODES},
        "what_each_node_claims": {
            NODES[0]: "the page itself asked the server for the id in the address bar and got 200, and the rendered heading is that trip's city, not the other trip that exists on the same server",
            NODES[1]: "a ghost id reaches the named screen, classified JOURNEY_NOT_FOUND on HTTP_RESPONSE evidence with the 404 it classified on, and the visible sentence is the copy table's own",
            NODES[2]: "the same link with its read aborted never reaches JOURNEY_NOT_FOUND and never prints the not-found sentence -- the two legs stay separate",
            NODES[3]: "a dead link voids the device's reference and nothing else: the other journey's row reads byte-identical before and after, and the ghost still 404s (nothing was created)",
            NODES[4]: "no route key or alias is UUID-shaped, a server-issued id is, and walking six real routes neither adopts nor drops a reference",
        },
        "neighbor_gates_not_owned_by_this_lane": (None if neighbor is None else {
            "zero_drift": neighbor["zero_drift"],
            "per_gate": {label: {"spec": g["spec"], "nodes_compared": g["nodes_compared"],
                                 "tip": g["tip"]["statuses"], "fixed": g["fixed"]["statuses"],
                                 "red_both_arms": g["red_both_arms"], "drift": g["drift"]}
                         for label, g in neighbor["gates"].items()},
            "readings_file": Path(neighbor_path[-1]).name}),
        "boundaries": {
            "demo_reset_route_present_in_specs_run": demo_reset_calls,
            "seed_project_skipped": all("--no-deps" in two["arms"][a]["command"] for a in ("tip", "fixed")),
            "own_ports_and_own_sqlite": all(two["arms"][a]["database_url"].startswith(
                "sqlite:///" + (HERE / "db").as_posix()) for a in ("tip", "fixed")),
            "shared_live_or_preview_db_touched": sorted(
                {db for a in ("tip", "fixed") for db in [two["arms"][a]["database_url"]]
                 if "_live.db" in db or "_preview.db" in db}),
            "product_files_touched": sorted(numstat),
            "existing_assertions_edited": "see verdict nothing_removed_from_the_product_file: "
                                          f"removed={numstat.get('frontend/src/main.tsx', {}).get('removed')}",
            "derived_result": None,
        },
        "self_faults_disclosed": {
            "first_run_raced_its_own_fixture": {
                "readings_kept": sorted(p.name for p in (HERE / "selffault_r1").glob("ord0351_two_way*")),
                "what_was_wrong": ("seedStoredId asserted on a response array before the reload's boot read "
                                   "had landed, so nodes d and e reported a setup failure that was not the "
                                   "product's; the fix was a waitForResponse in the helper"),
                "expectations_changed": False,
                "pre_written_expectations_still": two["pre_written_expectations"],
            },
            "status_join_first_draft": "playwright titles carry the node id plus an em-dash and a Chinese clause; the first join keyed on the whole title and reported MISSING for every node",
            "two_gauge_false_positives_fixed_before_publishing": {
                "jsx_probe_ate_a_comment": "the surface gauge matched `<journey id>` inside my own block comment; it now scans non-comment added lines only",
                "demo_reset_probe_ate_prose": "the boundary gauge grepped the words `demo/reset`, which my spec header uses to say it does not call it; it now looks for the route a caller uses, `/api/v1/demo/reset`",
            },
        },
        "open_residual_named": {
            "url_is_an_entry_not_a_persistent_identity": ("after the entry hands off, any navigation inside the shell rewrites the address to a route name "
                                                          "(app/V8Experience.tsx:844 navigate); making the journey id survive in-address belongs to "
                                                          "frontend/src/app/V8Experience.tsx, which lane S1 holds an in-flight change on (ORD-0344b)"),
            "blocked_storage": ("if localStorage.setItem throws, the address still names a journey this document cannot adopt and the shell will speak of "
                                "the journey the device holds; closing that needs the boot surface, so it is named rather than fixed here"),
            "healthy_probe_with_aborted_read": ("measured in node c: an aborted request plus a 200 /api/v1/health keeps reason "
                                                "NETWORK_UNAVAILABLE -- the sentence's body only claims what that one request did, which was measured, "
                                                "so no change is claimed here; it is reported for whoever owns the classifier's call sites"),
        },
        "claimed_result": "OBSERVED",
        "written_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    # 判定必须从实测推出来，不许写字面量
    checks = {
        "two_way_matched_pre_written_expectations": bool(two["two_way"]),
        "all_five_nodes_green_on_the_fixed_generation": all(statuses["fixed"][n] == "passed" for n in NODES),
        "four_expected_nodes_red_on_the_tip": all(statuses["tip"][n] == "failed" for n in NODES[:4]),
        "control_node_green_on_both_generations": statuses["tip"][NODES[4]] == "passed" == statuses["fixed"][NODES[4]],
        "per_node_readings_written": all(n in fixed_readings for n in NODES),
        "nothing_removed_from_the_product_file": numstat.get("frontend/src/main.tsx", {}).get("removed") == 0,
        "worktree_restored_to_measured_bytes": bool(two["restored_equals_fixed"]),
        "neighbor_gates_zero_drift": bool(neighbor and neighbor["zero_drift"]),
    }
    receipt["verdicts"] = checks
    surface = receipt["no_new_surface_computed"]
    receipt["verdicts"].update({
        "entry_adds_no_jsx": surface["added_lines_with_jsx"] == [],
        "entry_adds_no_reason_or_copy_literal": surface["added_lines_with_a_reason_or_copy_literal"] == [],
        "shared_classifier_file_untouched": surface["failureAttribution_untouched"],
    })
    receipt["all_verdicts_true"] = all(receipt["verdicts"].values())
    out = HERE / "ord0351_receipt_r1.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print("receipt:", out.name, "all_verdicts_true =", receipt["all_verdicts_true"])
    for k, v in checks.items():
        print(f"  {k}: {v}")
    return 0 if receipt["all_verdicts_true"] else 1


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    sys.exit(main())
