/* ORD-0557 boot diagnostic: what does the dev server actually hand the traveller?
 *
 * The screen read came back with an empty body, so before anything is claimed about the failure view
 * this prints the five things that would explain it: the document status, the title, what mounted in
 * #root, every console line, and every request that the stub answered.
 *
 * Run: node review/taichenggong/boot_debug_r1.mjs
 */

import { createRequire } from "node:module";
import { spawn, spawnSync } from "node:child_process";
import path from "node:path";

const HERE = import.meta.dirname;
const REPO = path.resolve(HERE, "..", "..");
const FRONTEND = path.join(REPO, "frontend");
const PORT = Number(process.env.CITYNEXUS_TAICHENG_PORT ?? 4614);
const JOURNEY = "11111111-2222-4333-8444-555555555555";
const { chromium } = createRequire(path.join(FRONTEND, "package.json"))("@playwright/test");

const viteLog = path.join(HERE, "vite_dev.log");
const vite = spawn(process.execPath, [path.join(FRONTEND, "node_modules", "vite", "bin", "vite.js"),
  "--host", "127.0.0.1", "--port", String(PORT), "--strictPort"],
  { cwd: FRONTEND, stdio: ["ignore", "pipe", "pipe"] });
{
  const fs = await import("node:fs");
  const sink = fs.createWriteStream(viteLog);
  vite.stdout.pipe(sink);
  vite.stderr.pipe(sink);
}

const wait = async () => {
  for (let i = 0; i < 90; i += 1) {
    const probe = spawnSync("node", ["-e",
      `fetch("http://127.0.0.1:${PORT}/").then(r=>process.stdout.write(String(r.status))).catch(()=>{})`],
      { encoding: "utf8" });
    if ((probe.stdout ?? "").trim() !== "") return probe.stdout.trim();
    await new Promise((r) => setTimeout(r, 1000));
  }
  return "<no answer in 90s>";
};

console.log("0 vite answered with status", await wait());

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
const page = await context.newPage();
const messages = [];
const requests = [];
page.on("console", (m) => messages.push(`${m.type()}: ${m.text()}`.slice(0, 200)));
page.on("pageerror", (e) => messages.push(`pageerror: ${String(e.message).slice(0, 200)}`));
page.on("request", (r) => requests.push(`${r.method()} ${r.url()}`.slice(0, 140)));
await page.addInitScript(({ id, loc }) => {
  localStorage.clear();
  localStorage.setItem("citynexus.v8.journey_id", id);
  localStorage.setItem("citynexus.locale", loc);
}, { id: JOURNEY, loc: "zh-CN" });
await page.route("**/api/**", (r) => {
  requests.push(`STUBBED ${r.request().url()}`.slice(0, 140));
  return r.fulfill({ status: 200, contentType: "application/json",
    body: JSON.stringify({ detail: "lane stub" }) });
});
const response = await page.goto(`http://127.0.0.1:${PORT}/v8/hub`, { waitUntil: "load" });
console.log("1 document status", response?.status(), "url", response?.url());
console.log("2 title", await page.title());
console.log("3 root mounts", await page.evaluate(() => {
  const root = document.getElementById("root");
  return { children: root ? root.childElementCount : -1, text: (root?.innerText ?? "").slice(0, 240),
    bodyLen: document.body.innerText.length };
}));
await page.waitForTimeout(6000);
console.log("4 after 6s", await page.evaluate(() => ({
  text: (document.getElementById("root")?.innerText ?? "").slice(0, 400),
  testids: [...document.querySelectorAll("[data-testid]")].map((e) => e.getAttribute("data-testid")).slice(0, 25),
})));
console.log("5 console lines", messages.slice(0, 12));
console.log("6 requests", requests.slice(0, 20));
await browser.close();
vite.kill("SIGTERM");
