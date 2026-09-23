"""ORD-0247 acceptance: three sabotage shapes on the touch-target rule, each owning one node.

Same rules as the ORD-0246 run: green baseline of the owner file before every arm, mutations through
`live_checks/mutation_anchor_guard.py` (sha-verified restore), a run with no per-test summary is
`INVALID_STACK`, ports pre-flighted, and the tree must come back byte-identical.  Each arm is also
played against the sibling ORD-0246 spec so a CSS change cannot claim independence it has not shown.

H1 doubles as the before-state measurement: with the rule deleted, the failure message carries the
height the order reported (311x14), so the defect is re-confirmed by this instrument and not quoted.
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

OWNER_SPEC = "e2e/qoder-advanced-summary-is-tappable.spec.ts"
MIRROR_SPEC = "e2e/qoder-same-tick-double-tap-plans-once.spec.ts"
CSS = ROOT / "frontend/src/styles.css"
PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
RECEIPT = ROOT / "review/evidence/ui-overnight/ord0247-arms.json"

FILES = [CSS]

RULE = (
    "@media (max-width: 680px) { .v8-advanced > summary "
    "{ min-height: var(--cn-touch-min); line-height: var(--cn-touch-min); } }"
)

# name, file, anchor, mutant, why, owner node
ARMS = [
    (
        "killH1-touch-floor-deleted",
        CSS,
        RULE,
        "",
        "the named defect returns: the disclosure is a 14px-tall strip again, and this arm also "
        "re-measures the before-state height",
        "ord0247-1",
    ),
    (
        "killH2-target-grown-but-not-tappable",
        CSS,
        RULE,
        RULE.replace("line-height: var(--cn-touch-min); }",
                    "line-height: var(--cn-touch-min); pointer-events: none; }"),
        "geometry passes while the finger lands on an ancestor -- exactly the false pass the order "
        "names ('命中的就是该控件本身，不是它的父容器')",
        "ord0247-2",
    ),
    (
        "killH3-floor-moved-out-of-the-mobile-layer",
        CSS,
        RULE,
        RULE.replace("@media (max-width: 680px)", "@media (min-width: 0px)"),
        "the touch floor leaks onto the pointer layout, breaking Amendment F-2's compact desktop "
        "density that this file's third node owns",
        "ord0247-3",
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
        match = re.match(r"^\s*(ok|x|✘)\s+\d+\s+\[[a-z-]+\].*›\s*([a-z0-9]+-[a-z0-9]+)", line)
        if match:
            nodes[match.group(2)] = "GREEN" if match.group(1) == "ok" else "RED"
    geometry = re.findall(r"measures (\d+)x(\d+)", out)
    print(
        f"[{label}] exit={proc.returncode} run_id={run_id} {round(time.time() - started)}s {summary!r} "
        + " ".join(f"{k}:{v}" for k, v in sorted(nodes.items()))
        + (f" measured={geometry}" if geometry else ""),
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
        "geometryInFailureMessage": [f"{w}x{h}" for w, h in geometry],
    }


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else ""
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5200
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
        "order": "ORD-0247",
        "runTag": tag or "first",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "guard": "live_checks/mutation_anchor_guard.py :: temporary_guarded_replace",
        "ownerSpec": OWNER_SPEC,
        "mirrorSpec": MIRROR_SPEC,
        "runShape": (
            "whole owner spec file per arm (3 nodes + the real-seed setup project = 4 passes when green); "
            "the same mutant is then run against the ORD-0246 spec as the independence mirror"
        ),
        "judgingCriterion": "elementFromPoint(盒中心) === 该 <summary> 本身，且真触摸屏点把它打开；桌面那格守住 <=30px",
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
    record["mirrorCollateral"] = [
        {
            "arm": a["name"],
            "mirrorRed": sorted(k for k, v in a["mirror"]["nodes"].items() if v == "RED"),
        }
        for a in record["arms"]
    ]
    record["invalidStackArms"] = [a["name"] for a in record["arms"] if a["verdict"] == "INVALID_STACK"]
    out_path = RECEIPT.with_name(f"ord0247-arms{'-' + tag if tag else ''}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for arm in record["arms"]:
        print(
            f"{arm['verdict']:16s} exclusive={str(arm['exclusiveToOwner']):5s} owner={arm['ownerNode']} "
            f"red={','.join(arm['redSet']) or '-'} survivors={','.join(arm['survivingNodes']) or '-'} "
            f"measured={arm['attempt']['geometryInFailureMessage'] or '-'} "
            f"anchor_hits={arm['anchor_hits']} bytes_changed={arm['bytes_changed']} "
            f"restored_exact={arm['restored_exact']}  {arm['name']}"
        )
    print(f"exclusive killers: {json.dumps(record['exclusiveKiller'], ensure_ascii=False)}")
    print(f"nodes without a killing arm: {record['nodesWithoutAKillingArm']}")
    print(f"mirror collateral: {json.dumps(record['mirrorCollateral'], ensure_ascii=False)}")
    print(f"allArmsKilled={record['allArmsKilled']} treeUnchanged={record['treeUnchangedByThisRun']}")
    print(f"receipt={out_path}")
    return 0 if record["treeUnchangedByThisRun"] and record["allArmsKilled"] else 1


if __name__ == "__main__":
    sys.exit(main())
