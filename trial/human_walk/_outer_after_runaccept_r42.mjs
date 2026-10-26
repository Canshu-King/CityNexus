import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/outer-after-runaccept-390.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const injected = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.demo_ticket_run3.json", "utf8"));

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_classroom_run4", {
  channel: "chrome", headless: false, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
let cdp = null;
async function shot(name) {
  try {
    cdp ??= await page.context().newCDPSession(page);
    const { data } = await cdp.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(`${DIR}/${name}.png`, Buffer.from(data, "base64"));
    note("SHOT " + name);
  } catch (e) { note("SHOT_ERR " + String(e).slice(0, 60)); }
}

await page.goto(`http://127.0.0.1:14492/revolution#pair=${injected.ticket}`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(9000);
const read = async () => {
  const text = await page.evaluate(() => document.body.innerText || "");
  return {
    first: (text.match(/第一站[：:][^\n]{0,60}/) || [null])[0],
    next: (text.match(/接下来[：:][^\n]{0,50}/) || [null])[0],
    now: (text.match(/现在[：:][^\n]{0,50}/) || [null])[0],
    running: /行程执行中|旅途正在继续/.test(text),
  };
};
note("FIRST_VIEW " + JSON.stringify(await read()));
await shot("outer-after-runaccept-390-a");
await page.reload({ waitUntil: "domcontentloaded" });
await page.waitForTimeout(8000);
note("AFTER_RELOAD " + JSON.stringify(await read()));
await shot("outer-after-runaccept-390-b");
await ctx.close();
