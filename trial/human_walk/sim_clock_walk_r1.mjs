/** Real-browser walk of the classroom clock card: root shell -> sim-ball -> +1 hour -> reload. */
import fs from "node:fs";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/sim-clock-walk-1.txt";
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
async function press(testid) {
  const rect = await evaluate(`(() => {
    const el = document.querySelector("[data-testid='${testid}']");
    if (!el) return { found: false };
    el.scrollIntoView({ block: "center" });
    const r = el.getBoundingClientRect();
    return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: !!el.disabled };
  })()`);
  if (!rect.found || rect.disabled) return rect;
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  return rect;
}
const state = () => evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const tid = (t) => { const n = document.querySelector("[data-testid='" + t + "']"); return n ? flat(n.innerText).slice(0, 220) : null; };
  return { clock: tid("sim-clock"), clock_value: tid("sim-clock-value"), error: tid("sim-clock-error"),
    traveller: tid("sim-clock-traveller"), has_ball: !!document.querySelector("[data-testid='sim-ball']"),
    has_panel: !!document.querySelector("[data-testid='sim-panel']"), path: location.pathname };
})()`);

const created = await (await fetch("http://127.0.0.1:9335/json/new?" + encodeURIComponent("http://127.0.0.1:14461/"), { method: "PUT" })).json();
wsUrl = created.webSocketDebuggerUrl;
emit(`OPEN ${created.id}`);
await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
await sleep(7000);
emit(`HOME ${JSON.stringify(await state())}`);
emit(`BALL ${JSON.stringify(await press("sim-ball"))}`);
await sleep(2500);
emit(`OPENED ${JSON.stringify(await state())}`);
const before = await state();
emit(`SHOT_BEFORE ${JSON.stringify(await shot("sim-clock-390-before.png"))}`);
emit(`ADVANCE ${JSON.stringify(await press("sim-clock-advance-60"))}`);
await sleep(3000);
const after = await state();
emit(`AFTER_ADVANCE ${JSON.stringify(after)}`);
emit(`SHOT_AFTER ${JSON.stringify(await shot("sim-clock-390-after.png"))}`);
await evaluate("location.reload(); 'reload'");
await sleep(8000);
emit(`BALL2 ${JSON.stringify(await press("sim-ball"))}`);
await sleep(2500);
const reloaded = await state();
emit(`AFTER_RELOAD ${JSON.stringify(reloaded)}`);
emit(`SHOT_RELOAD ${JSON.stringify(await shot("sim-clock-390-reload.png"))}`);
emit(`VERDICT ${JSON.stringify({ before: before.clock_value, after: after.clock_value, reloaded: reloaded.clock_value })}`);
console.log(log.join("\n"));
