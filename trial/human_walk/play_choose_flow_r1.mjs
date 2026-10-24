/** Choose from the Agent's options (real pointer), wait for the next turn, and read whether a
 * formal candidate plan appears. Repeats while new questions are asked, at most three rounds. */
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/play-v3-choose-1.txt";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };
const CDP = "http://127.0.0.1:9335";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let wsUrl = null;
let nextId = 1;

async function send(method, params, timeoutMs = 20000) {
  const ws = new WebSocket(wsUrl);
  const id = nextId++;
  return new Promise((resolve) => {
    const timer = setTimeout(() => { try { ws.close(); } catch {} resolve({ error: "timeout" }); }, timeoutMs);
    ws.onopen = () => ws.send(JSON.stringify({ id, method, params }));
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id !== id) return;
      clearTimeout(timer);
      try { ws.close(); } catch {}
      resolve(msg.error ? { error: msg.error.message } : (msg.result || {}));
    };
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
async function clickRegionOption(index) {
  const rect = await evaluate(`(() => {
    const region = document.querySelector("[aria-label='Agent 请你选择']");
    if (!region) return { found: false };
    const b = region.querySelectorAll("button")[${index}];
    if (!b) return { found: false, count: region.querySelectorAll("button").length };
    b.scrollIntoView({ block: "center" });
    const r = b.getBoundingClientRect();
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, hit_is_self: hit === b || b.contains(hit),
      label: (b.innerText || "").slice(0, 40) };
  })()`);
  if (!rect.found) return rect;
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  return rect;
}
const state = () => evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const text = flat(document.body.innerText);
  return { question: !!document.querySelector("[aria-label='Agent 请你选择']"),
    running: /Agent 正在推进|正在研究/.test(text),
    plans: /正式候选方案|份正式候选方案/.test(text),
    select_button: [...document.querySelectorAll("button")].some((b) => flat(b.innerText) === "选用这份方案"),
    head: text.slice(-420) };
})()`);

const pages = (await (await fetch(CDP + "/json/list")).json()).filter((t) => t.type === "page" && (t.url || "").includes("14461"));
for (const p of pages) {
  wsUrl = p.webSocketDebuggerUrl;
  if ((await evaluate("!!document.querySelector(\"[aria-label='Agent 请你选择']\")")) === true) break;
}
emit(`TAB ${new Date().toISOString()}`);
for (let round = 0; round < 3; round += 1) {
  const before = await state();
  emit(`ROUND${round}_BEFORE ${JSON.stringify(before)}`);
  if (before.select_button) break;
  if (before.question) {
    const clicked = await clickRegionOption(0);
    emit(`ROUND${round}_CLICK ${JSON.stringify(clicked)}`);
  } else {
    emit(`ROUND${round}_NO_QUESTION`);
    break;
  }
  for (let i = 0; i < 15; i += 1) {
    await sleep(6000);
    const s = await state();
    if (s.select_button || s.plans || (!s.running && !s.question)) { emit(`ROUND${round}_SETTLED ${JSON.stringify(s)}`); break; }
    if (i === 14) emit(`ROUND${round}_TIMEOUT ${JSON.stringify(s)}`);
  }
  const after = await state();
  emit(`ROUND${round}_AFTER ${JSON.stringify(after)}`);
  if (after.select_button) break;
}
emit(`FINAL ${JSON.stringify(await state())}`);
emit(`SHOT ${JSON.stringify(await shot("play-v3-choose-1.png"))}`);
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));
