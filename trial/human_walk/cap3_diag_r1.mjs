/** cap3 diag: why did 选用这份方案 answer 422, and what actually sits over its centre? */
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/cap3-diag-1.txt";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };
const CDP = "http://127.0.0.1:9335";

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

const pages = (await (await fetch(CDP + "/json/list")).json()).filter((t) => t.type === "page" && (t.url || "").includes("14532"));
for (const page of pages) {
  const onPrep = await evaluate(page.webSocketDebuggerUrl, "document.body.innerText.includes('准备出发 · 正式计划与待办')");
  if (onPrep !== true) continue;
  const state = await evaluate(page.webSocketDebuggerUrl, `(() => {
    const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
    const alerts = [...document.querySelectorAll("[role='alert'],[role='status']")].map((n) => flat(n.innerText)).filter(Boolean);
    const b = [...document.querySelectorAll("button")].find((x) => flat(x.innerText) === "选用这份方案");
    let probe = null;
    if (b) {
      b.scrollIntoView({ block: "center" });
      const r = b.getBoundingClientRect();
      const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      probe = { rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
        disabled: b.disabled, viewport: { w: innerWidth, h: innerHeight },
        hit: hit ? { tag: hit.tagName, testid: hit.getAttribute && hit.getAttribute("data-testid"), cls: String(hit.className).slice(0, 60), text: flat(hit.innerText).slice(0, 40) } : null,
        hit_is_button: hit === b || b.contains(hit) };
    }
    const tail = flat(document.body.innerText).slice(-600);
    return { href: location.href, alerts, probe, tail, localStorage: Object.keys(localStorage) };
  })()`);
  emit(`DIAG ${page.id} ${JSON.stringify(state)}`);
}
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));
