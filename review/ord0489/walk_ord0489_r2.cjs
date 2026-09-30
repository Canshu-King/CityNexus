/* ORD-0489 · walk the built frontend on the board this lane seeded, and read what paints.
 *
 * One Chromium lane, two shapes (390x844 touch, 1280x900 desktop).  Every reading is rendered
 * text or a visible control's own label; a `data-*` attribute is never accepted as the screen.
 * Screenshots get ASCII names because CJK filenames collide and silently overwrite each other.
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const PREVIEW = process.env.CNX_PREVIEW || "http://127.0.0.1:8791";
const BACKEND = process.env.CNX_BACKEND || "http://127.0.0.1:8790";
const OUT = process.env.CNX_EVIDENCE || "D:/moodle/_qoder_seed_ord0489/evidence/ord0489_screens";
fs.mkdirSync(OUT, { recursive: true });

const readJson = async (url) => {
  const res = await fetch(url);
  const text = await res.text();
  let body = null;
  try { body = JSON.parse(text); } catch { body = { raw: text.slice(0, 400) }; }
  return { status: res.status, bytes: Buffer.byteLength(text), body };
};

const postJson = async (url, body, headers = {}) => {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body ?? {}),
  });
  const text = await res.text();
  let parsed = null;
  try { parsed = JSON.parse(text); } catch { parsed = { raw: text.slice(0, 400) }; }
  return { status: res.status, bytes: Buffer.byteLength(text), body: parsed };
};

async function textOf(page, sel) {
  const loc = page.locator(sel).first();
  if ((await loc.count()) === 0) return null;
  return (await loc.innerText()).replace(/\s+/g, " ").trim();
}

async function testidReadings(page, ids) {
  const out = {};
  for (const id of ids) {
    const loc = page.locator(`[data-testid="${id}"]`);
    const count = await loc.count();
    out[id] = {
      present: count,
      text: count ? (await loc.first().innerText()).replace(/\s+/g, " ").trim().slice(0, 260) : null,
    };
  }
  return out;
}

/* The screen's own identity, read off what mounted: every visible testid, in DOM order. */
async function mountedTestids(page) {
  return page.evaluate(() =>
    Array.from(document.querySelectorAll("[data-testid]")).map((el) => el.getAttribute("data-testid"))
  );
}

/* Rendered option order of a <select> is what a traveller actually sees listed. */
async function pickerOrder(page, testid) {
  const loc = page.locator(`[data-testid="${testid}"]`);
  if ((await loc.count()) === 0) return { present: 0, options: [] };
  return {
    present: await loc.count(),
    options: (await loc.locator("option").allInnerTexts()).map((t) => t.replace(/\s+/g, " ").trim()),
  };
}

async function shot(page, name) {
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return { file: file.replace(/\\/g, "/"), bytes: fs.statSync(file).size };
}

async function mountCheck(page, url) {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForFunction(() => {
    const root = document.getElementById("root");
    return !!root && root.children.length > 0 && (document.body.innerText || "").trim().length > 40;
  }, { timeout: 30000 }).catch(() => {});
  return {
    root_children: await page.evaluate(() => (document.getElementById("root")?.children || []).length),
    body_chars: await page.evaluate(() => (document.body.innerText || "").length),
    sw_controlled: await page.evaluate(async () => {
      const reg = await navigator.serviceWorker?.getRegistration?.("/");
      return reg ? "registered" : "none";
    }),
    lang: await page.evaluate(() => document.documentElement.lang || null),
  };
}

