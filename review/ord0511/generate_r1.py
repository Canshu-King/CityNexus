"""ORD-0511 step 1b: the generate door's own answer, unwrapped, on both journeys.

The first pass showed the result rides under a nested key, so this prints that object as it arrived
rather than a guessed top-level field, and runs the same call on the demo trip -- the one whose stay
screen is empty today -- to see whether a real candidate list comes back at all.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8018/api/v1"
UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def call(method: str, path: str) -> tuple[int, str]:
    request = urllib.request.Request(f"{BASE}{path}", method=method, data=b"" if method == "POST" else None)
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return 200, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


def report(label: str, journey_id: str) -> dict:
    status, text = call("POST", f"/journeys/{journey_id}/stay-options/generate")
    out: dict = {"label": label, "generate_http_status": status, "uuid_hits": len(UUID_RE.findall(text))}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        out["not_json_head"] = text[:300]
        return out
    out["top_level_keys"] = sorted(parsed)
    generation = parsed.get("generation")
    if isinstance(generation, dict):
        out["generation_keys"] = sorted(generation)
        for key in (
            "outcome",
            "options_ranked",
            "offers_from_provider",
            "rejections_by_reason",
            "provider_attempts",
            "candidate_count",
            "reasons",
        ):
            if key in generation:
                value = generation[key]
                out[f"generation.{key}"] = value if not isinstance(value, str) else value[:200]
    status2, text2 = call("GET", f"/journeys/{journey_id}/stay-options")
    read = json.loads(text2) if status2 == 200 else {}
    out["read_http_status"] = status2
    out["options_after"] = len(read.get("options") or [])
    out["offers_after"] = len(read.get("offers") or [])
    out["selected_option_id_after"] = read.get("selected_option_id")
    if read.get("options"):
        out["first_option_keys"] = sorted(read["options"][0])
    return out


readings = []
readings.append(report("demo trip", "22222222-2222-4222-8222-222222222222"))
status, text = call("GET", "/journeys")
rows = json.loads(text) if status == 200 else []
bare = [row["id"] for row in rows if str(row.get("title", "")).startswith("CNX-ORD0511")]
if bare:
    readings.append(report("bare trip created by this lane", bare[0]))

with open("D:/moodle/_qoder_n2b_ord0511_20260930/generate_r1.json", "w", encoding="utf-8") as handle:
    json.dump(readings, handle, ensure_ascii=False, indent=1)
print(json.dumps(readings, ensure_ascii=False, indent=1)[:2600])
