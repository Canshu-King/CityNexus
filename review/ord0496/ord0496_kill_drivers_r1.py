"""ORD-0496 - the kill campaign for the calendar door: every clause of the order has a line whose
removal must turn a named arm red.

Why this file exists: the order says 删掉那一行转义/校验必须变红, and a green suite by itself cannot
tell a guard apart from a decoration.  Each entry below deletes or re-points exactly one thing the
exporter does -- an escape pair, the octet budget, the offset rule, the row-derived stamp, the bin
predicate, the CRLF constant, the trailing-space migration, the trim, the invented-location
temptation, the ordering column, and the read authority itself -- runs the module, and records which
arms went red by name.

Nothing here is a mock: the product source is edited in place, the same test module is run against
it, and the original bytes are written back and re-hashed, so the tree this receipt describes is the
tree that ships.

Run it with the project interpreter from the backend directory::

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0496/ord0496_kill_drivers_r1.py
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
MODULE = "tests/test_qoder_ord0496_calendar_export.py"
PRODUCT = BACKEND / "app/calendar_export.py"
DOOR = BACKEND / "app/main.py"
RECEIPT = pathlib.Path(
    sys.argv[1]
    if len(sys.argv) > 1
    else ROOT / "review/ord0496/ord0496_kill_receipt_r1.json"
)

MUTATIONS: list[dict] = [
    {
        "id": "M1a_escape_semicolon",
        "file": PRODUCT,
        "claim": "RFC 5545 3.3.11 escapes a semicolon inside a value",
        "old": '        .replace(";", "\\\\;")\n',
        "new": "",
        "expect_red": ["test_comma_semicolon_backslash_and_newline_are_escaped_and_survive_the_round_trip"],
    },
    {
        "id": "M1b_escape_comma",
        "file": PRODUCT,
        "claim": "RFC 5545 3.3.11 escapes a comma inside a value",
        "old": '        .replace(",", "\\\\,")\n',
        "new": "",
        "expect_red": ["test_comma_semicolon_backslash_and_newline_are_escaped_and_survive_the_round_trip"],
    },
    {
        "id": "M2_no_folding_at_all",
        "file": PRODUCT,
        "claim": "a physical line never exceeds 75 octets",
        "old": "        if current and current_octets + size > budget:",
        "new": "        if False and current and current_octets + size > budget:",
        "expect_red": ["test_no_physical_line_exceeds_seventy_five_octets_and_unfolding_restores_every_value"],
    },
    {
        "id": "M3_naive_time_accepted_as_a_clock",
        "file": PRODUCT,
        "claim": "a timestamp without its own UTC offset is not a printable instant",
        "old": "    if parsed.tzinfo is None:\n        return None\n",
        "new": "",
        "expect_red": ["test_an_activity_without_a_usable_clock_is_skipped_and_counted_never_silently_lost"],
    },
    {
        "id": "M4_dtstamp_from_the_request_clock",
        "file": PRODUCT,
        "claim": "DTSTAMP is the row's own moment, never the instant of the request",
        "old": "        stamp = _usable_clock(activity.stamp_at)",
        "new": "        stamp = datetime.now(timezone.utc)",
        "expect_red": ["test_two_exports_are_the_same_bytes_and_moving_the_rows_moment_moves_the_stamp"],
    },
    {
        "id": "M5_recycle_bin_predicate_off",
        "file": DOOR,
        "claim": "a binned trip is refused by name instead of exporting",
        # anchored on the raise that follows, because that guard line alone appears four times in
        # this module -- a mutation driver that edits the wrong one of four is worse than no driver.
        "old": "    if journey.deleted_at is not None:\n"
               "        raise _share_refusal(\n"
               "            409,\n"
               '            "This trip is in the recycle bin. 找回 it before exporting its calendar.",\n',
        "new": "    if False and journey.deleted_at is not None:\n"
               "        raise _share_refusal(\n"
               "            409,\n"
               '            "This trip is in the recycle bin. 找回 it before exporting its calendar.",\n',
        "expect_red": ["test_a_trip_in_the_recycle_bin_is_refused_by_name_and_not_as_an_empty_calendar"],
    },
    {
        "id": "M6_line_terminator_is_lf",
        "file": PRODUCT,
        "claim": "3.1 makes CRLF the only line terminator",
        "old": 'CRLF = "\\r\\n"',
        "new": 'CRLF = "\\n"',
        "expect_red": ["test_every_line_ends_with_crlf_and_the_object_carries_no_bare_line_feed"],
    },
    {
        "id": "M7_fold_may_end_at_a_space",
        "file": PRODUCT,
        "claim": "unfolding deletes CRLF plus one space, so a line must not end at a space",
        "old": "            ended = current\n            moved = \"\"\n"
               '            while ended and (ended.endswith(" ") or ended.endswith("\\t")):\n'
               "                moved = ended[-1] + moved\n"
               "                ended = ended[:-1]\n",
        "new": '            ended = current\n            moved = ""\n',
        "expect_red": ["test_a_fold_never_eats_the_space_it_breaks_at_and_a_value_keeps_its_edges"],
    },
    {
        "id": "M8_value_edges_not_trimmed_and_not_counted",
        "file": PRODUCT,
        "claim": "a value cannot carry an edge space, so it is trimmed and the trim is reported",
        "old": "        trimmed = _trim_value(escaped)",
        "new": "        trimmed = escaped",
        "expect_red": ["test_a_fold_never_eats_the_space_it_breaks_at_and_a_value_keeps_its_edges"],
    },
    {
        "id": "M9_location_invented_from_the_title",
        "file": DOOR,
        "claim": "a row with no place emits no LOCATION rather than a made-up one",
        "old": "            location=names.get(row.place_id) if row.place_id else None,",
        "new": "            location=names.get(row.place_id) or str(row.title),",
        "expect_red": ["test_a_multi_day_trip_exports_one_vevent_per_clocked_activity_in_the_plants_own_order"],
    },
    {
        "id": "M10_order_by_the_start_at_string",
        "file": DOOR,
        "claim": "the plan's own sequence_no is the order; a string sort of mixed offsets is not",
        # anchored with the where-line above it: `.order_by(Activity.sequence_no, Activity.id)` alone
        # appears twice in this module.
        "old": "        select(Activity)\n"
               "        .where(Activity.plan_version_id == plan_version_id)\n"
               "        .order_by(Activity.sequence_no, Activity.id)\n",
        "new": "        select(Activity)\n"
               "        .where(Activity.plan_version_id == plan_version_id)\n"
               "        .order_by(Activity.start_at, Activity.id)\n",
        "expect_red": ["test_a_multi_day_trip_exports_one_vevent_per_clocked_activity_in_the_plants_own_order"],
    },
    {
        "id": "M11_second_read_authority",
        "file": DOOR,
        "claim": "the 404 is the read door's own answer, not a rebuilt one",
        "old": '        journey = require(session, Journey, journey_id, "Journey")',
        "new": '        journey = session.get(Journey, journey_id)\n'
               "        if journey is None:\n"
               '            raise HTTPException(404, f"Trip {journey_id} was not found")',
        "expect_red": ["test_an_unknown_trip_gets_the_read_authoritys_own_404_plus_the_name"],
    },
]


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: pathlib.Path) -> str:
    """Line-ending-normalised read, so one anchor works on an LF file and on a CRLF one.

    Measured need, not tidiness: `backend/app/main.py` is LF at my base and CRLF on the current
    authoritative tip (CR bytes 0 -> 13,362 across those commits), so a driver that matched raw
    bytes would report `anchor_occurrences = 0` for its own shape and read that as a verdict.
    Restoring is always done from the original bytes, so the file's own ending comes back intact.
    """

    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def _write(path: pathlib.Path, text: str, eol: str = "\n") -> None:
    """Write the mutated text with the ending that file already used -- never os.linesep."""

    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace("\n", eol))


def _eol(raw: bytes) -> str:
    return "\r\n" if b"\r\n" in raw else "\n"


def _run_module() -> dict:
    environment = dict(os.environ)
    environment.pop("DEEPSEEK_API_KEY", None)
    finished = subprocess.run(
        [
            sys.executable, "-m", "pytest", MODULE, "-p", "no:randomly", "-q", "--no-header",
            "-o", "console_output_style=classic",
        ],
        cwd=BACKEND,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    names = sorted(
        line.split("::", 1)[1].split(" ")[0]
        for line in finished.stdout.splitlines()
        if line.startswith("FAILED ")
    )
    summary = [
        line for line in finished.stdout.splitlines()
        if ("passed" in line or "error" in line) and "=====" not in line
    ][-1:]
    return {"rc": finished.returncode, "red_arms": names, "summary": summary}


def main() -> int:
    originals = {path: path.read_bytes() for path in (PRODUCT, DOOR)}
    digests_before = {str(path): _digest(path) for path in originals}
    clean_before = _run_module()

    results: list[dict] = []
    for mutation in MUTATIONS:
        path = mutation["file"]
        text = _read(path)
        occurrences = text.count(mutation["old"])
        if occurrences != 1:
            results.append({**{k: mutation[k] for k in ("id", "claim")},
                            "applied": False,
                            "anchor_occurrences": occurrences})
            continue
        _write(path, text.replace(mutation["old"], mutation["new"], 1), _eol(originals[path]))
        try:
            answer = _run_module()
        finally:
            path.write_bytes(originals[path])
        restored = _digest(path) == digests_before[str(path)]
        results.append(
            {
                "id": mutation["id"],
                "claim": mutation["claim"],
                "file": path.name,
                "file_line_ending": _eol(originals[path]),
                "applied": True,
                "anchor_occurrences": occurrences,
                "restored_byte_identical": restored,
                "rc_after_mutation": answer["rc"],
                "red_arms": answer["red_arms"],
                "red_arm_count": len(answer["red_arms"]),
                "summary_after_mutation": answer["summary"],
                "predicted_red_arm": mutation["expect_red"],
                "prediction_covered": all(
                    name in answer["red_arms"] for name in mutation["expect_red"]
                ),
            }
        )

    clean_after = _run_module()
    digests_after = {str(path): _digest(path) for path in originals}
    receipt = {
        "order": "ORD-0496 slice 1",
        "interpreter": sys.executable,
        "pytest_command": f"{sys.executable} -m pytest {MODULE} -p no:randomly -q --no-header",
        "cwd": str(BACKEND),
        "module_denylisted_env": ["DEEPSEEK_API_KEY"],
        "clean_run_before": clean_before,
        "clean_run_after_restore": clean_after,
        "mutations": results,
        "mutations_attempted": len(MUTATIONS),
        "mutations_applied": sum(1 for item in results if item.get("applied")),
        "mutations_that_turned_a_named_arm_red": sum(
            1 for item in results if item.get("applied") and item["red_arm_count"] > 0
        ),
        "predictions_covered": sum(
            1 for item in results if item.get("applied") and item["prediction_covered"]
        ),
        "product_bytes_restored_identically": digests_before == digests_after,
        "digests_before": digests_before,
        "digests_after": digests_after,
        "note": (
            "a mutation that reddens MORE arms than predicted is still a kill -- the prediction "
            "column says the arm the order named is among them, not that nothing else moved"
        ),
    }
    _write(RECEIPT, json.dumps(receipt, indent=2, ensure_ascii=False))
    print(f"receipt={RECEIPT}")
    for item in receipt["mutations"]:
        print(
            f"{item['id']:44s} applied={item.get('applied')} "
            f"red={item.get('red_arm_count')} covered={item.get('prediction_covered')} "
            f"restored={item.get('restored_byte_identical')}"
        )
    print(
        f"clean_before={clean_before['summary']} clean_after={clean_after['summary']} "
        f"restored_identically={receipt['product_bytes_restored_identically']}"
    )
    failed = (
        clean_before["rc"] != 0
        or clean_after["rc"] != 0
        or receipt["mutations_applied"] != len(MUTATIONS)
        or not all(item.get("prediction_covered") for item in results)
        or not receipt["product_bytes_restored_identically"]
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
