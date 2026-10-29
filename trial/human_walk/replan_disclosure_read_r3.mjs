/**
 * Raw CDP read (no Playwright): find pages on 14522, read whether the cap sentence is on screen
 * and inside which <details>. Opens the enclosing details if it is closed (DOM state only).
 */
import fs from "node:fs";

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/replan-disclosure-cap3-1.txt";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };

const list = await (await fetch("http://127.0.0.1:9335/json/list")).json();
const pages = list.filter((t) => t.type === "page" && (t.url || "").includes("14522"));
emit(`START ${new Date().toISOString()} pages=${pages.length}`);

const expr = `(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const leaves = [...document.querySelectorAll("body *")].filter((n) => n.children.length === 0 && /超过你写的/.test(n.textContent || ""));
  const describe = (n) => {
    const r = n.getBoundingClientRect();
    const d = n.closest("details");
    return { text: flat(n.textContent).slice(0, 150), w: Math.round(r.width), h: Math.round(r.height),
      visible: r.width > 0 && r.height > 0, details_open: d ? d.open : null,
      summary: d ? flat(d.querySelector("summary")?.textContent || "").slice(0, 60) : null };
  };
  return { href: location.href, title: document.title,
    caps: leaves.map(describe),
    details: [...document.querySelectorAll("details")].map((d) => ({ open: d.open, summary: flat(d.querySelector("summary")?.textContent || "").slice(0, 60), h: Math.round(d.getBoundingClientRect().height) })),
    buttons: [...document.querySelectorAll("button")].map((b) => flat(b.textContent)).filter(Boolean).slice(0, 25),
    head: flat(document.body.innerText).slice(0, 200) };
})()`;

const openExpr = `(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const n = [...document.querySelectorAll("body *")].find((x) => x.children.length === 0 && /超过你写的/.test(x.textContent || ""));
  const d = n ? n.closest("details") : null;
  if (!d) return { opened: false };
  d.open = true;
  return { opened: true, summary: flat(d.querySelector("summary")?.textContent || "").slice(0, 60) };
})()`;

async function evaluate(wsUrl, expression, timeoutMs = 8000) {
  const ws = new WebSocket(wsUrl);
  const id = Math.floor(Math.random() * 1e6);
  return await new Promise((resolve) => {
    const timer = setTimeout(() => { try { ws.close(); } catch {} resolve({ error: "timeout " + timeoutMs }); }, timeoutMs);
    ws.onopen = () => ws.send(JSON.stringify({ id, method: "Runtime.evaluate", params: { expression, returnByValue: true, awaitPromise: true } }));
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id !== id) return;
      clearTimeout(timer);
      try { ws.close(); } catch {}
      resolve(msg.result?.result?.value ?? { error: msg.error?.message || "no value" });
    };
    ws.onerror = () => { clearTimeout(timer); resolve({ error: "ws error" }); };
  });
}

for (let i = 0; i < pages.length; i += 1) {
  const state = await evaluate(pages[i].webSocketDebuggerUrl, expr);
  emit(`PAGE_${i} ${JSON.stringify(state)}`);
  if (state && Array.isArray(state.caps) && state.caps.some((c) => !c.visible)) {
    const opened = await evaluate(pages[i].webSocketDebuggerUrl, openExpr);
    emit(`PAGE_${i}_OPEN ${JSON.stringify(opened)}`);
    await new Promise((r) => setTimeout(r, 600));
    const after = await evaluate(pages[i].webSocketDebuggerUrl, expr);
    emit(`PAGE_${i}_AFTER ${JSON.stringify(after)}`);
  }
}
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));
