/** cap3 walk r3: on the departure card, press 选用这份方案, then read whether the replan control
 * appears; if it does, press it, read the diff, apply it, and read the sentence the screen shows
 * after applying. Every press is one real pointer click on a visible button. */
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/cap3-replan-1.txt";
const SHOT1 = DIR + "/cap3-replan-1-select.png";
const SHOT2 = DIR + "/cap3-replan-1-applied.png";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };
const CDP = "http://127.0.0.1:9335";
const WEB = "http://127.0.0.1:14532";
const TOKENS_FILE = "D:/moodle/_cmdr_v3_port_1022/_cap3_tokens.json";
const JOURNEY = "cb4b3e56-ab40-4408-93b5-3f078222c995";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function evaluate(wsUrl, expression, timeoutMs = 20000) {
  const ws = new WebSocket(wsUrl);
  const id = Math.floor(Math.random() * 1e6);
  return await new Promise((resolve) => {
    const timer = setTimeout(() => { try { ws.close(); } catch {} resolve({ error: "timeout" }); }, timeoutMs);
    ws.onopen = () => ws.send(JSON.stringify({ id, method: "Runtime.evaluate", params: { expression, returnByValue: true, awaitPromise: true } }));
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id !== id) return;
      clearTimeout(timer);
      try { ws.close(); } catch {}
      resolve(msg.error ? { error: msg.error.message } : (msg.result?.result?.value ?? { error: "no value" }));
    };
    ws.onerror = () => { clearTimeout(timer); resolve({ error: "ws error" }); };
  });
}

async function waitFor(wsUrl, expression, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if ((await evaluate(wsUrl, expression)) === true) return true;
    await sleep(800);
  }
  return false;
}

async function shot(wsUrl, path) {
  const ws = new WebSocket(wsUrl);
  const id = Math.floor(Math.random() * 1e6);
  return await new Promise((resolve) => {
    const timer = setTimeout(() => { try { ws.close(); } catch {} resolve({ error: "timeout" }); }, 20000);
    ws.onopen = () => ws.send(JSON.stringify({ id, method: "Page.captureScreenshot", params: { format: "png" } }));
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id !== id) return;
      clearTimeout(timer);
      try { ws.close(); } catch {}
      const data = msg.result?.data;
      if (!data) return resolve({ error: msg.error?.message || "no data" });
      fs.writeFileSync(path, Buffer.from(data, "base64"));
      resolve({ bytes: fs.statSync(path).size });
    };
    ws.onerror = () => { clearTimeout(timer); resolve({ error: "ws error" }); };
  });
}

const snap = (wsUrl, tag) => evaluate(wsUrl, `(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  return { tag: ${JSON.stringify(tag)},
    head: flat(document.body.innerText).slice(-900),
    buttons: [...document.querySelectorAll("button")].map((b) => flat(b.innerText).slice(0, 40)).filter(Boolean),
    messages: [...document.querySelectorAll("[role='status'],[role='alert'],p")].map((n) => flat(n.innerText)).filter((s) => s && s.length < 160).slice(-12) };
})()`);

