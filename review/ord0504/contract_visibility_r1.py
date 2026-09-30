"""ORD-0504 -- can the contract see the money this screen reads?  Read out of the yaml, not assumed.

The face renders four classes of price. This probe asks the hand-written contract, for the two doors
the face actually calls, which of those fields it describes -- by walking the parsed 200 schema and
listing every field path it names.

What it prints is the basis for the order's one ruling request: the amounts are real, they are on the
wire, and the contract describes none of them. `contracts/openapi.yaml` gives `/experience` a partial
property tree that stops at `active_plan.activities` and never mentions `legs`, and gives `/wallet` a
bare `{type: object}`. So a client generated from the contract knows nothing about any of the four
price classes this screen reads, and `frontend/src/generated/api.ts` cannot be the place a reviewer
goes to check what the page is allowed to show.

    /d/moodle/CityNexus/.venv/Scripts/python.exe review/ord0504/contract_visibility_r1.py
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import yaml

TREE = Path("D:/moodle/_qoder_r_ord0465_20260929/wt")
OUT = TREE / "review" / "ord0504" / "contract_visibility_r1.json"

#: The fields this screen reads, by the name the server sends them under.
SPEND_FIELDS = [
    "active_plan.legs[].cost_amount_minor",
    "active_plan.legs[].cost_status",
    "active_plan.legs[].currency",
    "options[].stay_total_minor",
    "reservations[].price",
    "commitments[].monetary_value",
]

DOORS = {
    "experience": "/journeys/{journey_id}/experience",
    "wallet": "/journeys/{journey_id}/wallet",
}


def paths_of(node, prefix="$") -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        if "properties" in node and isinstance(node["properties"], dict):
            for key, child in node["properties"].items():
                found.append(f"{prefix}.{key}")
                found.extend(paths_of(child, f"{prefix}.{key}"))
        if "items" in node:
            found.extend(paths_of(node["items"], prefix))
    return found


def main() -> int:
    document = yaml.safe_load(io.open(TREE / "contracts" / "openapi.yaml", encoding="utf-8"))
    report: dict[str, object] = {"contract_paths": len(document["paths"])}
    described: list[str] = []
    for door, path in DOORS.items():
        schema = document["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        names = paths_of(schema)
        described.extend(names)
        report[door] = {
            "200_schema_is_bare_object": names == [],
            "described_field_paths": len(names),
        }
    # A field counts as described only if some path in the contract ends with its own name.
    report["spend_fields_this_screen_reads"] = {
        field: any(field.split("[].")[-1].split(".")[-1] in name for name in described)
        for field in SPEND_FIELDS
    }
    report["described_count"] = len(described)
    report["verdict"] = (
        "NONE_OF_THE_SPEND_FIELDS_ARE_IN_THE_CONTRACT"
        if not any(report["spend_fields_this_screen_reads"].values())
        else "PARTIALLY_DESCRIBED"
    )
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
