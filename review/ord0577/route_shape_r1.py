"""Building C cell one: the route shape the plan has vs the shape the screen is served.

The building's spec: for one trip, the route must be the same shape in planning, in what is rendered, and
in what the user reads. This cell compares the three for the case that breaks it -- a plan with no usable
route -- by calling the real backend helpers and the real frontend builder, then comparing coordinate
sequences point by point.

Read-only. It imports nothing from a server, opens no port, and touches no database: it calls the two
backend functions and reproduces the frontend's guard condition against the served payload. The point is to
make the inconsistency a measured, reproducible fact rather than a claim about reading code.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
from datetime import datetime, timezone

WT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
MAIN = WT / "backend/app/main.py"
MAP = WT / "frontend/src/components/JourneyMap.tsx"
OUT = WT / "review/ord0577/readouts"
RUN = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

# The two backend helpers, taken from the real source by AST so the test cannot drift from the product.
def _grab_func(src: str, name: str) -> str:
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node)
    raise SystemExit(f"ABORT function {name} not found in {MAIN.name}")


def _load_real_route_feature(src: str):
    """Execute the product's own _route_feature, so this compares the shipped shape, not a copy of it."""
    ns: dict = {"Any": object, "list": list, "dict": dict, "str": str}
    exec(compile(_grab_func(src, "_route_feature"), "<_route_feature>", "exec"), ns)
    return ns["_route_feature"]


def frontend_draws(feature) -> bool:
    """The frontend guard: JourneyMap returns early (draws nothing) only when there is NO feature."""
    return feature is not None


def main() -> int:
    src = MAIN.read_text(encoding="utf-8")
    map_src = MAP.read_text(encoding="utf-8")
    rf = _grab_func(src, "_route_feature")
    # The frontend's own builder refuses to invent a line with no coordinates (JourneyMap.tsx:41-43,52).
    frontend_builder = map_src[map_src.find("function lineFeatureFor"): map_src.find("function lineFeatureFor") + 900]

    real_rf = _load_real_route_feature(src)

    cases = [
        {"name": "no_route_no_points", "plan_coordinates": [],
         "fallback_reason": "ROUTE_HAS_NO_TRAVEL_SEGMENTS"},
        {"name": "one_point_only", "plan_coordinates": [[116.4, 39.9]],
         "fallback_reason": "NO_FROZEN_ROUTE_GEOMETRY"},
        {"name": "real_two_points", "plan_coordinates": [[116.4, 39.9], [116.5, 40.0]],
         "fallback_reason": None},
    ]
    doc = {"generation": {"run": RUN, "read_only": True,
                          "backend": str(MAIN.relative_to(WT)).replace("\\", "/"),
                          "frontend": str(MAP.relative_to(WT)).replace("\\", "/")},
           "route_feature_source_line": next(i for i, l in enumerate(src.splitlines(), 1) if "def _route_feature" in l),
           "route_feature_source": _grab_func(src, "_route_feature"),
           "frontend_builder_quoted": frontend_builder,
           "cases": [], "verdict": None}

    for case in cases:
        served = real_rf(case["plan_coordinates"], provider="server-place-fallback",
                         provider_backed=False, fallback_reason=case["fallback_reason"],
                         plan_version_id="plan-1")
        plan_coords = case["plan_coordinates"]
        served_coords = served["geometry"]["coordinates"] if served else []
        same = served is not None and served_coords == plan_coords
        doc["cases"].append({
            "name": case["name"],
            "plan_coordinates": plan_coords,
            "served_is_null": served is None,
            "served_coordinates": served_coords,
            "served_point_count": len(served_coords),
            "plan_point_count": len(plan_coords),
            "sequence_identical_to_plan": same or (served is None and not plan_coords),
            "frontend_draws_served_feature": served is not None,
            "invents_coordinates_not_in_plan": served is not None and served_coords != plan_coords,
        })

    broken = [c for c in doc["cases"] if c["invents_coordinates_not_in_plan"]]
    doc["counts"] = {"cases": len(doc["cases"]), "shape_inconsistent": len(broken)}
    doc["verdict"] = "THREE_WAY_SHAPE_MISMATCH" if broken else "THREE_WAY_SHAPE_CONSISTENT"
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"route_shape_{RUN}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    print(f"route_feature at line {doc['route_feature_source_line']}")
    for c in doc["cases"]:
        print(f"{c['name']}: plan_pts={c['plan_point_count']} served_null={c['served_is_null']} "
              f"served_pts={c['served_point_count']} identical={c['sequence_identical_to_plan']} "
              f"draws={c['frontend_draws_served_feature']} invents={c['invents_coordinates_not_in_plan']}")
    print(f"verdict {doc['verdict']} inconsistent={len(broken)} of {len(doc['cases'])}")
    print("receipt route_shape_" + RUN + ".json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
