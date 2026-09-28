"""ORD-0402 tail: build the artifact the byte-comparison arm reads instead of shelling out to git.

The arm's job is unchanged: prove `list_journeys` moved by zero bytes since the baseline tip.
What changes is where the baseline text comes from - the commander runs the suite on a
`git archive` export with no `.git`, so an arm that calls `git show` cannot answer there.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TREE = REPO
BASELINE_TIP = "8f4ddfa9feffe4233b48cbf608caf8e1bbb76291"
START = '@app.get("/api/v1/journeys", response_model=list[JourneySchema])'
END = '@app.delete("/api/v1/journeys/{journey_id}", status_code=204)'
OUT = TREE / "review/ord0402-readouts/LIST_DOOR_BASELINE_r2.json"


def journey_function(text: str) -> str:
    return text[text.index(START) : text.index(END)]


def git(*args: str) -> str:
    out = subprocess.run(
        ["git", "-c", "http.proxy=", "-c", "https.proxy=", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        cwd=str(REPO),
    )
    return out.stdout


def main() -> None:
    tip = sys.argv[1] if len(sys.argv) > 1 else BASELINE_TIP
    baseline_text = git("show", f"{tip}:backend/app/main.py")
    baseline_blob = git("rev-parse", f"{tip}:backend/app/main.py").strip()
    segment = journey_function(baseline_text)

    working = (TREE / "backend/app/main.py").read_text("utf-8")
    current = journey_function(working)

    payload = {
        "what": "list_journeys, byte for byte, as it stood at the baseline tip",
        "baseline_tip": tip,
        "baseline_main_py_blob": baseline_blob,
        "source_file": "backend/app/main.py",
        "extractor": "the text between the two decorators named in marker_start / marker_end",
        "marker_start": START,
        "marker_end": END,
        "segment_bytes": len(segment.encode("utf-8")),
        "segment_sha256": hashlib.sha256(segment.encode("utf-8")).hexdigest(),
        "segment_lf": segment.replace("\r\n", "\n"),
        "how_to_regenerate": (
            "python review/ord0402-readouts/make_list_door_baseline_artifact_r1.py <tip40> "
            "- run it from a checkout that has .git; it refuses to write unless the segment it "
            "extracts is byte-equal to the segment in the tree the arm reads"
        ),
        "measured": {
            "current_segment_bytes": len(current.encode("utf-8")),
            "current_segment_sha256": hashlib.sha256(current.encode("utf-8")).hexdigest(),
            "equal_to_baseline": current == segment,
            "tree_under_test": str(TREE) + " at cbb6f160b60316895c20713fcfb277f363781161",
        },
    }
    assert payload["measured"]["equal_to_baseline"], (
        "the door already moved between the baseline and this tree - writing this artifact would "
        "turn the arm into a record of the change it is meant to refuse"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8", newline="\n")
    print(
        json.dumps(
            {
                "artifact": str(OUT),
                "segment_bytes": payload["segment_bytes"],
                "segment_sha256": payload["segment_sha256"],
                "baseline_main_py_blob": baseline_blob,
                "artifact_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
