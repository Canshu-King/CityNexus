// Commander's own check of the just-landed AI three-stage surface, on the phone chain,
// with the server's AI switch OFF (CITYNEXUS_AI_ENABLED=false on hop1).
// Reads what the traveller actually sees -- body.innerText -- not data attributes.
const path = require("path");
const fs = require("fs");
const { chromium } = require(path.join("D:", "moodle", "CityNexus", "frontend", "node_modules", "playwright"));
const OUT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_ai_sheet_walk_r1.json";
const SHOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_walk_shots/ai_sheet_off.png";
const BASE = "http://127.0.0.1:4781/";
function txt(s) { return (s || "").replace(/\s+/g, " ").trim(); }

(async () => {
  const rep = { base: BASE, steps: [], console_errors: [] };
  const browser = await chromium.launch({ channel: "chrome" });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  page.on("pageerror", e => rep.console_errors.push("pageerror:" + txt(String(e)).slice(0, 200)));
  page.on("console", m => { if (m.type() === "error") rep.console_errors.push(txt(m.text()).slice(0, 200)); });
  await page.goto(BASE, { waitUntil: "networkidle", timeout: 45000 });
  const read = async () => ({
    labels: (await page.locator("button").allInnerTexts()).map(txt).filter(Boolean),
    body: txt(await page.locator("body").innerText()),
  });
  let st = await read();
  rep.steps.push({ step: "landing", labels: st.labels.slice(0, 10), body_chars: st.body.length });
  const enter = st.labels.find(l => /封存的演示行程/.test(l));
  if (enter) {
    await page.getByRole("button", { name: enter }).first().click();
    await page.waitForTimeout(1600);
    st = await read();
    rep.steps.push({ step: "entered", body_chars: st.body.length });
  }
  const ai = st.labels.find(l => /AI 帮我规划|帮我规划/.test(l));
  if (!ai) { rep.steps.push({ step: "no_ai_entry", have: st.labels.slice(0, 20) }); }
  else {
    await page.getByRole("button", { name: ai }).first().click();
    await page.waitForTimeout(1800);
    st = await read();
    await page.screenshot({ path: SHOT });
    rep.steps.push({ step: "sheet_open", tapped: ai, body_chars: st.body.length,
                     body_head: st.body.slice(0, 1400), labels: st.labels.slice(0, 24),
                     screenshot: SHOT, shot_bytes: fs.statSync(SHOT).size });
  }
  await browser.close();
  fs.writeFileSync(OUT, JSON.stringify(rep, null, 1));
  console.log("WROTE steps=" + rep.steps.length + " errs=" + rep.console_errors.length);
})().catch(e => { fs.writeFileSync(OUT, JSON.stringify({ fatal: String(e) }, null, 1)); console.log("FATAL"); });
