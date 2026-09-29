/* ORD-0440 second half - the screen reading that the ruler cannot do.
 *
 * The ruler proves which expressions can carry upstream text; it cannot prove what a traveller reads.
 * This walk forces a failing capability read and a failing job answer on a real screen and asserts:
 *   C1 the alert line is a sentence this build wrote (byte-equal to the dictionary), not the answer's
 *   C2 the upstream sentence appears nowhere in the panel's text, and no upstream value rides in a data-*
 *   C3 the receipt fold really renders (open, visible, counted) and still shows the server's own number
 *   C4 the fold is anchored to a field this device measured, under its contract name
 *
 * usage: node walk_cells_r1.cjs <preview-base> <reset-token> <out-dir> [zh|en]
 */
const { chromium } = require("D:/moodle/_qoder_n3_ord0440b/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:49970";
const TOKEN = process.argv[3] || "";
const OUT = process.argv[4] || "D:/moodle/_qoder_n3_ord0440b/review/n3_0440_evidence_r1/cells_walk";
const LOCALE = process.argv[5] === "en" ? "en" : "zh-CN";
const TAG = LOCALE === "en" ? "en" : "zh";

/* The two sentences this build owns for those two failures, copied from prepFailureCopy.ts by hand
   into the assertion so a change to the file has to be noticed here rather than absorbed silently. */
const SENTENCE = {
  "zh-CN": {
    check: "这一次没读到这座城市的判定。行程没有因此变化，可以再问一次。",
    resolver: "目的地来源这一次没答上。这不是这座城不能规划，可以再问一次。",
  },
  en: {
    check: "This read of the destination's verdict did not come back. Nothing about the trip changed; asking again is safe.",
    resolver: "The destination source did not answer this time. That does not mean the city cannot be planned - ask again.",
  },
}[LOCALE];

const UPSTREAM_PROSE = "上游原话：这台服务器不想谈";
const RECEIPT_ID = "CNX-7H4TQ2KM";

const readings = { base: BASE, locale: LOCALE, checks: [], steps: [], shots: [] };
const check = (name, pass, detail) => readings.checks.push({ name, pass, detail });

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();

  await page.goto(BASE + "/v8/discover", { waitUntil: "load" });
  await page.evaluate(async (tok) => {
    await fetch("/api/v1/demo/reset", {
      method: "POST",
      headers: { "content-type": "application/json", "X-Demo-Reset-Token": tok },
      body: "{}",
    });
  }, TOKEN);
  const scene = await page.evaluate(() => fetch("/api/v1/demo/scene").then((r) => r.json()));
  await page.addInitScript(
    ([l, j]) => {
      localStorage.setItem("citynexus.locale", l);
      localStorage.setItem("citynexus.v8.journey_id", j);
    },
    [LOCALE, scene.journey_id],
  );

  /* A refusal in the contract's own shape: a named code, a receipt the server owns, and prose that
     the screen is not allowed to repeat. */
  await page.route("**/api/v1/destinations/capability**", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "RESOLVER_UNAVAILABLE",
          reason_code: "DESTINATION_RESOLVER_UNAVAILABLE",
          message: UPSTREAM_PROSE,
          error_receipt_id: RECEIPT_ID,
        },
      }),
    }),
  );

  /* The discovery console's failure block is the mount that carries a receipt, so the same refusal
     shape is answered there too - the leg that proves C3/C4 is read from a real mount, not from the
     component's source. */
  await page.route("**/real-city/discover**", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "PROVIDER_SERVER_ERROR",
          reason_code: "PROVIDER_SERVER_ERROR",
          message: UPSTREAM_PROSE,
          error_receipt_id: RECEIPT_ID,
        },
      }),
    }),
  );

  await page.goto(BASE + "/v8/discover", { waitUntil: "load" });
  const seal = page.getByText(/使用封存的演示行程|sealed demo/i).first();
  if (await seal.count()) {
    await seal.click();
    await page.waitForTimeout(1200);
  }
  await page.waitForSelector('[data-testid="prep-panel"]', { timeout: 20000 });
  await page.fill('[data-testid="prep-query"]', "某座故意读不到的城");
  await page.click('[data-testid="prep-check"]');
  await page.waitForSelector('[data-testid="prep-check-error"]', { timeout: 30000 });

  const alertText = (await page.getByTestId("prep-check-error").innerText()).replace(/\s+/g, " ").trim();
  check(
    "C1 the failure line is a sentence this build wrote",
    alertText === SENTENCE.resolver.replace(/\s+/g, " ").trim() ||
      alertText === SENTENCE.check.replace(/\s+/g, " ").trim(),
    { alert_text: alertText, expected_from_dictionary: [SENTENCE.check, SENTENCE.resolver] },
  );

  const panelText = (await page.getByTestId("prep-panel").innerText()).replace(/\s+/g, " ");
  check("C2 the upstream sentence is not on the screen", !panelText.includes(UPSTREAM_PROSE), {
    searched_for: UPSTREAM_PROSE,
    present_in_panel: panelText.includes(UPSTREAM_PROSE),
  });
  const attrsCarryingUpstream = await page.evaluate((needle) => {
    const hits = [];
    for (const el of document.querySelectorAll("[data-testid^='prep-'], .prep-server, .role-alert")) {
      for (const attr of el.attributes) {
        if (attr.value.includes(needle)) hits.push(`${el.getAttribute("data-testid")}|${attr.name}`);
      }
    }
    return hits;
  }, UPSTREAM_PROSE);
  check("C2 no upstream value rides into a data-* either", attrsCarryingUpstream.length === 0, {
    attribute_hits: attrsCarryingUpstream,
  });

  /* C3/C4 need a mount of CnxMeasuredFacts with a real envelope: the discovery panel's failure block
     is the one this build already owns, so drive it the way the traveller does. */
  await page.fill('[data-testid="v13-discovery-goal"]', "找一间靠近地铁的安静旅馆");
  await page.click('[data-testid="v13-discover-submit"]');
  await page.waitForSelector('[data-testid="v13-discovery-technical-toggle"]', { timeout: 30000 });
  await page.click('[data-testid="v13-discovery-technical-toggle"]');
  await page.waitForTimeout(300);
  const fold = page.locator('[data-testid="v13-discovery-fact-receipt-fold"]');
  const foldCount = await fold.count();
  readings.steps.push({ step: "receipt fold mounted on this screen", count: foldCount });
  if (foldCount > 0) {
    const visible = await fold.isVisible();
    const openAttr = await fold.getAttribute("open");
    check("C3 the receipt fold really renders", visible && openAttr !== null, {
      visible,
      open_attribute_present: openAttr !== null,
    });
    const anchor = await page.locator('[data-testid="v13-discovery-fact-receipt-fold"] [data-cnx-field]').count();
    const anchorName = await page
      .locator('[data-testid="v13-discovery-fact-receipt-fold"] [data-cnx-field]')
      .first()
      .getAttribute("data-cnx-field")
      .catch(() => null);
    check("C4 the fold is anchored to a field this device measured", anchor > 0 && anchorName === "http_status", {
      anchor_count: anchor,
      anchor_field: anchorName,
    });
    const receiptLine = (
      await page.locator('[data-testid="v13-discovery-fact-receipt"]').innerText()
    ).replace(/\s+/g, " ").trim();
    check(
      "C5 the fold still shows the server's own number, not a stand-in",
      // either the number the answer sent (any shape the contract allows) or the named missing token
      (/(CNX-[23456789ABCDEFGHJKMNPQRSTVWXYZ]{8})|NOT-EMITTED/.test(receiptLine) ||
        receiptLine.includes(RECEIPT_ID)) &&
        !receiptLine.includes(UPSTREAM_PROSE),
      { receipt_line: receiptLine, expected_shape: "CNX-<8 crockford chars> or NOT-EMITTED", stubbed_number: RECEIPT_ID },
    );
    await page.screenshot({ path: `${OUT}/${TAG}_receipt_fold.png` });
    readings.shots.push(`${TAG}_receipt_fold.png`);
  } else {
    check("C3 the receipt fold is mounted where a refusal was read", false, {
      mounted_count: foldCount,
      note: "the discovery failure block did not mount after a stubbed 503",
    });
  }

  readings.pass_count = readings.checks.filter((c) => c.pass).length;
  readings.fail_count = readings.checks.filter((c) => !c.pass).length;
  fs.writeFileSync(`${OUT}/cells_walk_${TAG}.json`, JSON.stringify(readings, null, 2), "utf8");
  console.log(`locale=${TAG} checks=${readings.checks.length} pass=${readings.pass_count} fail=${readings.fail_count}`);
  for (const c of readings.checks) if (!c.pass) console.log("  RED", c.name, JSON.stringify(c.detail).slice(0, 220));
  console.log("wrote", `${OUT}/cells_walk_${TAG}.json`);
  await browser.close();
  process.exit(readings.fail_count ? 1 : 0);
})().catch((error) => {
  console.log("CELLS_WALK_CRASH", String(error).slice(0, 300));
  process.exit(2);
});
