"""ORD-0238 + ORD-0240 acceptance: five sabotage shapes, each with the node it owns.

Same rules this lane earned on 0226/0232: green baseline of the **same spec file** before every arm,
mutations through `live_checks/mutation_anchor_guard.py`, a run without a per-test summary is
`INVALID_STACK` rather than a verdict, ports checked against netstat before anything is touched, and
the **other** spec file run under the same mutant so a shared judge cannot hide behind one arm.
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

STATED = "e2e/qoder-stated-versus-stored-versus-planned.spec.ts"
WORDS = "e2e/qoder-model-words-are-labelled.spec.ts"
SETUP = ROOT / "frontend/src/features/setup/JourneyTrialSetup.tsx"
HUB = ROOT / "frontend/src/app/V8Experience.tsx"
CMP = ROOT / "frontend/src/features/planning/PlanComparison.tsx"
SHEET = ROOT / "frontend/src/features/planning/PlanWithAiSheet.tsx"
PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
RECEIPT = ROOT / "review/evidence/ui-overnight/ord0238-0240-arms.json"

FILES = [SETUP, HUB, CMP, SHEET]

# name, file, anchor, mutant, why, owner node, owner spec, mirror spec
ARMS = [
    (
        "killD1-review-drops-what-she-picked",
        SETUP,
        '                {optionLabels(draft.interests ?? [], INTEREST_OPTIONS, zh) || "—"}\n',
        '                {optionLabels([], INTEREST_OPTIONS, zh) || "—"}\n',
        "layer 1 breaks: the confirmation screen no longer reports the chips she pressed",
        "ord0238-1",
        STATED,
        WORDS,
    ),
    (
        "killD2-interests-never-reach-the-server",
        HUB,
        "        await syncStatedInterests(traveler.id, draft.interests ?? []);\n",
        "        await syncStatedInterests(traveler.id, []);\n",
        "layer 2 breaks: her words are shown but never stored through the contract",
        "ord0238-2",
        STATED,
        WORDS,
    ),
    (
        "killD3-headline-claims-pace-again",
        CMP,
        "            ? `我们按这座城可核验的地点和你的预算，生成了 ${candidates.length} 个可选方案。`\n",
        "            ? `我们按你的预算和节奏生成了 ${candidates.length} 个可选方案。`\n",
        "layer 3 breaks: the screen promises an input the planner does not take",
        "ord0238-3",
        STATED,
        WORDS,
    ),
    (
        "killD4-model-words-back-in-the-main-flow",
        SHEET,
        "            <p>{copy.body}</p>\n",
        '            <p>{copy.body}</p>\n            {result?.summary && <p className="plan-ai-summary">{result.summary}</p>}\n',
        "the exact defect ORD-0240 was filed for: the model's English sentence painted into a Chinese screen's own copy",
        "ord0240-1",
        WORDS,
        STATED,
    ),
    (
        "killD5-model-words-unlabelled",
        SHEET,
        '                    <span className="plan-ai-detail-label" data-testid="plan-ai-model-label">\n',
        '                    <span className="plan-ai-detail-label" data-testid="plan-ai-model-label-hid">\n',
        "the raw sentence survives but loses the label that says whose words they are",
        "ord0240-2",
        WORDS,
        STATED,
    ),
    (
        "killD6-disclosure-open-by-default",
        SHEET,
        '              <details className="plan-ai-detail">\n',
        '              <details className="plan-ai-detail" open>\n',
        "the technical layer spills onto the first screen without anyone opening it -- node 3's property alone",
        "ord0240-3",
        WORDS,
        STATED,
    ),
]


def digests() -> dict[str, str]:
    return {path.name: sha256(path.read_bytes()).hexdigest() for path in FILES}


def port_busy(port: int) -> bool:
    out = subprocess.run(
        "netstat -ano -p tcp", capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True
    ).stdout
    return any(f":{port} " in line and "LISTENING" in line for line in out.splitlines())


def run(label: str, port: int, spec: str) -> dict:
    cmd = [PYTHON, str(ROOT / "review/run_spec.py"), spec, str(port)]
    started = time.time()
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = proc.stdout + proc.stderr
    log = next((line.split("log=", 1)[1].strip() for line in out.splitlines() if line.startswith("exit=")), "")
    run_id = next((line.split("run_id=", 1)[1].split()[0] for line in out.splitlines() if line.startswith("run_id=")), "")
    summary = next((line.strip() for line in reversed(out.splitlines()) if " passed" in line or " failed" in line), "")
    nodes: dict[str, str] = {}
    for line in out.splitlines():
        # Playwright prints two "›" per line; anchor greedily on the last one or every node reads absent.
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
    for name, path, anchor, _mutant, _why, _owner, _spec, _mirror in ARMS:
        hits = open(path, encoding="utf-8", newline="").read().count(anchor)
        if hits != 1:
            print(f"ABORT: {name} anchor hits={hits} in {path.name}, expected exactly 1")
            return 2

    record = {
        "generatedBy": "e345b9d6",
        "order": "ORD-0238 + ORD-0240",
        "runTag": tag or "first",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "guard": "live_checks/mutation_anchor_guard.py :: temporary_guarded_replace",
        "specs": [STATED, WORDS],
        "runShape": "whole spec file per arm (owner's file for the verdict, the other file as the mirror run); the real-seed setup project counts as one extra pass",
        "filesBefore": originals,
        "arms": [],
    }
    for name, path, anchor, mutant, why, owner, spec, mirror_spec in ARMS:
        print(f"\n=== {name} (owner {owner}) ===", flush=True)
        baseline = run("baseline-owner-spec", port, spec)
        port += 1
        before = digests()[path.name]
        with temporary_guarded_replace(path, anchor.encode(), mutant.encode(), expected_hits=1) as guard:
            attempt = run("mutated-owner-spec", port, spec)
            port += 1
            mirror = run("same-mutant-other-spec", port, mirror_spec)
            port += 1
        after = digests()[path.name]
        red = sorted(k for k, v in attempt["nodes"].items() if v == "RED")
        record["arms"].append(
            {
                "name": name,
                "why": why,
                "file": str(path),
                "ownerNode": owner,
                "ownerSpec": spec,
                "anchor_hits": guard.anchor_hits,
                "bytes_changed": guard.bytes_changed,
                "mutated_sha256": guard.mutated_sha256,
                "restored_sha256": after,
                "restored_exact": after == before == originals[path.name],
                "baseline": baseline,
                "attempt": attempt,
                "mirror": mirror,
                "redSet": red,
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
    record["invalidStackArms"] = [a["name"] for a in record["arms"] if a["verdict"] == "INVALID_STACK"]
    out_path = RECEIPT.with_name(f"ord0238-0240-arms{'-' + tag if tag else ''}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for arm in record["arms"]:
        print(
            f"{arm['verdict']:16s} exclusive={str(arm['exclusiveToOwner']):5s} owner={arm['ownerNode']} "
            f"red={','.join(arm['redSet']) or '-'} anchor_hits={arm['anchor_hits']} "
            f"bytes_changed={arm['bytes_changed']} restored_exact={arm['restored_exact']}  {arm['name']}"
        )
    print(f"exclusive killers: {json.dumps(record['exclusiveKiller'], ensure_ascii=False)}")
    print(f"allArmsKilled={record['allArmsKilled']} treeUnchanged={record['treeUnchangedByThisRun']}")
    print(f"receipt={out_path}")
    return 0 if record["allArmsKilled"] and record["treeUnchangedByThisRun"] and not record["invalidStackArms"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
