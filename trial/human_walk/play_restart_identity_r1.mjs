/** Measure the restart question: with KEEP_DB=1 the file survives, but the auth secret is new each
 * boot. Phase "before" records the live tab's bearer + Journey read; phase "after" reloads the same
 * tab on a restarted stack and reads what the traveller sees and what /journeys answers.
 * The bearer is kept only in a temp file for this measurement and deleted at the end.
 */
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const CDP = "http://127.0.0.1:9335";
const TOKEN_FILE = "D:/moodle/_cmdr_v3_port_1022/_restart_bearer.tmp";
const phase = process.argv.includes("--after") ? "after" : "before";
const OUT = DIR + (phase === "after" ? "/restart-identity-after-1.txt" : "/restart-identity-before-1.txt");
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let wsUrl = null; let nextId = 1;
async function send(method, params, timeoutMs = 25000) {
  const ws = new WebSocket(wsUrl); const id = nextId++;
  return new Promise((resolve) => {
    const timer = setTimeout(() => { try { ws.close(); } catch {} resolve({ error: "timeout" }); }, timeoutMs);
    ws.onopen = () => ws.send(JSON.stringify({ id, method, params }));
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id !== id) return;
      clearTimeout(timer); try { ws.close(); } catch {}
      resolve(msg.error ? { error: msg.error.message } : (msg.result || {}));
    };
    ws.onerror = () => { clearTimeout(timer); resolve({ error: "ws error" }); };
  });
}
async function evaluate(expression, timeoutMs = 20000) {
  const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }, timeoutMs);
  return r.error ? { error: r.error } : (r.result?.value ?? { error: "no value" });
}
async function shot(name) {
  const r = await send("Page.captureScreenshot", { format: "png" }, 20000);
  if (!r.data) return { error: r.error || "no data" };
  fs.writeFileSync(DIR + "/" + name, Buffer.from(r.data, "base64"));
  return { bytes: fs.statSync(DIR + "/" + name).size };
}

const pages = (await (await fetch(CDP + "/json/list")).json()).filter((t) => t.type === "page" && (t.url || "").includes("14461"));
let chosen = null;
for (const p of pages) {
  wsUrl = p.webSocketDebuggerUrl;
  const has = await evaluate("!!sessionStorage.getItem('citynexus.traveler.bearer')");
  if (has === true) { chosen = p; break; }
}
emit(`PHASE ${phase} ${new Date().toISOString()} tab=${chosen ? chosen.id : "none"} pages=${pages.length}`);
if (!chosen) process.exit(1);

if (phase === "before") {
  const state = await evaluate(`(() => {
    const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
    let pointer = null;
    try { pointer = JSON.parse(localStorage.getItem('citynexus.revolution.firstlook.journey') || 'null'); } catch {}
    return { bearer: sessionStorage.getItem('citynexus.traveler.bearer') || "",
      traveler: sessionStorage.getItem('citynexus.traveler.session-id') || "",
      pointer, head: flat(document.body.innerText).slice(0, 300) };
  })()`);
  fs.writeFileSync(TOKEN_FILE, JSON.stringify({ bearer: state.bearer, traveler: state.traveler, pointer: state.pointer }));
  emit(`BEFORE_STATE ${JSON.stringify({ traveler: state.traveler, pointer: state.pointer, head: state.head })}`);
  if (state.pointer?.id) {
    const read = await evaluate(`(async () => {
      const res = await fetch('/api/v1/journeys/' + encodeURIComponent(${JSON.stringify(state.pointer.id)}), { headers: { Authorization: 'Bearer ' + sessionStorage.getItem('citynexus.traveler.bearer') } });
      return res.status;
    })()`, 20000);
    emit(`BEFORE_JOURNEY_HTTP ${JSON.stringify(read)}`);
  }
  emit(`END ${new Date().toISOString()}`);
  console.log(log.join("\n"));
  process.exit(0);
}

// after: the page was reloaded against a restarted stack (new TRAVELER_AUTH_SECRET).
const token = fs.existsSync(TOKEN_FILE) ? JSON.parse(fs.readFileSync(TOKEN_FILE, "utf8")) : null;
await evaluate("location.reload(); 'reload'");
await sleep(7000);
const after = await evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  let pointer = null;
  try { pointer = JSON.parse(localStorage.getItem('citynexus.revolution.firstlook.journey') || 'null'); } catch {}
  return { head: flat(document.body.innerText).slice(0, 500),
    expired: /登录已过期|无法读取这份行程|重新进入行程|旧行程无法恢复/.test(document.body.innerText),
    pointer_kept: !!pointer, start_date_on_screen: document.querySelector("[data-testid='rev-trip-start-date']")?.value || null,
    bearer_kept: !!sessionStorage.getItem('citynexus.traveler.bearer') };
})()`, 25000);
emit(`AFTER_STATE ${JSON.stringify(after)}`);
if (token?.pointer?.id) {
  const status = await evaluate(`(async () => {
    const res = await fetch('/api/v1/journeys/' + encodeURIComponent(${JSON.stringify(token.pointer.id)}), { headers: { Authorization: 'Bearer ' + ${JSON.stringify(token.bearer)} } });
    return res.status;
  })()`, 20000);
  emit(`AFTER_JOURNEY_HTTP_OLD_BEARER ${JSON.stringify(status)}`);
}
emit(`SHOT ${JSON.stringify(await shot("restart-identity-after-390.png"))}`);
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));
