// v2: iterative phone walk. Re-reads the button set after every tap, so the
// bottom nav that only exists post-onboarding is actually reachable.
const path = require("path");
const fs = require("fs");
const { chromium } = require(path.join("D:", "moodle", "CityNexus", "frontend", "node_modules", "playwright"));
const OUT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_walkthrough_r2.json";
const SHOTDIR = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_walk_shots";
const BASE = "http://127.0.0.1:4781/";
function txt(s) { return (s || "").replace(/\s+/g, " ").trim(); }

(async () => {
  fs.mkdirSync(SHOTDIR, { recursive: true });
  const report = { base: BASE, steps: [], console_errors: [] };
  const browser = await chromium.launch({ channel: "chrome" });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  page.on("pageerror", e => report.console_errors.push("pageerror:" + txt(String(e)).slice(0, 200)));
  page.on("console", m => { if (m.type() === "error") report.console_errors.push(txt(m.text()).slice(0, 200)); });

  await page.goto(BASE, { waitUntil: "networkidle", timeout: 45000 });
  const read = async () => {
    const labels = (await page.locator("button").allInnerTexts()).map(txt).filter(Boolean);
    const body = txt(await page.locator("body").innerText());
    return { labels, body };
  };
  let st = await read();
  report.steps.push({ step: "landing", labels: st.labels.slice(0, 20), body_chars: st.body.length, body_head: st.body.slice(0, 300) });

  const enter = st.labels.find(l => /封存的演示行程/.test(l));
  if (enter) {
    await page.getByRole("button", { name: enter }).first().click();
    await page.waitForTimeout(1500);
    st = await read();
    report.steps.push({ step: "entered", label: enter, labels: st.labels.slice(0, 20), body_chars: st.body.length });
  }
  const names = { "行程": "studio", "地图": "map", "Copilot": "copilot", "我的": "me", "今天": "today" };
  for (const target of ["行程", "地图", "Copilot", "我的", "今天"]) {
    const label = st.labels.find(l => l === target || (target === "Copilot" && /Copilot/.test(l)));
    if (!label) { report.steps.push({ step: "not_found", want: target, have: st.labels.slice(0, 14) }); continue; }
    try {
      await page.getByRole("button", { name: label, exact: false }).first().click({ timeout: 6000 });
      await page.waitForTimeout(1400);
      st = await read();
      const file = path.join(SHOTDIR, "walk_" + (names[target] || ("step_" + report.steps.length)) + ".png");
      await page.screenshot({ path: file });
      report.steps.push({ step: "visit", want: target, tapped: label, body_chars: st.body.length,
                          labels: st.labels.slice(0, 16), body_head: st.body.slice(0, 620),
                          screenshot: file, shot_bytes: fs.statSync(file).size });
    } catch (e) { report.steps.push({ step: "click_failed", want: label, err: txt(String(e)).slice(0, 200) }); }
  }
  report.console_errors = report.console_errors.slice(0, 20);
  await browser.close();
  fs.writeFileSync(OUT, JSON.stringify(report, null, 1));
  console.log("WROTE steps=" + report.steps.length + " errs=" + report.console_errors.length);
})().catch(e => { fs.writeFileSync(OUT, JSON.stringify({ fatal: String(e) }, null, 1)); console.log("FATAL"); });
