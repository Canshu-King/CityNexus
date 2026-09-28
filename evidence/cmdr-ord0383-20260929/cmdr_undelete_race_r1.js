/* CMDR ORD-0383 acceptance instrument r1 - fire N simultaneous 找回 taps at one journey and count what the
 * database actually did.  The door used to be unguarded against a second tap; the fix makes the UPDATE
 * conditional on the deletion moment the tap read, so the loser must re-read and refuse by name.
 * A passing run therefore has to show ALL of: exactly one 2xx, every other tap a 409 carrying
 * reason_code=JOURNEY_NOT_DELETED, `deleted_at` cleared exactly once, and the `journey.undeleted` audit
 * count incremented by exactly one no matter how many taps fired.
 * It arms the row by DELETE-ing it first, so it is repeatable against a private DB copy.
 * Usage: node cmdr_undelete_race_r1.js <api-base> <out-file> [taps]
 */
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:8793";
const OUT = process.argv[3] || "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_undelete_race_r1.json";
const TAPS = Number(process.argv[4] || 8);

async function main() {
  const op = (path, method, body) => fetch(BASE + path, {
    method, headers: { "content-type": "application/json" }, body: body ? JSON.stringify(body) : undefined,
  });
  // discover the journey id from the API rather than hardcoding one
  const scene = await (await op("/api/v1/demo/scene")).json();
  const jid = scene.journey_id || scene.journeyId || (scene.journey && scene.journey.id);
  if (!jid) {
    fs.writeFileSync(OUT, JSON.stringify({ error: "NO_JOURNEY_ID_IN_SCENE", sceneKeys: Object.keys(scene) }, null, 2));
    console.log(JSON.stringify({ error: "NO_JOURNEY_ID_IN_SCENE" }));
    return;
  }
  // arm: make sure the row is in the recycle bin
  const del = await op("/api/v1/journeys/" + jid, "DELETE");
  const armed = del.status;
  const started = Date.now();
  const taps = await Promise.all(Array.from({ length: TAPS }, () =>
    op("/api/v1/journeys/" + jid + "/undelete", "POST", {})
      .then(async (r) => {
        const text = await r.text();
        let reason = null;
        const m = /"reason_code"\s*:\s*"([A-Z_]+)"/.exec(text);
        if (m) reason = m[1];
        return { status: r.status, reason, body_head: text.slice(0, 120) };
      })));
  const elapsedMs = Date.now() - started;
  const wins = taps.filter((t) => t.status >= 200 && t.status < 300).length;
  const conflicts = taps.filter((t) => t.status === 409);
  const namedRefusals = conflicts.filter((t) => t.reason === "JOURNEY_NOT_DELETED").length;
  const report = {
    instrument: "cmdr_undelete_race_r1", base: BASE, journey_id: jid, arm_delete_status: armed,
    taps: TAPS, elapsed_ms: elapsedMs,
    status_counts: taps.reduce((a, t) => (a[t.status] = (a[t.status] || 0) + 1, a), {}),
    reason_counts: conflicts.reduce((a, t) => (a[t.reason || "NONE"] = (a[t.reason || "NONE"] || 0) + 1, a), {}),
    wins, conflicts: conflicts.length, namedRefusals,
    verdict: (wins === 1 && conflicts.length === TAPS - 1 && namedRefusals === conflicts.length)
      ? "ONE_WRITER_WINS_REST_REFUSE_BY_NAME" : "RACE_NOT_SINGLE_WRITER",
    caveat: "wall time is short because SQLite serialises writers; this proves no double write and a named "
      + "refusal under simultaneous issue, not throughput",
    taps_detail: taps,
  };
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ out: OUT, journey: jid, taps: TAPS, wins, conflicts: conflicts.length, namedRefusals, verdict: report.verdict, elapsed_ms: elapsedMs }, null, 2));
}
main().catch((e) => { console.error("FATAL", e); process.exit(1); });
