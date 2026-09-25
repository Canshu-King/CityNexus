"""把 ORD-0287 已发布读数重排成 Q38 尺读得到的 `cells` 形状，并证明这把尺在我这份工件上真有牙。

规矩（我自己写死，免得手滑）：
* 只用**已从 commander/control 按 40 位 blob 取回、且重算 sha1 相等**的字节当输入，不重跑产品、不改候选；
* 每格的 `why` 一律由本格自己的读数现场 f-string 拼出：句子里的哈希/计数/行号必须是读数里逐字存在的那一枚，
  所以我先算再写，不手写任何一个数字；
* 判级 `verdict` 也从读数派生（布尔与不等式），`derived_result` 留 null（B-1，闭单归验方）；
* 三枚反控（复制句 / 掏空句 / 假 derived_from）都要红，否则说明这份 r2 只是碰巧过了尺。
"""
from __future__ import annotations

import copy
import hashlib
import re
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUN = Path("D:/moodle/_qoder_f_run")
PUB = RUN / "q38_on_f"
GATE = RUN / "q38_gate_from_commander.py"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
OUT = Path("D:/moodle/_qoder_f_run/o225_receipts")

TS = json.loads((PUB / "pub_two_state_on_candidate.json").read_text(encoding="utf-8"))
TS_EXPORT = json.loads((PUB / "pub_two_state_on_landed_export.json").read_text(encoding="utf-8"))
FACTS = json.loads((PUB / "pub_candidate_commit_facts.json").read_text(encoding="utf-8"))
REF = json.loads((PUB / "pub_ref_readback.json").read_text(encoding="utf-8"))
FREEZE = json.loads((PUB / "pub_frozen_tip_addendum_r1.json").read_text(encoding="utf-8"))
STEP0 = json.loads((PUB / "pub_ord0287_step0_portability.json").read_text(encoding="utf-8"))

GATE_BLOB = "35caa42c0697faf0a8eeb0929a3e11cb53c9709a"
CARRIER = "backend/tests/test_qoder_ord0287_k8_carrier.py"
AUTH = "45b0a5e281cae9c37715173afd3ac5778f309ca7"


def sha40(path: Path) -> tuple[str, int]:
    b = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest(), len(b)


def per_round(doc: dict, side: str, cell: str) -> list[dict]:
    return [{"round": r["round"], "rc": r[side][cell]["rc"],
             "summary_line": r[side][cell]["summary_line"],
             "failure_lines": r[side][cell]["failure_lines"]} for r in doc["rounds"]]


def all_rc(rows: list[dict]) -> list[int]:
    return [r["rc"] for r in rows]


# ---------------------------------------------------------------- the eight cells
K1 = TS["rounds"][0]["authoritative"]["K1"]["target"]
land_blob = TS["rounds"][0]["authoritative"]["main_blob"]
mut_before = TS["rounds"][0]["mutant"]["before_blob"]
mut_after = TS["rounds"][0]["mutant"]["after_blob_40"]
carrier_blob = TS["tree"]["carrier_blob"]
a1, m1 = per_round(TS, "authoritative", "K1"), per_round(TS, "mutant", "K1")
a2, m2 = per_round(TS, "authoritative", "K2"), per_round(TS, "mutant", "K2")
ea1, em1 = per_round(TS_EXPORT, "authoritative", "K1"), per_round(TS_EXPORT, "mutant", "K1")
hunks = TS["rounds"][0]["mutant"]["hunks"]
hunk_headers = TS["rounds"][0]["mutant"]["hunk_headers"]
lines_delta = TS["rounds"][0]["mutant"]["lines_delta"]
removed = TS["rounds"][0]["mutant"]["removed_expression"]
restores = [r["restored_byte_exact"] for r in TS["rounds"]]
c2 = FACTS["criterion_2_test_only"]
c1 = FACTS["criterion_1_parent_is_landed_tip"]
c5 = FACTS["criterion_5_external_readback"]
sym = STEP0["symbols"]
v1 = STEP0["case_v1_verbatim_append"]
ctl = STEP0["positive_control_landed_cell"]

cells: dict[str, dict] = {}

