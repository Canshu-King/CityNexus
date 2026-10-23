/**
 * V3 slice 5 · 三种方案与刷新恢复, on the rescue line, against its own backend.
 *
 * The questions this run answers with readings rather than prose:
 *  1. when the traveller asks for three variants, does the workbench actually show three?
 *  2. can they pick a different one than the first, and does the server say so on screen?
 *  3. after a real page reload -- with nothing but the browser's own storage -- is the same plan
 *     still the one in force, or does the screen silently fall back to "go and explore again"?
 */
import { createRequire } from "module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const [url, bearer, shotBefore, shotAfter, travelerId, journeyId] = process.argv.slice(2);
const say = (label, value) => console.log(`${label} :: ${value}`);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
const writes = [];
const bad = [];
page.on("request", (request) => {
  if (request.method() === "POST" && /\/departure\/commit|\/plans$/.test(request.url())) {
    writes.push({ url: request.url().replace("http://127.0.0.1:5199", "").replace(journeyId, "{journey}"),
                  key: request.headers()["idempotency-key"] ?? null, body: request.postData() });
  }
});
page.on("response", (response) => {
  if (response.status() >= 400) bad.push(`${response.status()} ${response.url().replace("http://127.0.0.1:5199", "").replace(journeyId, "{journey}")}`);
});
page.on("pageerror", (error) => say("PAGEERROR", String(error).slice(0, 240)));

const readGate = async () => (await page.getByTestId("rev-v3-server-departure").innerText().catch(() => "(none)"))
  .replace(/\n/g, " / ");

try {
  await page.addInitScript(([token, id]) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", token);
    window.sessionStorage.setItem("citynexus.traveler.session-id", id);
  }, [bearer, travelerId]);

  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.getByTestId("rev-mobile-tab-trips").click();
  await page.getByTestId("rev-trip-resume").first().click({ timeout: 20000 });
  await page.getByTestId("rev-plan-workbench").waitFor({ state: "visible", timeout: 30000 });

  // the workbench fills itself asynchronously, so a count taken too early reads zero: poll for the
  // variant cards instead of reporting the empty moment as if it were the answer
  let buttons = page.getByTestId("rev-plan-select");
  let seen = await buttons.count();
  for (let waited = 0; seen === 0 && waited < 20; waited += 1) {
    await page.waitForTimeout(1000);
    seen = await buttons.count();
  }
  say("SELECT_BUTTONS", String(seen));
  say("PLAN_HEADINGS", JSON.stringify(await page.locator("h3").allInnerTexts()));
  say("GATE_BEFORE", await readGate());
  await page.screenshot({ path: shotBefore });

  const count = seen;
  if (count >= 2) {
    await buttons.nth(count - 1).click({ timeout: 20000 });   // the LAST variant, on purpose
    say("PRESSED", "the last of the listed variants");
  } else if (count === 1) {
    await buttons.first().click({ timeout: 20000 });
    say("PRESSED", "the only variant the server gave back");
  } else {
    say("PRESSED", "nothing: no 选用 button was on screen");
  }
  await page.waitForTimeout(3000);
  say("GATE_AFTER_COMMIT", await readGate());

  // a real reload: only what the browser itself kept may be used to find the trip again
  await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
  await page.getByTestId("rev-mobile-tab-trips").click();
  await page.waitForTimeout(3000);
  const workbench = page.getByTestId("rev-plan-workbench");
  say("AFTER_RELOAD_WORKBENCH", String(await workbench.count()));
  say("AFTER_RELOAD_GATE", await readGate());
  const live = page.getByTestId("live-recovery");
  say("LIVE_VISIBLE", String(await live.first().isVisible().catch(() => false)));
  say("LIVE_KICKER", (await live.locator("p").first().innerText().catch(() => "(unreadable)")).replace(/\s+/g, " ").trim());
  say("LIVE_TITLE", (await live.locator("h1").first().innerText().catch(() => "(unreadable)")).replace(/\s+/g, " ").trim());
  say("LIVE_NEXT", (await live.getByTestId("live-next").innerText().catch(() => "(unreadable)")).replace(/\s+/g, " ").trim());
  await page.screenshot({ path: shotAfter.replace(".png", "-live.png") }).catch(() => say("SCREENSHOT", "live failed"));
  say("AFTER_RELOAD_HEADLINE", (await page.locator("body").innerText())
    .replace(/\s+/g, " ").slice(0, 260));
  say("HTTP_WRITES", JSON.stringify(writes));
  say("HTTP_4XX", JSON.stringify(bad));
  await page.screenshot({ path: shotAfter });
  say("SCREENSHOTS", `${shotBefore} | ${shotAfter}`);
} catch (error) {
  say("STEP_FAILED", String(error).slice(0, 260));
  say("BODY_TEXT", (await page.locator("body").innerText().catch(() => "(unreadable)")).replace(/\s+/g, " ").slice(0, 300));
  await page.screenshot({ path: shotAfter }).catch(() => say("SCREENSHOT", "failed"));
} finally {
  await browser.close();
}
