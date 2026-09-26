/* Commander's own read of a state that needs a click, on the deployed phone bundle.
   Why: my render check only reads the first paint, and today two changes (the honest destination
   grouping, and the technical-details fold) are only visible after a click.  This drives the real
   chain at phone size with the repo's own playwright, and prints the text before and after.
   usage: node cmdr_click_read_r1.js [--base http://127.0.0.1:4781] [--out file.json] */
const path = require("path");
const fs = require("fs");
const NM = "D:/moodle/CityNexus/frontend/node_modules";
const { chromium, devices } = require(path.join(NM, "playwright"));

const arg = (k, d) => {
  const i = process.argv.indexOf(k);
  return i > 0 && process.argv[i + 1] ? process.argv[i + 1] : d;
};
const BASE = arg("--base", "http://127.0.0.1:4781");
const OUT = arg("--out", "patrol/click_read_r1.json");

function txt(el) {
  return el ? el.replace(/\s+/g, " ").trim() : null;
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ ...devices["Pixel 5"], locale: "zh-CN" });
  const page = await ctx.newPage();
  const shots = [];
  try {
    await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForTimeout(3000);
    const body0 = txt(await page.locator("body").innerText().catch(() => ""));
    shots.push({ stage: "first_paint", len: body0.length, head: body0.slice(0, 400) });

    const toggle = page.getByText("看支持的目的地", { exact: false }).first();
    const hasToggle = await toggle.count();
    let clicked = false;
    if (hasToggle) {
      try {
        await toggle.click({ timeout: 8000 });
        clicked = true;
      } catch (e) {
        shots.push({ stage: "click_error", note: String(e).slice(0, 200) });
      }
      await page.waitForTimeout(2500);
      const body1 = txt(await page.locator("body").innerText().catch(() => ""));
      shots.push({
        stage: clicked ? "after_open_destinations" : "click_failed",
        len: body1.length,
        // what the click revealed, not the whole page: the difference against first paint
        added_text: body1.length > body0.length ? body1.slice(body0.length - 40, body0.length + 900) : body1.slice(0, 900),
      });
      await page.screenshot({ path: OUT.replace(/\.json$/, "_opened.png"), fullPage: false });
    }
    const details = await page.evaluate(() => {
      const out = [];
      document.querySelectorAll("details").forEach((d) => {
        out.push({
          summary: (d.querySelector("summary") || {}).innerText || null,
          open: !!d.open,
          inner: ((d.innerText || "").replace(/\s+/g, " ").trim()).slice(0, 300),
          fields: Array.from(d.querySelectorAll("[data-cnx-field]")).map((x) => x.getAttribute("data-cnx-field")),
        });
      });
      return out;
    });
    const attrScan = await page.evaluate(() => {
      const hits = [];
      document.querySelectorAll("*").forEach((el) => {
        for (const a of Array.from(el.attributes || [])) {
          if (/^(data|aria)-/i.test(a.name) && /(error|exception|stack|message|failed|fetch|internal)/i.test(a.value || "")) {
            hits.push({ attr: a.name, value: String(a.value).slice(0, 120) });
          }
        }
      });
      return hits;
    });
    const doc = {
      base: BASE, viewport: "390x844-ish (Pixel 5)", at_local: new Date().toString(),
      clicked, shots, details_blocks: details, suspect_attribute_values: attrScan,
      leak_shapes_on_screen: ["failed to fetch", "typeerror", "internal server error", "net::err"].filter(
        (p) => (shots[shots.length - 1].added_text || "").toLowerCase().includes(p)),
    };
    fs.mkdirSync(path.dirname(OUT), { recursive: true });
    fs.writeFileSync(OUT, JSON.stringify(doc, null, 1), "utf-8");
    console.log("clicked =", clicked, " details_on_page =", details.length,
      " suspect_attrs =", attrScan.length, " leak_on_screen =", doc.leak_shapes_on_screen.join(",") || "none");
    for (const s of shots) console.log(" -", s.stage, "len", s.len, ":", (s.added_text || s.head || "").slice(0, 220));
    console.log("out =", OUT);
  } catch (e) {
    console.log("RUN FAILED:", String(e).slice(0, 300));
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
