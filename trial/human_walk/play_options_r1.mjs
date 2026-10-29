import fs from "node:fs";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/play-v3-options-1.txt";
const list = await (await fetch("http://127.0.0.1:9335/json/list")).json();
const pages = list.filter((t) => t.type === "page" && (t.url || "").includes("14461"));
const out = [];
for (const p of pages) {
  const ws = new WebSocket(p.webSocketDebuggerUrl);
  const id = 11;
  const value = await new Promise((resolve) => {
    const timer = setTimeout(() => resolve({ error: "timeout" }), 15000);
    ws.onopen = () => ws.send(JSON.stringify({ id, method: "Runtime.evaluate", params: { returnByValue: true, awaitPromise: true, expression: `(() => {
      const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
      const vis = [...document.querySelectorAll("button")].filter((b) => { const r = b.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
      return vis.map((b) => { const r = b.getBoundingClientRect(); return { t: flat(b.innerText).slice(0, 70), x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), id: b.getAttribute("data-testid") }; });
    })()` } }));
    ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id !== id) return; clearTimeout(timer); try { ws.close(); } catch {} resolve(m.result?.result?.value ?? { error: m.error?.message }); };
    ws.onerror = () => resolve({ error: "ws" });
  });
  out.push(JSON.stringify({ id: p.id, buttons: value }));
}
fs.writeFileSync(OUT, out.join("\n") + "\n");
console.log(out.join("\n"));
