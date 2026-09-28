/* ORD-0435 server read-back, outside the browser (lane be19052c).
 *
 * The screen's receipt is one reading. This is the second one, with no page in the loop: for every
 * plan the after-probe wrote, ask the route for it and read the same rows out of the sqlite file the
 * backend owns. Both have to agree with what the screen printed, or the screen is lying.
 *
 * The database is opened read-only (`mode=ro`); nothing here writes, and the demo/reset route is
 * never called.
 */
const fs = require("fs");
const { DatabaseSync } = require("node:sqlite");

const BASE = "http://127.0.0.1:8811";
const JOURNEY = "22222222-2222-4222-8222-222222222222";
const DB = "D:/moodle/_qoder_b_ord0435_20260929/backend/_ord0435_priv.db";
const PROBE = "D:/moodle/_qoder_b_ord0435_20260929/_probe_after_p1/probe_after_p1.json";

const report = JSON.parse(fs.readFileSync(PROBE, "utf-8"));
const db = new DatabaseSync(DB.replace(/\//g, "\\"), { readOnly: true });

const out = { base: BASE, database: DB, journey_id: JOURNEY, arms: [] };

async function main() {
for (const arm of [report.zh, report.en]) {
  const entry = { locale: arm.locale, screen_rows: arm.a2?.row_texts ?? [], plan_id: null, http: null, sqlite: null, agrees: null };
  const planText = String(arm.a2?.plan_text ?? "");
  const planId = /([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/.exec(planText)?.[1] ?? null;
  entry.plan_id = planId;
  if (!planId) {
    out.arms.push(entry);
    continue;
  }

  const res = await fetch(`${BASE}/api/v1/plans/${planId}`);
  const body = await res.json();
  entry.http = {
    status: res.status,
    bytes: JSON.stringify(body).length,
    version_no: body.version_no,
    status_field: body.status,
    activity_count: (body.activities ?? []).length,
    picked_rows: (body.activities ?? [])
      .filter((a) => a.place_id && String(a.place_id).startsWith("real-place-"))
      .map((a) => ({ id: a.id, seq: a.sequence_no, start_at: a.start_at, place_id: a.place_id, title: a.title })),
  };

  const rows = db
    .prepare(
      "SELECT id, sequence_no, activity_type, title, place_id, start_at, end_at, status, locked FROM activities WHERE plan_version_id = ? ORDER BY sequence_no",
    )
    .all(planId);
  entry.sqlite = {
    row_count: rows.length,
    picked_rows: rows
      .filter((r) => r.place_id && String(r.place_id).startsWith("real-place-"))
      .map((r) => ({ id: r.id, seq: r.sequence_no, start_at: r.start_at, place_id: r.place_id, title: r.title })),
  };

  /* Three ways the same row has to answer: what the screen printed, what the route says, what the
     file holds. Compare on the identity that matters -- activity id, its place, its instant. */
  const key = (r) => `${r.id}|${r.place_id}|${r.start_at}`;
  entry.agrees = {
    screen_row_count: (arm.a2?.row_texts ?? []).length,
    route_picked_count: entry.http.picked_rows.length,
    store_picked_count: entry.sqlite.picked_rows.length,
    route_and_store_same_rows:
      JSON.stringify(entry.http.picked_rows.map(key)) === JSON.stringify(entry.sqlite.picked_rows.map(key)),
    screen_ids_all_present_in_store: (arm.a2?.row_texts ?? []).every((t) =>
      rows.some((r) => t.includes(String(r.id))),
    ),
    screen_titles_all_present_in_store: (arm.a2?.row_texts ?? []).every((t) =>
      rows.some((r) => t.includes(String(r.title))),
    ),
  };
  out.arms.push(entry);
}

const planCountBefore = db
  .prepare("SELECT COUNT(*) AS n FROM plan_versions WHERE journey_id = ?")
  .get(JOURNEY).n;
const activitiesTotal = db.prepare("SELECT COUNT(*) AS n FROM activities").get().n;
out.journey_scope = { plan_versions_now: planCountBefore, activities_in_store_now: activitiesTotal };
/* The marker row this lane planted to prove the port and the file are its own -- if it is still
   readable, the rows above came from the copy, not from a neighbour's backend. */
out.ownership_marker = db
  .prepare("SELECT id, title FROM activities WHERE title LIKE ?")
  .all("%ORD0435MARKER-d6fae13a%");

fs.writeFileSync(
  "D:/moodle/_qoder_b_ord0435_20260929/_probe_after_p1/readback_after_p1.json",
  JSON.stringify(out, null, 1),
  "utf-8",
);
console.log(JSON.stringify(out, null, 1));
db.close();
}

main().catch((cause) => {
  console.error("READBACK_FAILED", cause instanceof Error ? cause.message : String(cause));
  process.exitCode = 1;
});
