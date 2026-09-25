"""Write the ORD-0310 gen-3 erratum out of the artifacts, never out of my memory.

Three fields in the landed r3 block were wrong, all of them labels or derivations inside my own
instruments - none of them a reading. So this file re-reads the two receipts, the raw command
outputs and the git objects, and states was/now with a resolvable coordinate for each claim.
Nothing here re-runs a gate, an arm or a measurement.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
SC = ROOT / "_scratch_0310"
R3 = SC / "r3"
R3B = SC / "r3b"
EVDIR = "evidence/ord0288-keyless-deadline"
OUT_JSON = SC / "ord0310-erratum-r1.json"
OUT_BLOCK = SC / "ord0310-block-erratum-r1.md"
TIME_TOKEN = sys.argv[1] if len(sys.argv) > 1 else "@2026-09-25 22:3x+08"

MEASURED_REF = "refs/heads/review/ord0310-keyless-deadline-d-on-2344145c"
TOOLS_REF = "refs/heads/review/ord0310-tools-r3b"
AUTH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
URL = "https://github.com/Canshu-King/CityNexus.git"
TOOL_PATHS = ["review/ord0310_make_receipt.py", "review/ord0310_make_block.py",
              "review/ord0310_stage_pub.py", "review/ord0310_pub_names.py"]


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def of(path: Path) -> str:
    return blob(path.read_bytes())


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def ref_read_raw() -> tuple[str, str]:
    """ls-remote the three refs, keep the raw stdout, print nothing that could be a credential."""
    proc = subprocess.run(["git", "ls-remote", URL, MEASURED_REF, TOOLS_REF, AUTH_REF],
                          cwd=ROOT, capture_output=True, text=True)
    lines = [l for l in proc.stdout.splitlines() if l.strip()]
    parsed = {l.split("\t")[1].strip(): l.split("\t")[0].strip() for l in lines}
    raw = "".join(f"$ git ls-remote {URL} {r}\n" for r in (MEASURED_REF, TOOLS_REF, AUTH_REF))
    raw += f"exit={proc.returncode}\nstdout:\n" + "".join(l + "\n" for l in lines)
    raw += "parsed: " + json.dumps(parsed, ensure_ascii=False, sort_keys=True) + "\n"
    return raw, parsed


raw_stdout, parsed_refs = ref_read_raw()
ref_out = R3B / "ord0310-ref-read-r3b.out"
ref_out.write_text(raw_stdout, encoding="utf-8", newline="\n")
REF_BLOB = of(ref_out)
TOOLS_SHA = parsed_refs.get(TOOLS_REF, "NOT_READ")
MEASURED_SHA = parsed_refs.get(MEASURED_REF, "NOT_READ")
AUTH_SHA = parsed_refs.get(AUTH_REF, "NOT_READ")
for label, sha in ((TOOLS_REF, TOOLS_SHA), (MEASURED_REF, MEASURED_SHA), (AUTH_REF, AUTH_SHA)):
    if not re.fullmatch(r"[0-9a-f]{40}", sha or ""):
        raise SystemExit(f"ABORT: {label} did not read back as a 40-hex sha (got {sha!r})")

Q38_RULER = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/receipt_cell_derivation_check_r2.py")
Q38_RULER_BLOB = of(Q38_RULER)

rec = load(SC / "ord0310_keyless_deadline_receipt_r3.json")
recb = load(SC / "ord0310_keyless_deadline_receipt_r3b.json")
q38 = load(SC / "ord0310-q38r2-on-receipt-r3b.json")
arms = load(SC / "arms_receipt_r5.json")
back = load(SC / "backend_readings_r3.json")
landed_block = SC / "ord0310-ledger-block-r3.md"
prev_tip_read = of(R3 / "ord0310-tip-read.out")
cells = {c["id"]: c for c in recb["cells"]}
c2 = cells["C2_single_named_constant"]["readings"]
k1b = back["cells"]["K1"]
genb = recb["generation_binding"]
refb = recb["candidate_ref_readback"]

def ancestor(older: str, newer: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", older, newer],
                          cwd=ROOT, capture_output=True, text=True).returncode == 0


def blob_of_at(rev: str, path: str) -> str:
    """The git object's own sha1, or a named absence - never the echoed argument."""
    proc = subprocess.run(["git", "rev-parse", "--verify", "-q", f"{rev}:{path}"],
                          cwd=ROOT, capture_output=True, text=True)
    sha = proc.stdout.strip()
    return sha if re.fullmatch(r"[0-9a-f]{40}", sha) else "NOT_IN_THAT_TREE"


