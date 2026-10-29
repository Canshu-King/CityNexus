/** Press the research control once and watch whether a formal candidate plan appears. */
import fs from "node:fs";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/play-v3-research-1.txt";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let wsUrl = null; let nextId = 1;
async function send(method, params, timeoutMs = 20000) {
  const ws = new WebSocket(wsUrl); const id = nextId++;
  return new Promise((resolve) => {
    const timer = setTimeout(() => { try { ws.close(); } catch {} resolve({ error: "timeout" }); }, timeoutMs);
    ws.onopen = () => ws.send(JSON.stringify({ id, method, params }));
    ws.onmessage = (event) => { const msg = JSON.parse(event.data); if (msg.id !== id) return; clearTimeout(timer); try { ws.close(); } catch {} resolve(msg.error ? { error: msg.error.message } : (msg.result || {})); };
    ws.onerror = () => { clearTimeout(timer); resolve({ error: "ws error" }); };
  });
}
async function evaluate(expression, timeoutMs = 15000) {
  const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }, timeoutMs);
  return r.error ? { error: r.error } : (r.result?.value ?? { error: "no value" });
}
async function shot(name) {
  const r = await send("Page.captureScreenshot", { format: "png" }, 20000);
  if (!r.data) return { error: r.error || "no data" };
  fs.writeFileSync(DIR + "/" + name, Buffer.from(r.data, "base64"));
  return { bytes: fs.statSync(DIR + "/" + name).size };
}
const pages = (await (await fetch("http://127.0.0.1:9335/json/list")).json()).filter((t) => t.type === "page" && (t.url || "").includes("14461"));
for (const p of pages) { wsUrl = p.webSocketDebuggerUrl; if ((await evaluate("document.body.innerText.includes('旅行研究')")) === true) break; }
const click = await evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const b = [...document.querySelectorAll("button")].find((x) => flat(x.innerText) === "按讨论的方向开始研究" && !x.disabled);
  if (!b) return { found: false };
  b.scrollIntoView({ block: "center" });
  const r = b.getBoundingClientRect();
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, hit_is_self: hit === b || b.contains(hit) };
})()`);
emit(`PRESS ${JSON.stringify(click)}`);
if (click.found) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: click.x, y: click.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: click.x, y: click.y, button: "left", clickCount: 1 });
}
const state = () => evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const text = flat(document.body.innerText);
  return { question: !!document.querySelector("[aria-label='Agent 请你选择']"),
    running: /Agent 正在推进|正在研究/.test(text), plans: /份正式候选方案/.test(text),
    select_button: [...document.querySelectorAll("button")].some((b) => flat(b.innerText) === "选用这份方案"),
    places: /处地点|个地点/.test(text), head: text.slice(-360) };
})()`);
for (let i = 0; i < 21; i += 1) {
  await sleep(10000);
  const s = await state();
  emit(`POLL${i} ${JSON.stringify(s)}`);
  if (s.select_button || s.plans || (!s.running && i > 2 && !s.question)) break;
}
emit(`FINAL ${JSON.stringify(await state())}`);
emit(`SHOT ${JSON.stringify(await shot("play-v3-research-1.png"))}`);
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));
