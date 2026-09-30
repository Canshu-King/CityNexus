/* ORD-0504 · second pass: the read-back proof with a city that actually gets places, the paste
 * door pressed through its own controls, the unreadable state forced, and mutant A measured on the
 * sheet's own buttons instead of the page nav.
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
const cityCount = async (code) => {
  const r = await api("GET", `/api/v1/places?city_code=${code}`);
  return Array.isArray(r.body) ? r.body.length : `status_${r.status}`;
};

async function openAndSubmit(page, journeyId, words) {
  await page.goto(`${PATCHED}/v8/${journeyId}`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500);
  const opener = page.locator('[data-testid="hub-plan-with-ai"]');
  const openerVisible = (await opener.count()) > 0 && (await opener.first().isVisible().catch(() => false));
  if (openerVisible) await opener.first().click({ timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(1200);
  const sheetUp = (await page.locator('[data-testid="plan-ai-sheet"]').count()) > 0;
  if (!sheetUp) return { sheetUp: false, openerVisible };
  const box = page.locator('[data-testid="plan-ai-sheet"] textarea').first();
  await box.fill(words);
  await page.waitForTimeout(400);
  const go = page.locator('[data-testid="plan-ai-sheet"] button', { hasText: /开始规划|排|生成/ }).first();
  const pressed = await go.innerText().catch(() => null);
  await go.click({ timeout: 8000 }).catch(() => {});
  const deadline = Date.now() + 120000;
  let painted = null;
  while (Date.now() < deadline) {
    const loc = page.locator('[data-testid="plan-ai-catalogue-count"]');
    if ((await loc.count()) > 0) { painted = (await loc.first().innerText()).replace(/\s+/g, " ").trim(); break; }
    const blocked = await page.locator('[data-testid="plan-ai-next-step"]').count();
    if (blocked > 0 && (await page.locator('[data-testid="plan-ai-catalogue-count"]').count()) === 0) { painted = "ABSENT_ON_PATCHED"; break; }
    await page.waitForTimeout(1500);
  }
  return { sheetUp: true, openerVisible, pressed, painted, status_text: (await page.evaluate(() => document.body.innerText)).replace(/\s+/g, " ") };
}

const shot = async (page, name) => {
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return { file: file.replace(/\\/g, "/"), bytes: fs.statSync(file).size };
};

(async () => {
  const report = { started_at: new Date().toISOString(), runs: {} };
  const journeys = (await api("GET", "/api/v1/journeys")).body;
  const traveler = journeys[0].traveler_id;

  /* --- 1. find a city that this build can actually supply, and a journey in it --- */
  const candidates = ["CN-GUANGZHOU", "CN-CHENGDU"];
  /* Nominatim answers a single spaced request with 200 and punishes a burst; r2's first pass fired twelve
   * requests back to back and every one of them came back classified RESOLVER_UNREACHABLE. Cool down
   * and pace, and keep the attempts in the receipt either way. */
  await new Promise((r) => setTimeout(r, Number(process.env.CNX_COOLDOWN_MS || 75000)));
  const attempts = [];
  let chosen = null;
  for (const code of candidates) {
    const made = await api("POST", "/api/v1/journeys", {
      traveler_id: traveler,
      title: `ORD-0504 走查 · ${code} 两日`,
      city_code: code,
      timezone: "Asia/Shanghai",
      start_at: "2026-11-14T09:00:00+08:00",
      end_at: "2026-11-15T18:00:00+08:00",
      budget: { currency: "CNY", amount_minor: 400000 },
      planning_mode: "balanced",
      party_size: 2,
      arrival_anchor: { at: "2026-11-14T09:00:00+08:00", location: `${code.replace("CN-", "").toLowerCase()} railway station` },
    });
    if (made.status !== 201) { attempts.push({ code, create_status: made.status }); continue; }
    const id = made.body.id;
    const before = await cityCount(code);
    let after = before;
    for (const q of ["museum", "cafe"]) {
      const d = await api("POST", `/api/v1/journeys/${id}/real-city/discover`, { query: q, radius_m: 3000, limit: 8, mode: "live" });
      const c = d.body?.candidates?.length ?? null;
      after = await cityCount(code);
      attempts.push({ code, journey_id: id, query: q, provenance: d.body?.provenance, status: d.status, candidates: c, rows_after: after, anchor: d.body?.provider_status?.anchor });
      await new Promise((r) => setTimeout(r, 14000));
      if (typeof after === "number" && after >= 3) break;
    }
    if (typeof after === "number" && after >= 3) { chosen = { code, id, before, after }; break; }
  }
  report.supply_attempts = attempts;
  report.chosen_city = chosen;

  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, locale: "zh-CN" });

  /* --- 2. mutant A, measured on the sheet's own controls --- */
  if (chosen) {
    const empty = journeys.find((j) => j.city_code === "CN-FUZHOU") || null;
    const emptyId = empty ? empty.id : chosen.id;
    const baseCtx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, locale: "zh-CN" });
    const bp = await baseCtx.newPage();
    await bp.goto(`${BASE}/v8/${emptyId}`, { waitUntil: "domcontentloaded" });
    await bp.waitForTimeout(2500);
    await bp.locator('[data-testid="hub-plan-with-ai"]').first().click({ timeout: 8000 }).catch(() => {});
    await bp.waitForTimeout(1500);
    const sheetButtons = await bp.evaluate(() =>
      Array.from(document.querySelectorAll('[data-testid="plan-ai-sheet"] button')).map((el) => (el.textContent || "").replace(/\s+/g, " ").trim())
    );
    const navReachable = await bp.evaluate(() =>
      Array.from(document.querySelectorAll('[data-testid^="nav-"]')).map((el) => ({ t: el.getAttribute("data-testid"), vis: !!(el.offsetWidth || el.offsetHeight) }))
    );
    report.mutant_A = {
      generation: "base",
      sheet_up: (await bp.locator('[data-testid="plan-ai-sheet"]').count()) > 0,
      sheet_buttons: sheetButtons,
      buttons_reaching_import_in_sheet: sheetButtons.filter((l) => /导入|粘贴/.test(l)),
      nav_row_while_sheet_open: navReachable,
      shot: await shot(bp, "base_sheet_buttons"),
    };
    await baseCtx.close();

    /* --- 3. read-back after a real supply write: the sentence must equal the server's count --- */
    const pp = await ctx.newPage();
    const readPatched = await openAndSubmit(pp, chosen.id, "帮我排一天，想看博物馆和喝咖啡");
    const liveCount = await cityCount(chosen.code);
    report.readback_after_supply = {
      city_code: chosen.code,
      server_count_now: liveCount,
      painted_sentence: readPatched.painted,
      status_text_has_code: /CATALOG_INSUFFICIENT|CATALOG_EMPTY|服务器回的原因编号/.test(readPatched.status_text || ""),
      agrees: typeof liveCount === "number" && String(readPatched.painted || "").includes(String(liveCount)),
      shot: await shot(pp, "patched_sheet_after_supply"),
    };

    /* --- 4. the unreadable state forced on the door --- */
    const deadCtx = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: "zh-CN" });
    const dp = await deadCtx.newPage();
    await dp.route("**/api/v1/places*", (route) => route.fulfill({ status: 503, contentType: "application/json", body: '{"error":{"code":"UNAVAILABLE"}}' }));
    await dp.goto(`${PATCHED}/v8/${chosen.id}`, { waitUntil: "domcontentloaded" });
    await dp.waitForTimeout(2500);
    await dp.locator('[data-testid="hub-plan-with-ai"]').first().click({ timeout: 8000 }).catch(() => {});
    await dp.waitForTimeout(1200);
    await dp.locator('[data-testid="plan-ai-sheet"] textarea').first().fill("帮我排一天");
    await dp.locator('[data-testid="plan-ai-sheet"] button', { hasText: /开始规划|排|生成/ }).first().click({ timeout: 8000 }).catch(() => {});
    await dp.waitForTimeout(30000);
    const countText = await dp.locator('[data-testid="plan-ai-catalogue-count"]').first().innerText().catch(() => null);
    report.unreadable_state = {
      painted: countText && countText.replace(/\s+/g, " ").trim(),
      contains_digit_count: !!countText && /\d/.test(countText),
      server_count_was: liveCount,
      shot: await shot(dp, "patched_sheet_door_unreadable"),
    };
    await deadCtx.close();

    /* --- 5. mutant B: press the paste door's own controls with text that matches nothing --- */
    const ip = await ctx.newPage();
    await ip.goto(`${PATCHED}/v8/${chosen.id}`, { waitUntil: "domcontentloaded" });
    await ip.waitForTimeout(2200);
    await ip.goto(`${PATCHED}/v8/import`, { waitUntil: "domcontentloaded" });
    await ip.waitForTimeout(2600);
    const panelUp = (await ip.locator('[data-testid="poi-import"]').count()) > 0;
    const ta = ip.locator('[data-testid="poi-import-text"]');
    let pressedParse = null;
    if (panelUp && (await ta.count()) > 0) {
      await ta.first().fill("一家根本不存在的老字号茶楼");
      await ip.waitForTimeout(400);
      const parse = ip.locator('[data-testid="poi-import-parse"]');
      pressedParse = (await parse.count()) > 0;
      if (pressedParse) await parse.first().click({ timeout: 8000 }).catch(() => {});
      await ip.waitForTimeout(6000);
    }
    const readTestId = async (id) => {
      const loc = ip.locator(`[data-testid="${id}"]`);
      return (await loc.count()) > 0 ? (await loc.first().innerText()).replace(/\s+/g, " ").trim().slice(0, 220) : null;
    };
    report.mutant_B_import_zero_rows = {
      panel_up: panelUp,
      parse_control_pressed: pressedParse,
      counts: await readTestId("poi-import-counts"),
      empty_words: await readTestId("poi-import-empty"),
      error_why: await readTestId("poi-import-error-why"),
      error_detail: await readTestId("poi-import-error-detail"),
      add_button: await ip.locator('[data-testid="poi-import-add"]').count(),
      cards: await ip.locator('[data-testid="poi-import-card"]').count(),
      sheet_sentence_after: null,
      shot: await shot(ip, "paste_door_zero_rows"),
    };
    await ip.close();
    const afterZero = await openAndSubmit(pp, emptyId, "帮我排一天");
    report.mutant_B_import_zero_rows.sheet_sentence_after = afterZero.painted;
    report.mutant_B_import_zero_rows.sheet_claimed_places = !!afterZero.painted && /已有|有 \d+ 个地点/.test(afterZero.painted);
    await pp.close();
  }
  await ctx.close();
  await browser.close();

  report.verdicts = {
    A_no_import_entry_on_base_sheet: !!(report.mutant_A && report.mutant_A.buttons_reaching_import_in_sheet.length === 0 && report.mutant_A.nav_row_while_sheet_open.every((n) => n.vis !== true)),
    B_zero_import_sentence_does_not_claim_places: !!(report.mutant_B_import_zero_rows && report.mutant_B_import_zero_rows.sheet_sentence_after && report.mutant_B_import_zero_rows.sheet_claimed_places === false),
    C_sentence_equals_server_count: !!(report.readback_after_supply && report.readback_after_supply.agrees),
    D_unreadable_door_says_so_without_a_number: !!(report.unreadable_state && report.unreadable_state.painted && report.unreadable_state.contains_digit_count === false),
  };
  report.finished_at = new Date().toISOString();
  const stamp = report.finished_at.replace(/[-:]/g, "").slice(0, 13);
  const file = path.join(OUT, `walk_ord0504_r2_${stamp}.json`);
  fs.writeFileSync(file, JSON.stringify(report, null, 1), "utf-8");
  console.log(JSON.stringify({ evidence: file.replace(/\\/g, "/"), chosen: report.chosen_city, verdicts: report.verdicts }, null, 1));
})().catch((exc) => {
  console.error("R2_FAILED", exc && exc.message ? exc.message : exc);
  process.exit(1);
});
