/** Raw-CDP scout on the isolated cap3 stack: sign in with a server-minted token, then read the
 * trip screen — frozen transit rows, the cap sentence, and the replan control. No synthetic DOM
 * events: this only sets the same localStorage keys the product itself writes after a sign-in.
 */
import fs from "node:fs";

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/cap3-scout-1.txt";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };
const CDP = "http://127.0.0.1:9335";
const WEB = "http://127.0.0.1:14532";
const TOKENS_FILE = "D:/moodle/_cmdr_v3_port_1022/_cap3_tokens.json";
const JOURNEY = "cb4b3e56-ab40-4408-93b5-3f078222c995";

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function waitFile(path, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (fs.existsSync(path)) return true;
    await sleep(1000);
  }
  return false;
}

async function evaluate(wsUrl, expression, timeoutMs = 12000) {
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
      if (msg.error) resolve({ error: msg.error.message });
      else resolve(msg.result?.result?.value ?? { error: "no value" });
    };
    ws.onerror = () => { clearTimeout(timer); resolve({ error: "ws error" }); };
  });
}

async function waitFor(wsUrl, expression, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const value = await evaluate(wsUrl, expression);
    if (value === true) return true;
    await sleep(1000);
  }
  return false;
}

if (!(await waitFile(TOKENS_FILE, 90000))) { emit("NO_TOKENS_FILE"); process.exit(1); }
const tokens = JSON.parse(fs.readFileSync(TOKENS_FILE, "utf8"));
const traveler = "ac7c8c87-3f10-49e5-a86e-71728e6afecd";
const token = tokens[traveler];
if (!token) { emit("NO_TOKEN_FOR " + traveler); process.exit(1); }

const created = await (await fetch(CDP + "/json/new?" + encodeURIComponent(WEB + "/revolution"), { method: "PUT" })).json();
const wsUrl = created.webSocketDebuggerUrl;
emit(`OPEN ${new Date().toISOString()} target=${created.id} url=${created.url}`);

await waitFor(wsUrl, "document.readyState === 'complete'", 30000);
await sleep(1500);

const seed = {
  bearer: token,
  traveler,
  journey: JSON.stringify({ id: JOURNEY, cityCode: "CN-RV-EEFAC972A958", cityName: "北京", status: "DRAFT" }),
};
const seeded = await evaluate(wsUrl, `(() => {
  localStorage.removeItem("citynexus.traveler.bearer");
  localStorage.removeItem("citynexus.traveler.session-id");
  sessionStorage.setItem("citynexus.traveler.bearer", ${JSON.stringify(seed.bearer)});
  sessionStorage.setItem("citynexus.traveler.session-id", ${JSON.stringify(seed.traveler)});
  localStorage.setItem("citynexus.locale", "zh-CN");
  localStorage.setItem("citynexus.revolution.firstlook.journey", ${JSON.stringify(seed.journey)});
  return { session_keys: Object.keys(sessionStorage), local_keys: Object.keys(localStorage).filter((k) => k.startsWith("citynexus.")) };
})()`);
emit(`SEEDED ${JSON.stringify(seeded)}`);

const reloaded = await evaluate(wsUrl, "location.reload(); 'reloading'");
emit(`RELOAD ${JSON.stringify(reloaded)}`);
await sleep(6000);
await waitFor(wsUrl, "document.body && document.body.innerText.trim().length > 200", 40000);
await sleep(3000);

const snap = (tag) => evaluate(wsUrl, `(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const leaves = [...document.querySelectorAll("body *")].filter((n) => n.children.length === 0);
  const frozen = [...document.querySelectorAll("[data-testid='rev-amap-research-frozen']")].map((n) => flat(n.innerText).slice(0, 180));
  const caps = leaves.filter((n) => /超过你写的|少于你写的|步行上限/.test(n.textContent || "")).map((n) => {
    const d = n.closest("details");
    return { text: flat(n.textContent).slice(0, 180), details_open: d ? d.open : null,
             summary: d ? flat(d.querySelector("summary")?.textContent || "").slice(0, 50) : null };
  });
  const buttons = [...document.querySelectorAll("button")].map((b) => ({ label: flat(b.innerText).slice(0, 36), disabled: !!b.disabled, testid: b.getAttribute("data-testid") })).filter((b) => b.label);
  const details = [...document.querySelectorAll("details")].map((d) => ({ open: d.open, summary: flat(d.querySelector("summary")?.textContent || "").slice(0, 60) }));
  return { ${JSON.stringify(tag)}: true, href: location.href, head: flat(document.body.innerText).slice(0, 500),
    frozen_count: frozen.length, frozen, caps, details, buttons };
})()`);

emit(`SNAP ${JSON.stringify(await snap("snap"))}`);
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));
