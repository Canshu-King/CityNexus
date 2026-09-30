"""ORD-0477: does the re-recorded `list_journeys` byte pin still bite?

The pin was moved onto ORD-0477's own bytes, so the question has to be answered by measurement rather
than by assurance: put the door's *pre-tier* segment -- the bytes ORD-0402 recorded, read out of that
record -- back into `main.py`, and the arm must go red.  A pin that stays green while the door is
swapped back to the previous generation is a pin that guards nothing.

Runs in the full-tree snap (`ord0477full`), because the arm reads
`review/ord0402-readouts/LIST_DOOR_BASELINE_r3.json` and a sparse export has no `review/`.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

FULL = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/ord0477full")
VENV_PY = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
SOURCE = FULL / "backend/app/main.py"
R2 = FULL / "review/ord0402-readouts/LIST_DOOR_BASELINE_r2.json"
R3 = FULL / "review/ord0402-readouts/LIST_DOOR_BASELINE_r3.json"
REPORT = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/run/ord0477_pin_mutant_r1.txt")
NL = chr(10)
START = '@app.get(' + NL + '    "/api/v1/journeys",' + NL + '    response_model=list[JourneySchema],'
END = '@app.delete("/api/v1/journeys/{journey_id}", status_code=204)'


def slice_of(text: str) -> tuple[int, int]:
    return text.index(START), text.index(END)


def main() -> int:
    original = SOURCE.read_text(encoding="utf-8")
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    pre_tier = json.loads(R2.read_text(encoding="utf-8"))["segment_lf"]
    post_tier = json.loads(R3.read_text(encoding="utf-8"))["segment_lf"]
    start, end = slice_of(original)
    assert original[start:end] == post_tier, "the tree's segment is not what r3 recorded"

    swapped = original[:start] + pre_tier + original[end:]
    SOURCE.write_text(swapped, encoding="utf-8", newline=NL)
    print("swapped in the pre-tier segment:", len(pre_tier), "chars, was", end - start)
    try:
        run = subprocess.run(
            [VENV_PY, "-m", "pytest", "tests/test_qoder_ord0402_recycle_bin.py", "-q", "-p", "no:cacheprovider"],
            cwd=str(FULL / "backend"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    finally:
        SOURCE.write_text(original, encoding="utf-8", newline=NL)
    restored = hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before
    lines = [
        "mutant=list_journeys_bytes_reverted_to_ORD-0402_record",
        "pytest_rc=%d" % run.returncode,
        "source_restored=%s sha_before=%s sha_after=%s" % (restored, before[:12], hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:12]),
        "pre_tier_segment_chars=%d post_tier_segment_chars=%d" % (len(pre_tier), len(post_tier)),
        "",
        (run.stdout or "")[-2500:],
    ]
    REPORT.write_text(NL.join(lines), encoding="utf-8")
    tail = [ln for ln in run.stdout.splitlines() if "passed" in ln or "failed" in ln or "Error" in ln][-5:]
    sys.stdout.buffer.write(("RC=%s restored=%s" % (run.returncode, restored) + NL + NL.join(tail) + NL).encode("utf-8", "replace"))
    return 0 if (run.returncode != 0 and restored) else 4


if __name__ == "__main__":
    sys.exit(main())
