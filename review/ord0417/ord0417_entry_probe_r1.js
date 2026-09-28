/* ORD-0417 entry diagnostic: does the demo-entry affordance still say what the instruments click? */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
(async () => {
  const br = await chromium.launch({ channel: "chrome", headless: true });
  const p = await br.newPage({ viewport: { width: 390, height: 844 } });
  const url = (process.argv[2] || "http://127.0.0.1:4841/") + "v8/map";
  await p.goto(url, { waitUntil: "networkidle", timeout: 60000 });
  await p.waitForTimeout(2500);
  const read = await p.evaluate(() => ({
    path: location.pathname, lang: document.documentElement.lang,
    stored_locale: localStorage.getItem("citynexus.locale"), stored_journey: (localStorage.getItem("citynexus.v8.journey_id") || "").slice(0, 8),
    buttons: Array.from(document.querySelectorAll("button")).map((b) => (b.innerText || "").replace(/\s+/g, " ").trim().slice(0, 44)).filter(Boolean).slice(0, 12),
    has_panel: !!document.querySelector(".v8-map-panel"), markers: document.querySelectorAll(".v9-map-marker").length,
    body_head: (document.body.innerText || "").replace(/\s+/g, " ").trim().slice(0, 150),
  }));
  console.log(JSON.stringify(read, null, 1));
  await br.close();
})().catch((e) => { console.log("FATAL", String(e).slice(0, 200)); process.exit(9); });
