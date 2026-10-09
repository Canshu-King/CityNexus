// AccessPanel.focusInviteForm reaches the control by its testid and focuses it
// (AccessPanel.tsx:365). Replacing that markup with a component could have broken the
// route without breaking anything the height ruler measures, so drive it as a user.
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

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
await page.goto(`${BASE}/hub`);
await page.evaluate((id) => localStorage.setItem("citynexus.v8.journey_id", id), JOURNEY);
await page.goto(`${BASE}/v8/access`, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(1500);

const trigger = page.locator('[data-testid="access-empty-focus-invite"]');
const found = await trigger.count();
if (found === 0) {
  console.log(
    "SKIP  the empty-state door is not on screen; testids present:",
    (
      await page.evaluate(() =>
        Array.from(document.querySelectorAll("[data-testid]"))
          .map((n) => n.getAttribute("data-testid"))
          .filter((t) => t.startsWith("access-"))
          .slice(0, 20)
      )
    ).join(", "),
  );
} else {
  await trigger.click();
  await page.waitForTimeout(500);
  const focused = await page.evaluate(() => {
    const a = document.activeElement;
    return {
      tag: a ? a.tagName.toLowerCase() : null,
      testid: a ? a.getAttribute("data-testid") : null,
      is_the_select: !!a && a.tagName === "SELECT" && a.getAttribute("data-testid") === "access-invite-visibility",
    };
  });
  console.log(
    focused.is_the_select ? "PASS" : "FAIL",
    "focusInviteForm still lands on the control",
    JSON.stringify(focused),
  );
}
await browser.close();
