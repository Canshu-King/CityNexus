"""Kill evidence for ORD-0099: five sabotages, each owned by a named gate.

Run:  python review/mutate_ord99.py
Writes: D:/moodle/_qoder_ord30_evidence_20260920/ord99/kill-evidence.json

Every clause of the order is a claim that can be falsified, so each one is removed
individually: forward the internal code again (①), put the exception class name back on the
wire (②), call "answered, found nothing" a bad response (②' - the distinction the reason
vocabulary exists for), blame the provider for our own malformed label (②'' - the direction
of blame is the point), and drop the failure stage (③'s observability). Files are restored
from raw bytes and verified by SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

TREE = Path(r"D:\moodle\_qoder_integration_20260919")
RC = TREE / "backend" / "app" / "integrations" / "discovery" / "real_city.py"
TEST_FILE = "tests/test_qoder_city_failure_reasons.py"
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
OUT = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord99\kill-evidence.json")

FALLBACK_CALL = "                    candidates = geocoder.search(query, city=city_label, limit=limit)"
REASON_LINE = "                live_error = live_failure_reason(exc)"
NO_RESULTS = '                    "fallback_reason": live_error or PROVIDER_NO_RESULTS,'
LABEL_BRANCH = """    if isinstance(exc, ValueError) and "RESOLVER_LABEL_CARRIES_INTERNAL_CODE" in str(exc):
        return RESOLVER_LABEL_CARRIES_INTERNAL_CODE
"""
STAGE_KEY = '                    "failure_stage": failure_stage,'

MUTANTS = [
    {
        "name": "M1 the bounded fallback forwards the internal city code again",
        "old": FALLBACK_CALL,
        "new": "                    candidates = geocoder.search(query, city=journey.city_code, limit=limit)",
        "gate": "test_the_bounded_fallback_asks_with_the_same_label_as_the_anchor",
    },
    {
        "name": "M2 the exception class name goes back onto the response",
        "old": REASON_LINE,
        "new": "                live_error = type(exc).__name__",
        "gate": "test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at",
    },
    {
        "name": "M3 'answered but found nothing' is reported as a bad response",
        "old": NO_RESULTS,
        "new": '                    "fallback_reason": live_error or PROVIDER_BAD_RESPONSE,',
        "gate": "test_finding_nothing_is_not_reported_as_a_provider_failure",
        # both fallback branches carry the same line; mutate the live-unavailable one only
        "occurrence": 2,
    },
    {
        "name": "M4 our own malformed label is blamed on the provider",
        "old": LABEL_BRANCH,
        "new": "",
        "gate": "test_our_own_malformed_label_is_not_blamed_on_the_provider",
    },
    {
        "name": "M5 the failure stage stops being published",
        "old": STAGE_KEY,
        "new": '                    "failure_stage": None,',
        "gate": "test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at",
        # both fallback branches publish a stage; the generic-city one is the second
        "occurrence": 2,
    },
]


def run_gate(gate: str) -> tuple[int, str]:
    completed = subprocess.run(
        [str(PYTHON), "-m", "pytest", TEST_FILE, "-q", "--no-header", "-k", gate,
         "-p", "no:cacheprovider"],
        cwd=TREE / "backend",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.returncode, completed.stdout + completed.stderr


def mutate(text: str, old: str, new: str, occurrence: int) -> str | None:
    """Replace the Nth occurrence only, when the anchor is exactly that many."""
    hits = [i for i in range(len(text)) if text.startswith(old, i)]
    if len(hits) < occurrence:
        return None
    index = hits[occurrence - 1]
    return text[:index] + new + text[index + len(old) :]


def main() -> int:
    original = RC.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    text = original.decode("utf-8")
    results = []
    try:
        for mutant in MUTANTS:
            occurrence = mutant.get("occurrence", 1)
            hits = text.count(mutant["old"])
            mutated = mutate(text, mutant["old"], mutant["new"], occurrence)
            if mutated is None:
                results.append(
                    {"mutant": mutant["name"], "verdict": "NOT-MEASURED", "anchor_hits": hits}
                )
                continue
            RC.write_bytes(mutated.encode("utf-8"))
            code, output = run_gate(mutant["gate"])
            summary = [l for l in output.splitlines() if " passed" in l or " failed" in l]
            results.append(
                {
                    "mutant": mutant["name"],
                    "owner_gate": mutant["gate"],
                    "anchor_hits": hits,
                    "killed": code != 0,
                    "summary": summary[-1] if summary else output[-200:],
                }
            )
            RC.write_bytes(original)
    finally:
        RC.write_bytes(original)

    payload = {
        "restored": hashlib.sha256(RC.read_bytes()).hexdigest() == digest,
        "cases": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["restored"] and all(item.get("killed") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
