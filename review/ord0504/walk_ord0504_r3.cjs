/* ORD-0504 · third pass, with the three judging mistakes of r2 corrected:
 *   - mutant A now actually submits a request, so the refusal is on screen when it is judged;
 *   - the count-change proof uses a city that goes 0 -> 1 places, which is the only way to keep the
 *     run inside a catalogue-shaped refusal (8 places plans fine and the line never has to appear);
 *   - the zero-row paste is done against the city that has no rows, i.e. the one where the import
 *     can match nothing;
 *   - the unreadable state is judged after the code was extended to cover PLACES_HTTP_*.
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const PATCHED = process.env.CNX_PATCHED || "http://127.0.0.1:8793";
const BASE = process.env.CNX_BASE || "http://127.0.0.1:8794";
const BACKEND = process.env.CNX_BACKEND || "http://127.0.0.1:8790";
const OUT = "D:/moodle/_qoder_seed_ord0489/evidence/ord0504";
fs.mkdirSync(OUT, { recursive: true });

const api = async (method, p, body) => {
  const res = await fetch(BACKEND + p, { method, headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
  const text = await res.text();
  let json = null; try { json = JSON.parse(text); } catch { json = { raw: text.slice(0, 240) }; }
  return { status: res.status, body: json };
};
const doorCount = async (code) => {
  const r = await api("GET", `/api/v1/places?city_code=${code}`);
  return Array.isArray(r.body) ? r.body.length : `status_${r.status}`;
};

const WORDS = "帮我排一天，想喝咖啡和看老建筑";

async function refuse(page, origin, journeyId) {
  await page.goto(`${origin}/v8/${journeyId}`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2400);
  const opener = page.locator('[data-testid="hub-plan-with-ai"]');
  await opener.first().click({ timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(1200);
  const sheetUp = (await page.locator('[data-testid="plan-ai-sheet"]').count()) > 0;
  if (!sheetUp) return { sheetUp: false };
  await page.locator('[data-testid="plan-ai-sheet"] textarea').first().fill(WORDS);
  await page.waitForTimeout(400);
  const go = page.locator('[data-testid="plan-ai-sheet"] button', { hasText: /开始规划|排|生成/ }).first();
  const pressed = (await go.innerText().catch(() => "")).replace(/\s+/g, " ").trim();
  await go.click({ timeout: 8000 }).catch(() => {});
  const deadline = Date.now() + 150000;
  while (Date.now() < deadline) {
    const btns = await page.evaluate(() => Array.from(document.querySelectorAll('[data-testid="plan-ai-sheet"] button')).map((el) => (el.textContent || "").replace(/\s+/g, " ").trim()).filter(Boolean));
    const note = await page.evaluate(() => (document.querySelector('[data-testid="plan-ai-sheet"]')?.innerText || "").replace(/\s+/g, " "));
    if (/排不出方案|No plan this time|服务器回读|没能从服务器读到/.test(note)) {
      return { sheetUp: true, pressed, sheet_buttons: btns, note_head: note.slice(0, 420) };
    }
    await page.waitForTimeout(1500);
  }
  return { sheetUp: true, pressed, timed_out: true, note_head: await page.evaluate(() => (document.querySelector('[data-testid="plan-ai-sheet"]')?.innerText || "").replace(/\s+/g, " ").slice(0, 300)) };
}

async function readIds(page) {
  const ids = ["plan-ai-catalogue-count", "plan-ai-import-entry", "plan-ai-next-step"];
  const out = {};
  for (const id of ids) {
    const loc = page.locator(`[data-testid="${id}"]`);
    const n = await loc.count();
    out[id] = { present: n, text: n ? (await loc.first().innerText()).replace(/\s+/g, " ").trim().slice(0, 200) : null };
  }
  const body = await page.evaluate(() => document.body.innerText || "");
  out.leaks = {
    uuid: (body.match(/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi) || []).slice(0, 3),
    place_key: (body.match(/\breal-place-[0-9a-f]{6,}\b/g) || []).slice(0, 3),
    internal: (body.match(/\bCN-[A-Z]{5,}\b|city_code=|reason_code\b/g) || []).slice(0, 3),
  };
  return out;
}

const shot = async (page, name) => {
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return { file: file.replace(/\\/g, "/"), bytes: fs.statSync(file).size };
};

(async () => {
  const report = { started_at: new Date().toISOString(), steps: {} };
  let journeys = (await api("GET", "/api/v1/journeys")).body;
  if (!journeys.some((j) => j.city_code === "CN-FUZHOU")) {
    const bin = (await api("GET", "/api/v1/recycle-bin/journeys")).body;
    const fz = bin.find((b) => b.city_code === "CN-FUZHOU") || bin[0];
    if (fz) await api("POST", `/api/v1/journeys/${fz.id}/undelete`, {});
    journeys = (await api("GET", "/api/v1/journeys")).body;
  }
  const fuzhou = journeys.find((j) => j.city_code === "CN-FUZHOU");
  report.fuzhou_id = fuzhou ? fuzhou.id : null;
  report.fuzhou_door = fuzhou ? await doorCount("CN-FUZHOU") : null;

  const browser = await chromium.launch();
  for (const shape of ["phone", "desktop"]) {
    const opts = shape === "phone"
      ? { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, deviceScaleFactor: 3, locale: "zh-CN" }
      : { viewport: { width: 1280, height: 900 }, locale: "zh-CN" };
    const ctx = await browser.newContext(opts);
    const p = await ctx.newPage();

    /* --- mutant A: the same refusal on the unmodified generation --- */
    const a = await refuse(p, BASE, report.fuzhou_id);
    const aIds = await readIds(p);
    report[`A_base_${shape}`] = { ...a, ids: aIds, sheet_buttons_matching_import: (a.sheet_buttons || []).filter((l) => /导入|粘贴/.test(l)), shot: await shot(p, `A_base_refusal_${shape}`) };

    /* --- the patched pair: same journey, same words --- */
    const b = await refuse(p, PATCHED, report.fuzhou_id);
    const bIds = await readIds(p);
    report[`B_patched_refusal_${shape}`] = { ...b, ids: bIds, shot: await shot(p, `B_patched_refusal_${shape}`) };
    if ((bIds["plan-ai-import-entry"].present || 0) > 0) {
      await p.locator('[data-testid="plan-ai-import-entry"]').first().click({ timeout: 8000 }).catch(() => {});
      await p.waitForTimeout(2600);
      report[`B_patched_refusal_${shape}`].after_press = {
        url: p.url(),
        poi_panel: await p.locator('[data-testid="poi-import"]').count(),
        journey_still_empty_city: (p.url().includes("/v8/import")),
      };
      report[`B_patched_refusal_${shape}`].shot_after = await shot(p, `C_import_from_refusal_${shape}`);

      /* --- the zero-row paste, on the city that holds no rows --- */
      const ta = p.locator('[data-testid="poi-import-text"]');
      if ((await ta.count()) > 0) {
        await ta.first().fill("一家根本不存在的老字号茶楼");
        await p.waitForTimeout(500);
        const parse = p.locator('[data-testid="poi-import-parse"]');
        if ((await parse.count()) > 0) await parse.first().click({ timeout: 8000 }).catch(() => {});
        await p.waitForTimeout(6000);
        const readT = async (id) => {
          const loc = p.locator(`[data-testid="${id}"]`);
          return (await loc.count()) > 0 ? (await loc.first().innerText()).replace(/\s+/g, " ").trim().slice(0, 200) : null;
        };
        report[`D_zero_row_import_${shape}`] = {
          counts: await readT("poi-import-counts"),
          empty_words: await readT("poi-import-empty"),
          scope_hint: await readT("poi-import-scope-hint"),
          error_why: await readT("poi-import-error-why"),
          cards: await p.locator('[data-testid="poi-import-card"]').count(),
          add_button: await p.locator('[data-testid="poi-import-add"]').count(),
          shot: await shot(p, `D_zero_row_import_${shape}`),
        };
      }
      /* the sentence back on the refusal screen must still not claim places */
      const again = await refuse(p, PATCHED, report.fuzhou_id);
      report[`D_zero_row_import_${shape}`].sentence_after = again.note_head;
      report[`D_zero_row_import_${shape}`].ids_after = await readIds(p);
    }
    await ctx.close();
  }

  /* --- the count actually follows the store: 0 -> 1 places, refusal kept --- */
  const made = await api("POST", "/api/v1/journeys", {
    traveler_id: (await api("GET", "/api/v1/journeys")).body[0].traveler_id,
    title: "ORD-0504 走查 · 厦门一日",
    city_code: "CN-XIAMEN",
    timezone: "Asia/Shanghai",
    start_at: "2026-11-18T09:00:00+08:00",
    end_at: "2026-11-18T18:00:00+08:00",
    budget: { currency: "CNY", amount_minor: 200000 }, planning_mode: "balanced", party_size: 1,
  });
  report.xiamen = { status: made.status, id: made.body?.id };
  const ctx2 = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, locale: "zh-CN" });
  const p2 = await ctx2.newPage();
  const beforeDoor = await doorCount("CN-XIAMEN");
  const r0 = await refuse(p2, PATCHED, report.xiamen.id);
  report.E_before_supply = { door: beforeDoor, note: r0.note_head, ids: await readIds(p2), shot: await shot(p2, "E_xiamen_zero") };
  await new Promise((r) => setTimeout(r, 20000));
  const disc = await api("POST", `/api/v1/journeys/${report.xiamen.id}/real-city/discover`, { query: "cafe", radius_m: 3000, limit: 1, mode: "live" });
  const afterDoor = await doorCount("CN-XIAMEN");
  report.supply_one = { status: disc.status, provenance: disc.body?.provenance, candidates: (disc.body?.candidates || []).length, door_after: afterDoor };
  await new Promise((r) => setTimeout(r, 15000));
  const r1 = await refuse(p2, PATCHED, report.xiamen.id);
  report.E_after_one_place = { door: afterDoor, note: r1.note_head, ids: await readIds(p2), shot: await shot(p2, "E_xiamen_one") };
  report.E_agrees_with_door = String((report.E_after_one_place.ids["plan-ai-catalogue-count"] || {}).text || "").includes(String(afterDoor));

  /* --- unreadable: the door refuses, the sentence must say so and show no number --- */
  const ctx3 = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: "zh-CN" });
  const p3 = await ctx3.newPage();
  await p3.route("**/api/v1/places*", (route) => route.fulfill({ status: 503, contentType: "application/json", body: '{"error":{"code":"UNAVAILABLE","message":"down"}}' }));
  const r2 = await refuse(p3, PATCHED, report.xiamen.id);
  report.F_unreadable = { note: r2.note_head, ids: await readIds(p3), shot: await shot(p3, "F_door_unreadable") };
  const painted = (report.F_unreadable.ids["plan-ai-catalogue-count"] || {}).text || "";
  report.F_says_unreadable_without_number = /没能从服务器读到/.test(painted) && !/\d/.test(painted);

  await browser.close();
  report.finished_at = new Date().toISOString();
  const stamp = report.finished_at.replace(/[-:]/g, "").slice(0, 13);
  const file = path.join(OUT, `walk_ord0504_r3_${stamp}.json`);
  fs.writeFileSync(file, JSON.stringify(report, null, 1), "utf-8");
  console.log(JSON.stringify({ evidence: file.replace(/\\/g, "/"), fuzhou_door: report.fuzhou_door, E: report.E_agrees_with_door, F: report.F_says_unreadable_without_number }, null, 1));
})().catch((exc) => {
  console.error("R3_FAILED", exc && exc.message ? exc.message : exc);
  process.exit(1);
});
