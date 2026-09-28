/* ORD-0417 entry diagnostic r2 -- does the demo-entry click actually land, and what did the server say?
   r1 of this probe only loaded the route, so `has_panel:false` proved nothing about the product.
   This one records ENTRY_FOUND, the HTTP statuses the click produced, and reached_route afterwards --
   the same self-proof cmdr's untranslated_scan_r3.js added after its r2 measured the wrong screen. */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
(async () => {
  const base = (process.argv[2] || "http://127.0.0.1:4843/").replace(/\/$/, "");
  const br = await chromium.launch({ channel: "chrome", headless: true });
  const p = await br.newPage({ viewport: { width: 390, height: 844 } });
  const seen = [];
  p.on("response", (r) => { const u = r.url(); if (u.includes("/api/")) seen.push(r.status() + " " + u.replace(base, "").slice(0, 74)); });
  await p.goto(base + "/v8/map", { waitUntil: "networkidle", timeout: 60000 });
  await p.waitForTimeout(2000);
  const btn = p.getByText("使用封存的演示行程", { exact: false }).first();
  const found = await btn.count();
  let clicked = false;
  if (found) { await btn.click(); clicked = true; await p.waitForTimeout(8000); }
  const read = await p.evaluate(() => ({
    path: location.pathname, lang: document.documentElement.lang,
    stored_journey: (localStorage.getItem("citynexus.v8.journey_id") || "").slice(0, 13),
    has_panel: !!document.querySelector(".v8-map-panel"),
    markers: document.querySelectorAll(".v8-map-panel .v9-map-marker").length,
    caption: (document.querySelector(".v8-map-caption")?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 90),
    body_head: (document.body.innerText || "").replace(/\s+/g, " ").trim().slice(0, 110),
  }));
  console.log(JSON.stringify({ base, entry_found: found, clicked, api_after_click: seen.slice(-10), ...read }, null, 1));
  await br.close();
})().catch((e) => { console.log("FATAL", String(e).slice(0, 200)); process.exit(9); });
