/** Remove the one location-less band ("天坛周边补充") through the draft editor's own controls,
 * save the draft, and report the saved state. Real pointer clicks only. */
import fs from "node:fs";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/drop-placeholder-1.txt";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let wsUrl = null; let nextId = 1;
async function send(method, params, timeoutMs = 25000) {
  const ws = new WebSocket(wsUrl); const id = nextId++;
  return new Promise((resolve) => {
    const timer = setTimeout(() => { try { ws.close(); } catch {} resolve({ error: "timeout" }); }, timeoutMs);
    ws.onopen = () => ws.send(JSON.stringify({ id, method, params }));
    ws.onmessage = (event) => { const msg = JSON.parse(event.data); if (msg.id !== id) return; clearTimeout(timer); try { ws.close(); } catch {} resolve(msg.error ? { error: msg.error.message } : (msg.result || {})); };
    ws.onerror = () => { clearTimeout(timer); resolve({ error: "ws error" }); };
  });
}
async function evaluate(expression, timeoutMs = 25000) {
  const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }, timeoutMs);
  return r.error ? { error: r.error } : (r.result?.value ?? { error: "no value" });
}
async function shot(name) {
  const r = await send("Page.captureScreenshot", { format: "png" }, 25000);
  if (!r.data) return { error: r.error || "no data" };
  fs.writeFileSync(DIR + "/" + name, Buffer.from(r.data, "base64"));
  return { bytes: fs.statSync(DIR + "/" + name).size };
}
async function clickByJs(expression) {
  const rect = await evaluate(expression);
  if (!rect.found || rect.disabled) return rect;
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  return rect;
}
const clickText = (label) => clickByJs(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const b = [...document.querySelectorAll("button")].find((x) => flat(x.innerText) === ${JSON.stringify(label)} && x.getBoundingClientRect().width > 0);
  if (!b) return { found: false };
  b.scrollIntoView({ block: "center" });
  const r = b.getBoundingClientRect();
  return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: !!b.disabled };
})()`);
const clickTid = (tid) => clickByJs(`(() => {
  const el = document.querySelector("[data-testid='${tid}']");
  if (!el) return { found: false };
  el.scrollIntoView({ block: "center" });
  const r = el.getBoundingClientRect();
  return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: !!el.disabled };
})()`);
const state = () => evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const text = flat(document.body.innerText);
  const band = [...document.querySelectorAll("details")].find((d) => flat(d.querySelector("summary")?.innerText || "").includes("天坛周边补充"));
  const dayTabs = [...document.querySelectorAll("[role='tab']")].map((t) => flat(t.innerText));
  return { dayTabs, band: band ? flat(band.querySelector("summary").innerText) : null,
    band_open: band ? band.open : null,
    draft_status: (() => { const p = [...document.querySelectorAll("p[role='status'],p[role='alert']")].map((n) => flat(n.innerText)); return p.slice(-2); })(),
    has_prep: !!document.querySelector("[data-testid='rev-v3-generate-plans']"),
    save: (() => { const b = [...document.querySelectorAll("button")].find((x) => ["保存草案", "检查草案保存状态"].includes(flat(x.innerText))); return b ? flat(b.innerText) : null; })() };
})()`);

const pages = (await (await fetch("http://127.0.0.1:9335/json/list")).json()).filter((t) => t.type === "page" && (t.url || "").includes("14461"));
wsUrl = pages[0].webSocketDebuggerUrl;
await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
await sleep(800);
emit(`TAB ${JSON.stringify(await clickText("我的旅程"))}`);
await sleep(2500);
emit(`AT_TRIPS ${JSON.stringify(await state())}`);
emit(`SHOT_TRIPS ${JSON.stringify(await shot("drop-placeholder-390-trips.png"))}`);
const s0 = await state();
if (s0.dayTabs.length > 1) {
  emit(`DAY2 ${JSON.stringify(await clickByJs(`(() => {
    const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
    const b = [...document.querySelectorAll("button")].find((x) => flat(x.innerText).startsWith("Day 2"));
    if (!b) return { found: false };
    b.scrollIntoView({ block: "center" });
    const r = b.getBoundingClientRect();
    return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`))}`);
  await sleep(1200);
}
emit(`OPEN_BAND ${JSON.stringify(await clickByJs(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const d = [...document.querySelectorAll("details")].find((x) => flat(x.querySelector("summary")?.innerText || "").includes("天坛周边补充"));
  if (!d) return { found: false };
  const s = d.querySelector("summary");
  s.scrollIntoView({ block: "center" });
  const r = s.getBoundingClientRect();
  return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2 };
})()`))}`);
await sleep(1000);
emit(`REMOVE ${JSON.stringify(await clickByJs(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const d = [...document.querySelectorAll("details")].find((x) => flat(x.querySelector("summary")?.innerText || "").includes("天坛周边补充"));
  if (!d) return { found: false };
  const b = [...d.querySelectorAll("button")].find((x) => flat(x.innerText) === "移除这项安排");
  if (!b) return { found: false };
  b.scrollIntoView({ block: "center" });
  const r = b.getBoundingClientRect();
  return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2 };
})()`))}`);
await sleep(1500);
emit(`AFTER_REMOVE ${JSON.stringify(await state())}`);
emit(`SHOT_REMOVED ${JSON.stringify(await shot("drop-placeholder-390-removed.png"))}`);
emit(`SAVE ${JSON.stringify(await clickText("保存草案"))}`);
for (let i = 0; i < 12; i += 1) {
  await sleep(2000);
  const s = await state();
  emit(`POLL${i} ${JSON.stringify({ save: s.save, status: s.draft_status, band: s.band })}`);
  if (s.draft_status.some((t) => t.includes("草案已保存") || t.includes("已保存到"))) break;
}
emit(`FINAL ${JSON.stringify(await state())}`);
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));
