"""ORD-0253 Phase A/B 的收据：三格读数 + 五格机械门的归属，全部从工件派生，不写字面量。

派生来源：
  · 跨进程那一问  ← xproc 门的整份日志（逐批 FAILED 行）
  · 门体五格      ← 反突变 campaign 的 red_beyond_control（控制轮的绿是前提）
  · 无新增红      ← 3×3 全量 A/B 的名字差集
  · 坐标          ← git 现算（40 位）+ patch 重放到 1f86a8f 树、write-tree 与 e8b994c^{tree} 比对
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path("D:/moodle/_qoder_integration_20260919")
RUN = Path("D:/moodle/_qoder_f_run")
RCP = RUN / "o225_receipts"
HEAD = "408d851"
SUPERSEDED = "1f86a8f"          # 不得并线那一版（重放的基树）
BASE = "aabd47e"                # 整条链之前
PATCHES = sorted((RUN / "patches_phaseab").glob("*.patch"))
MUT = RCP / "ord0253_claimfirst_mutation_receipt.json"
XPROC_LOG = RCP / "xproc_three_runs_0923_phaseAB.txt"
AB = RCP / "ord0253_phaseAB_ab_0923.json"
OUT = RCP / "ord0253_phaseab_receipt.json"

GATES = {  # 仲裁 5796421307 §② 点名的五格，逐格钉到 nodeid
    "① 竞争连接在 impl 之前看到已提交的 NULL claim":
        "test_10_a_competing_connection_sees_the_committed_null_claim_before_impl_starts",
    "② 败者不进 impl，mission/run 行数不长":
        "test_11_the_loser_is_stopped_before_impl_and_persists_nothing",
    "③ 赢家副作用与 completed 回执同一次提交可见":
        "test_12_the_claim_commits_first_and_the_answer_shares_one_commit_with_the_work",
    "④ 故障注入后 Phase B 无 durable 行而 NULL claim 仍在":
        "test_13_a_phase_b_failure_leaves_no_durable_side_effect_but_keeps_the_null_claim",
    "⑤ stale claim 恢复不删不过期重跑且不重复副作用":
        "test_14_stale_claim_recovery_fails_closed_and_duplicates_nothing",
}


def git(*args: str) -> str:
    p = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert p.returncode == 0, f"git {' '.join(args)} rc={p.returncode} :: {p.stderr[:200]}"
    return p.stdout.strip()


def sha256_12(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def replay_proofs() -> dict:
    """把 patch 重放到 1f86a8f 的树上，write-tree 必须等于 e8b994c 的树。"""
    idx = Path(tempfile.gettempdir()) / f"cnx_replay_{datetime.now():%H%M%S}.idx"
    try:
        env_idx = str(idx.as_posix())
        def g(*args: str) -> str:
            import os
            e = dict(os.environ, GIT_INDEX_FILE=env_idx)
            p = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", env=e)
            assert p.returncode == 0, f"replay 步骤失败 {args[:3]}: {p.stderr[:250]}"
            return p.stdout.strip()
        g("read-tree", SUPERSEDED)
        for patch in PATCHES:
            g("apply", "--cached", patch.as_posix())
        replayed = g("write-tree")
    finally:
        idx.unlink(missing_ok=True)
    want = git("rev-parse", f"{HEAD}^{{tree}}")
    return {"replayed_tree": replayed, "head_tree": want, "byte_equal": replayed == want,
            "base_tree_rev": SUPERSEDED, "patches": [
                {"name": p.name, "bytes": p.stat().st_size, "sha256_12": sha256_12(p)}
                for p in PATCHES]}


def xproc_readings() -> dict:
    text = XPROC_LOG.read_text(encoding="utf-8", errors="replace")
    batches = [b for b in re.split(r"=== RUN \d+ ===", text)[1:]]
    per = [{"summary": re.findall(r"(\d+ (?:passed|failed)[^\n]*)", b)[-1] if b else "",
            "red_cells": sorted(set(re.findall(r"FAILED \S+::(\w+)", b))),
            "shape_tallies": re.findall(r"\{[^{}]*?(?:GHOST|UNNAMED)[^{}]*\}", b)[-1:]}
           for b in batches]
    reds = sum(len(p["red_cells"]) for p in per)
    return {"batches": len(per), "per_batch": per, "red_cells_total": reds,
            "reading": ("全部批次 0 红 ⇒ 跨进程那一问在这一版上有实测读数；"
                        "任何一批有红 ⇒ 记 RED 并附具名格与形态计数"),
            "verdict": "CROSS_PROCESS_MEASURED_GREEN" if (per and reds == 0) else "MEASURED_RED"}


def mutation_readings() -> dict:
    data = json.loads(MUT.read_text(encoding="utf-8"))
    control_red = data["control"]["red_nodeids"]
    table = {}
    for name, spec in data["mutations"].items():
        new_red = spec["red_beyond_control"]
        table[name] = {
            "claimed_result": spec["claimed_result"],
            "derived_result": spec["derived_result"],
            "red_beyond_control": new_red,
            "named_targets_red": spec["named_targets_red"],
            "expected_green_arm_broke": spec["expected_green_arm_broke"],
            "owner": spec["owner_assertion"],
        }
    gates = {}
    for label, nodeid in GATES.items():
        killers = [n for n, t in table.items() if nodeid in t["red_beyond_control"]]
        gates[label] = {
            "nodeid": nodeid,
            "green_in_control": nodeid not in control_red,
            "killed_by": killers,
            "has_a_killer": bool(killers),
        }
    return {"campaign_valid": data.get("campaign_valid"),
            "control": {"summary": data["control"]["summary"],
                        "executed": data["control"].get("executed_from_summary"),
                        "red_nodeids": control_red},
            "restore_verified": data["restore_verified"],
            "target_sha256_16_before_and_after": data["target_sha256_16_before_and_after"],
            "anchor_preflight": data.get("anchor_preflight"),
            "five_gates": gates, "mutations": table}


def ab_readings() -> dict:
    if not AB.is_file():
        return {"status": "NOT_MEASURED",
                "note": "3×3 全量 A/B 的收据还没落盘 ⇒ 这一格不许写成'无新增红'"}
    data = json.loads(AB.read_text(encoding="utf-8"))
    cmp = data.get("comparison")
    return {"status": "MEASURED" if cmp else "PARTIAL", "comparison": cmp,
            "per_round_counts": {t: v["per_round_red_counts"] for t, v in data["trees"].items()},
            "collect_denominators": {t: v["collect"]["collected"] for t, v in data["trees"].items()},
            "blob_equality": {t: all(v.get("equal", True) for v in
                                     info["blob_equality"].values())
                              for t, info in data["trees"].items()},
            "full_sha": {t: info["full_sha"] for t, info in data["trees"].items()}}


def main() -> int:
    head40 = git("rev-parse", HEAD)
    xproc = xproc_readings()
    mut = mutation_readings()
    ab = ab_readings()
    five = mut["five_gates"]
    gate4 = five["④ 故障注入后 Phase B 无 durable 行而 NULL claim 仍在"]
    gate5 = five["⑤ stale claim 恢复不删不过期重跑且不重复副作用"]
    gate1 = five["① 竞争连接在 impl 之前看到已提交的 NULL claim"]
    paths = ["backend/app/main.py", "backend/tests/test_qoder_agent_command_claim_first.py",
             "backend/tests/test_qoder_agent_command_idempotency.py",
             "backend/tests/test_qoder_agent_command_idempotency_xproc.py"]

    def verdict(gate: dict, extra_killer: str | None = None) -> str:
        """绿的判级必须有反突变撑着：控制轮绿 + 至少一枚突变打红它那一格。"""
        if not mut["campaign_valid"] or not gate["green_in_control"]:
            return "NOT_PROVEN（控制轮不成立或这一格本身是红的）"
        killers = list(gate["killed_by"])
        if extra_killer and extra_killer in killers:
            return "MEASURED_GREEN_WITH_NAMED_KILLER"
        return "MEASURED_GREEN_WITH_NAMED_KILLER" if killers else "GREEN_BUT_NO_KILLER"

    receipt = {
        "what": "ORD-0253 · Phase A/B claim-first（仲裁 5796421307 §② 的形状）三格读数 + 五格机械门归属",
        "lane": "F 8ccd71d8",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "coordinates": {
            "head": head40, "tree": git("rev-parse", f"{head40}^{{tree}}"),
            "chain": git("log", "--format=%h", f"{BASE}..{head40}").split(),
            "chain_with_subjects": git("log", "--format=%h %s", f"{BASE}..{head40}").splitlines(),
            "not_mergeable_superseded": SUPERSEDED + " " + git("rev-parse", SUPERSEDED),
            "base_before_this_order": BASE + " " + git("rev-parse", BASE),
            "blobs": {p: git("rev-parse", f"{head40}:{p}") for p in paths},
            "pushed": False,
            "replay_proof": replay_proofs()},
        "three_readings": {
            "(i) 占位=跨进程互斥点（且是 claim-first）":
                f"{xproc['verdict']}（跨进程门 {xproc['batches']} 批，红格 {xproc['red_cells_total']}）"
                + " + " + verdict(gate1),
            "(ii) mission 与占位同生同死（Phase B 回滚收得回）": verdict(gate4),
            "(iii) stale-claim recovery 区分 IN_FLIGHT/COMPLETED 且不重复副作用": verdict(gate5),
        },
        "cross_process": xproc,
        "gate_and_mutations": mut,
        "regression_ab": ab,
        "instrument_notes": [
            "分母：`pytest -q` 不打印 collected 行 ⇒ 门体格数从摘要行 passed+failed+error 派生",
            "M3（回填守卫拆开）SURVIVED 是**读数**：进程内没有任何一格会把已填好的回执推进到回填那一步；"
            "这一格登记为『本门不测这一问』，不当 KILLED 卖",
            "上一版依赖的 join_transaction_mode=create_savepoint 在 pysqlite 下最外层 RELEASE 即提交"
            "（探针 o253_ghost_writer_probe 的语句序列）⇒ 已由 M2 反突变钉住：装回来 ④ 就红",
        ],
        "print_policy": "只印 sha/计数/语句名/约束名；0 key、0 env 值、0 用户库路径",
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps({"head": receipt["coordinates"]["head"][:9],
                      "replay_equal": receipt["coordinates"]["replay_proof"]["byte_equal"],
                      "three": receipt["three_readings"],
                      "campaign_valid": receipt["gate_and_mutations"]["campaign_valid"],
                      "restore": receipt["gate_and_mutations"]["restore_verified"],
                      "ab_status": receipt["regression_ab"]["status"],
                      "gates": {k[:1]: v["green_in_control"] and v["has_a_killer"]
                                for k, v in
                                receipt["gate_and_mutations"]["five_gates"].items()}},
                     ensure_ascii=False, indent=1))
    print(f"WROTE {OUT} ({OUT.stat().st_size} B) sha256[:12]={sha256_12(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
