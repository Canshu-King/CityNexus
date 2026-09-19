#!/usr/bin/env python3
"""Repository-owned catastrophic mutation campaign (EXTENDED truth gate).

Idea: a test that passes with the fix removed is not evidence of the fix.  This
script applies one deliberate defect at a time to the shipped source, runs the
convergence suites that are supposed to notice it, restores the file, and reports
killed / survived.

It is deliberately *not* part of the normal gate: it edits source files and costs one
test run per sabotage.  Run it before an integration freeze and before a release
candidate, alongside `backend/tests/stateful`.

A survivor is only acceptable if it is listed in EXPECTED_SURVIVORS with the reason it
cannot be reached.  An unlisted survivor fails the campaign (the suite missed a
catastrophe), and a listed survivor that has started dying also fails, so the allowlist
cannot rot into a place where real gaps go to be forgotten.

    python tools/verification/mutation_campaign.py
    python tools/verification/mutation_campaign.py --only B E A
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

SUITES = [
    "tests/test_sol_execution_cursor.py",
    "tests/test_sol_concurrency_and_remap.py",
    "tests/test_sol_migration_truth.py",
    "tests/test_sol_plan_handover.py",
    "tests/test_sol_guardian_projection.py",
    "tests/test_rx1_cross_journey_trigger_gate.py",
    "tests/test_rx2_mock_hard_laundering_gate.py",
    "tests/test_rx3_stale_cursor_fails_closed.py",
    "tests/stateful",
]


# The stateful machine found the orphan-ACTIVE defect only at freeze scale; a
# campaign running it at 12x12 would report kills it cannot actually deliver.
ENV = {
    **os.environ,
    "DEEPSEEK_API_KEY": "",
    "CITYNEXUS_AI_API_KEY": "",
    "CITYNEXUS_AI_ENABLED": "false",
    "CITYNEXUS_STATEFUL_CASES": "60",
    "CITYNEXUS_STATEFUL_STEPS": "30",
}


@dataclass
class Sabotage:
    key: str
    label: str
    source: str
    original: str
    replacement: str
    # A mutant is expected to survive only when the shipped product cannot reach it.
    expected_survivor_reason: str | None = None


@dataclass
class Campaign:
    results: list[tuple[str, str]] = field(default_factory=list)



SABOTAGES = [
    Sabotage(
        key="A",
        label="a stale execution cursor falls back like an absent one",
        source="backend/app/operations/v9.py",
        original="""    elif stale_cursor:
        current_index = len(activities)""",
        replacement="""    elif stale_cursor:
        current_index = next(
            (index for index, item in enumerate(activities) if item.status not in terminal),
            len(activities),
        )""",
    ),
    Sabotage(
        key="B",
        label="the Journey-scoped write lock becomes a no-op",
        source="backend/app/concurrency_guards.py",
        original="""    key = str(journey_id)
    with _registry_guard:
        lock = _journey_locks.get(key)
        if lock is None:
            lock = RLock()
            _journey_locks[key] = lock
    with lock:
        yield""",
        replacement="    yield  # SABOTAGE",
    ),
    Sabotage(
        key="E",
        label="a capture stops re-anchoring its commitment",
        source="backend/app/commerce/service_impl.py",
        original="        _remap_commitment_to_active_plan(session, commitment)",
        replacement="        pass  # SABOTAGE",
    ),
    Sabotage(
        key="A1",
        label="a same-key conflict stops replaying the durable receipt",
        source="backend/app/main.py",
        original="""    except HTTPException as exc:
        if exc.status_code != 409:
            raise
        replayed = _replay_committed_accept(session, scoped_key, signature, wait=True)
        if replayed is not None:
            return replayed
        raise""",
        replacement="""    except HTTPException:
        raise  # SABOTAGE""",
    ),
    Sabotage(
        key="G1",
        label="the duplicate-ACTIVE migration picks the newest row again",
        source="backend/app/db/session.py",
        original="""        if pointer_id not in active_ids:
            raise RuntimeError(""",
        replacement="""        if False:
            raise RuntimeError(""",
    ),
    Sabotage(
        key="G2",
        label="selecting a new plan stops retiring the plan being abandoned",
        source="backend/app/main.py",
        original="""        retired = session.execute(
            update(PlanVersion)
            .where(PlanVersion.id == abandoned_id, PlanVersion.status == "ACTIVE")
            .values(status="SUPERSEDED")
        )""",
        replacement="""        # SABOTAGE: the old plan is abandoned still-ACTIVE, and the guard below is
        # satisfied so nothing complains about it.
        retired = type("Rowcount", (), {"rowcount": 1})()""",
    ),
    Sabotage(
        key="F1",
        label="the resolver picks the first of many candidates instead of AMBIGUOUS",
        source="backend/app/replanning/commitment_remap.py",
        original="""    if len(matches) > 1:
        raise RemapConflict(
            f"{subject} remap is AMBIGUOUS on the active Journey plan "
            f"({len(matches)} candidates carry the same identity)",
            matched=len(matches),
        )""",
        replacement="""    if len(matches) > 1:
        return matches[0]""",
    ),
    Sabotage(
        key="F2",
        label="the resolver returns nothing instead of failing on zero matches",
        source="backend/app/replanning/commitment_remap.py",
        original="""    raise RemapConflict(
        f"{subject} cannot be attached to the active Journey plan",
        matched=0,
    )""",
        replacement="    return None  # SABOTAGE",
    ),
    Sabotage(
        key="F3",
        label="commitment identity falls back to suffix similarity",
        source="backend/app/replanning/commitment_remap.py",
        original="        if identity.strong & candidate_strong:",
        replacement="""        if identity.strong & candidate_strong or any(
            candidate.endswith(term)
            for candidate in candidate_strong | candidate_generic
            for term in identity.strong | identity.generic
            if term
        ):""",
    ),
    Sabotage(
        key="F4",
        label="the scheduled instant stops being part of the anchor",
        source="backend/app/replanning/commitment_remap.py",
        original="""        if not _same_instant(identity.scheduled_at, moment):
            continue""",
        replacement="""        if False:
            continue""",
    ),
    Sabotage(
        key="RX1",
        label="the replan trigger stops checking which Journey owns the event",
        source="backend/app/main.py",
        original="""    if trigger_event is None or trigger_event.journey_id != journey.id:
        raise HTTPException(422, "trigger event is not on this journey")""",
        replacement="""    if trigger_event is None:
        raise HTTPException(422, "trigger event is not on this journey")""",
    ),
    Sabotage(
        key="RX2",
        label="a hard mobility capture is allowed to fall back to the mock",
        source="backend/app/integrations/mobility/runtime.py",
        original="            fallback=None if hard_capture else mock,",
        replacement="            fallback=mock,",
    ),
    Sabotage(
        key="F",
        label="an unresolvable C4 is skipped instead of failing the acceptance",
        source="backend/app/main.py",
        original="""            if protected:""",
        replacement="""            if False:""",
        expected_survivor_reason=(
            "Not reachable through the public endpoint.  Dropping the committed "
            "activity from a proposed plan is refused earlier by the feasibility gate "
            "with LOCKED_COMMITMENT_LOST, and duplicating it is refused with "
            "ACTIVITY_OVERLAP, so no legal acceptance reaches this branch.  It is "
            "retained as defence in depth, and the 0 / 1 / many counting it depends on "
            "is asserted directly against resolve_commitment_target()."
        ),
    ),
]


