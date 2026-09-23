"""V1 reverse-mutation receipts for the *in-process* corrected g3 door (ORD-0225's remaining arm).

The commander's order: "corrected g3 的产品侧反向突变 = 破坏部分唯一索引 + 败者回读，跑 ≥10 轮，
收据按 `CNX_REVERSE_MUTATION_RECEIPT_V1`". This emitter does that, and - because a kill rate is only
meaningful next to the carriers that actually exist - it also measures the neighbouring arms on the same
door, so whoever closes ORD-0225 reads a picture instead of one lucky number.

What the product actually has, in order of who can carry "five callers, one operation":

```text
A1 pre-resolution read   submit_operation asks the store before asking the world   (weak fix, 50d1c4d)
A2 post-resolution read  the original reuse check                                  (kept by disposition)
B  partial unique index  ux_catalog_hydration_one_open_job                         (durable)
C  loser read-back       except IntegrityError -> report the winner                (durable's recovery)
```

Arms measured here (each >=10 rounds, one round = one fresh process + one fresh database):
`Y23`  = B + C removed            (the ordered arm)
`Y123` = A1 + A2 + B + C removed  (no carrier left at all)

Both are **product** edits; no test file is touched, so `actual_scope=product` is literal. The row column
comes from the commander's own `gate_streak.row_counts()` (the version that reports `row_total` and
per-table counts), so the "0 -> N rows" claim is read with the same instrument the streak is judged with.

Usage:  python xproc_v1_gate_receipt.py <tree> <exact_sha> <rounds> <Y23|Y123>
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path

GUARD_DIR = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks")
sys.path.insert(0, str(GUARD_DIR))
from mutation_anchor_guard import temporary_guarded_replace  # noqa: E402

import gate_streak as RULER  # the commander's own尺; imported read-only, never edited here

RULER_SRC = GUARD_DIR / "gate_streak.py"

REPO_LOCAL = Path("D:/moodle/_qoder_integration_20260919")
PY = Path("D:/moodle/CityNexus/.venv/Scripts/python.exe")
TREE = Path(sys.argv[1]).resolve()
EXACT_SHA = sys.argv[2]
ROUNDS = int(sys.argv[3]) if len(sys.argv) > 3 else 10
ARM = (sys.argv[4] if len(sys.argv) > 4 else "Y23").upper()
# A batch tag, so repeated batches of the same arm are each published instead of overwriting each
# other - the spread between batches IS the finding for the in-process door.
TAG = (sys.argv[5] if len(sys.argv) > 5 else "a").strip().lower()
BACKEND = TREE / "backend"
PRODUCT = BACKEND / "app/catalog_hydration_operations.py"
SCHEMA = BACKEND / "db/schema.sql"

NODE = ("tests/test_qoder_anywhere_gates.py"
        "::test_g3_concurrent_open_generation_five_callers_share_one_operation")
PRE_READ = (
    b"    in_flight = find_open_operation(session, pending_request_fingerprint(query))\n"
    b"    if in_flight is not None and str(in_flight.status) in (QUEUED, RUNNING):\n"
    b"        return in_flight, True\n"
)
POST_READ = (
    b"    existing = find_open_operation(session, fingerprint)\n"
    b"    if existing is not None:\n"
    b"        return existing, True\n"
)
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


def _off(block: bytes, tag: bytes) -> bytes:
    """Disable a reuse read: keep its lookup line, replace the *condition* with `if False:`.

    The body line stays, so the mutant is one condition wide and nothing else moves - which is what keeps
    `anchor_hits == 1` and `bytes_changed` meaningful instead of a rewrite of the whole function.
    """
    lines = block.splitlines(keepends=True)
    if len(lines) < 3:
        raise SystemExit(f"anchor shape unexpected for {tag}: {lines!r}")
    return (lines[0] + b"    if False:  # MUTANT " + tag + b": this reuse check stops firing\n"
            + b"".join(lines[2:]))


LOSER_BROKEN = (b"        winner = find_open_operation(session, fingerprint)\n"
                b"        if winner is None:\n"
                b"            raise\n"
                b'        raise HydrationStoreBusy("MUTANT Y3: the loser stopped reporting the winner")\n')

ARMS = {
    # C alone: the arm that measured 3/10 at 2ab69f2 (pre-V1 artifact
    # xproc_y3_rounds_raw_test_g3_concurrent_open_ge_2ab69f2.json, git blob ee79303eb72a1704),
    # re-emitted here in CNX_REVERSE_MUTATION_RECEIPT_V1 shape because that file has no scope key
    # a verifier can read (lane F, 14:3x: "列了 evidence/ord0224 全 11 件确实拿不到 scope 键").
    "Y3": {
        "mutation_id": "C-ORD0224A2-Y3-loser-readback-only",
        "carriers_removed": ["C loser read-back"],
        "claim_broken": (
            "only the loser's read-back: the process that loses the race against the partial unique index "
            "now raises instead of reporting the winner. The index (B) and both reuse reads (A1/A2) stay "
            "live on purpose, so a green round here means some *other* carrier converged the five callers "
            "- which is exactly why this arm is not deterministic on the in-process door (3/10 at 2ab69f2)."),
        "edits": [
            {"path": PRODUCT, "find": LOSER, "marker": b"MUTANT Y3", "replace": LOSER_BROKEN},
        ],
    },
    # the ordered arm: the two durable carriers
    "Y23": {
        "mutation_id": "C-ORD0225-Y23-index-and-loser-readback",
        "carriers_removed": ["B partial unique index", "C loser read-back"],
        "claim_broken": (
            "the durable half of 'one open generation, one job': the partial unique index cannot reject a "
            "second open row (its predicate names a status no row can hold) and the process that would "
            "have lost the race no longer reports the winner. A1/A2 reads stay live on purpose, so this "
            "is exactly '破坏部分唯一索引 + 败者回读' and not a wider change."),
        "edits": [
            {"path": SCHEMA, "find": INDEX_SQL, "marker": b"__MUTANT_Y2_NEVER__",
             "replace": b"CREATE UNIQUE INDEX IF NOT EXISTS ux_catalog_hydration_one_open_job\n"
                        b"    ON catalog_hydration_operations(fingerprint)\n"
                        b"    WHERE status IN ('__MUTANT_Y2_NEVER__');\n"},
            {"path": PRODUCT, "find": LOSER, "marker": b"MUTANT Y3",
             "replace": b"        winner = find_open_operation(session, fingerprint)\n"
                        b"        if winner is None:\n"
                        b"            raise\n"
                        b'        raise HydrationStoreBusy("MUTANT Y3: the loser stopped reporting the winner")\n'},
        ],
    },
    # the neighbour that tells the verifier why Y23 may still be green: all four carriers
    "Y123": {
        "mutation_id": "C-ORD0225-Y123-all-four-carriers",
        "carriers_removed": ["A1 pre-resolution read", "A2 post-resolution read",
                             "B partial unique index", "C loser read-back"],
        "claim_broken": (
            "every mechanism that can hand five concurrent callers one job: both reuse reads, the partial "
            "unique index and the loser's read-back. If this arm is not deterministic either, the door is "
            "not measuring what it claims."),
        "edits": [
            {"path": PRODUCT, "find": PRE_READ, "marker": b"MUTANT Y1a", "replace": _off(PRE_READ, b"Y1a")},
            {"path": PRODUCT, "find": POST_READ, "marker": b"MUTANT Y1b", "replace": _off(POST_READ, b"Y1b")},
            {"path": SCHEMA, "find": INDEX_SQL, "marker": b"__MUTANT_Y2_NEVER__",
             "replace": b"CREATE UNIQUE INDEX IF NOT EXISTS ux_catalog_hydration_one_open_job\n"
                        b"    ON catalog_hydration_operations(fingerprint)\n"
                        b"    WHERE status IN ('__MUTANT_Y2_NEVER__');\n"},
            {"path": PRODUCT, "find": LOSER, "marker": b"MUTANT Y3",
             "replace": b"        winner = find_open_operation(session, fingerprint)\n"
                        b"        if winner is None:\n"
                        b"            raise\n"
                        b'        raise HydrationStoreBusy("MUTANT Y3: the loser stopped reporting the winner")\n'},
        ],
    },
}
def _arm_with_read_off(name: bytes, tag: str, which: str) -> dict:
    """Y23 plus one reuse read switched off, so the *surviving* read is the one being tested."""
    block = PRE_READ if which == "A1" else POST_READ
    return {
        "mutation_id": f"C-ORD0225-Y23-{which}-off",
        "carriers_removed": [f"{which} reuse read", "B partial unique index", "C loser read-back"],
        "claim_broken": (
            f"the ordered arm plus the {which} reuse read: whatever still converges the five callers here "
            f"is the mechanism left standing when both durable carriers and {which} are gone."),
        "edits": [{"path": PRODUCT, "find": block, "marker": b"MUTANT " + name,
                   "replace": _off(block, name)}] + ARMS["Y23"]["edits"],
    }


ARMS["Y23_OFF_A1"] = _arm_with_read_off(b"Y1a", "Y23_OFF_A1", "A1")
ARMS["Y23_OFF_A2"] = _arm_with_read_off(b"Y1b", "Y23_OFF_A2", "A2")

if ARM not in ARMS:
    raise SystemExit(f"unknown arm {ARM}; have {sorted(ARMS)}")
A = ARMS[ARM]
# Where this run's artifacts go, so every self-reference in the receipt names a path a verifier can open.
PUBLISH_PREFIX = "evidence/ord0224_a2" if EXACT_SHA.startswith("2ab69f2") else "evidence/ord0225"
# Earlier artifacts carrying the *same scope key* (same exact sha + same nodeid + same run_shape).
# Naming them is what turns "another batch" into a repeat instead of a fresh number to admire.
PRIOR_MEASUREMENTS = {
    ("Y3", "2ab69f2"): {
        "file": "evidence/ord0224_a2/xproc_y3_rounds_raw_test_g3_concurrent_open_ge_2ab69f2.json",
        "git_blob_sha1": "ee79303eb72a1704",
        "bytes": 9245,
        "shape": "pre-V1 (the reason this file exists: lane F read evidence/ord0224's 11 files at 14:3x "
                 "and could not recover a scope key from it)",
        "rounds": 10, "killed": 3, "control": "GREEN",
        "same_exact_sha": True, "same_target_nodeids": True, "same_run_shape": True,
        "field_correction": ("那份旧文件的 verdict 里 campaign_valid=false 与 deterministic_kill=false 是同一个条件写的："
                            "旧仪器把'这批证据有效'与'击杀是确定性的'混成一格。V1 里两格分开记 - 控制轮绿 + 还原逐字节 +"
                            "锚点 1 命中 ⇒ 证据有效；3/10 ⇒ 击杀不确定，这是**关于突变体的结论**，不是关于仪器的。"),
    },
}
PRIOR = PRIOR_MEASUREMENTS.get((ARM, EXACT_SHA[:7]))
ARGV = [str(PY), "-X", "utf8", "-m", "pytest", NODE, "-p", "no:cacheprovider", "-v", "-rA"]
FORBIDDEN = re.compile(r"--reruns|--dist|--maxfail|^-x$|--timeout|--deselect|-k\b|--collect-only|-n\b|-n=")
TEMP = Path(tempfile.gettempdir())


def _rel(path: Path) -> str:
    return str(path.relative_to(TREE)).replace(os.sep, "/")


def _rev_blob(rel: str) -> str:
    out = subprocess.run(["git", "-C", str(REPO_LOCAL), "rev-parse", f"{EXACT_SHA}:{rel}"],
                         capture_output=True, text=True)
    blob = out.stdout.strip()
    if out.returncode != 0 or len(blob) != 40:
        raise SystemExit(f"rev-parse failed for {rel}: {out.stderr.strip()[:120]}")
    return blob


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def committed(sha: str, rel: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO_LOCAL), "show", f"{sha}:{rel}"],
                          capture_output=True).stdout


def environment_block() -> dict:
    mods = []
    for name in ("app", "app.main", "fastapi", "sqlalchemy", "pytest"):
        try:
            spec = importlib.util.find_spec(name)
            origin = getattr(spec, "origin", None) if spec else None
        except Exception:  # noqa: BLE001
            origin = None
        mods.append({"name": name, "import_origin": origin or "NOT_FOUND"})
    return {
        "cwd": str(BACKEND),
        "python_executable": str(PY),
        "python_version": subprocess.run([str(PY), "--version"], capture_output=True, text=True).stdout.strip(),
        "pytest_version": subprocess.run([str(PY), "-m", "pytest", "--version"],
                                          capture_output=True, text=True).stdout.strip().splitlines()[-1],
        "platform": subprocess.run([str(PY), "-c", "import platform;print(platform.platform())"],
                                    capture_output=True, text=True).stdout.strip(),
        "pythonpath": ["(unset for the pytest process; this door runs in-process, no child interpreter)"],
        "required_local_modules": mods,
        "forbidden_command_surface_hits": sorted({m.group(0) for a in ARGV for m in [FORBIDDEN.search(a)] if m}),
        "row_column_instrument": {
            "module": str(RULER.__file__),
            "git_blob_sha1": hashlib.sha1(b"blob %d\x00" % RULER_SRC.stat().st_size
                                          + RULER_SRC.read_bytes()).hexdigest(),
            "commander_announced_prefix": "ac5377f207f18334",
            "function": "row_counts (the version reporting row_total + per-table counts)",
            "note": "行读数出自判级那把尺本身，不是我另写一份 SQL；两个摘要对得上才是同一把尺",
        },
    }


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
    reason = next((l.strip()[:300] for l in lines if l.startswith("E  ") and "AssertionError" in l), "")
    outcome = "RED" if NODE in failed else ("GREEN" if counts.get("passed") else "NOT_OBSERVED")
    return {"argv": ARGV, "collected": collected,
            "pytest_counts": {"passed": counts.get("passed", 0), "failed": counts.get("failed", 0),
                              "errors": counts.get("error", 0) + len(setup_errors),
                              "skipped": counts.get("skipped", 0)},
            "target_outcomes": {NODE: outcome}, "failed_nodeids": failed, "errored_nodeids": errored,
            "collection_or_setup_errors": setup_errors,
            "resolved_absolute_db_path": db_line,
            "path_source": "app_printed_receipt_line" if db_line else "NOT_OBSERVED",
            "assertion_red_reason": reason, "summary_line": summary.strip()}


BEFORE_DIGESTS: dict[str, str] = {}


def run_round(mutate: bool, index: int) -> dict:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    before_dirs = {p.name for p in TEMP.glob("cnx_pytest_*") if p.is_dir()}
    files = [e["path"] for e in A["edits"]]
    for f in files:  # refuse to emit a receipt over a tree that is not the commit it claims
        if sha256(f) != hashlib.sha256(committed(EXACT_SHA, _rel(f))).hexdigest():
            raise SystemExit(f"tree mismatch: {_rel(f)} in the export is not the bytes at {EXACT_SHA[:7]}")
    anchors = []
    mutated_digests = {}
    with ExitStack() as stack:
        if mutate:
            for e in A["edits"]:
                receipt = stack.enter_context(
                    temporary_guarded_replace(e["path"], e["find"], e["replace"]))
                # keyed by EDIT INDEX: three of Y123's four edits hit the same file, and matching a
                # receipt back by path suffix would hand the same digest to all three - a wrong
                # digest in a receipt is worse than a missing one.
                anchors.append({"edit_index": len(anchors), **asdict(receipt)})
                mutated_digests[str(len(anchors) - 1)] = sha256(e["path"])  # keyed by edit index
        proc = subprocess.run(ARGV, cwd=BACKEND, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=env)
    rec = parse((proc.stdout or "") + (proc.stderr or ""))
    rec["exit_code"] = proc.returncode
    raw = rec.get("resolved_absolute_db_path")
    d = Path(raw).parent if raw else None
    fresh = bool(d) and d.name not in before_dirs and d.name.startswith("cnx_pytest_")
    rows = RULER.row_counts(str(d / "suite.db")) if d else {"absent": True}
    rec["initial_db_state"] = {"path_did_not_exist_before_this_run": fresh,
                               "temp_dirs_present_before_round": len(before_dirs)}
    rec["final_db_state"] = {"rows_by_table": rows,
                             "store_role": "this door runs in-process, so the claim's store IS the suite DB",
                             "catalog_rows": ((rows.get("nonempty_tables") or {})
                                              .get("catalog_hydration_operations", 0))}
    rec["db_fresh"] = fresh
    after_digests = {_rel(f): sha256(f) for f in files}
    rec["restore"] = {
        "attempted": mutate, "restored": all(after_digests[k] == BEFORE_DIGESTS[k] for k in after_digests),
        "restored_digest_by_file": after_digests,
        "byte_exact_match_before": all(after_digests[k] == BEFORE_DIGESTS[k] for k in after_digests),
        "mutant_marker_hits_after_restore": sum(
            e["path"].read_bytes().count(e["marker"]) for e in A["edits"]),
        "post_restore_dirty_paths": [k for k in after_digests if after_digests[k] != BEFORE_DIGESTS[k]],
    }
    if d and fresh:
        shutil.rmtree(d, ignore_errors=True)  # the producer cleans only the path this round named
    return {"run_index": index, "mutated": mutate, "anchor_receipts": anchors,
            "mutated_digest_by_file": mutated_digests, **rec}


def _norm(path: str) -> str:
    return path.replace(os.sep, "/")


def _changed_files(runs: list[dict]) -> list[dict]:
    """One entry per edit, in the order the guard applied them.

    Y123 edits the same file three times, so an edit's own receipt - not a path lookup - is the only
    correct source for its mutated digest. The digest is cumulative (the state after that edit), which
    is stated in `digest_semantics` so nobody reads three rows as three independent file versions.
    """
    first = runs[0]["anchor_receipts"] if runs else []
    by_index = {a.get("edit_index"): a for a in first}
    out = []
    for i, e in enumerate(A["edits"]):
        rel = _rel(e["path"])
        hit = by_index.get(i, {})
        out.append({
            "path": _norm(rel),
            "before_blob": _rev_blob(rel),
            "before_digest": BEFORE_DIGESTS[rel],
            "mutated_digest": hit.get("mutated_sha256"),
            "expected_anchor_hits": 1,
            "anchor_hits": hit.get("anchor_hits"),
            "bytes_changed": hit.get("bytes_changed"),
        })
    return out


def main() -> int:
    global BEFORE_DIGESTS
    BEFORE_DIGESTS = {_rel(e["path"]): sha256(e["path"]) for e in A["edits"]}
    files = [e["path"] for e in A["edits"]]
    for f in files:  # refuse to emit a receipt over a tree that is not the commit it claims
        if sha256(f) != hashlib.sha256(committed(EXACT_SHA, _rel(f))).hexdigest():
            raise SystemExit(f"tree mismatch: {_rel(f)} in the export is not the bytes at {EXACT_SHA[:7]}")
    baseline = run_round(False, 0)
    runs = [run_round(True, i) for i in range(1, ROUNDS + 1)]
    for r in runs:
        print(f"round {r['run_index']}: {r['target_outcomes'][NODE]} | restored="
              f"{r['restore']['byte_exact_match_before']} | fresh={r['db_fresh']} | "
              f"catalog_rows={r['final_db_state']['catalog_rows']} | row_total="
              f"{r['final_db_state']['rows_by_table'].get('row_total')}", flush=True)
    primary_reds = [r["run_index"] for r in runs if r["target_outcomes"][NODE] == "RED"]
    baseline_green = baseline["target_outcomes"][NODE] == "GREEN"
    claimed = ("KILLED" if baseline_green and len(primary_reds) == ROUNDS
               else "STREAK_BROKEN" if baseline_green and primary_reds
               else "INVALID" if not baseline_green else "SURVIVED")
    receipt = {
        "schema_version": "CNX_REVERSE_MUTATION_RECEIPT_V1",
        "receipt_kind": "reverse_mutation",
        "scope": {
            "repo": "Canshu-King/CityNexus", "exact_sha": EXACT_SHA, "tree_kind": "clean_sha",
            "composite_recipe": [], "dirty": False, "dirty_paths": [],
            "target_nodeids": [NODE], "run_shape": "single-node", "command_argv": ARGV,
            "tree_kind_check": {
                str(f.relative_to(TREE)).replace(os.sep, "/"): {
                    "export_tree_digest": sha256(f),
                    "committed_at_exact_sha_digest": hashlib.sha256(committed(EXACT_SHA, _rel(f))).hexdigest(),
                    "identical": sha256(f) == hashlib.sha256(committed(EXACT_SHA, _rel(f))).hexdigest(),
                } for f in files},
            "note": ("被测树 = `git archive <exact_sha>` 的一次性只读导出；两把文件的 export 摘要与 "
                     "`git show <exact_sha>:<path>` 摘要逐一对齐才算 clean_sha"),
        },
        "environment": environment_block(),
        "baseline": {
            "receipt_ref": (f"{PUBLISH_PREFIX}/ 本批控制轮（同一棵被测树、同一条 nodeid、同一个 run_shape）"
                            + ("；同键旧件见 provenance.prior_measurement_same_scope_key" if PRIOR else "")),
            "receipt_blob": "本文件即 baseline + 10 轮，不需要外部收据才读得懂",
            "same_exact_sha": True,
            "same_exact_sha_note": ("baseline = 本批在同一棵导出树上的控制轮，同 sha / 同 nodeid / 同 run_shape。"
                                    "别人不同的 baseline（如 lane F 第 1 步在 composite `ec65a3e` 上的读数）是**另一个 scope 键**，"
                                    "两边不互换，按仲裁 A-5。"),
            "same_target_nodeids": True, "same_run_shape": True,
            "target_outcomes": baseline["target_outcomes"],
            "this_run_exit_code": baseline["exit_code"], "this_run_collected": baseline["collected"],
            "this_run_pytest_counts": baseline["pytest_counts"],
            "failed_nodeids": baseline["failed_nodeids"], "errored_nodeids": baseline["errored_nodeids"],
            "collection_or_setup_errors": baseline["collection_or_setup_errors"],
            "resolved_absolute_db_path": baseline["resolved_absolute_db_path"],
            "path_source": baseline["path_source"],
            "initial_db_state": baseline["initial_db_state"], "final_db_state": baseline["final_db_state"],
            "db_fresh": baseline["db_fresh"], "summary_line": baseline["summary_line"],
        },
        "mutation": {
            "mutation_id": A["mutation_id"], "claim_broken": A["claim_broken"],
            "carriers_removed": A["carriers_removed"],
            "allowed_scope": "product", "actual_scope": "product",
            "primary_target_nodeids": [NODE],
            "patch_or_mutator_ref": (f"{PUBLISH_PREFIX}/xproc_v1_gate_receipt.py"
                                     "（字节由 provenance.emitter_git_blob_sha1_this_file 钉住，不是靠文件名）"),
            "no_test_file_touched": "两把（或四把）改动全在 app/ 与 db/schema.sql；门与断言 0 字节",
            "changed_files": _changed_files(runs),
            "digest_semantics": ("一条 edit 一行；同文件多条 edit 的 mutated_digest 是**累计态**（该 edit 之后文件的形状），"
                                 "不是三个独立版本。anchor_hits 每行都必须是 1，由守卫自己数。"),
        },
        "mutated_runs": {"rounds": ROUNDS, "runs": runs},
        "provenance": {
            "prior_measurement_same_scope_key": PRIOR or {
                "absent": True,
                "note": ("本 (arm, exact_sha) 组合之前没有出过同键读数；这一格显式写 absent，"
                         "是为了让 verifier 不必去猜'没有'是漏填还是真的没有。"),
            },
            "publish_prefix": PUBLISH_PREFIX,
            "emitter_git_blob_sha1_this_file": hashlib.sha1(
                b"blob %d\x00" % Path(__file__).stat().st_size + Path(__file__).read_bytes()).hexdigest(),
            "emitter_blob_semantics": ("出这枚收据那一刻本文件的 git blob sha1（自己按字节算，不是抄来的坐标）；"
                                       "发布步骤要重算一次并核对，不一致就说明收据不再描述那台仪器。"),
        },
        "derivation": {
            "claimed_result": claimed,
            "claimed_result_note": "交付方自称；closure 只认 verifier 派生的 derived_result。",
            "derived_result": None, "direct_red_nodeids": None, "collateral_red_nodeids": None,
            "verifier_problems": [],
            "batch_tag": TAG,
            "primary_red_rounds": primary_reds,
            "every_round_named_a_fresh_db": all(r["db_fresh"] for r in runs),
            "every_round_restored_byte_exact": all(r["restore"]["byte_exact_match_before"] for r in runs),
            "baseline_catalog_rows": baseline["final_db_state"]["catalog_rows"],
            "mutated_catalog_rows": [r["final_db_state"]["catalog_rows"] for r in runs],
        },
    }
    out = Path(__file__).with_name(f"v1_gate_receipt_{ARM}_{TAG}_{EXACT_SHA[:7]}.json")
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(f"arm={ARM} claimed={claimed} primary_reds={len(primary_reds)}/{ROUNDS} "
          f"baseline={baseline['target_outcomes'][NODE]} "
          f"rows base={baseline['final_db_state']['catalog_rows']} mut={[r['final_db_state']['catalog_rows'] for r in runs]}")
    print("->", out, len(out.read_bytes()), "B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
