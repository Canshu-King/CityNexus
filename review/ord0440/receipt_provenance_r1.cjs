/* ORD-0440 second half - where did the receipt number on the screen come from?
 *
 * The delivered walk asserts the fold shows a number shaped like the contract's (`CNX-` + 8 crockford
 * characters). Shape alone is not provenance: a client that minted its own number would satisfy it too.
 * Grepping the tree shows `frontend/src` only ever *matches* that shape (`lib/errorReceipt.ts:22`) and the
 * backend is the only writer (`backend/app/error_receipt.py:29`), but that is an inference. This records
 * every CNX- token that actually arrived in an HTTP answer body on the way to that screen and asks whether
 * the token the traveller can read is one of them.
 *
 * usage: node receipt_provenance_r1.cjs <preview-base> <reset-token> <out-dir> [zh|en]
 */
const { chromium } = require("D:/moodle/_qoder_n3_ord0440b/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:49972";
const TOKEN = process.argv[3] || "";
const OUT = process.argv[4] || "D:/moodle/_qoder_n3_ord0440b/review/n3_0440_evidence_r3/receipt_provenance";
const LOCALE = process.argv[5] === "en" ? "en" : "zh-CN";
const TAG = LOCALE === "en" ? "en" : "zh";

const SHAPE = /CNX-[23456789ABCDEFGHJKMNPQRSTVWXYZ]{8}/g;
const STUB_RECEIPT = "CNX-7H4TQ2KM";

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();

  /* Every token that arrived in a response body, tagged with the route and status that carried it. */
  const serverSent = [];
  page.on("response", async (res) => {
    let body = "";
    try {
      body = await res.text();
    } catch (e) {
      body = "";
    }
    for (const m of body.match(SHAPE) || []) {
      serverSent.push({ token: m, url: res.url().replace(BASE, ""), status: res.status() });
    }
  });

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

  const refusal = (code) => ({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({
      error: {
        code,
        reason_code: code,
        message: "上游原话：这台服务器不想谈",
        error_receipt_id: STUB_RECEIPT,
      },
    }),
  });
  await page.route("**/api/v1/destinations/capability**", (route) => route.fulfill(refusal("RESOLVER_UNAVAILABLE")));
  await page.route("**/real-city/discover**", (route) => route.fulfill(refusal("PROVIDER_SERVER_ERROR")));

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

  await page.fill('[data-testid="v13-discovery-goal"]', "找一间靠近地铁的安静旅馆");
  await page.click('[data-testid="v13-discover-submit"]');
  await page.waitForSelector('[data-testid="v13-discovery-technical-toggle"]', { timeout: 30000 });
  await page.click('[data-testid="v13-discovery-technical-toggle"]');
  await page.waitForTimeout(500);

  const receiptLine = await page
    .locator('[data-testid="v13-discovery-fact-receipt"]')
    .innerText()
    .then((s) => s.replace(/\s+/g, " ").trim())
    .catch(() => "");
  const onScreen = receiptLine.match(SHAPE) || [];
  const tokensSent = serverSent.map((s) => s.token);
  const matched = onScreen.filter((t) => tokensSent.includes(t));

  const checks = [
    {
      name: "P1 the number on the screen is one an answer actually sent",
      pass: onScreen.length > 0 && onScreen.every((t) => tokensSent.includes(t)),
      detail: { on_screen: onScreen, server_sent: tokensSent, carriers: serverSent },
    },
  ];
  /* Which leg mounted the fold is reported, not asserted: the stub's own number only proves something
     if that stub is the answer this fold is reading, and the fold can be fed by either failing leg. */
  const observations = {
    stubbed_number: STUB_RECEIPT,
    stub_arrived_in_a_body: tokensSent.includes(STUB_RECEIPT),
    shown: onScreen,
  };
  const payload = {
    base: BASE,
    locale: LOCALE,
    receipt_line: receiptLine,
    server_sent_tokens: serverSent,
    on_screen_tokens: onScreen,
    matched: matched,
    checks: checks,
    observations: observations,
    pass_count: checks.filter((c) => c.pass).length,
    fail_count: checks.filter((c) => !c.pass).length,
  };
  fs.writeFileSync(`${OUT}/receipt_provenance_${TAG}.json`, JSON.stringify(payload, null, 2), "utf8");
  await page.screenshot({ path: `${OUT}/${TAG}_receipt_fold.png` });
  for (const c of checks) {
    console.log(`${c.pass ? "GREEN" : "RED  "} ${c.name} ${JSON.stringify(c.detail).slice(0, 200)}`);
  }
  console.log(`receipt_line="${receiptLine}" on_screen=${onScreen.join(",")} server_sent=${new Set(tokensSent).size} unique`);
  console.log(`checks=${checks.length} pass=${payload.pass_count} fail=${payload.fail_count}`);
  console.log(`wrote ${OUT}/receipt_provenance_${TAG}.json`);
  await browser.close();
  process.exit(payload.fail_count === 0 ? 0 : 1);
})();
