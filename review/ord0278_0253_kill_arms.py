"""ORD-0278 / ORD-0253 acceptance: the named reverse mutations, one owning node each.

Each arm is the shape of the defect the order forbids:

  K278_NO_MISSION_ID_IN_BODY   the resumed batch stops saying whose it is -> the positive node
  K278_TWO_KEYS_MERGED         the transport header is filled with the mission id, i.e. one name
                               standing in for two keys -> the positive node
  K278_CLEAR_BEFORE_SEND       the record is erased ahead of the send -> ORD-0269 cell 1 (clause 5)
  K278_SILENCE_ON_NON_ACCEPT   a refusal / timeout / dead transport paints no outcome and erases the
                               record anyway -> the refused negative node
  K253_LEG2_KEY_DROPPED        the leg the server actually reads carries no key -> all three 0253
                               nodes (this is the pre-fix shape, put back on purpose)
  K253_KEY_PER_FETCH           the key is minted at each fetch instead of once per intent, so the
                               two legs of one press disagree -> the 0253 positive node

Nodes are keyed by their FULL test id, and verdicts are parsed from the run log the runner writes,
not from its truncated console echo.  claimed_result is self-reported; derived_result belongs to the
verifier.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from hashlib import sha256
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
sys.path.insert(0, str(Path("D:/moodle/_qoder_integration_20260919/live_checks")))
from mutation_anchor_guard import temporary_guarded_replace  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

MODULE = ROOT / "frontend/src/api/journeyContinuation.ts"
V8 = ROOT / "frontend/src/app/V8Experience.tsx"
SHEET = ROOT / "frontend/src/features/planning/PlanWithAiSheet.tsx"
SPEC_278 = "e2e/qoder-continuation-resume-carries-identity.spec.ts"
SPEC_269 = "e2e/qoder-continuation-owner.spec.ts"
SPEC_253 = "e2e/qoder-sheet-legs-carry-idempotency-key.spec.ts"
PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
RECEIPT_DIR = ROOT / "review/evidence/ui-overnight"
FILES = [MODULE, V8, SHEET]

POS = "ord0278-positive-the-resume-request-carries-both-keys"
REFUSED = "ord0278-negative-refused-keeps-the-marker-and-says-whose-words-these-are"
CELL1 = "ord0269-cell1-reveals-and-names-its-boundary"
BOTH_LEGS = "ord0253-both-legs-of-one-intent-share-one-key"
FRESH = "ord0253-each-intent-mints-a-fresh-key"
BURST = "ord0253-a-burst-consumes-no-key"

BODY_LINE = '      body: JSON.stringify({ candidate_count: 3, mission_id: args.missionId }),'
HEADER_LINE = '        "Idempotency-Key": args.idempotencyKey,'
CLEAR_LINE = "    if (outcome.kind === \"accepted\") clearPendingContinuation(data.journey.id);"
SET_OUTCOME_LINE = "    setResumeOutcome(outcome);"
LEG2_HEADERS = (
    "              headers: {\n"
    "                \"Content-Type\": \"application/json\",\n"
    "                Accept: \"application/json\",\n"
    "                \"Idempotency-Key\": idempotencyKey,\n"
    "              },\n"
    "              body: JSON.stringify({ candidate_count: 3 }),"
)
MINT_LINE = "    const idempotencyKey = crypto.randomUUID();"
LEG1_HEADERS = (
    "        headers: {\n"
    "          \"Content-Type\": \"application/json\",\n"
    "          Accept: \"application/json\",\n"
    "          \"Idempotency-Key\": idempotencyKey,\n"
    "        },\n"
    "        body: JSON.stringify({ command }),"
)

ARMS = [
    (
        "K278_NO_MISSION_ID_IN_BODY",
        POS,
        SPEC_278,
        MODULE,
        BODY_LINE,
        "      body: JSON.stringify({ candidate_count: 3 }),",
        "the resumed batch no longer says whose it is: the server can replay it but cannot bind it to "
        "the interrupted round, which is the half this order was opened for",
    ),
    (
        "K278_TWO_KEYS_MERGED",
        POS,
        SPEC_278,
        MODULE,
        HEADER_LINE,
        "        \"Idempotency-Key\": args.missionId,",
        "the ruling's 'two keys, never merged' violated in the direction that looks harmless: one "
        "name standing in for both, so 'same mission, different request' and 'same request, resent' "
        "collapse in storage",
    ),
    (
        "K278_CLEAR_BEFORE_SEND",
        CELL1,
        SPEC_269,
        V8,
        "    setResumeOutcome(null);\n    const outcome = await continuePendingPlan({",
        "    setResumeOutcome(null);\n    clearPendingContinuation(data.journey.id);\n"
        "    const outcome = await continuePendingPlan({",
        "clause 5's forbidden shape -- the record is erased AHEAD of the send, so a run interrupted "
        "after this press is unfindable again. (v1 measured this arm with a different edit: moving "
        "the post-await clear out of its condition still erased after the send, which is a different "
        "defect and cell 1 correctly ignored it. That mutant was wrong, not the gate.)",
    ),
    (
        "K278_SILENCE_ON_NON_ACCEPT",
        REFUSED,
        SPEC_278,
        V8,
        SET_OUTCOME_LINE,
        "    if (outcome.kind === \"accepted\") setResumeOutcome(outcome);",
        "a refusal, timeout or dead transport paints no word and leaves the card standing -- the "
        "'never silence' half of the reveal",
    ),
    (
        "K253_LEG2_KEY_DROPPED",
        BOTH_LEGS,
        SPEC_253,
        SHEET,
        LEG2_HEADERS,
        "              headers: { \"Content-Type\": \"application/json\" },\n"
        "              body: JSON.stringify({ candidate_count: 3 }),",
        "the pre-fix shape: the leg the server actually reads arrives with no identity, so the "
        "receipt machinery never sees the phone's own press",
    ),
    (
        "K253_LEG1_KEY_DROPPED",
        BOTH_LEGS,
        SPEC_253,
        SHEET,
        LEG1_HEADERS,
        "        headers: { \"Content-Type\": \"application/json\", Accept: \"application/json\" },\n"
        "        body: JSON.stringify({ command }),",
        "only one leg of one press carries the identity, so the two disagree about whose send this "
        "is -- 'one intent, one key' broken across the legs rather than dropped from both",
    ),
    (
        "K253_ONE_KEY_FOR_ALL_INTENTS",
        FRESH,
        SPEC_253,
        SHEET,
        MINT_LINE,
        "    const idempotencyKey = \"ord0253-static-transport-key\";",
        "the key stops being per intent and becomes a per-session constant: both legs still agree, "
        "so only the second-press node can see it -- which is what that node exists for",
    ),
]

NODE_RE = re.compile(r"^\s*(ok|x|✘|failed|-)\s+\d+\s+\[[^\]]+\]\s+›\s+\S+\s+›\s+(.+?)(?:\s+\([\d.]+[ms]+\))?\s*$")
EXPECTED = {SPEC_278: [POS, REFUSED], SPEC_269: [CELL1], SPEC_253: [BOTH_LEGS, FRESH, BURST]}


def digests() -> dict[str, str]:
    return {p.name: sha256(p.read_bytes()).hexdigest() for p in FILES}


def port_busy(port: int) -> bool:
    out = subprocess.run(
        "netstat -ano -p tcp", capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True
    ).stdout
    return any(f":{port} " in line and "LISTENING" in line for line in out.splitlines())


def run(label: str, port: int, spec: str) -> dict:
    env = dict(os.environ)
    env["CNX_LANE_ROOT"] = str(ROOT)
    started = time.time()
    proc = subprocess.run(
        [PYTHON, str(ROOT / "review/run_spec.py"), spec, str(port)],
        cwd=str(ROOT), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = proc.stdout + proc.stderr
    run_id = next((l.split("run_id=", 1)[1].split()[0] for l in out.splitlines() if l.startswith("run_id=")), "")
    # The runner's id is `run293283`; the throwaway database it created is `_run293283.db`.  Naming a
    # file that does not exist is a wrong coordinate, so build the name and then look for it.
    db_name = f"_run{run_id[3:]}.db" if run_id.startswith("run") else "?"
    db_seen = (RECEIPT_DIR.parent / db_name).exists()
    log_path = ROOT / f"review/run-{run_id}.log"
    text = log_path.read_text(encoding="utf-8", errors="replace") if run_id and log_path.exists() else out
    nodes: dict[str, str] = {}
    for line in text.splitlines():
        m = NODE_RE.match(line)
        if not m:
            continue
        token, title = m.group(1), m.group(2).split(" — ")[0].strip()
        if not title.startswith("ord02"):
            continue
        nodes[title] = {"ok": "GREEN"}.get(token, "RED")
    tallies = [l.strip() for l in text.splitlines() if re.match(r"^\s*\d+ (passed|failed|flaky)", l)]
    missing = [n for s, ns in EXPECTED.items() if s == spec for n in ns if n not in nodes]
    print(
        f"[{label}] exit={proc.returncode} run={run_id} {round(time.time() - started)}s "
        f"{' / '.join(tallies)!r} " + " ".join(f"{k.split('-')[1][:9]}:{v}" for k, v in sorted(nodes.items())),
        flush=True,
    )
    return {
        "label": label, "spec": spec, "exitCode": proc.returncode, "runId": run_id, "port": port,
        "log": log_path.name if run_id and log_path.exists() else "", "tallies": tallies,
        "db": db_name, "db_exists": db_seen,
        # A stack that finished a spec but whose named throwaway database is not on disk did not run
        # on the database the run_shape claims -- that reading is refused, not graded.
        "stackStarted": bool(tallies) and not missing and db_seen, "missingNodes": missing, "nodes": nodes,
    }


def rel_to_root(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def git_text(cmd: str) -> str:
    return subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace"
    ).stdout


def git_bytes(arg: str) -> bytes:
    return subprocess.run(arg, cwd=str(ROOT), capture_output=True, shell=True).stdout


def frontend_blob_map(rev: str) -> dict:
    """Every tracked file under `frontend/` in `rev`, as path -> git blob id."""
    out = {}
    for line in git_text(f"git ls-tree -r {rev} -- frontend").splitlines():
        meta, path = line.split("\t", 1)
        out[path] = meta.split()[2]
    return out


def sha256_at(rev: str, path: str) -> str:
    raw = git_bytes(f"git cat-file blob {rev}:{path}")
    return sha256(raw).hexdigest()


def numstat(a: str, b: str, path: str) -> str:
    line = git_text(f"git diff --numstat {a} {b} -- {path}").strip()
    return line or "0\t0\t(no diff)"


def generation_compare(frozen: str, landed: str, tested: str) -> dict:
    """The per-file table a re-parent owes: this tip against the tree it was cut from, and against
    the landed tip it was cut onto.  A whole-tree digest covers the files that did NOT change, so
    'only these moved' is a measurement, not an impression."""
    maps = {rev: frontend_blob_map(rev) for rev in (frozen, landed, tested)}
    paths = sorted(set().union(*[set(m) for m in maps.values()]))
    differing = [
        p for p in paths
        if len({maps[rev].get(p, "ABSENT") for rev in (frozen, landed, tested)}) > 1
    ]
    rows = []
    for p in differing:
        rows.append({
            "path": p,
            "sha256_at_frozen_tree": sha256_at(frozen, p) if p in maps[frozen] else "ABSENT",
            "sha256_at_landed_tip": sha256_at(landed, p) if p in maps[landed] else "ABSENT",
            "sha256_under_test": sha256_at(tested, p),
            "equals_frozen_tree": maps[frozen].get(p) == maps[tested].get(p),
            "equals_landed_tip": maps[landed].get(p) == maps[tested].get(p),
            "lines_vs_landed_tip": numstat(landed, tested, p),
            "lines_vs_frozen_tree": numstat(frozen, tested, p),
        })
    return {
        "frozen_tree": frozen,
        "landed_tip": landed,
        "tested_tree": tested,
        "frontend_tree_object": {rev: git_text(f"git rev-parse {rev}:frontend").strip() for rev in (frozen, landed, tested)},
        "frontend_files_tracked": {rev: len(maps[rev]) for rev in (frozen, landed, tested)},
        "files_differing_across_the_three": len(differing),
        "files_equal_to_frozen_tree": sum(1 for r in rows if r["equals_frozen_tree"]) + (
            len(paths) - len(differing)
        ),
        "identical_under_test": [r["path"] for r in rows if not r["equals_frozen_tree"]],
        "rows": rows,
        "reading": "the frontend/** files listed in `identical_under_test` are the ones this tip does NOT "
        "carry byte-for-byte from the frozen tree; for each, `lines_vs_landed_tip` is what this lane re-added "
        "and `lines_vs_frozen_tree` is what the landed line added underneath it. Every other tracked frontend "
        "file has the same git blob id in all three trees, which is what the counts assert.",
    }


def committed_digests(rev: str) -> dict:
    """sha256 of each mutated file AS COMMITTED in `rev`, read straight out of the object store.

    The round's own restore check (working bytes == bytes before the mutation) cannot see a working
    tree that drifted from the candidate; this can, and it is what lets the receipt say the kills
    are evidence about `rev`."""
    out = {}
    for p in FILES:
        proc = subprocess.run(
            f"git cat-file blob {rev}:{rel_to_root(p)}",
            cwd=str(ROOT), capture_output=True, shell=True,
        )
        out[p.name] = {
            "path": rel_to_root(p),
            "object_readable": proc.returncode == 0 and bool(proc.stdout),
            "bytes": len(proc.stdout),
            "sha256": sha256(proc.stdout).hexdigest(),
        }
    return out


def main() -> int:
    argv = sys.argv[1:]

    def flag(name: str) -> str:
        return argv[argv.index(name) + 1] if name in argv else ""

    positional = [
        token
        for index, token in enumerate(argv)
        if not token.startswith("--")
        and argv[index - 1] not in (
            "--tested-tree", "--round", "--frozen-tree", "--landed-tip", "--candidate-ref", "--candidate-line"
        )
    ]
    tag = positional[0] if positional else "first"
    port = int(positional[1]) if len(positional) > 1 else 4920
    head_now = subprocess.run(
        "git rev-parse HEAD", cwd=str(ROOT), capture_output=True, text=True, shell=True
    ).stdout.strip()
    tested_tree = flag("--tested-tree") or head_now
    round_path = flag("--round")
    remote_line = flag("--remote-line")
    frozen_tree = flag("--frozen-tree")
    landed_tip = flag("--landed-tip")
    candidate_ref = flag("--candidate-ref")
    candidate_line = flag("--candidate-line")
    # The tree the gates were judged on is the FROZEN candidate tip, not this branch's tooling tip.
    # If they differ, only review/** may differ, and that has to be measured rather than claimed.
    moved_frontend = [
        line
        for line in subprocess.run(
            f"git diff --name-only {tested_tree} {head_now} -- frontend",
            cwd=str(ROOT), capture_output=True, text=True, shell=True,
        ).stdout.splitlines()
        if line.strip()
    ]
    dirty_frontend = [
        line
        for line in subprocess.run(
            "git status --porcelain -- frontend",
            cwd=str(ROOT), capture_output=True, text=True, shell=True,
        ).stdout.splitlines()
        if line.strip()
    ]
    round_receipt = json.loads(Path(round_path).read_text(encoding="utf-8")) if round_path else None
    round_keys = (
        {f"{t['exact_sha']} :: {t['nodeid']}" for t in round_receipt.get("triples", [])}
        if round_receipt
        else set()
    )
    busy = sorted({
        p
        for base in range(port, port + 2 * len(ARMS))
        for p in (base, base + 4000)
        if port_busy(p)
    })

    if busy:
        print(f"ABORT: ports already listening: {busy}")
        return 6
    originals = digests()
    committed = committed_digests(tested_tree)
    for name, _o, _s, path, anchor, _m, _w in ARMS:
        hits = open(path, encoding="utf-8", newline="").read().count(anchor)
        if hits != 1:
            print(f"ABORT: {name} anchor hits={hits} in {path.name}, expected exactly 1")
            return 2
    for p in FILES:
        entry = committed[p.name]
        if not entry["object_readable"]:
            print(f"ABORT: {p.name} is not readable at {tested_tree}")
            return 3
        if originals[p.name] != entry["sha256"]:
            print(
                f"ABORT: working {p.name} sha {originals[p.name][:16]} != {tested_tree[:16]} blob "
                f"{entry['sha256'][:16]} -- the arms would be mutating a drifted file"
            )
            return 4

    record = {
        "generatedBy": "e345b9d6",
        "order": "ORD-0292 (re-run this lane's own reverse-mutation arms on the current generation)",
        "orders": ["ORD-0278 resume carries mission_id + Idempotency-Key", "ORD-0253 client half: both legs carry the key"],
        "runTag": tag,
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "candidate_ref": {
            "ref": candidate_ref or "NOT_GIVEN",
            "tip": tested_tree,
            "externally_readable_ls_remote_line": candidate_line or "NOT_GIVEN",
        },
        "superseded_frozen_ref": {
            "ref": "refs/heads/review/0278-0253-on-45b0a5e",
            "tip": frozen_tree or "NOT_GIVEN",
            "externally_readable_ls_remote_line": remote_line or "NOT_GIVEN",
            "push_stopped_at": "frozen by the commander's ORD-0292 order and still frozen: ORD-0298 cut a "
            "new ref instead of moving this one, so the two generations keep their own coordinates",
        },
        "authoritative_tip_under_test": {
            "ref": "refs/heads/mirror/integration-frontend-apple-pass1",
            "tip": landed_tip or "NOT_GIVEN",
        },
        "tested_tree": tested_tree,
        "tooling_commit": head_now,
        "tooling_vs_tested_tree": {
            "frontend_files_moved": moved_frontend,
            "identical_under_test": not moved_frontend,
            "worktree_dirty_frontend": dirty_frontend,
            "worktree_clean_for_frontend": not dirty_frontend,
            "reading": "the arms mutate frontend/ only, so the kills are evidence about `tested_tree` "
            "even though the scripts run from a tooling commit on top of it -- but only if that list "
            "is empty, which is measured here rather than promised",
        },
        "generation_compare": (
            generation_compare(frozen_tree, landed_tip, tested_tree)
            if frozen_tree and landed_tip
            else {
                "status": "NOT_MEASURED",
                "frozen_tree": frozen_tree or "NOT_GIVEN",
                "landed_tip": landed_tip or "NOT_GIVEN",
                "needs": "both --frozen-tree and --landed-tip, or the re-parent table is an impression",
            }
        ),
        "pristine_files_match_tested_tree": {
            p.name: {"path": committed[p.name]["path"], "sha256": originals[p.name],
                     "equals_blob_at_tested_tree": originals[p.name] == committed[p.name]["sha256"]}
            for p in FILES
        },
        "gate_round": {
            "file": round_path or "NOT_GIVEN",
            "tip": (round_receipt or {}).get("candidate_tip", ""),
            "tip_equals_tested_tree": (round_receipt or {}).get("candidate_tip", "") == tested_tree,
            "triple_keys": len(round_keys),
            "reading": "every arm below re-states the (exact_sha, nodeid) key it was green under in this "
            "round, so a kill can only be read against a node that was measured green on the same tree",
        },
        "verifierNote": "claimed_result is self-reported; derived_result / direct_red / collateral_red are WRITTEN_BY_VERIFIER",
        "manualControlsAlreadyRecorded": (
            "before this batch: removing the leg-2 header reddened all three ORD-0253 nodes and the "
            "tree restored clean -- the same shape is re-measured here as K253_LEG2_KEY_DROPPED"
        ),
        "filesBefore": originals,
        "arms": [],
    }
    for name, owner, spec, path, anchor, mutant, why in ARMS:
        print(f"\n=== {name} (owner {owner}) ===", flush=True)
        baseline = run("baseline-owner-spec", port, spec)
        port += 1
        before = digests()
        with temporary_guarded_replace(path, anchor.encode(), mutant.encode(), expected_hits=1) as guard:
            attempt = run("mutated-owner-spec", port, spec)
            port += 1
        after = digests()
        red = sorted(k for k, v in attempt["nodes"].items() if v == "RED")
        # (exact_sha, nodeid, run_shape) for the ARM run itself, keyed exactly the way the green
        # round keys it -- spec-qualified title, slash-normalised -- so the two receipts join on
        # the same string and a kill cannot quietly borrow another generation's green.
        round_nodeid = f"{spec} :: {owner}".replace("\\", "/")
        key = f"{tested_tree} :: {round_nodeid}"
        # Q38: every cell's sentence has to name values that are checkable and that come out of THIS
        # cell's own readings, so the sentence is assembled from the numbers the guard and the two runs
        # produced rather than written by hand next to the arm definition.
        mutated12 = guard.mutated_sha256[:12]
        restored12 = after[path.name][:12]
        committed12 = committed[path.name]["sha256"][:12]
        why_measured = (
            f"{why}  Measured on this tip: anchor {guard.anchor_hits} hit in {rel_to_root(path)}, "
            f"{guard.bytes_changed} bytes changed, mutant {mutated12}. Baseline run {baseline['runId']} "
            f"({baseline['db']}, port {baseline['port']}) read {baseline['nodes'].get(owner)}; the same "
            f"spec with the mutant in place ran as {attempt['runId']} ({attempt['db']}, port "
            f"{attempt['port']}) and put {len(red)} node(s) in RED [{', '.join(red) or 'none'}] out of "
            f"{len(attempt['nodes'])}. After the arm the file hashed {restored12}, which equals the tested "
            f"tree's blob {committed12}."
        )
        record["arms"].append({
            "name": name, "ownerNode": owner, "why": why_measured, "intent": why, "file": str(path),
            "derived_from": (
                f"this arm's own readings; the one no other arm can quote is the mutant hash: "
                f"arm_shape_digest_12={mutated12} · attempt.db={attempt['db']} · baseline.db={baseline['db']} "
                f"· attempt.port={attempt['port']} · baseline.port={baseline['port']}"
            ),
            "triple": {
                "exact_sha": tested_tree,
                "nodeid": round_nodeid,
                "nodeid_root": f"{ROOT.as_posix()}/frontend",
                "run_shape": (
                    f"cwd={ROOT.as_posix()}/frontend (the nodeid root above), whole owner spec {spec} with ONE "
                    f"guarded mutation live in {rel_to_root(path)}, 1 worker, mobile 390x844, "
                    f"command=python review/run_spec.py {spec} {attempt['port']}, "
                    f"run_id={attempt['runId']}, fresh {attempt['db']}, ports {attempt['port']}; "
                    f"verdict taken from the `{name}` redSet below, log {attempt['log']}"
                ),
            },
            "same_key_precondition": {
                "key": key,
                "was_green_under_this_key_in_the_gate_round": key in round_keys,
                "gate_round_file": round_path or "NOT_GIVEN",
                "gate_round_tip": (round_receipt or {}).get("candidate_tip", ""),
                "gate_round_verdict_for_this_key": next(
                    (t.get("status_from_log") for t in (round_receipt or {}).get("triples", [])
                     if f"{t['exact_sha']} :: {t['nodeid']}" == key), "NO SUCH TRIPLE"
                ),
                "baseline_owner_verdict_this_batch": baseline["nodes"].get(owner),
                "arm_shape_digest": guard.mutated_sha256,
                "arm_shape_digest_12": mutated12,
                "reading": "an arm only counts as a kill on this generation if the identical "
                "(sha :: spec :: title) string is present in the green round, that round's line read "
                "`ok`, and this batch's own baseline run of the same spec read GREEN before the mutant "
                "went in -- three independent readings, none of them inherited from an earlier tip",
            },
            "restore_proof": {
                "file": rel_to_root(path),
                "digest_before_mutant": before[path.name],
                "digest_mutated": guard.mutated_sha256,
                "digest_mutated_12": mutated12,
                "digest_after_restore": after[path.name],
                "digest_after_restore_12": restored12,
                "digest_as_committed_in_tested_tree": committed[path.name]["sha256"],
                "digest_as_committed_in_tested_tree_12": committed12,
                "roundtrip_equal": before[path.name] == after[path.name],
                "restored_to_tested_tree_bytes": after[path.name] == committed[path.name]["sha256"],
                "owner_spec_ran_to_completion_under_the_mutant": bool(attempt["stackStarted"]),
            },
            "anchor_hits": guard.anchor_hits, "bytes_changed": guard.bytes_changed,
            "mutated_sha256": guard.mutated_sha256,
            "restored_exact": after[path.name] == before[path.name] == originals[path.name],
            "baseline": baseline, "attempt": attempt, "redSet": red,
            "exclusiveToOwner": red == [owner],
            "claimed_result": (
                "INVALID_STACK" if not (baseline["stackStarted"] and attempt["stackStarted"])
                else "KILLED" if attempt["nodes"].get(owner) == "RED" and baseline["nodes"].get(owner) == "GREEN"
                else "SURVIVED" if attempt["nodes"].get(owner) == "GREEN"
                else "BASELINE_RED -- arm not measured"
            ),
        })

    record["filesAfter"] = digests()
    record["treeUnchangedByThisRun"] = record["filesAfter"] == originals
    record["allArmsKilled"] = all(a["claimed_result"] == "KILLED" for a in record["arms"])
    record["allArmsRestoredToTestedTreeBytes"] = all(
        a["restore_proof"]["restored_to_tested_tree_bytes"] for a in record["arms"]
    )
    record["allArmsCarryAGreenSameKeyPrecondition"] = all(
        a["same_key_precondition"]["was_green_under_this_key_in_the_gate_round"]
        and a["same_key_precondition"]["gate_round_verdict_for_this_key"] == "ok"
        and a["same_key_precondition"]["baseline_owner_verdict_this_batch"] == "GREEN"
        for a in record["arms"]
    )
    out_path = RECEIPT_DIR / f"ord0278-0253-arms-{tag}.json"
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for arm in record["arms"]:
        print(
            f"{arm['claimed_result']:14s} owner={arm['ownerNode'][:44]:44s} "
            f"same_key={arm['same_key_precondition']['was_green_under_this_key_in_the_gate_round']} "
            f"restored={arm['restore_proof']['restored_to_tested_tree_bytes']} "
            f"red={','.join(arm['redSet']) or '-'}"
        )
    print(
        f"allArmsKilled={record['allArmsKilled']} treeUnchanged={record['treeUnchangedByThisRun']} "
        f"restoredToTestedTree={record['allArmsRestoredToTestedTreeBytes']} "
        f"sameKeyPrecondition={record['allArmsCarryAGreenSameKeyPrecondition']}"
    )
    print(f"receipt={out_path}")
    return 0 if (
        record["treeUnchangedByThisRun"]
        and record["allArmsKilled"]
        and record["allArmsRestoredToTestedTreeBytes"]
        and record["allArmsCarryAGreenSameKeyPrecondition"]
    ) else 1


if __name__ == "__main__":
    sys.exit(main())