cells["S1_K1_green_on_authoritative_line"] = {
    "claim": "权威线那一棵上，载体格 K1 两轮全绿",
    "claim_kind": "code_determined",
    "cell_named": K1,
    "measured": {"main_py_blob": land_blob, "rounds": a1, "rc_values": all_rc(a1),
                 "round_count": len(a1)},
    "verdict": "CARRIER_GREEN_ON_AUTHORITATIVE_LINE"
               if all_rc(a1) == [0] * len(a1) and len(a1) == 2 else "CARRIER_NOT_GREEN",
    "why": f"{len(a1)} 轮在 main.py blob {land_blob} 上单独跑 {K1}，"
           f"每行 pytest 汇总逐字是 {a1[0]['summary_line']!r}，rc 依次 {all_rc(a1)}",
}

cells["S2_K1_red_when_guard_removed"] = {
    "claim": "只删掉回填守卫那一个布尔谓词，同一格必红（这就是它咬人的那一面）",
    "claim_kind": "code_determined",
    "cell_named": K1,
    "measured": {"before_blob": mut_before, "after_blob": mut_after, "rounds": m1,
                 "rc_values": all_rc(m1), "removed_expression": removed,
                 "authoritative_rc_for_comparison": all_rc(a1),
                 "failure_lines": m1[0]["failure_lines"]},
    "verdict": "CARRIER_RED_WHEN_GUARD_REMOVED"
               if all(rc == 1 for rc in all_rc(m1)) and all_rc(m1) != all_rc(a1)
               else "CARRIER_DID_NOT_TURN_RED",
    "why": f"{land_blob} 改成 {mut_after} 之后，同一格 {K1} 的 rc 依次 {all_rc(m1)}，"
           f"FAILED 行逐字含 {m1[0]['failure_lines'][0][:60]!r}",
}

cells["S3_K2_positive_control_green_both_states"] = {
    "claim": "正控：我占的两把 NULL 键在两态下都必须真被填上 ⇒ 红不能靠『永远失败』蒙出来",
    "claim_kind": "code_determined",
    "cell_named": TS["rounds"][0]["authoritative"]["K2"]["target"],
    "measured": {"carrier_blob": carrier_blob, "authoritative_rounds": a2, "mutant_rounds": m2,
                 "authoritative_rc": all_rc(a2), "mutant_rc": all_rc(m2)},
    "verdict": "POSITIVE_CONTROL_GREEN_IN_BOTH_STATES"
               if all_rc(a2) == [0] * len(a2) and all_rc(m2) == [0] * len(m2)
               else "POSITIVE_CONTROL_NOT_STABLE",
    "why": f"载体文件 blob {carrier_blob} 的 {all_rc(a2)} (守卫在位) 与 {all_rc(m2)} (守卫拆掉) 两侧 rc 全 0，"
           f"两态汇总行分别是 {a2[0]['summary_line']!r} / {m2[0]['summary_line']!r}",
}

cells["S4_mutation_is_one_line_and_compiles"] = {
    "claim": "变量只有一处：一枚 hunk、一行谓词、改动后仍可编译",
    "claim_kind": "code_determined",
    "measured": {"hunks": hunks, "hunk_headers": hunk_headers, "lines_delta": lines_delta,
                 "py_compile_ok": TS["rounds"][0]["mutant"]["py_compile_ok"],
                 "before_blob": mut_before, "after_blob": mut_after},
    "verdict": "SINGLE_HUNK_SINGLE_PREDICATE"
               if hunks == 1 and lines_delta[0] - lines_delta[1] == 1
               and TS["rounds"][0]["mutant"]["py_compile_ok"] else "MUTATION_NOT_ISOLATED",
    "why": f"{hunk_headers[0]} 这一枚 hunk 把行数从 {lines_delta[0]} 改成 {lines_delta[1]}，"
           f"blob {mut_before} → {mut_after}，py_compile_ok={TS['rounds'][0]['mutant']['py_compile_ok']}",
}

