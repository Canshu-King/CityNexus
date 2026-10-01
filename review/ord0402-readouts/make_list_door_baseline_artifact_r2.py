"""ORD-0477: re-record the `list_journeys` byte pin, without rewriting the record it replaces.

ORD-0402's arm `test_the_existing_list_door_was_not_touched_down_to_its_bytes` pins this door to the
bytes it had at `8f4ddfa9feffe4233b48cbf608caf8e1bbb76291`, and it is right to: that order was told not
to change one word of it.  ORD-0477 changed words -- deliberately, by command -- so the pin has to move
or the suite stays red for a change the commander ordered.

Two rules this generator keeps, and `make_list_door_baseline_artifact_r1.py` keeps them too:

* it reads no git.  The suite is also run on `git archive` exports with no `.git`, where a `git show`
  dies with rc 128 and reports the environment instead of the door.  The pre-ORD-0477 bytes are taken
  from r2's own `segment_lf`, which is why r2 stays in the tree untouched;
* it refuses to write unless the pre-tier segment it recovered from r2 is byte-equal to what r2 says it
  is (`segment_sha256`), and unless the post-tier segment it records is the one in this tree.  A record
  that could be produced from hand-edited JSON would not be a record of anything.

usage: python make_list_door_baseline_artifact_r2.py     (run from the tree whose arm will read it)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

TREE = Path(__file__).resolve().parents[2]
R2 = TREE / "review/ord0402-readouts/LIST_DOOR_BASELINE_r2.json"
OUT = TREE / "review/ord0402-readouts/LIST_DOOR_BASELINE_r3.json"
SOURCE = "backend/app/main.py"

# what the door looked like before this order, and what it looks like now.  Both markers are literal
# text in `backend/app/main.py`: a reformatted decorator is exactly the thing this pin exists to catch,
# so it is allowed to break loudly rather than to match loosely.
PRE_TIER_START = '@app.get("/api/v1/journeys", response_model=list[JourneySchema])'
START = '@app.get(\n    "/api/v1/journeys",\n    response_model=list[JourneySchema],'
END = '@app.delete("/api/v1/journeys/{journey_id}", status_code=204)'
TIER_TIP = "be0ffee216c7d24e48652427d290da848a9195cf"


def segment(text: str, start: str) -> str:
    return text[text.index(start) : text.index(END)]


def main() -> int:
    previous = json.loads(R2.read_text(encoding="utf-8"))
    pre_tier = previous["segment_lf"]
    recorded_hash = hashlib.sha256(pre_tier.encode("utf-8")).hexdigest()
    if recorded_hash != previous["segment_sha256"]:
        raise SystemExit(
            f"REFUSE: r2's segment_lf no longer hashes to its own segment_sha256 "
            f"({recorded_hash[:12]} != {previous['segment_sha256'][:12]}) - r2 was edited, not read"
        )

    live = (TREE / SOURCE).read_text(encoding="utf-8").replace("\r\n", "\n")
    current = segment(live, START)
    pre_in_tree = PRE_TIER_START in live

    payload = {
        "what": "list_journeys, byte for byte, as ORD-0477 left it on top of the tier tip",
        "supersedes": R2.name,
        "superseded_by": "ORD-0477 (the trip list takes a named `sort` tier)",
        "why_this_moved": (
            "ORD-0402 pinned this door because its own order was told to change nothing here. "
            "ORD-0477 was told to change the order the door answers in, so the decorator gained a "
            "`responses` block naming the refusal and the function gained a `sort` parameter. "
            "The rows the door lists and the shape of each row are not part of that change, and the "
            "same arm keeps judging them below the byte comparison."
        ),
        "baseline_tip": TIER_TIP,
        "pre_tier_main_py_blob": previous["baseline_main_py_blob"],
        "pre_tier_tip": previous["baseline_tip"],
        "pre_tier_segment_bytes": previous["segment_bytes"],
        "pre_tier_segment_sha256": previous["segment_sha256"],
        "source_file": SOURCE,
        "extractor": "the text from marker_start up to marker_end",
        "marker_start": START,
        "marker_end": END,
        "segment_bytes": len(current.encode("utf-8")),
        "segment_sha256": hashlib.sha256(current.encode("utf-8")).hexdigest(),
        "segment_lf": current,
        "how_to_regenerate": (
            "python review/ord0402-readouts/make_list_door_baseline_artifact_r2.py - run it from the "
            "tree whose arm reads this file; it reads no git, and it refuses unless r2's own segment "
            "still hashes to r2's own recorded hash"
        ),
        "measured": {
            "pre_tier_marker_still_in_this_tree": pre_in_tree,
            "post_tier_segment_bytes": len(current.encode("utf-8")),
            "post_tier_segment_sha256": hashlib.sha256(current.encode("utf-8")).hexdigest(),
            "changed_from_pre_tier": current != pre_tier,
        },
    }
    if payload["measured"]["changed_from_pre_tier"] is not True:
        raise SystemExit("REFUSE: the door did not move, so there is nothing to re-record")
    if pre_in_tree:
        raise SystemExit(
            "REFUSE: the pre-ORD-0477 decorator is still in the tree, so this record would describe a "
            "door that is not the one being shipped"
        )

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8", newline="\n")
    print(
        json.dumps(
            {
                "artifact": str(OUT),
                "segment_bytes": payload["segment_bytes"],
                "segment_sha256": payload["segment_sha256"],
                "pre_tier_segment_sha256": payload["pre_tier_segment_sha256"],
                "artifact_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
