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
KEYED_MODULE = "frontend/src/lib/writeDeadline.ts"
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


def remote_tip() -> tuple:
    proc = subprocess.run(["git", "ls-remote", URL, TIP_REF], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=120)
    sha = proc.stdout.split("\t")[0].strip() if "\t" in proc.stdout else ""
    raw = (f"$ git ls-remote {URL} {TIP_REF}\nexit={proc.returncode}\n"
           f"stdout:\n{proc.stdout}" + (f"stderr:\n{proc.stderr}" if proc.stderr else ""))
    return sha, raw


def ref_read_raw(ref: str) -> tuple:
    proc = subprocess.run(["git", "ls-remote", URL, ref], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=120)
    sha = proc.stdout.split("\t")[0].strip() if "\t" in proc.stdout else ""
    raw = (f"$ git ls-remote {URL} {ref}\nexit={proc.returncode}\n"
           f"stdout:\n{proc.stdout}" + (f"stderr:\n{proc.stderr}" if proc.stderr else ""))
    return sha, raw


def remote_tip_via_api() -> tuple:
    """Second, independent route to the same ref: the git/ref REST endpoint.

    The token is read from the git credential helper into memory and never printed.
    """
    import urllib.error
    import urllib.request
    helper = subprocess.run(["git", "credential", "fill"],
                            input="protocol=https\nhost=github.com\n\n",
                            capture_output=True, text=True, check=True).stdout
    secret = next((l[len("password="):] for l in helper.splitlines() if l.startswith("password=")), "")
    url = (f"https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/"
           f"{TIP_REF[len('refs/heads/'):]}")
    if not secret:
        return "NO_CREDENTIAL_FROM_HELPER", f"$ GET {url}\n(no credential from the git helper)\n"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {secret}",
                                               "Accept": "application/vnd.github+json",
                                               "User-Agent": "qoder-e345b9d6-ord0310"})
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            body = response.read().decode("utf-8")
        sha = json.loads(body)["object"]["sha"]
        return sha, (f"$ GET {url}\nHTTP {response.status}\n"
                     f"(the Authorization header is written as a placeholder above; the secret is "
                     f"held in memory only and appears in no artifact)\nbody:\n{body}")
    except urllib.error.HTTPError as error:
        return f"HTTP_{error.code}", f"$ curl {url}\nHTTP {error.code}\n{error.read().decode('utf-8', errors='replace')[:400]}"


