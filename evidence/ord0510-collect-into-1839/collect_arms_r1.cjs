/**
 * ORD-0510 -- the 收藏到… entry, read off the screen the way a traveller reaches it.
 *
 * Arms, in this order, because the first one needs a state the later ones destroy:
 *   empty_390_zh   -- the traveller holds no shelf.  The picker must say there is nowhere to put it
 *                    and must not print 已收在.  This is the counter-example against a screen that
 *                    treats "I clicked" as "it is stored".
 *   happy_390_zh   -- a shelf exists (created through the server's own POST door, not by writing rows),
 *                    picking it must name the shelf on the result line, and the same line must agree
 *                    with a fresh `GET /api/v1/collections` taken outside the browser.
 *   again_390_zh   -- picking the same shelf twice: the door answers 409, the screen must read as
 *                    already-there and still name the shelf from the read-back.
 *   happy_desktop_en -- the same write on a desktop viewport in English, so the claim is not a
 *                    390 px / Chinese-only reading.
 *
 * Every reading is `innerText`, and every control is hit-tested at its own centre with
 * `elementFromPoint` after being scrolled into view -- laid out is not hittable (ORD-0338).
 */
const { chromium } = require("playwright");
const fs = require("fs");

const BASE = process.env.CNX_BASE || "http://localhost:4511";
const API = process.env.CNX_API || "http://127.0.0.1:7011";
const OUT = process.env.CNX_OUT || "collect_arms.json";
const TRAVELER = "11111111-1111-4111-8111-111111111111";
const SHELF_NAME = "周末架子";

const hitTest = (page, selector) => page.evaluate((sel) => {
  const el = document.querySelector(sel);
  if (!el) return { found: false };
  el.scrollIntoView({ block: "center" });
  const r = el.getBoundingClientRect();
  const x = r.x + r.width / 2;
  const y = r.y + r.height / 2;
  const top = document.elementFromPoint(x, y);
  return { found: true, box: { w: Math.round(r.width), h: Math.round(r.height), x: Math.round(x), y: Math.round(y) },
           top_is_the_control: !!top && (top === el || el.contains(top)), top_tag: top ? top.tagName : null };
}, selector);

const inner = (page, sel) => page.locator(sel).first().innerText().then((s) => s.replace(/\s+/g, " ").trim()).catch(() => null);

const openScreen = async (page, locale) => {
  await page.goto(`${BASE}/v8/trips`, { waitUntil: "domcontentloaded", timeout: 60000 });
  const entry = page.getByRole("button", { name: /封存的演示|sealed demo/i }).first();
  if (await entry.isVisible({ timeout: 8000 }).catch(() => false)) {
    await entry.click();
    await page.waitForTimeout(2500);
    await page.goto(`${BASE}/v8/trips`, { waitUntil: "domcontentloaded", timeout: 60000 });
  }
  await page.waitForSelector('[data-testid="trip-itinerary"]', { timeout: 45000 });
  await page.waitForTimeout(2000);
};

const arm = async (browser, name, { width, height, locale, expectShelf }) => {
  const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 2,
                                        locale: locale === "en" ? "en-US" : "zh-CN" });
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 160)); });
  await page.addInitScript((v) => { try { localStorage.setItem("citynexus.locale", v); } catch (e) {} }, locale);
  await openScreen(page, locale);

  const stops = await page.locator('[data-testid="trip-stop"]').count();
  const entrySel = '[data-testid="collect-into"] [data-testid="collect-entry"]';
  const firstEntry = page.locator(entrySel).first();
  await firstEntry.scrollIntoViewIfNeeded();
  const hit = await hitTest(page, entrySel);
  const entryText = await inner(page, entrySel);
  await firstEntry.click();
  await page.waitForSelector('[data-testid="collect-picker"]', { timeout: 15000 });
  await page.waitForTimeout(1800);
  const pickerText = await inner(page, '[data-testid="collect-picker"]');
  const shelves = await page.locator('[data-testid="collect-shelf"]').count();
  const noShelf = await inner(page, '[data-testid="collect-no-shelf"]');

  let picked = null;
  if (shelves > 0) {
    const shelfSel = '[data-testid="collect-shelf"]';
    const hitShelf = await hitTest(page, shelfSel);
    await page.locator(shelfSel).first().click();
    await page.waitForSelector('[data-testid="collect-result"]', { timeout: 20000 });
    await page.waitForTimeout(1500);
    picked = { hit: hitShelf, result: await inner(page, '[data-testid="collect-result"]') };
  }
  await page.screenshot({ path: `collect_${name}.png` });
  const out = { arm: name, viewport: { width, height }, locale, stops_on_screen: stops,
                entry_text: entryText, entry_hit: hit, picker_text: pickerText,
                shelves_listed: shelves, no_shelf_line: noShelf, after_pick: picked,
                console_errors: errors };
  await ctx.close();
  return out;
};

(async () => {
  const browser = await chromium.launch();
  const results = [];
  results.push(await arm(browser, "empty_390_zh", { width: 390, height: 844, locale: "zh-CN" }));

  // the shelf is created through the server's own door, so the screen never holds a container the
  // store does not
  const created = await (await fetch(`${API}/api/v1/collections`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ name: SHELF_NAME, owner_traveler_id: TRAVELER }),
  })).json();
  const shelfStatus = created && created.id ? "created" : JSON.stringify(created).slice(0, 160);

  results.push(await arm(browser, "happy_390_zh", { width: 390, height: 844, locale: "zh-CN" }));
  results.push(await arm(browser, "again_390_zh", { width: 390, height: 844, locale: "zh-CN" }));
  results.push(await arm(browser, "happy_desktop_en", { width: 1280, height: 900, locale: "en" }));

  // the server's own answer, read outside the browser, to compare against what the screens said
  const readBack = await (await fetch(`${API}/api/v1/collections?traveler_id=${TRAVELER}`)).json();
  const receipt = { order: "ORD-0510", instrument: "collect_arms_r1", base_url: BASE,
                    shelf_created: { status: shelfStatus, id: created && created.id, name: SHELF_NAME },
                    arms: results,
                    server_readback_after_all_arms: readBack.map((s) => ({ id: s.id, name: s.name,
                      item_count: s.item_count, items: s.items.map((i) => ({ place_id: i.place_id, name: i.name })) })) };
  fs.writeFileSync(OUT, JSON.stringify(receipt, null, 1));
  console.log(JSON.stringify({ shelf_created: shelfStatus,
    arms: results.map((r) => ({ arm: r.arm, stops: r.stops_on_screen, entry: r.entry_text,
      hit_ok: r.entry_hit.top_is_the_control, box: r.entry_hit.box, shelves: r.shelves_listed,
      no_shelf: r.no_shelf_line, result: r.after_pick && r.after_pick.result,
      errs: r.console_errors.length })),
    server_readback: receipt.server_readback_after_all_arms }, null, 1));
  await browser.close();
})().catch((e) => { console.error("DRIVER_FAILED", String(e)); process.exit(1); });
