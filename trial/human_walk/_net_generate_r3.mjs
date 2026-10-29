/** Capture the real /plans/generate response produced by the live click (status + body). */
import fs from "node:fs";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/_net_generate_r3.txt";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws; let nextId = 1; const pending = new Map(); const hits = [];
function connect(url) {
  return new Promise((resolve) => {
    ws = new WebSocket(url);
    ws.onopen = () => resolve();
    ws.onmessage = async (event) => {
      const msg = JSON.parse(event.data);
      if (msg.method === "Network.responseReceived") {
        const u = msg.params.response.url || "";
        if (u.includes("/plans/generate")) hits.push({ requestId: msg.params.requestId, status: msg.params.response.status, url: u.slice(0, 160) });
      }
      if (msg.method === "Network.requestWillBeSent") {
        const u = msg.params.request.url || "";
        if (u.includes("/plans/generate")) hits.push({ req: msg.params.request.method, url: u.slice(0, 160), post: (msg.params.request.postData || "").slice(0, 200) });
      }
      if (msg.id && pending.has(msg.id)) { const fn = pending.get(msg.id); pending.delete(msg.id); fn(msg); }
    };
  });
}
function cmd(method, params = {}, timeoutMs = 20000) {
  const id = nextId++;
  return new Promise((resolve) => {
    const t = setTimeout(() => { pending.delete(id); resolve({ error: "timeout" }); }, timeoutMs);
    pending.set(id, (m) => { clearTimeout(t); resolve(m.error ? { error: m.error.message } : (m.result || {})); });
    ws.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression) {
  const r = await cmd("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  return r.error ? { error: r.error } : (r.result?.value ?? null);
}
async function click(testid) {
  const rect = await evaluate(`(() => {
    const el = document.querySelector("[data-testid='${testid}']");
    if (!el) return { found: false };
    el.scrollIntoView({ block: "center" });
    const r = el.getBoundingClientRect();
    return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: !!el.disabled };
  })()`);
  if (!rect.found || rect.disabled) return rect;
  await cmd("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  await cmd("Input.dispatchMouseEvent", { type: "mouseReleased", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  return rect;
}
const pages = (await (await fetch("http://127.0.0.1:9335/json/list")).json()).filter((t) => t.type === "page" && (t.url || "").includes("14461"));
await connect(pages[0].webSocketDebuggerUrl);
await cmd("Network.enable");
await cmd("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
await evaluate(`(() => { const b = [...document.querySelectorAll("button")].find((x) => String(x.innerText).replace(/\\s+/g, " ").trim() === "我的旅程"); if (b) b.click(); return !!b; })()`);
await sleep(2000);
emit(`GENERATE ${JSON.stringify(await click("rev-v3-generate-plans"))}`);
await sleep(12000);
emit(`HITS ${JSON.stringify(hits)}`);
for (const h of hits.filter((x) => x.requestId)) {
  const body = await cmd("Network.getResponseBody", { requestId: h.requestId });
  emit(`BODY ${h.status} ${String(body.body || body.error || "").slice(0, 1500)}`);
}
emit(`STATUS ${JSON.stringify(await evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  return [...document.querySelectorAll("[role='status'],[role='alert']")].map((n) => flat(n.innerText)).filter(Boolean).slice(-3);
})()`))}`);
console.log(log.join("\n"));
process.exit(0);
