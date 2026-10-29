import fs from "node:fs";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const lines = [];
const list = await (await fetch("http://127.0.0.1:9335/json/list")).json();
const pages = list.filter((t) => t.type === "page" && (t.url || "").includes("14461"));
for (let i = 0; i < pages.length; i += 1) {
  const p = pages[i]; const ws = new WebSocket(p.webSocketDebuggerUrl);
  const v = await new Promise((resolve) => {
    const t = setTimeout(() => resolve(null), 8000);
    ws.onopen = () => ws.send(JSON.stringify({ id: 1, method: "Runtime.evaluate", params: { returnByValue: true, expression: `(() => {
      const raw = sessionStorage.getItem("citynexus.traveler.bearer") || "";
      const body = raw.split(".")[0] || "";
      if (!body) return null;
      try {
        const b64 = body.replace(/-/g,"+").replace(/_/g,"/");
        const payload = JSON.parse(decodeURIComponent(escape(atob(b64))));
        return { page: ${i}, iat: payload.iat, exp: payload.exp, ttl_s: payload.exp - payload.iat, sub8: String(payload.sub || "").slice(0, 8), body_head: String(document.body.innerText).replace(/\s+/g," ").slice(0, 40) };
      } catch (e) { return { page: ${i}, err: String(e).slice(0, 60) }; }
    })()` } }));
    ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id !== 1) return; clearTimeout(t); try { ws.close(); } catch {} resolve(m.result?.result?.value); };
  });
  if (v) lines.push(JSON.stringify(v));
}
fs.writeFileSync(DIR + "/_ttl_read-1.txt", lines.join("\n") + "\n");
console.log(lines.join("\n"));
