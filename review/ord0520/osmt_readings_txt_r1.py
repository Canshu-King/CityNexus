"""Land the osm_type readings as one plainly-numbered text file, so the block can cite `path:line`.

Every line is computed out of a measurement file this lane actually produced, plus one collection
count this run measures itself.  Nothing here is typed in from memory: the `path:line` anchors are
grabbbed by reading the files, and the "before" anchor is read out of the parent commit's blob.

Why a .txt at all: the ledger's coordinate ruler takes `path:line` on .txt but not on .json or .jsonl
(measured on earlier cells of this lane), so the readings get stable line numbers the block can point at.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import re
import subprocess

TREE = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930/wt2")
LANE = TREE.parent
OUT = TREE / "review/ord0520/OSMT_READINGS_r1.txt"
MAIN = json.loads((TREE / "review/ord0520/OSMT_ARMS_AND_SUPPLY_ab_r1.json").read_text(encoding="utf-8"))
FLAKE = json.loads((TREE / "review/ord0520/OSMT_FLAKE_ATTRIBUTION_r1.json").read_text(encoding="utf-8"))
FIRST = json.loads((LANE / "tmp/OSMT_XPROC_AB_r1.json").read_text(encoding="utf-8"))
BACKEND = TREE / "backend"
PRODUCT = "backend/app/anywhere_capability.py"


def git_text(*args: str) -> str:
    return subprocess.run(["git", "-C", str(TREE), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout


def grab(relpath: str, needle: str) -> str:
    text = (TREE / relpath).read_text(encoding="utf-8")
    for number, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return "%s:%d" % (relpath, number)
    raise SystemExit("anchor not found: %r in %s" % (needle, relpath))


def tip_line(needle: str) -> str:
    text = git_text("show", "%s:%s" % (MAIN["parent_tip"], PRODUCT))
    for number, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return "%s:%d" % (PRODUCT, number)
    raise SystemExit("tip anchor missing: %r" % needle)


def collect_only() -> tuple[int, str]:
    """One real collection over the whole backend suite on this HEAD."""

    db = LANE / "db" / ("_osmt-collect-%s.db"
                        % datetime.datetime.now(datetime.timezone.utc).strftime("%H%M%S"))
    env = dict(subprocess.os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([MAIN["interpreter"], "-X", "utf8", "-m", "pytest", "-q", "--collect-only", "tests/"],
                          cwd=str(BACKEND), env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    hit = re.search(r"(\d+) tests? collected", proc.stdout or "")
    for suffix in ("", "-wal", "-shm"):
        path = pathlib.Path(str(db) + suffix)
        if path.exists():
            path.unlink()
    return proc.returncode, hit.group(0) if hit else (proc.stdout or "")[-120:]


collect_rc, collect_line = collect_only()
lines = [
    "osm_type cell readings - lane 89f2e2d6 - computed from measurement files in this tree",
    "measured_at=%s" % MAIN["measured_at"],
    "measured_against_head=%s" % MAIN["measured_against_head"],
    "parent_tip=%s" % MAIN["parent_tip"],
    "product_blob_patched=%s" % MAIN["product_blob_patched"],
    "product_blob_parent=%s" % MAIN["product_blob_parent"],
    "arms_file_blob=%s" % MAIN["arms_file_blob"],
    "interpreter=%s" % MAIN["interpreter"],
    "collect_only rc=%d %s" % (collect_rc, collect_line),
    "arms_before=%s" % MAIN["arms_before"],
    "arms_before_red_names=%s" % ", ".join(MAIN["each_state"]["tip_bytes"]["arms"]["red_names"]),
    "arms_after=%s" % MAIN["arms_after"],
    "supply_before=%s" % MAIN["supply_before"],
    "supply_after=%s" % MAIN["supply_after"],
    "supply_rows=%d rows_missing_coordinates=%d probe_verdict=%s probe_rc=%d"
    % (MAIN["each_state"]["patched"]["real_supply"]["places_rows"],
       MAIN["each_state"]["patched"]["real_supply"]["rows_missing_coordinates"],
       MAIN["each_state"]["patched"]["real_supply"]["probe_verdict"],
       MAIN["each_state"]["patched"]["real_supply"]["rc"]),
    "neighbour_reds_before=%s | %s"
    % (MAIN["each_state"]["tip_bytes"]["neighbours"]["line"], ", ".join(MAIN["neighbour_reds_before"])),
    "neighbour_reds_after=%s | %s"
    % (MAIN["each_state"]["patched"]["neighbours"]["line"], ", ".join(MAIN["neighbour_reds_after"])),
    "new_red_names_from_this_patch=%s"
    % (", ".join(MAIN["new_red_names_from_this_patch"]) or "none"),
    "main_verdict=%s" % MAIN["verdict"],
    "first_flake_verdict_published=%s" % FIRST["verdict"],
    "flake_experiment_1_rate=%s" % json.dumps(FLAKE["family_red_rate_experiment_1"], ensure_ascii=False),
    "flake_experiment_2_rate=%s" % json.dumps(FLAKE["family_red_rate_experiment_2"], ensure_ascii=False),
    "flake_verdict=%s" % FLAKE["verdict"],
    "flaking_arms_read_the_capability_door=%s"
    % json.dumps(FLAKE["do_the_flaking_arms_read_the_capability_door"], ensure_ascii=False),
    "anchor_projection_before=%s" % tip_line('"osm_type": str(place.external_id).split(":", 1)[0].lower()'),
    "anchor_projection_after=%s" % grab(PRODUCT, '"osm_type": _place_geometry_kind(place.external_id)'),
    "anchor_helper_names=%s" % grab(PRODUCT, "_OSM_GEOMETRY_KINDS = (\"node\", \"way\", \"relation\")"),
    "anchor_helper_def=%s" % grab(PRODUCT, "def _place_geometry_kind("),
    "anchor_arm_a1=%s" % grab("backend/tests/test_qoder_ord0520_osm_type_bare_kind_r1.py",
                              "def test_a1_a_slash_shaped_way_identity_answers_a_bare_kind"),
    "anchor_arm_a3=%s" % grab("backend/tests/test_qoder_ord0520_osm_type_bare_kind_r1.py",
                              "def test_a3_an_identity_that_is_not_an_osm_element_answers_a_named_null"),
    "anchor_arm_a5=%s" % grab("backend/tests/test_qoder_ord0520_osm_type_bare_kind_r1.py",
                              "def test_a5_the_bare_kind_arms_bite_when_the_projection_echoes_the_composite"),
    "anchor_g10_reader=%s" % grab("backend/tests/test_qoder_anywhere_provider_truth.py",
                                  'kind = str(item.get("source_kind_geometry")'),
    "anchor_flaky_family_first=%s" % grab("backend/tests/test_qoder_catalog_hydration.py",
                                          "def test_a_worker_that_wakes_on_an_abandoned_row_closes_it"),
    "anchor_flaky_family_last=%s" % grab("backend/tests/test_qoder_catalog_hydration.py",
                                         "def test_an_abandon_whose_own_write_never_landed_still_closes_the_job"),
    "replay_supply_file=%s" % "data/replay/tianjin_real_snapshot.json",
]
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print(OUT.read_text(encoding="utf-8"))
