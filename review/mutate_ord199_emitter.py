"""ORD-0199 acceptance mutants: does the named gap carry its weight, and can it shield?

The order asked for two directions and I refuse to claim either by reading my own code:

    E1  delete the emitter's call            -> the naming door must go RED, and the two
                                                neighbours that speak about other things stay GREEN
    E2  widen the product's own allowlist to the fixture constant -> the named reason must
        disappear with the refusal, the ordinary-proposal door stays GREEN (the gap is not a
        shield), and the door that expects a refusal goes RED because the leg is now priced
    E3  keep the branch, drop the name        -> the naming door must go RED while the
                                                wording door stays GREEN: proof that the door
                                                reads the reason field, not the sentence

Every mutant is a byte-exact text replacement in `backend/app/main.py`, restored and SHA-verified
after each run, and each run is preceded by a baseline of the same node ids measured green on the
unmutated file - a "kill" against an already-red door proves nothing, and this ledger has that
mistake written up twice.

Deliberately NOT attempted, and named so it does not read as an oversight: the base family
(`MOBILITY_DATA_UNAVAILABLE` inside `details.reason_codes`) has no endpoint scenario today, because
in the demo world every stripped leg is frozen as `SYNTHETIC_DEFAULT` - a positively-named
ineligible fact, which is the new name's job. Producing "no fact at all" needs a strict capture that
fails, i.e. an unreachable provider; I did not fake one to widen the matrix. The boundary is instead
held by the unit door `test_ord199_a_leg_with_no_fact_at_all_is_not_called_ineligible`.

usage:  D:/moodle/CityNexus/.venv/Scripts/python.exe D:/moodle/_qoder_integration_20260919/review/mutate_ord199_emitter.py
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess

TREE = pathlib.Path(r"D:\moodle\_qoder_integration_20260919")
TARGET = TREE / "backend" / "app" / "main.py"
PY = pathlib.Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
DOORS = "tests/test_qoder_mobility_replan_endpoint.py"

NAMED = f"{DOORS}::test_ord199_a_leg_whose_only_number_is_the_fixture_constant_says_so"
NOFACT = f"{DOORS}::test_ord199_a_leg_with_no_fact_at_all_is_not_called_ineligible"
REVERSE = f"{DOORS}::test_ord199_the_named_gap_is_not_a_shield"
BASE_FAMILY = f"{DOORS}::test_replans_never_freezes_synthetic_default_as_hard_fact"

NAME_ANCHOR = '    reason_code = "MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE"\n'

MUTANTS = [
    {
        "id": "E1",
        "file": TARGET,
        "note": "the classification is computed and then thrown away - no reason is ever named",
        "find": "        raise MobilityEvidenceNotHardEligible(origin, destination, fact.fact_quality)\n",
        "replace": "        pass  # MUTANT E1: ineligible evidence is silently treated as missing\n",
        "expect_red": [NAMED],
        "expect_green": [REVERSE, NOFACT, BASE_FAMILY],
    },
    {
        "id": "E2",
        # ③ 的反向条件："把所有边标成 eligible ⇒ 这个 reason 必须不再出现"。第一次尝试只放宽了我
        # 这一层的判据，实测两条门照绿——因为真正的名单 `hard_minutes` 仍然拒收，候选还是被排除，
        # 那个突变其实只是 E3 的又一种写法。要造"全都合格"的世界，必须动产品自己那份 allowlist。
        "file": TREE / "backend" / "app" / "replanning" / "provider_snapshots.py",
        "note": "the fixture constant becomes hard-eligible - the named gap must vanish with it",
        "find": (
            "HARD_FEASIBLE_QUALITIES = frozenset({EXPLICIT_FROZEN_FIXTURE, LIVE_PROVIDER_CAPTURE})\n"
        ),
        "replace": (
            "HARD_FEASIBLE_QUALITIES = frozenset(  # MUTANT E2: everything is eligible\n"
            "    {EXPLICIT_FROZEN_FIXTURE, LIVE_PROVIDER_CAPTURE, SYNTHETIC_DEFAULT}\n"
            ")\n"
        ),
        "expect_red": [NAMED, BASE_FAMILY],
        "expect_green": [REVERSE, NOFACT],
    },
    {
        "id": "E3",
        "file": TARGET,
        "note": "the branch fires but carries the base name - the specific truth is lost",
        "find": NAME_ANCHOR,
        "replace": '    reason_code = "MOBILITY_DATA_UNAVAILABLE"  # MUTANT E3\n',
        "expect_red": [NAMED],
        "expect_green": [REVERSE, NOFACT, BASE_FAMILY],
    },
]


def _run(node_ids: list[str]) -> dict[str, str]:
    # verbose is required: `-q` suppresses the per-test PASSED lines this parser reads, which
    # makes a green door indistinguishable from one that was never collected.
    finished = subprocess.run(
        [str(PY), "-m", "pytest", "-v", "--no-header", "-p", "no:cacheprovider", *node_ids],
        cwd=str(TREE / "backend"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    outcome: dict[str, str] = {}
    for line in (finished.stdout or "").splitlines():
        for node in node_ids:
            name = node.split("::", 1)[1]
            if name not in line:
                continue
            tokens = line.split()
            for token in reversed(tokens):
                if token in {"PASSED", "FAILED", "ERROR", "XFAIL", "XPASS", "SKIPPED"}:
                    outcome[node] = token
                    break
    for node in node_ids:
        outcome.setdefault(node, "NOT-RUN")
    return outcome


def main() -> int:
    pristine: dict[pathlib.Path, bytes] = {}
    digests: dict[pathlib.Path, str] = {}
    problems: list[str] = []

    def source(path: pathlib.Path) -> str:
        if path not in pristine:
            pristine[path] = path.read_bytes()
            digests[path] = hashlib.sha256(pristine[path]).hexdigest()
        return pristine[path].decode("utf-8")

    nodes: list[str] = []
    for spec in MUTANTS:
        for node in spec["expect_red"] + spec["expect_green"]:
            if node not in nodes:
                nodes.append(node)
    baseline = _run(nodes)
    print("baseline (unmutated):")
    for node, state in baseline.items():
        print(f"   {state:8s} {node.split('::', 1)[1][:76]}")
    if any(state != "PASSED" for state in baseline.values()):
        print("FATAL: baseline is not green - a kill measured against a red door is not a kill")
        return 1

    results = []
    for spec in MUTANTS:
        path = spec["file"]
        text = source(path)
        hits = text.count(spec["find"])
        if hits != 1:
            problems.append(f"{spec['id']}: anchor hits = {hits} in {path.name}")
            continue
        path.write_bytes(text.replace(spec["find"], spec["replace"], 1).encode("utf-8"))
        try:
            outcome = _run(spec["expect_red"] + spec["expect_green"])
        finally:
            path.write_bytes(pristine[path])
        restored_ok = hashlib.sha256(path.read_bytes()).hexdigest() == digests[path]
        reddened = [node for node in spec["expect_red"] if outcome[node] != "PASSED"]
        survived = [node for node in spec["expect_red"] if outcome[node] == "PASSED"]
        collateral = [node for node in spec["expect_green"] if outcome[node] != "PASSED"]
        results.append(
            {
                "id": spec["id"],
                "file": path.name,
                "note": spec["note"],
                "killed": [node.split("::", 1)[1] for node in reddened],
                "survived": [node.split("::", 1)[1] for node in survived],
                "declared_green_held": not collateral,
                "collateral": [node.split("::", 1)[1] for node in collateral],
                "restored": restored_ok,
            }
        )
        print(
            f"{spec['id']} ({path.name}): killed {len(reddened)}/{len(spec['expect_red'])}"
            f" | survived {len(survived)} | declared greens held={not collateral}"
            f" | restored={restored_ok}"
        )
        for node in survived:
            print("    SURVIVED:", node.split("::", 1)[1])
        for node in collateral:
            print("    COLLATERAL (declared green went red):", node.split("::", 1)[1])

    all_restored = all(
        hashlib.sha256(path.read_bytes()).hexdigest() == digests[path] for path in digests
    )
    out = TREE / "review" / "mutate_ord199_emitter.evidence.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    bad = [
        spec["id"]
        for spec in results
        if spec["survived"] or not spec["declared_green_held"] or not spec["restored"]
    ] + problems
    print("files restored:", all_restored, "|", ", ".join(sorted(p.name for p in digests)))
    print("evidence ->", out)
    print("as declared:", "YES" if not bad else f"NO -> {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
