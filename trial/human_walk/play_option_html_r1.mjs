const list = await (await fetch("http://127.0.0.1:9335/json/list")).json();
const pages = list.filter((t) => t.type === "page" && (t.url || "").includes("14461"));
for (const p of pages) {
  const ws = new WebSocket(p.webSocketDebuggerUrl);
  const id = 21;
  const value = await new Promise((resolve) => {
    const timer = setTimeout(() => resolve({ error: "timeout" }), 15000);
    ws.onopen = () => ws.send(JSON.stringify({ id, method: "Runtime.evaluate", params: { returnByValue: true, awaitPromise: true, expression: `(() => {
      const vis = [...document.querySelectorAll("button")].filter((b) => { const r = b.getBoundingClientRect(); return r.width > 300 && r.height >= 40 && r.height <= 60 && !b.getAttribute("data-testid"); });
      return vis.slice(0, 5).map((b) => ({ text: (b.innerText || "").slice(0, 80), html: b.outerHTML.slice(0, 260), label: b.getAttribute("aria-label"), parent: (b.parentElement ? b.parentElement.className : "") }));
    })()` } }));
    ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id !== id) return; clearTimeout(timer); try { ws.close(); } catch {} resolve(m.result?.result?.value ?? { error: m.error?.message }); };
    ws.onerror = () => resolve({ error: "ws" });
  });
  console.log(JSON.stringify({ id: p.id, value }, null, 1));
}