(async () => {
  const report = { preview: PREVIEW, backend: BACKEND, started_at: new Date().toISOString(), screens: {} };

  const journeys = await readJson(`${BACKEND}/api/v1/journeys`);
  report.journeys_door = { status: journeys.status, rows: journeys.body.length };
  report.journey_order_from_server = journeys.body.map((j) => j.title);
  const bin = await readJson(`${BACKEND}/api/v1/recycle-bin/journeys`);
  report.recycle_bin_door = { status: bin.status, rows: bin.body.map((r) => r.title ?? r.journey_id) };
  const tianjin = journeys.body.find((j) => j.city_code === "CN-TIANJIN");
  const beijing = journeys.body.find((j) => j.city_code === "CN-BEIJING");

  const grantsTj = await readJson(`${BACKEND}/api/v1/journeys/${tianjin.id}/share-grants`);
  const grantsBj = await readJson(`${BACKEND}/api/v1/journeys/${beijing.id}/share-grants`);
  const liveToken = grantsTj.body.find((g) => !g.revoked_at)?.token ?? null;
  const revokedToken = grantsBj.body.find((g) => g.revoked_at)?.token ?? null;
  report.grants = {
    tianjin: grantsTj.body.map((g) => ({ id: g.id, revoked: !!g.revoked_at, visibility: g.visibility })),
    beijing: grantsBj.body.map((g) => ({ id: g.id, revoked: !!g.revoked_at, visibility: g.visibility })),
    live_token_len: liveToken ? liveToken.length : 0,
    revoked_token_len: revokedToken ? revokedToken.length : 0,
  };

  /* The third share state: the key the seed cut while the trip was still live, now that the trip
   * sits in the bin.  It is read from the grants door, not re-cut here - cutting a second key is a
   * different question (and the seed already measured that the door allows it). */
  const binned = bin.body[0];
  let binnedGrant = null;
  report.binned_row_keys = binned ? Object.keys(binned).slice(0, 24) : [];
  if (binned) {
    const created = await readJson(`${BACKEND}/api/v1/journeys/${binned.id}/share-grants`);
    const rows = Array.isArray(created.body) ? created.body : [];
    report.grants.binned_trip_grants = rows.map((g) => ({
      id: g.id,
      revoked: !!g.revoked_at,
      created_at: g.created_at,
      deleted_at_on_trip: binned.deleted_at,
      bin_state: binned.bin_state,
    }));
    binnedGrant = (rows.sort((a, b) => String(a.created_at).localeCompare(String(b.created_at)))[0] || {}).token ?? null;
    report.grants.binned_trip_grant_used = { token_len: binnedGrant ? binnedGrant.length : 0, which: "earliest created_at = cut before the bin" };
  }

  const browser = await chromium.launch();
  const shapes = [
    { name: "phone", opts: { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, deviceScaleFactor: 3, locale: "zh-CN" } },
    { name: "desktop", opts: { viewport: { width: 1280, height: 900 }, locale: "zh-CN" } },
  ];

  for (const shape of shapes) {
    const ctx = await browser.newContext(shape.opts);
    const page = await ctx.newPage();
    const S = {};
    report.screens[shape.name] = S;

    /* 1. the trip list screen (members/access panel holds the only journey list control) */
    /* `/v8/access` behind the onboarding gate paints the wizard, not the panel (measured on r1:
     * every access-* testid absent, 168 chars of body).  Enter through a journey address, which is
     * the door the shell honours, then ask for the panel. */
    await page.goto(`${PREVIEW}/v8/${tianjin.id}`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2200);
    await page.goto(`${PREVIEW}/v8/access`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2200);
    const m1 = { mounted_via: "journey address then /v8/access", ...(await mountCheck(page, `${PREVIEW}/v8/access`)) };
    S.access = {
      mount: m1,
      picker: await pickerOrder(page, "access-journey-picker"),
      ids: await testidReadings(page, ["access-panel", "access-journey-picker", "access-chosen", "access-trips-empty", "access-grant-list", "access-roster-empty"]),
      heading: await textOf(page, ".v8-page, .cn-access, main"),
      shot: await shot(page, `access_${shape.name}_a_two_rows`),
    };

    /* 2. change the store, re-read the same control: the list order is the store order */
    if (binned) {
      const back = await postJson(`${BACKEND}/api/v1/journeys/${binned.id}/undelete`, {});
      report.undelete = { status: back.status, title: back.body?.title };
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForTimeout(1500);
      S.access_after_undelete = {
        picker: await pickerOrder(page, "access-journey-picker"),
        rows_from_door: (await readJson(`${BACKEND}/api/v1/journeys`)).body.map((j) => j.title),
        shot: await shot(page, `access_${shape.name}_b_three_rows`),
      };
      const rebin = await fetch(`${BACKEND}/api/v1/journeys/${binned.id}`, { method: "DELETE" });
      report.rebin = { status: rebin.status };
    }

    /* 3. the trip workspace, on the trip that has a 10-activity plan */
    await page.goto(`${PREVIEW}/v8/${tianjin.id}`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2500);
    await page.goto(`${PREVIEW}/v8/trips`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2500);
    S.trips = {
      mount: { root_children: await page.evaluate(() => (document.getElementById("root")?.children || []).length), body_chars: await page.evaluate(() => (document.body.innerText || "").length) },
      tabs: await testidReadings(page, ["trips-tabs", "trips-commitments", "trips-spend"]),
      mounted_ids: (await mountedTestids(page)).slice(0, 120),
      rendered_head: (await page.evaluate(() => document.body.innerText)).replace(/\s+/g, " ").trim().slice(0, 700),
      shot: await shot(page, `trips_${shape.name}`),
    };

    /* 4. footprint and long-image export: ask every route this shell knows, and print what mounted */
    const probeRoutes = ["hub", "trips", "studio", "map", "me", "live", "stay", "discover", "bookings", "trash", "access", "twin", "agent", "intelligence", "authoritative", "import"];
    const footprintSweep = {};
    for (const r of probeRoutes) {
      await page.goto(`${PREVIEW}/v8/${r}`, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(900);
      const ids = await mountedTestids(page);
      const text = (await page.evaluate(() => document.body.innerText || "")).replace(/\s+/g, " ");
      footprintSweep[r] = {
        mounted_count: ids.length,
        footprint_or_checkin_ids: ids.filter((i) => /footprint|checkin|stamp/i.test(i)),
        poster_or_longimage_ids: ids.filter((i) => /poster|longimage|long_image|export/i.test(i)),
        words: {
          足迹: (text.match(/足迹/g) || []).length,
          长图: (text.match(/长图/g) || []).length,
          打卡: (text.match(/打卡/g) || []).length,
          导出: (text.match(/导出/g) || []).length,
        },
      };
    }
    S.footprint_and_poster_sweep = footprintSweep;

    /* 5. the recycle bin screen */
    await page.goto(`${PREVIEW}/v8/trash`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1800);
    S.trash = {
      ids: await testidReadings(page, ["journey-trash-panel", "trash-count", "trash-list", "trash-row", "trash-row-title", "trash-row-state", "trash-outcome-text"]),
      rendered: (await page.evaluate(() => document.body.innerText)).replace(/\s+/g, " ").trim().slice(0, 400),
      shot: await shot(page, `trash_${shape.name}`),
    };

    await ctx.close();
  }

  /* 6. the share-receiving screen, three states + the no-token address */
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, locale: "zh-CN" });
  const page = await ctx.newPage();
  const SHARE_IDS = ["shared-screen", "shared-title", "shared-window", "shared-day-count", "shared-plan-row-missing", "shared-stop-name", "shared-refused", "shared-refusal-title", "shared-refusal-code", "shared-no-token", "shared-no-plan", "shared-plan-empty"];
  const states = [
    ["valid", liveToken],
    ["revoked", revokedToken],
    ["binned_trip", binnedGrant],
    ["unknown", "a".repeat(32)],
    ["absent", null],
  ];
  report.share_screen = {};
  for (const [label, token] of states) {
    const url = token ? `${PREVIEW}/v8/shared/${token}` : `${PREVIEW}/v8/shared/`;
    const mount = await mountCheck(page, url);
    const door = token ? await readJson(`${BACKEND}/api/v1/shared/journeys/${token}`) : null;
    report.share_screen[label] = {
      url_without_token_painted: token ? url.replace(token, "<token>") : url,
      mount,
      guest_door: door ? { status: door.status, reason_code: door.body?.error?.reason_code ?? null, plan_state: door.body?.plan_state ?? null, bytes: door.bytes } : "NOT_ASKED",
      ids: await testidReadings(page, SHARE_IDS),
      rendered: (await page.evaluate(() => document.body.innerText)).replace(/\s+/g, " ").trim().slice(0, 600),
      shot: await shot(page, `shared_${label}`),
    };
  }
  await ctx.close();

  await browser.close();
  report.finished_at = new Date().toISOString();
  const stamp = report.finished_at.replace(/[-:]/g, "").slice(0, 13);
  const file = path.join(OUT, `walk_r2_${stamp}.json`);
  fs.writeFileSync(file, JSON.stringify(report, null, 1), "utf-8");
  console.log(JSON.stringify({ evidence: file.replace(/\\/g, "/"), screens: Object.keys(report.screens), share_states: Object.keys(report.share_screen) }));
})().catch((exc) => {
  console.error("WALK_FAILED", exc && exc.message ? exc.message : exc);
  process.exit(1);
});