// Reuse an open 14532 page that is already on the preparation card; otherwise sign in fresh.
const pages = (await (await fetch(CDP + "/json/list")).json()).filter((t) => t.type === "page" && (t.url || "").includes("14532"));
let wsUrl = null;
for (const candidate of pages) {
  const onPrep = await evaluate(candidate.webSocketDebuggerUrl, "document.body.innerText.includes('准备出发 · 正式计划与待办')");
  if (onPrep === true) { wsUrl = candidate.webSocketDebuggerUrl; break; }
}
if (!wsUrl) {
  const tokens = JSON.parse(fs.readFileSync(TOKENS_FILE, "utf8"));
  const token = tokens["ac7c8c87-3f10-49e5-a86e-71728e6afecd"];
  const created = await (await fetch(CDP + "/json/new?" + encodeURIComponent(WEB + "/revolution"), { method: "PUT" })).json();
  wsUrl = created.webSocketDebuggerUrl;
  await waitFor(wsUrl, "document.readyState === 'complete'", 30000);
  await sleep(1000);
  await evaluate(wsUrl, `(() => {
    sessionStorage.setItem("citynexus.traveler.bearer", ${JSON.stringify(token)});
    sessionStorage.setItem("citynexus.traveler.session-id", "ac7c8c87-3f10-49e5-a86e-71728e6afecd");
    localStorage.setItem("citynexus.locale", "zh-CN");
    localStorage.setItem("citynexus.revolution.firstlook.journey", ${JSON.stringify(JSON.stringify({ id: JOURNEY, cityCode: "CN-RV-EEFAC972A958", cityName: "北京", status: "DRAFT" }))});
    location.reload(); return true; })()`);
  await sleep(6000);
  await waitFor(wsUrl, "document.body && document.body.innerText.includes('想去哪儿逛逛')", 45000);
  await sleep(2000);
  await evaluate(wsUrl, `(() => {
    const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
    const b = [...document.querySelectorAll("button")].find((x) => flat(x.innerText) === "准备出发");
    if (b) { b.scrollIntoView({ block: "center" }); b.click(); }
    return !!b; })()`);
  await sleep(4000);
}
emit(`PAGE ${new Date().toISOString()} url=${WEB}`);
emit(`PREP ${JSON.stringify(await snap(wsUrl, "prep"))}`);

const select = await evaluate(wsUrl, `(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const b = [...document.querySelectorAll("button")].find((x) => flat(x.innerText) === "选用这份方案" && !x.disabled);
  if (!b) return { found: false, labels: [...document.querySelectorAll("button")].map((x) => flat(x.innerText)).slice(0, 40) };
  b.scrollIntoView({ block: "center" });
  const box = b.getBoundingClientRect();
  const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
  b.click();
  return { found: true, centre_hit_is_button: hit === b || b.contains(hit) };
})()`);
emit(`SELECT ${JSON.stringify(select)}`);
await sleep(7000);
emit(`AFTER_SELECT ${JSON.stringify(await snap(wsUrl, "after_select"))}`);
emit(`SHOT_SELECT ${JSON.stringify(await shot(wsUrl, SHOT1))}`);

const replan = await evaluate(wsUrl, `(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const b = [...document.querySelectorAll("button")].find((x) => /根据路线重新安排/.test(x.innerText || "") && !x.disabled);
  if (!b) return { found: false };
  b.scrollIntoView({ block: "center" });
  const box = b.getBoundingClientRect();
  const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
  b.click();
  return { found: true, centre_hit_is_button: hit === b || b.contains(hit) };
})()`);
emit(`REPLAN ${JSON.stringify(replan)}`);
if (replan.found) {
  await sleep(9000);
  emit(`AFTER_REPLAN ${JSON.stringify(await snap(wsUrl, "after_replan"))}`);
  const apply = await evaluate(wsUrl, `(() => {
    const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
    const scope = document.querySelector("[data-testid='rev-v3-replan-diff']") || document.body;
    const b = [...scope.querySelectorAll("button")].find((x) => !x.disabled && /按这一版安排/.test(x.innerText || ""));
    if (!b) return { found: false, labels: [...scope.querySelectorAll("button")].map((x) => flat(x.innerText)).slice(0, 20) };
    b.scrollIntoView({ block: "center" });
    const box = b.getBoundingClientRect();
    const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
    b.click();
    return { found: true, centre_hit_is_button: hit === b || b.contains(hit) };
  })()`);
  emit(`APPLY ${JSON.stringify(apply)}`);
  await sleep(12000);
  emit(`AFTER_APPLY ${JSON.stringify(await snap(wsUrl, "after_apply"))}`);
  emit(`SHOT_APPLIED ${JSON.stringify(await shot(wsUrl, SHOT2))}`);
}
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));