def run_suite(python: str) -> tuple[int, list[str], str]:
    result = subprocess.run(
        [python, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", *SUITES],
        cwd=REPO / "backend",
        env=ENV,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    failed = sorted(
        {
            line.split("::")[-1].split(" ")[0]
            for line in result.stdout.splitlines()
            if line.startswith("FAILED")
        }
    )
    summary = [
        line for line in result.stdout.splitlines() if " passed" in line or " failed" in line
    ]
    return result.returncode, failed, (summary[-1] if summary else result.stdout[-400:])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*", help="run a subset of sabotage keys")
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="python that can import the app (default: this interpreter)",
    )
    args = parser.parse_args()

    selected = [
        item for item in SABOTAGES if not args.only or item.key in args.only
    ]

    code, failed, summary = run_suite(args.python)
    print(f"baseline (no sabotage): {summary}")
    if code != 0:
        print(f"refusing to mutate a red suite: {failed}")
        return 1

    problems: list[str] = []
    campaign = Campaign()
    for sabotage in selected:
        path = REPO / sabotage.source
        # Bytes, not text: write_text translates LF to the platform newline, so a
        # campaign that restores a file by rewriting it would leave every line of the
        # checkout changed.  Verification must not touch what it is verifying.
        original_text = path.read_bytes().decode("utf-8")
        if sabotage.original not in original_text:
            print(f"!! {sabotage.key}: anchor not found in {sabotage.source}; skipping")
            problems.append(f"{sabotage.key} anchor missing")
            continue
        try:
            path.write_bytes(
                original_text.replace(sabotage.original, sabotage.replacement, 1).encode("utf-8")
            )
            code, failed, summary = run_suite(args.python)
            verdict = "KILLED" if code else "SURVIVED"
            campaign.results.append((sabotage.key, verdict))
            detail = summary if code == 0 else f"{summary} -> {failed}"
            print(f"{sabotage.key:>3} {verdict:<8} {sabotage.label}: {detail}")
            if code == 0 and not sabotage.expected_survivor_reason:
                problems.append(f"{sabotage.key} survived without being declared")
            if code != 0 and sabotage.expected_survivor_reason:
                problems.append(
                    f"{sabotage.key} was declared unreachable but is now killed; "
                    "prune it from EXPECTED_SURVIVORS"
                )
        finally:
            path.write_bytes(original_text.encode("utf-8"))

    print("\n--- EXPECTED_SURVIVORS ---")
    for sabotage in selected:
        if sabotage.expected_survivor_reason:
            print(f"{sabotage.key}: {sabotage.label}\n    {sabotage.expected_survivor_reason}")

    killed = sum(1 for _key, verdict in campaign.results if verdict == "KILLED")
    survived = sum(1 for _key, verdict in campaign.results if verdict == "SURVIVED")
    print(f"\ncampaign: {killed} killed / {survived} survived / {len(selected)} attempted")
    if problems:
        print("CAMPAIGN FAILED:")
        for problem in problems:
            print("  -", problem)
        return 1
    print("CAMPAIGN PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
