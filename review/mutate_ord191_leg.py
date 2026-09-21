"""Kill + cross-isolation evidence for the ORD-0191 5 / ORD-0197 destination leg.

Run:  python D:/moodle/_qoder_integration_20260919/review/mutate_ord191_leg.py
Writes: D:/moodle/_qoder_ord30_evidence_20260920/ord191/kill-evidence.json

The leg was rewired (ORD-0197 / arbiter 甲) to consume lane B's typed outcome instead of talking to
`PhotonGeocoder` itself, so the anchors below name the typed candidate fields.  Eleven sabotages in
two families.

Kills, each owned by one door measured green in this script before mounting:
* M6 un-wire the resolver call               -> g2 must fall back to red (the commander's own test)
* M7 treat any returned candidate as a match -> g6
* M8 launder a runtime failure into NO_MATCH -> g4
* M9 collapse a tie between two areas        -> g5
* M10 prefer the point marker over the area   -> g10

Cross-isolation, because `test_execution_truth_policy.md` @ f5afdcf9 says two node ids prove two
tests exist, not that two assertions are independent: every entry names the doors that must redden
**and** the doors that must stay green, so a shared code path cannot hide behind a passing count.

Files are restored from bytes and verified; nothing is committed from here.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

TREE = Path(r"D:\moodle\_qoder_integration_20260919")
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
CAPABILITY = TREE / "backend" / "app" / "anywhere_capability.py"
OUT = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord191\kill-evidence.json")
FILE = "tests/test_qoder_provider_identity_leg.py"

# --- anchors, each measured to hit exactly once in the file being sabotaged -----------------
LEG_CALL = "    provider = _provider_resolution(raw)\n"

EXACT_RETURN = '''    return [
        candidate
        for candidate in candidates
        if _normalise(getattr(candidate, "display_name", "") or "") == wanted
    ]
'''

BOUNDED_RETURN = '''    return str(getattr(candidate, "source_entity_id", "")).startswith("R:") and (
        len(getattr(candidate, "extent_wgs84", None) or ()) == 4
    )
'''

BOUNDED_INVERTED = '''    return (not str(getattr(candidate, "source_entity_id", "")).startswith("R:")) or (
        len(getattr(candidate, "extent_wgs84", None) or ()) != 4
    )
'''

AREAS_IF = "    if len(areas) == 1:\n"
AREAS_IF_BROKEN = "    if areas:\n        areas = areas[:1]  # sabotage: first bounded answer wins\n"

RUNTIME_TYPED = '''            method="provider_error",
            state="RUNTIME_FAILURE",
            reason_code=REASON_RESOLVER_UNAVAILABLE,
            retryable=True,
            resolver_attempted=True,
            resolver_status=status,
'''

RUNTIME_EXCEPT = RUNTIME_TYPED.replace("resolver_status=status", 'resolver_status="UNREACHABLE"')

NO_MATCH_RETURN = '''        method="provider_no_match",
        state="NO_MATCH",
'''

SEAM_GUARD = '''    seam = (name if name is not None else anywhere_resolver_name())
    return seam == "photon"
'''


def launder(block: str) -> str:
    return block.replace('state="RUNTIME_FAILURE"', 'state="NO_MATCH"')


MUTANTS = [
    {
        "name": "M6 the resolver call is un-wired (gate 1 must fall back to red)",
        "gates": ["test_g2_a_provider_named_county_becomes_hydratable_not_dead"],
        "old": LEG_CALL,
        "new": "    provider = None  # M6: the leg exists but is never consulted\n",
    },
    {
        "name": "M7 any provider candidate counts as the name",
        "gates": ["test_g6_a_fuzzy_near_match_is_not_an_identity"],
        "old": EXACT_RETURN,
        "new": "    return list(candidates)  # M7: a near match is treated as a resolution\n",
    },
    {
        "name": "M8 a transport failure becomes a structural NO_MATCH",
        "gates": ["test_g4_a_timeout_stays_a_named_runtime_failure_and_never_structural"],
        "old": RUNTIME_TYPED,
        "new": launder(RUNTIME_TYPED),
    },
    {
        "name": "M9 a tie between two bounded areas is collapsed anyway",
        "gates": ["test_g5_two_disagreeing_answers_must_not_pick_one"],
        "old": AREAS_IF,
        "new": AREAS_IF_BROKEN,
    },
    {
        "name": "M10 the point marker is preferred over the area it marks",
        "gates": ["test_g10_one_place_two_index_entries_collapses_under_a_named_version"],
        "old": BOUNDED_RETURN,
        "new": BOUNDED_INVERTED,
    },
]

CROSS = [
    {
        "name": "C1 typed runtime failure laundered into NO_MATCH touches nothing else",
        "old": RUNTIME_TYPED,
        "new": launder(RUNTIME_TYPED),
        # g9 owns "no digest, no placeholder, nothing in an identity column", which this sabotage
        # leaves true.  It is listed as expected-green on purpose: an earlier run claimed it as
        # expected-red and it stayed green, which was my mis-declaration and not a pass.
        "expect_red": ["test_g4_a_timeout_stays_a_named_runtime_failure_and_never_structural"],
        "expect_green": [
            "test_g2_a_provider_named_county_becomes_hydratable_not_dead",
            "test_g3_healthy_provider_with_no_answer_is_unavailable_and_invents_nothing",
            "test_g5_two_disagreeing_answers_must_not_pick_one",
            "test_g9_provider_leg_never_writes_a_digest_or_a_placeholder",
        ],
    },
    {
        "name": "C6 the seam-broke runtime site must not launder either",
        # The first run of this entry expected g4 to redden and it did not: g4 exercises a provider
        # that answered badly, while this branch is our own seam failing to start.  Nothing covered
        # that path, so the door (g11) was written and the expectation moved onto it.
        "old": RUNTIME_EXCEPT,
        "new": launder(RUNTIME_EXCEPT),
        "expect_red": ["test_g11_a_broken_seam_is_a_runtime_failure_too_not_a_verdict_about_the_world"],
        "expect_green": [
            "test_g2_a_provider_named_county_becomes_hydratable_not_dead",
            "test_g3_healthy_provider_with_no_answer_is_unavailable_and_invents_nothing",
            "test_g4_a_timeout_stays_a_named_runtime_failure_and_never_structural",
        ],
    },
    {
        "name": "C3 the mirror image: a healthy zero laundered into RUNTIME_FAILURE",
        "old": NO_MATCH_RETURN,
        "new": NO_MATCH_RETURN.replace('state="NO_MATCH"', 'state="RUNTIME_FAILURE"'),
        "expect_red": [
            "test_g3_healthy_provider_with_no_answer_is_unavailable_and_invents_nothing"
        ],
        "expect_green": [
            "test_g2_a_provider_named_county_becomes_hydratable_not_dead",
            "test_g4_a_timeout_stays_a_named_runtime_failure_and_never_structural",
            "test_g5_two_disagreeing_answers_must_not_pick_one",
        ],
    },
    {
        "name": "C2 accepting near matches must not disturb zero-candidate or tie handling",
        "old": EXACT_RETURN,
        "new": "    return list(candidates)  # C2: any returned candidate counts\n",
        "expect_red": ["test_g6_a_fuzzy_near_match_is_not_an_identity"],
        "expect_green": [
            "test_g3_healthy_provider_with_no_answer_is_unavailable_and_invents_nothing",
            "test_g4_a_timeout_stays_a_named_runtime_failure_and_never_structural",
            "test_g5_two_disagreeing_answers_must_not_pick_one",
        ],
    },
    {
        "name": "C4 preferring the point marker must not disturb the tie between two areas",
        "old": BOUNDED_RETURN,
        "new": BOUNDED_INVERTED,
        "expect_red": ["test_g10_one_place_two_index_entries_collapses_under_a_named_version"],
        "expect_green": [
            "test_g2_a_provider_named_county_becomes_hydratable_not_dead",
            "test_g3_healthy_provider_with_no_answer_is_unavailable_and_invents_nothing",
            "test_g5_two_disagreeing_answers_must_not_pick_one",
        ],
    },
    {
        "name": "C5 forcing the seam on must redden only the default-off doors",
        "old": SEAM_GUARD,
        "new": '    seam = (name if name is not None else anywhere_resolver_name())\n    return True  # C5: the switch is decorative\n',
        "expect_red": [
            "test_g1_default_off_still_answers_structurally_and_attempts_no_network",
            "test_g8_the_seam_is_read_per_call_and_defaults_off",
        ],
        "expect_green": [
            "test_g2_a_provider_named_county_becomes_hydratable_not_dead",
            "test_g4_a_timeout_stays_a_named_runtime_failure_and_never_structural",
        ],
    },
]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _run(gates: list[str]) -> tuple[int, str]:
    command = [
        str(PYTHON), "-m", "pytest", "-q", "--tb=line", "-p", "no:randomly",
        *[f"{FILE}::{gate}" for gate in gates],
    ]
    finished = subprocess.run(
        command, cwd=str(TREE / "backend"), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return finished.returncode, (finished.stdout or "") + (finished.stderr or "")


def _failed_node_ids(text: str) -> set[str]:
    return {
        line.split("::")[-1].split(" ")[0].strip()
        for line in text.splitlines()
        if line.startswith("FAILED") and "::" in line
    }


def main() -> int:
    original = CAPABILITY.read_bytes()
    text = original.decode("utf-8")
    for entry in MUTANTS + CROSS:
        hits = text.count(entry["old"])
        entry["anchor_hits"] = hits
        if hits != 1:
            print(f"FATAL: anchor hits = {hits} for {entry['old'][:60]!r}")
            return 1

    targets = sorted({gate for mutant in MUTANTS for gate in mutant["gates"]})
    code, out = _run(targets)
    print("kill baseline", code, out.strip().splitlines()[-1] if out.strip() else "")
    if code != 0:
        print("FATAL: a declared target is not green in this baseline; refusing to mount")
        return 1

    report = {"baseline_targets": targets, "mutants": [], "cross_isolation": []}
    problems = 0
    for mutant in MUTANTS:
        CAPABILITY.write_bytes(text.replace(mutant["old"], mutant["new"], 1).encode("utf-8"))
        code, out = _run(mutant["gates"])
        CAPABILITY.write_bytes(original)
        restored = _sha(CAPABILITY.read_bytes()) == _sha(original)
        verdict = "KILLED" if code != 0 else "SURVIVED"
        problems += 0 if verdict == "KILLED" else 1
        report["mutants"].append(
            {
                "name": mutant["name"],
                "gates": mutant["gates"],
                "anchor_hits": mutant["anchor_hits"],
                "returncode": code,
                "verdict": verdict,
                "restored": restored,
            }
        )
        print(f"{verdict:9s} {mutant['name']} rc={code} restored={restored}")
        if not restored:
            print("FATAL: byte restore failed")
            return 1

    doors = sorted({g for entry in CROSS for g in entry["expect_red"] + entry["expect_green"]})
    code, out = _run(doors)
    print("cross baseline", code, out.strip().splitlines()[-1] if out.strip() else "")
    if code != 0:
        print("FATAL: a cross-isolation door is not green in this baseline:", sorted(_failed_node_ids(out)))
        return 1
    report["cross_baseline"] = {"doors": doors, "returncode": code}

    for entry in CROSS:
        gates = sorted(set(entry["expect_red"] + entry["expect_green"]))
        CAPABILITY.write_bytes(text.replace(entry["old"], entry["new"], 1).encode("utf-8"))
        code, out = _run(gates)
        CAPABILITY.write_bytes(original)
        restored = _sha(CAPABILITY.read_bytes()) == _sha(original)
        failed = _failed_node_ids(out)
        missed = [gate for gate in entry["expect_red"] if gate not in failed]
        coupled = [gate for gate in entry["expect_green"] if gate in failed]
        verdict = "KILLED+ISOLATED" if (not missed and not coupled and restored) else "NOT_ISOLATED"
        problems += 0 if verdict == "KILLED+ISOLATED" else 1
        report["cross_isolation"].append(
            {
                "name": entry["name"],
                "anchor_hits": entry["anchor_hits"],
                "ran": gates,
                "failed": sorted(failed),
                "expected_red_missed": missed,
                "expected_green_went_red": coupled,
                "verdict": verdict,
                "restored": restored,
            }
        )
        print(f"{verdict:16s} {entry['name']} coupled={coupled} missed={missed}")
        if not restored:
            print("FATAL: byte restore failed")
            return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(
        f"{len(MUTANTS) - sum(1 for m in report['mutants'] if m['verdict'] != 'KILLED')}/"
        f"{len(MUTANTS)} killed; "
        f"{sum(1 for c in report['cross_isolation'] if c['verdict'] == 'KILLED+ISOLATED')}/"
        f"{len(CROSS)} cross-isolated; {problems} problem(s); evidence -> {OUT}"
    )
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
