/**
 * ORD-0428 槽二 screen reader, r2.  One arm = one evidence file.
 *
 * r1 -> r2 changed two things, both found by running r1 against the untouched tip:
 *   - the place-slug pattern in r1 was `place-[a-z0-9]+(?:-[a-z0-9]+)*`, which read the card's whole
 *     text and swallowed the leading digits of the next line ("place-river-cruise10" from
 *     "…cruise" + "10月10日 15:30").  The `h2` readings were never affected because that field is
 *     read alone, but a derived count that over-captures is not a count.  Letters-only now.
 *   - r1 asserted only what is painted.  That is the order's criterion, but it cannot tell "the
 *     identifier left the document" from "the identifier moved into a `data-*` attribute", and the
 *     second one is the re-filing face ORD-0448 measured.  So every attribute of the card and of the
 *     headline is dumped, and the id search runs over the serialised outer HTML too.
 *
 * Driven from node rather than by dumping served HTML: this is a state-driven SPA and the tab body
 * does not exist in the document until 预订 is clicked.
 *
 * Instrument history, said out loud: the first r2 run failed on every arm with
 * `Cannot read properties of undefined (reading 'attributes')` because `ATTR_DUMP` was handed to
 * `page.evaluate` as a *string*, which Playwright evaluates as an expression rather than calling.
 * No reading was ever taken from that shape, so it is fixed in this file rather than versioned
 * around; the bytes published are the bytes that produced the four receipts beside it.
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.env.CNX_BASE || "http://localhost:4471";
const LOCALE = process.env.CNX_LOCALE || "zh-CN";
const OUT = process.env.CNX_OUT || `card_${LOCALE === "en" ? "en" : "zh"}.json`;
const SHOT = process.env.CNX_SHOT || OUT.replace(/\.json$/, ".png");
const LABEL = process.env.CNX_LABEL || "arm";

const PLACE_ID = /place-[a-z]+(?:-[a-z]+)+/;
const SCREAMING = /[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+/;

function hits(pattern, text) {
  const out = [];
  const re = new RegExp(pattern.source, "gi");
  let m;
  while ((m = re.exec(text)) !== null) out.push(m[0]);
  return out;
}

const ATTR_DUMP = (el) => ({
  tag: el.tagName,
  attributes: Array.from(el.attributes).map((a) => a.name + "=" + a.value),
  outer_html: el.outerHTML,
});

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    locale: LOCALE === "en" ? "en-US" : "zh-CN",
  });
  const page = await ctx.newPage();
  const consoleErrors = [];
  page.on("console", (m) => {
    if (m.type() === "error") consoleErrors.push(m.text().slice(0, 200));
  });

  await page.addInitScript((value) => {
    try {
      window.localStorage.setItem("citynexus.locale", value);
    } catch (e) {
      /* storage can be blocked; the arm then reads the document default, which the receipt says. */
    }
  }, LOCALE);

  await page.goto(`${BASE}/v8/trips`, { waitUntil: "domcontentloaded", timeout: 60000 });

  const entry = page.getByRole("button", { name: /封存的演示|sealed demo/i }).first();
  let entryUsed = null;
  if (await entry.isVisible({ timeout: 8000 }).catch(() => false)) {
    entryUsed = (await entry.textContent()) || null;
    await entry.click();
    await page.waitForTimeout(2500);
    await page.goto(`${BASE}/v8/trips`, { waitUntil: "domcontentloaded", timeout: 60000 });
  }

  await page.waitForSelector('[data-testid="trips-tabs"]', { timeout: 45000 });
  const tabs = await page.evaluate(() =>
    Array.from(document.querySelectorAll('[data-testid^="trips-tab-"]')).map((b) => ({
      testid: b.getAttribute("data-testid"),
      text: (b.textContent || "").trim(),
    })),
  );
  const localeOnScreen = await page.evaluate(() =>
    (document.querySelector('[data-testid="trips-tabs"]')?.getAttribute("aria-label")) || "",
  );
  await page.click('[data-testid="trips-tab-bookings"]');

  const cards = page.locator('[data-testid="wallet-commitment"]');
  await cards.first().waitFor({ state: "attached", timeout: 45000 });
  await page.waitForTimeout(1500);

  const n = await cards.count();
  const read = [];
  for (let i = 0; i < n; i += 1) {
    const card = cards.nth(i);
    const h2 = card.locator("h2");
    const badge = card.locator(".v8-selected-label");
    const h2Text = (await h2.textContent()) || "";
    const badgeText = (await badge.textContent()) || "";
    const cardText = (await card.textContent()) || "";
    const h2Dom = await h2.evaluate(ATTR_DUMP);
    const cardDom = await card.evaluate(ATTR_DUMP);
    read.push({
      index: i,
      h2_text_content: h2Text,
      badge_text_content: badgeText,
      whole_card_text_content: cardText,
      h2_children_count: await h2.evaluate((el) => el.children.length),
      place_id_hits_h2: hits(PLACE_ID, h2Text),
      screaming_hits_h2: hits(SCREAMING, h2Text),
      place_id_hits_badge: hits(PLACE_ID, badgeText),
      screaming_hits_badge: hits(SCREAMING, badgeText),
      whole_card_place_id_hits: hits(PLACE_ID, cardText),
      whole_card_screaming_hits: hits(SCREAMING, cardText),
      h2_attributes: h2Dom.attributes,
      card_attributes: cardDom.attributes,
      place_id_hits_card_outer_html: hits(PLACE_ID, cardDom.outer_html),
      place_id_hits_h2_outer_html: hits(PLACE_ID, h2Dom.outer_html),
      bounding_box: await card.boundingBox().then((b) => (b ? { x: Math.round(b.x), y: Math.round(b.y), width: Math.round(b.width), height: Math.round(b.height) } : null)),
    });
    await card.scrollIntoViewIfNeeded();
  }
  await cards.first().screenshot({ path: SHOT }).catch(async () => {
    await page.screenshot({ path: SHOT, fullPage: false });
  });

  const receipt = {
    order: "ORD-0428",
    instrument: "card_reader_r2",
    arm: LABEL,
    locale_written_to_storage: LOCALE,
    tabs_aria_label_read: localeOnScreen,
    base_url: BASE,
    route_used: "/v8/trips",
    tab_clicked: "trips-tab-bookings",
    entry_button_used: entryUsed,
    tabs_found: tabs,
    wallet_commitment_cards: n,
    cards: read,
    console_errors: consoleErrors,
    verdict: {
      any_place_id_in_any_h2: read.some((r) => r.place_id_hits_h2.length > 0),
      any_screaming_in_any_h2: read.some((r) => r.screaming_hits_h2.length > 0),
      any_place_id_in_any_badge: read.some((r) => r.place_id_hits_badge.length > 0),
      any_screaming_in_any_badge: read.some((r) => r.screaming_hits_badge.length > 0),
      any_place_id_in_any_card_attribute: read.some(
        (r) =>
          r.place_id_hits_card_outer_html.length > 0 ||
          r.place_id_hits_h2_outer_html.length > 0,
      ),
    },
    h2_texts: read.map((r) => r.h2_text_content),
    screenshot: path.basename(SHOT),
  };
  fs.writeFileSync(OUT, JSON.stringify(receipt, null, 1));
  console.log(JSON.stringify(receipt, null, 1));
  await browser.close();
})().catch((e) => {
  console.error("DRIVER_FAILED", String(e));
  process.exit(1);
});