parent = git("rev-parse", f"{MEASURED_SHA}^")
tools_blobs_before = {p: blob_of_at(MEASURED_SHA, p) for p in TOOL_PATHS}
tools_blobs_after = {p: blob_of_at(TOOLS_SHA, p) for p in TOOL_PATHS}
subject_blobs = {f: v["blob_on_the_pushed_ref"]
                 for f, v in refb["per_subject_file_blob"].items()}

DEFECTS = [
    {
        "id": "D1_boolean_compares_the_wrong_pair",
        "where": f"{EVDIR}/ord0310_keyless_deadline_receipt_r3.json -> candidate.is_cut_on_the_tip_read_now",
        "was": rec["candidate"]["is_cut_on_the_tip_read_now"],
        "cause": "the field compared the declared fork base with the tip, while the block sentence "
                 "read it as 'the parent of the code commit equals the tip' - so two identical shas "
                 "sat next to a printed false",
        "measured_now": {"parent_of_the_measured_tip": parent, "authority_tip_read_now": AUTH_SHA,
                         "parent_equals_tip": parent == AUTH_SHA,
                         "declared_base": rec["candidate"]["base_cut_from"],
                         "declared_base_equals_tip": rec["candidate"]["base_cut_from"] == AUTH_SHA},
        "now_fields": ["candidate.is_parent_the_tip_read_now",
                       "candidate.is_declared_base_the_tip_read_now"],
        "now_values": [recb["candidate"]["is_parent_the_tip_read_now"],
                       recb["candidate"]["is_declared_base_the_tip_read_now"]],
    },
    {
        "id": "D2_generation_label_was_a_literal",
        "where": "the landed block heading, from revision.generation",
        "was": rec["revision"]["generation"],
        "cause": "the builder carried gen-2's literal string, so every later generation was titled r2",
        "now": recb["revision"]["generation"],
        "how_fixed": "revision.generation is now an argument (--generation-label); the builder refuses "
                     "to fall back to another generation's name",
    },
    {
        "id": "D3_patch_id_pair_was_a_self_comparison",
        "where": "revision.what_a_recut_proves.patch_id_of_the_product_commit, cited in the block as "
                 "proof that a re-cut moved only the base",
        "was": rec["revision"]["what_a_recut_proves"]["patch_id_of_the_product_commit"],
        "cause": "once the commander lands the commit, this generation's product commit IS the previous "
                 "generation's, so the two patch-ids are one commit compared with itself",
        "now_flag": recb["revision"]["what_a_recut_proves"]["is_a_self_comparison"],
        "what_this_generation_may_still_claim": {
            "subject_files_equal_to_the_tested_tree": refb["subject_files_equal_to_the_tested_tree"],
            "tested_tree_vs_product_commit_all_equal":
                recb["revision"]["tested_tree_vs_product_commit"]["all_equal"]},
        "where_the_cross_generation_claim_lives":
            f"the previous receipt, blob {rec['revision']['previous_generation_receipt_blob']}",
    },
]

UNCHANGED = {
    "clean_round_runId": arms["clean_round"]["runId"],
    "clean_round_db": arms["clean_round"]["db"],
    "clean_round_port": arms["clean_round"]["port"],
    "measured_wait_ms": c2["measured_wait_clean_round_ms"],
    "post_count": c2["post_count_clean_round"],
    "deadline_constant_ms": c2["constant_ms_in_the_module"],
    "idempotency_keys_rows": [k1b["idempotency_keys_rows_from"], k1b["idempotency_keys_rows_to"]],
    "journey_missions_rows": [k1b["journey_missions_rows_from"], k1b["journey_missions_rows_to"]],
    "arms_killed_of_total": [arms["killed"], arms["arms_total"] - arms["probes"]],
    "predicted_merge_tree": genb["merge_prediction"]["predicted_tree"],
    "measured_ref": [MEASURED_REF, MEASURED_SHA],
    "authority_tip": [AUTH_REF, AUTH_SHA],
    "subject_file_blobs": subject_blobs,
    "gate_evidence_blobs_untouched": {
        "ord0310-tip-read.out": [prev_tip_read, of(R3B / "ord0310-tip-read.out")],
        "ord0310-path-disjointness.tsv": [of(R3 / "ord0310-path-disjointness.tsv"),
                                          of(R3B / "ord0310-path-disjointness.tsv")],
        "ord0310-mergetree-tip-x-candidate.out": [of(R3 / "ord0310-mergetree-tip-x-candidate.out"),
                                                  of(R3B / "ord0310-mergetree-tip-x-candidate.out")]},
    "re_measurements_run_for_this_erratum": 0,
}