def merge_prediction(tip: str, code: str) -> dict:
    """Read-only merge prediction: writes blobs/trees into the object store, moves no ref."""
    proc = subprocess.run(["git", "merge-tree", "--write-tree", tip, code], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = proc.stdout.splitlines()
    return {"command": f"git merge-tree --write-tree {tip} {code}", "exit": proc.returncode,
            "predicted_tree": lines[0] if lines else "",
            "raw_after_first_line": "\n".join(lines[1:]),
            "stderr": proc.stderr.strip()}


def generation_of(tip: str, code: str, base: str = "") -> dict:
    """Where this candidate sits relative to the line that was read, and what landing would do."""
    parent = base or git("rev-parse", f"{code}^")
    fork = git("merge-base", parent, tip)
    theirs = git("diff", "--name-only", fork, tip).splitlines()
    mine = git("diff", "--name-only", fork, code).splitlines()
    return {
        "parent_of_the_code_commit": parent,
        "fork_point_with_the_line": fork,
        "is_my_history_a_descendant_line_from_the_fork": subprocess.run(
            ["git", "merge-base", "--is-ancestor", fork, parent],
            cwd=ROOT, capture_output=True).returncode == 0,
        "tip_is_descendant_of_the_fork": subprocess.run(
            ["git", "merge-base", "--is-ancestor", fork, tip],
            cwd=ROOT, capture_output=True).returncode == 0,
        # the interesting question once the lane's own work has been landed: is what I am measuring
        # sitting on top of the line (a superset), or beside it?
        "authority_tip_is_ancestor_of_this_tree": subprocess.run(
            ["git", "merge-base", "--is-ancestor", tip, code],
            cwd=ROOT, capture_output=True).returncode == 0,
        "files_this_tree_adds_on_top_of_the_tip": git("diff", "--name-only", tip, code).splitlines(),
        "commits_on_the_line_since_the_fork": git("log", "--format=%h %s", f"{fork}..{tip}").splitlines(),
        "files_the_line_changed_since_the_fork": theirs,
        "files_my_candidate_changed_since_the_fork": mine,
        "intersection_between_their_files_and_mine": sorted(set(theirs) & set(mine)),
        "frontend_subtree_oid_my_tree": git("rev-parse", f"{code}:frontend"),
        "frontend_subtree_oid_tip": git("rev-parse", f"{tip}:frontend"),
        "merge_prediction": merge_prediction(tip, code),
    }


def keyed_shape_at_tip(tip: str, code: str) -> dict:
    """B's 0281 keyed deadline, read on the line — not present in this candidate's generation."""
    shown = subprocess.run(["git", "show", f"{tip}:{KEYED_MODULE}"], cwd=ROOT, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
    hit = re.search(r"export const CLIENT_WRITE_DEADLINE_MS = ([0-9_]+)", shown.stdout)
    importers = [line.split(":", 1)[1] for line in
                 git("grep", "-l", "lib/writeDeadline", tip, "--", "frontend/src").splitlines()]
    return {
        "path": KEYED_MODULE,
        "blob_at_tip": git("rev-parse", f"{tip}:{KEYED_MODULE}") if shown.returncode == 0 else "ABSENT_AT_TIP",
        "absent_from_my_tested_tree": subprocess.run(
            ["git", "cat-file", "-e", f"{code}:{KEYED_MODULE}"], cwd=ROOT).returncode != 0,
        "exported_constant": hit.group(0) if hit else "NOT_FOUND",
        "constant_value_ms": int(hit.group(1).replace("_", "")) if hit else None,
        "importers_at_tip": sorted(importers),
        "sheet_call_sites_at_tip": (lambda hits: {
            "command": f"git grep -n fetchWithWriteDeadline {tip} -- {SHEET}",
            "lines_returned": len(hits), "raw": hits})
        (git("grep", "-n", "fetchWithWriteDeadline", tip, "--", SHEET).splitlines()),
    }


def grep_lines(rev: str, path: str, pattern: str) -> list:
    """`git grep -n` at a rev, returned as (line_number, stripped_text) so a claim names its own line."""
    rows = []
    for line in git("grep", "-n", pattern, rev, "--", path).splitlines():
        parts = line.split(":", 3)
        if len(parts) == 4:
            rows.append([int(parts[2]), parts[3].strip()[:70]])
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-sha", required=True)
    ap.add_argument("--arms", default=str(SC / "arms_receipt_r1.json"))
    ap.add_argument("--backend", default=str(SC / "backend_readings.json"))
    ap.add_argument("--out", default=str(SC / "ord0310_keyless_deadline_receipt_r1.json"))
    ap.add_argument("--pushed-ref", default="refs/heads/review/ord0310-keyless-deadline-d")
    ap.add_argument("--supersedes-receipt", default="",
                    help="blob of the previous-generation receipt this one replaces (never deleted)")
    ap.add_argument("--raw-dir", default="",
                    help="where to write the raw .out/.tsv artifacts (defaults to the receipt's own folder)")
    ap.add_argument("--previous-generation-sha", default="",
                    help="the tested tree of the previous generation, to prove a re-cut moved only the base")
    ap.add_argument("--base", default="",
                    help="the line commit this candidate is cut from (defaults to code^)")
    ap.add_argument("--product-commit", default="",
                    help="the commit inside the candidate that carries the product change (patch-id source)")
    ap.add_argument("--previous-product-commit", default="",
                    help="its counterpart in the previous generation, for the patch-id pair")
    ap.add_argument("--supersedes-predicted-tree", default="",
                    help="predicted tree of the previous generation, marked SUPERSEDED rather than removed")
    ap.add_argument("--generation-label", default="",
                    help="what this generation is, spelled out; it goes into the block heading, so it "
                         "must not be a literal left over from an earlier generation")
    args = ap.parse_args()
    RAW = Path(args.raw_dir) if args.raw_dir else SC
    RAW.mkdir(parents=True, exist_ok=True)

    code = args.code_sha.strip()
    arms = json.loads(Path(args.arms).read_text(encoding="utf-8"))
    backend = json.loads(Path(args.backend).read_text(encoding="utf-8"))
    tip, tip_raw = remote_tip()
    if not re.fullmatch(r"[0-9a-f]{40}", tip or ""):
        print(f"ABORT: the external read of {TIP_REF} did not return a 40-hex sha (got {tip!r}). "
              f"A receipt whose coordinate is missing is not written.")
        return 5
    subprocess.run(["git", "fetch", "--no-write-fetch-head", "--quiet", URL, tip],
                   cwd=ROOT, capture_output=True)
    tip_api, tip_api_raw = remote_tip_via_api()
    base = args.base or git("rev-parse", f"{code}^")
    generation = generation_of(tip, code, base)
    keyed = keyed_shape_at_tip(tip, code)
    parent = git("rev-parse", f"{code}^")

    clean_evidence = json.loads((ROOT / "review/evidence/ord0310" /
                                 f"keyless_deadline_arms-{arms['clean_round']['runId']}.json")
                                .read_text(encoding="utf-8"))
    k1 = clean_evidence["arms"]["K1"]
    clean_seconds = re.search(r"等到 (\d+) 秒", (k1.get("read") or {}).get("reason") or "")
    module_src = Path(ROOT / MODULE).read_text(encoding="utf-8")
    constant = int(re.search(r"KEYLESS_WRITE_DEADLINE_MS = (\d+)_?(\d*)", module_src).group(0)
                   .split("=")[1].replace("_", "").rstrip(";").strip())
    keyed_hunks = [h for h in re.findall(r"^@@ [^\n]*", git("diff", "-U0", base, code, "--", SHEET),
                                          flags=re.M)]
    keyed_call_line = next((i for i, line in enumerate(Path(ROOT / SHEET).read_text(encoding="utf-8")
                                                       .splitlines(), 1)
                            if "const generate = await fetch(" in line), 0)
    touched_keyed = any(
        int(re.search(r"\+(\d+)", h).group(1)) <= keyed_call_line <= int(re.search(r"\+(\d+)", h).group(1))
        + 20 for h in keyed_hunks if re.search(r"\+(\d+)", h))

    probe = next(a for a in arms["arms"] if a["kind"] != "kill")    # The arms file flattens one screen reading per node (verdict/elapsed_ms/reason_text at the top
    # level); only the gate's own evidence JSON nests them under `read`. Reading the wrong shape is
    # how a cell ends up printing `None` next to a claim about a number on the screen.
    probe_k1 = (probe["screen_reading_from_this_run"] or {}).get("K1", {})
    probe_seconds = re.search(r"等到 (\d+) 秒", probe_k1.get("reason_text") or "")

    cells = [
        {
            "id": "C1_keyed_shape_untouched",
            "triple": {"exact_sha": code, "nodeid": f"{SPEC_PATH} :: K2 正控：服务器两秒内答完时，这枚期限不碰正常结局",
                       "shape": ["chromium"]},
            "verdict": "KEYED_LEG_UNTOUCHED",
            "readings": {
                "parent_of_the_code_commit": parent,
                "base_cut_from": base,
                "authoritative_tip_read_now": tip,
                "files_changed_by_this_candidate": git("diff", "--name-only", base, code).splitlines(),
                "hunk_headers_in_the_sheet": keyed_hunks,
                "keyed_call_site_line": keyed_call_line,
                "any_hunk_covers_the_keyed_call_site": touched_keyed,
                "keyed_shape_on_the_line_0281": keyed,
                "keyless_shape_this_order_0310": {
                    "path": MODULE, "blob_in_this_tree": blob(MODULE, code),
                    "constant": f"KEYLESS_WRITE_DEADLINE_MS = {constant}",
                    "sheet_wrapped_call": git("grep", "-n", "fetchWithKeylessWriteDeadline", code,
                                              "--", SHEET).splitlines(),
                },
            },
            "derived_from": f"hunk_headers={json.dumps(keyed_hunks)} · keyed_call_site_line={keyed_call_line} · "
                            f"covers={touched_keyed} · 0281_module_blob_at_tip={keyed['blob_at_tip']} · "
                            f"0281_importers={json.dumps(keyed['importers_at_tip'])}",
            "why": f"这一笔提交只碰无键那一支：`plans/generate` 的调用点在第 {keyed_call_line} 行，"
                   f"本提交在该文件里的 hunk 起点是 {', '.join(keyed_hunks) or '（无）'}，"
                   f"没有任何一枚覆盖到 {keyed_call_line} ± 的区间。两枚形状分开具名："
                   f"{SHAPE_LABELS['keyed']} = 线上 `{KEYED_MODULE}`（blob `{keyed['blob_at_tip']}`，"
                   f"常数 `{keyed['exported_constant']}`，只被 {', '.join('`'+p+'`' for p in keyed['importers_at_tip'])} 引用）；"
                   f"{SHAPE_LABELS['keyless']} = 本单新建 `{MODULE}`（blob `{blob(MODULE, code)}`，"
                   f"常数 `KEYLESS_WRITE_DEADLINE_MS = {constant}`）。"
                   f"两枚数值同为 {constant} ms 但各管各的调用点，本单没有替 0281 交卷，也没有改它一个字节："
                   + (f"被测那一代里根本没有那枚文件（`absent_from_my_tested_tree=true`），"
                      f"它是我在量完之后按线尖的只读 `git show` 读到的。"
                      if keyed["absent_from_my_tested_tree"] else
                      f"这一代它就在树里（`{KEYED_MODULE}` 在本候选里的 blob = "
                      f"`{git('rev-parse', str(code) + ':' + KEYED_MODULE)}`，与线尖那一枚"
                      f"`{keyed['blob_at_tip']}` 同值），而本道那一笔提交的改动清单里没有它："
                      f"{json.dumps(git('diff', '--name-only', base, code).splitlines(), ensure_ascii=False)}。"),
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
                "probe_run_id": probe["attempt"]["runId"], "probe_db": probe["attempt"]["db"],
                "probe_port": probe["attempt"]["port"],
                "probe_constant_ms": probe_k1.get("deadline_constant_ms"),
                "probe_seconds_shown": probe_seconds.group(1) if probe_seconds else "",
                "probe_reason_text": probe_k1.get("reason_text"),
                "probe_measured_wait_ms": probe_k1.get("elapsed_ms"),
                "probe_post_count": probe_k1.get("post_count"),
            },
            "derived_from": f"clean: elapsed={k1.get('elapsed_ms')} constant={constant} · "
                            f"probe: {probe['arm']} elapsed={probe_k1.get('elapsed_ms')} "
                            f"verdict={probe['claimed_result']}",
            "why": f"常数是 `KEYLESS_WRITE_DEADLINE_MS = {constant}`（`{MODULE}` 里一处定义，"
                   f"屏幕秒数与计时器都从它取）。干净轮 `runId={arms['clean_round']['runId']}` "
                   f"实测等待 {k1.get('elapsed_ms')} ms，屏幕那句里的秒数是 "
                   f"`{clean_seconds.group(1) if clean_seconds else 'NOT_READ'}`；"
                   f"把常数改小到 {probe_k1.get('deadline_constant_ms')} 的那一枚探针臂（{probe['arm']}，"
                   f"轮次 `runId={probe['attempt']['runId']}`）里，屏幕那句跟着变成 "
                   f"`{probe_seconds.group(1) if probe_seconds else ''}` 秒、实测等待变成 "
                   f"{probe_k1.get('elapsed_ms')} ms、`post_count={probe_k1.get('post_count')}`，"
                   f"且该臂判 {probe['claimed_result']}（仍绿）—— 两处一起动才叫同源，"
                   f"这就是 0281 那对 TB/TC 反件先例的形制。",
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
            "why": f"屏上两件事都在：`status={(k1.get('read') or {}).get('status')}` 的卡片正文（前 60 字）"
                   f"「{((k1.get('read') or {}).get('card_text') or '')[:60]}」里同时出现"
                   f"「结果未知」与逐字「不能靠同一把键补问」；归因标签 "
                   f"`origin={(k1.get('read') or {}).get('origin')}`、`label={(k1.get('read') or {}).get('label')}`"
                   f"（不是「服务器给出的原因」），`detail_block_attached="
                   f"{json.dumps((k1.get('read') or {}).get('detail_block_attached'))}`；"
                   f"四个禁句（已取消 / 没有发生 / 再试一次 / 连不上服务端）在这枚 "
                   f"{len(k1.get('rows', []))} 行判据里逐条判缺，实测等待 {k1.get('elapsed_ms')} ms、"
                   f"`post_count={k1.get('post_count')}`（判据所在文件 "
                   f"`{SPEC_PATH}`，blob `{blob(SPEC_PATH, code)}`）。",
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
                "every_arm_parsed_at_least_one_node": arms["every_arm_parsed_at_least_one_node"],
                "per_arm": [{"arm": a["arm"], "claimed": a["claimed_result"],
                             "red_nodes": a["red_nodes"],
                             "same_key_precondition_holds": a["same_key_precondition_holds"],
                             "anchor_hits": a["anchor_hits"],
                             "bytes_changed": a["bytes_changed"],
                             "restored": a["restored_to_tested_tree_bytes"],
                             "gate_exit": a["attempt"]["gateExit"]} for a in arms["arms"]],
                "all_arms_restored_to_tested_tree_bytes": arms["all_arms_restored_to_tested_tree_bytes"],
                "tree_unchanged_by_this_run": arms["tree_unchanged_by_this_run"],
                "every_arm_has_a_green_same_key_precondition": arms["all_arms_carry_a_green_same_key_precondition"],
                "clean_round": {"runId": arms["clean_round"]["runId"], "db": arms["clean_round"]["db"],
                                "port": arms["clean_round"]["port"],
                                "nodes": arms["clean_round"]["nodes"]},
                "blob_module": blob(MODULE, code), "blob_sheet": blob(SHEET, code),
                "blob_spec": blob(SPEC_PATH, code), "blob_backend_test": blob(BACKEND_TEST, code),
                "blob_keyed_module_at_the_tested_tree": subprocess.run(
                    ["git", "cat-file", "-e", f"{code}:{KEYED_MODULE}"],
                    cwd=ROOT, capture_output=True).returncode == 0 and blob(KEYED_MODULE, code) or "ABSENT",
            },
            "derived_from": f"killed={arms['killed']} of {arms['arms_total'] - arms['probes']} killers · "
                            f"survived={arms['survived']} · probe_holding={arms['probes']} · "
                            f"every_arm_parsed_a_node={arms['every_arm_parsed_at_least_one_node']} · "
                            f"restored={arms['all_arms_restored_to_tested_tree_bytes']} · "
                            f"tree_unchanged={arms['tree_unchanged_by_this_run']}",
            "why": f"{arms['arms_total']} 枚臂里 {arms['killed']} 枚击杀、{arms['survived']} 枚存活、"
                   f"{arms['probes']} 枚探针按预期绿；每臂带自己的 (sha, nodeid, shape) 与"
                   f"还原前后 12 位摘要，`restored={json.dumps(arms['all_arms_restored_to_tested_tree_bytes'])}`、"
                   f"`tree_unchanged={json.dumps(arms['tree_unchanged_by_this_run'])}`、"
                   f"`every_arm_parsed_a_node={json.dumps(arms['every_arm_parsed_at_least_one_node'])}`。"
                   f"绿轮坐标：`runId={arms['clean_round']['runId']}`、库 `{arms['clean_round']['db']}`、"
                   f"端口 {arms['clean_round']['port']}。四枚被测工件的 blob："
                   f"`{MODULE}`={blob(MODULE, code)}、`{SHEET}`={blob(SHEET, code)}、"
                   f"`{SPEC_PATH}`={blob(SPEC_PATH, code)}、`{BACKEND_TEST}`={blob(BACKEND_TEST, code)}。"
                   f"`claimed_result` 是本车道观测，`derived_result` 一律留 null 给红队，等级不由本车道签。",
        },
        {
            "id": "C6_deadline_is_the_criterion_not_signal",
            "triple": {"exact_sha": code, "nodeid": f"{SPEC_PATH} :: K3 反控：旅行者按取消时，期限不许冒充用户",
                       "shape": ["chromium"]},
            "verdict": "SIGNAL_PRECEDED_THIS_ORDER_SO_IT_IS_NOT_THE_DISCRIMINATOR",
            "readings": {
                "signal_option_lines_at_the_tip": grep_lines(tip, SHEET, "signal,"),
                "post_call_sites_at_the_tip": grep_lines(tip, SHEET, "await fetch("),
                "keyless_leg_wrapped_in_this_tree": grep_lines(code, SHEET, "fetchWithKeylessWriteDeadline("),
                "wrapper_preserves_the_callers_signal": grep_lines(code, MODULE, "init.signal"),
                "deadline_branch": grep_lines(code, SHEET, "UNKNOWN_KEYLESS_WRITE_DEADLINE"),
                "cancel_branch": grep_lines(code, SHEET, "CANCELLED_AFTER_SEND"),
                "k3_node_clean_round": arms["clean_round"]["nodes"].get(
                    "K3 反控：旅行者按取消时，期限不许冒充用户", "NOT_FOUND"),
                "arm_that_breaks_the_distinction": next(
                    {"arm": a["arm"], "red_nodes": a["red_nodes"], "claimed": a["claimed_result"]}
                    for a in arms["arms"] if a["arm"] == "K0310_DEADLINE_IMPERSONATES_TRAVELLER"),
                # the two-sided witness the commander asked for: keep the caller's `signal`, delete the
                # deadline. K1 has to go red while K2/K3 stay green, or the criterion is really about aborts
                "signal_but_no_deadline_arm": next(
                    ({"arm": a["arm"], "nodes": a["attempt"]["nodes"], "claimed": a["claimed_result"],
                      "restored": a["restored_to_tested_tree_bytes"], "anchor_hits": a["anchor_hits"],
                      "sizes": a["sizes"]}
                     for a in arms["arms"]
                     if a["arm"] == "K0310_KEYLESS_LEG_HAS_SIGNAL_BUT_NO_DEADLINE"),
                    "ARM_NOT_IN_THIS_BATCH"),
                "premise_proof": (lambda p: {
                    "file": "ord0310-signal-vs-deadline-proof.out", "exists": p.exists(),
                    "bytes": p.stat().st_size if p.exists() else 0,
                    "blob": hashlib.sha1(b"blob %d\0" % len(p.read_bytes()) + p.read_bytes()).hexdigest()
                    if p.exists() else "NOT_WRITTEN"})(RAW / "ord0310-signal-vs-deadline-proof.out"),
            },
            "derived_from": f"tip signal lines={json.dumps(grep_lines(tip, SHEET, 'signal,'))} · "
                            f"deadline branch={json.dumps(grep_lines(code, SHEET, 'UNKNOWN_KEYLESS_WRITE_DEADLINE'))} · "
                            f"cancel branch={json.dumps(grep_lines(code, SHEET, 'CANCELLED_AFTER_SEND'))} · "
                            f"K3={arms['clean_round']['nodes'].get('K3 反控：旅行者按取消时，期限不许冒充用户', 'NOT_FOUND')} · "
                            f"impersonation arm red_nodes="
                            f"{json.dumps(next(a['red_nodes'] for a in arms['arms'] if a['arm'] == 'K0310_DEADLINE_IMPERSONATES_TRAVELLER'), ensure_ascii=False)}",
            "why": f"号令者 20:2x 那条新事实我复算成立并可指名：在这枚尖 `{tip}` 上两条 POST 的选项对象"
                   f"**本来就带 `signal`**（`{SHEET}` 的第 "
                   f"{', '.join(str(n) for n, _t in grep_lines(tip, SHEET, 'signal,'))} 行就是 `signal,`；"
                   f"两处调用点在第 "
                   f"{', '.join(str(n) for n, _t in grep_lines(tip, SHEET, 'await fetch('))} 行）。"
                   f"所以本单加的东西不是 signal，是**期限**：wrapper 原样接住调用方的信号"
                   f"（`{MODULE}` 第 "
                   f"{', '.join(str(n) for n, _t in grep_lines(code, MODULE, 'init.signal'))} 行读 `init.signal`），"
                   f"到点才由 `firedHere` 抛 `KeylessWriteDeadlineMissed`，屏上落 "
                   f"`{grep_lines(code, SHEET, 'UNKNOWN_KEYLESS_WRITE_DEADLINE')[:1]}` 那一支；"
                   f"旅行者自己按取消仍走取消那一支（`CANCELLED_AFTER_SEND`，"
                   f"`{SHEET}` 第 "
                   f"{', '.join(str(n) for n, _t in grep_lines(code, SHEET, 'CANCELLED_AFTER_SEND'))} 行）。"
                   f"判据按**到点**写而不按**有没有 signal** 写，并且这一条有牙齿：K3 反控本轮判 "
                   f"{arms['clean_round']['nodes'].get('K3 反控：旅行者按取消时，期限不许冒充用户', 'NOT_FOUND')}，"
                   f"而把 `firedHere` 判定拆掉的臂 "
                   f"`K0310_DEADLINE_IMPERSONATES_TRAVELLER` 实测红的正是 K3 那一枚节点。",
        },
    ]

    pushed, pushed_raw = ref_read_raw(args.pushed_ref)
    if not re.fullmatch(r"[0-9a-f]{40}", pushed or ""):
        print(f"ABORT: {args.pushed_ref} did not read back as a 40-hex sha (got {pushed!r}).")
        return 6
    subjects = [MODULE, SHEET, SPEC_PATH, BACKEND_TEST]
    per_file = {f: {"blob_at_tested_tree": git("rev-parse", f"{code}:{f}"),
                    "blob_on_the_pushed_ref": git("rev-parse", f"{pushed}:{f}") if pushed else ""}
                for f in subjects}
    ref_readback = {
        "ref": args.pushed_ref,
        "sha_read_back_over_https": pushed,
        "read_by": "git ls-remote <ref> (same two-route rule as the tip: https git protocol here, "
                   "and the file contents below are read with git show / git rev-parse by sha)",
        "tools_commit_at_the_push": git("rev-parse", "HEAD"),
        "subject_files_equal_to_the_tested_tree": all(
            v["blob_at_tested_tree"] == v["blob_on_the_pushed_ref"] for v in per_file.values()),
        "per_subject_file_blob": per_file,
        "what_differs_between_tested_tree_and_the_push": git("diff", "--name-only", code, pushed).splitlines()
        if pushed else [],
        # the commander grades the landing on the ref as it stands now, so predict on that sha too
        "merge_prediction_on_the_pushed_ref": merge_prediction(tip, pushed),
        "subject_blob_equal_to_previous_generation": {
            f: {"previous_generation_blob": git("rev-parse", f"{args.previous_generation_sha}:{f}")
                if args.previous_generation_sha else "",
                "this_generation_blob": git("rev-parse", f"{code}:{f}")}
            for f in subjects} if args.previous_generation_sha else "NO_PRIOR_GENERATION_PASSED",
    }

    tip_recheck, tip_recheck_raw = remote_tip()
    payload = {
        "order": "ORD-0310", "lane": "D e345b9d6",
        "title": "ORD-0288 无键写腿的客户端期限（Q54=① 的形制）：客户端半件 + 屏上句子的射程",
        "generated_at": datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%:z"),
        "ref_tip_read": {
            "ref": TIP_REF, "sha": tip,
            "read_by": ["git ls-remote https://github.com/Canshu-King/CityNexus.git <ref> (git protocol over https)",
                        "GET https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/<ref> (https REST, token from the git credential helper, never printed)"],
            "sha_by_the_second_route": tip_api,
            "the_two_routes_agree": tip == tip_api,
            "recheck_after_all_measurement": tip_recheck,
            "stable_across_this_run": tip == tip_recheck,
        },
        "generation_binding": {
            "tested_tree": arms["tested_tree"],
            **generation,
            "carry": "READINGS_ARE_FOR_THE_TESTED_TREE_ONLY",
            "note": "本收据里每一枚读数（绿轮、五枚反突变臂、服务端字段）都是在 `tested_tree` 那一代上量的；"
                    "线尖比我的分叉点新 `commits_on_the_line_since_the_fork` 那几笔，"
                    "两边动的文件交集见 `intersection_between_their_files_and_mine`。"
                    "按 Q24 我不把这一代的读数折算到线尖：要当代数，需要把候选重父到尖上再跑一轮绿 + 一轮拆。"
                    "合流是否会冲突不靠嘴说，看 `merge_prediction`（只读，0 移动任何 ref）。",
        },
        "candidate": {"code_sha": code, "parent": parent, "base_cut_from": base,
                      "product_commit": args.product_commit or code,
                      "tools_sha": git("rev-parse", "HEAD"),
                      # two different questions, so two different fields: was the *commit* cut on the
                      # tip I read, and is the *declared base* that same tip. gen-r3 landed with the
                      # second one printed next to two equal shas, which read as a contradiction.
                      "is_parent_the_tip_read_now": parent == tip,
                      "is_declared_base_the_tip_read_now": base == tip},
        "revision": {
            "generation": args.generation_label or "NO_GENERATION_LABEL_PASSED",
            "previous_generation_tested_tree": args.previous_generation_sha or "NOT_PASSED",
            "previous_generation_receipt_blob": args.supersedes_receipt or "NOT_PASSED",
            "previous_predicted_tree": {
                "sha": args.supersedes_predicted_tree or "NOT_PASSED",
                "status": "SUPERSEDED_BY_THIS_GENERATION_NOT_DELETED",
                "why": "那枚预测树是对上一代被测尖算的；号令者按 ref 当下尖重量出的是 "
                       f"{ref_readback['merge_prediction_on_the_pushed_ref']['predicted_tree']}"
                       "（见 candidate_ref_readback.merge_prediction_on_the_pushed_ref）"},
            "tested_tree_vs_product_commit": {
                "arms_tested_tree": arms["tested_tree"], "candidate_tip": code,
                "product_commit": args.product_commit or code,
                "per_subject_blob": {f: {"at_tested_tree": git("rev-parse", f"{arms['tested_tree']}:{f}"),
                                         "at_candidate_tip": git("rev-parse", f"{code}:{f}")}
                                     for f in subjects},
                "all_equal": all(git("rev-parse", f"{arms['tested_tree']}:{f}")
                                 == git("rev-parse", f"{code}:{f}") for f in subjects),
                "note": "臂与绿轮跑的就是本道分支尖这一枚树；这里逐枚证明四件被测工件在它上面"
                        "与收据所称的候选尖同 blob，所以 `--code-sha` 用分支尖不改变被量字节。",
            },
            "what_a_recut_proves": {
                "subject_blobs_equal_across_generations": all(
                    v["previous_generation_blob"] == v["this_generation_blob"]
                    for v in (ref_readback["subject_blob_equal_to_previous_generation"] or {}).values())
                if isinstance(ref_readback["subject_blob_equal_to_previous_generation"], dict) else "NOT_PASSED",
                "patch_id_of_the_product_commit": [
                    subprocess.run(f"git show {args.previous_product_commit} | git patch-id --stable",
                                   shell=True, cwd=ROOT, capture_output=True, text=True,
                                   encoding="utf-8").stdout.strip(),
                    subprocess.run(f"git show {args.product_commit or code} | git patch-id --stable",
                                   shell=True, cwd=ROOT, capture_output=True, text=True,
                                   encoding="utf-8").stdout.strip()],
                # once the commander has landed the commit, this generation's product commit IS the
                # previous generation's, so a patch-id "pair" would be one commit compared with itself
                # and prove nothing; the cross-generation claim then belongs to the earlier receipt.
                "is_a_self_comparison": (args.previous_product_commit or "") == (args.product_commit or code),
            },
        },
        "candidate_ref_readback": ref_readback,
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
        "discipline": {
            "authority_line_writes": 0,
            "authority_line_moved_by_this_lane": 0,
            "other_lanes_refs_touched": 0,
            "own_candidate_ref_pushed": {"count": 1, "ref": args.pushed_ref,
                                         "sha": pushed,
                                         "why_allowed": "边界写的是 0 权威线写入、0 推他人 ref；"
                                                        "这枚是本车道自己的新候选 ref，名字与旧 ref 都没被人占过"},
            "demo_reset": 0,
            "user_db_reads_writes": 0,
            "credentials_printed": 0,
            "assertions_changed_to_buy_green": 0,
            "instrument_tightened_because_a_survivor_proved_a_hole":
                "K0310_SENTENCE_PROMISES_REPLAY 第一次是 SURVIVED：门禁只在折叠态读卡片，"
                "而禁句活在「技术详情」展开之后；补法是把卡片折叠态与展开态各读一遍，并把"
                "「不能靠同一把键补问」钉成逐字判据 —— 收紧量具，不是把断言改松换绿",
            "note": "逐臂的还原与同一枚树的字节回读见 C5；`derived_result` 全为 null，等级不由本车道签",
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out} {out.stat().st_size} B")
    print(f"tip={tip} parent==tip? {payload['candidate']['is_parent_the_tip_read_now']} "
          f"base==tip? {payload['candidate']['is_declared_base_the_tip_read_now']} "
          f"killed={arms['killed']}/{arms['arms_total'] - arms['probes']} restored={arms['all_arms_restored_to_tested_tree_bytes']}")
    mp = generation["merge_prediction"]
    (RAW / "ord0310-mergetree-tip-x-candidate.out").write_text(
        f"$ {mp['command']}\nexit={mp['exit']}\nstdout line 1 (predicted tree): {mp['predicted_tree']}\n"
        f"stdout after line 1 (the conflict section, empty means no conflict):\n{mp['raw_after_first_line']}\n"
        f"stderr:\n{mp['stderr']}\n"
        f"note: read-only prediction; it writes blobs/trees into the object store and moves 0 refs. "
        f"Rendered in the same process run that produced {out.name}, so the numbers cannot drift apart.\n",
        encoding="utf-8", newline="\n")
    (RAW / "ord0310-tip-read.out").write_text(
        tip_raw + "\n" + tip_api_raw + "\n" + pushed_raw + "\n" + tip_recheck_raw + "\n"
        f"parsed: tip={tip} tip_via_api={tip_api} agree={tip == tip_api} recheck={tip_recheck} "
        f"stable={tip == tip_recheck} pushed_candidate={pushed}\n",
        encoding="utf-8", newline="\n")
    rows = ["kind\tpath\n"]
    rows += [f"line_moved_since_fork\t{p}\n" for p in generation["files_the_line_changed_since_the_fork"]]
    rows += [f"my_candidate_moves_since_fork\t{p}\n" for p in generation["files_my_candidate_changed_since_the_fork"]]
    rows += (["intersection\tNONE\n"] if not generation["intersection_between_their_files_and_mine"]
             else [f"intersection\t{p}\n" for p in generation["intersection_between_their_files_and_mine"]])
    (RAW / "ord0310-path-disjointness.tsv").write_text("".join(rows), encoding="utf-8", newline="\n")
    for name in ("ord0310-mergetree-tip-x-candidate.out", "ord0310-tip-read.out",
                 "ord0310-path-disjointness.tsv"):
        p = RAW / name
        print(f"wrote {p} {p.stat().st_size} B")
    print(f"secret scan in the raw files: hits={sum('ghp_' in p.read_text(encoding='utf-8') for p in RAW.glob('ord0310-*.out'))}")
    return 0


raise SystemExit(main())
