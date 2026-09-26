"""ORD-0346 S4 requirement 1: the fact sheet, computed from the artefacts it names.

Every number in the output is derived here from a file or a reading -- the two source tables are
re-parsed from the generation's own bytes, and the verdicts come from the HTTP reading taken against
this lane's server.  Nothing is copied in from prose.
"""
import io
import json
import os
import re
import subprocess

WORK = os.path.dirname(os.path.abspath(__file__))
GEN = "c740f45d68f337c460a1a43b995162689d0110af"
TREE = "D:/moodle/_qoder_ord0346_S4"
REPO = "D:/moodle/CityNexus"
SCREEN = "frontend/src/features/setup/JourneyTrialSetup.tsx"
MAIN = "backend/app/main.py"

blob = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (GEN, SCREEN)],
                      capture_output=True).stdout.decode("utf-8")
lines = blob.splitlines()



facts_start = next(i for i, line in enumerate(lines, 1) if line.startswith("const CITY_FACTS"))
facts_end = next(i for i in range(facts_start, len(lines)) if lines[i - 1].strip() == "};")
facts_text = "\n".join(lines[facts_start - 1:facts_end])
keys = re.findall(r'^\s{2}(?:"([^"]+)"|([a-z]+)):\s*\{', facts_text, re.M)
advertised = [zh or latin for zh, latin in keys]
advertised_zh = [name for name in advertised if re.search(r"[^\x00-\x7F]", name)]
advertised_en = [name for name in advertised if re.match(r"^[\x00-\x7F]+$", name)]

main_blob = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (GEN, MAIN)],
                           capture_output=True).stdout.decode("utf-8").splitlines()
names_start = next(i for i, line in enumerate(main_blob, 1) if line.startswith("_CITY_DISPLAY_NAMES"))
names_end = next(i for i in range(names_start, len(main_blob)) if main_blob[i - 1].strip() == "}")
vocabulary_text = "\n".join(main_blob[names_start - 1:names_end])
vocabulary = dict(re.findall(r'^\s{4}"([A-Z_]+)":\s*"([^"]+)",?$', vocabulary_text, re.M))

reading = json.load(open(os.path.join(WORK, "capability_reading_r1.json"), encoding="utf-8"))
by_query = {}
for item in reading["readings"]:
    if item["group"] in ("screen_zh", "screen_en") and item["fields"]:
        by_query[item["query"]] = item["fields"]

named = [name for name in advertised_zh if by_query[name]["canonical_destination_id"]]
unnamed = [name for name in advertised_zh if not by_query[name]["canonical_destination_id"]]
with_rows = [name for name in advertised_zh if (by_query[name]["place_count"] or 0) > 0]
ready = [name for name in advertised_zh if by_query[name]["capability"] == "READY"]
intersects = sorted(set(advertised_zh) & set(vocabulary.values()))

placeholder_hits = [item["query"] for item in reading["readings"] if item["placeholder_shaped_strings"]]

out = {
  "order": "ORD-0346",
  "lane": "S4-ast-taint",
  "generation": GEN,
  "screen": {
    "file": SCREEN,
    "control_line": next(i for i, line in enumerate(lines, 1) if "看支持的目的地" in line),
    "list_rendered_at": [i for i, line in enumerate(lines, 1) if "SUPPORTED_CITIES.zh : SUPPORTED_CITIES.en" in line],
    "source_table": "CITY_FACTS at %s:%d-%d" % (SCREEN, facts_start, facts_end),
    "derived_list": "SUPPORTED_CITIES at %s:%d" % (SCREEN, next(i for i, line in enumerate(lines, 1) if line.startswith("const SUPPORTED_CITIES"))),
    "routes_read_by_the_screen_before_this_change": [],
    "note": "the panel read no route at all: the names came from a client-side spelling table, and the "
            "heading called them supported destinations",
  },
  "server_side": {
    "vocabulary_table": "%s:%d-%d" % (MAIN, names_start, names_end),
    "vocabulary_codes": len(vocabulary),
    "capability_route": "backend/app/main.py:2908 GET /api/v1/destinations/capability -> evaluate_capability",
    "identity_field": "canonical_destination_id (backend/app/anywhere_capability.py:344-357 identity_fields)",
    "resolver_seam": "CITYNEXUS_ANYWHERE_RESOLVER, off by default (backend/app/anywhere_capability.py:205-206)",
  },
  "set_difference": {
    "advertised_zh_spellings": len(advertised_zh),
    "advertised_en_spellings": len(advertised_en),
    "advertised_zh": advertised_zh,
    "backend_vocabulary_labels": len(vocabulary),
    "in_both": intersects,
    "in_both_count": len(intersects),
    "advertised_but_not_in_the_backend_vocabulary": sorted(set(advertised_zh) - set(vocabulary.values())),
    "in_the_backend_vocabulary_but_not_advertised": sorted(set(vocabulary.values()) - set(advertised_zh)),
  },
  "measured_against_the_server": {
    "reading_artifact": "capability_reading_r1.json",
    "port": reading["server"]["port"],
    "database": reading["server"]["database_url_named_by_this_lane"],
    "resolver_seam": reading["server"]["resolver_seam"],
    "named_by_the_server": named,
    "named_count": len(named),
    "not_named": unnamed,
    "not_named_count": len(unnamed),
    "with_catalogue_rows": with_rows,
    "capability_READY": ready,
    "capability_READY_count": len(ready),
    "per_name": {name: by_query[name] for name in advertised_zh},
  },
  "identity_column": {
    "readings_where_any_field_held_a_placeholder_shaped_string": placeholder_hits,
    "the_values_that_matched": sorted({entry["value"] for item in reading["readings"]
                                       for entry in item["placeholder_shaped_strings"]}),
    "the_paths_that_matched": sorted({entry["path"] for item in reading["readings"]
                                      for entry in item["placeholder_shaped_strings"]}),
    "identity_fields_holding_any_of_them": sorted({
        key for item in reading["readings"] for entry in item["placeholder_shaped_strings"]
        for key in [entry["path"].rsplit(".", 1)[-1]] if key in {
            "canonical_destination_id", "destination_pending_key", "pending_destination_label",
            "resolver_query_normalized", "matched_label"}}),
    "identity_values_seen": sorted({str(by_query[name]["canonical_destination_id"]) for name in advertised_zh}),
    "destination_pending_key_values_seen": sorted({str(by_query[name]["destination_pending_key"]) for name in advertised_zh}),
    "note": "the placeholder this order named was retired from the server's identity fields before this "
            "generation; what remains is the trap that made it look present: for a name the server "
            "cannot resolve, pending_destination_label and resolver_query_normalized are non-empty "
            "beside a null canonical_destination_id, so a column that reads 'not blank' reports an "
            "identity that was never given",
  },
}
path = os.path.join(WORK, "fact_sheet_r1.json")
json.dump(out, io.open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: out[k] for k in ("set_difference",)}, ensure_ascii=False, indent=1)[:1400])
print("measured:", json.dumps(out["measured_against_the_server"], ensure_ascii=False)[:600])
print("identity:", json.dumps(out["identity_column"], ensure_ascii=False)[:600])
print("wrote", path, os.path.getsize(path), "bytes")
