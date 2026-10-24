/** Read-only: is the backend alive, and does the tab still hold a bearer the server accepts? */
import fs from "node:fs";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(DIR + "/_session_probe_r1.txt", log.join("\n") + "\n"); };
let healthy = "unknown";
try {
  const r = await fetch("http://127.0.0.1:60361/health");
  healthy = `${r.status} ${(await r.text()).slice(0, 120)}`;
} catch (e) { healthy = "unreachable " + String(e).slice(0, 80); }
emit(`HEALTH ${healthy}`);
const list = await (await fetch("http://127.0.0.1:9335/json/list")).json();
const pages = list.filter((t) => t.type === "page" && (t.url || "").includes("14461"));
for (let i = 0; i < pages.length; i += 1) {
  const p = pages[i];
  const ws = new WebSocket(p.webSocketDebuggerUrl);
  const v = await new Promise((resolve) => {
    const t = setTimeout(() => resolve({ error: "timeout" }), 12000);
    ws.onopen = () => ws.send(JSON.stringify({ id: 1, method: "Runtime.evaluate", params: { returnByValue: true, awaitPromise: true, expression: `(async () => {
      const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
      const bearer = sessionStorage.getItem("citynexus.traveler.bearer") || "";
      const stored = localStorage.getItem("citynexus.revolution.firstlook.journey");
      let jid = null;
      try { jid = stored ? JSON.parse(stored).id : null; } catch {}
      const out = { session_keys: Object.keys(sessionStorage), bearer_len: bearer.length, jid };
      if (jid) {
        for (const [label, path] of [["journey", "/api/v1/journeys/" + jid], ["operator", "/api/v1/journeys/" + jid + "/operator"], ["session", "/api/v1/travelers/session"]]) {
          try {
            const r = await fetch(path, { headers: bearer ? { Authorization: "Bearer " + bearer } : {} });
            out[label] = r.status + " " + (await r.text()).slice(0, 120);
          } catch (e) { out[label] = "err " + String(e).slice(0, 60); }
        }
      }
      out.body = flat(document.body.innerText).slice(0, 100);
      return out;
    })()` } }));
    ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id !== 1) return; clearTimeout(t); try { ws.close(); } catch {} resolve(m.result?.result?.value ?? m.error); };
  });
  emit(`PAGE${i} ${JSON.stringify(v)}`);
}
console.log(log.join("\n"));
