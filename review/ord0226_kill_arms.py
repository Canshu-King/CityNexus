"""ORD-0226 acceptance run: three arms through `live_checks/mutation_anchor_guard.py`.

Order is fixed by the order: one green baseline, then one arm at a time, and a **fresh green
baseline before every arm** -- a red baseline would let any mutant "kill" the node for unrelated
reasons.  Every arm is measured on the same node, in the same whole-file-free shape (single node),
and the product file is restored by the guard's `finally`, whose own sha check raises on mismatch;
we re-hash after the context exits so `restored_exact` is a reading, not a promise.

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
NODE = "ord0220-1-the-tight-caveat-cannot-contradict-itself"
RECEIPT = ROOT / "review/evidence/ui-overnight/ord0226-arms.json"
PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"

FROZEN = '  "按这个预算，住宿、交通和吃饭很可能超出计划。可以先调整预算，或你确认继续也可以。";\n'

ARMS = [
    (
        "killAC1-e1-reassurance-outside-any-word-table",
        '  "按这个预算，住宿、交通和吃饭很可能超出计划。可以先调整预算，或你确认继续也可以。不过别担心，肯定够用";\n',
        "the red team's E1 arm verbatim: 别担心/肯定够 are not in ALLAY_WORDS, so only literal equality can catch it",
    ),
    (
        "killAC2-e2-the-caveat-denies-itself",
        '  "这个预算不会超出计划，你可以放心调整。";\n',
        "arm E2's shape: the caveat stops warning and tells the traveller to relax",
    ),
    (
        "killAC3-selftest-one-punctuation-mark",
        '  "按这个预算，住宿、交通和吃饭很可能超出计划。可以先调整预算，或你确认继续也可以，";\n',
        "acceptance 5: one full stop becomes one comma -- green here would mean the equality is not literal",
    ),
]


def digest() -> str:
    return sha256(PRODUCT.read_bytes()).hexdigest()


def run(label: str, port: int) -> dict:
    """One node, one throwaway stack.  run_spec.py prints `exit=` and its own log path."""
    cmd = [PYTHON, str(ROOT / "review/run_spec.py"), SPEC, str(port), "--grep", NODE]
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
            if NODE in line and ("frozen sentence" in line or "contradicts" in line or "no risk" in line):
                owner = " ".join(line.split())
                break
        lines: list[str] = []
        if log and Path(log).exists():
            lines = Path(log).read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines):
            if line.strip().startswith("Error:") and NODE in line:
                block = "\n".join(item.strip()[:220] for item in lines[index : index + 4])
                break
    print(
        f"[{label}] exit={proc.returncode} run_id={run_id} {round(time.time() - started)}s "
        f"summary={summary!r}",
        flush=True,
    )
    return {
        "label": label,
        "command": " ".join(cmd[:3]) + f" {port} --grep {NODE}",
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
    if source.count(FROZEN) != 1:
        print("ABORT: the frozen caveat line is not a single, unique occurrence in the product file")
        return 2

    tag = sys.argv[1] if len(sys.argv) > 1 else ""
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 4620
    receipt_path = RECEIPT.with_name(f"ord0226-arms{'-' + tag if tag else ''}.json")
    record = {
        "generatedBy": "e345b9d6",
        "order": "ORD-0226",
        "runTag": tag or "first",
        "fix": "A -- the tight caveat is a frozen literal in the product, and the gate asserts string equality",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "guard": "live_checks/mutation_anchor_guard.py :: temporary_guarded_replace",
        "node": NODE,
        "spec": SPEC,
        "runShape": "single node (--grep on the exact node id) against an authoritative throwaway stack",
        "productFileBeforeSha256": digest(),
        "arms": [],
    }

    for name, mutant, why in ARMS:
        print(f"\n=== {name} ===", flush=True)
        baseline = run("baseline-before-arm", port)
        port += 1
        before = digest()
        with temporary_guarded_replace(PRODUCT, FROZEN.encode(), mutant.encode(), expected_hits=1) as receipt:
            mutated = receipt.mutated_sha256
            attempt = run("mutated-arm", port)
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
                "verdict": (
                    "KILLED"
                    if attempt["exitCode"] != 0 and baseline["exitCode"] == 0
                    else "SURVIVED"
                    if attempt["exitCode"] == 0
                    else "BASELINE_RED -- arm not measured"
                ),
            }
        )

    record["productFileAfterSha256"] = digest()
    record["treeUnchangedByThisRun"] = record["productFileAfterSha256"] == record["productFileBeforeSha256"]
    record["allArmsKilled"] = all(a["verdict"] == "KILLED" for a in record["arms"])
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for arm in record["arms"]:
        print(f"{arm['verdict']:26s} {arm['name']}  anchor_hits={arm['anchor_hits']} bytes_changed={arm['bytes_changed']} restored_exact={arm['restored_exact']}")
    print(f"allArmsKilled={record['allArmsKilled']} treeUnchanged={record['treeUnchangedByThisRun']}")
    print(f"receipt={receipt_path}")
    return 0 if record["allArmsKilled"] and record["treeUnchangedByThisRun"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
