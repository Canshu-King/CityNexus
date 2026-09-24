"""ORD-0262-NARROW 最后一格（busy 等值收进各自阶梯）的收据：数字全部现场重算，不抄自己上一帖。

要机械回答的是包工头那四条：
  ① 三处硬编码 500 是否真的没了、且改成了从**各自操作**的阶梯派生；
  ② 复跑 3×3 后 only_in_candidate 是否从 1 变 0；
  ③ 那一格由红转绿有没有正控（把阶梯调用抄回 500 ⇒ 该格必红）；
  ④ 有没有发新错误码、有没有新增第四份 500/503 常数。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path("D:/moodle/_qoder_integration_20260919")
RUN = Path("D:/moodle/_qoder_f_run")
RCP = RUN / "o225_receipts"
HEAD = "3093eea"
PARENT = "7762fdf"          # 派单时那一枚 tip
BASE = "d2665e25855aeb265329266831983de42321697d"
MAIN = "backend/app/main.py"
GATE = "backend/tests/test_qoder_ord0262_narrow_contention.py"
CELL = "test_5_the_retry_hint_comes_from_the_operation_ladder_not_a_fourth_literal"
LIT_RE = re.compile(r'\"retry_after_ms\":\s*(\d+)')
AB = RCP / "ord0262_retry_collapse_ab_r2.json"
TRIAGE = RCP / "ord0262_swimmer_triage.json"
MUT = RCP / "ord0262_narrow_mutation_receipt.json"


def git(*a: str) -> str:
    p = subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert p.returncode == 0, f"git {a[:2]}: {p.stderr[:180]}"
    return p.stdout.strip()


def blob_of(rev: str, path: str) -> str:
    return git("rev-parse", f"{rev}:{path}")


def replay_proof(head40: str) -> dict:
    """把两笔 patch 重放到父树上，write-tree 必须等于 tip 的树（等值是读数，不是话）。"""
    import shutil
    import tempfile
    patches = sorted((RUN / "patches_0262_retry").glob("*.patch"))
    idx = Path(tempfile.gettempdir()) / f"cnx_262replay_{int(time.time())}.idx"
    env = dict(os.environ, GIT_INDEX_FILE=idx.as_posix())
    try:
        steps: list[list[str]] = [["read-tree", PARENT]]
        steps += [["apply", "--cached", str(p)] for p in patches]
        for args in steps:
            p = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True,
                               encoding="utf-8", env=env)
            assert p.returncode == 0, f"重放失败 {args[:2]}：{p.stderr[:220]}"
        replayed = subprocess.run(["git", "-C", str(REPO), "write-tree"], capture_output=True,
                                  text=True, encoding="utf-8", env=env).stdout.strip()
    finally:
        idx.unlink(missing_ok=True)
    want = git("rev-parse", f"{head40}^{{tree}}")
    return {"base_tree_rev": PARENT, "replayed_tree": replayed, "head_tree": want,
            "byte_equal": replayed == want,
            "patches": [{"name": q.name, "bytes": q.stat().st_size} for q in patches]}


def emissions(rev: str) -> dict:
    text = git("show", f"{rev}:{MAIN}")
    vals = [v.strip() for v in re.findall(r"\"retry_after_ms\":\s*([^,}\n]+)", text)]
    return {"total_emissions": len(vals),
            "bare_numbers": sorted(v for v in vals if re.fullmatch(r"\d+", v)),
            "from_generation_ladder": sum(1 for v in vals
                                          if v == "_contention_retry_after_ms()"),
            "from_hydration_ladder": sum(1 for v in vals
                                         if v == "_hydration_busy_retry_after_ms()"),
            "passthrough_of_operation_body": sum(1 for v in vals if v.startswith("body[")),
            "distinct_codes_in_busy_family": sorted(set(re.findall(
                r"\"(HYDRATION_STORE_BUSY|GENERATION_STORE_BUSY)\"", text)))}


def main() -> int:
    head40 = git("rev-parse", HEAD)
    mut = json.loads(MUT.read_text(encoding="utf-8")) if MUT.is_file() else {}
    ab = json.loads(AB.read_text(encoding="utf-8")) if AB.is_file() else {}
    before, after = emissions(PARENT), emissions(head40)
    controls = {k: {"claimed_result": v["claimed_result"], "killed_by": v["killed_by"],
                    "still_green": v["still_green"], "owner": v["owner_assertion"]}
                for k, v in (mut.get("mutations") or {}).items()
                if k.startswith(("M3_", "M4_", "M5_"))}
    cmp_block = ab.get("comparison") or {}
    cell_states = {name: status
                   for m in (mut.get("mutations") or {}).values()
                   for name, status in [(x, "RED") for x in m["killed_by"]]
                   + [(x, "GREEN") for x in m["still_green"]]}
    triage = json.loads(TRIAGE.read_text(encoding="utf-8")) if TRIAGE.is_file() else {}
    focus = triage.get("trees") or {}
    n_focus = triage.get("focused_rounds")
    cand_rounds = (ab.get("trees") or {}).get("candidate_3093eea", {}).get("rounds", [])
    cls = {}
    for name in (cmp_block.get("only_in_candidate") or []):
        c = focus.get("candidate_3093eea", {}).get("red_rounds")
        b = focus.get("base_d2665e2", {}).get("red_rounds")
        cls[name] = {
            "nodeid_matches_the_triage": name == triage.get("nodeid"),
            "whole_suite_rounds_red": sum(1 for r in cand_rounds if name in r["named_red_nodeids"]),
            "focused_red_rounds_candidate": c, "focused_red_rounds_baseline": b,
            "focused_rounds": n_focus,
            "classification": ("REGRESSION" if (c == n_focus and b == 0 and c is not None)
                               else "BATCH_SENSITIVE（聚焦不恒红 ⇒ 不成回归形状）")}
    regressions = sorted(k for k, v in cls.items() if v["classification"] == "REGRESSION")
    if not cmp_block:
        q2_verdict = "NOT_MEASURED（A/B 的 JSON 还没落盘 ⇒ 这一格不许口头宣布）"
    elif not cmp_block.get("only_in_candidate"):
        q2_verdict = "MET：only_in_candidate 已从 1 变 0"
    elif regressions:
        q2_verdict = f"NOT MET：{len(regressions)} 条聚焦也恒红的名字"
    else:
        q2_verdict = (f"MET-WITH-NAMED-SWIMMER：0 条回归、{len(cls)} 条批次敏感"
                      "（聚焦 3 轮两棵树都全绿，全量只在候选 1/3 轮出现）⇒ 不许写成'0 新红'")
    receipt = {
        "what": "ORD-0262-NARROW 最后一格：busy 的 retry 等值收口进两枚操作自己的阶梯（01:1x §③ 的派单）",
        "lane": "F 8ccd71d8",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "coordinates": {
            "branch": "agent/f-ord0262-narrow", "head": head40, "parent": git("rev-parse", PARENT),
            "base_of_this_order": BASE, "tree": git("rev-parse", f"{head40}^{{tree}}"),
            "blobs": {p: {"parent": blob_of(PARENT, p), "head": blob_of(head40, p)}
                      for p in (MAIN, GATE)},
            "diff_stat_vs_parent": git("diff", "--numstat", PARENT, head40).split("\n"),
            "patch_replay": replay_proof(head40),
            "pushed": False},
        "question_1_three_literals_gone": {
            "before": before, "after": after,
            "verdict": ("MET：三处写死数字已为 0，且两处 generation 站点 + 一处 hydration 站点分别走各自阶梯"
                        if not after["bare_numbers"] and after["from_hydration_ladder"] == 1
                        and after["from_generation_ladder"] >= 2 else
                        f"NOT MET：after={after}")},
        "question_2_regression_ab": {
            "shape": "3 轮 × 2 棵新鲜 git archive 导出，逐文件核对导出字节==提交字节",
            "first_round_finding": (
                "第一版 A/B（候选 30092dc）曾量到 1 条候选独有红：既存门 "
                "tests/test_qoder_stay_generation_operations.py::"
                "test_a_busy_store_answers_a_named_retry_on_both_doors 把 ==500 写死在断言里 "
                "⇒ 收口之后它必然红。这一条不是我的格子坏了，是**旧契约在证据层还留着一个载体**；"
                "已按写域改掉那枚断言（判阶梯下限 + 两门必须一致），本收据只报 3093eea 这一版"),
            "per_round_red_counts": {t: v["per_round_red_counts"] for t, v in (ab.get("trees") or {}).items()},
            "collect_denominators": cmp_block.get("collect_denominators"),
            "only_in_candidate": cmp_block.get("only_in_candidate"),
            "only_in_baseline": cmp_block.get("only_in_baseline"),
            "expectation": cmp_block.get("expectation_under_the_ruling"),
            "candidate_only_names_classified": cls,
            "verdict": q2_verdict},
        "question_3_positive_control": {
            "note": "把某一处阶梯调用**抄回写死的 500**，该格必须红；共享信封那一处还要看见 ①/② 继续绿（独立性反证）",
            "controls": controls,
            "controls_run": len(controls),
            "the_cell_under_test_red_when_literal_returned": all(
                CELL in c["killed_by"] for c in controls.values()),
            "verdict": (f"MET：{len(controls)} 枚正控（hydration 站点 / 共享信封 / generation 等待门）"
                        "各自把 ④ 打红；其中信封与 generation 那两枚同时给出'该继续绿'的一侧"
                        if len(controls) == 3 and all(CELL in c["killed_by"] for c in controls.values())
                        else f"NOT MET（正控 {len(controls)} 枚或有没打红的）")},
        "question_4_no_new_vocabulary": {
            "codes_before": before["distinct_codes_in_busy_family"],
            "codes_after": after["distinct_codes_in_busy_family"],
            "new_code_introduced": sorted(set(after["distinct_codes_in_busy_family"])
                                          - set(before["distinct_codes_in_busy_family"])),
            "fourth_constant_added": after["bare_numbers"],
            "verdict": ("MET：没发新码、没添第四份常数"
                        if not sorted(set(after["distinct_codes_in_busy_family"])
                                      - set(before["distinct_codes_in_busy_family"]))
                        and not after["bare_numbers"] else "NOT MET")},
        "guardrail_kept_verbatim": (
            "本收据只声明这一格。19 B/21 B 变漂亮 JSON 不等于 ORD-0262 的原子性/完整性已闭："
            "孤儿 `CREATED` mission 与未落库的 `plan_version`（e168580c v22）仍是各留各门的独立义务；"
            "跨进程同键那一格归红队派生，我不在此宣布。"),
        "campaign_health": {"control_reading": (mut.get("control") or {}).get("reading"),
                            "campaign_valid": mut.get("campaign_valid"),
                            "restore_verified": mut.get("restore_verified"),
                            "target_file_sha_before_and_after": mut.get(
                                "scope", {}).get("target_sha_before_and_after"),
                            "mutation_receipt_blob": (hashlib.sha1(
                                b"blob %d\0" % MUT.stat().st_size + MUT.read_bytes()).hexdigest()
                                if MUT.is_file() else None)},
        "print_policy": "只印 sha/计数/来源表达式；0 凭据、0 用户库路径、0 demo/reset",
    }
    out = RCP / "ord0262_retry_collapse_receipt.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps({k: receipt[k] for k in ("question_1_three_literals_gone",
                                              "question_2_regression_ab",
                                              "question_4_no_new_vocabulary")} |
                     {"q3": receipt["question_3_positive_control"]["verdict"],
                      "out": out.name, "bytes": out.stat().st_size},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
