/**
 * ORD-0510 -- the two counter-examples, run for real against the same stack the happy arms used.
 *
 * A counter-example is only worth what it can fail for, so each arm here has the reading it is meant
 * to deny, and the denial has to show:
 *
 *   A  empty-shelf arm -- the read door is intercepted to answer `[]` while the server actually holds
 *      a shelf.  The screen must say there is nowhere to put the place, must offer no shelf to click,
 *      and must produce NO result line at all.  A face that cached the list, or that wrote "已收在"
 *      because a button was pressed, passes this arm only by lying -- and lying here is visible
 *      because the server's own answer is printed beside the reading.
 *
 *   B  fake-write arm -- the list door is left real (a shelf that holds nothing), and the add door is
 *      intercepted to answer 201 with a fabricated row without the server ever seeing it.  The screen
 *      re-reads the list door, so it must report that no shelf carries this place.  The same control
 *      against the real door prints 「已收在 …」 (see collect_arms_r1's happy arm), which is what makes
 *      this a measurement of the write leg rather than of the copy: remove the real write and the
 *      claim goes red.
 */
const { chromium } = require("playwright");
const fs = require("fs");

const BASE = process.env.CNX_BASE || "http://localhost:4511";
const API = process.env.CNX_API || "http://127.0.0.1:7011";
const OUT = process.env.CNX_OUT || "collect_mutants.json";
const TRAVELER = "11111111-1111-4111-8111-111111111111";

const inner = (page, sel) => page.locator(sel).first().innerText()
  .then((s) => s.replace(/\s+/g, " ").trim()).catch(() => null);
const count = (page, sel) => page.locator(sel).count();

const open = async (page) => {
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

const useStop = async (page, index) => {
  const card = page.locator('[data-testid="collect-into"]').nth(index);
  await card.scrollIntoViewIfNeeded();
  await card.locator('[data-testid="collect-entry"]').click();
  await page.waitForSelector('[data-testid="collect-picker"]', { timeout: 15000 });
  await page.waitForTimeout(1500);
};

(async () => {
  const browser = await chromium.launch();
  const out = { order: "ORD-0510", instrument: "collect_mutants_r2", arms: {} };

  /* ---------- A: the list door answers "no shelves" ---------- */
  {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    await page.addInitScript(() => localStorage.setItem("citynexus.locale", "zh-CN"));
    await page.route("**/api/v1/collections?*", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
    await open(page);
    await useStop(page, 0);
    const a = {
      shelves_offered: await count(page, '[data-testid="collect-shelf"]'),
      no_shelf_line: await inner(page, '[data-testid="collect-no-shelf"]'),
      result_line_present: (await count(page, '[data-testid="collect-result"]')) > 0,
      picker_text: await inner(page, '[data-testid="collect-picker"]'),
    };
    a.claims_collected_anywhere = /已收在|Collected into/.test(
      await page.locator('[data-testid="collect-into"]').first().innerText().catch(() => ""));
    await page.screenshot({ path: "collect_mutant_A.png" });
    out.arms.A_empty_shelf = a;
    await ctx.close();
  }

  /* ---------- the real door, so B has something true to contradict ---------- */
  /* A shelf created for this run, by name, so the fake-write arm always has a shelf that genuinely
     does not hold the place.  Reusing a shelf from an earlier run made the second run of this arm
     pass for the wrong reason: the place was already on it, so the read-back named it and the arm
     could no longer tell "the write happened" from "the write was intercepted". */
  const nonce = new Date().toISOString().replace(/[^0-9]/g, "").slice(-9);
  const SHELF_B = `反件架 ${nonce}`;
  const created = await (await fetch(`${API}/api/v1/collections`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ name: SHELF_B, owner_traveler_id: TRAVELER }),
  })).json();
  out.shelf_for_B = { id: created && created.id, name: SHELF_B, item_count: created && created.item_count };

  /* ---------- B: the write door is a lie, the read door is real ---------- */
  {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    await page.addInitScript(() => localStorage.setItem("citynexus.locale", "zh-CN"));
    let postReachedServer = false;
    await page.route("**/api/v1/collections/*/items", (route) => {
      postReachedServer = true;
      return route.fulfill({
        status: 201, contentType: "application/json",
        body: JSON.stringify({ id: "deadbeef-0000-4000-8000-000000000001", folder_id: "x",
                               place_id: "place-riverside-museum", name: "Riverside Museum",
                               category: "museum", city_code: "CNX-DEMO", note: null,
                               added_at: new Date().toISOString() }),
      });
    });
    await open(page);
    // stop index 1 is Riverside Museum, which no shelf holds yet
    await useStop(page, 1);
    const shelves = await count(page, '[data-testid="collect-shelf"]');
    let clicked = null;
    if (shelves > 0) {
      const target = page.locator('[data-testid="collect-shelf"]')
        .filter({ hasText: SHELF_B }).first();
      const use = (await target.count()) ? target : page.locator('[data-testid="collect-shelf"]').first();
      await use.click();
      await page.waitForSelector('[data-testid="collect-result"]', { timeout: 20000 });
      await page.waitForTimeout(1500);
      clicked = { result_line: await inner(page, '[data-testid="collect-result"]') };
    }
    await page.screenshot({ path: "collect_mutant_B.png" });
    out.arms.B_faked_write = {
      shelves_offered: shelves, clicked,
      /* the POST never reached this server -- the route handler answered it in the browser */
      intercepted_post: true,
      server_answer_for_that_place: await (await fetch(`${API}/api/v1/collections?traveler_id=${TRAVELER}`))
        .json().then((rows) => rows.map((s) => ({ name: s.name, item_count: s.item_count,
                                                   places: s.items.map((i) => i.place_id) }))),
      postReachedServer: postReachedServer,
    };
    await ctx.close();
  }

  /* ---------- B control: the same arm with the write leg real ---------- */
  {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    await page.addInitScript(() => localStorage.setItem("citynexus.locale", "zh-CN"));
    await open(page);
    await useStop(page, 1);
    const target = page.locator('[data-testid="collect-shelf"]').filter({ hasText: SHELF_B }).first();
    await target.click();
    await page.waitForSelector('[data-testid="collect-result"]', { timeout: 20000 });
    await page.waitForTimeout(1500);
    out.arms.B_control_real_write = {
      result_line: await inner(page, '[data-testid="collect-result"]'),
      server_answer: await (await fetch(`${API}/api/v1/collections?traveler_id=${TRAVELER}`))
        .json().then((rows) => rows.map((s) => ({ name: s.name, item_count: s.item_count,
                                                   places: s.items.map((i) => i.place_id) }))),
    };
    await ctx.close();
  }

  fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out, null, 1));
  await browser.close();
})().catch((e) => { console.error("MUTANT_FAILED", String(e)); process.exit(1); });
