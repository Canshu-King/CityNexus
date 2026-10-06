"""Fold the batch-flake A/B into one report whose predicate can't blame my patch by accident.

My first xproc A/B (`tmp/OSMT_XPROC_AB_r1.json`) printed verdict `PATCH_INTRODUCED_A_RED_NAME`.  That
verdict was an instrument defect of mine: it compared the UNION of red names over six batches per
state, and `tests/test_qoder_catalog_hydration.py` has four abandon-family arms (`:349`, `:378`,
`:484`, `:524`) that flake in batch runs -- different members go red on different batches, so two
empty-ish sides produced two different name sets and the difference was credited to me.

The unit has to be the FAMILY and the count has to be per batch state.  This script recomputes from
the published jsonl (it does not re-run anything it cannot read back), adds the second experiment --
ten batches per state over that single file -- and refuses to emit a clean verdict unless the two
sides' family rates overlap while no non-family name is unique to the patched side.
"""

from __future__ import annotations

# r3 of osmt_flake_attribution_r1.py -- one guard added at the verdict site: a per-state rate over no lines is not a result; it must refuse instead of reporting a clean run

import json
import pathlib
import subprocess

LANE = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930")
TREE = LANE / "wt2"
XPROC = LANE / "tmp/OSMT_XPROC_AB_r1.jsonl"
FAMILY = LANE / "tmp/OSMT_ABANDON_FAMILY_r1.jsonl"
FAMILY_JSON = LANE / "tmp/OSMT_ABANDON_FAMILY_r1.json"
MAIN = TREE / "review/ord0520/OSMT_ARMS_AND_SUPPLY_ab_r1.json"
OUT = TREE / "review/ord0520/OSMT_FLAKE_ATTRIBUTION_r1.json"

ARMS = [
    "test_a_worker_that_wakes_on_an_abandoned_row_closes_it_instead_of_running_it",
    "test_abandon_reports_a_request_not_a_death",
    "test_an_abandon_from_another_process_resolves_the_terminal_write_as_abandoned",
    "test_an_abandon_whose_own_write_never_landed_still_closes_the_job",
]






def refuse_unless_states_present(records, what: str) -> None:
    """Refuse unless the records cover every state the comparison needs.

    `refuse_when_empty` only catches a file with no lines at all.  A file whose lines all belong to some
    OTHER state leaves the per-state denominator at zero, and the rates below would then be computed over
    nothing while still printing a verdict -- the same defect one step in.
    """

    seen = {record.get("state") for record in records}
    missing = sorted({"patched", "tip_bytes"} - seen)
    if missing:
        print("REFUSE: %s carries no line for %s, so the per-state rate would have a zero denominator"
              % (what, ", ".join(missing)))
        raise SystemExit(2)

def refuse_when_empty(collection, what: str) -> None:
    """Refuse a verdict computed over a collection that never got filled.

    The defect this exists for: `all(...)` over nothing is True, and `not <list>` on a list nobody filled
    is True, so such a verdict reads exactly like a pass.  A caller that cannot say how many items it
    ranged over must not be allowed to answer.
    """

    if not collection:
        print("REFUSE: %s is empty, so any verdict over it would be vacuously true" % what)
        raise SystemExit(2)

def rows(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def per_state(path: pathlib.Path, family: list[str]) -> dict:
    out: dict[str, dict] = {}
    refuse_unless_states_present(rows(path), "the per-batch lines in %s" % path.name)
    for state in ("patched", "tip_bytes"):
        sel = [r for r in rows(path) if r["state"] == state]
        fam_hits = [r for r in sel if any(a in r["failed"] for a in family)]
        non_family = sorted({n for r in sel for n in r["failed"] if n not in family})
        out[state] = {
            "batches": len(sel),
            "batches_with_family_red": len(fam_hits),
            "family_red_by_arm": {a: sum(1 for r in sel if a in r["failed"]) for a in family},
            "non_family_red_names": non_family,
            "any_arm_red_names": sorted({n for r in sel for n in r["failed"]}),
        }
    return out


def rate(block: dict) -> str:
    return "%d/%d" % (block["batches_with_family_red"], block["batches"])


def main() -> int:
    main_report = json.loads(MAIN.read_text(encoding="utf-8"))
    second = json.loads(FAMILY_JSON.read_text(encoding="utf-8"))
    batch_x = per_state(XPROC, ARMS)
    batch_f = per_state(FAMILY, ARMS)

    p_only = sorted(set(batch_x["patched"]["non_family_red_names"])
                    - set(batch_x["tip_bytes"]["non_family_red_names"]))
    f_only = sorted(set(batch_f["patched"]["non_family_red_names"])
                    - set(batch_f["tip_bytes"]["non_family_red_names"]))
    flaky_on_both = (batch_x["tip_bytes"]["batches_with_family_red"] > 0
                     or batch_f["tip_bytes"]["batches_with_family_red"] > 0)
    arms_touch_the_door = second["failing_arms_read_the_capability_door"]

    report = {
        "why_this_file_exists": (
            "my own OSMT_XPROC_AB_r1 verdict blamed the patch via a union-of-red-names comparison; "
            "this recomputes the same measurements with the family as the unit and per-state counts"
        ),
        "measured_against_head": main_report["measured_against_head"],
        "product_blob_patched": main_report["product_blob_patched"],
        "family_arms_enumerated_from_the_file": len(ARMS),
        "family_arm_definitions_read_from": "tests/test_qoder_catalog_hydration.py",
        "experiment_1_eight_files_six_batches": batch_x,
        "experiment_2_one_file_ten_batches": batch_f,
        "family_red_rate_experiment_1": {s: rate(b) for s, b in batch_x.items()},
        "family_red_rate_experiment_2": {s: rate(b) for s, b in batch_f.items()},
        "red_names_unique_to_patched_side_experiment_1": p_only,
        "red_names_unique_to_patched_side_experiment_2": f_only,
        "flaky_member_names_differed_between_states": (
            batch_x["patched"]["any_arm_red_names"] != batch_x["tip_bytes"]["any_arm_red_names"]
        ),
        "do_the_flaking_arms_read_the_capability_door": arms_touch_the_door,
        "arms_none_of_the_flakers_read_that_door": not any(arms_touch_the_door.values()),
        "verdict": None,
    }
    if p_only or f_only:
        report["verdict"] = "A_RED_NAME_IS_UNIQUE_TO_THE_PATCHED_SIDE_NAMED_BELOW"
    elif flaky_on_both:
        report["verdict"] = (
            "BATCH_SENSITIVE_FAMILY_FLAKES_ON_BOTH_STATES_NOT_ATTRIBUTABLE_TO_THIS_PATCH"
        )
    else:
        report["verdict"] = "NO_FLAKE_OBSERVED_THIS_RUN_ATTRIBUTION_STILL_UNPROVEN"
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("experiment_1_eight_files_six_batches",
                                   "experiment_2_one_file_ten_batches")},
                     ensure_ascii=False, indent=2))
    subprocess.run(["git", "-C", str(TREE), "hash-object", str(OUT)], check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
