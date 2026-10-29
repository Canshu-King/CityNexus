/** Ten-step walk, part 3: answer the date clarification like a traveller would, wait for the run,
 * then read map / schedule / departure, press 选用这份方案 if offered, and reload once. */
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/play-v3-walk-5.txt";
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

async function clickByTestId(testid) {
  const rect = await evaluate(`(() => {
    const el = document.querySelector("[data-testid='${testid}']");
    if (!el) return { found: false };
    el.scrollIntoView({ block: "center" });
    const r = el.getBoundingClientRect();
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, hit_is_self: hit === el || el.contains(hit) };
  })()`);
  if (!rect.found) return rect;
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  return rect;
}

async function clickPrefix(prefix) {
  const rect = await evaluate(`(() => {
    const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
    const b = [...document.querySelectorAll("button")].find((x) => flat(x.innerText).startsWith(${JSON.stringify(prefix)}) && !x.disabled && x.getBoundingClientRect().width > 0);
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

const snap = async (tag) => {
  const s = await evaluate(`(() => {
    const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
    return { tag: ${JSON.stringify(tag)}, head: flat(document.body.innerText).slice(0, 900),
      waiting: /等待你的决定/.test(document.body.innerText), researching: /正在研究|正在推进/.test(document.body.innerText),
      buttons: [...document.querySelectorAll("button")].map((b) => flat(b.innerText).slice(0, 44)).filter(Boolean),
      photos: [...document.querySelectorAll("img")].map((i) => (i.alt || "").slice(0, 30)).filter(Boolean).slice(0, 6) };
  })()`);
  emit(`${tag} ${JSON.stringify(s)}`);
  return s;
};

const pages = (await (await fetch(CDP + "/json/list")).json()).filter((t) => t.type === "page" && (t.url || "").includes("14461"));
for (const candidate of pages) {
  wsUrl = candidate.webSocketDebuggerUrl;
  const ok = await evaluate("document.body && document.body.innerText.includes('等待你的决定')");
  if (ok === true) break;
}
emit(`TAB ${new Date().toISOString()}`);
await snap("BEFORE_ANSWER");

await clickByTestId("rev-mission-layer-agent");
await sleep(2000);
emit(`AGENT_LAYER ${JSON.stringify(await evaluate("document.body.innerText.includes('等待你的决定')"))}`);
const answer = await clickPrefix("按讨论的方向开始研究");
emit(`ANSWER ${JSON.stringify(answer)}`);
await sleep(6000);

let settled = false;
for (let i = 0; i < 20; i += 1) {
  const state = await evaluate(`(() => {
    const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
    const text = flat(document.body.innerText);
    const opts = [...document.querySelectorAll("button")].map((b) => flat(b.innerText)).filter((t) => /^(按 |暂用 |两边都)/.test(t));
    return { waiting: /等待你的决定/.test(text), running: /正在研究|正在推进/.test(text), opts: opts.slice(0, 4),
      head: text.slice(0, 260) };
  })()`);
  emit(`POLL${i} ${JSON.stringify(state)}`);
  if (state.waiting && !state.running && i % 3 === 2) {
    await clickByTestId("rev-mission-layer-agent");
    await sleep(1200);
    const clicked = await clickPrefix("按讨论的方向开始研究");
    emit(`NUDGE ${JSON.stringify(clicked)}`);
    await sleep(6000);
    continue;
  }
  if (!state.running && !state.waiting) { settled = true; break; }
  await sleep(9000);
}
emit(`SETTLED ${settled}`);
await sleep(2500);
await snap("AFTER_RESEARCH");
emit(`SHOT6 ${JSON.stringify(await shot("play-v3-06-research-done.png"))}`);

emit(`MAP ${JSON.stringify(await clickByTestId("rev-mission-layer-map"))}`);
await sleep(3500);
await snap("MAP_VIEW");
emit(`SHOT7 ${JSON.stringify(await shot("play-v3-07-map.png"))}`);

emit(`TIMELINE ${JSON.stringify(await clickByTestId("rev-mission-layer-timeline"))}`);
await sleep(2500);
await snap("TIMELINE_VIEW");
emit(`SHOT8 ${JSON.stringify(await shot("play-v3-08-schedule.png"))}`);

emit(`PREP ${JSON.stringify(await clickPrefix("准备出发"))}`);
await sleep(3500);
await snap("PREP_VIEW");
emit(`SHOT9 ${JSON.stringify(await shot("play-v3-09-departure.png"))}`);

const select = await clickPrefix("选用这份方案");
emit(`SELECT ${JSON.stringify(select)}`);
await sleep(6000);
await snap("AFTER_SELECT");
emit(`SHOT9B ${JSON.stringify(await shot("play-v3-09b-selected.png"))}`);

await evaluate("location.reload(); 'reload'");
await sleep(7000);
await snap("AFTER_RELOAD");
emit(`SHOT10 ${JSON.stringify(await shot("play-v3-10-after-reload.png"))}`);
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));
