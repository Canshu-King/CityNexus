"""ORD-0225 · 第二家 verifier：从 C 已发布的 8 件**原始轮次**独立派生，并与红队的派生**对表**。

仲裁 15:14 Q5 已裁：Y23=`STREAK_BROKEN`、Y123=`MULTI_CARRIER_CUTSET_KILLED`（不得升格成单臂 RECEIPT_V1）、
ORD-0225 继续 `STREAK_GREEN`/不 CLOSED ⇒ 本脚本**不重跑任何进程**，只做两件事：
  1) 每个红/每行/每次复原都从 `mutated_runs.runs[]` 的原始字段数出来（不读 `derivation.*` 的聚合结论）；
  2) 与红队已发布的派生逐字段比，两家不同尺同判才算数；不一致就点名是哪一件、哪一格。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = "D:/moodle/_qoder_integration_20260919"
DIR = Path("D:/moodle/_qoder_f_run/o225_receipts/ord0225_c")
RECEIPTS = [
    "v1_gate_receipt_Y23_a_21f1e8d.json", "v1_gate_receipt_Y23_b_21f1e8d.json",
    "v1_gate_receipt_Y23_c_21f1e8d.json", "v1_gate_receipt_Y23_OFF_A1_a_21f1e8d.json",
    "v1_gate_receipt_Y23_OFF_A2_a_21f1e8d.json", "v1_gate_receipt_Y123_a_21f1e8d.json",
    "v1_gate_receipt_Y123_b_21f1e8d.json",
]
REPEATS = "ord0225_arm_repeats_21f1e8d.json"
#: 红队 verifier 已发布的派生（账本 195 行表，AS_REPORTED，我不重跑他们的代码）
RED_TEAM = {
    "v1_gate_receipt_Y23_a_21f1e8d.json": {"carriers": 2, "reds": 6, "claimed": "STREAK_BROKEN",
                                           "derived": "STREAK_BROKEN", "agree_lane": True},
    "v1_gate_receipt_Y23_b_21f1e8d.json": {"carriers": 2, "reds": 2, "claimed": "STREAK_BROKEN",
                                           "derived": "STREAK_BROKEN", "agree_lane": True},
    "v1_gate_receipt_Y23_c_21f1e8d.json": {"carriers": 2, "reds": 2, "claimed": "STREAK_BROKEN",
                                           "derived": "STREAK_BROKEN", "agree_lane": True},
    "v1_gate_receipt_Y23_OFF_A1_a_21f1e8d.json": {"carriers": 3, "reds": 3, "claimed": "STREAK_BROKEN",
                                                  "derived": "STREAK_BROKEN", "agree_lane": True},
    "v1_gate_receipt_Y23_OFF_A2_a_21f1e8d.json": {"carriers": 3, "reds": 8, "claimed": "STREAK_BROKEN",
                                                  "derived": "STREAK_BROKEN", "agree_lane": True},
    "v1_gate_receipt_Y123_a_21f1e8d.json": {"carriers": 4, "reds": 10, "claimed": "KILLED",
                                            "derived": "MULTI_CARRIER_CUTSET_KILLED", "agree_lane": False},
    "v1_gate_receipt_Y123_b_21f1e8d.json": {"carriers": 4, "reds": 10, "claimed": "KILLED",
                                            "derived": "MULTI_CARRIER_CUTSET_KILLED", "agree_lane": False},
}
RED_TEAM_SRC = "CITYNEXUS_AGENT_CONTROL.md 第 195 行表（SESSION=d2305848，17:5x）"


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def git_bytes(*a: str) -> bytes:
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True).stdout


def ruler(sha: str, path: str) -> dict:
    """尺的具名坐标：**按字节取**（早先我用 text=True 走了一遍解码，CRLF 被折掉 ⇒ 50,315 而不是真的 50,316）。
    现在顺手自证：重算的 git 对象哈希必须等于 rev-parse 出来的 oid，不等就当场报错。"""
    oid = git("rev-parse", "--verify", "-q", f"{sha}:{path}")
    b = git_bytes("cat-file", "blob", oid)
    recomputed = hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()
    if recomputed != oid:
        raise SystemExit(f"REFUSE：{sha}:{path} 取回字节重算 blob={recomputed} ≠ oid={oid} ⇒ 读数不可信，不落盘")
    return {"git_blob_sha1": oid, "bytes": len(b), "sha256_12": hashlib.sha256(b).hexdigest()[:12],
            "from_commit": sha, "object_hash_selfcheck": "OK"}


def derive(d: dict, fn: str) -> dict:
    """只吃原始字段：target_outcomes / failed_nodeids / errored_nodeids / final_db_state / restore / db_fresh。"""
    sc, mu = d["scope"], d["mutation"]
    target = sc["target_nodeids"][0]
    runs = d["mutated_runs"]["runs"]
    rounds = int(d["mutated_runs"]["rounds"])
    seq_out, seq_fail, rows, errored_rounds = [], [], [], []
    direct, collateral = set(), set()
    fresh_all, restore_all, anchor_all, scope_ok = True, True, True, True
    for i, r in enumerate(runs, start=1):
        out = (r.get("target_outcomes") or {}).get(target)
        seq_out.append("R" if out not in (None, "GREEN") else "G")
        seq_fail.append("R" if target in (r.get("failed_nodeids") or []) else "G")
        if r.get("errored_nodeids") or r.get("collection_or_setup_errors"):
            errored_rounds.append(i)
        fdb = ((r.get("final_db_state") or {}).get("rows_by_table") or {})
        rows.append(fdb.get("row_total"))
        fresh_all &= bool(r.get("db_fresh"))
        rst = r.get("restore") or {}
        restore_all &= bool(rst.get("restored")) and bool(rst.get("byte_exact_match_before"))
        for a in r.get("anchor_receipts") or []:
            anchor_all &= (a.get("anchor_hits") == a.get("expected_anchor_hits")) and bool(a.get("bytes_changed"))
        scope_ok &= (r.get("mutated") is True)
        for f in r.get("failed_nodeids") or []:
            (direct if f in (mu.get("primary_target_nodeids") or [target]) else collateral).add(f)
    reds_out, reds_fail = seq_out.count("R"), seq_fail.count("R")
    carriers = mu.get("carriers_removed") or []
    n_carriers = len(carriers) if isinstance(carriers, list) else int(carriers or 0)
    base_out = (d.get("baseline", {}).get("target_outcomes") or {})
    control_green = bool(base_out) and all(v == "GREEN" for v in base_out.values())
    if reds_out != reds_fail:
        problem = f"两种原始红读数不一致：target_outcomes={reds_out} vs failed_nodeids={reds_fail}"
    else:
        problem = ""
    if n_carriers == 1 and control_green and reds_out == rounds:
        derived = "KILLED"
    elif n_carriers > 1 and control_green and reds_out == rounds:
        derived = "MULTI_CARRIER_CUTSET_KILLED"
    elif reds_out == 0:
        derived = "SURVIVED"
    else:
        derived = "STREAK_BROKEN"
    return {
        "file": fn, "schema": d.get("schema_version"),
        "scope": {"repo": sc.get("repo"), "exact_sha": sc.get("exact_sha"), "tree_kind": sc.get("tree_kind"),
                  "dirty": sc.get("dirty"), "target_nodeid": target, "run_shape": sc.get("run_shape")},
        "carriers_removed": n_carriers, "carriers_list": carriers,
        "rounds_declared": rounds, "rounds_seen": len(runs), "every_round_marked_mutated": scope_ok,
        "reds_by_target_outcomes": reds_out, "reds_by_failed_nodeids": reds_fail,
        "sequence_outcomes": "".join(seq_out), "sequence_failed_sets": "".join(seq_fail),
        "errored_rounds": errored_rounds,
        "campaign_valid": bool(control_green) and fresh_all and restore_all and anchor_all and len(runs) == rounds,
        "control_green": bool(control_green), "every_round_fresh_db": fresh_all,
        "every_round_restored_byte_exact": restore_all, "every_anchor_hit_expected": anchor_all,
        "rows_per_round": rows, "baseline_rows": (d.get("derivation") or {}).get("baseline_catalog_rows"),
        "direct_red_nodeids": sorted(direct), "collateral_red_nodeids": sorted(collateral),
        "lane_claimed_result": (d.get("derivation") or {}).get("claimed_result"),
        "lane_derived_field_is_null": (d.get("derivation") or {}).get("derived_result") is None,
        "derived_result_BY_LANE_F_verifier": derived,
        "red_team_AS_REPORTED": RED_TEAM.get(fn, {}),
        "两家同判": derived == RED_TEAM.get(fn, {}).get("derived"),
        "红队与车道声明一致": (RED_TEAM.get(fn, {}).get("agree_lane") is not False),
        "verifier_problem": problem,
        "row_column_instrument_blob_named_in_receipt":
            (d.get("environment") or {}).get("row_column_instrument", {}).get("git_blob_sha1"),
    }


def main() -> int:
    out: dict = {
        "order": "ORD-0225 · 第二家 verifier 对表（不重跑进程）",
        "lane": "F 8ccd71d8", "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "children_started": 0,
        "ruler_digests_named": {
            "f_current_streak_ruler_6f0e5fc": ruler("6f0e5fc", "backend/tests/_qoder_streak_receipt.py"),
            "c_measure_time_streak_ruler_a4079bc": ruler("a4079bc", "backend/tests/_qoder_streak_receipt.py"),
            "row_column_instrument_gate_streak_announced": "ac5377f207f1833441f24784043a809eddb4d3be",
        },
        "red_team_source_coordinate": RED_TEAM_SRC,
        "receipts": [],
    }
    problems: list[str] = []
    for fn in RECEIPTS:
        p = DIR / fn
        if not p.is_file():
            problems.append(f"{fn}: NOT_FETCHED ⇒ 无法派生（不许当'没有这一件'）")
            continue
        raw = p.read_bytes()
        d = json.loads(raw.decode("utf-8", "replace"))
        item = derive(d, fn)
        item["bytes"] = len(raw)
        item["local_blob_sha1"] = hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()
        want = RED_TEAM.get(fn)
        if want:
            if item["reds_by_target_outcomes"] != want["reds"]:
                problems.append(f"{fn}: 我数到的红 {item['reds_by_target_outcomes']} ≠ 红队 {want['reds']}")
            if item["carriers_removed"] != want["carriers"]:
                problems.append(f"{fn}: carriers {item['carriers_removed']} ≠ 红队 {want['carriers']}")
        if not item["两家同判"]:
            problems.append(f"{fn}: 我的派生 {item['derived_result_BY_LANE_F_verifier']} ≠ 红队派生 {want and want.get('derived')}")
        if item["verifier_problem"]:
            problems.append(f"{fn}: {item['verifier_problem']}")
        announced = item["row_column_instrument_blob_named_in_receipt"]
        if announced != "ac5377f207f1833441f24784043a809eddb4d3be":
            problems.append(f"{fn}: 行读数那把尺不是 commander 公布的那一枚（{announced}）")
        out["receipts"].append(item)

    # 重复批次表：堵"挑一批好看的"
    rp = DIR / REPEATS
    if rp.is_file():
        rep = json.loads(rp.read_text(encoding="utf-8", errors="replace"))
        mine = {i["file"].replace("v1_gate_receipt_", "").replace("_21f1e8d.json", ""):
                i["reds_by_target_outcomes"] for i in out["receipts"]}
        out["arm_repeats"] = {"file": REPEATS, "top_keys": list(rep)[:8],
                              "my_per_batch_reds": mine,
                              "raw": {k: v for k, v in rep.items() if not isinstance(v, (dict, list))}}
    else:
        out["arm_repeats"] = {"file": REPEATS, "status": "NOT_FETCHED"}

    out["verifier_problems"] = problems
    r = [x for x in out["receipts"]]
    out["summary"] = {
        "Y23_三批": [f"{x['reds_by_target_outcomes']}/10" for x in r if x["carriers_removed"] == 2],
        "Y23_OFF_A1_A2": {x["carriers_list"][-1] if x["carriers_list"] else "?": x["reds_by_target_outcomes"]
                          for x in r if x["carriers_removed"] == 3},
        "Y123_两批": [f"{x['reds_by_target_outcomes']}/10" for x in r if x["carriers_removed"] == 4],
        "单臂杀手有没有": any(x["derived_result_BY_LANE_F_verifier"] == "KILLED" for x in r),
        "ORD_0225_等级": "STREAK_GREEN（无单臂 KILLED ⇒ 推不到 CLOSED；与仲裁 15:14 Q5 一致）",
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    fp = Path("D:/moodle/_qoder_f_run/o225_receipts/o225_second_verifier_crosscheck.json")
    fp.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nWROTE {fp} ({fp.stat().st_size} B, sha256[:12]="
          f"{hashlib.sha256(fp.read_bytes()).hexdigest()[:12]})")
    print("problems:", problems or "无（两家逐字段一致）")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
