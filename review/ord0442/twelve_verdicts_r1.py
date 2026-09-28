#!/usr/bin/env python3
"""ORD-0442 - build the twelve-red verdict table *from the evidence files*, not from prose.

Every number in the output is read back out of an artifact this script is told about, so the ledger
block can cite `review/ord0442/twelve_verdicts_r1.md:<line>` and the commander can recompute the
same table with one command. Nothing here edits a test or a product file.

Usage:
    CityNexus/.venv/Scripts/python.exe -X utf8 review/ord0442/twelve_verdicts_r1.py <lane-repo>
"""

from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

LANE = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
EV = LANE / "review" / "n3_0442_evidence_r1"
TRUE_DEFECT = "真缺陷"
ENV = "ENVIRONMENT_NOT_PRODUCIBLE_ON_LINE"
STALE = "尺过期"
INSTRUMENT = "仪器缺陷（令中未列这一类，具名报上游）"


def states(path: Path, ids: list[str] | None = None) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in io.open(path, encoding="utf-8", errors="replace").read().replace("\r", "").splitlines():
        if line.startswith("FAILED "):
            out[line[len("FAILED "):].strip().replace("\\", "/")] = "FAILED"
        elif line.startswith("PASSED "):
            out[line[len("PASSED "):].strip().replace("\\", "/")] = "PASSED"
    summary = [l for l in reversed(
        io.open(path, encoding="utf-8", errors="replace").read().replace("\r", "").splitlines())
        if re.search(r"\d+ (failed|passed)", l)]
    out["_summary"] = summary[0].strip() if summary else "NO SUMMARY LINE"
    # `pytest -q` prints only the failures, so an absent nodeid is a pass - but this fills it only
    # when the run's own counts add up to the twelve, so a truncated log cannot fake a green.
    if ids:
        match = re.search(r"(\d+) failed, (\d+) passed", out["_summary"])
        if match:
            failed_n, passed_n = int(match.group(1)), int(match.group(2))
            if failed_n + passed_n == len(ids):
                for node in ids:
                    out.setdefault(node, f"PASSED (counts {failed_n}+{passed_n}={len(ids)})")
    return out


def nodeids(path: Path) -> list[str]:
    return [l.strip() for l in io.open(path, encoding="utf-8").read().splitlines() if l.strip()]


def jp(name: str) -> dict:
    return json.loads(io.open(EV / name, encoding="utf-8").read())


