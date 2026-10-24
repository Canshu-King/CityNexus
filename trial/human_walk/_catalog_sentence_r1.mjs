/** Press 生成正式候选 once more on the live stack and read the new catalogue sentence. */
import fs from "node:fs";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(DIR + "/catalog-sentence-1.txt", log.join("\n") + "\n"); };
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
async function evaluate(expression) {
  const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  return r.error ? { error: r.error } : (r.result?.value ?? null);
}
async function shot(name) {
  const r = await send("Page.captureScreenshot", { format: "png" });
  if (!r.data) return { error: r.error || "no data" };
  fs.writeFileSync(DIR + "/" + name, Buffer.from(r.data, "base64"));
  return { bytes: fs.statSync(DIR + "/" + name).size };
}
const pages = (await (await fetch("http://127.0.0.1:9335/json/list")).json()).filter((t) => t.type === "page" && (t.url || "").includes("14461"));
let chosen = null;
// pick the page that has the generate control
for (const p of pages) {
  const w = new WebSocket(p.webSocketDebuggerUrl);
  const ok = await new Promise((resolve) => {
    const t = setTimeout(() => { try { w.close(); } catch {} resolve(false); }, 8000);
    w.onopen = () => w.send(JSON.stringify({ id: 1, method: "Runtime.evaluate", params: { returnByValue: true, expression: "!!document.querySelector(\"[data-testid='rev-v3-generate-plans']\")" } }));
    w.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id !== 1) return; clearTimeout(t); try { w.close(); } catch {} resolve(m.result?.result?.value === true); };
  });
  if (ok) { chosen = p; break; }
}
if (!chosen) { emit("NO_PAGE"); console.log(log.join("\n")); process.exit(0); }
wsUrl = chosen.webSocketDebuggerUrl;
await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
await sleep(800);
const press = await evaluate(`(() => {
  const b = [...document.querySelectorAll("button")].find((x) => String(x.innerText).replace(/\\s+/g, " ").trim() === "我的旅程");
  if (b) b.click();
  const g = document.querySelector("[data-testid='rev-v3-generate-plans']");
  if (!g) return { found: false };
  g.scrollIntoView({ block: "center" });
  const r = g.getBoundingClientRect();
  return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: !!g.disabled };
})()`);
emit(`PRESS ${JSON.stringify(press)}`);
if (press.found && !press.disabled) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: press.x, y: press.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: press.x, y: press.y, button: "left", clickCount: 1 });
}
await sleep(7000);
const out = await evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  return { status: [...document.querySelectorAll("[role='status'],[role='alert']")].map((n) => flat(n.innerText)).filter(Boolean).slice(-2),
    card: (() => { const n = document.querySelector("[data-testid='rev-v3-generate-plans']"); return n ? flat(n.closest("section").innerText).slice(-320) : null; })() };
})()`);
emit(`AFTER ${JSON.stringify(out)}`);
emit(`SHOT ${JSON.stringify(await shot("catalog-sentence-390.png"))}`);
console.log(log.join("\n"));
