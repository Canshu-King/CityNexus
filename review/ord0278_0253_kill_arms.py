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
        "label": label, "spec": spec, "exitCode": proc.returncode, "runId": run_id,
        "log": str(log_path) if log_path.exists() else "", "tallies": tallies,
        "stackStarted": bool(tallies) and not missing, "missingNodes": missing, "nodes": nodes,
    }


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else "first"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 4920
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
    for name, _o, _s, path, anchor, _m, _w in ARMS:
        hits = open(path, encoding="utf-8", newline="").read().count(anchor)
        if hits != 1:
            print(f"ABORT: {name} anchor hits={hits} in {path.name}, expected exactly 1")
            return 2

    record = {
        "generatedBy": "e345b9d6",
        "orders": ["ORD-0278 resume carries mission_id + Idempotency-Key", "ORD-0253 client half: both legs carry the key"],
        "runTag": tag,
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "head": subprocess.run("git rev-parse HEAD", cwd=str(ROOT), capture_output=True, text=True, shell=True).stdout.strip(),
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
        record["arms"].append({
            "name": name, "ownerNode": owner, "why": why, "file": str(path),
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
    out_path = RECEIPT_DIR / f"ord0278-0253-arms-{tag}.json"
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for arm in record["arms"]:
        print(f"{arm['claimed_result']:14s} owner={arm['ownerNode'][:44]:44s} red={','.join(arm['redSet']) or '-'}")
    print(f"allArmsKilled={record['allArmsKilled']} treeUnchanged={record['treeUnchangedByThisRun']}")
    print(f"receipt={out_path}")
    return 0 if record["treeUnchangedByThisRun"] and record["allArmsKilled"] else 1


if __name__ == "__main__":
    sys.exit(main())
