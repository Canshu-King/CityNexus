/** Fresh ten-step walk on the fixed launcher stack (play, 14461). Steps 1-5 first: read the cold
 * first screen, type one sentence and a city, press the single submit control, tick the two consent
 * rows, press send, and read what the Agent says. Real pointer clicks via Input.dispatchMouseEvent. */
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/play-v3-walk-1.txt";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };
const CDP = "http://127.0.0.1:9335";
const WEB = "http://127.0.0.1:14461";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let wsUrl = null;

async function openSocket() {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => resolve(ws);
    ws.onerror = (e) => reject(e);
  });
}

let nextId = 1;
async function send(method, params, timeoutMs = 20000) {
  const ws = await openSocket();
  const id = nextId++;
  return new Promise((resolve) => {
    const timer = setTimeout(() => { try { ws.close(); } catch {} resolve({ error: "timeout" }); }, timeoutMs);
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id !== id) return;
      clearTimeout(timer);
      try { ws.close(); } catch {}
      resolve(msg.error ? { error: msg.error.message } : (msg.result || {}));
    };
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression, timeoutMs = 15000) {
  const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }, timeoutMs);
  return r.error ? { error: r.error } : (r.result?.value ?? { error: "no value" });
}

async function waitFor(expression, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if ((await evaluate(expression)) === true) return true;
    await sleep(800);
  }
  return false;
}

async function shot(name) {
  const r = await send("Page.captureScreenshot", { format: "png" }, 20000);
  if (!r.data) return { error: r.error || "no data" };
  const path = DIR + "/" + name;
  fs.writeFileSync(path, Buffer.from(r.data, "base64"));
  return { bytes: fs.statSync(path).size };
}

async function clickText(label, exact = true) {
  const rect = await evaluate(`(() => {
    const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
    const b = [...document.querySelectorAll("button")].find((x) => ${exact ? `flat(x.innerText) === ${JSON.stringify(label)}` : `/^${label}/.test(flat(x.innerText))`} && !x.disabled);
    if (!b) return { found: false };
    b.scrollIntoView({ block: "center" });
    const r = b.getBoundingClientRect();
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: b.disabled,
      hit_is_button: hit === b || b.contains(hit) };
  })()`);
  if (!rect.found) return rect;
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  return rect;
}

const created = await (await fetch(CDP + "/json/new?" + encodeURIComponent(WEB + "/revolution"), { method: "PUT" })).json();
wsUrl = created.webSocketDebuggerUrl;
emit(`OPEN ${new Date().toISOString()} ${created.id}`);
await waitFor("document.readyState === 'complete'", 30000);
await evaluate("localStorage.setItem('citynexus.locale','zh-CN'); sessionStorage.clear(); 'ok'");
await evaluate("location.reload(); 'reload'");
await sleep(5000);
await waitFor("document.body && document.body.innerText.length > 100", 40000);
await sleep(1500);

const snap = async (tag) => {
  const s = await evaluate(`(() => {
    const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
    return { tag: ${JSON.stringify(tag)}, href: location.href,
      head: flat(document.body.innerText).slice(0, 500),
      buttons: [...document.querySelectorAll("button")].map((b) => ({ t: flat(b.innerText).slice(0, 30), d: !!b.disabled, id: b.getAttribute("data-testid") })).filter((b) => b.t),
      inputs: [...document.querySelectorAll("input,textarea")].map((i) => ({ id: i.getAttribute("data-testid"), tag: i.tagName, ph: i.placeholder || "" })).slice(0, 10) };
  })()`);
  emit(`${tag} ${JSON.stringify(s)}`);
  return s;
};

await snap("STEP1");
emit(`SHOT1 ${JSON.stringify(await shot("play-v3-01-cold-screen.png"))}`);

const typed = await evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const goal = document.querySelector("[data-testid='rev-trip-goal']");
  const city = document.querySelector("[data-testid='rev-firstlook-city']");
  if (goal) { goal.focus(); goal.value = ""; }
  return { goal: !!goal, city: !!city };
})()`);
emit(`FIELDS ${JSON.stringify(typed)}`);

// Type with real key events so React sees them.
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

if (typed.city) emit(`TYPE_CITY ${JSON.stringify(await typeInto("rev-firstlook-city", "北京"))}`);
if (typed.goal) emit(`TYPE_GOAL ${JSON.stringify(await typeInto("rev-trip-goal", "12 月 3 日到 12 月 4 日在北京玩两天，两个人，每段步行不超过 1 公里，远的请改坐地铁。"))}`);
await sleep(800);
await snap("STEP2");
emit(`SHOT2 ${JSON.stringify(await shot("play-v3-02-one-sentence.png"))}`);

const start = await clickText("继续规划 →", true);
emit(`START ${JSON.stringify(start)}`);
await sleep(4000);
await snap("STEP3");
emit(`SHOT3 ${JSON.stringify(await shot("play-v3-03-dock.png"))}`);

// Tick the two consent rows (the send control stays disabled until they are on).
const consent = await evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const boxes = [...document.querySelectorAll("input[type='checkbox']")].map((b) => {
    const lab = b.closest("label") || document.querySelector("label[for='" + b.id + "']");
    return { checked: b.checked, text: flat(lab ? lab.innerText : "").slice(0, 60) };
  });
  return { count: boxes.length, boxes };
})()`);
emit(`CONSENT_READ ${JSON.stringify(consent)}`);
if (consent.count) {
  for (let i = 0; i < consent.count; i += 1) {
    await evaluate(`(() => {
      const b = [...document.querySelectorAll("input[type='checkbox']")][${i}];
      if (b && !b.checked) b.click();
      return b ? b.checked : null;
    })()`);
    await sleep(300);
  }
}
await sleep(1000);
await snap("STEP4");
emit(`SHOT4 ${JSON.stringify(await shot("play-v3-04-consent.png"))}`);

const sendPress = await clickText("发送 ↑", true);
emit(`SEND ${JSON.stringify(sendPress)}`);
await sleep(20000);
await snap("STEP5");
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));