cells["S5_tree_restored_byte_exact"] = {
    "claim": "每轮跑完把产品文件按字节还原，末态与落地代逐位相同",
    "claim_kind": "code_determined",
    "measured": {"per_round_restored": restores, "final_main_blob": TS["final"]["main_blob_after_all"],
                 "landing_main_blob": land_blob, "byte_exact_vs_landing": TS["final"]["byte_exact_vs_landing"]},
    "verdict": "TREE_RESTORED_BYTE_EXACT"
               if all(restores) and TS["final"]["byte_exact_vs_landing"]
               and TS["final"]["main_blob_after_all"] == land_blob else "TREE_NOT_RESTORED",
    "why": f"{len(restores)} 轮逐轮还原 {restores}，末态 main.py 读回 {TS['final']['main_blob_after_all']}"
           f" 与落地代 {land_blob} 相等：{TS['final']['byte_exact_vs_landing']}",
}

cells["S6_candidate_is_test_only_on_authoritative_parent"] = {
    "claim": "候选只动测试、父提交正是权威尖、产品 0 件",
    "claim_kind": "code_determined",
    "measured": {"tip": c1["tip"], "parent": c1["parent_observed"], "authoritative_read_first": c1["base_read_by_me_first"],
                 "tree": c1["tree"], "files_changed": c2["files_changed"], "numstat": c2["numstat"],
                 "all_paths_under_backend_tests": c2["all_paths_under_backend_tests"],
                 "parent_equals_base": c1["parent_equals_base"],
                 "carrier_blob_matches": c2["carrier_blob_matches"],
                 "product_paths_touched": c2["product_paths_touched"],
                 "carrier_blob_at_tip": c2["carrier_blob_at_tip"]},
    "verdict": "TEST_ONLY_ON_AUTHORITATIVE_PARENT"
               if c1["parent_equals_base"] and c1["parent_observed"] == AUTH
               and c2["all_paths_under_backend_tests"] and not c2["product_paths_touched"]
               and c2["carrier_blob_matches"] else "CANDIDATE_SHAPE_UNSAFE",
    "why": f"{c1['tip']} 的父是 {c1['parent_observed']}（先读到的权威尖 {c1['base_read_by_me_first']}），"
           f"改动清单只有 {c2['files_changed'][0]}，numstat {c2['numstat'][0]!r}，产品路径 {len(c2['product_paths_touched'])} 件",
}

cells["S7_frozen_tip_is_externally_readable"] = {
    "claim": "按 Q37 冻结的那枚尖在 GitHub 上两条路都读得到，且没有第二条 ref",
    "claim_kind": "code_determined",
    "measured": {"ref": REF["ref"], "github_ls_remote_line": REF["github_ls_remote_line"],
                 "https_sha": REF["https_sha"], "tip": REF["tip"],
                 "equals_frozen_tip": REF["https_sha"] == FREEZE["frozen_tip"],
                 "ref_recheck_at": FREEZE["ref_recheck"]["checked_at"],
                 "committer_date": FREEZE["committer_date_read_from_commit"]},
    "verdict": "FROZEN_TIP_EXTERNALLY_READABLE"
               if REF["https_equals_tip"] and REF["tip"] == FREEZE["frozen_tip"]
               and FREEZE["ref_recheck"]["equals_frozen_tip"] else "FROZEN_TIP_NOT_READABLE",
    "why": f"ls-remote 与 https 两条路都回 {REF['https_sha']}，与申报的 frozen_tip "
           f"{FREEZE['frozen_tip']} 相等：{REF['https_equals_tip']}（复校于 {FREEZE['ref_recheck']['checked_at']}）",
}

cells["S8_verbatim_port_is_refused_at_import"] = {
    "claim": "第 0 条：旧代那格原样搬到权威线跑不起，拦路的是产品符号而不是我的断言",
    "claim_kind": "code_determined",
    "measured": {"missing_symbol": sym["missing_symbol"],
                 "hits_in_landed_main_py": sym["hits_in_landed_main_py"],
                 "hits_in_candidate_main_py": sym["hits_in_candidate_main_py"],
                 "landed_main_blob": sym["landed_main_blob"], "candidate_main_blob": sym["candidate_main_blob"],
                 "verbatim_case_rc": v1["rc"], "verbatim_gate_blob": v1["gate_blob_after"],
                 "control_cell_rc": ctl["rc"], "control_cell": ctl["nodeid"], "control_summary": ctl["summary_line"]},
    "verdict": "VERBATIM_PORT_REFUSED_BY_IMPORT"
               if v1["rc"] == 1 and sym["hits_in_landed_main_py"] == 0
               and sym["hits_in_candidate_main_py"] == 2 and ctl["rc"] == 0
               else "PORTABILITY_FACT_NOT_REPRODUCED",
    "why": f"{sym['landed_main_blob']} 里 {sym['missing_symbol']} 命中 {sym['hits_in_landed_main_py']} 处、"
           f"{sym['candidate_main_blob']} 里 {sym['hits_in_candidate_main_py']} 处 ⇒ 原样 append 的 "
           f"{v1['gate_blob_after']} rc={v1['rc']}，同棵拷贝树同解释器下权威线自己的 {ctl['nodeid'][:56]} rc={ctl['rc']}",
}

