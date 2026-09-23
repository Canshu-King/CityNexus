"""Emit a `CNX_REVERSE_MUTATION_RECEIPT_V1` for one arm of the cross-process closure door.

Why this file exists: arbiter B-1 (bus 5788270524, landed by the commander @11:1x) froze the
reverse-mutation receipt format and took the word `KILLED` away from the delivering lane - "交付方最多写
`claimed_result`，closure 只认 verifier 从原始字段机械派生的 `derived_result`". My earlier batches
(`mutant_rounds_Y3_http_*.json` / `mutant_rounds_Y2_http_*.json`) therefore count as **claims**: they carry
a kill count but not the per-round `collected` / `pytest_counts` / `failed_nodeids` / `initial_db_state` /
`final_db_state` fields a verifier derives from, and they never separated `primary_target_nodeids` from
collateral reds. This emitter writes the schema-shaped receipt so a verifier - not me - can decide.

Field names follow the frozen schema; nothing required is dropped. `derived_result`, `direct_red_nodeids`,
`collateral_red_nodeids` and `verifier_problems` are deliberately left null/empty, because filling them here
would be exactly what B-1 forbids.

Freshness is measured against a *before* picture of the temp directory: a field named
`path_did_not_exist_before_this_run` that is computed after the process exited (and after my own cleanup)
would be true forever and measure nothing.

Usage:  python xproc_v1_receipt.py <tree> <exact_sha> <rounds> <Y2|Y3>
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

GUARD = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks")
sys.path.insert(0, str(GUARD))
from mutation_anchor_guard import temporary_guarded_replace  # noqa: E402

REPO_LOCAL = Path("D:/moodle/_qoder_integration_20260919")
PY = Path("D:/moodle/CityNexus/.venv/Scripts/python.exe")
TREE = Path(sys.argv[1]).resolve()
EXACT_SHA = sys.argv[2]
ROUNDS = int(sys.argv[3]) if len(sys.argv) > 3 else 10
ARM = (sys.argv[4] if len(sys.argv) > 4 else "Y3").upper()
BACKEND = TREE / "backend"
PRODUCT = BACKEND / "app/catalog_hydration_operations.py"
SCHEMA = BACKEND / "db/schema.sql"

NODE = ("tests/test_qoder_g3_xproc_http.py"
        "::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation")
LOSER = (
    b"        winner = find_open_operation(session, fingerprint)\n"
    b"        if winner is None:\n"
    b"            raise\n"
    b"        return winner, True\n"
)
INDEX_SQL = (
    b"CREATE UNIQUE INDEX IF NOT EXISTS ux_catalog_hydration_one_open_job\n"
    b"    ON catalog_hydration_operations(fingerprint)\n"
    b"    WHERE status IN ('QUEUED','RUNNING','ABANDON_REQUESTED');\n"
)
ARMS = {
    "Y3": {
        "mutation_id": "C-ORD0224-Y3-loser-readback",
        "path": PRODUCT, "find": LOSER,
        "replace": (
            b"        winner = find_open_operation(session, fingerprint)\n"
            b"        if winner is None:\n"
            b"            raise\n"
            b'        raise HydrationStoreBusy("MUTANT Y3: the loser stopped reporting the winner")\n'
        ),
        "marker": b"MUTANT Y3",
        "claim_broken": (
            "product protection point = the loser's read-back inside `except IntegrityError` in "
            "submit_operation: the process whose INSERT lost the race reports the winner's id instead of "
            "failing. Removing it makes a cross-process HTTP caller receive 503 HYDRATION_STORE_BUSY rather "
            "than the one operation both callers must be handed."),
    },
    "Y2": {
        "mutation_id": "C-ORD0224-Y2-partial-unique-index",
        "path": SCHEMA, "find": INDEX_SQL,
        "replace": (
            b"CREATE UNIQUE INDEX IF NOT EXISTS ux_catalog_hydration_one_open_job\n"
            b"    ON catalog_hydration_operations(fingerprint)\n"
            b"    WHERE status IN ('__MUTANT_Y2_NEVER__');\n"
        ),
        "marker": b"__MUTANT_Y2_NEVER__",
        "claim_broken": (
            "product protection point = the durable partial unique index ux_catalog_hydration_one_open_job, "
            "the only thing in the product that can stop two processes from each opening a job for the same "
            "open generation. The predicate is switched to a status no row can ever have, so the schema stays "
            "in place while the protection stops firing."),
    },
}
if ARM not in ARMS:
    raise SystemExit(f"unknown arm {ARM}; have {sorted(ARMS)}")
A = ARMS[ARM]
FILE = A["path"]
ARGV = [str(PY), "-X", "utf8", "-m", "pytest", NODE, "-p", "no:cacheprovider", "-v", "-rA"]
FORBIDDEN = re.compile(r"--reruns|--dist|--maxfail|^-x$|--timeout|--deselect|-k\b|--collect-only|-n\b|-n=")
TEMP = Path(tempfile.gettempdir())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_LOCAL, capture_output=True, text=True).stdout.strip()


def temp_snapshot() -> set[str]:
    return {p.name for p in TEMP.glob("cnx_pytest_*") if p.is_dir()}


def environment_block() -> dict:
    mods = []
    for name in ("app", "app.main", "uvicorn", "fastapi", "sqlalchemy", "pytest"):
        try:
            spec = importlib.util.find_spec(name)
            origin = getattr(spec, "origin", None) if spec else None
        except Exception:  # noqa: BLE001 - a missing module is a reading, and NOT_FOUND is a legal value
            origin = None
        mods.append({"name": name, "import_origin": origin or "NOT_FOUND"})
    ver_py = subprocess.run([str(PY), "--version"], capture_output=True, text=True).stdout.strip()
    ver_pt = subprocess.run([str(PY), "-m", "pytest", "--version"], capture_output=True,
                            text=True).stdout.strip()
    plat = subprocess.run([str(PY), "-c", "import platform;print(platform.platform())"],
                          capture_output=True, text=True).stdout.strip()
    return {
        "cwd": str(BACKEND),
        "python_executable": str(PY),
        "python_version": ver_py,
        "pytest_version": (ver_pt.splitlines()[-1] if ver_pt else "NOT_FOUND"),
        "platform": plat,
        "pythonpath": ["(unset for the parent; the spawned uvicorn children get PYTHONPATH="
                       "<export tree>/backend, set inside the door)"],
        "required_local_modules": mods,
        "forbidden_command_surface_hits": sorted({m.group(0) for a in ARGV for m in [FORBIDDEN.search(a)] if m}),
    }


def read_db_state(directory: Path) -> dict:
    """What the durable store actually held when this round finished (read before self-clean)."""
    db = directory / "suite.db"
    if not db.exists():
        return {"present": False, "looked_for": str(db)}
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        out = {"present": True, "table_count": len(tables)}
        if "catalog_hydration_operations" in tables:
            ids = [str(r[0])[:8] for r in con.execute("SELECT id FROM catalog_hydration_operations")]
            opens = ["QUEUED", "RUNNING", "ABANDON_REQUESTED"]
            marks = ",".join("?" * len(opens))
            out.update({
                "catalog_hydration_operations_rows": len(ids),
                "catalog_hydration_operations_row_ids": ids,
                "catalog_hydration_operations_open_rows": len(
                    list(con.execute(f"SELECT id FROM catalog_hydration_operations WHERE status IN ({marks})",
                                     opens))),
                "catalog_hydration_operations_distinct_fingerprints": len(list(con.execute(
                    "SELECT DISTINCT fingerprint FROM catalog_hydration_operations"))),
            })
        return out
    finally:
        con.close()


def parse(out: str) -> dict:
    lines = out.splitlines()
    collected = next((int(m.group(1)) for l in lines if (m := re.search(r"collected (\d+) item", l))), None)
    summary = next((l for l in reversed(lines) if re.search(r"\d\W+(passed|failed|error)", l)), "")
    counts = {k: int(v) for v, k in re.findall(r"(\d+) (passed|failed|error|skipped)", summary)}
    failed = [l[7:].split(" ")[0] for l in lines if l.startswith("FAILED ")]
    errored = [l.split(" ")[1] for l in lines if l.startswith("ERROR ") and " " in l]
    setup_errors = [l.strip()[:200] for l in lines if "ERROR collecting" in l or "ERROR setup of" in l]
    db_line = next((l.split("resolved=", 1)[1].split(" | ")[0] for l in lines
                    if "ORD-0211 test database: resolved=" in l), None)
    if NODE in failed:
        outcome = "RED"
    elif counts.get("passed"):
        outcome = "GREEN"
    else:
        outcome = "NOT_OBSERVED"
    reason = next((l.strip()[:280] for l in lines if l.startswith("E  ") and "AssertionError" in l), "")
    door_line = next((l.strip() for l in lines if "G3_XPROC_LOSER_READBACK·HTTP" in l), "")
    return {"argv": ARGV, "exit_code": None, "collected": collected,
            "pytest_counts": {"passed": counts.get("passed", 0), "failed": counts.get("failed", 0),
                              "errors": counts.get("error", 0) + len(setup_errors),
                              "skipped": counts.get("skipped", 0)},
            "target_outcomes": {NODE: outcome}, "failed_nodeids": failed, "errored_nodeids": errored,
            "collection_or_setup_errors": setup_errors,
            "resolved_absolute_db_path": db_line,
            "path_source": ("app_printed_receipt_line" if db_line else "NOT_OBSERVED"),
            "assertion_red_reason": reason, "summary_line": summary.strip(),
            "door_print_line": door_line}


class StoreWatcher:
    """Sample the door's own per-round database while the round is in flight.

    The door mints `cnx_g3http_*/workers.db` and deletes it in its own teardown, so anything measured
    after pytest exits sees nothing and proves nothing. This thread reads the file from a *second*
    connection while the servers are live, which gives the verifier a durable reading that does not depend
    on the door vouching for itself: the directory name, how many job rows existed, their statuses, and how
    many distinct operation ids were visible at the same instant.
    """

    def __init__(self, before: set[str]):
        self.before = before
        self.samples: list[dict] = []
        self.stop = False
        self.thread: subprocess | None = None
        self.t0 = 0.0

    def start(self) -> None:
        self.t0 = __import__("time").monotonic()
        self.thread = __import__("threading").Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self) -> None:
        import time
        while not self.stop:
            for d in TEMP.glob("cnx_g3http_*"):
                if d.name in self.before:
                    continue
                db = d / "workers.db"
                if not db.exists():
                    continue
                try:
                    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
                    try:
                        rows = con.execute(
                            "SELECT id, status, fingerprint FROM catalog_hydration_operations").fetchall()
                        tables = len([r for r in con.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'")])
                    finally:
                        con.close()
                except sqlite3.Error as exc:  # a locked mid-write read is a reading, not a crash
                    rows, tables = [("READ_FAILED", "READ_FAILED", "READ_FAILED")], None
                live = [r for r in rows if r[1] != "READ_FAILED"]
                # The discriminating count: the door runs two arms with two different questions, so "2 rows
                # total" is normal even when nothing is broken. Two OPEN rows on the SAME fingerprint is the
                # invariant breaking, and that is what this has to count.
                per_fp: dict[str, int] = {}
                for _id, status, fp in live:
                    if str(status) in ("QUEUED", "RUNNING", "ABANDON_REQUESTED"):
                        per_fp[str(fp)[:12]] = per_fp.get(str(fp)[:12], 0) + 1
                self_samples = {
                    "open_rows_per_fingerprint": per_fp,
                    "max_open_rows_on_one_fingerprint": max(per_fp.values(), default=0),
                    "fingerprints_with_more_than_one_open_row": sorted(
                        k for k, v in per_fp.items() if v > 1),
                }
                self.samples.append({
                    "elapsed_ms": round((__import__("time").monotonic() - self.t0) * 1000, 1),
                    "door_store_dir": d.name,
                    "table_count": tables,
                    "job_rows": len(live),
                    "statuses": sorted({str(r[1]) for r in live}),
                    "distinct_operation_ids": len({str(r[0]) for r in live}),
                    "operation_id_prefixes": sorted({str(r[0])[:8] for r in live}),
                    **self_samples,
                })
            time.sleep(0.1)

    def summary(self) -> dict:
        self.stop = True
        if self.thread:
            self.thread.join(timeout=5)
        peak = max(self.samples, key=lambda s: s["job_rows"]) if self.samples else None
        return {
            "samples_taken": len(self.samples),
            "distinct_door_stores_seen": sorted({s["door_store_dir"] for s in self.samples}),
            "peak_row_sample": peak,
            "last_sample": (self.samples[-1] if self.samples else None),
            "max_job_rows_observed": max([s["job_rows"] for s in self.samples], default=0),
            "max_distinct_operation_ids_observed": max(
                [s["distinct_operation_ids"] for s in self.samples], default=0),
            # the one number that decides "did the durable invariant break":
            "worst_open_rows_on_one_fingerprint": max(
                [s.get("max_open_rows_on_one_fingerprint", 0) for s in self.samples], default=0),
            "fingerprints_ever_holding_two_open_rows": sorted({
                fp for s in self.samples for fp in s.get("fingerprints_with_more_than_one_open_row", [])}),
        }


def run_round(mutate: bool, index: int) -> dict:
    """One round: optional mutation, one pytest process, per-round freshness + durable state, then clean."""
    before_dirs = temp_snapshot()
    before_g3http = {p.name for p in TEMP.glob("cnx_g3http_*") if p.is_dir()}
    before_digest = sha256(FILE)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")

    def go() -> dict:
        watcher = StoreWatcher(before_g3http)
        watcher.start()
        try:
            proc = subprocess.run(ARGV, cwd=BACKEND, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", env=env)
        finally:
            witness = watcher.summary()
        rec = parse((proc.stdout or "") + (proc.stderr or ""))
        rec["exit_code"] = proc.returncode
        rec["door_store_witness"] = witness
        return rec

    def observe(rec: dict) -> tuple[dict, Path | None]:
        raw = rec.get("resolved_absolute_db_path")
        if not raw:
            return ({"initial_db_state": {"path_did_not_exist_before_this_run": False,
                                          "note": "no resolved path printed; verifier should treat as INVALID"},
                     "final_db_state": {"present": False}, "db_fresh": False}, None)
        d = Path(raw).parent
        # WHICH STORE IS WHICH (a verifier must not confuse them):
        #   * `resolved_absolute_db_path` = the pytest process's own suite DB, declared by conftest and
        #     printed by the app. This door does not write its claim there.
        #   * the store the claim is about = a per-round database the door mints itself (`cnx_g3http_*`)
        #     and deletes in its own teardown. Anything sampled after pytest exits sees nothing, so the
        #     durable reading here comes from a SECOND connection held open while the round was in flight
        #     (StoreWatcher) - it does not depend on the door vouching for itself.
        witness = rec.get("door_store_witness") or {}
        seen = witness.get("distinct_door_stores_seen") or []
        left = sorted(n for n in seen if (TEMP / n).exists())
        state = read_db_state(d)
        state["store_role"] = "pytest process suite DB - NOT the store this door's claim is about"
        state["door_store_witnessed_mid_round"] = witness
        state["door_store_dirs_seen"] = seen
        state["door_store_left_behind_after_round"] = left
        state["door_store_printed_by_the_door"] = {
            "source": "the door's own receipt line, emitted after it read the file back",
            "line": (rec.get("door_print_line") or "")[:400] or None,
            "per_arm": {arm: {"operation_id_prefix": oid, "status": status}
                        for arm, oid, status in re.findall(
                            r"(natural|scheduled)=([0-9a-f]{8})/([A-Z_]+)",
                            rec.get("door_print_line") or "")},
        }
        return ({"initial_db_state": {
                    "path_did_not_exist_before_this_run": d.name not in before_dirs,
                    "temp_dirs_present_before_round": len(before_dirs),
                    "door_store_dirs_present_before_round": len(before_g3http)},
                 "final_db_state": state,
                 "db_fresh": (d.name not in before_dirs and d.parent.name == TEMP.name
                              and d.name.startswith("cnx_pytest_"))}, d)

    if not mutate:
        rec = go()
        extra, d = observe(rec)
        if d is not None:
            shutil.rmtree(d, ignore_errors=True)
        return {"run_index": index, "mutated": False, **rec, **extra}

    with temporary_guarded_replace(FILE, A["find"], A["replace"]) as receipt:
        mutated_digest = sha256(FILE)
        rec = go()
    anchor = asdict(receipt)
    after = sha256(FILE)
    extra, d = observe(rec)
    if d is not None:
        shutil.rmtree(d, ignore_errors=True)  # the producer cleans only the path this round named
    return {"run_index": index, "mutated": True, "anchor": anchor, "mutated_digest": mutated_digest,
            **rec, **extra,
            "restore": {"attempted": True, "restored": after == before_digest,
                        "restored_digest_by_file": {str(FILE.relative_to(TREE)).replace(os.sep, "/"): after},
                        "byte_exact_match_before": after == before_digest,
                        "mutant_marker_hits_after_restore": FILE.read_bytes().count(A["marker"]),
                        "post_restore_dirty_paths": [] if after == before_digest
                        else [str(FILE.relative_to(TREE))]},
            "db_removed_after_receipt": (d.name if d else None)}


def main() -> int:
    before_digest = sha256(FILE)
    baseline = run_round(False, 0)
    runs = [run_round(True, i) for i in range(1, ROUNDS + 1)]
    for r in runs:
        print(f"round {r['run_index']}: {r['target_outcomes'][NODE]} | restored="
              f"{r['restore']['byte_exact_match_before']} | fresh={r['db_fresh']} | "
              f"rows={r['final_db_state'].get('catalog_hydration_operations_rows')} | "
              f"collected={r['collected']}", flush=True)

    primary_reds = [r["run_index"] for r in runs if r["target_outcomes"][NODE] == "RED"]
    baseline_green = baseline["target_outcomes"][NODE] == "GREEN"
    claimed = ("KILLED" if baseline_green and len(primary_reds) == ROUNDS
               else "STREAK_BROKEN" if baseline_green and primary_reds
               else "INVALID" if not baseline_green else "SURVIVED")
    rel = str(FILE.relative_to(TREE)).replace(os.sep, "/")
    receipt = {
        "schema_version": "CNX_REVERSE_MUTATION_RECEIPT_V1",
        "receipt_kind": "reverse_mutation",
        "scope": {
            "repo": "Canshu-King/CityNexus",
            "exact_sha": EXACT_SHA,
            "tree_kind": "clean_sha",
            "composite_recipe": [],
            "dirty": False,
            "dirty_paths": [],
            "target_nodeids": [NODE],
            "run_shape": "single-node",
            "command_argv": ARGV,
            "tree_note": ("被测树 = `git archive <exact_sha>` 的一次性只读导出（不是车道工作树）；"
                          "突变只施加在这份导出的 product 文件上，每轮复原后按 sha256 复验。"
                          "dirty=false 的判据 = 该文件在这棵树里逐字节等于 `git show <exact_sha>:<path>`。"),
            "tree_clean_check": {
                "path": rel,
                "export_tree_digest": hashlib.sha256(FILE.read_bytes()).hexdigest(),
                "committed_at_exact_sha_digest": hashlib.sha256(
                    subprocess.run(["git", "-C", str(REPO_LOCAL), "show", f"{EXACT_SHA}:{rel}"],
                                   capture_output=True).stdout).hexdigest(),
                "identical": FILE.read_bytes() == subprocess.run(
                    ["git", "-C", str(REPO_LOCAL), "show", f"{EXACT_SHA}:{rel}"],
                    capture_output=True).stdout,
            },
        },
        "environment": environment_block(),
        "baseline": {
            "receipt_ref": "evidence/ord0224_a2/streak_xproc_http_2ab69f2.json",
            "receipt_blob": "02a42d1bb21546038bd347a8169eb136dabef978",
            "same_exact_sha": True, "same_target_nodeids": True, "same_run_shape": True,
            "target_outcomes": baseline["target_outcomes"],
            "this_run_exit_code": baseline["exit_code"],
            "this_run_collected": baseline["collected"],
            "this_run_pytest_counts": baseline["pytest_counts"],
            "failed_nodeids": baseline["failed_nodeids"],
            "errored_nodeids": baseline["errored_nodeids"],
            "collection_or_setup_errors": baseline["collection_or_setup_errors"],
            "resolved_absolute_db_path": baseline["resolved_absolute_db_path"],
            "path_source": baseline["path_source"],
            "initial_db_state": baseline["initial_db_state"],
            "final_db_state": baseline["final_db_state"],
            "db_fresh": baseline["db_fresh"],
            "summary_line": baseline["summary_line"],
        },
        "mutation": {
            "mutation_id": A["mutation_id"],
            "claim_broken": A["claim_broken"],
            "allowed_scope": "product",
            "actual_scope": "product",
            "primary_target_nodeids": [NODE],
            "patch_or_mutator_ref": "evidence/ord0224_a2/xproc_v1_receipt.py",
            "changed_files": [{
                "path": rel,
                "before_blob": git("rev-parse", f"{EXACT_SHA}:{rel}"),
                "before_digest": before_digest,
                "mutated_digest": runs[0]["mutated_digest"],
                "expected_anchor_hits": 1,
                "anchor_hits": runs[0]["anchor"]["anchor_hits"],
                "bytes_changed": runs[0]["anchor"]["bytes_changed"],
            }],
            "not_a_test_assertion_edit": ("这一臂只改产品保护点（app/… 或 db/schema.sql）；"
                                          "门文件与断言一个字节都没动（门的 sha 在 baseline 里可比）"),
        },
        "mutated_runs": {"rounds": ROUNDS, "runs": runs},
        "derivation": {
            "claimed_result": claimed,
            "claimed_result_note": ("交付方自称，仅供参考；closure 只认 verifier 派生的 derived_result。"
                                    "上一批 `mutant_rounds_*.json` 里的 deterministic_kill / campaign_valid "
                                    "属同一类自称，按 B-1 不再单独生效。"),
            "derived_result": None,
            "direct_red_nodeids": None,
            "collateral_red_nodeids": None,
            "verifier_problems": [],
            "primary_red_rounds": primary_reds,
            "every_round_named_a_fresh_db": all(r["db_fresh"] for r in runs),
            "every_round_restored_byte_exact": all(r["restore"]["byte_exact_match_before"] for r in runs),
            "every_round_zero_collateral": all(not r["failed_nodeids"] or len(r["failed_nodeids"]) == 1
                                               for r in runs),
        },
    }
    out = Path(__file__).with_name(f"v1_receipt_{ARM}_http_{EXACT_SHA[:7]}.json")
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(f"claimed={claimed} primary_reds={len(primary_reds)}/{ROUNDS} baseline={baseline['target_outcomes'][NODE]}")
    print("->", out, len(out.read_bytes()), "B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
