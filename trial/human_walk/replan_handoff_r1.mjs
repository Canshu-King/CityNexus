/** Verify the refusal's handoff on the live card: press 选用 on 方案 2 (the one the server
 * refused for travel time), read the new in-place 根据路线重新安排 control, press it with a real
 * pointer, and check that the diff appears in the departure card. */
import fs from "node:fs";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/replan-handoff-1.txt";
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
  return r.error ? { error: r.error } : (r.result?.value ?? null);
}
async function shot(name) {
  const r = await send("Page.captureScreenshot", { format: "png" }, 25000);
  if (!r.data) return { error: r.error || "no data" };
  fs.writeFileSync(DIR + "/" + name, Buffer.from(r.data, "base64"));
  return { bytes: fs.statSync(DIR + "/" + name).size };
}
const state = () => evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const tid = (t) => { const n = document.querySelector("[data-testid='" + t + "']"); return n ? { text: flat(n.innerText).slice(0, 260), disabled: !!n.disabled } : null; };
  const cards = [...document.querySelectorAll("[data-testid='rev-plan-option']")].map((n) => flat(n.innerText).slice(0, 24));
  return { cards, message: (() => { const n = document.querySelector(".rev-plan-message"); return n ? flat(n.innerText) : null; })(),
    handoff: tid("rev-plan-replan"), diff: tid("rev-v3-replan-diff"), apply: tid("rev-v3-replan-apply"),
    status: [...document.querySelectorAll("[role='status'],[role='alert']")].map((n) => flat(n.innerText)).filter(Boolean).slice(-2),
    scrollY: Math.round(window.scrollY) };
})()`);
const pages = (await (await fetch("http://127.0.0.1:9335/json/list")).json()).filter((t) => t.type === "page" && (t.url || "").includes("14461"));
let page = null;
for (const p of pages) {
  const has = await new Promise((resolve) => {
    const w = new WebSocket(p.webSocketDebuggerUrl);
    const t = setTimeout(() => { try { w.close(); } catch {} resolve(false); }, 8000);
    w.onopen = () => w.send(JSON.stringify({ id: 1, method: "Runtime.evaluate", params: { returnByValue: true, expression: "!!document.querySelector(\"[data-testid='rev-mission-cockpit']\") && !document.body.innerText.includes('登录已过期')" } }));
    w.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id !== 1) return; clearTimeout(t); try { w.close(); } catch {} resolve(m.result?.result?.value === true); };
  });
  if (has) { page = p; break; }
}
if (!page) { emit("NO_PAGE"); console.log(log.join("\n")); process.exit(0); }
wsUrl = page.webSocketDebuggerUrl;
await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
await sleep(800);
const tab = await evaluate(`(() => {
  const b = [...document.querySelectorAll("button")].find((x) => String(x.innerText).replace(/\s+/g, " ").trim() === "我的旅程");
  if (!b) return { found: false };
  b.scrollIntoView({ block: "center" });
  const r = b.getBoundingClientRect();
  return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2 };
})()`);
if (tab.found) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: tab.x, y: tab.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: tab.x, y: tab.y, button: "left", clickCount: 1 });
  await sleep(2500);
}
emit(`TAB ${JSON.stringify(tab)}`);
emit(`BEFORE ${JSON.stringify(await state())}`);
const press = await evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const card = [...document.querySelectorAll("[data-testid='rev-plan-option']")].find((n) => flat(n.innerText).startsWith("方案 2"));
  if (!card) return { found: false, why: "no card 2" };
  const b = card.querySelector("[data-testid='rev-plan-select']");
  if (!b) return { found: false, why: "no select in card 2", tail: flat(card.innerText).slice(-160) };
  b.scrollIntoView({ block: "center" });
  const r = b.getBoundingClientRect();
  return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: !!b.disabled };
})()`);
emit(`PRESS_SELECT ${JSON.stringify(press)}`);
if (press.found && !press.disabled) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: press.x, y: press.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: press.x, y: press.y, button: "left", clickCount: 1 });
  await sleep(9000);
}
emit(`AFTER_SELECT ${JSON.stringify(await state())}`);
emit(`SHOT_REFUSED ${JSON.stringify(await shot("replan-handoff-390-refused.png"))}`);
const hand = await evaluate(`(() => {
  const b = document.querySelector("[data-testid='rev-plan-replan']");
  if (!b) return { found: false };
  b.scrollIntoView({ block: "center" });
  const r = b.getBoundingClientRect();
  return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: !!b.disabled };
})()`);
emit(`PRESS_HANDOFF ${JSON.stringify(hand)}`);
if (hand.found && !hand.disabled) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: hand.x, y: hand.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: hand.x, y: hand.y, button: "left", clickCount: 1 });
  await sleep(3000);
}
emit(`AFTER_HANDOFF ${JSON.stringify(await state())}`);
emit(`SHOT_HANDOFF ${JSON.stringify(await shot("replan-handoff-390-diff.png"))}`);
console.log(log.join("\n"));
