/** Probe: after sending, wait for the Agent's choices and read whether the big "start research"
 * control is gone while a question waits. Real pointer clicks; one screenshot. */
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/play-v3-ask-1.txt";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };
const CDP = "http://127.0.0.1:9335";
const WEB = "http://127.0.0.1:14461";
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

async function clickText(label, exact = true) {
  const rect = await evaluate(`(() => {
    const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
    const b = [...document.querySelectorAll("button")].find((x) => ${exact ? `flat(x.innerText) === ${JSON.stringify(label)}` : `/^${label}/.test(flat(x.innerText))`} && !x.disabled && x.getBoundingClientRect().width > 0);
    if (!b) return { found: false };
    b.scrollIntoView({ block: "center" });
    const r = b.getBoundingClientRect();
    return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`);
  if (!rect.found) return rect;
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  return rect;
}

async function typeInto(testid, text) {
  const rect = await evaluate(`(() => {
    const el = document.querySelector("[data-testid='${testid}']");
    if (!el) return { found: false };
    el.scrollIntoView({ block: "center" });
    const r = el.getBoundingClientRect();
    return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`);
  if (!rect.found) return rect;
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  await send("Input.insertText", { text });
  return { typed: text.length };
}

const created = await (await fetch(CDP + "/json/new?" + encodeURIComponent(WEB + "/revolution"), { method: "PUT" })).json();
wsUrl = created.webSocketDebuggerUrl;
emit(`OPEN ${new Date().toISOString()} ${created.id}`);
await sleep(3000);
await evaluate("sessionStorage.clear(); localStorage.clear(); localStorage.setItem('citynexus.locale','zh-CN'); location.reload(); 'ok'");
await sleep(6000);
for (let i = 0; i < 20; i += 1) {
  if ((await evaluate("!!document.querySelector(\"[data-testid='rev-firstlook-city']\")")) === true) break;
  await sleep(1000);
}
emit(`CITY ${JSON.stringify(await typeInto("rev-firstlook-city", "北京"))}`);
emit(`GOAL ${JSON.stringify(await typeInto("rev-trip-goal", "12 月 3 日到 12 月 4 日在北京玩两天，两个人，每段步行不超过 1 公里，远的请改坐地铁。"))}`);
await sleep(500);
emit(`START ${JSON.stringify(await clickText("继续规划 →"))}`);
await sleep(4000);
const boxes = await evaluate("[...document.querySelectorAll(\"input[type='checkbox']\")].length");
emit(`BOXES ${JSON.stringify(boxes)}`);
for (let i = 0; i < 2; i += 1) {
  await evaluate(`(() => { const b = [...document.querySelectorAll("input[type='checkbox']")][${i}]; if (b && !b.checked) b.click(); return b ? b.checked : null; })()`);
  await sleep(300);
}
emit(`SEND ${JSON.stringify(await clickText("发送 ↑"))}`);

let found = false;
let last = null;
for (let i = 0; i < 25; i += 1) {
  last = await evaluate(`(() => {
    const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
    const region = document.querySelector("[aria-label='Agent 请你选择']");
    const research = [...document.querySelectorAll("button")].filter((b) => flat(b.innerText) === "按讨论的方向开始研究");
    return { at: ${Date.now()}, has_region: !!region,
      region_text: region ? flat(region.innerText).slice(0, 300) : "",
      region_buttons: region ? [...region.querySelectorAll("button")].map((b) => flat(b.innerText).slice(0, 80)) : [],
      research_buttons: research.length,
      status_text: flat(document.body.innerText).slice(-260) };
  })()`);
  emit(`POLL${i} ${JSON.stringify(last)}`);
  if (last && last.has_region) { found = true; break; }
  await sleep(6000);
}
emit(`FOUND ${found}`);
emit(`SHOT ${JSON.stringify(await shot("play-v3-ask-1.png"))}`);
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));
