/** Does the pointer on this device still name the traveller this tab is signed in as? */
import { createRequire } from "node:module";
const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");
const browser = await chromium.connectOverCDP("http://127.0.0.1:9335");
const context = browser.contexts()[0];
const page = context.pages().find((p) => p.url().includes("14381"));
if (!page) { console.log("NO_TAB"); process.exit(0); }
const read = () => page.evaluate(() => {
  const pointer = JSON.parse(localStorage.getItem("citynexus.revolution.firstlook.journey") || "null");
  const recent = JSON.parse(localStorage.getItem("citynexus.revolution.firstlook.recent-journeys") || "[]");
  return {
    session_id: window.sessionStorage.getItem("citynexus.traveler.session-id"),
    bearer_present: Boolean(window.sessionStorage.getItem("citynexus.traveler.bearer")),
    pointer_owner: pointer ? pointer.ownerTravelerId : null,
    pointer_id: pointer ? pointer.id : null,
    recent_owners: recent.map((r) => (r.ownerTravelerId || "none").slice(0, 14)),
    tiles: document.querySelectorAll(".cn-place-photo").length,
  };
});
console.log("NOW " + JSON.stringify(await read()));
await page.reload({ waitUntil: "domcontentloaded" });
await page.waitForTimeout(6000);
console.log("AFTER_RELOAD " + JSON.stringify(await read()));
process.exit(0);
