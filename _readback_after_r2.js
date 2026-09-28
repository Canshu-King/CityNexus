/* ORD-0435 (r2) server read-back, outside the browser (lane be19052c).
 *
 * The screen's receipt is one reading; this is the second and third, with no page in the loop:
 *   - `GET /api/v1/plans/{id}` on the port this lane started, and
 *   - a read-only sqlite query against the file that port has open.
 * All three have to agree, or the screen is claiming a write the store does not hold.
 *
 * Inputs come from the environment so the same instrument works on a fresh base:
 *   EVIDENCE  the Q4 arm's json the playwright run wrote
 *   BASE      backend origin          DB  the sqlite file it has open
 *   JOURNEY   the demo journey        MARKER  this round's ownership row
 * The database is opened `mode=ro`; nothing here writes, and `POST /api/v1/demo/reset` is never
 * called from this script.
 */
const fs = require("fs");
const { DatabaseSync } = require("node:sqlite");

const EVIDENCE = process.env.EVIDENCE ?? "D:/moodle/_qoder_b_ord0435b_20260929/_r2_evidence/ord0435/local__Q4.json";
const BASE = process.env.BASE ?? "http://127.0.0.1:8812";
const DB = process.env.DB ?? "D:/moodle/_qoder_b_ord0435b_20260929/backend/_ord0435b_priv.db";
const JOURNEY = process.env.JOURNEY ?? "22222222-2222-4222-8222-222222222222";
const MARKER = process.env.MARKER ?? "ORD0435BMARKER-16388da5";
const OUT = process.env.OUT ?? "D:/moodle/_qoder_b_ord0435b_20260929/_r2_evidence/readback_r2.json";

const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g;

async function main() {
  const arm = JSON.parse(fs.readFileSync(EVIDENCE, "utf-8"));
  const planId = arm.plan_id;
  const screenRows = arm.row_texts ?? [];
  const screenActivityIds = screenRows.flatMap((t) => t.match(UUID) ?? []);
  if (!planId) throw new Error("the Q4 evidence names no plan, so there is nothing to reconcile");

  const res = await fetch(`${BASE}/api/v1/plans/${planId}`);
  const body = await res.json();
  const routeRows = (body.activities ?? []).filter((a) => String(a.place_id ?? "").startsWith("real-place-"));

  const db = new DatabaseSync(DB.replace(/\//g, "\\"), { readOnly: true });
  const storeRows = db
    .prepare("SELECT id, sequence_no, title, place_id, start_at, status FROM activities WHERE plan_version_id = ? ORDER BY sequence_no")
    .all(planId);
  const storePicked = storeRows.filter((r) => String(r.place_id ?? "").startsWith("real-place-"));
  const markerRows = db.prepare("SELECT id, title FROM activities WHERE title = ?").all(MARKER);
  const planVersions = db
    .prepare("SELECT COUNT(*) AS n FROM plan_versions WHERE journey_id = ?")
    .get(JOURNEY).n;
  db.close();

  const key = (r) => `${r.id}|${r.place_id}|${r.start_at}`;
  const out = {
    base: BASE,
    database: DB,
    evidence: EVIDENCE,
    plan_id: planId,
    route: {
      http_status: res.status,
      plan_status: body.status,
      version_no: body.version_no,
      activity_rows: (body.activities ?? []).length,
      picked: routeRows.map((a) => ({ id: a.id, title: a.title, place_id: a.place_id, start_at: a.start_at })),
    },
    store: {
      activity_rows: storeRows.length,
      picked: storePicked.map((a) => ({ id: a.id, title: a.title, place_id: a.place_id, start_at: a.start_at })),
    },
    screen: { row_count: screenRows.length, activity_ids: screenActivityIds, rows: screenRows },
    agrees: {
      route_http_200: res.status === 200,
      route_and_store_same_rows:
        JSON.stringify(routeRows.map(key)) === JSON.stringify(storePicked.map(key)),
      every_screen_id_is_in_the_store: screenActivityIds.every((id) => storeRows.some((r) => r.id === id)),
      every_screen_title_is_in_the_store: screenRows.every((t) => storeRows.some((r) => t.includes(String(r.title)))),
      screen_row_count_matches_store: screenRows.length === storePicked.length,
      day_on_screen_matches_the_row: String(arm.day_on_screen ?? "") === String(storePicked[0]?.start_at ?? "").slice(0, 10),
    },
    ownership: { marker: MARKER, marker_rows_found: markerRows.length, plan_versions_for_this_journey: planVersions },
  };
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1), "utf-8");
  console.log(JSON.stringify(out, null, 1));
  const failed = Object.entries(out.agrees).filter(([, v]) => v !== true);
  if (failed.length || out.ownership.marker_rows_found !== 1) {
    console.log("READBACK_NOT_CONSISTENT", JSON.stringify(failed), "marker_rows", out.ownership.marker_rows_found);
    process.exitCode = 1;
  } else {
    console.log("READBACK_CONSISTENT");
  }
}

main().catch((cause) => {
  console.error("READBACK_FAILED", cause instanceof Error ? cause.message : String(cause));
  process.exitCode = 1;
});
