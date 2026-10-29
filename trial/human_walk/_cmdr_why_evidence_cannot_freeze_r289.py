"""bw289: why can no evidence be frozen for a stay-materialised plan?  Read the canary database.

bw285 and bw288 both stopped the accept walk with 503 "mobility fact unavailable ... KeyError", on
Tianjin and on Beijing alike - the city with the complete OD matrix.  That says the missing evidence
is not a city-coverage gap.  This ruler answers the next question by reading only the sqlite file the
previous probe produced for itself: do the Places that the plan actually walks even appear as
endpoints in the mobility evidence tables?

Positive control: the ruler copies the file into its own scratch directory, inserts one synthetic
mobility row whose endpoints ARE the two places the walk needs, and re-runs the same intersection
test on the copy.  If the copy reports an intersection of one, the zero on the original is a fact
about the database, not a broken join in this ruler.  Nothing is written to the original file (it is
opened with mode=ro) and nothing is written to any classroom or shared database.
"""

import json
import os
import pathlib
import re
import shutil
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw289-why-evidence-cannot-freeze.txt")
SOURCE_RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                              "bw288-accept-with-frozen-evidence.txt")

FORBIDDEN_FRAGMENTS = ("_cmdr_clean_1028", "_cmdr_tip_113", "citynexus_v3_rescue")


def _db_path_from_receipt() -> str:
    text = open(SOURCE_RECEIPT, encoding="utf-8").read()
    match = re.search(r"^DATABASE sqlite:///(\S+)", text, re.M)
    if not match:
        raise SystemExit("ABORT cannot read the database coordinate out of %s" % SOURCE_RECEIPT)
    path = match.group(1)
    if not os.path.exists(path):
        raise SystemExit("ABORT the probe database no longer exists: %s" % path)
    lowered = path.lower().replace("\\", "/")
    for fragment in FORBIDDEN_FRAGMENTS:
        if fragment.lower() in lowered:
            raise SystemExit("ABORT refusing to open a shared/classroom database: %s" % path)
    if "temp" not in lowered and "tmp" not in lowered:
        raise SystemExit("ABORT this probe only reads a temporary database, refusing %s" % path)
    return path


def _columns(conn, table) -> list[str]:
    try:
        return [row[1] for row in conn.execute("PRAGMA table_info(%s)" % table)]
    except sqlite3.Error:
        return []


def _rows(conn, query, params=()) -> list[tuple]:
    try:
        return list(conn.execute(query, params))
    except sqlite3.Error as exc:
        # A failed query must never be returned as if it were data - that is how a
        # broken ruler reports a confident zero.
        raise SystemExit("ABORT query failed: %s | %s" % (query[:80], str(exc)[:160]))


JOURNEY_TITLE_PREFIX = "r288 probe"


