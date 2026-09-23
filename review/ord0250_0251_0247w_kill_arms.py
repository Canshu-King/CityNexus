"""ORD-0250 + ORD-0251 + ORD-0247(widened) acceptance: nine sabotage shapes, each owning one node.

The discipline this lane already earned, unchanged: green baseline of the owner file before every arm,
mutations only through `live_checks/mutation_anchor_guard.py` (sha-verified restore), a run without a
per-test summary is `INVALID_STACK` rather than a verdict, ports pre-flighted against netstat (an
unstarted webServer exits non-zero exactly like a kill), and every arm is also played against another
lane-critical spec so collateral cannot hide behind one owner.

Arm list -- what each one is the *named* regression of:
  M1 the silent refusal of ORD-0250 coming back       K1 the raw server label of ORD-0251 coming back
  M2 the length floor drifting                        K2 an unknown label falling back to a known one
  M3 the control no longer saying it cannot advance   K3 the "not knowable" sentinel back on data-*
  W2 the touch floor re-narrowed to one class         W3 a reported disclosure leaving the sweep
  W4 the touch floor leaking into the pointer layout
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

SHEET = ROOT / "frontend/src/features/planning/PlanWithAiSheet.tsx"
CARD = ROOT / "frontend/src/features/notifications/PushCapabilityCard.tsx"
CSS = ROOT / "frontend/src/styles.css"
PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
RECEIPT = ROOT / "review/evidence/ui-overnight/ord0250-0251-0247w-arms.json"

A = "e2e/qoder-empty-request-says-what-is-missing.spec.ts"
B = "e2e/qoder-no-internal-words-or-sentinels.spec.ts"
C = "e2e/qoder-every-summary-is-tappable.spec.ts"

FILES = [SHEET, CARD, CSS]

SUMMARY_RULE = (
    "@media (max-width: 680px) { summary "
    "{ min-height: var(--cn-touch-min); line-height: var(--cn-touch-min); } }\n"
)

# name, order, owner spec, mirror spec, file, anchor, mutant, why, owner node
ARMS = [
    (
        "killM1-refusal-goes-silent-again",
        "ORD-0250",
        A,
        B,
        SHEET,
        "      setRequestTooShort(true);\n      return;\n",
        "      return;\n",
        "the exact defect ORD-0250 was filed for: a press that is refused and says nothing",
        "ord0250-1",
    ),
    (
        "killM2-length-floor-lowered-to-one",
        "ORD-0250",
        A,
        B,
        SHEET,
        "const REQUEST_MIN_LENGTH = 8;\n",
        "const REQUEST_MIN_LENGTH = 1;\n",
        "the boundary stops being the boundary: seven characters is planned from",
        "ord0250-2",
    ),
    (
        "killM3-control-stops-saying-it-cannot-advance",
        "ORD-0250",
        A,
        B,
        SHEET,
        "            aria-disabled={text.trim().length < REQUEST_MIN_LENGTH || undefined}\n",
        "            /* mutant: the control no longer declares that it cannot be advanced */\n",
        "an unusable press presented as an ordinary button, and dropped out of the keyboard path",
        "ord0250-3",
    ),
    (
        "killK1-server-label-echoed-again",
        "ORD-0251",
        B,
        A,
        CARD,
        '      <strong>\n        {keys ? t(keys.state) : unreadable ? t("push.capUnread") : t("push.checkingState")}\n      </strong>\n',
        '      <strong>{config?.capability ?? t("push.checkingState")}</strong>\n',
        "the pre-fix line from /v8/me: the server's own enum as the traveller's status",
        "ord0251-1",
    ),
    (
        "killK1b-state-stops-saying-what-it-means",
        "ORD-0251",
        B,
        A,
        CARD,
        '      <p>{message ?? t(keys ? keys.help : "push.checking")}</p>\n',
        '      <p>{message ?? t("push.checking")}</p>\n',
        "added after the v1 pass: K1 reddens nodes 1 AND 2 (an echo breaks both readings), so node 1 needed "
        "a mutant of its own -- a status line that names a state but never says what it means for the traveller",
        "ord0251-1",
    ),
    (
        "killK2-unknown-label-wears-a-known-sentence",
        "ORD-0251",
        B,
        A,
        CARD,
        'const UNKNOWN_CAPABILITY = { state: "push.capUnknown", help: "push.capUnknownHelp" };\n',
        'const UNKNOWN_CAPABILITY = { state: "push.capRecordOnly", help: "push.capRecordOnlyHelp" };\n',
        "fail closed quietly becomes fail comfortable: a status we do not know is reported as one we do",
        "ord0251-2",
    ),
    (
        "killK3-not-knowable-sentinel-back-on-data",
        "ORD-0251",
        B,
        A,
        SHEET,
        '              result?.planCount !== undefined && result.planCount >= 0 ? result.planCount : "unknown"\n',
        "              result?.planCount ?? 0\n",
        "the internal -1 published again on an attribute a gate parses as a count",
        "ord0251-3",
    ),
    (
        "killW2-touch-floor-re-narrowed-to-one-class",
        "ORD-0247",
        C,
        B,
        CSS,
        SUMMARY_RULE,
        SUMMARY_RULE.replace("summary {", ".v8-advanced > summary {"),
        "the single-page fix the widened acceptance exists to refuse: bookings passes, the AI sheet's "
        "「技术详情」 goes back to 25px",
        "ord0247w-1",
    ),
    (
        "killW3-reported-disclosure-leaves-the-sweep",
        "ORD-0247",
        C,
        B,
        SHEET,
        '{zh ? "技术详情" : "Technical detail"}',
        '{zh ? "细节" : "Detail"}',
        "a sweep over nothing would still read green, so the inventory has to keep containing the "
        "controls that were reported",
        "ord0247w-2",
    ),
    (
        "killW4-touch-floor-moved-out-of-the-mobile-layer",
        "ORD-0247",
        C,
        B,
        CSS,
        SUMMARY_RULE,
        SUMMARY_RULE.replace("@media (max-width: 680px)", "@media (min-width: 0px)"),
        "the touch floor leaking onto the pointer layout, which Amendment F-2 owns",
        "ord0247w-3",
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
        match = re.match(r"^\s*(ok|x|✘)\s+\d+\s+\[[a-z-]+\].*›\s*([a-z0-9]+(?:w)?-[a-z0-9]+)", line)
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
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5300
    span = list(range(port, port + 3 * len(ARMS)))
    busy = sorted({p for p in span + [p + 4000 for p in span] if port_busy(p)})
    if busy:
        print(f"ABORT: these ports are already listening: {busy} -- another chain owns them")
        return 6
    originals = digests()
    for name, _order, _spec, _mirror, path, anchor, _mutant, _why, _owner in ARMS:
        hits = open(path, encoding="utf-8", newline="").read().count(anchor)
        if hits != 1:
            print(f"ABORT: {name} anchor hits={hits} in {path.name}, expected exactly 1")
            return 2

    record = {
        "generatedBy": "e345b9d6",
        "orders": ["ORD-0250", "ORD-0251", "ORD-0247 (widened)"],
        "runTag": tag or "first",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "guard": "live_checks/mutation_anchor_guard.py :: temporary_guarded_replace",
        "specs": {"ORD-0250": A, "ORD-0251": B, "ORD-0247": C},
        "runShape": (
            "whole owner spec file per arm (3 nodes + the real-seed setup project = 4 passes when green); "
            "the same mutant is then played against another lane-critical spec as the collateral mirror"
        ),
        "verifierNote": (
            "claimed_result lives here; derived_result / direct_red / collateral_red are WRITTEN_BY_VERIFIER "
            "per the frozen receipt schema -- this lane does not grade its own kills"
        ),
        "filesBefore": originals,
        "arms": [],
    }
    for name, order, spec, mirror_spec, path, anchor, mutant, why, owner in ARMS:
        print(f"\n=== {name} ({order}, owner {owner}) ===", flush=True)
        baseline = run("baseline-owner-spec", port, spec)
        port += 1
        before = digests()[path.name]
        with temporary_guarded_replace(path, anchor.encode(), mutant.encode(), expected_hits=1) as guard:
            attempt = run("mutated-owner-spec", port, spec)
            port += 1
            mirror = run("same-mutant-mirror-spec", port, mirror_spec)
            port += 1
        after = digests()[path.name]
        red = sorted(k for k, v in attempt["nodes"].items() if v == "RED")
        green = sorted(k for k, v in attempt["nodes"].items() if v == "GREEN")
        record["arms"].append(
            {
                "name": name,
                "order": order,
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
                "survivingNodes": green,
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
    owners = [a["ownerNode"] for a in record["arms"]]
    record["exclusiveKiller"] = {
        owner: [a["name"] for a in record["arms"] if a["exclusiveToOwner"] and a["ownerNode"] == owner]
        for owner in owners
    }
    record["nodesWithoutAKillingArm"] = [o for o in owners if not record["exclusiveKiller"].get(o)]
    record["mirrorCollateral"] = [
        {"arm": a["name"], "mirrorRed": sorted(k for k, v in a["mirror"]["nodes"].items() if v == "RED")}
        for a in record["arms"]
    ]
    record["invalidStackArms"] = [a["name"] for a in record["arms"] if a["claimed_result"] == "INVALID_STACK"]
    out_path = RECEIPT.with_name(f"ord0250-0251-0247w-arms{'-' + tag if tag else ''}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for arm in record["arms"]:
        print(
            f"{arm['claimed_result']:16s} exclusive={str(arm['exclusiveToOwner']):5s} owner={arm['ownerNode']} "
            f"red={','.join(arm['redSet']) or '-'} survivors={','.join(arm['survivingNodes']) or '-'} "
            f"anchor_hits={arm['anchor_hits']} bytes_changed={arm['bytes_changed']} "
            f"restored_exact={arm['restored_exact']}  {arm['name']}"
        )
    print(f"exclusive killers: {json.dumps(record['exclusiveKiller'], ensure_ascii=False)}")
    print(f"nodes without a killing arm: {record['nodesWithoutAKillingArm']}")
    print(f"mirror collateral: {json.dumps([m for m in record['mirrorCollateral'] if m['mirrorRed']], ensure_ascii=False)}")
    print(f"allArmsKilled={record['allArmsKilled']} treeUnchanged={record['treeUnchangedByThisRun']}")
    print(f"receipt={out_path}")
    return 0 if record["treeUnchangedByThisRun"] and record["allArmsKilled"] else 1


if __name__ == "__main__":
    sys.exit(main())
