"""ORD-0226 acceptance run: five arms through `live_checks/mutation_anchor_guard.py`.

Order is fixed by the order: one green baseline, then one arm at a time, and a **fresh green
baseline before every arm** -- a red baseline would let any mutant "kill" the node for unrelated
reasons.  Follow-up ① (commander 02:1x) added the English arm, so each language now has its own
frozen literal and its own node, and every arm additionally runs **the other language's node under
the same mutant**: that has to stay green, or the two pins share one judge and neither is proven
independent.

The arms are the red team's (`d2305848`, 23:4x): E1 appended 「不过别担心，肯定够用」 to the frozen
caveat -- every word outside `ALLAY_WORDS`, which is why the old word-table gate stayed green.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from hashlib import sha256
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_integration_20260919")
sys.path.insert(0, str(ROOT / "live_checks"))
from mutation_anchor_guard import temporary_guarded_replace  # noqa: E402

# Redirecting this script's stdout to a file makes Python pick the console codepage (gbk here), which
# turned the published arm console into mojibake on every Chinese line while the JSON receipt stayed
# clean.  Same fix as review/run_spec.py.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

PRODUCT = ROOT / "frontend/src/app/V8Experience.tsx"
SPEC = "e2e/qoder-budget-advisory-tiers.spec.ts"
ZH_NODE = "ord0220-1-the-tight-caveat-cannot-contradict-itself"
EN_NODE = "ord0226-e-the-english-caveat-reaches-the-screen-and-is-the-frozen-sentence"
RECEIPT = ROOT / "review/evidence/ui-overnight/ord0226-arms.json"
PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"

ZH_FROZEN = '  "按这个预算，住宿、交通和吃饭很可能超出计划。可以先调整预算，或你确认继续也可以。";\n'
EN_FROZEN = (
    '  "At this budget, lodging, transport and food are likely to exceed the plan. '
    'Adjust the budget, or continue intentionally.";\n'
)

# name, anchor, mutant, why, node under test, node that must stay green under the same mutant
ARMS = [
    (
        "killAC1-e1-reassurance-outside-any-word-table",
        ZH_FROZEN,
        '  "按这个预算，住宿、交通和吃饭很可能超出计划。可以先调整预算，或你确认继续也可以。不过别担心，肯定够用";\n',
        "the red team's E1 arm verbatim: 别担心/肯定够 are not in ALLAY_WORDS, so only literal equality can catch it",
        ZH_NODE,
        EN_NODE,
    ),
    (
        "killAC2-e2-the-caveat-denies-itself",
        ZH_FROZEN,
        '  "这个预算不会超出计划，你可以放心调整。";\n',
        "arm E2's shape: the caveat stops warning and tells the traveller to relax",
        ZH_NODE,
        EN_NODE,
    ),
    (
        "killAC3-selftest-one-punctuation-mark",
        ZH_FROZEN,
        '  "按这个预算，住宿、交通和吃饭很可能超出计划。可以先调整预算，或你确认继续也可以，";\n',
        "acceptance 5: one full stop becomes one comma -- green here would mean the equality is not literal",
        ZH_NODE,
        EN_NODE,
    ),
    (
        "killAC4-e1-shape-in-english",
        EN_FROZEN,
        '  "At this budget, lodging, transport and food are likely to exceed the plan. Adjust the budget, or continue intentionally, but do not worry, it will be plenty.";\n',
        "follow-up ①: the same E1 shape in the language arm the word tables never covered at all",
        EN_NODE,
        ZH_NODE,
    ),
    (
        "killAC5-selftest-one-english-punctuation-mark",
        EN_FROZEN,
        '  "At this budget, lodging, transport and food are likely to exceed the plan. Adjust the budget, or continue intentionally,";\n',
        "follow-up ①: the English pin is literal too -- one final full stop becomes one comma",
        EN_NODE,
        ZH_NODE,
    ),
    (
        "killAC6-redteam-e1-verbatim-in-english",
        EN_FROZEN,
        '  "At this budget, lodging, transport and food are likely to exceed the plan. Adjust the budget, or continue intentionally. Don\'t worry, you have plenty.";\n',
        "red team `d2305848` on e08131e, sentence copied verbatim -- it broke the English face where E1 broke the Chinese one",
        EN_NODE,
        ZH_NODE,
    ),
]


def port_busy(port: int) -> bool:
    """`netstat` is the only honest probe here: a TCP connect can hang instead of refusing."""
    out = subprocess.run(
        "netstat -ano -p tcp",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    ).stdout
    return any(f":{port} " in line and "LISTENING" in line for line in out.splitlines())


def digest() -> str:
    return sha256(PRODUCT.read_bytes()).hexdigest()


def run(label: str, port: int, node: str) -> dict:
    """One node, one throwaway stack.  run_spec.py prints `exit=` and its own log path."""
    cmd = [PYTHON, str(ROOT / "review/run_spec.py"), SPEC, str(port), "--grep", node]
    started = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = proc.stdout + proc.stderr
    log = next((line.split("log=", 1)[1].strip() for line in out.splitlines() if line.startswith("exit=")), "")
    run_id = next((line.split("run_id=", 1)[1].split()[0] for line in out.splitlines() if line.startswith("run_id=")), "")
    summary = next((line.strip() for line in reversed(out.splitlines()) if " passed" in line or " failed" in line), "")
    owner = ""
    block = ""
    if proc.returncode != 0:
        # The assertion's own message carries the node id, so a red names the assertion that reddened.
        for line in reversed(out.splitlines()):
            if node in line and ("frozen sentence" in line or "not renderable" in line or "contradicts" in line):
                owner = " ".join(line.split())
                break
        lines: list[str] = []
        if log and Path(log).exists():
            lines = Path(log).read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines):
            if line.strip().startswith("Error:") and node in line:
                block = "\n".join(item.strip()[:220] for item in lines[index : index + 4])
                break
    print(
        f"[{label}] node={node.split('-')[0]} exit={proc.returncode} run_id={run_id} "
        f"{round(time.time() - started)}s summary={summary!r}",
        flush=True,
    )
    if not summary:
        print(
            f"[{label}] INVALID_STACK: no per-test summary at all (port {port}); this run measured nothing",
            flush=True,
        )
    return {
        "label": label,
        "node": node,
        "stackStarted": bool(summary),
        "command": " ".join(cmd[:3]) + f" {port} --grep {node}",
        "exitCode": proc.returncode,
        "runId": run_id,
        "log": log,
        "summary": summary,
        "ownerAssertion": owner[:600],
        "errorBlock": block,
    }


def main() -> int:
    with open(PRODUCT, encoding="utf-8", newline="") as fh:
        source = fh.read()
    for anchor in (ZH_FROZEN, EN_FROZEN):
        if source.count(anchor) != 1:
            print(f"ABORT: anchor occurs {source.count(anchor)} times, expected 1: {anchor[:40]!r}")
            return 2

    tag = sys.argv[1] if len(sys.argv) > 1 else ""
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 4620
    span = list(range(port, port + 3 * len(ARMS)))
    busy = sorted({p for p in span + [p + 4000 for p in span] if port_busy(p)})
    if busy:
        print(f"ABORT: these ports are already listening: {busy} -- another chain owns them")
        return 6
    receipt_path = RECEIPT.with_name(f"ord0226-arms{'-' + tag if tag else ''}.json")
    record = {
        "generatedBy": "e345b9d6",
        "order": "ORD-0226 (+ follow-up ① English arm)",
        "runTag": tag or "first",
        "fix": "A -- both caveat sentences are frozen literals in the product; each gate holds its OWN copy and asserts string equality",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "guard": "live_checks/mutation_anchor_guard.py :: temporary_guarded_replace",
        "nodes": {"zh": ZH_NODE, "en": EN_NODE},
        "spec": SPEC,
        "runShape": (
            "single node (--grep on the exact node id) against an authoritative throwaway stack; "
            "the 'real-seed' setup project counts as one extra pass, so a green single-node run reads '2 passed'"
        ),
        "productFileBeforeSha256": digest(),
        "arms": [],
    }

    for name, anchor, mutant, why, node, other in ARMS:
        print(f"\n=== {name} ===", flush=True)
        baseline = run("baseline-before-arm", port, node)
        port += 1
        before = digest()
        with temporary_guarded_replace(PRODUCT, anchor.encode(), mutant.encode(), expected_hits=1) as receipt:
            mutated = receipt.mutated_sha256
            attempt = run("mutated-target-node", port, node)
            port += 1
            mirror = run("same-mutant-other-language-node", port, other)
            port += 1
        after = digest()
        record["arms"].append(
            {
                "name": name,
                "why": why,
                "anchorPath": str(PRODUCT),
                "anchor_hits": receipt.anchor_hits,
                "expected_anchor_hits": receipt.expected_anchor_hits,
                "bytes_changed": receipt.bytes_changed,
                "before_sha256": before,
                "mutated_sha256": mutated,
                "restored_sha256": after,
                "restored_exact": after == record["productFileBeforeSha256"] == before,
                "baseline": baseline,
                "mutated": attempt,
                "mirror_other_language": mirror,
                "verdict": (
                    "INVALID_STACK"
                    if not all(r["stackStarted"] for r in (baseline, attempt, mirror))
                    else "KILLED"
                    if attempt["exitCode"] != 0 and baseline["exitCode"] == 0
                    else "SURVIVED"
                    if attempt["exitCode"] == 0
                    else "BASELINE_RED -- arm not measured"
                ),
                "independent": all(r["stackStarted"] for r in (baseline, attempt, mirror))
                and attempt["exitCode"] != 0
                and mirror["exitCode"] == 0,
            }
        )

    record["productFileAfterSha256"] = digest()
    record["treeUnchangedByThisRun"] = record["productFileAfterSha256"] == record["productFileBeforeSha256"]
    record["allArmsKilled"] = all(a["verdict"] == "KILLED" for a in record["arms"])
    record["allArmsIndependent"] = all(a["independent"] for a in record["arms"])
    record["invalidStackArms"] = [a["name"] for a in record["arms"] if a["verdict"] == "INVALID_STACK"]
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for arm in record["arms"]:
        print(
            f"{arm['verdict']:26s} independent={str(arm['independent']):5s} {arm['name']}  "
            f"anchor_hits={arm['anchor_hits']} bytes_changed={arm['bytes_changed']} restored_exact={arm['restored_exact']}"
        )
    print(
        f"allArmsKilled={record['allArmsKilled']} allArmsIndependent={record['allArmsIndependent']} "
        f"treeUnchanged={record['treeUnchangedByThisRun']}"
    )
    print(f"receipt={receipt_path}")
    return 0 if (record["allArmsKilled"] and record["allArmsIndependent"] and record["treeUnchangedByThisRun"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
