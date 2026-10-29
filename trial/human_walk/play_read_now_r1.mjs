import fs from "node:fs";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/play-v3-now-1.txt";
const list = await (await fetch("http://127.0.0.1:9335/json/list")).json();
const pages = list.filter((t) => t.type === "page" && (t.url || "").includes("14461"));
const out = [];
for (const p of pages) {
  const ws = new WebSocket(p.webSocketDebuggerUrl);
  const id = 7;
  const value = await new Promise((resolve) => {
    const timer = setTimeout(() => resolve({ error: "timeout" }), 15000);
    ws.onopen = () => ws.send(JSON.stringify({ id, method: "Runtime.evaluate", params: { returnByValue: true, awaitPromise: true, expression: `(() => {
      const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
      return { href: location.href, head: flat(document.body.innerText).slice(0, 1200),
        buttons: [...document.querySelectorAll("button")].map((b) => ({ t: flat(b.innerText).slice(0, 40), id: b.getAttribute("data-testid"), d: !!b.disabled })).filter((b) => b.t) };
    })()` } }));
    ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id !== id) return; clearTimeout(timer); try { ws.close(); } catch {} resolve(m.result?.result?.value ?? { error: m.error?.message }); };
    ws.onerror = () => resolve({ error: "ws" });
  });
  out.push(JSON.stringify({ id: p.id, ...value }));
}
fs.writeFileSync(OUT, out.join("\n") + "\n");
console.log(out.join("\n"));
