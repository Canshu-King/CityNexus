"""ORD-0232 acceptance: five sabotage shapes, each with a named owner node.

Follows the ORD-0226 driver's rules, all learned the hard way there:
  * a green baseline of the **whole spec file** is re-taken before every arm -- a red baseline would
    let any mutant "kill" a node for unrelated reasons;
  * the mutation goes through `live_checks/mutation_anchor_guard.py` and the receipt carries
    `anchor_hits` / `bytes_changed` / `restored_exact`;
  * a run that produced no per-test summary is `INVALID_STACK`, never a kill (a webServer that could
    not start also exits non-zero);
  * ports are checked against netstat before anything is touched, because this lane's driver once
    walked onto the shared preview chain's :4781 and read that as a kill;
  * **independence** is measured, not asserted: the other three nodes must stay green under each
    mutant, otherwise one killer is secretly watching two contracts.
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

SPEC = "e2e/qoder-dropped-candidates-say-why.spec.ts"
HUB = ROOT / "frontend/src/app/V8Experience.tsx"
FEED = ROOT / "frontend/src/api/candidateRejections.ts"
RECEIPT = ROOT / "review/evidence/ui-overnight/ord0232-arms.json"
PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"

NODE1 = "ord0232-1-a-dropped-candidate-names-its-stop-and-its-condition"
NODE2 = "ord0232-2-no-rejection-event-puts-nothing-on-the-screen"
NODE3 = "ord0232-3-raw-ids-and-raw-codes-reach-neither-the-eye-nor-a-screen-reader"
NODE4 = "ord0232-4-the-card-is-painted-not-only-spoken"
ALL = [NODE1, NODE2, NODE3, NODE4]

# name, file, anchor, mutant, why, owner node
ARMS = [
    (
        "killB1-heading-without-rows",
        HUB,
        "                {dropped.map((row) => (\n",
        "                {([] as typeof dropped).map((row) => (\n",
        "the count is printed but the named stops are not: the traveller learns something was dropped and not what",
        NODE1,
    ),
    (
        "killB2-card-with-no-evidence",
        HUB,
        "          {dropped.length > 0 && (\n",
        "          {dropped.length >= 0 && (\n",
        "the card is claimed even when the audit fact says nothing was dropped -- an invented reason",
        NODE2,
    ),
    (
        "killB3-fallback-leaks-the-raw-id",
        FEED,
        '        placeName: row.placeId ? (names.get(row.placeId) ?? null) : null,\n',
        '        placeName: row.placeId ? (names.get(row.placeId) ?? row.placeId) : null,\n',
        "when the directory does not answer, the raw `place-…` id is dressed up as a place name (only the fallback path: the resolvable rows must stay green)",
        NODE3,
    ),
    (
        "killB4-raw-code-reaches-the-prose",
        HUB,
        "                      rule: hardRuleLabel(\n                        row.ruleCode,\n                        zh,\n                        t(\"hub.droppedCandidateUnknownRule\"),\n                      ),\n",
        '                      rule: row.ruleCode ?? t("hub.droppedCandidateUnknownRule"),\n',
        "the internal enum is printed instead of labelled -- the ORD-0222 leak, one field later",
        NODE3,
    ),
    (
        "killB5-spoken-but-never-seen",
        HUB,
        '              className="today-dropped"\n',
        '              className="today-dropped v8-sr-only"\n',
        "the reason exists only for a screen reader, so a sighted traveller still sees an unexplained short list",
        NODE4,
    ),
    (
        "killB6-heading-count-off-by-one",
        HUB,
        '                {t("hub.droppedCandidates", { count: dropped.length })}\n',
        '                {t("hub.droppedCandidates", { count: dropped.length + 1 })}\n',
        "the heading claims one more dropped candidate than there is evidence for -- node 1's own number, nothing else's",
        NODE1,
    ),
]


def digests() -> dict[str, str]:
    return {path.name: sha256(path.read_bytes()).hexdigest() for path in (HUB, FEED)}


def run(label: str, port: int) -> dict:
    cmd = [PYTHON, str(ROOT / "review/run_spec.py"), SPEC, str(port)]
    started = time.time()
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = proc.stdout + proc.stderr
    log = next((line.split("log=", 1)[1].strip() for line in out.splitlines() if line.startswith("exit=")), "")
    run_id = next((line.split("run_id=", 1)[1].split()[0] for line in out.splitlines() if line.startswith("run_id=")), "")
    summary = next((line.strip() for line in reversed(out.splitlines()) if " passed" in line or " failed" in line), "")
    result = {node: "absent" for node in ALL}
    for line in out.splitlines():
        # Two "›" per line (one after the file, one before the title): `.*?` and `[^›]*` both stop at
        # the first and capture the literal "e2e", so the separator has to be anchored greedily.
        match = re.match(r"^\s*(ok|x|✘)\s+\d+\s+\[[a-z-]+\].*›\s*([a-z0-9-]+)", line)
        if match and match.group(2) in result:
            result[match.group(2)] = "GREEN" if match.group(1) == "ok" else "RED"
    print(
        f"[{label}] exit={proc.returncode} run_id={run_id} {round(time.time() - started)}s "
        f"{summary!r} " + " ".join(f"{node.split('-')[1]}:{result[node]}" for node in ALL),
        flush=True,
    )
    return {
        "label": label,
        "exitCode": proc.returncode,
        "runId": run_id,
        "log": log,
        "summary": summary,
        "stackStarted": bool(summary),
        "nodes": result,
    }


def port_busy(port: int) -> bool:
    out = subprocess.run(
        "netstat -ano -p tcp", capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True
    ).stdout
    return any(f":{port} " in line and "LISTENING" in line for line in out.splitlines())


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else ""
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 4900
    span = list(range(port, port + 2 * len(ARMS)))
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
        "order": "ORD-0232",
        "runTag": tag or "first",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "guard": "live_checks/mutation_anchor_guard.py :: temporary_guarded_replace",
        "spec": SPEC,
        "runShape": "whole spec file (4 nodes + the real-seed setup project = '5 passed' when green), one fresh authoritative stack and one throwaway sqlite per run",
        "filesBefore": originals,
        "arms": [],
    }
    for name, path, anchor, mutant, why, owner in ARMS:
        print(f"\n=== {name} (owner {owner.split('-')[1]}) ===", flush=True)
        baseline = run("baseline-before-arm", port)
        port += 1
        before = digests()[path.name]
        with temporary_guarded_replace(path, anchor.encode(), mutant.encode(), expected_hits=1) as guard:
            attempt = run("mutated", port)
            port += 1
        after = digests()[path.name]
        red_set = sorted(node for node in ALL if attempt["nodes"][node] == "RED")
        others_green = all(
            attempt["nodes"][node] == "GREEN" for node in ALL if node != owner
        )
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
                "redSet": red_set,
                "exclusiveToOwner": red_set == [owner],
                "othersGreen": others_green,
                "verdict": (
                    "INVALID_STACK"
                    if not (baseline["stackStarted"] and attempt["stackStarted"])
                    else "KILLED"
                    if attempt["nodes"][owner] == "RED"
                    and baseline["nodes"][owner] == "GREEN"
                    else "SURVIVED"
                    if attempt["nodes"][owner] == "GREEN"
                    else "BASELINE_RED -- arm not measured"
                ),
                "independent": attempt["nodes"][owner] == "RED" and others_green,
            }
        )

    after_all = digests()
    record["filesAfter"] = after_all
    record["treeUnchangedByThisRun"] = after_all == originals
    record["allArmsKilled"] = all(a["verdict"] == "KILLED" for a in record["arms"])
    record["everyNodeKilled"] = {
        node: sorted(a["name"] for a in record["arms"] if node in a["redSet"]) for node in ALL
    }
    record["exclusiveKiller"] = {
        node: sorted(
            a["name"] for a in record["arms"] if a["exclusiveToOwner"] and a["ownerNode"] == node
        )
        for node in ALL
    }
    record["invalidStackArms"] = [a["name"] for a in record["arms"] if a["verdict"] == "INVALID_STACK"]
    path_out = RECEIPT.with_name(f"ord0232-arms{'-' + tag if tag else ''}.json")
    path_out.parent.mkdir(parents=True, exist_ok=True)
    path_out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for arm in record["arms"]:
        print(
            f"{arm['verdict']:16s} exclusive={str(arm['exclusiveToOwner']):5s} owner={arm['ownerNode'].split('-')[1]} "
            f"red={','.join(item.split('-')[1] for item in arm['redSet']) or '-'}  {arm['name']}  "
            f"anchor_hits={arm['anchor_hits']} bytes_changed={arm['bytes_changed']} restored_exact={arm['restored_exact']}"
        )
    print("per-node killers   :", json.dumps({k: v for k, v in record["everyNodeKilled"].items()}, ensure_ascii=False))
    print("exclusive killers  :", json.dumps(record["exclusiveKiller"], ensure_ascii=False))
    print(
        f"allArmsKilled={record['allArmsKilled']} everyNodeHasKiller={all(record['everyNodeKilled'].values())} "
        f"treeUnchanged={record['treeUnchangedByThisRun']}"
    )
    print(f"receipt={path_out}")
    ok = (
        record["allArmsKilled"]
        and all(record["everyNodeKilled"].values())
        and record["treeUnchangedByThisRun"]
        and not record["invalidStackArms"]
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