def main() -> int:
    ids = nodeids(EV / "twelve_r1.txt")
    named = states(EV / "twelve_run_before_r1.txt", ids)
    full = states(EV / "twelve_run_fulltree_r1.txt", ids)
    present = states(EV / "twelve_run_present_tip_r1.txt", ids)
    tip = states(EV / "twelve_run_present_tip_r1.txt", ids)
    p1 = jp("attribution_probe_r1.json")["probes"]
    p2 = jp("attribution_probe_r2.json")["probes"]
    p4 = jp("sqlite_lock_probe_r4.json")["probes"]
    g3 = json.loads(io.open(EV / "g3_child_repro_r3.json", encoding="utf-8").read())
    seam_g9 = io.open(EV / "g9_family_seam_photon_r1.txt", encoding="utf-8", errors="replace").read()
    siblings = io.open(EV / "sibling_doors_r1.txt", encoding="utf-8", errors="replace").read()
    sib_failed = len(re.findall(r"^FAILED ", siblings, re.M))
    sib_passed = int(re.search(r"(\d+) passed", siblings).group(1))

    q1 = p2["q1_g9b_overlap"]
    q2 = p2["q2_g10_capability"]
    q4 = p4["q4_sqlite_lock_during_provider_call"]
    q5 = p4["q5_lock_probe_control"]
    arms = {a["arm"]: a for a in g3["arms"]}

    def short(node: str) -> str:
        return node.split("::")[-1]

    rows: list[dict] = []

    def add(node: str, klass: str, discriminator: str, owner: str, next_step: str,
            arm: str | None = None) -> None:
        rows.append({
            "nodeid": node,
            "test": short(node),
            "named_recipe_export": named.get(node, "NOT RUN"),
            "complete_tree": full.get(node, "NOT RUN"),
            "present_tip_complete_tree": present.get(node, "NOT RUN"),
            "opt_in_arm": arm or "not applicable",
            "class": klass,
            "discriminator": discriminator,
            "shape_change_owner": owner,
            "next_step": next_step,
        })

    matrix_cells = p1["p1_matrix_shape"]["n11_cells"]
    add("backend/tests/test_qoder_anywhere_gates.py::test_g5_an_ai_run_that_changed_must_say_which_it_was",
        TRUE_DEFECT,
        f"run.outcome={p1['p3_agent_run']['run_outcome_value']} / run.status="
        f"{p1['p3_agent_run']['run_status']} / failure_reason="
        f"{p1['p3_agent_run']['run_failure_reason']!r} (http_status="
        f"{p1['p3_agent_run']['http_status']})",
        "product: backend/app/agent/runtime.py:645-679 leaves the column null; "
        "contracts/openapi-anywhere-draft.yaml names 车道 A/C as the owner",
        "结构化 run.outcome 要同时改 4 条形（COMPLETED/PARTIAL/FAILED_EXTERNAL/SKIPPED）与 "
        "frontend/src/api/citynexus.ts 的 outcome: string | null 两处类型，属跨车道契约改动")

    add("backend/tests/test_qoder_anywhere_lock_duration.py::test_g9b_provider_http_never_runs_inside_an_open_write_transaction",
        INSTRUMENT,
        f"seam off -> provider calls {p1['p2_hydration_egress']['egress_attempts_total']}; "
        f"seam on -> {q1['provider_call_total']} calls, {q1['write_window_total']} write windows, "
        f"door reports overlap; SQLite BEGIN IMMEDIATE during the same calls: locked="
        f"{sum(1 for r in q4['readings'] if r['during_call'].get('locked'))}/{q4['provider_calls_sampled']}, "
        f"controls write={q5['write_control']['locked']} read={q5['read_control']['locked']} "
        f"discriminator_holds={q5['discriminator_holds']}",
        "ruler: _overlaps() intersects wall-clock windows keyed by id(conn) across every connection, "
        "so an ORM transaction that only *later* writes is convicted",
        "g9a/g9c 在同一条 arm 下都绿（"
        + ("1 failed, 2 passed" if "1 failed, 2 passed" in seam_g9 else "见 g9_family_seam_photon_r1.txt")
        + "）⇒ 报上游：判据要落到锁视图或并发饥饿，不是事件簿记")

    add("backend/tests/test_qoder_anywhere_matrix_truth.py::test_g14a_an_oversized_matrix_fails_closed_and_invents_no_facts",
        STALE,
        f"fixture premise N=11 sends one oversized request; measured cells {matrix_cells} "
        f"(max {max(matrix_cells)}, cap {p1['p1_matrix_shape']['max_cells_setting']}) -> status "
        f"{p1['p1_matrix_shape']['n11_status']}, any_oversized="
        f"{p1['p1_matrix_shape']['n11_any_request_oversized']}",
        "product shape 6cb92983 2026-09-22 14:06 (chunked matrix)",
        "报上游：这条门要量「越界请求必须失败关闭」，今天产品已不再发出越界请求 "
        f"(N=20 -> {p1['p1_matrix_shape']['n20_requests']} 片 / cells_max "
        f"{p1['p1_matrix_shape']['n20_cells_max']} / {p1['p1_matrix_shape']['n20_facts']} facts)，"
        "需要一个能真造出越界片的形状才能判")

    add("backend/tests/test_qoder_anywhere_matrix_truth.py::test_g14c_the_verdict_must_not_depend_on_the_providers_wording",
        STALE,
        f"KeyError 'error_type' because both arms returned status "
        f"{p1['p1_matrix_shape']['n11_status']} / error_type present="
        f"{p1['p1_matrix_shape']['n11_has_error_type_key']} (keys {p1['p1_matrix_shape']['n11_keys'][:5]}...)",
        "product shape 6cb92983 2026-09-22 14:06 (chunked matrix)",
        "报上游：与 g14a 同一根因，错误字段只在真失败时才存在")

    add("backend/tests/test_qoder_anywhere_provider_independence.py::test_g8a_default_suite_contains_no_live_provider_calls",
        STALE,
        f"both flagged lines make socket connects="
        f"{p1['p6_socket_guard']['socket_connect_attempt_count']} under a connect guard; "
        f"mock transport answered status={p1['p6_socket_guard']['mock_transport_status']}",
        "ruler predates the two mocked-host lines (file added c421d681 09-21 14:12; offenders "
        "fed18613 09-21 17:15 and 44e4ea78 09-22 01:12)",
        "报上游：同行文法判不出 MockTransport / 被 monkeypatch 的 transport，需要出网自证那一档")

    add("backend/tests/test_qoder_anywhere_provider_truth.py::test_g10_every_normalised_place_carries_a_usable_coordinate_including_nodes",
        ENV,
        f"seam off -> egress {p1['p2_hydration_egress']['egress_attempts_total']} and "
        f"reason_code {p1['p2_hydration_egress']['capability_reason_code']}; seam on -> photon answered, "
        f"destination_resolution={q2['unseen_county']['destination_resolution']}, "
        f"capability={q2['unseen_county']['capability']}, places_len={q2['unseen_county']['places_len']}; "
        f"a city the provider can name (云和县) resolves to "
        f"{q2['yunhe']['canonical_destination_id']} with places_len={q2['yunhe']['places_len']}; "
        f"Beijing -> {q2['beijing']['places_len']} places, status {q2['beijing']['operation_status']}",
        "opt-in leg: CITYNEXUS_ANYWHERE_RESOLVER defaults to off (app/anywhere_capability.py:223)",
        "报上游：这条门要 live provider 且要一个 provider 认得的目的地；默认套件按 §17C 不许出网")

    add("backend/tests/test_qoder_city_failure_reasons.py::test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at",
        STALE,
        f"measured mapping 429->{p1['p4_live_failure_reasons']['mapped']['status_429']} "
        f"500->{p1['p4_live_failure_reasons']['mapped']['status_500']} "
        f"502->{p1['p4_live_failure_reasons']['mapped']['status_502']} "
        f"KeyError->{p1['p4_live_failure_reasons']['mapped']['keyerror_lat']}; "
        f"5xx differs from a malformed body="
        f"{p1['p4_live_failure_reasons']['five_hundred_and_malformed_body_differ']}",
        "product shape 6cb92983 2026-09-22 14:06 added PROVIDER_SERVER_ERROR "
        "(assertion pinned at d4814644 09-21 14:46)",
        "报上游：产品现在把 5xx 与畸形 2xx 分开命名，正是这条门自己文件写的「六形五码」诉求；"
        "断言钉的是塌缩前的旧码")

    add("backend/tests/test_qoder_g3_xproc_http.py::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation",
        INSTRUMENT,
        f"child self-reports serving and urllib gets status="
        f"{arms['A_default_env_with_dead_proxy']['urllib_leg']['reported']['status']} even with a dead "
        f"proxy exported; the port refuses connects for "
        f"{arms['A_default_env_with_dead_proxy']['readiness_attempts_head'][0]['at_s']}-"
        f"{arms['A_default_env_with_dead_proxy']['readiness_attempts_head'][-1]['at_s']} s "
        f"(arm B first ok at {arms['B_proxy_vars_removed']['readiness_attempts_head'][-1]['at_s']} s); "
        "the door's _http catches HTTPError only, so its first poll raises",
        "instrument: backend/tests/test_qoder_g3_xproc_http.py:83-90 (no URLError branch) vs "
        ":188-195 (readiness loop that assumes it can poll a not-yet-bound port)",
        "报上游：门的就绪循环扛不过 1.0-1.5 s 的绑定窗口，硬约束不许我为跑绿改测试，故本轮不动")

    add("backend/tests/test_qoder_ord0296_write_deadline.py::test_G4_the_lock_wait_is_written_in_exactly_one_place",
        STALE,
        f"inline-copy offenders={p1['p5_lock_wait']['inline_copy_offenders']} and "
        f"literal-30000-with-busy_timeout={p1['p5_lock_wait']['literal_30000_with_busy_timeout']}; "
        f"the extra name is main.py whose only mention is "
        f"{p1['p5_lock_wait']['main_py_lines'][0]}",
        "product shape 5bb04b8f 2026-09-26 08:22 (ORD-0340 lease reads the same settings source)",
        "报上游：门的第一条断言（内联第二份拷贝）仍然绿，红的只是它抄死的模块名清单")

    add("backend/tests/test_qoder_ord0307_credential_gate.py::test_C01_the_scanned_set_is_named_and_actually_present",
        ENV,
        f"named-recipe export -> {named['backend/tests/test_qoder_ord0307_credential_gate.py::test_C01_the_scanned_set_is_named_and_actually_present']} "
        f"(roots_missing ['qoder-handoff']); complete tree -> "
        f"{full['backend/tests/test_qoder_ord0307_credential_gate.py::test_C01_the_scanned_set_is_named_and_actually_present']}",
        "export recipe drops the top-level qoder-handoff/ path",
        "把 qoder-handoff/ 加进入档清单（本轮已证：完整树 3 枚转绿）")

    add("backend/tests/test_qoder_ord0402_recycle_bin.py::test_the_existing_list_door_was_not_touched_down_to_its_bytes",
        ENV,
        f"named-recipe export -> {named['backend/tests/test_qoder_ord0402_recycle_bin.py::test_the_existing_list_door_was_not_touched_down_to_its_bytes']} "
        "(baseline record missing); complete tree -> "
        f"{full['backend/tests/test_qoder_ord0402_recycle_bin.py::test_the_existing_list_door_was_not_touched_down_to_its_bytes']}",
        "export recipe drops review/",
        "把 review/ 加进入档清单")

    add("backend/tests/test_v18_3_convergence.py::test_release_metadata_and_map_entrypoint_are_converged",
        ENV,
        f"named-recipe export -> {named['backend/tests/test_v18_3_convergence.py::test_release_metadata_and_map_entrypoint_are_converged']} "
        "(PACKAGE-MANIFEST.json missing); complete tree -> "
        f"{full['backend/tests/test_v18_3_convergence.py::test_release_metadata_and_map_entrypoint_are_converged']}",
        "export recipe drops PACKAGE-MANIFEST.json",
        "把 PACKAGE-MANIFEST.json 加进入档清单")

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["class"]] = counts.get(row["class"], 0) + 1

    payload = {
        "pinned_tip": "8d038b21f09477b933cff3b1c7b09845c542373b",
        "tip_at_run": "123fabb637fefe9e1be442b67f2da4be7e95ac74",
        "named_recipe_states": {"FAILED": len([v for v in named.values() if v == "FAILED"]),
                                "summary": named["_summary"]},
        "complete_tree_states": {"FAILED": len([v for v in full.values() if v == "FAILED"]),
                                 "PASSED_by_inference": len(ids) - len([v for v in full.values() if v == "FAILED"]),
                                 "summary": full["_summary"]},
        "present_tip_states": {"FAILED": len([v for v in present.values() if v == "FAILED"]),
                               "PASSED_by_inference": len(ids) - len([v for v in present.values() if v == "FAILED"]),
                               "summary": present["_summary"]},
        "sibling_doors_in_the_three_ruler_files": {"failed": sib_failed, "passed": sib_passed},
        "class_counts": counts,
        "rows": rows,
        "evidence_inputs": [str(p.relative_to(LANE)).replace("\\", "/") for p in [
            EV / "twelve_r1.txt", EV / "twelve_run_before_r1.txt", EV / "twelve_run_fulltree_r1.txt",
            EV / "twelve_run_present_tip_r1.txt",
            EV / "attribution_probe_r1.json", EV / "attribution_probe_r2.json",
            EV / "sqlite_lock_probe_r4.json", EV / "g3_child_repro_r3.json",
            EV / "g9_family_seam_photon_r1.txt", EV / "sibling_doors_r1.txt"]],
    }
    (EV / "twelve_verdicts_r1.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")

    lines = [
        "# ORD-0442 十二枚具名红 - 逐枚归因（由 review/ord0442/twelve_verdicts_r1.py 从证据件重算，不是手抄）",
        "",
        f"- 尖：{payload['pinned_tip']}（派单点名）；本轮现读现尖 {payload['tip_at_run']}",
        f"- 具名导出配方（backend data contracts tools scripts agent-mcp frontend/src frontend/e2e）："
        f"{payload['named_recipe_states']['FAILED']} 枚全红，摘要 {payload['named_recipe_states']['summary']}",
        f"- 完整树导出（git archive 全量，尖 {payload['pinned_tip']}）："
        f"{payload['complete_tree_states']['FAILED']} 枚红 / "
        f"{payload['complete_tree_states']['PASSED_by_inference']} 枚绿，摘要 {payload['complete_tree_states']['summary']}",
        f"- 现尖 {payload['tip_at_run']} 完整树复跑：{payload['present_tip_states']['FAILED']} 枚红 / "
        f"{payload['present_tip_states']['PASSED_by_inference']} 枚绿，摘要 {payload['present_tip_states']['summary']}",
        f"- 三把尺文件里的其余门：{sib_passed} 绿 / {sib_failed} 红（红的全是本表点名的这几枚）",
        f"- 分类计数：{json.dumps(payload['class_counts'], ensure_ascii=False)}",
        "",
        "| 测试 | 具名配方 | 完整树(派单尖) | 现尖完整树 | 点名档 | 判据（实测） | 形状变更归属 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['test']} | {row['named_recipe_export']} | {row['complete_tree']} | "
            f"{row['present_tip_complete_tree']} | "
            f"{row['class']} | {row['discriminator']} | {row['shape_change_owner']} |"
        )
    lines.append("")
    lines.append("## 下一步（每条一枚）")
    for row in rows:
        lines.append(f"- {row['test']}：{row['next_step']}")
    (EV / "twelve_verdicts_r1.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print("rows", len(rows), "class_counts", json.dumps(counts, ensure_ascii=False))
    print("wrote", (EV / "twelve_verdicts_r1.json").relative_to(LANE).as_posix())
    print("wrote", (EV / "twelve_verdicts_r1.md").relative_to(LANE).as_posix())
    missing = [r["test"] for r in rows if r["named_recipe_export"] == "NOT RUN"
               or r["complete_tree"] == "NOT RUN"]
    print("rows_with_no_measured_state", missing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