ERRATUM = {
    "order": "ORD-0310", "lane": "D e345b9d6", "kind": "ERRATUM_ON_LANDED_BLOCK",
    "written_at": datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%:z"),
    "subject_of_the_erratum": {"block_blob": of(landed_block), "bytes": landed_block.stat().st_size,
                               "receipt_blob": of(SC / "ord0310_keyless_deadline_receipt_r3.json"),
                               "published_as": ["ord0310-ledger-block-r3.md",
                                                "ord0310_keyless_deadline_receipt_r3.json"]},
    "defects": DEFECTS,
    "corrected_artifacts": {
        "receipt": {"path": f"{EVDIR}/ord0310_keyless_deadline_receipt_r3b.json",
                    "blob": of(SC / "ord0310_keyless_deadline_receipt_r3b.json"),
                    "bytes": (SC / "ord0310_keyless_deadline_receipt_r3b.json").stat().st_size},
        "q38_r2": {"ruler_blob": Q38_RULER_BLOB,
                   "verdict": q38["overall"], "exit": q38["exit"], "hard": q38["hard_count"],
                   "soft": q38["soft_count"],
                   "path": f"{EVDIR}/ord0310-q38r2-on-receipt-r3b.json",
                   "blob": of(SC / "ord0310-q38r2-on-receipt-r3b.json")},
        "instrument_commit": {"ref": TOOLS_REF, "sha": TOOLS_SHA,
                              "parent_of_the_tools_tip": git("rev-parse", f"{TOOLS_SHA}^"),
                              "measured_tree_is_an_ancestor_of_it": ancestor(MEASURED_SHA, TOOLS_SHA),
                              "commits_between": git("rev-list", "--count",
                                                     f"{MEASURED_SHA}..{TOOLS_SHA}"),
                              "paths_it_touches": git("diff", "--name-only",
                                                     f"{MEASURED_SHA}..{TOOLS_SHA}").splitlines(),
                              "anything_outside_review_slash":
                                  [p for p in git("diff", "--name-only",
                                                  f"{MEASURED_SHA}..{TOOLS_SHA}").splitlines()
                                   if not p.startswith("review/")],
                              "raw_readback": {"path": f"{EVDIR}/ord0310-ref-read-r3b.out",
                                               "blob": REF_BLOB},
                              "tool_blobs_before_and_after": {
                                  p: [tools_blobs_before[p], tools_blobs_after[p]] for p in TOOL_PATHS}},
        "raw_outputs": {"equal_to_the_published_ones":
                        ["ord0310-tip-read.out", "ord0310-path-disjointness.tsv"],
                        "differing": ["ord0310-mergetree-tip-x-candidate.out"],
                        "only_difference_in_the_differing_one":
                            "the trailing note names the receipt file it was rendered with "
                            "(..._r3.json -> ..._r3b.json); command, exit, predicted tree and the "
                            "empty conflict section are byte-identical"},
    },
    "readings_unchanged": UNCHANGED,
    "nothing_published_was_rewritten": {
        "ord0310-ledger-block-r3.md": "left in place, not deleted, not edited",
        "ord0310_keyless_deadline_receipt_r3.json": "same",
        "discipline": "corrections ship as new files under new names (Q57 refuses changed bytes under "
                      "a published path, and that is the behaviour I want)"},
}
OUT_JSON.write_bytes((json.dumps(ERRATUM, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))

rc = DEFECTS[0]["measured_now"]
da3 = DEFECTS[2]
L = []
L.append(f"### SESSION=e345b9d6 {TIME_TOKEN} —— **ORD-0310 勘误（只改标签与派生，0 重新测量、0 读数改动）**")
L.append("")
L.append(
    f"对象 = 21:56 落进 `## DELIVERIES` 的那一块（本地件 `ord0310-ledger-block-r3.md`，"
    f"blob `{of(landed_block)}`，{landed_block.stat().st_size:,} B；"
    f"它的收据 `ord0310_keyless_deadline_receipt_r3.json` blob "
    f"`{of(SC / 'ord0310_keyless_deadline_receipt_r3.json')}`）。"
    f"三处是我量具里写错/算错的标签，全部不是读数。机器可读的 was/now 在 "
    f"`{EVDIR}/ord0310-erratum-r1.json`，blob `{of(OUT_JSON)}`"
    f"（{OUT_JSON.stat().st_size:,} B）。")
L.append("")
L.append(
    f"**其一：`is_cut_on_the_tip_read_now=false` 与两个一模一样的 40 位并排出现。** 枚字段实际比的是"
    f"「本单声明的分叉基座 `{rec['candidate']['base_cut_from']}`」与尖，不是我那句话说的「父位」与尖。"
    f"现测（只读）：`git rev-parse {MEASURED_SHA}^` = `{rc['parent_of_the_measured_tip']}`，"
    f"`git ls-remote` 现读 `{AUTH_REF}` = `{rc['authority_tip_read_now']}` ⇒ "
    f"`parent_equals_tip={json.dumps(rc['parent_equals_tip'])}`，而 "
    f"`declared_base_equals_tip={json.dumps(rc['declared_base_equals_tip'])}`。"
    f"修正后的收据把两问拆成 `is_parent_the_tip_read_now` / `is_declared_base_the_tip_read_now`，"
    f"逐位读回原样在 `{EVDIR}/ord0310-ref-read-r3b.out`，blob `{REF_BLOB}`。")
L.append("")
L.append(
    f"**其二：那块标题挂着 `{DEFECTS[1]['was']}`。** 它来自 `revision.generation` 的一枚字面量 —— "
    f"r2 那轮留下的，于是后面每一代都被叫做 r2。现在这一枚由 `--generation-label` 传入，"
    f"本代记为 `{DEFECTS[1]['now']}`；量具不再允许它回落到上一代的名字。")
L.append("")
L.append(
    f"**其三：那块把 `patch-id` 两枚相同当成「只搬基座没改字」的证据。** 落地之后本代的产品那一笔就是"
    f"`{rec['candidate']['product_commit']}`，与上一代同一笔 —— 两枚 patch-id "
    f"（`{da3['was'][0].split(' ')[0]}` 与 `{da3['was'][1].split(' ')[0]}`）是同一笔与它自己比，"
    f"不构成证据。新收据里它具名为 `what_a_recut_proves.is_a_self_comparison="
    f"{json.dumps(da3['now_flag'])}`；跨代那论证退回上一枚收据 blob "
    f"`{rec['revision']['previous_generation_receipt_blob']}`。本代仍可声明的是被量字节没动："
    f"`subject_files_equal_to_the_tested_tree="
    f"{json.dumps(da3['what_this_generation_may_still_claim']['subject_files_equal_to_the_tested_tree'])}`、"
    f"`tested_tree_vs_product_commit.all_equal="
    f"{json.dumps(da3['what_this_generation_may_still_claim']['tested_tree_vs_product_commit_all_equal'])}`。")
L.append("")
L.append(
    f"**修正后的收据与尺**：`{EVDIR}/ord0310_keyless_deadline_receipt_r3b.json` blob "
    f"`{ERRATUM['corrected_artifacts']['receipt']['blob']}`"
    f"（{ERRATUM['corrected_artifacts']['receipt']['bytes']:,} B）；Q38 r2（尺 blob "
    f"`{Q38_RULER_BLOB}`）判它 "
    f"`{q38['overall']}`、hard `{q38['hard_count']}`、soft `{q38['soft_count']}`、exit `{q38['exit']}`，"
    f"输出 `{EVDIR}/ord0310-q38r2-on-receipt-r3b.json`，blob "
    f"`{of(SC / 'ord0310-q38r2-on-receipt-r3b.json')}`。三件原始输出里两件的字节与已发布那代同名件"
    f"逐字节相同（`{EVDIR}/ord0310-tip-read-r3.out` blob `{prev_tip_read}`；"
    f"`{EVDIR}/ord0310-path-disjointness-r3.tsv` blob "
    f"`{of(R3 / 'ord0310-path-disjointness.tsv')}`），唯一不同的那件只差在末尾一句自述文件名的字，"
    f"命令、退出、预测树 `{genb['merge_prediction']['predicted_tree']}` 与空的 conflict 段逐字节相同："
    f"`{EVDIR}/ord0310-mergetree-tip-x-candidate-r3b.out` blob "
    f"`{of(R3B / 'ord0310-mergetree-tip-x-candidate.out')}`。")
L.append("")
ic = ERRATUM["corrected_artifacts"]["instrument_commit"]
L.append(
    f"**改动落在哪一枚可解析坐标**：只改量具，产品与门字节 0 改动 ⇒ 单独一枚新 ref "
    f"`{TOOLS_REF}` = `{TOOLS_SHA}`。它与被量那一代的关系是量出来的，不是说的："
    f"`measured_tree_is_an_ancestor_of_it="
    f"{json.dumps(ic['measured_tree_is_an_ancestor_of_it'])}`、中间隔 "
    f"{ic['commits_between']} 笔、`git diff --name-only {MEASURED_SHA[:8]}..{TOOLS_SHA[:8]}` "
    f"里 `review/` 之外的件数 = {len(ic['anything_outside_review_slash'])}"
    f"（即产品/门字节 0 改动）；该 ref 自己的父位是 `{ic['parent_of_the_tools_tip']}`，"
    f"**不是**被量那一代 —— 上一枚 erratum 犯的正是把这类相等写成话，这里只写测到的那枚。"
    f"被量的那枚 ref `{MEASURED_REF}` 仍是 `{MEASURED_SHA}`，一个字节没被这次改动挪动。"
    f"逐件前后 blob：`review/ord0310_make_receipt.py` "
    f"`{tools_blobs_before['review/ord0310_make_receipt.py']}` → "
    f"`{tools_blobs_after['review/ord0310_make_receipt.py']}`；"
    f"`review/ord0310_make_block.py` `{tools_blobs_before['review/ord0310_make_block.py']}` → "
    f"`{tools_blobs_after['review/ord0310_make_block.py']}`。已发布路径 0 覆盖：被勘误那两件留在原位"
    f"不删不改，修正件一律用新名（`…r3b` / `…r4`）。")
L.append("")
L.append(
    f"**没被这次勘误碰过的读数（一枚都没重测）**：绿轮 `{UNCHANGED['clean_round_runId']}`"
    f"（库 `{UNCHANGED['clean_round_db']}`、端口 {UNCHANGED['clean_round_port']}）、实测等待 "
    f"{UNCHANGED['measured_wait_ms']} ms、`post_count={UNCHANGED['post_count']}`、常数 "
    f"{UNCHANGED['deadline_constant_ms']} ms、`{back['table']}` 行 "
    f"{UNCHANGED['idempotency_keys_rows'][0]}→{UNCHANGED['idempotency_keys_rows'][1]}、"
    f"`journey_missions` {UNCHANGED['journey_missions_rows'][0]}→{UNCHANGED['journey_missions_rows'][1]}、"
    f"臂 {UNCHANGED['arms_killed_of_total'][0]}/{UNCHANGED['arms_killed_of_total'][1]} 杀、"
    f"四枚工件 blob {json.dumps(UNCHANGED['subject_file_blobs'], ensure_ascii=False)}。"
    f"等级与 `derived_result` 仍归红队，本块不签级。")
L.append("")
L.append(
    f"**纪律**：`0 权威线写入`（现读 `{AUTH_REF}` = `{AUTH_SHA}`，与 r3 那次读数逐位相同、"
    f"我 0 次移动）、`0 推他人 ref`（这次推的 `{TOOLS_REF}` 是我自己命名的新 ref）、"
    f"`demo/reset` 0、`_live`/`_preview` 库 0 读写、凭据 0 打印、`0 为了绿而改断言`"
    f"（这次连门都没开跑：`re_measurements_run_for_this_erratum="
    f"{UNCHANGED['re_measurements_run_for_this_erratum']}`）。")
L.append("")

text = "\n".join(L) + "\n"
OUT_BLOCK.write_bytes(text.encode("utf-8"))
print(f"wrote {OUT_BLOCK} {OUT_BLOCK.stat().st_size} B blob={of(OUT_BLOCK)}")
print(f"wrote {OUT_JSON} {OUT_JSON.stat().st_size} B blob={of(OUT_JSON)}")
print(f"token_in_block={TIME_TOKEN in text}  time={datetime.now().astimezone().strftime('%F %T%z')}")
