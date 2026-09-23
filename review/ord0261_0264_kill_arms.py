"""ORD-0261/0264 acceptance: the two ruling-named arms, each owning one node, on my branch bytes.

K261_REMOVE_STICKY_RESERVE deletes the 76px (+mobile clearance) reserve from styles.css -- the sticky
bar's gradient then paints over the summary row again and the 0261 node must redden at its centre
hit-test.

K264_MOVE_OPENER_BACK_TO_PAGE_TAIL relocates the opener button back into the page-bottom secondary
row -- the locality cell (step-1-card containment) must redden FIRST; any centre-hit overlap red is
collateral, not independent evidence, which is exactly what the locality cell exists to guarantee.

Same discipline as previous runs: green baseline of the owner file before every arm, mutations through
`live_checks/mutation_anchor_guard.py` (sha-verified restore), INVALID_STACK when a run produces no
per-test summary, ports pre-flighted, tree byte-identical after, and a mirror spec per arm for
collateral visibility. Receipt = claimed_result only; grading is the verifier's.
"""

from __future__ import annotations

import json
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

OWNER = "e2e/qoder-wizard-advanced-is-tappable.spec.ts"
MIRROR = "e2e/qoder-ord0261-overlap-readonly-reproduction.spec.ts"
TSX = ROOT / "frontend/src/features/setup/JourneyTrialSetup.tsx"
CSS = ROOT / "frontend/src/styles.css"
PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
RECEIPT = ROOT / "review/evidence/ui-overnight/ord0261-0264-arms.json"

FILES = [TSX, CSS]

RESERVE = (
    "@media (max-width: 680px) {\n"
    "  .cn-onboarding .trial-steps {\n"
    "    padding-bottom: calc(76px + var(--cn-sim-float-clearance, 132px) + env(safe-area-inset-bottom, 0px));\n"
    "  }\n"
    "}"
)
OPENER_BLOCK = (
    "          {step === 1 && (\n"
    "            <button\n"
    "              type=\"button\"\n"
    "              className=\"trial-back-link\"\n"
    "              data-testid=\"trial-show-advanced\"\n"
    "              onClick={() => {\n"
    "                setAdvanced(true);\n"
    "                const node = document.querySelector(\".trial-advanced\") as HTMLDetailsElement | null;\n"
    "                if (node) node.open = true;\n"
    "              }}\n"
    "            >\n"
    "              {zh ? \"高级设置\" : \"Advanced settings\"}\n"
    "            </button>\n"
    "          )}\n"
)