def _survey(conn, label, out) -> dict:
    found = _rows(conn, "SELECT id, city_code, status, active_plan_version_id FROM journeys "
                        "WHERE title LIKE ?", (JOURNEY_TITLE_PREFIX + "%",))
    if not found:
        out.append("%s: no journey titled %r in this database" % (label, JOURNEY_TITLE_PREFIX))
        return {}
    journey_id, city, journey_status, plan_id = found[0]
    if plan_id is None:
        out.append("%s: the journey has no active plan pointer" % label)
        return {}
    places = _rows(conn,
                   "SELECT a.place_id, pl.provider_key FROM activities a "
                   "LEFT JOIN places pl ON pl.id = a.place_id "
                   "WHERE a.plan_version_id = ? ORDER BY a.sequence_no", (plan_id,))
    used = [row[0] for row in places if row and row[0]]
    mf_cols = _columns(conn, "mobility_facts")
    endpoint_cols = [c for c in (("from_key", "to_key"), ("origin_key", "destination_key"))
                     if all(name in mf_cols for name in c)][0:1]
    endpoint_cols = list(endpoint_cols[0]) if endpoint_cols else []
    facts_total = _rows(conn, "SELECT COUNT(*) FROM mobility_facts")[0][0]
    facts_for_this_journey = _rows(
        conn, "SELECT COUNT(*) FROM mobility_facts WHERE journey_id = ?", (journey_id,))[0][0]
    tables = [r[0] for r in _rows(conn, "SELECT name FROM sqlite_master WHERE type='table'")]
    ops_total = (_rows(conn, "SELECT COUNT(*) FROM route_acquisition_operations")[0][0]
                 if "route_acquisition_operations" in tables else "no table")
    endpoints: set[str] = set()
    endpoint_sample: list[str] = []
    if len(endpoint_cols) == 2:
        for row in _rows(conn, "SELECT %s, %s FROM mobility_facts" % tuple(endpoint_cols)):
            for value in (str(row[0]), str(row[1])):
                if value not in endpoints:
                    endpoints.add(value)
                    endpoint_sample.append(value)
    provider_keys = sorted({str(row[1]) for row in places if row[1] is not None})
    snapshot = _rows(conn, "SELECT mobility_snapshot_id, mobility_evidence_json FROM plan_versions "
                           "WHERE id = ?", (plan_id,))
    evidence_facts = 0
    if snapshot and isinstance(snapshot[0][1], str):
        try:
            evidence_facts = len(json.loads(snapshot[0][1]).get("facts") or [])
        except json.JSONDecodeError:
            evidence_facts = -1
    intersect = sorted(set(used) & endpoints)
    out.extend([
        "%s: journey_status=%s city=%s plan=%s activities=%d used_place_ids=%d"
        % (label, journey_status, city, str(plan_id)[:8] + "…", len(places), len(used)),
        "%s: provider_keys=%s" % (label, provider_keys),
        "%s: mobility_facts rows=%d (for this journey=%d), endpoint columns=%s, "
        "distinct endpoints=%d"
        % (label, facts_total, facts_for_this_journey, endpoint_cols, len(endpoints)),
        "%s: route_acquisition_operations rows=%s" % (label, ops_total),
        "%s: plan mobility_snapshot_id=%s, facts inside its own evidence json=%d"
        % (label, (snapshot[0][0] if snapshot else None), evidence_facts),
        "%s: first used place ids=%s" % (label, [str(x)[:8] + "…" for x in used[:2]]),
        "%s: first evidence endpoint ids=%s"
        % (label, [str(x)[:8] + "…" for x in endpoint_sample[:2]]),
        "%s: INTERSECT used place ids with mobility_fact endpoints = %d" % (label, len(intersect)),
    ])
    return {"used": used, "journey_id": journey_id, "plan_id": plan_id,
            "intersect": len(intersect), "endpoint_cols": endpoint_cols,
            "mf_cols": mf_cols}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    path = _db_path_from_receipt()
    out = ["WHY NO EVIDENCE CAN BE FROZEN FOR A STAY-MATERIALIZED PLAN bw289",
           "READ-ONLY SOURCE %s (the temporary database bw288 produced for itself)" % path]
    uri = "file:%s?mode=ro" % path.replace("\\", "/")
    conn = sqlite3.connect(uri, uri=True)
    original = _survey(conn, "ORIGINAL", out)
    conn.close()

    scratch = pathlib.Path(tempfile.mkdtemp(prefix="cnx_r289_"))
    copy = scratch / "copy.db"
    shutil.copyfile(path, copy)
    out.append("CONTROL COPY %s (this ruler's own scratch file; the original stays read-only)"
               % copy.as_posix())
    control_conn = sqlite3.connect(copy)
    # find which tables a synthetic endpoint row would need
    tables = [r[0] for r in _rows(control_conn,
                                  "SELECT name FROM sqlite_master WHERE type='table'")]
    out.append("CONTROL: tables carrying mobility endpoints = %s"
               % [t for t in tables if "mobility" in t or "route" in t][:8])
    injected = 0
    if original.get("used") and len(original.get("endpoint_cols") or []) == 2:
        cols = original["endpoint_cols"]
        info = list(control_conn.execute("PRAGMA table_info(mobility_facts)"))
        known = {
            "id": "control-row-1", "journey_id": original["journey_id"],
            cols[0]: original["used"][0], cols[1]: original["used"][1],
            "mode": "WALK", "duration_min": 12, "distance_m": 800,
            "provider_key": "control-synthetic", "provenance": "CONTROL_SYNTHETIC",
            "captured_at": "2026-10-29T00:00:00+08:00",
        }
        insert_columns, values = [], []
        for _, name, type_name, notnull, default, _pk in info:
            if name in known:
                insert_columns.append(name)
                values.append(known[name])
            elif notnull and default is None:
                # every mandatory column the walk does not care about still has to be
                # satisfiable, or the control row never lands and proves nothing
                insert_columns.append(name)
                values.append(0 if type_name.upper() in ("INTEGER", "REAL") else "control")
        missing = [c for c in (cols[0], cols[1]) if c not in insert_columns]
        if missing:
            out.append("CONTROL: the copy has no endpoint columns %s - refusing to fake "
                       "an intersection" % missing)
        else:
            try:
                control_conn.execute(
                    "INSERT INTO mobility_facts (%s) VALUES (%s)"
                    % (",".join(insert_columns), ",".join(["?"] * len(insert_columns))),
                    tuple(values))
                control_conn.commit()
                injected = 1
                out.append("CONTROL: inserted 1 synthetic mobility row into the copy whose %s and "
                           "%s are the first two place ids the walk actually uses (id=control-row-1, "
                           "provider_key=control-synthetic, %d columns filled: %s); the copy is this "
                           "ruler's own scratch file, not a shared database"
                           % (cols[0], cols[1], len(insert_columns), ",".join(insert_columns)))
            except sqlite3.Error as exc:
                out.append("CONTROL: the copy refused a synthetic row (%s) - reporting that instead "
                           "of faking an intersection" % str(exc)[:160])
    after = _survey(control_conn, "CONTROL-COPY-AFTER-INJECT", out)
    control_conn.close()

    bites = (after.get("intersect", 0) > original.get("intersect", 0))
    out.append("RULER_BITES_ON_THE_COPY %s (original intersect=%s, copy intersect=%s, injected=%d)"
               % ("YES" if bites else "NO", original.get("intersect"),
                  after.get("intersect"), injected))
    out.append("VERDICT %s"
               % ("The join works and reports an intersection when the endpoints exist, so the "
                  "zero on the original database is a fact about what the product ever captured: "
                  "the places a stay-materialised plan walks are not present as endpoints in any "
                  "mobility evidence row."
                  if bites else
                  "INCONCLUSIVE: the control did not produce an intersection, so the zero on the "
                  "original cannot be read as a fact - fix this ruler first."))
    io_open = open(RECEIPT, "w", encoding="utf-8", newline="\n")
    io_open.write("\n".join(out) + "\n")
    io_open.close()
    for line in out:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0 if bites else 7


if __name__ == "__main__":
    sys.exit(main())
