/* ORD-0489 · walk the two screens that only exist on a candidate ref, against this lane's board.
 *
 * Generation under test: refs/heads/1ba48dbf-ord0476-footprint-screen-r2 @
 * 15d65d7f289c628b810cf5ab4a097d858a128821  (足迹屏 ORD-0476 slice 2 + 长图 ORD-0472 poster).
 * That ref is NOT an ancestor of the line this lane seeded on
 * (dcb90cccc68b81f2317b28db19051dedb9f06c80); every reading here therefore says
 * `candidate_ref` in its own header, and nothing in it may be quoted as line behaviour.
 *
 * The backend stays the line's (:8790 at the base tip), so what is being asked is one thing:
 * does the board this lane seeded actually feed those two screens.
 */
const { chromium } = require("playwright");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const PREVIEW = process.env.CNX_PREVIEW || "http://127.0.0.1:8792";
const BACKEND = process.env.CNX_BACKEND || "http://127.0.0.1:8790";
const DIST = process.env.CNX_DIST || "D:/moodle/_qoder_seed_ord0489/dist476";
const OUT = "D:/moodle/_qoder_seed_ord0489/evidence/ord0489_screens";
fs.mkdirSync(OUT, { recursive: true });

const get = async (url) => {
  const res = await fetch(url);
  const buf = Buffer.from(await res.arrayBuffer());
  let json = null;
  try { json = JSON.parse(buf.toString("utf-8")); } catch { json = null; }
  return { status: res.status, bytes: buf.length, sha1: crypto.createHash("sha1").update(buf).digest("hex"), body: json, content_type: res.headers.get("content-type") };
};

const post = async (url, body) => {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}) });
  const text = await res.text();
  let json = null; try { json = JSON.parse(text); } catch { json = { raw: text.slice(0, 300) }; }
  return { status: res.status, bytes: Buffer.byteLength(text), body: json };
};

async function ids(page, list) {
  const out = {};
  for (const id of list) {
    const loc = page.locator(`[data-testid="${id}"]`);
    const n = await loc.count();
    out[id] = { present: n, text: n ? (await loc.first().innerText()).replace(/\s+/g, " ").trim().slice(0, 200) : null };
  }
  return out;
}

async function shot(page, name) {
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return { file: file.replace(/\\/g, "/"), bytes: fs.statSync(file).size };
}

