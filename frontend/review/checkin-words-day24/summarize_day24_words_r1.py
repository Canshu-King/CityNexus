"""day24 打卡门新句 -- fold the per-arm readings into one table, so the block quotes computed rows.

Nothing is typed here: every count is summed out of the reading files the run wrote, and the judgement
("did the sentence reach the glass") is derived from the checks each arm recorded, not re-decided.
Arms that never produced a file are named `MISSING_ARM` rather than silently dropped from the denominator.
"""
import glob
import io
import json
import os
import time

READINGS = ("D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/checkin-words-day24/"
            "readings")
OUT = ("D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/checkin-words-day24/"
       "receipts/day24_words_summary_r1.json")
EXPECTED_STATES = ["duplicateAt", "duplicateNoMoment", "activityUnknown", "activityNotInJourney",
                   "placeUnknown", "targetRequired", "targetAmbiguous", "journeyInBin",
                   "journeyUnknown", "unexpected", "unreachable"]


def main():
    rows = []
    for name in sorted(os.listdir(READINGS)):
        if not name.endswith(".json") or name.startswith("report_"):
            continue
        with io.open(os.path.join(READINGS, name), encoding="utf-8") as handle:
            body = json.load(handle)
        checks = body.get("checks") or {}
        failed = sorted(k for k, v in checks.items() if v is False)
        rows.append({
            "file": name, "mode": body.get("mode"), "locale": body.get("locale"),
            "state": body.get("state"), "painted_notice": body.get("painted_notice"),
            "notices_count": body.get("notices_count"), "stop_tapped": body.get("stop_tapped"),
            "control_word_painted": body.get("control_word_painted"),
            "scan_visual_leaves": body.get("scan_visual_leaves"),
            "checks_total": len(checks), "checks_failed": failed,
            "png": name.replace(".json", ".png") if os.path.exists(
                os.path.join(READINGS, name.replace(".json", ".png"))) else "NO_PNG_IN_RUN",
        })

    covered = {}
    for row in rows:
        if row["mode"] == "fake":
            covered.setdefault(row["locale"], set()).add(row["state"])
    missing = {locale: sorted(set(EXPECTED_STATES) - got) for locale, got in covered.items()}
    for locale in ("zh-CN", "en"):
        if locale not in covered:
            missing[locale] = EXPECTED_STATES

    verdict = {
        "taken_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "readings_dir": READINGS,
        "states_expected_per_locale": len(EXPECTED_STATES),
        "reading_files": len(rows),
        "fake_arms": len([r for r in rows if r["mode"] == "fake"]),
        "real_arms": len([r for r in rows if r["mode"] == "real"]),
        "arms_with_a_failed_check": sorted(r["file"] for r in rows if r["checks_failed"]),
        "failed_check_names": sorted({c for r in rows for c in r["checks_failed"]}),
        "painted_equals_table_arms": len([r for r in rows if r["mode"] == "fake" and
                                          "painted_equals_the_tables_own_row" not in r["checks_failed"]]),
        "notices_never_more_than_one": all((r["notices_count"] or 0) <= 1 for r in rows),
        "every_reading_has_a_sentence_on_the_glass": all(
            bool(r["painted_notice"]) and len(str(r["painted_notice"])) > 8 for r in rows),
        "coverage_missing_states_by_locale": missing,
        "rows": rows,
        "painted_sentences": {("%s/%s" % (r["locale"], r["state"])): r["painted_notice"] for r in rows
                              if r["mode"] == "fake"},
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(verdict, handle, indent=1, ensure_ascii=False)
    printable = json.dumps(verdict, ensure_ascii=False).encode("ascii", "replace").decode("ascii")
    print(printable[:1600])
    print("WROTE %s bytes=%d" % (OUT, len(json.dumps(verdict, ensure_ascii=False).encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
