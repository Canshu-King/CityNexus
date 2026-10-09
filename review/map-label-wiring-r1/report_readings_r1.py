#!/usr/bin/env python3
"""ORD-0415 readings summariser -- recompute the two numbers this order asks for out of the evidence.

Nothing here types a count. Every number is read from the JSON the gate wrote while it ran, so the
figure in the delivery block and the figure in the artefact cannot drift apart, and so a re-run of
this script against a new evidence directory produces a new number rather than repeating an old one.

    python review/map-label-wiring-r1/report_readings_r1.py --tag before
    python review/map-label-wiring-r1/report_readings_r1.py --tag after
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTEFACTS = ROOT.parent / "evidence"
OUT = ROOT / "review" / "map-label-wiring-r1" / "readings"


def load(tag: str) -> dict:
    base = ARTEFACTS / tag / "ord0415-wiring"
    if not base.exists():
        raise SystemExit(f"no evidence directory for tag {tag!r}: {base}")
    readings = {}
    for path in sorted(base.glob("reading_*.json")):
        readings[path.name[len("reading_"): -len(".json")]] = json.loads(path.read_text(encoding="utf-8"))
    provenance = sorted((ARTEFACTS / tag).glob("provenance_*.json"))
    summaries = sorted((ARTEFACTS / tag).glob("run_summary_*.json"))
    if not readings:
        raise SystemExit(f"tag {tag!r} produced no reading_*.json under {base}")
    return {
        "readings": readings,
        "provenance": json.loads(provenance[-1].read_text(encoding="utf-8")) if provenance else None,
        "run_summary": json.loads(summaries[-1].read_text(encoding="utf-8")) if summaries else None,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", required=True)
    args = parser.parse_args(argv)
    bundle = load(args.tag)
    readings = bundle["readings"]

    glass = readings.get("glass-carries-no-class", {})
    pins = readings.get("whole-word-stops-keep-pin", {})
    fixture = readings.get("fixture-lands-in-payload", {})
    applied = readings.get("fixture-applied", {})
    attribution = readings.get("attribution-still-reads", {})

    offenders = glass.get("offenders", [])
    # 处 = one rendered string on the glass that carries at least one forbidden class. The same string
    # carrying two classes is still one place where a traveller reads something the rule forbids, so the
    # per-class tally is reported separately rather than folded into this count. Two tallies, because the
    # gate writes two judges: `span_classes` is as wide as the cut, `accepted_classes` is the list the
    # four accepted gates judge with, and they disagree on `duration` on a Chinese word.
    def tally(key: str) -> dict:
        counts: dict[str, int] = {}
        for entry in offenders:
            for name in entry.get(key, []):
                counts[name] = counts.get(name, 0) + 1
        return counts

    per_class = tally("span_classes")
    per_class_accepted = tally("accepted_classes")

    summary = {
        "tag": args.tag,
        "head": (bundle["provenance"] or {}).get("head"),
        "head_subject": (bundle["provenance"] or {}).get("head_subject"),
        "watched_blobs": (bundle["provenance"] or {}).get("watched_blobs"),
        # The bytes the run actually served. `watched_blobs` is what HEAD claims, and in the
        # before-run the two differ deliberately: the render files were checked out to the authority
        # line while the instrument itself stayed at HEAD.
        "watched_worktree_blobs": (bundle["provenance"] or {}).get("watched_worktree_blobs"),
        "dirty_files": (bundle["provenance"] or {}).get("dirty_files"),
        "database": (bundle["provenance"] or {}).get("database"),
        "python": (bundle["provenance"] or {}).get("python"),
        "python_version": (bundle["provenance"] or {}).get("python_version"),
        "node_version": (bundle["provenance"] or {}).get("node_version"),
        "exit_code": (bundle["run_summary"] or {}).get("exit_code"),
        "fixture_landed_cases": sum(1 for row in fixture.get("cases_in_payload", []) if row.get("in_payload")),
        "fixture_renamed": applied.get("renamed"),
        "rendered_chip_count": glass.get("rendered_chips"),
        "judged_string_count": glass.get("judged_string_count"),
        "forbidden_rendered_hits": glass.get("rendered_strings_with_forbidden_class", len(offenders)),
        "forbidden_rendered_hits_by_class": per_class,
        "forbidden_rendered_hits_by_accepted_class": per_class_accepted,
        "rendered_strings_with_accepted_class": glass.get("rendered_strings_with_accepted_class"),
        "rendered_chip_texts": glass.get("rendered_chip_texts"),
        "pin_arias": glass.get("pin_arias"),
        "offender_texts": [entry.get("text") for entry in offenders],
        "offender_classes": [{"text": e.get("text"), "span": e.get("span_classes"), "accepted": e.get("accepted_classes")} for e in offenders],
        "cut_words_on_glass": glass.get("cut_words_on_glass"),
        "clean_control_on_glass": glass.get("clean_control_on_glass"),
        "rule_fired_on": glass.get("rule_fired_on"),
        "no_chip_for_the_clock": pins.get("no_chip_for_the_clock"),
        # "hiding a word is not deleting a stop" needs its own denominator: how many pins the screen
        # really painted, and which of them are still buttons without a rendered word beside them.
        "pin_count": pins.get("pin_count"),
        "chip_node_count": glass.get("chip_nodes"),
        "pins_still_buttons_without_a_word": [
            row.get("painted") for row in pins.get("pins_without_a_rendered_word") or []
            if row.get("role") == "button" and row.get("rendered") is True
        ],
        "pins_announcing_a_forbidden_class": len(pins.get("pins_announcing_a_forbidden_class", [])),
        "attribution_rendered": attribution.get("rendered"),
        "attribution_text": attribution.get("on_screen"),
        "attribution_matches_authored_arm": attribution.get("matches_authored_arm"),
        "attribution_box": attribution.get("box"),
        "attribution_violations_if_fed": attribution.get("violations_if_it_were_judged"),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"{args.tag}.json"
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"written {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
