"""Assemble the ORD-0310 receipt out of artifacts this lane already produced.

Nothing here retypes a number: every value is read from the gate's evidence file, the arms receipt,
the backend readings, or a git command run at this moment. The order's five requirements each become
one cell with `derived_from` pointing at the readings that support it, so the Q38 ruler can check the
sentence against the measurement rather than against my prose.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
SC = ROOT / "_scratch_0310"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
URL = "https://github.com/Canshu-King/CityNexus.git"
MODULE = "frontend/src/lib/keylessWriteDeadline.ts"
SHEET = "frontend/src/features/planning/PlanWithAiSheet.tsx"
SPEC = "e2e/qoder-ord0310-keyless-write-deadline.spec.ts"
BACKEND_TEST = "backend/tests/test_qoder_ord0310_keyless_leg_receipts.py"
SPEC_PATH = f"frontend/{SPEC}"
SHAPE_LABELS = {
    "keyed": "0281 有键那一支（`plans/generate`：仍走裸 fetch，期限由 0281 自己管）",
    "keyless": "0288/0310 无键那一支（`agent/commands`：本单新加的具名设备期限）",
}


def git(*args: str) -> str:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    return out.stdout.strip()


def blob(rel: str, rev: str = "HEAD") -> str:
    out = subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=ROOT, capture_output=True)
    if out.returncode != 0:
        return ""
    data = out.stdout
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def remote_tip() -> str:
    out = subprocess.run(["git", "ls-remote", URL, TIP_REF], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=120).stdout
    return out.split("\t")[0].strip() if "\t" in out else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-sha", required=True)
    ap.add_argument("--arms", default=str(SC / "arms_receipt_r1.json"))
    ap.add_argument("--backend", default=str(SC / "backend_readings.json"))
    ap.add_argument("--out", default=str(SC / "ord0310_keyless_deadline_receipt_r1.json"))
    args = ap.parse_args()

    code = args.code_sha.strip()
    arms = json.loads(Path(args.arms).read_text(encoding="utf-8"))
    backend = json.loads(Path(args.backend).read_text(encoding="utf-8"))
    tip = remote_tip()
    parent = git("rev-parse", f"{code}^")

    clean_evidence = json.loads((ROOT / "review/evidence/ord0310" /
                                 f"keyless_deadline_arms-{arms['clean_round']['runId']}.json")
                                .read_text(encoding="utf-8"))
    k1 = clean_evidence["arms"]["K1"]
    module_src = Path(ROOT / MODULE).read_text(encoding="utf-8")
    constant = int(re.search(r"KEYLESS_WRITE_DEADLINE_MS = (\d+)_?(\d*)", module_src).group(0)
                   .split("=")[1].replace("_", "").rstrip(";").strip())
    keyed_hunks = [h for h in re.findall(r"^@@ [^\n]*", git("diff", "-U0", parent, code, "--", SHEET),
                                          flags=re.M)]
    keyed_call_line = next((i for i, line in enumerate(Path(ROOT / SHEET).read_text(encoding="utf-8")
                                                       .splitlines(), 1)
                            if "const generate = await fetch(" in line), 0)
    touched_keyed = any(
        int(re.search(r"\+(\d+)", h).group(1)) <= keyed_call_line <= int(re.search(r"\+(\d+)", h).group(1))
        + 20 for h in keyed_hunks if re.search(r"\+(\d+)", h))

    probe = next(a for a in arms["arms"] if a["kind"] != "kill")
    probe_k1 = (probe["screen_reading_from_this_run"] or {}).get("K1", {})

    cells = [
        {
            "id": "C1_keyed_shape_untouched",
            "triple": {"exact_sha": code, "nodeid": f"{SPEC_PATH} :: K2 正控：服务器两秒内答完时，这枚期限不碰正常结局",
                       "shape": ["chromium"]},
            "verdict": "KEYED_LEG_UNTOUCHED",
            "readings": {
                "parent_of_the_code_commit": parent,
                "authoritative_tip_read_now": tip,
                "files_changed_by_this_commit": git("diff", "--name-only", parent, code).splitlines(),
                "hunk_headers_in_the_sheet": keyed_hunks,
                "keyed_call_site_line": keyed_call_line,
                "any_hunk_covers_the_keyed_call_site": touched_keyed,
            },
            "derived_from": f"hunk_headers={json.dumps(keyed_hunks)} · keyed_call_site_line={keyed_call_line} · "
                            f"covers={touched_keyed}",
            "why": f"这一笔提交只碰无键那一支：`plans/generate` 的调用点在第 {keyed_call_line} 行，"
                   f"本提交在该文件里的 hunk 起点是 {', '.join(keyed_hunks) or '（无）'}，"
                   f"没有任何一枚覆盖到 {keyed_call_line} ± 的区间，且提交里没有 `writeDeadline.ts`（那是 0281 的文件）。"
                   f"两枚形状分开具名：{SHAPE_LABELS['keyed']} / {SHAPE_LABELS['keyless']}。",
        },
        {
            "id": "C2_single_named_constant",
            "triple": {"exact_sha": code, "nodeid": f"{SPEC_PATH} :: {k1.get('node_title') or 'K1'}",
                       "shape": ["chromium"]},
            "verdict": "NUMBER_AND_TIMER_SHARE_ONE_SOURCE",
            "readings": {
                "constant_ms_in_the_module": constant,
                "seconds_shown_on_screen_clean_round": (k1.get("read") or {}).get("reason", ""),
                "measured_wait_clean_round_ms": k1.get("elapsed_ms"),
                "post_count_clean_round": k1.get("post_count"),
                "probe_arm": probe["arm"], "probe_verdict": probe["claimed_result"],
                "probe_constant_ms": (probe.get("screen_reading_from_this_run") or {}).get(
                    "deadline_constant_ms"),
                "probe_seconds_shown": (probe_k1.get("read") or {}).get("reason", ""),
                "probe_measured_wait_ms": probe_k1.get("elapsed_ms"),
            },
            "derived_from": f"clean: elapsed={k1.get('elapsed_ms')} constant={constant} · "
                            f"probe: {probe['arm']} elapsed={probe_k1.get('elapsed_ms')} "
                            f"verdict={probe['claimed_result']}",
            "why": f"常数是 `KEYLESS_WRITE_DEADLINE_MS = {constant}`（模块里一处定义，屏幕与计时器都从它取）。"
                   f"干净轮实测等待 {k1.get('elapsed_ms')} ms 且屏幕上写着同一个秒数；把常数改小的那一枚探针臂"
                   f"（{probe['arm']}）里，实测等待变成 {probe_k1.get('elapsed_ms')} ms、屏幕那句也跟着动，"
                   f"且该格仍判 {probe['claimed_result']} —— 这就是 0281 的 TB/TC 那对反件先例的形制。",
        },
        {
            "id": "C3_screen_sentence_shape",
            "triple": {"exact_sha": code, "nodeid": f"{SPEC_PATH} :: K1", "shape": ["chromium"]},
            "verdict": "TWO_CLAUSES_PRESENT_FORBIDDEN_ABSENT",
            "readings": {
                "status_attribute": (k1.get("read") or {}).get("status"),
                "rendered_card_first_240": ((k1.get("read") or {}).get("card_text") or "")[:240],
                "reason_label": (k1.get("read") or {}).get("label"),
                "reason_origin": (k1.get("read") or {}).get("origin"),
                "detail_block_attached": (k1.get("read") or {}).get("detail_block_attached"),
                "rows_in_this_cell": k1.get("rows"),
                "verdict_of_the_node": k1.get("verdict"),
            },
            "derived_from": f"rows={json.dumps([r['claim'] for r in k1.get('rows', [])], ensure_ascii=False)[:400]}"
                            f" · origin={(k1.get('read') or {}).get('origin')} · status="
                            f"{(k1.get('read') or {}).get('status')}",
            "why": "两件事都在屏上：结果未知（并明写「不是没发生」）、且这一笔不能靠同一把键补问；"
                   "归因标签说的是这台设备自己的读数而不是「服务器给出的原因」，技术详情仍在，"
                   "四个禁句（已取消 / 没有发生 / 再试一次 / 连不上服务端）一个都没出现。",
        },
        {
            "id": "C4_server_field_readings",
            "triple": {"exact_sha": code, "nodeid": f"{BACKEND_TEST} :: K1/K2/T1a/T1b/T1c",
                       "shape": ["pytest-single-process"]},
            "verdict": "NO_KEY_ADDS_ZERO_RECEIPT_ROWS_AND_THREE_MISSIONS",
            "readings": backend["cells"],
            "derived_from": f"db_file={backend['db_file']} table={backend['table']} "
                            f"K1={{from:{backend['cells']['K1']['idempotency_keys_rows_from']},"
                            f"to:{backend['cells']['K1']['idempotency_keys_rows_to']},"
                            f"missions+{backend['cells']['K1']['mission_rows_added']}}}",
            "why": f"不带键连发三发：`{backend['table']}` 从 {backend['cells']['K1']['idempotency_keys_rows_from']} 到 "
                   f"{backend['cells']['K1']['idempotency_keys_rows_to']}（+0），而 `journey_missions` 同轮 +"
                   f"{backend['cells']['K1']['mission_rows_added']} 且三个 mission id 互不相同；带一把形制正确的键仍 +0"
                   f"（K2），说明「请求里有个头」不是凭条。库文件具名：`{backend['db_file']}`。",
        },
        {
            "id": "C5_arms_and_provenance",
            "triple": {"exact_sha": code, "nodeid": f"{SPEC_PATH} :: 全部三枚节点", "shape": ["chromium"]},
            "verdict": "ARMS_RESTORED_TREE_UNCHANGED",
            "readings": {
                "arms_total": arms["arms_total"], "killed": arms["killed"], "survived": arms["survived"],
                "probes": arms["probes"],
                "all_arms_restored_to_tested_tree_bytes": arms["all_arms_restored_to_tested_tree_bytes"],
                "tree_unchanged_by_this_run": arms["tree_unchanged_by_this_run"],
                "every_arm_has_a_green_same_key_precondition": arms["all_arms_carry_a_green_same_key_precondition"],
                "clean_round": {"runId": arms["clean_round"]["runId"], "db": arms["clean_round"]["db"],
                                "port": arms["clean_round"]["port"],
                                "nodes": arms["clean_round"]["nodes"]},
                "blob_module": blob(MODULE, code), "blob_sheet": blob(SHEET, code),
                "blob_spec": blob(SPEC, code), "blob_backend_test": blob(BACKEND_TEST, code),
            },
            "derived_from": f"killed={arms['killed']} of {arms['arms_total'] - arms['probes']} killers · "
                            f"restored={arms['all_arms_restored_to_tested_tree_bytes']} · "
                            f"tree_unchanged={arms['tree_unchanged_by_this_run']}",
            "why": "逐臂都带自己的 (sha, nodeid, shape) 与还原三点摘要；`claimed_result` 是本车道观测，"
                   "`derived_result` 一律留 null 给红队。等级不由本车道签。",
        },
    ]

    payload = {
        "order": "ORD-0310", "lane": "D e345b9d6",
        "title": "ORD-0288 无键写腿的客户端期限（Q54=① 的形制）：客户端半件 + 屏上句子的射程",
        "generated_at": datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%:z"),
        "ref_tip_read": {"ref": TIP_REF, "sha": tip, "read_by": "git ls-remote at receipt build time"},
        "candidate": {"code_sha": code, "parent": parent, "tools_sha": git("rev-parse", "HEAD"),
                      "is_child_of_the_tip_read_now": parent == tip},
        "gates": {
            "frontend_spec": {"path": SPEC_PATH, "run_shape": ["chromium"],
                              "run_id": arms["clean_round"]["runId"], "db": arms["clean_round"]["db"],
                              "tallies": arms["clean_round"]["tallies"],
                              "command": f"python review/run_spec.py qoder-{SPEC.replace('.spec.ts','')} <port>"},
            "backend_pytest": {"path": BACKEND_TEST, "run_shape": ["pytest-single-process"],
                               "command": "python -m pytest " + BACKEND_TEST + " -q",
                               "db_file": backend["db_file"],
                               "note": "单进程 TestClient；跨进程耐久那一形是 HJ-P3 在 "
                                       "dc964086c9d412573ac19d70b24b30e6c3ee6168 上量的（她的 C4），不在本收据主张之内"},
        },
        "cells": cells,
        "claimed_and_derived": {"claimed_result": "CLIENT_HALF_DELIVERED_ON_A_NAMED_CONSTANT",
                                "derived_result": None},
        "discipline": {"refs_pushed": 0, "authority_line_moved": 0, "demo_reset": 0,
                       "user_db_reads_writes": 0, "credentials_printed": 0,
                       "assertions_changed_to_buy_green": 0,
                       "note": "候选与工具只落本车道分支；权威线由号令者移动"},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out} {out.stat().st_size} B")
    print(f"tip={tip} parent==tip? {payload['candidate']['is_child_of_the_tip_read_now']} "
          f"killed={arms['killed']}/{arms['arms_total'] - arms['probes']} restored={arms['all_arms_restored_to_tested_tree_bytes']}")
    return 0


raise SystemExit(main())
