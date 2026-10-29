/** cap3 walk r2: sign in, open the departure preparation, and read the frozen transit rows and
 * the replan control from the rendered screen. One real click on 准备出发, then read-only DOM. */
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/cap3-prep-1.txt";
const SHOT = DIR + "/cap3-prep-1.png";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };
const CDP = "http://127.0.0.1:9335";
const WEB = "http://127.0.0.1:14532";
const TOKENS_FILE = "D:/moodle/_cmdr_v3_port_1022/_cap3_tokens.json";
const JOURNEY = "cb4b3e56-ab40-4408-93b5-3f078222c995";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function evaluate(wsUrl, expression, timeoutMs = 15000) {
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

const tokens = JSON.parse(fs.readFileSync(TOKENS_FILE, "utf8"));
const token = tokens["ac7c8c87-3f10-49e5-a86e-71728e6afecd"];
const created = await (await fetch(CDP + "/json/new?" + encodeURIComponent(WEB + "/revolution"), { method: "PUT" })).json();
const wsUrl = created.webSocketDebuggerUrl;
emit(`OPEN ${new Date().toISOString()} ${created.id}`);
await waitFor(wsUrl, "document.readyState === 'complete'", 30000);
await sleep(1200);
await evaluate(wsUrl, `(() => {
  sessionStorage.setItem("citynexus.traveler.bearer", ${JSON.stringify(token)});
  sessionStorage.setItem("citynexus.traveler.session-id", "ac7c8c87-3f10-49e5-a86e-71728e6afecd");
  localStorage.setItem("citynexus.locale", "zh-CN");
  localStorage.setItem("citynexus.revolution.firstlook.journey", ${JSON.stringify(JSON.stringify({ id: JOURNEY, cityCode: "CN-RV-EEFAC972A958", cityName: "北京", status: "DRAFT" }))});
  location.reload();
  return true;
})()`);
await sleep(6000);
await waitFor(wsUrl, "document.body && document.body.innerText.includes('想去哪儿逛逛')", 40000);
await sleep(2500);

const snap = (tag) => evaluate(wsUrl, `(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const frozen = [...document.querySelectorAll("[data-testid='rev-amap-research-frozen']")].map((n) => flat(n.innerText).slice(0, 200));
  const caps = [...document.querySelectorAll("body *")].filter((n) => n.children.length === 0 && /超过你写的|少于你写的|步行/.test(n.textContent || "")).map((n) => {
    const d = n.closest("details");
    return { text: flat(n.textContent).slice(0, 200), details_open: d ? d.open : null };
  });
  return { tag: ${JSON.stringify(tag)}, head: flat(document.body.innerText).slice(0, 700), frozen_count: frozen.length, frozen,
    caps, details: [...document.querySelectorAll("details")].map((d) => ({ open: d.open, summary: flat(d.querySelector("summary")?.textContent || "").slice(0, 60) })),
    buttons: [...document.querySelectorAll("button")].map((b) => flat(b.innerText).slice(0, 40)).filter(Boolean) };
})()`);

emit(`BEFORE ${JSON.stringify(await snap("before"))}`);

const pressed = await evaluate(wsUrl, `(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const b = [...document.querySelectorAll("button")].find((x) => flat(x.innerText) === "准备出发");
  if (!b) return { found: false, labels: [...document.querySelectorAll("button")].map((x) => flat(x.innerText)).slice(0, 30) };
  b.scrollIntoView({ block: "center" });
  const box = b.getBoundingClientRect();
  const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
  b.click();
  return { found: true, disabled: b.disabled, centre_hit_is_button: hit === b || b.contains(hit) };
})()`);
emit(`PRESS_PREP ${JSON.stringify(pressed)}`);
await sleep(4000);
await sleep(1500);

emit(`AFTER ${JSON.stringify(await snap("after"))}`);
emit(`SHOT ${JSON.stringify(await shot(wsUrl, SHOT))}`);
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));
