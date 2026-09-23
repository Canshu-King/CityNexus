"""把 ORD-0253 claim-first 的反突变交齐成 **CNX_REVERSE_MUTATION_RECEIPT_V1**（一枚突变一份收据）。

与上一版的差别就是包工头 00:2x 要的"轮次字段"：
  · 被测树 = `git archive 408d851ec…` 的一次性只读导出（tree_kind=clean_sha），**不在工作树里改产品码**；
  · 每枚突变跑 **3 轮**，`mutated_runs.rounds=3` + 逐轮 exit/counts/红 nodeid/门外第二条连接的 durable 行读数；
  · claimed_result 只在"点名的每一格在 3 轮里都红"时才写 KILLED，否则 **STREAK_BROKEN**；
  · M3 按仲裁 5798572255 钉死：只记 SURVIVED / UNPROVEN，绝不写成"守卫已被反突变证明"。
derived_result 恒 null，交红队 d2305848 派生。
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUNS_PER_MUTANT = 3
HEAD = "408d851ec2ec7ab02142233c6a497c5037adfda4"
REPO = Path("D:/moodle/_qoder_integration_20260919")
RUN = Path("D:/moodle/_qoder_f_run")
OUT_DIR = RUN / "o225_receipts" / "ord0253_claimfirst_v1"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
GATE_REL = "tests/test_qoder_agent_command_claim_first.py"
TARGET_REL = "backend/app/main.py"
SCHEMA = "CNX_REVERSE_MUTATION_RECEIPT_V1"
FAIL_RE = re.compile(r"FAILED \S+::(\w+)")
DOOR_BLOBS = {
    "backend/app/main.py": None,
    "backend/tests/test_qoder_agent_command_claim_first.py": None,
    "backend/tests/test_qoder_agent_command_idempotency.py": None,
    "backend/tests/test_qoder_agent_command_idempotency_xproc.py": None,
}

MUTANTS = {
    "M1_claim_never_committed": {
        "edits": [("            claim_tx.commit()          # 早于任何 mission / run / audit / event",
                   "            claim_tx.rollback()  # 突变：占位不落库，所有权点消失")],
        "claim_broken": "Phase A 的独立提交 = 跨进程所有权点",
        "carriers_removed": ["claim_tx.commit()（占位先于任何副作用 durable）"],
        "primary": ["test_10_a_competing_connection_sees_the_committed_null_claim_before_impl_starts",
                    "test_12_the_claim_commits_first_and_the_answer_shares_one_commit_with_the_work"],
        "expect_green": ["test_11_the_loser_is_stopped_before_impl_and_persists_nothing"],
    },
    "M2_savepoint_join_restored": {
        "edits": [("        work_session = Session(bind=work_conn, expire_on_commit=False)",
                   '        work_session = Session(bind=work_conn,\n'
                   '                                 join_transaction_mode="create_savepoint",\n'
                   '                                 expire_on_commit=False)')],
        "claim_broken": "Phase B 的单一提交边界（pysqlite 下 create_savepoint 的最外层 RELEASE 即提交）",
        "carriers_removed": ["engine.begin() 之下被调方 commit 不落库这一性质"],
        "primary": ["test_13_a_phase_b_failure_leaves_no_durable_side_effect_but_keeps_the_null_claim",
                    "test_12_the_claim_commits_first_and_the_answer_shares_one_commit_with_the_work"],
        "expect_green": ["test_11_the_loser_is_stopped_before_impl_and_persists_nothing"],
    },
    "M3_fill_guard_removed": {
        "edits": [("                .where(IdempotencyKey.key == scoped_key,\n"
                   "                       IdempotencyKey.response_json.is_(None))",
                   "                .where(IdempotencyKey.key == scoped_key)")],
        "claim_broken": "回填只允许 NULL → completed（不覆盖已填回执）",
        "carriers_removed": ["update(...).where(..., response_json IS NULL) 里的 IS NULL 谓词"],
        "primary": [],            # 按仲裁：这一枚无点名格；只记 SURVIVED / UNPROVEN
        "expect_green": ["test_14_stale_claim_recovery_fails_closed_and_duplicates_nothing"],
    },
    "M4_claim_ttl_shortened": {
        "edits": [("                    expires_at=(now + timedelta(days=7)).isoformat(),",
                   "                    expires_at=(now + timedelta(minutes=5)).isoformat(),")],
        "claim_broken": "completed 回执沿用现成 +7d 语义",
        "carriers_removed": ["+timedelta(days=7)（换成 5 分钟＝给到点回收开门）"],
        "primary": ["test_9_completed_receipts_keep_the_existing_seven_day_semantics"],
        "expect_green": ["test_8_a_committed_run_never_leaves_an_unfilled_claim"],
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
        "claim_broken": "唯一索引在 impl 之前就把败者挡住（不进 impl、不重复副作用）",
        "carriers_removed": ["IntegrityError 分支里的读赢家 + fail-closed 409"],
        "primary": ["test_11_the_loser_is_stopped_before_impl_and_persists_nothing",
                    "test_1_an_unfilled_claim_blocks_the_write_and_is_answered_with_the_existing_409"],
        "expect_green": [],
    },
}


def git(*args: str) -> str:
    p = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert p.returncode == 0, f"git {args[:2]} rc={p.returncode} {p.stderr[:180]}"
    return p.stdout.strip()


def sha256_16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def durable_rows(backend: Path) -> dict:
    """门外第二条 sqlite3 直连的 durable 读数（与门内那把同源，但我在这里独立复量）。"""
    import sqlite3
    db = os.environ["CITYNEXUS_DATABASE_URL"].replace("sqlite:///", "", 1)
    with sqlite3.connect(db, timeout=30) as conn:
        rows = list(conn.execute(
            "SELECT operation, count(*), sum(response_json IS NULL) FROM idempotency_keys "
            "WHERE operation='agent.command' GROUP BY operation"))
        missions = conn.execute("SELECT count(*) FROM journey_missions").fetchone()[0]
    return {"agent_command_claim_rows": (rows[0][1] if rows else 0),
            "agent_command_unfilled_rows": (rows[0][2] if rows else 0),
            "journey_missions_total": missions, "db_file": Path(db).name}


def run_suite(backend: Path) -> dict:
    t0 = time.time()
    p = subprocess.run([PY, "-m", "pytest", GATE_REL, "-q", "--no-header", "-p", "no:cacheprovider",
                        "-rf", "--tb=no"], cwd=str(backend), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    out = p.stdout or ""
    tail = next((l for l in reversed(out.splitlines())
                 if "passed" in l or "failed" in l or "error" in l), "")

    def num(label: str) -> int:
        m = re.search(rf"(\d+) {label}", tail)
        return int(m.group(1)) if m else 0

    return {"exit_code": p.returncode, "summary": tail, "seconds": round(time.time() - t0, 1),
            "executed": num("passed") + num("failed") + num("error"),
            "pytest_counts": {"passed": num("passed"), "failed": num("failed"),
                              "errors": num("error"), "skipped": num("skipped")},
            "red_nodeids": sorted(set(FAIL_RE.findall(out))),
            "stderr_tail": (p.stderr or "")[-200:]}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tree = git("rev-parse", f"{HEAD}^{{tree}}")
    root = RUN / f"e_v1_{HEAD[:7]}"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    proc = subprocess.run(f'git archive --format=tar {HEAD} | tar -xf - -C "{root}"',
                          shell=True, cwd=REPO, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=900)
    assert proc.returncode == 0, f"SETUP：archive 解不出 {HEAD[:7]}：{proc.stderr[:250]}"
    backend = root / "backend"
    target = backend / "app/main.py"
    # 库：一次导出用一只具名临时库，控制轮与突变轮共用 ⇒ 唯一变量是产品码
    import tempfile
    tmp_db = Path(tempfile.mkdtemp(prefix="cnx_claimfirst_v1_")) / "v1.db"
    os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{tmp_db.as_posix()}"
    os.environ["CITYNEXUS_DEMO_MODE"] = "true"
    for name in DOOR_BLOBS:
        DOOR_BLOBS[name] = git("rev-parse", f"{HEAD}:{name}")
        export_blob = blob_sha1(root / name)
        assert export_blob == DOOR_BLOBS[name], f"SETUP：导出字节 != 提交字节 {name}"

    env_block = {
        "cwd": str(backend), "python_executable": PY,
        "python_version": subprocess.run([PY, "-V"], capture_output=True, text=True).stdout.strip(),
        "pytest_version": subprocess.run([PY, "-m", "pytest", "--version"], capture_output=True,
                                         text=True).stdout.splitlines()[0].strip(),
        "platform": platform.platform(),
        "pythonpath": ["（未设：靠 cwd=导出的 backend/）"],
        "required_local_modules": sorted(DOOR_BLOBS),
        "forbidden_command_surface_hits": [h for h in (
            "demo/reset" if "demo/reset" in " ".join(sys.argv) else "",) if h],
        "row_column_instrument": {
            "module": "门内 tests/test_qoder_agent_command_claim_first.py::_durable（sqlite3 直连）",
            "git_blob_sha1": DOOR_BLOBS["backend/tests/test_qoder_agent_command_claim_first.py"],
            "note": "判级用的行读数出自门本身；本收据另在门外用第二条连接复量（见 runs[].second_connection）"},
    }
    control_runs = [run_suite(backend) for _ in range(RUNS_PER_MUTANT)]
    control_red = sorted({n for r in control_runs for n in r["red_nodeids"]})
    control_ok = all(r["executed"] >= 14 for r in control_runs) and not control_red
    control_rows = durable_rows(backend)
    print(f"[control] executed={[r['executed'] for r in control_runs]} "
          f"red={control_red} valid={control_ok}", flush=True)
    base_text = target.read_text(encoding="utf-8")
    base_sha = sha256_16(target)
    index = {"schema_version": SCHEMA, "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
             "order": "ORD-0253", "lane": "F 8ccd71d8", "head": HEAD, "tree": tree,
             "rounds_per_mutant": RUNS_PER_MUTANT, "campaign_valid": control_ok,
             "control": {"runs": control_runs, "red_union": control_red,
                         "second_connection": control_rows},
             "ruling": ("仲裁 5798572255：M3 = 具名非阻塞覆盖率余项，只记 SURVIVED/UNPROVEN；"
                        "闭单证据不得把 NULL→completed 守卫说成已被反突变证明"),
             "receipts": []}
    for name, spec in MUTANTS.items():
        text = base_text
        for a, b in spec["edits"]:
            assert text.count(a) == 1, f"{name}：锚点 {text.count(a)} 次 ≠ 唯一 ⇒ 中止"
            text = text.replace(a, b)
        target.write_text(text, encoding="utf-8", newline="\n")
        mutant_sha = sha256_16(target)
        assert mutant_sha != base_sha, f"{name}：突变后 sha 未变 ⇒ 空操作"
        runs = []
        for i in range(RUNS_PER_MUTANT):
            r = run_suite(backend)
            r["round"] = i + 1
            r["second_connection"] = durable_rows(backend)
            runs.append(r)
            print(f"[{name}] r{i+1} rc={r['exit_code']} red={len(r['red_nodeids'])} "
                  f"rows={r['second_connection']['agent_command_claim_rows']}", flush=True)
        target.write_bytes(base_text.encode("utf-8"))
        assert sha256_16(target) == base_sha, f"{name}：还原后 sha 不一致 ⇒ 停"
        for f, want in DOOR_BLOBS.items():        # 还原 + 没碰测试文件，两件事一起验
            assert blob_sha1(root / f) == want, f"{name}：{f} 字节变了"
        red_union = sorted({n for r in runs for n in r["red_nodeids"]})
        new_union = sorted(set(red_union) - set(control_red))
        per_node_rounds = {n: sum(1 for r in runs if n in r["red_nodeids"])
                           for n in spec["primary"]}
        all_named_every_round = bool(spec["primary"]) and all(
            v == RUNS_PER_MUTANT for v in per_node_rounds.values())
        if not spec["primary"]:
            claimed, note = "SURVIVED", ("无点名格 ⇒ 按仲裁只记 SURVIVED / UNPROVEN；"
                                        "**不得**读成『守卫无效』，也不得读成『守卫已被证明』")
        elif all_named_every_round:
            claimed, note = "KILLED", "点名的每一格在 3 轮里都红 ⇒ 承重（仍待 verifier derived）"
        else:
            claimed, note = "STREAK_BROKEN", f"逐轮命中次数 {per_node_rounds}（<{RUNS_PER_MUTANT}）⇒ 不写 KILLED"
        receipt = {
            "schema_version": SCHEMA, "receipt_kind": "reverse_mutation",
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "scope": {"repo": "Canshu-King/CityNexus", "exact_sha": HEAD, "tree_kind": "clean_sha",
                      "composite_recipe": [], "dirty": False, "dirty_paths": [],
                      "target_nodeids": spec["primary"] or ["（无点名格：M3 记 UNPROVEN）"],
                      "run_shape": "whole-door（14 格一起跑，不挑着跑）",
                      "command_argv": [PY, "-m", "pytest", GATE_REL, "-q", "--no-header",
                                       "-p", "no:cacheprovider", "-rf", "--tb=no"],
                      "tree_kind_check": {f: {"commit_blob_sha1": v,
                                              "export_blob_sha1": blob_sha1(root / f),
                                              "equal": blob_sha1(root / f) == v}
                                          for f, v in DOOR_BLOBS.items()},
                      "note": "被测树 = git archive 的一次性只读导出；产品码只在导出里被改，导出外用 sha 回验还原"},
            "environment": env_block,
            "baseline": {"receipt_ref": "本批控制轮（同一次导出、同一只库、未突变）",
                         "same_exact_sha": True, "same_target_nodeids": True, "same_run_shape": True,
                         "control_rounds": RUNS_PER_MUTANT,
                         "target_outcomes": {n: ("RED" if n in control_red else "GREEN")
                                             for n in (spec["primary"] + spec["expect_green"])},
                         "this_run_exit_code": control_runs[-1]["exit_code"],
                         "this_run_executed": control_runs[-1]["executed"],
                         "this_run_pytest_counts": control_runs[-1]["pytest_counts"],
                         "failed_nodeids": control_red,
                         "second_connection": control_rows},
            "mutation": {"mutation_id": name, "claim_broken": spec["claim_broken"],
                         "carriers_removed": spec["carriers_removed"],
                         "allowed_scope": "只改 backend/app/main.py（keyed run_agent_command 的 Phase A/B）",
                         "actual_scope": ["backend/app/main.py"],
                         "primary_target_nodeids": spec["primary"],
                         "expected_green_arm": spec["expect_green"],
                         "patch_or_mutator_ref": str(Path(__file__).resolve()),
                         "no_test_file_touched": True,
                         "changed_files": [TARGET_REL],
                         "digest_semantics": {"base_sha256_16": base_sha, "mutant_sha256_16": mutant_sha,
                                              "restored_sha256_16": sha256_16(target),
                                              "anchors": [a[:70] for a, _ in spec["edits"]]}},
            "mutated_runs": {"rounds": RUNS_PER_MUTANT, "runs": runs,
                             "red_union": red_union, "red_beyond_control": new_union},
            "derivation": {"claimed_result": claimed, "claimed_result_note": note,
                           "derived_result": None,
                           "direct_red_nodeids": sorted(set(spec["primary"]) & set(new_union)),
                           "collateral_red_nodeids": sorted(set(new_union) - set(spec["primary"])),
                           "expected_green_arm_held": [n for n in spec["expect_green"]
                                                       if n not in red_union],
                           "expected_green_arm_broke": [n for n in spec["expect_green"]
                                                        if n in red_union],
                           "verifier_problems": [
                               "claimed_result 由 mutated_runs 派生，不是自宣；derived_result 留给 verifier",
                               "M3 之外若有人把『回填守卫』写成已证明承重 ⇒ 与本收据冲突，以本收据为准"],
                           "batch_tag": f"o253-claimfirst-{HEAD[:7]}",
                           "primary_red_rounds": per_node_rounds,
                           "every_round_restored_byte_exact": True,
                           "baseline_claim_rows": control_rows["agent_command_claim_rows"],
                           "mutated_claim_rows": [r["second_connection"]["agent_command_claim_rows"]
                                                  for r in runs],
                           "mutated_unfilled_rows": [r["second_connection"]["agent_command_unfilled_rows"]
                                                     for r in runs]},
        }
        out = OUT_DIR / f"v1_receipt_{name}_{HEAD[:7]}.json"
        out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        index["receipts"].append({"mutation_id": name, "file": out.name, "bytes": out.stat().st_size,
                                  "blob_sha1": blob_sha1(out), "claimed_result": claimed,
                                  "primary_red_rounds": per_node_rounds,
                                  "red_beyond_control": new_union})
        print(f"  → {out.name} claimed={claimed}", flush=True)
    (OUT_DIR / "v1_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1),
                                           encoding="utf-8", newline="\n")
    print(json.dumps(index["receipts"], ensure_ascii=False, indent=1))
    print(f"WROTE {OUT_DIR/'v1_index.json'} ({(OUT_DIR/'v1_index.json').stat().st_size} B)")
    print(f"campaign_valid={control_ok} 还原 sha={sha256_16(target) == base_sha}")
    return 0 if control_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
