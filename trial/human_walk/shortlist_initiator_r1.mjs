/**
 * Who asks the server for a bootstrap shortlist, and from which line of the bundle?
 *
 * Three walks logged HTTP_409 on GET /journeys/<id>/bootstrap-shortlist with reason
 * BOOTSTRAP_PLAN_ALREADY_EXISTS, but the walk listener records only status + URL, so the
 * request had no author.  This attaches Chrome's own Network domain, which carries the
 * initiator stack, reloads the tab the traveller already has open, and writes down who
 * fired the request, what the browser held locally, and what the screen said afterwards.
 *
 * Nothing is seeded here: the page is reloaded as a person would, and localStorage is only
 * read, never written.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const LOG = process.env.PROBE_LOG || "shortlist-initiator-1.txt";
const stream = fs.openSync(path.join(OUT, LOG), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();
const page = context.pages().find((p) => (p.url() || "").includes("/revolution")) ?? context.pages()[0];
say(`PROBE_START ${new Date().toISOString()} url=${page.url()}`);

const cdp = await context.newCDPSession(page);
await cdp.send("Network.enable");
cdp.on("Network.requestWillBeSent", (event) => {
  const url = event.request?.url ?? "";
  if (!url.includes("bootstrap-shortlist")) return;
  const init = event.initiator ?? {};
  const frames = (init.stack?.callFrames ?? init.parent?.stack?.callFrames ?? [])
    .slice(0, 4)
    .map((f) => `${(f.url || "").split("/").pop()}:${f.lineNumber + 1} ${f.functionName || "(anon)"}`);
  say(`ASK ${event.request.method} ${url.split("/api/v1")[1] ?? url} initiator=${init.type}${frames.length ? " | " + frames.join(" <- ") : ""}`);
});
page.on("response", (response) => {
  const url = response.url();
  if (!url.includes("bootstrap-shortlist")) return;
  say(`ANSWER ${response.status()} ${url.split("/api/v1")[1] ?? url}`);
});

const local = await page.evaluate(() => {
  const out = {};
  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i);
    if (/journey|traveler|v8|revolution/i.test(key)) out[key] = String(localStorage.getItem(key)).slice(0, 120);
  }
  return out;
}).catch((e) => ({ probe_error: flat(e.message).slice(0, 80) }));
say(`LOCAL_KEYS ${JSON.stringify(local).slice(0, 900)}`);

await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 }).catch((e) => say(`RELOAD_FAILED ${flat(e.message).slice(0, 60)}`));
await page.waitForTimeout(14000);

const body = await page.evaluate(() => document.body.innerText.replace(/\s+/g, " ").trim()).catch(() => "(unreadable)");
say(`SCREEN ${flat(body).slice(0, 700)}`);
say(`SCREEN_HAS_NO_RESTORE_TEXT=${/旧行程无法恢复/.test(body)}`);
say(`PROBE_DONE ${new Date().toISOString()}`);
await browser.disconnect();
