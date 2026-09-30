/* ORD-0504 · walk the empty-catalogue screen on two generations, and run both mutants for real.
 *
 * Reads are `innerText` and mounted testids only.  Two viewport shapes (390x844 touch, 1280x900).
 * Screenshots carry ASCII names.  Nothing here trusts a status code as proof of what the screen
 * says, and nothing prints an identifier: the checks below look for uuid-shaped text on the screen
 * and fail the run if the product painted one.
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const GEN = {
  patched: { url: process.env.CNX_PATCHED || "http://127.0.0.1:8793", asset: "dist504" },
  base: { url: process.env.CNX_BASE || "http://127.0.0.1:8794", asset: "dist504base" },
};
const BACKEND = process.env.CNX_BACKEND || "http://127.0.0.1:8790";
const OUT = "D:/moodle/_qoder_seed_ord0489/evidence/ord0504";
fs.mkdirSync(OUT, { recursive: true });

const api = async (method, p, body) => {
  const res = await fetch(BACKEND + p, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch { json = { raw: text.slice(0, 300) }; }
  return { status: res.status, bytes: Buffer.byteLength(text), body: json };
};

const uuidish = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i;
const placeKeyish = /\breal-place-[0-9a-f]{6,}\b|\bplace-beijing-|\bplace-city-/;
const internalKey = /\bcity_code\s*=|\bCN-FUZHOU\b|\bCN-TIANJIN\b|\bcapability\b|\breason_code\b/;

async function sheetState(page) {
  const ids = ["plan-ai-sheet", "plan-ai-catalogue-count", "plan-ai-next-step", "plan-ai-import-entry", "plan-ai-blocked-note"];
  const out = {};
  for (const id of ids) {
    const loc = page.locator(`[data-testid="${id}"]`);
    const n = await loc.count();
    out[id] = { present: n, text: n ? (await loc.first().innerText()).replace(/\s+/g, " ").trim().slice(0, 240) : null };
  }
  const body = (await page.evaluate(() => document.body.innerText || "")).replace(/\s+/g, " ");
  out.screen_leaks = {
    uuid_like: (body.match(new RegExp(uuidish, "g")) || []).slice(0, 3),
    place_key_like: (body.match(new RegExp(placeKeyish, "g")) || []).slice(0, 3),
    internal_wording_like: (body.match(new RegExp(internalKey, "g")) || []).slice(0, 3),
  };
  out.body_chars = body.length;
  out.buttons = (await page.locator("button").allInnerTexts()).map((t) => t.replace(/\s+/g, " ").trim()).filter(Boolean).slice(0, 30);
  return out;
}

/* Only a button the traveller can see counts as an entry.  The mobile nav row is in the DOM but
 * `offsetWidth` is 0 until the menu opens, and clicking one of those is how the first pass of this
 * driver spent 30 s on a click that never landed. */
async function clickVisibleButton(page, scope, pattern, timeout = 8000) {
  const buttons = page.locator(`${scope || "page"} button`.replace("page button", "button"));
  const n = await buttons.count();
  const tried = [];
  for (let i = 0; i < n; i += 1) {
    const b = buttons.nth(i);
    if (!(await b.isVisible().catch(() => false))) continue;
    const label = (await b.textContent().catch(() => "")).replace(/\s+/g, " ").trim();
    if (!pattern.test(label)) continue;
    tried.push(label.slice(0, 28));
    await b.click({ timeout }).catch(() => {});
    await page.waitForTimeout(1200);
    return { clicked: label.slice(0, 28), tried };
  }
  return { clicked: null, tried };
}

