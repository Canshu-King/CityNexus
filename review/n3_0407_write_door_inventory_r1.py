"""ORD-0407 cell 1-3: does a door to "add an activity location" exist at all?

The order allows two answers -- open a real control, or name NOT_AVAILABLE.  Only the
second one is falsifiable without a screen, so this instrument prints the whole
inventory the claim would have to survive: every write operation the contract declares,
every write call the shipped frontend makes, every place in the backend that inserts an
Activity row, and for each frontend door the request-schema fields it carries.

Read-only.  Runs from the repo root:
    python review/n3_0407_write_door_inventory_r1.py --out review/evidence/x.json
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "openapi.yaml"
SRC = ROOT / "frontend" / "src"
GENERATED = SRC / "generated"

# A door is a candidate for "add an activity location" if it writes, is reachable from
# the shipped frontend, and its payload can name a place (coordinates or a place/title).
PLACE_FIELDS = {
    "latitude",
    "longitude",
    "lat",
    "lng",
    "place_id",
    "place_name",
    "address",
    "location",
    "coordinates",
    "title",
    "name",
    "activity",
    "activities",
}
WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")


def contract_ops() -> dict[str, dict[str, object]]:
    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    schemas = spec.get("components", {}).get("schemas", {})
    out: dict[str, dict[str, object]] = {}
    for path, item in spec["paths"].items():
        for verb, op in item.items():
            if verb not in ("get", "post", "put", "patch", "delete"):
                continue
            fields: list[str] = []
            try:
                schema = op["requestBody"]["content"]["application/json"]["schema"]
                fields = resolve_fields(schema, schemas)
            except KeyError:
                pass
            out[f"{verb.upper()} {path}"] = {
                "path": path,
                "verb": verb.upper(),
                "operationId": op.get("operationId"),
                "request_fields": fields,
            }
    return out


def resolve_fields(schema: object, schemas: dict[str, dict[str, object]], depth: int = 0) -> list[str]:
    """Property names reachable from a request schema, following $ref one level deep."""
    if depth > 2 or not isinstance(schema, dict):
        return []
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return resolve_fields(schemas.get(name, {}), schemas, depth + 1)
    names: list[str] = []
    for key in ("properties",):
        for prop, sub in (schema.get(key) or {}).items():
            names.append(prop)
            names.extend(resolve_fields(sub, schemas, depth + 1))
    for combo in ("allOf", "anyOf", "oneOf"):
        for sub in schema.get(combo) or []:
            names.extend(resolve_fields(sub, schemas, depth + 1))
    if isinstance(schema.get("items"), dict):
        names.extend(resolve_fields(schema["items"], schemas, depth + 1))
    return sorted(set(names))


def frontend_write_calls() -> list[dict[str, object]]:
    """Every fetch()/request()/requestJson()/v8Request() call that names a write method."""
    calls: list[dict[str, object]] = []
    call_re = re.compile(r"\b(fetch|request|requestJson|v8Request|apiRequest)\s*(<[^>]*>)?\(")
    method_re = re.compile(r'method:\s*"(POST|PUT|PATCH|DELETE)"')
    for file in sorted(SRC.rglob("*.ts")) + sorted(SRC.rglob("*.tsx")):
        if GENERATED in file.parents or file.name in {"generated"}:
            continue
        text = file.read_text(encoding="utf-8")
        lines = text.splitlines()
        for m in method_re.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            # Walk back to the opening paren of the enclosing call, then forward for the
            # first template/literal argument inside it.
            start = max(0, m.start() - 900)
            window_before = text[start : m.start()]
            opened = list(call_re.finditer(window_before))
            if not opened:
                continue
            call = opened[-1]
            tail = text[m.start() : m.start() + 500]
            path_expr = window_before[call.end() :].lstrip()
            first_arg = path_expr.split(",")[0].split(")")[0].strip()
            url = re.sub(r"\$\{[^}]*\}", "{p}", first_arg).strip("\"'`")
            if not url.startswith("/"):
                url = re.sub(r"^.*?(/api/v1)?/", "/", url)
            url = "/journeys/{p}" + url.split("/journeys", 1)[-1] if "journeys" in url else url
            calls.append(
                {
                    "file": str(file.relative_to(ROOT)).replace("\\", "/"),
                    "line": line_no,
                    "method": m.group(1),
                    "url": url,
                    "context": lines[line_no - 1].strip()[:120],
                }
            )
    return calls


def activity_row_creators() -> list[dict[str, object]]:
    """Where the backend writes the word `Activity(`, split into the two things that word means.

    The first version of this function counted `class Activity(BaseModel)` as a place a row is made,
    which is wrong twice over: a class declaration inserts nothing, and mixing it in made the total
    (8) unreadable as "how many places create activity rows" (4).
    """
    out: list[dict[str, object]] = []
    for file in sorted((ROOT / "backend" / "app").rglob("*.py")):
        text = file.read_text(encoding="utf-8")
        lines = text.splitlines()
        for idx, line in enumerate(lines):
            if not re.search(r"\bActivity\(", line):
                continue
            kind = "class_declaration" if line.strip().startswith("class ") else "row_insert_point"
            ln = idx + 1
            route, fn = None, None
            for back in range(idx, max(-1, idx - 400), -1):
                s = lines[back]
                if fn is None and re.match(r"^(async )?def \w+", s):
                    fn = f"{file.name}:{back + 1} {s.strip()[:70]}"
                if fn and s.strip().startswith(("@app.", "@router.")):
                    route = f"{file.name}:{back + 1} {s.strip()[:90]}"
                    break
            out.append(
                {
                    "file": str(file.relative_to(ROOT)).replace("\\", "/"),
                    "line": ln,
                    "kind": kind,
                    "enclosing_function": fn,
                    "nearest_route_decorator_above": route,
                }
            )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--sha", default="")
    args = ap.parse_args()

    ops = contract_ops()
    write_ops = {k: v for k, v in ops.items() if v["verb"] in WRITE_METHODS}
    calls = frontend_write_calls()

    activity_paths = sorted(
        k
        for k in write_ops
        if "/activities" in k or re.search(r"/activit", k)
    )
    # A door that could *create* an activity addresses the collection, not one row of it.
    creation_paths = sorted(k for k in write_ops if re.search(r"/activities$", k))
    inserts = [c for c in activity_row_creators() if c["kind"] == "row_insert_point"]
    place_doors = sorted(
        k
        for k, v in write_ops.items()
        if set(f.lower() for f in v["request_fields"]) & PLACE_FIELDS
    )
    matched = []
    for c in calls:
        key = next(
            (
                k
                for k in write_ops
                if normalize(c["url"]) == normalize(k.split(" ", 1)[1])
                and write_ops[k]["verb"] == c["method"]
            ),
            None,
        )
        matched.append({**c, "contract_operationId": (write_ops[key]["operationId"] if key else None),
                        "in_contract": key is not None})

    result = {
        "command": " ".join(sys.argv),
        "repo_head": args.sha
        or subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
        "denominators": {
            "contract_paths": len(ops) and len(yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))["paths"]),
            "contract_operations": len(ops),
            "contract_write_operations": len(write_ops),
            "frontend_write_call_sites": len(calls),
            "frontend_write_call_sites_matched_to_a_contract_operation": sum(
                1 for m in matched if m["in_contract"]
            ),
            "contract_write_paths_containing_activities": len(activity_paths),
            "contract_write_paths_addressing_the_activity_collection": len(creation_paths),
            "contract_write_paths_naming_a_place_or_coordinate_field": len(place_doors),
            "backend_activity_row_insert_points": len(inserts),
            "backend_activity_class_declarations_matched_by_the_same_pattern": len(
                [c for c in activity_row_creators() if c["kind"] == "class_declaration"]
            ),
        },
        "contract_write_paths_containing_activities": activity_paths,
        "contract_write_paths_addressing_the_activity_collection": creation_paths,
        "place_naming_write_doors": [
            {"door": k, "operationId": write_ops[k]["operationId"],
             "request_fields": write_ops[k]["request_fields"]}
            for k in place_doors
        ],
        "frontend_write_calls": matched,
        "backend_activity_row_creators": activity_row_creators(),
        "instrument_limitations": [
            "url matching: several frontend call sites build their path by string concatenation, so "
            f"the contract-operation join resolves only "
            f"{sum(1 for m in matched if m['in_contract'])} of {len(calls)} sites. The counts that "
            "carry this verdict are the contract and backend ones, which are scanned in full; the "
            "call-site join is inventory, not the denominator of the claim.",
        ],
        "verdict": {
            "a_route_that_creates_an_activity_from_a_user_named_place_exists": bool(creation_paths),
            "note": "creation_paths counts write operations whose own path addresses the activity "
            "collection (/…/activities). Every /activities door in this build carries an "
            "{activity_id}, so it acts on a row that already exists; Activity rows are inserted only "
            "inside plan composition, trip-studio accept of ids that already exist, and replan accept.",
        },
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["denominators"], ensure_ascii=False, indent=2))
    print("activity_write_paths", activity_paths)
    print("collection_level_activity_doors", creation_paths)
    print("place_doors", [d["door"] for d in result["place_naming_write_doors"]])
    print("activity_row_insert_points", len(inserts))
    return 0


def normalize(url: str) -> str:
    """Fold every concrete id and template hole to one token so paths can be compared."""
    u = re.sub(r"\{[^}]*\}", "{p}", url)
    u = re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{20,}", "{p}", u)
    u = u.replace("/api/v1", "")
    parts = [p for p in u.split("/") if p]
    return "/" + "/".join("{p}" if re.fullmatch(r"[\w-]*\{p\}[\w-]*", p) else p for p in parts)


if __name__ == "__main__":
    sys.exit(main())
