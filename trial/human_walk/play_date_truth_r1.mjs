/** Real-stack check for the single date truth: type a sentence with 12月3日到12月4日, read the
 * form, submit, and read the created Journey's start_at/end_at from the same signed session. */
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/date-truth-live-1.txt";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };
const CDP = "http://127.0.0.1:9335";
const WEB = "http://127.0.0.1:14461";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let wsUrl = null; let nextId = 1;

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
async function clickText(label) {
  const rect = await evaluate(`(() => {
    const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
    const b = [...document.querySelectorAll("button")].find((x) => flat(x.innerText) === ${JSON.stringify(label)} && !x.disabled && x.getBoundingClientRect().width > 0);
    if (!b) return { found: false };
    b.scrollIntoView({ block: "center" });
    const r = b.getBoundingClientRect();
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, hit_is_self: hit === b || b.contains(hit) };
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
await sleep(2500);
await evaluate("sessionStorage.clear(); localStorage.clear(); localStorage.setItem('citynexus.locale','zh-CN'); location.reload(); 'ok'");
await sleep(6000);
for (let i = 0; i < 25; i += 1) {
  if ((await evaluate("!!document.querySelector(\"[data-testid='rev-trip-goal']\")")) === true) break;
  await sleep(1000);
}
const before = await evaluate(`(() => ({
  start: document.querySelector("[data-testid='rev-trip-start-date']")?.value,
  days: document.querySelector("[data-testid='rev-trip-duration']")?.value,
  source: document.querySelector("[data-testid='rev-firstlook-dates-source']")?.textContent?.trim() || null
}))()`);
emit(`BEFORE_TYPE ${JSON.stringify(before)}`);
emit(`TYPE_GOAL ${JSON.stringify(await typeInto("rev-trip-goal", "12 月 3 日到 12 月 4 日在北京玩两天，两个人，每段步行不超过 1 公里，远的请改坐地铁。"))}`);
await sleep(1200);
const after = await evaluate(`(() => ({
  start: document.querySelector("[data-testid='rev-trip-start-date']")?.value,
  days: document.querySelector("[data-testid='rev-trip-duration']")?.value,
  source: document.querySelector("[data-testid='rev-firstlook-dates-source']")?.textContent?.trim() || null,
  city: document.querySelector("[data-testid='rev-firstlook-city']")?.value,
  conflict: !!document.querySelector("[data-testid='rev-firstlook-dates-conflict']")
}))()`);
emit(`AFTER_TYPE ${JSON.stringify(after)}`);
emit(`SHOT_FORM ${JSON.stringify(await shot("date-truth-live-form-390.png"))}`);
emit(`START ${JSON.stringify(await clickText("继续规划 →"))}`);
let pointer = null;
for (let i = 0; i < 20; i += 1) {
  await sleep(1000);
  pointer = await evaluate("(() => { try { return JSON.parse(localStorage.getItem('citynexus.revolution.firstlook.journey') || 'null'); } catch { return null; } })()");
  if (pointer && pointer.id) break;
}
emit(`POINTER ${JSON.stringify({ id: pointer?.id, city: pointer?.cityName, status: pointer?.status })}`);
if (pointer && pointer.id) {
  const read = await evaluate(`(async () => {
    const id = ${JSON.stringify(pointer.id)};
    const res = await fetch('/api/v1/journeys/' + encodeURIComponent(id), { headers: { Authorization: 'Bearer ' + sessionStorage.getItem('citynexus.traveler.bearer') } });
    const body = await res.json();
    return { status: res.status, id: body.id, start_at: body.start_at, end_at: body.end_at, title: body.title,
      intent_goal: body.planning_intent?.goal ?? null };
  })()`, 20000);
  emit(`JOURNEY ${JSON.stringify(read)}`);
}
emit(`SHOT_JOURNEY ${JSON.stringify(await shot("date-truth-live-journey-390.png"))}`);
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));