async function openSheet(page) {
  /* The product's own control first, then the words a traveller would read - and either way the
   * pressed label is part of the reading. */
  const byTestid = page.locator('[data-testid="hub-plan-with-ai"]');
  if ((await byTestid.count()) > 0 && (await byTestid.first().isVisible().catch(() => false))) {
    await byTestid.first().click({ timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(1400);
    if ((await page.locator('[data-testid="plan-ai-sheet"]').count()) > 0) {
      return { pressed: { label: (await byTestid.first().textContent() || "").trim(), via: "testid hub-plan-with-ai" } };
    }
  }
  const res = await clickVisibleButton(page, null, /排行程|帮我规划|AI|方案|生成/);
  await page.waitForTimeout(1000);
  return { pressed: res.clicked ? { label: res.clicked, via: "visible label" } : null, tried: res.tried };
}

async function submitInSheet(page, words) {
  const box = page.locator('[data-testid="plan-ai-sheet"] textarea').first();
  if ((await box.count()) === 0) return { box: false };
  await box.fill(words);
  await page.waitForTimeout(500);
  const res = await clickVisibleButton(page, '[data-testid="plan-ai-sheet"]', /开始规划|排|生成|提交|发送/);
  return { box: true, ...res };
}

async function waitForBlocked(page, ms = 90000) {
  const deadline = Date.now() + ms;
  while (Date.now() < deadline) {
    const text = await page.evaluate(() => document.body.innerText || "");
    if (/排不出方案|No plan this time|服务器回读|没能从服务器读到/.test(text)) return { blocked: true, waited_ms: ms - (deadline - Date.now()) };
    await page.waitForTimeout(1500);
  }
  return { blocked: false, waited_ms: ms };
}

const shot = async (page, name) => {
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return { file: file.replace(/\\/g, "/"), bytes: fs.statSync(file).size };
};

(async () => {
  const report = { started_at: new Date().toISOString(), backend: BACKEND, generations: {}, runs: [] };

  /* board preconditions, all through product doors */
  const journeys = (await api("GET", "/api/v1/journeys")).body;
  const bin = (await api("GET", "/api/v1/recycle-bin/journeys")).body;
  let fuzhou = journeys.find((j) => j.city_code === "CN-FUZHOU") || null;
  if (!fuzhou && bin.length) {
    const back = await api("POST", `/api/v1/journeys/${bin[0].id}/undelete`, {});
    report.undelete_fuzhou = { status: back.status, city: back.body?.city_code };
    fuzhou = (await api("GET", "/api/v1/journeys")).body.find((j) => j.city_code === "CN-FUZHOU") || null;
  }
  /* a scratch trip in a city that resolves but holds no rows yet - this is what proves the sentence
   * is read from the server and not remembered */
  const created = await api("POST", "/api/v1/journeys", {
    traveler_id: journeys[0].traveler_id,
    title: "ORD-0504 走查 · 广州两日",
    city_code: "CN-GUANGZHOU",
    timezone: "Asia/Shanghai",
    start_at: "2026-11-10T09:00:00+08:00",
    end_at: "2026-11-11T18:00:00+08:00",
    budget: { currency: "CNY", amount_minor: 400000 },
    planning_mode: "balanced",
    party_size: 2,
    arrival_anchor: { at: "2026-11-10T09:00:00+08:00", location: "Guangzhou South Railway Station" },
  });
  report.scratch_journey = { status: created.status, id: created.body?.id, city_code: created.body?.city_code };
  report.places_before = {};
  for (const city of ["CN-FUZHOU", "CN-GUANGZHOU"]) {
    const rows = await api("GET", `/api/v1/places?city_code=${city}`);
    report.places_before[city] = Array.isArray(rows.body) ? rows.body.length : rows.status;
  }

  const browser = await chromium.launch();
  for (const shapeName of ["phone", "desktop"]) {
    const ctx = await browser.newContext(
      shapeName === "phone"
        ? { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, deviceScaleFactor: 3, locale: "zh-CN" }
        : { viewport: { width: 1280, height: 900 }, locale: "zh-CN" }
    );
    const page = await ctx.newPage();

    for (const gen of ["patched", "base"]) {
      const base = GEN[gen].url;
      const entry = { shape: shapeName, generation: gen, steps: [] };
      report.runs.push(entry);
      await page.goto(`${base}/v8/${report.scratch_journey.id}`, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(2600);
      const opened = await openSheet(page);
      entry.steps.push({ action: "open sheet", ...opened });
      if (!opened.pressed) { await ctx.close(); continue; }
      const submit = await submitInSheet(page, "帮我排一天，想喝咖啡和看老建筑");
      entry.steps.push({ action: "submit", ...submit });
      const blocked = await waitForBlocked(page);
      entry.steps.push({ action: "wait blocked", ...blocked });
      entry.sheet_readback = await sheetState(page);
      entry.shot_before_import = await shot(page, `sheet_${gen}_${shapeName}_blocked`);

      if (gen === "patched" && entry.sheet_readback["plan-ai-import-entry"].present > 0) {
        await page.locator('[data-testid="plan-ai-import-entry"]').first().click();
        await page.waitForTimeout(2600);
        entry.after_press = {
          url: page.url(),
          poi_import_panel: await page.locator('[data-testid="poi-import"]').count(),
          panel_testids: await page.evaluate(() => Array.from(document.querySelectorAll("[data-testid]")).map((e) => e.getAttribute("data-testid")).filter((t) => /poi-import/.test(t)).slice(0, 12)),
        };
        entry.shot_after_press = await shot(page, `import_screen_${shapeName}`);

        /* mutant B: paste something the empty catalogue cannot match, import zero rows, and read
         * the sentence again - it must not claim places exist */
        const ta = page.locator('textarea').first();
        if ((await ta.count()) > 0) {
          await ta.fill("一家不存在的老字号茶楼");
          const res = await clickVisibleButton(page, '[data-testid="poi-import"]', /识别|解析|提取|导入|粘贴|开始/);
          entry.zero_row_import_press = res;
          await page.waitForTimeout(4000);
          entry.zero_row_import = {
            counts: await page.locator('[data-testid="poi-import-counts"]').count()
              ? await page.locator('[data-testid="poi-import-counts"]').first().innerText() : null,
            empty: await page.locator('[data-testid="poi-import-empty"]').count(),
            error_why: await page.locator('[data-testid="poi-import-error-why"]').count()
              ? await page.locator('[data-testid="poi-import-error-why"]').first().innerText() : null,
            add_button: await page.locator('[data-testid="poi-import-add"]').count(),
            shot: await shot(page, `import_zero_rows_${shapeName}`),
          };
        }
      }
      if (gen === "base") {
        /* mutant A: on the unmodified generation the entry does not exist, so the refusal has no
         * way to the paste door from this screen.  Prove it by enumeration, not by absence of a
         * single selector. */
        entry.base_absence_evidence = {
          import_entry_present: entry.sheet_readback["plan-ai-import-entry"].present,
          catalogue_count_present: entry.sheet_readback["plan-ai-catalogue-count"].present,
          buttons_on_screen: entry.sheet_readback.buttons,
          any_button_reaching_import: entry.sheet_readback.buttons.filter((l) => /导入|粘贴|地点/.test(l)),
        };
      }
    }

    /* the live read-back proof, patched generation only, phone pass */
    if (shapeName === "phone") {
      const page2 = await ctx.newPage();
      const disc = await api("POST", `/api/v1/journeys/${report.scratch_journey.id}/real-city/discover`, {
        query: "cafe", radius_m: 2500, limit: 8, mode: "live",
      });
      const rowsAfter = await api("GET", "/api/v1/places?city_code=CN-GUANGZHOU");
      report.supply_write = {
        discover_status: disc.status,
        provenance: disc.body?.provenance,
        runtime_provenance: disc.body?.runtime_provenance,
        provider_status: disc.body?.provider_status,
        places_after: Array.isArray(rowsAfter.body) ? rowsAfter.body.length : rowsAfter.status,
      };
      await page2.goto(`${GEN.patched.url}/v8/${report.scratch_journey.id}`, { waitUntil: "domcontentloaded" });
      await page2.waitForTimeout(2600);
      const opened2 = await openSheet(page2);
      if (opened2.pressed) {
        const submit2 = await submitInSheet(page2, "帮我排一天，想喝咖啡和看老建筑");
        const blocked2 = await waitForBlocked(page2);
        report.after_supply = {
          open: opened2.pressed, submit: submit2.pressed, blocked: blocked2,
          readback: await sheetState(page2),
          shot: await shot(page2, "sheet_patched_after_real_write"),
        };
        const serverCount = report.supply_write.places_after;
        const painted = report.after_supply.readback["plan-ai-catalogue-count"].text || "";
        report.after_supply.agrees_with_server = painted.includes(String(serverCount));
      }
      await page2.close();
    }
    await ctx.close();
  }
  await browser.close();

  /* verdicts computed from the readings above, not asserted as literals */
  const patchedRun = report.runs.find((r) => r.generation === "patched" && r.shape === "phone");
  const baseRun = report.runs.find((r) => r.generation === "base" && r.shape === "phone");
  report.verdicts = {
    A_entry_absent_on_base: !!(baseRun && baseRun.base_absence_evidence && baseRun.base_absence_evidence.import_entry_present === 0
      && baseRun.base_absence_evidence.any_button_reaching_import.length === 0),
    B_entry_reaches_import_on_patched: !!(patchedRun && patchedRun.after_press && patchedRun.after_press.poi_import_panel > 0),
    C_count_sentence_is_server_sourced: !!(report.after_supply && report.after_supply.agrees_with_server
      && report.supply_write.provenance === "LIVE_PROVIDER"),
    D_no_identifier_painted: report.runs.every((r) => {
      const leak = r.sheet_readback && r.sheet_readback.screen_leaks;
      return !leak || (leak.uuid_like.length === 0 && leak.place_key_like.length === 0);
    }),
    E_zero_import_does_not_claim_places: (() => {
      const z = patchedRun && patchedRun.zero_row_import;
      if (!z) return false;
      const counts = (z.counts || "") + (z.empty || "") ;
      return !/\d+ 个地点|已有/.test(String(counts));
    })(),
  };
  report.finished_at = new Date().toISOString();
  const stamp = report.finished_at.replace(/[-:]/g, "").slice(0, 13);
  const file = path.join(OUT, `walk_ord0504_r1_${stamp}.json`);
  fs.writeFileSync(file, JSON.stringify(report, null, 1), "utf-8");
  console.log(JSON.stringify({ evidence: file.replace(/\\/g, "/"), verdicts: report.verdicts, supply: report.supply_write.provenance }, null, 1));
})().catch((exc) => {
  console.error("ORD0504_WALK_FAILED", exc && exc.stack ? String(exc.stack).split("\n").slice(0, 3).join(" | ") : exc);
  process.exit(1);
});