# name, owner node, file, anchor, mutant, why
ARMS = [
    (
        "K261_REMOVE_STICKY_RESERVE",
        "ord0261",
        CSS,
        RESERVE,
        "",
        "the named reverse mutation: the reserve is gone, so the sticky bar's gradient paints over the "
        "summary row again and its centre hit-test must fail",
    ),
    (
        "K264_MOVE_OPENER_BACK_TO_PAGE_TAIL",
        "ord0264",
        TSX,
        OPENER_BLOCK,
        "",
        "the named reverse mutation: the opener returns to the page tail, the locality cell must redden "
        "first and any overlap red is collateral",
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
    env_cmd = [PYTHON, str(ROOT / "review/run_spec.py"), spec, str(port)]
    env = dict(os.environ)
    env["CNX_LANE_ROOT"] = str(ROOT)
    started = time.time()
    proc = subprocess.run(
        env_cmd, cwd=str(ROOT), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    out = proc.stdout + proc.stderr
    run_id = next(
        (line.split("run_id=", 1)[1].split()[0] for line in out.splitlines() if line.startswith("run_id=")), ""
    )
    summary = next(
        (line.strip() for line in reversed(out.splitlines()) if " passed" in line or " failed" in line), ""
    )
    nodes: dict[str, str] = {}
    for line in out.splitlines():
        verdict = "GREEN" if line.lstrip().startswith("ok") else "RED" if re.match(r"^\s*[x✘]", line) else None
        if verdict:
            m2 = re.search(r"(ord02[0-9]+)-", line)
            if m2:
                nodes[m2.group(1)] = verdict
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
        "summary": summary,
        "stackStarted": bool(summary),
        "nodes": nodes,
    }


import os  # noqa: E402


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else "first"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 4630
    span = list(range(port, port + 3 * len(ARMS)))
    busy = sorted({p for p in span + [p + 4000 for p in span] if port_busy(p)})
    if busy:
        print(f"ABORT: ports already listening: {busy}")
        return 6
    originals = digests()
    for name, _owner, path, anchor, _mutant, _why in ARMS:
        hits = open(path, encoding="utf-8", newline="").read().count(anchor)
        if hits != 1:
            print(f"ABORT: {name} anchor hits={hits} in {path.name}, expected exactly 1")
            return 2

    record = {
        "generatedBy": "e345b9d6",
        "order": "ORD-0261 + ORD-0264",
        "runTag": tag,
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tree": str(ROOT),
        "contract": "SCROLL_REACHABLE_AND_TAPPABLE (arbiter 17:19) with locality + human-path witness cells",
        "armsNamedByRuling": [a[0] for a in ARMS],
        "verifierNote": "claimed_result only; derived_result/direct_red/collateral_red are WRITTEN_BY_VERIFIER",
        "filesBefore": originals,
        "arms": [],
    }
    for name, owner, path, anchor, _mutant, why in ARMS:
        print(f"\n=== {name} (owner {owner}) ===", flush=True)
        baseline = run("baseline-owner-spec", port, OWNER)
        port += 1
        before = digests()
        with temporary_guarded_replace(path, anchor.encode(), b"", expected_hits=1) as guard:
            attempt = run("mutated-owner-spec", port, OWNER)
            port += 1
            mirror = run("same-mutant-mirror-spec", port, MIRROR)
            port += 1
        after = digests()
        red = sorted(k for k, v in attempt["nodes"].items() if v == "RED")
        record["arms"].append(
            {
                "name": name,
                "ownerNode": owner,
                "why": why,
                "file": str(path),
                "anchor_hits": guard.anchor_hits,
                "bytes_changed": guard.bytes_changed,
                "mutated_sha256": guard.mutated_sha256,
                "restored_exact": after[path.name] == before[path.name] == originals[path.name],
                "baseline": baseline,
                "attempt": attempt,
                "mirror": mirror,
                "redSet": red,
                "exclusiveToOwner": red == [owner],
                "claimed_result": (
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
    record["allArmsKilled"] = all(a["claimed_result"] == "KILLED" for a in record["arms"])
    record["exclusiveKiller"] = {
        a["ownerNode"]: [a["name"] for a in record["arms"] if a["exclusiveToOwner"] and a["ownerNode"] == a["ownerNode"]]
        for a in record["arms"]
    }
    record["mirrorCollateral"] = [
        {"arm": a["name"], "mirrorRed": sorted(k for k, v in a["mirror"]["nodes"].items() if v == "RED")}
        for a in record["arms"]
    ]
    out_path = RECEIPT.with_name(f"ord0261-0264-arms-{tag}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for arm in record["arms"]:
        print(
            f"{arm['claimed_result']:14s} owner={arm['ownerNode']} red={','.join(arm['redSet']) or '-'} "
            f"anchor_hits={arm['anchor_hits']} bytes_changed={arm['bytes_changed']} "
            f"restored_exact={arm['restored_exact']}  {arm['name']}"
        )
    print(f"allArmsKilled={record['allArmsKilled']} treeUnchanged={record['treeUnchangedByThisRun']}")
    print(f"receipt={out_path}")
    return 0 if record["treeUnchangedByThisRun"] and record["allArmsKilled"] else 1


if __name__ == "__main__":
    sys.exit(main())
