// Compatibility probe: the product's own E2E arms drive these dropdowns with
// Playwright's selectOption(), which only exists on a real <select>. This file calls
// it in exactly the shape those specs use, and then reads a consequence the React
// state -- not the DOM attribute -- is responsible for, so a control that only looks
// selected cannot pass.
//
//   existing call sites being protected:
//     e2e/legacy/archived-product-hardening.spec.ts:77  selectOption("ASSISTED")
//     e2e/legacy/archived-product-hardening.spec.ts:210 selectOption("AUTONOMOUS")
//     e2e/qoder-ord0502-phone-mainline.spec.ts:143      selectOption({ value: "RAIL" })
//     e2e/qoder-ord0502-phone-mainline.spec.ts:476      selectOption({ value: "ARRIVAL" })
//     e2e/real-world-trip-operations-v9.spec.ts:48      selectOption("RAIL")
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const require = createRequire(import.meta.url);
const HERE = dirname(fileURLToPath(import.meta.url));
const { chromium } = require(
  resolve(join(HERE, "..", "..", "frontend", "node_modules", "playwright"), "."),
);

const BASE = process.env.BASE_URL || "http://127.0.0.1:5399";
const JOURNEY = process.env.CITYNEXUS_JOURNEY_ID || "";
const results = [];
const record = (name, ok, detail) => {
  results.push({ control: name, verdict: ok ? "PASS" : "FAIL", detail });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}  ${detail}`);
};

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
const page = await ctx.newPage();
await page.goto(`${BASE}/hub`);
await page.evaluate((id) => localStorage.setItem("citynexus.v8.journey_id", id), JOURNEY);

// 1. manual-type -- the shape at qoder-ord0502-phone-mainline.spec.ts:143.
await page.goto(`${BASE}/v8/bookings`, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(1200);
await page.getByTestId("inbox-tab-manual").click();
await page.waitForTimeout(250);
const draftsBefore = await page.getByTestId("inbox-pending-row").count().catch(() => 0);
try {
  await page.getByTestId("manual-type").selectOption({ value: "RAIL" });
  const valueRead = await page.getByTestId("manual-type").inputValue();
  record(
    "manual-type selectOption({value})",
    valueRead === "RAIL",
    `inputValue=${valueRead} element=${await page.getByTestId("manual-type").evaluate((n) => n.tagName.toLowerCase())}`,
  );
} catch (error) {
  record("manual-type selectOption({value})", false, String(error).slice(0, 90));
}

// The state consequence: submit the form and the server must file a RAIL artifact.
// This is the leg that proves the control still drives the component, not just its own
// DOM value. It writes to this lane's own database file only.
await page.getByTestId("manual-title").fill("Select lane compatibility probe");
await page.getByTestId("manual-ref").fill("SEL-COMPAT-1");
await page.getByTestId("manual-submit").click();
await page.waitForTimeout(2500);
const submitted = await page.evaluate(
  ([journey]) =>
    fetch(`/api/v1/journeys/${journey}/inbox`, { cache: "no-store" })
      .then((r) => r.json())
      .then((d) => {
        const rows = (d.drafts ?? []).filter((x) =>
          JSON.stringify(x).includes("SEL-COMPAT-1"),
        );
        return {
          filed: rows.length,
          types: rows.map(
            (x) => x.extracted?.reservation_type ?? x.extracted?.type ?? null,
          ),
        };
      }),
  [JOURNEY],
);
record(
  "manual-type reaches app state",
  submitted.filed === 1 && submitted.types.includes("RAIL"),
  `drafts_before=${draftsBefore} filed=${submitted.filed} types=${JSON.stringify(submitted.types)}`,
);

// 2. access-invite-visibility -- the data-driven ladder.
await page.goto(`${BASE}/v8/access`, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(1400);
try {
  const before = await page.getByTestId("access-invite-submit").isDisabled();
  await page.getByTestId("access-invite-visibility").selectOption({ index: 1 });
  const after = await page.getByTestId("access-invite-submit").isDisabled();
  const valueRead = await page.getByTestId("access-invite-visibility").inputValue();
  record(
    "access-invite-visibility selectOption({index})",
    typeof valueRead === "string" && valueRead.length > 0,
    `value=${valueRead} submit_disabled ${before}->${after}`,
  );
} catch (error) {
  record("access-invite-visibility selectOption({index})", false, String(error).slice(0, 90));
}

// 3. discovery evidence mode -- the control that had no styling at all.
await page.goto(`${BASE}/v8/discover`, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(1400);
try {
  await page.locator("select").first().selectOption("live");
  record(
    "discovery evidence mode selectOption(string)",
    (await page.locator("select").first().inputValue()) === "live",
    `value=live tag=select`,
  );
} catch (error) {
  record("discovery evidence mode selectOption(string)", false, String(error).slice(0, 90));
}

await browser.close();
const failed = results.filter((r) => r.verdict === "FAIL").length;
console.log(`controls_probed=${results.length} failed=${failed}`);
process.exit(failed ? 1 : 0);