# ------------------------------------------------------------------ two-state also on the tarball export
cells["S9_two_state_repeats_on_the_github_export"] = {
    "claim": "两态读数不是只在车道工作树里成立：GitHub tarball 导出那棵同样翻",
    "claim_kind": "code_determined",
    "measured": {"backend_cwd": TS_EXPORT["tree"]["backend_cwd"], "main_py_blob": TS_EXPORT["tree"]["main_py_landing_blob"],
                 "carrier_blob": TS_EXPORT["tree"]["carrier_blob"], "authoritative_rounds": ea1,
                 "mutant_rounds": em1, "authoritative_rc": all_rc(ea1), "mutant_rc": all_rc(em1),
                 "final_main_blob": TS_EXPORT["final"]["main_blob_after_all"]},
    "verdict": "TWO_STATE_REPRODUCED_ON_EXPORT"
               if all_rc(ea1) == [0] * len(ea1) and all(rc == 1 for rc in all_rc(em1))
               and TS_EXPORT["final"]["byte_exact_vs_landing"] else "EXPORT_NOT_REPRODUCED",
    "why": f"导出树 blob {TS_EXPORT['tree']['main_py_landing_blob']} + 载体 {TS_EXPORT['tree']['carrier_blob']}："
           f"守卫在位 rc {all_rc(ea1)}、拆掉 rc {all_rc(em1)}，跑完末态 {TS_EXPORT['final']['main_blob_after_all']}",
}

# --------------------------------------------------------------- provenance: every input re-verified by blob
prov = {}
for name in sorted(p.name[len("pub_"):] for p in PUB.glob("pub_*.json")):
    p = PUB / ("pub_" + name)
    blob, size = sha40(p)
    prov[name] = {"blob_sha1_40": blob, "bytes": size}

receipt = {
    "what": "ORD-0287 收据按 Q38 口径重排成可判 `cells` 形状（读数一字未动，只是把每格的自己读数与句子配齐）",
    "lane": "F 8ccd71d8",
    "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "why_this_exists": "包工头 08:0x 那拍把 Q38 落成了可跑仪器并要求『每格 why 自带本格读数的具名值』；"
                       "他这台尺读我 07:14 那份两态收据报 NOT_ASSESSABLE（不足 2 格可判），"
                       "也就是说我这一单在新规定下**不可核**。这一版只改收据的呈现形状，不改任何主张、不重跑产品。",
    "claim_kind_rule": f"{len(cells)} 格全部 code_determined：判据一项都不依赖时长；读数里出现的秒数只当读数。",
    "cells": cells,
    "carried_over_verdict_from_r1": TS["derived"]["verdict"],
    "unchanged_by_this_file": {
        "candidate_frozen_tip": FREEZE["frozen_tip"],
        "carrier_blob": carrier_blob,
        "product_files_touched": 0,
        "assertions_changed": 0,
        "new_commits_or_refs": 0,
    },
    "derived_result": None,
    "provenance_inputs_verified_by_blob": prov,
    "instrument": {"name": "receipt_cell_derivation_check_r1.py", "owner": "commander 494abfd7",
                   "blob_40": GATE_BLOB, "bytes": sha40(GATE)[1],
                   "recomputed_sha1_equals_declared": sha40(GATE)[0] == GATE_BLOB,
                   "how_used": "子进程按 --receipt / --selftest 调用，文件一字未改、未复制改写"},
    "discipline": {"demo_reset_calls": 0, "live_or_preview_db_touched": False, "credentials_printed": 0,
                   "authoritative_branch_written": False, "published_paths_overwritten": 0,
                   "published_paths_deleted": 0, "candidate_ref_pushes_after_freeze": 0},
}
r2 = OUT / "ord0287_receipt_cells_r2.json"
r2.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("cells:", len(cells), "| verdicts:")
for cid, c in cells.items():
    print("   ", cid, "=", c["verdict"])