(async () => {
  const report = {
    generation: {
      frontend_ref: "refs/heads/1ba48dbf-ord0476-footprint-screen-r2",
      frontend_sha: "15d65d7f289c628b810cf5ab4a097d858a128821",
      backend_line_sha: "dcb90cccc68b81f2317b28db19051dedb9f06c80",
      candidate_ref_is_ancestor_of_line: false,
      preview: PREVIEW,
      backend: BACKEND,
    },
    static_serving_proof: {},
    screens: {},
    started_at: new Date().toISOString(),
  };

  /* Which bytes is this port actually serving?  Two receipts, because a preview port has no
   * request log: the entry file it paints, and served-bytes == on-disk-bytes. */
  const root = await get(`${PREVIEW}/`);
  const diskIndex = path.join(DIST, "index.html");
  const diskBytes = fs.readFileSync(diskIndex);
  const assetMatch = diskBytes.toString("utf-8").match(/\/(assets\/[A-Za-z0-9._-]+\.js)/);
  const assetPath = assetMatch ? path.join(DIST, assetMatch[1]) : null;
  const assetServed = assetPath ? await get(`${PREVIEW}/${assetMatch[1]}`) : null;
  report.static_serving_proof = {
    index_served_sha1: root.sha1,
    index_disk_sha1: crypto.createHash("sha1").update(diskBytes).digest("hex"),
    index_served_bytes: root.bytes,
    index_disk_bytes: diskBytes.length,
    entry_asset: assetMatch ? assetMatch[1] : null,
    asset_served_sha1: assetServed ? assetServed.sha1 : null,
    asset_disk_sha1: assetPath ? crypto.createHash("sha1").update(fs.readFileSync(assetPath)).digest("hex") : null,
    asset_served_bytes: assetServed ? assetServed.bytes : null,
    note: "the SPA fallback answers 200 for a missing asset, so the asset row is the one that proves generation",
  };

  const journeys = await get(`${BACKEND}/api/v1/journeys`);
  const tianjin = journeys.body.find((j) => j.city_code === "CN-TIANJIN");
  const beijing = journeys.body.find((j) => j.city_code === "CN-BEIJING");
  report.board_journeys = journeys.body.map((j) => ({ title: j.title, city: j.city_code, activities: null }));

  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, deviceScaleFactor: 3, locale: "zh-CN", acceptDownloads: true });
  const page = await ctx.newPage();

  /* --- 足迹屏: open the trip that holds three stamps --- */
  await page.goto(`${PREVIEW}/v8/${tianjin.id}`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500);
  await page.goto(`${PREVIEW}/v8/footprints`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2200);
  const FOOT = ["footprint-panel", "footprint-tally", "footprint-row", "footprint-empty", "footprint-no-journey", "footprint-failed"];
  report.screens.footprint_before_new_stamp = {
    ids: await ids(page, FOOT),
    row_texts: await page.locator('[data-testid="footprint-row"]').allInnerTexts().then((a) => a.map((t) => t.replace(/\s+/g, " ").trim().slice(0, 160))),
    rendered: (await page.evaluate(() => document.body.innerText)).replace(/\s+/g, " ").trim().slice(0, 500),
    shot: await shot(page, "footprint_before_r3"),
  };

  /* --- the 打卡 control on the itinerary: press a real one and watch the set change --- */
  await page.goto(`${PREVIEW}/v8/trips`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500);
  const checkinLoc = page.locator('[data-testid="stop-checkin"]');
  const checkinCount = await checkinLoc.count();
  let stampAttempt = { control_count: checkinCount, pressed: null, notice: null };
  if (checkinCount > 0) {
    const box = await checkinLoc.first().boundingBox();
    const hit = box
      ? await page.evaluate(([x, y]) => {
          const el = document.elementFromPoint(x, y);
          return el ? (el.getAttribute("data-testid") || el.tagName) : null;
        }, [box.x + box.width / 2, box.y + box.height / 2])
      : null;
    await checkinLoc.first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    const box2 = await checkinLoc.first().boundingBox();
    const hit2 = box2
      ? await page.evaluate(([x, y]) => {
          const el = document.elementFromPoint(x, y);
          return el ? (el.getAttribute("data-testid") || el.tagName) : null;
        }, [box2.x + box2.width / 2, box2.y + box2.height / 2])
      : null;
    await checkinLoc.first().tap().catch(async () => checkinLoc.first().click());
    await page.waitForTimeout(1800);
    const notice = await page.locator('[data-testid="stop-checkin-notice"]').count();
    stampAttempt.pressed = { box: box2 ? { x: Math.round(box2.x), y: Math.round(box2.y), width: Math.round(box2.width), height: Math.round(box2.height) } : null, hit_test_before_scroll: hit, hit_test_after_scroll: hit2 };
    stampAttempt.notice = notice ? await page.locator('[data-testid="stop-checkin-notice"]').first().innerText() : null;
  }
  report.screens.checkin_control = stampAttempt;
  report.screens.door_after_press = await get(`${BACKEND}/api/v1/journeys/${tianjin.id}/checkins`);
  report.screens.door_after_press_body = report.screens.door_after_press.body?.map?.((r) => ({ target_kind: r.target_kind, target_key: r.target_key, place_name: r.place_name, activity_title: r.activity_title }));

  await page.goto(`${PREVIEW}/v8/footprints`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2000);
  report.screens.footprint_after_new_stamp = {
    ids: await ids(page, FOOT),
    row_texts: await page.locator('[data-testid="footprint-row"]').allInnerTexts().then((a) => a.map((t) => t.replace(/\s+/g, " ").trim().slice(0, 160))),
    shot: await shot(page, "footprint_after_r3"),
  };

  /* --- 长图: open the sheet on the same trip, read it, take the download --- */
  await page.goto(`${PREVIEW}/v8/trips`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500);
  const POSTER_BAR = ["trip-poster-bar", "poster-open", "poster-title", "poster-days", "poster-stop", "poster-download", "poster-result", "trip-poster"];
  report.screens.poster_bar_on_multiday = { ids: await ids(page, POSTER_BAR) };
  const openBtn = page.locator('[data-testid="poster-open"]');
  if ((await openBtn.count()) > 0) {
    await openBtn.first().tap().catch(async () => openBtn.first().click());
    await page.waitForTimeout(2500);
    const days = await page.locator('[data-testid="poster-days"]').count();
    const stops = await page.locator('[data-testid="poster-stop"]').count();
    report.screens.poster_sheet = {
      days_blocks: days,
      stop_blocks: stops,
      title: await page.locator('[data-testid="poster-title"]').first().innerText().catch(() => null),
      subtitle: await page.locator('[data-testid="poster-subtitle"]').first().innerText().catch(() => null),
      attribution: await page.locator('[data-testid="poster-attribution"]').first().innerText().catch(() => null),
      ids: await ids(page, POSTER_BAR),
      shot: await shot(page, "poster_sheet_r3"),
    };
    const dl = page.locator('[data-testid="poster-download"]');
    if ((await dl.count()) > 0) {
      const downloadPromise = page.waitForEvent("download", { timeout: 30000 }).catch(() => null);
      await dl.first().tap().catch(async () => dl.first().click());
      const dl2 = await downloadPromise;
      if (dl2) {
        const saveTo = path.join(OUT, `poster_download_r3_${dl2.suggestedFilename()}`);
        await dl2.saveAs(saveTo);
        const buf = fs.readFileSync(saveTo);
        report.screens.poster_download = {
          suggested_filename: dl2.suggestedFilename(),
          saved_bytes: buf.length,
          saved_sha1: crypto.createHash("sha1").update(buf).digest("hex"),
          path: saveTo.replace(/\\/g, "/"),
        };
      } else {
        report.screens.poster_download = { status: "NO_DOWNLOAD_EVENT", result_text: await page.locator('[data-testid="poster-result"]').first().innerText().catch(() => null) };
      }
    }
  }

  /* --- the empty trip: the poster entry must not appear, and the footprint set is honestly empty ---
   * A fourth journey is created here only for the walk and deleted again; the seeded board itself
   * keeps its three, which is what the seed script's invariants read back. */
  const emptyJourney = await post(`${BACKEND}/api/v1/journeys`, {
    traveler_id: journeys.body[0].traveler_id,
    title: "ORD-0489 走查用空行程",
    city_code: "CN-FUZHOU",
    timezone: "Asia/Shanghai",
    start_at: "2026-11-02T10:00:00+08:00",
    end_at: "2026-11-03T16:00:00+08:00",
    budget: { currency: "CNY", amount_minor: 200000 },
    planning_mode: "balanced",
    party_size: 1,
    arrival_anchor: { at: "2026-11-02T10:00:00+08:00", location: "Fuzhou Railway Station" },
  });
  const emptyId = emptyJourney.body?.id;
  if (emptyId) {
    await page.goto(`${PREVIEW}/v8/${emptyId}`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2200);
    await page.goto(`${PREVIEW}/v8/trips`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2200);
    report.screens.empty_trip_poster_gate = {
      journey_id: emptyId,
      ids: await ids(page, POSTER_BAR),
      itinerary_has_stops: await page.locator('[data-testid="trip-itinerary"]').count(),
      rendered: (await page.evaluate(() => document.body.innerText)).replace(/\s+/g, " ").trim().slice(0, 400),
      shot: await shot(page, "empty_trip_poster_absent_r3"),
    };
    await page.goto(`${PREVIEW}/v8/footprints`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1800);
    report.screens.empty_trip_footprint = { ids: await ids(page, FOOT), shot: await shot(page, "empty_trip_footprint_r3") };
    await fetch(`${BACKEND}/api/v1/journeys/${emptyId}`, { method: "DELETE" });
  }

  await ctx.close();
  await browser.close();
  report.finished_at = new Date().toISOString();
  const stamp = report.finished_at.replace(/[-:]/g, "").slice(0, 13);
  const file = path.join(OUT, `walk_candidate_r3_${stamp}.json`);
  fs.writeFileSync(file, JSON.stringify(report, null, 1), "utf-8");
  console.log(JSON.stringify({ evidence: file.replace(/\\/g, "/"), screens: Object.keys(report.screens) }));
})().catch((exc) => {
  console.error("WALK_R3_FAILED", exc && exc.message ? exc.message : exc);
  process.exit(1);
});
