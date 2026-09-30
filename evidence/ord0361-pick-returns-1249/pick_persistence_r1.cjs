/**
 * ORD-0361 residual, three arms, one per claim.
 *
 * The claim being tested is not "a tap does something" (ORD-0390 and ORD-0417 already own that, and the
 * tap probe beside this file measures it).  It is narrower: a stop picked on the map is remembered for
 * THAT journey, and the remembering cannot lie.  Three arms, each with its own receipt:
 *
 *   normal  - pick a stop, reload, the same stop is named on the glass AND painted on its pin.
 *   foreign - the stored pick belongs to a different journey id: nothing is restored.  This is the arm
 *             that distinguishes "journey-scoped" from "global key with a journey in its name".
 *   stale   - the stored id is not a stop on this plan: nothing is named, and the entry is dropped.
 *             Restoring an id the plan does not have would print a name the server does not stand behind.
 *
 * Every reading is rendered text or a DOM attribute; the storage dump is printed so the reader can see
 * the key and its value rather than take a boolean from me.
 */
const { chromium } = require("playwright");
const fs = require("fs");

const BASE = process.env.CNX_BASE || "http://localhost:4491";
const OUT = process.env.CNX_OUT || "pick_arm.json";
const ARM = process.env.CNX_ARM || "normal";
const JOURNEY = "22222222-2222-4222-8222-222222222222";
const OLD_TOWN_GATE = "3a58c470-524c-5854-aa39-6c37a350eb80";
const keyFor = (id) => `citynexus.v8.map_pick.${id}`;

const SEED = {
  normal: () => [[keyFor(JOURNEY), OLD_TOWN_GATE]],
  foreign: () => [[keyFor("11111111-1111-4111-8111-111111111111"), OLD_TOWN_GATE]],
  stale: () => [[keyFor(JOURNEY), "00000000-0000-4000-8000-000000000000"]],
}[ARM];

const read = (page) => page.evaluate(() => ({
  markers: Array.from(document.querySelectorAll(".v9-map-marker")).map((e) => ({
    label: (e.textContent || "").trim(),
    aria_label: e.getAttribute("aria-label"),
    pressed: e.getAttribute("aria-pressed"),
    selected_class: e.classList.contains("selected"),
  })),
  storage: (() => {
    const o = {};
    for (let i = 0; i < localStorage.length; i += 1) {
      const k = localStorage.key(i);
      if (k && k.indexOf("citynexus") === 0) o[k] = String(localStorage.getItem(k)).slice(0, 60);
    }
    return o;
  })(),
}));

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 160)); });
  await page.addInitScript((pairs) => {
    localStorage.setItem("citynexus.locale", "zh-CN");
    localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
    (pairs || []).forEach(([k, v]) => localStorage.setItem(k, v));
  }, SEED());

  const openMap = async () => {
    await page.goto(`${BASE}/v8/map`, { waitUntil: "domcontentloaded", timeout: 60000 });
    const entry = page.getByRole("button", { name: /封存的演示|sealed demo/i }).first();
    if (await entry.isVisible({ timeout: 6000 }).catch(() => false)) {
      await entry.click();
      await page.waitForTimeout(2000);
      await page.goto(`${BASE}/v8/map`, { waitUntil: "domcontentloaded", timeout: 60000 });
    }
    await page.waitForSelector(".v9-map-marker", { timeout: 40000 });
    await page.waitForTimeout(3000);
  };
  await openMap();
  const first = await read(page);
  const glass1 = await page.locator('[data-testid="v8-map-selected-stop"]').first()
    .textContent().then((t) => (t || "").replace(/\s+/g, " ").trim()).catch(() => null);
  const heading1 = await page.locator(".v8-map-facts h1, .v8-map-facts h2").first()
    .textContent().then((t) => (t || "").replace(/\s+/g, " ").trim()).catch(() => null);

  // a real pick, then a reload, for the arm that must remember
  let afterUserPick = null;
  const h = await page.evaluateHandle(() => {
    const els = Array.from(document.querySelectorAll(".v9-map-marker"));
    return els.find((e) => (e.textContent || "").trim() === "3") || null;
  });
  if (h.asElement()) {
    await h.asElement().click();
    await page.waitForTimeout(1200);
    afterUserPick = await read(page);
  }
  await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector(".v9-map-marker", { timeout: 40000 });
  await page.waitForTimeout(3000);
  const afterReload = await read(page);
  const glass2 = await page.locator('[data-testid="v8-map-selected-stop"]').first()
    .textContent().then((t) => (t || "").replace(/\s+/g, " ").trim()).catch(() => null);

  const pressedOn = (m, id_label) => m.markers.filter((x) => x.label === id_label && x.pressed === "true").length;
  const receipt = {
    order: "ORD-0361", instrument: "pick_persistence_r1", arm: ARM, base_url: BASE,
    seeded_storage: SEED(),
    on_arrival: { glass: glass1, heading: heading1, markers: first.markers, storage: first.storage },
    after_user_pick_of_marker_3: afterUserPick && {
      markers: afterUserPick.markers, glass: null,
    },
    after_reload: { glass: glass2, markers: afterReload.markers, storage: afterReload.storage },
    verdict: {
      glass_named_on_arrival: !!glass1,
      glass_named_after_reload: !!glass2,
      pin_painted_after_reload: afterReload.markers.some((m) => m.pressed === "true" && m.selected_class),
      restored_entry_present_after_reload: Object.keys(afterReload.storage).some((k) => k.indexOf("map_pick") >= 0),
      stale_entry_dropped: !Object.keys(afterReload.storage).some((k) => k.indexOf("map_pick") >= 0),
    },
    console_errors: errors,
  };
  fs.writeFileSync(OUT, JSON.stringify(receipt, null, 1));
  console.log(JSON.stringify({ arm: ARM, glass_on_arrival: glass1, glass_after_reload: glass2,
    pin_painted_after_reload: receipt.verdict.pin_painted_after_reload,
    map_pick_keys_after_reload: Object.keys(afterReload.storage).filter((k) => k.indexOf("map_pick") >= 0),
    errors: errors.length }, null, 1));
  await browser.close();
})().catch((e) => { console.error("ARM_FAILED", String(e)); process.exit(1); });
