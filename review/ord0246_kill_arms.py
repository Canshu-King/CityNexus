"""ORD-0246 acceptance: three sabotage shapes on the synchronous re-entry guard, each with the node
it owns, plus a mirror run of the ORD-0240 sheet spec so a shared judge cannot hide behind one arm.

Rules this lane already earned (0226/0232/0238): green baseline of the same spec file before every
arm, mutations only through `live_checks/mutation_anchor_guard.py`, a run without a per-test summary
is `INVALID_STACK` and not a verdict, ports pre-flighted against netstat before anything is touched
(a webServer that never started exits non-zero exactly like a kill), and the tree must come back
byte-identical.

The reverse mutation the order names is K1: put the refusal back onto the rendered state.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from hashlib import sha256
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_integration_20260919")
sys.path.insert(0, str(ROOT / "live_checks"))
from mutation_anchor_guard import temporary_guarded_replace  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

OWNER_SPEC = "e2e/qoder-same-tick-double-tap-plans-once.spec.ts"
MIRROR_SPEC = "e2e/qoder-model-words-are-labelled.spec.ts"
SHEET = ROOT / "frontend/src/features/planning/PlanWithAiSheet.tsx"
PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
RECEIPT = ROOT / "review/evidence/ui-overnight/ord0246-arms.json"

FILES = [SHEET]

GUARD_CHECK = "    if (runningRef.current) return;\n"
GUARD_RELEASE = "      runningRef.current = false;\n"

# name, file, anchor, mutant, why, owner node
ARMS = [
    (
        "killG1-refusal-moved-back-to-rendered-state",
        SHEET,
        GUARD_CHECK,
        "",
        "the named reverse mutation: without the synchronous refusal only `disabled={busy}` is left, "
        "and a same-tick pair lands two commands and two mission rows",
        "ord0246-1",
    ),
    (
        "killG2-guard-never-releases",
        SHEET,
        GUARD_RELEASE,
        "",
        "the guard becomes sticky: the traveller's next request after a finished run is silently "
        "swallowed and the button is a dead control",
        "ord0246-2",
    ),
    (
        "killG3-refused-click-aborts-the-running-request",
        SHEET,
        GUARD_CHECK,
        "    if (runningRef.current) {\n      abortRef.current?.abort();\n      return;\n    }\n",
        "refusing the second click also cancels the run that survived, which is the sabotage the "
        "order does not ask for and the traveller would not accept",
        "ord0246-3",
    ),
]


def digests() -> dict[str, str]:
    return {path.name: sha256(path.read_bytes()).hexdigest() for path in FILES}


def port_busy(port: int) -> bool:
    out = subprocess.run(
        "netstat -ano -p tcp",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    ).stdout
    return any(f":{port} " in line and "LISTENING" in line for line in out.splitlines())


def run(label: str, port: int, spec: str) -> dict:
    cmd = [PYTHON, str(ROOT / "review/run_spec.py"), spec, str(port)]
    started = time.time()
    proc = subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    out = proc.stdout + proc.stderr
    log = next((line.split("log=", 1)[1].strip() for line in out.splitlines() if line.startswith("exit=")), "")
    run_id = next(
        (line.split("run_id=", 1)[1].split()[0] for line in out.splitlines() if line.startswith("run_id=")), ""
    )
    summary = next(
        (line.strip() for line in reversed(out.splitlines()) if " passed" in line or " failed" in line), ""
    )
    nodes: dict[str, str] = {}
    for line in out.splitlines():
        # Playwright prints two "›" per line; anchor greedily or every node reads absent.
        match = re.match(r"^\s*(ok|x|✘)\s+\d+\s+\[[a-z-]+\].*›\s*([a-z0-9]+-[a-z0-9]+)", line)
        if match:
            nodes[match.group(2)] = "GREEN" if match.group(1) == "ok" else "RED"
    print(
        f"[{label}] exit={proc.returncode} run_id={run_id} {round(time.time() - started)}s {summary!r} "
        + " ".join(f"{k}:{v}" for k, v in sorted(nodes.items())),
        flush=True,
    )
    return {
        "label": label,
        "spec": spec,
        "exitCode": proc.returncode,
        "runId": run_id,
        "log": log,
        "summary": summary,
        "stackStarted": bool(summary),
        "nodes": nodes,
    }


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else ""
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5040
    span = list(range(port, port + 3 * len(ARMS)))
    busy = sorted({p for p in span + [p + 4000 for p in span] if port_busy(p)})
    if busy:
        print(f"ABORT: these ports are already listening: {busy} -- another chain owns them")
        return 6
    originals = digests()
    for name, path, anchor, _mutant, _why, _owner in ARMS:
        hits = open(path, encoding="utf-8", newline="").read().count(anchor)
        if hits != 1:
            print(f"ABORT: {name} anchor hits={hits} in {path.name}, expected exactly 1")
            return 2

    record = {
        "generatedBy": "e345b9d6",
        "order": "ORD-0246",
        "runTag": tag or "first",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "guard": "live_checks/mutation_anchor_guard.py :: temporary_guarded_replace",
        "ownerSpec": OWNER_SPEC,
        "mirrorSpec": MIRROR_SPEC,
        "runShape": (
            "whole owner spec file per arm (3 nodes + the real-seed setup project = 4 passes when green); "
            "the same mutant is then run against the ORD-0240 sheet spec as the mirror/independence run"
        ),
        "judgingCriterion": "同一 tick 两击 => 1 POST / 1 journey_missions 行，行数由服务器自己的 GET agent-feed 数出",
        "reverseMutationNamedByOrder": "killG1-refusal-moved-back-to-rendered-state",
        "filesBefore": originals,
        "arms": [],
    }
    for name, path, anchor, mutant, why, owner in ARMS:
        print(f"\n=== {name} (owner {owner}) ===", flush=True)
        baseline = run("baseline-owner-spec", port, OWNER_SPEC)
        port += 1
        before = digests()[path.name]
        with temporary_guarded_replace(path, anchor.encode(), mutant.encode(), expected_hits=1) as guard:
            attempt = run("mutated-owner-spec", port, OWNER_SPEC)
            port += 1
            mirror = run("same-mutant-mirror-spec", port, MIRROR_SPEC)
            port += 1
        after = digests()[path.name]
        red = sorted(k for k, v in attempt["nodes"].items() if v == "RED")
        green = sorted(k for k, v in attempt["nodes"].items() if v == "GREEN")
        record["arms"].append(
            {
                "name": name,
                "why": why,
                "file": str(path),
                "ownerNode": owner,
                "anchor_hits": guard.anchor_hits,
                "bytes_changed": guard.bytes_changed,
                "mutated_sha256": guard.mutated_sha256,
                "restored_sha256": after,
                "restored_exact": after == before == originals[path.name],
                "baseline": baseline,
                "attempt": attempt,
                "mirror": mirror,
                "redSet": red,
                "survivingNodes": green,
                "exclusiveToOwner": red == [owner],
                "verdict": (
                    "INVALID_STACK"
                    if not (baseline["stackStarted"] and attempt["stackStarted"])
                    else "KILLED"
                    if attempt["nodes"].get(owner) == "RED" and baseline["nodes"].get(owner) == "GREEN"
                    else "SURVIVED"
                    if attempt["nodes"].get(owner) == "GREEN"
                    else "BASELINE_RED -- arm not measured"
                ),
            }
        )

    record["filesAfter"] = digests()
    record["treeUnchangedByThisRun"] = record["filesAfter"] == originals
    record["allArmsKilled"] = all(a["verdict"] == "KILLED" for a in record["arms"])
    record["exclusiveKiller"] = {
        owner: [a["name"] for a in record["arms"] if a["exclusiveToOwner"] and a["ownerNode"] == owner]
        for owner in (a["ownerNode"] for a in record["arms"])
    }
    record["nodesWithoutAKillingArm"] = [
        owner
        for owner in (a["ownerNode"] for a in record["arms"])
        if not record["exclusiveKiller"].get(owner)
    ]
    record["invalidStackArms"] = [a["name"] for a in record["arms"] if a["verdict"] == "INVALID_STACK"]
    out_path = RECEIPT.with_name(f"ord0246-arms{'-' + tag if tag else ''}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for arm in record["arms"]:
        print(
            f"{arm['verdict']:16s} exclusive={str(arm['exclusiveToOwner']):5s} owner={arm['ownerNode']} "
            f"red={','.join(arm['redSet']) or '-'} survivors={','.join(arm['survivingNodes']) or '-'} "
            f"anchor_hits={arm['anchor_hits']} bytes_changed={arm['bytes_changed']} "
            f"restored_exact={arm['restored_exact']}  {arm['name']}"
        )
    print(f"exclusive killers: {json.dumps(record['exclusiveKiller'], ensure_ascii=False)}")
    print(f"nodes without a killing arm: {record['nodesWithoutAKillingArm']}")
    print(f"allArmsKilled={record['allArmsKilled']} treeUnchanged={record['treeUnchangedByThisRun']}")
    print(f"receipt={out_path}")
    return 0 if record["treeUnchangedByThisRun"] and record["allArmsKilled"] else 1


if __name__ == "__main__":
    sys.exit(main())