# -------------------------------------------------------------------- run his gate: r2 + three killers
def run(args: list[str], label: str) -> dict:
    o = OUT / ("q38_out_" + label + ".json")
    p = subprocess.run([PY, str(GATE), *args, "--out", str(o)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=300)
    doc = json.loads(o.read_text(encoding="utf-8")) if o.exists() else None
    tail = (p.stdout or "").strip().splitlines()
    return {"rc": p.returncode, "stdout_all": p.stdout or "", "overall": (doc or {}).get("overall"),
            "cells_found": (doc or {}).get("cells_found"),
            "hard_codes": (doc or {}).get("hard_codes"), "soft_codes": (doc or {}).get("soft_codes"),
            "stdout_tail": tail[-3:], "doc": doc}


print("\n[gate] commander's own selftest on this machine")
st = run(["--selftest"], "selftest")
print("   ", {k: v for k, v in st.items() if k != "doc"})

print("[gate] my r2")
g = run(["--receipt", str(r2)], "r2")
print("   ", {k: v for k, v in g.items() if k != "doc"})

print("[gate] killer 1: two cells forced to share one sentence")
k1doc = copy.deepcopy(receipt)
shared = "两态都按预期翻了"
k1doc["cells"]["S1_K1_green_on_authoritative_line"]["why"] = shared
k1doc["cells"]["S5_tree_restored_byte_exact"]["why"] = shared
f1 = OUT / "killer_shared_sentence.json"
f1.write_text(json.dumps(k1doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
r_k1 = run(["--receipt", str(f1)], "killer_shared")
print("   ", {k: v for k, v in r_k1.items() if k != "doc"})

print("[gate] killer 2: sentences with nothing machine-checkable")
k2doc = copy.deepcopy(receipt)
for cid in k2doc["cells"]:
    k2doc["cells"][cid]["why"] = "这一格按预期翻了"
f2 = OUT / "killer_no_evidence_token.json"
f2.write_text(json.dumps(k2doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
r_k2 = run(["--receipt", str(f2)], "killer_notoken")
print("   ", {k: v for k, v in r_k2.items() if k != "doc"})

print("[gate] killer 3: shared sentence + a derived_from that cites nothing unique to its own cell")
k3doc = copy.deepcopy(receipt)
for cid in ("S1_K1_green_on_authoritative_line", "S5_tree_restored_byte_exact"):
    k3doc["cells"][cid]["why"] = shared
    k3doc["cells"][cid]["derived_from"] = "大家都有的那句 claim"
f3 = OUT / "killer_fake_derived_from.json"
f3.write_text(json.dumps(k3doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
r_k3 = run(["--receipt", str(f3)], "killer_fakedf")
print("   ", {k: v for k, v in r_k3.items() if k != "doc"})

def soft_why(doc: dict, style: str) -> None:
    labels = "甲乙丙丁戊己庚辛壬癸"
    for n, cid in enumerate(doc["cells"]):
        doc["cells"][cid]["why"] = (
            f"这一格判级由本格读数派生（第{labels[n]}式）：守卫在位则绿、拆掉那枚谓词则红"
            if style == "no_tokens" else f"第 {n + 1} 号格按预期翻了，见本格的 verdict 字段")


def control(label: str, mutate) -> dict:
    doc = copy.deepcopy(receipt)
    mutate(doc)
    f = OUT / (label + ".json")
    f.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    r = run(["--receipt", str(f)], label)
    r["words_containing_GREEN_printed"] = [w for w in re.findall(r"\S*GREEN\S*", r.pop("stdout_all") or "")]
    print(f"   {label}: rc={r['rc']} overall={r['overall']} hard={r['hard_codes']} soft={r['soft_codes']} GREEN_words={r['words_containing_GREEN_printed'] or 'none'}")
    return r


def strip_why(doc: dict, n: int = 2, short_verdicts: bool = True) -> None:
    for i, k in enumerate(list(doc["cells"])[:n]):
        doc["cells"][k].pop("why", None)
        if short_verdicts:
            doc["cells"][k]["verdict"] = f"OK{i + 1}"


print("[gate] 五枚对照 + 一枚边界读数：每枚只踩一档，踩对了才算这把尺在我这份工件上真有牙")
r_k4a = control("killer_unique_but_no_evidence_token", lambda d: soft_why(d, "no_tokens"))
r_k4b = control("killer_unique_but_tokens_not_own_readings", lambda d: soft_why(d, "other"))
r_k5 = control("killer_missing_why_short_verdict", lambda d: strip_why(d, 2, True))
r_k6 = control("boundary_missing_why_long_verdict", lambda d: strip_why(d, 2, False))

checks = {
    "r2_green": g["overall"] == "Q38_GATE_GREEN" and g["rc"] == 0,
    "r2_cells_equal_declared": g["cells_found"] == len(cells),
    "r2_no_soft_no_hard": not g["hard_codes"] and not g["soft_codes"],
    "selftest_rc0": st["rc"] == 0,
    "killer_shared_hard": r_k1["overall"] == "Q38_GATE_RED_HARD" and "DUPLICATE_WHY_LITERALS" in r_k1["hard_codes"],
    "killer_dup_sentence_hard": r_k2["overall"] == "Q38_GATE_RED_HARD",
    "killer_fake_derived_from_hard": "FAKE_OR_INEFFECTIVE_DERIVED_FROM" in (r_k3["hard_codes"] or []),
    "killer_soft_no_token_only": (r_k4a["overall"] == "Q38_GATE_SOFT_FINDINGS" and not r_k4a["hard_codes"]
                                  and r_k4a["rc"] == 0 and not r_k4a["words_containing_GREEN_printed"]),
    "killer_soft_not_own_readings": (r_k4b["overall"] == "Q38_GATE_SOFT_FINDINGS"
                                     and "WHY_NOT_FROM_OWN_READINGS" in (r_k4b["soft_codes"] or [])),
    "killer_missing_why_hard": "MISSING_WHY" in (r_k5["hard_codes"] or []),
    "boundary_long_verdict_falls_back_to_prose": (r_k6["overall"] == "Q38_GATE_SOFT_FINDINGS"
                                                  and "MISSING_WHY" not in (r_k6["hard_codes"] or [])),
}
print("[assert] controls behave:", {k: v for k, v in checks.items() if not v} or "ALL_CONTROLS_BEHAVE")

controls = {
    "selftest": {k: v for k, v in st.items() if k not in ("doc", "stdout_all")},
    "r2": {k: v for k, v in g.items() if k not in ("doc", "stdout_all")},
    "r2_cells_detail": [{"id": c["id"], "own_token_count": c.get("own_token_count"),
                         "why_token_count": c.get("why_token_count"),
                         "own_hits": len(c.get("own_hits") or []),
                         "shares_why_with": c.get("shares_why_with", [])}
                        for c in (g["doc"] or {}).get("cells", [])],
    "controls_behave_as_named": checks,
    "killer_shared_sentence": {k: v for k, v in r_k1.items() if k not in ("doc", "stdout_all")},
    "killer_unique_but_no_evidence_token": {k: v for k, v in r_k4a.items() if k not in ("doc", "stdout_all")},
    "killer_unique_but_tokens_not_own_readings": {k: v for k, v in r_k4b.items() if k not in ("doc", "stdout_all")},
    "killer_missing_why_short_verdict": {k: v for k, v in r_k5.items() if k not in ("doc", "stdout_all")},
    "boundary_missing_why_long_verdict": {k: v for k, v in r_k6.items() if k not in ("doc", "stdout_all")},
    "killer_all_cells_one_sentence": {k: v for k, v in r_k2.items() if k not in ("doc", "stdout_all")},
    "killer_fake_derived_from": {k: v for k, v in r_k3.items() if k not in ("doc", "stdout_all")},
    "gate_on_r1_artifacts": json.loads((OUT / "ord0287_q38_gate_on_f.json").read_text(encoding="utf-8"))["runs"],
}
(OUT / "ord0287_q38_controls_r2.json").write_text(
    json.dumps(controls, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("\nwrote", r2.name, "and ord0287_q38_controls_r2.json")
print("GATE r2:", g["overall"], "rc", g["rc"],
      "| killers:", r_k1["overall"], r_k2["overall"], r_k3["overall"])
