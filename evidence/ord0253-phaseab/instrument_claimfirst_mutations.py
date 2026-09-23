"""ORD-0253 claim-first（原子版 1f86a8f）门体的反突变 campaign。

四枚**只碰产品码**的突变（改断言不算杀手，B-1），每枚跑**整个文件** 9 格并把
每一格的红/绿都记下来：点名的 target 是主证，其余红是附带（primary/collateral 分开），
`SURVIVED` 也照实写 —— 存活可能证明那条保护点根本不在本门的射程里，那是要登记的事实。

规矩：claimed_result 由 red_nodeids 机械派生（不手写），derived_result 一律 null 交 verifier；
跑完逐字节还原并回验 sha1，还原失败立刻中止。控制轮（未突变）同批跑，控制轮不绿则整批作废。
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # 会印读数的仪器必须先钉输出编码

BACKEND = Path("D:/moodle/_qoder_f_ord253_20260923/backend")
TARGET = BACKEND / "app/main.py"
GATE = "tests/test_qoder_agent_command_claim_first.py"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
OUT = Path("D:/moodle/_qoder_f_run/o225_receipts/ord0253_claimfirst_mutation_receipt.json")
FAIL_RE = re.compile(r"FAILED \S+::(\w+)")

MUTANTS = {
    "M1_claim_never_committed": {
        "edits": [("            claim_tx.commit()          # 早于任何 mission / run / audit / event",
                   "            claim_tx.rollback()  # 突变：占位不落库，所有权点消失")],
        "primary": ["test_10_a_competing_connection_sees_the_committed_null_claim_before_impl_starts",
                    "test_12_the_claim_commits_first_and_the_answer_shares_one_commit_with_the_work"],
        "expect_green": ["test_11_the_loser_is_stopped_before_impl_and_persists_nothing"],
        "owner": "机械门①/③：占位不先提交 ⇒ 跨进程没有所有权点。② 自带预置占位，不该被这枚碰到"
                 "（碰到就说明 ② 其实在测同一条早先回放路径，而不是测败者不进 impl）",
    },
    "M2_savepoint_join_restored": {
        "edits": [('        work_session = Session(bind=work_conn, expire_on_commit=False)',
                   '        work_session = Session(bind=work_conn,\n'
                   '                                 join_transaction_mode="create_savepoint",\n'
                   '                                 expire_on_commit=False)')],
        "primary": ["test_13_a_phase_b_failure_leaves_no_durable_side_effect_but_keeps_the_null_claim",
                    "test_12_the_claim_commits_first_and_the_answer_shares_one_commit_with_the_work"],
        "expect_green": ["test_11_the_loser_is_stopped_before_impl_and_persists_nothing"],
        "owner": "机械门④/③：把 1f86a8f 那套 create_savepoint 装回来 ⇒ pysqlite 下最外层 RELEASE "
                 "即提交，注入点之前的东西就该 durable。这一枚是**上一版被判不得并线的那条机制**，"
                 "它必须被这一格抓住；抓不住就说明 ④ 是空的",
    },
    "M3_fill_guard_removed": {
        "edits": [("                .where(IdempotencyKey.key == scoped_key,\n"
                   "                       IdempotencyKey.response_json.is_(None))",
                   "                .where(IdempotencyKey.key == scoped_key)")],
        "primary": [],
        "expect_green": ["test_14_stale_claim_recovery_fails_closed_and_duplicates_nothing",
                         "test_4_the_happy_path_still_creates_exactly_one_mission_and_fills_the_claim"],
        "owner": "「只允许 NULL → 完成」这一道守卫：预期**存活** —— 进程内没有任何一格会把"
                 "已填好的回执推进到回填那一步（早先的回放在前面就返回了）。存活就登记成"
                 "『本门不测这一问』，不许写成 KILLED",
    },
    "M4_claim_ttl_shortened": {
        "edits": [("                    expires_at=(now + timedelta(days=7)).isoformat(),",
                   "                    expires_at=(now + timedelta(minutes=5)).isoformat(),")],
        "primary": ["test_9_completed_receipts_keep_the_existing_seven_day_semantics"],
        "expect_green": ["test_8_a_committed_run_never_leaves_an_unfilled_claim"],
        "owner": "completed 回执沿用现成 +7d：把占位 TTL 改短就是给『到点回收』开第一道门（仲裁禁止）",
    },
    "M5_conflict_does_not_block_the_work": {
        "edits": [("        except IntegrityError as exc:\n"
                   "            claim_tx.rollback()\n"
                   "            raced = _replay_committed_accept(session, scoped_key, signature, wait=True)\n"
                   "            if raced is not None:\n"
                   "                return raced\n"
                   "            raise HTTPException(\n"
                   "                409, \"agent idempotency record is incomplete\"\n"
                   "            ) from exc\n",
                   "        except IntegrityError:\n"
                   "            claim_tx.rollback()\n"
                   "            return None  # 突变：撞了键也照样去干活\n")],
        "primary": ["test_11_the_loser_is_stopped_before_impl_and_persists_nothing",
                    "test_1_an_unfilled_claim_blocks_the_write_and_is_answered_with_the_existing_409"],
        "expect_green": [],
        "owner": "机械门②：唯一索引说\"不是你的\"之后还放行 impl ⇒ 所有权点不存在。"
                 "这一枚是上一轮 campaign 暴露出来的**空缺**（② 当时没有任何杀手），补上才算数",
    },
}


def sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def run_gate() -> dict:
    t0 = time.time()
    p = subprocess.run([PY, "-m", "pytest", GATE, "-q", "--no-header", "-p", "no:cacheprovider",
                        "-rf", "--tb=line"], cwd=str(BACKEND), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    out = p.stdout or ""
    tail = next((l for l in reversed(out.splitlines()) if "passed" in l or "failed" in l
                 or "error" in l), "")

    def num(label: str) -> int:
        m = re.search(rf"(\d+) {label}", tail)
        return int(m.group(1)) if m else 0

    executed = num("passed") + num("failed") + num("error")
    return {"rc": p.returncode, "summary": tail, "seconds": round(time.time() - t0, 1),
            "executed_from_summary": executed, "passed": num("passed"),
            "denominator_note": "`pytest -q` 不打 collected 行 ⇒ 分母从摘要行的 passed+failed+error 派生，"
                                "不靠肉眼数",
            "collection_broke": "error" in tail.lower() and num("error") > 0,
            "red_nodeids": sorted(set(FAIL_RE.findall(out))),
            "stdout_tail": out.strip().splitlines()[-14:]}


def derive(red_beyond_control: list[str], primary: list[str]) -> tuple[str, bool]:
    """claimed_result 只从实测红集派生：点名的格一根没红 ⇒ SURVIVED，不挑个好看的词。"""
    hit = [n for n in primary if n in red_beyond_control]
    return ("KILLED" if hit else "SURVIVED"), bool(primary) and len(hit) == len(primary)


def main() -> int:
    original = TARGET.read_bytes()
    base_sha = sha16(TARGET)
    receipt = {"what": "claim-first 原子版门体的反突变 campaign（4 枚产品码突变 + 控制轮）",
               "lane": "F 8ccd71d8",
               "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
               "gate_file": GATE, "target_file": str(TARGET),
               "target_sha256_16_before_and_after": base_sha,
               "run_shape": f"{PY} -m pytest {GATE} -q --tb=line（每枚跑整份 9 格，不挑着跑）",
               "b_rule": "claimed_result 由 red_nodeids 机械派生；derived_result 恒 null 交 verifier",
               "mutations": {}, "restore_verified": False}

    # 锚点预检：非唯一锚点会造出假突变（或干脆写坏产品码），必须在跑控制轮**之前**炸
    text = TARGET.read_text(encoding="utf-8")
    preflight = {}
    for name, spec in MUTANTS.items():
        for a, _ in spec["edits"]:
            preflight[f"{name}::{a[:48]}"] = text.count(a)
    bad = {k: v for k, v in preflight.items() if v != 1}
    receipt["anchor_preflight"] = {"counts": preflight, "non_unique": bad}
    assert not bad, f"SETUP：锚点不唯一 ⇒ 中止，不跑任何读数：{bad}"

    control = run_gate()
    receipt["control"] = control
    control_ok = control["executed_from_summary"] >= 14 and not control["collection_broke"]
    receipt["campaign_valid"] = control_ok
    receipt["scope"] = {
        "branch": subprocess.run(["git", "-C", str(BACKEND.parent), "rev-parse", "--abbrev-ref", "HEAD"],
                                 capture_output=True, text=True).stdout.strip(),
        "head": subprocess.run(["git", "-C", str(BACKEND.parent), "rev-parse", "HEAD"],
                               capture_output=True, text=True).stdout.strip(),
        "superseded_and_not_mergeable": "1f86a8f（仲裁：(i) NOT MET AS CLAIM-FIRST，不得并线）",
        "cells_executed_in_control": control["executed_from_summary"]}
    print(f"[control] rc={control['rc']} executed={control['executed_from_summary']} "
          f"red={len(control['red_nodeids'])} :: {control['summary']}", flush=True)
    if not control_ok:
        receipt["note"] = "控制轮不绿/收不起来 ⇒ 整批作废，不出任何判级"
        OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        return 2

    for name, spec in MUTANTS.items():
        text = TARGET.read_text(encoding="utf-8")
        for a, b in spec["edits"]:
            n = text.count(a)
            assert n == 1, f"{name}：锚点出现 {n} 次而非唯一 ⇒ 中止（放宽锚点=假突变）"
            text = text.replace(a, b)
        TARGET.write_text(text, encoding="utf-8", newline="\n")
        mutated = sha16(TARGET)
        assert mutated != base_sha, f"{name}：突变后 sha 未变 ⇒ 这是个空操作，不许记读数"
        r = run_gate()
        red = r["red_nodeids"]
        new_red = sorted(set(red) - set(control["red_nodeids"]))
        claimed, all_named = derive(new_red, spec["primary"])
        receipt["mutations"][name] = {
            "mutation": {"base_sha256_16": base_sha, "mutant_sha256_16": mutated,
                         "anchors_changed": [a[:70] for a, _ in spec["edits"]]},
            "owner_assertion": spec["owner"],
            "reading": r,
            "control_was_already_red": sorted(set(red) & set(control["red_nodeids"])),
            "red_beyond_control": new_red,
            "named_targets_red": [n for n in spec["primary"] if n in red],
            "named_targets_green": [n for n in spec["primary"] if n not in red],
            "all_named_targets_red": all_named,
            "expected_green_arm_held": [n for n in spec["expect_green"] if n not in red],
            "expected_green_arm_broke": [n for n in spec["expect_green"] if n in red],
            "claimed_result": claimed,
            "derived_result": None,
        }
        print(f"[{name}] rc={r['rc']} 新增红={new_red} claimed="
              f"{receipt['mutations'][name]['claimed_result']}", flush=True)
        TARGET.write_bytes(original)
        assert sha16(TARGET) == base_sha, f"{name}：还原后 sha 不一致 ⇒ 停"
        OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    TARGET.write_bytes(original)
    receipt["restore_verified"] = sha16(TARGET) == base_sha
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps({k: v["claimed_result"] for k, v in receipt["mutations"].items()},
                     ensure_ascii=False))
    print(f"\nWROTE {OUT} ({OUT.stat().st_size} B)  还原={receipt['restore_verified']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
