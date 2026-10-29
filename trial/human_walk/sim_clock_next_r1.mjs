/** Real-browser: start execution from the classroom panel, then advance the current stop, and
 * read the clock card's current-stop + simulated traveller before/after a reload. */
import fs from "node:fs";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/sim-clock-next-1.txt";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let wsUrl = null; let nextId = 1;
async function send(method, params, timeoutMs = 30000) {
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
async function press(testid) {
  const rect = await evaluate(`(() => {
    const el = document.querySelector("[data-testid='${testid}']");
    if (!el) return { found: false };
    el.scrollIntoView({ block: "center" });
    const r = el.getBoundingClientRect();
    return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: !!el.disabled,
      aria_disabled: el.getAttribute("aria-disabled") };
  })()`);
  if (!rect.found || rect.disabled) return rect;
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  return rect;
}
const state = () => evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const tid = (t) => { const n = document.querySelector("[data-testid='" + t + "']"); return n ? flat(n.innerText).slice(0, 240) : null; };
  return { clock: tid("sim-clock"), value: tid("sim-clock-value"), traveller: tid("sim-clock-traveller"),
    outcome: tid("sim-outcome"),
    stage: (() => { const n = document.querySelector("[data-testid='sim-banner']"); return n ? flat(n.innerText).slice(0, 140) : null; })(),
    panel: !!document.querySelector("[data-testid='sim-panel']") };
})()`);

const list = await (await fetch("http://127.0.0.1:9335/json/list")).json();
const pages = list.filter((t) => t.type === "page" && (t.url || "").startsWith("http://127.0.0.1:14461/") && !(t.url || "").includes("/revolution"));
let page = pages[0];
if (!page) {
  const created = await (await fetch("http://127.0.0.1:9335/json/new?" + encodeURIComponent("http://127.0.0.1:14461/"), { method: "PUT" })).json();
  page = created; await sleep(7000);
}
wsUrl = page.webSocketDebuggerUrl;
await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
await sleep(1200);
if (!(await state()).panel) { emit(`BALL ${JSON.stringify(await press("sim-ball"))}`); await sleep(2200); }
emit(`BEFORE ${JSON.stringify(await state())}`);
emit(`START ${JSON.stringify(await press("sim-action-start"))}`);
await sleep(8000);
emit(`AFTER_START ${JSON.stringify(await state())}`);
emit(`SHOT_STARTED ${JSON.stringify(await shot("sim-clock-390-started.png"))}`);
for (let i = 0; i < 4; i += 1) {
  const before = await state();
  const pressed = await press("sim-action-advance");
  await sleep(4000);
  const after = await state();
  emit(`STEP${i} ${JSON.stringify({ pressed, before: before.value, after: after.value, outcome: after.outcome })}`);
  if (after.traveller && after.traveller !== before.traveller) break;
}
emit(`AFTER_STEPS ${JSON.stringify(await state())}`);
emit(`SHOT_NEXT ${JSON.stringify(await shot("sim-clock-390-next.png"))}`);
await evaluate("location.reload(); 'reload'");
await sleep(8000);
if (!(await state()).panel) { await press("sim-ball"); await sleep(2200); }
emit(`AFTER_RELOAD ${JSON.stringify(await state())}`);
emit(`SHOT_RELOAD ${JSON.stringify(await shot("sim-clock-390-next-reload.png"))}`);
console.log(log.join("\n"));
