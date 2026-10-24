/** The refusal's own road: press 根据路线重新安排, read the explicit diff, apply it, then
 * re-prepare / re-freeze / re-accept / select again. Real pointer events throughout. */
import fs from "node:fs";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/replan-select-1.txt";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let wsUrl = null; let nextId = 1;
async function send(method, params, timeoutMs = 30000) {
  const ws = new WebSocket(wsUrl); const id = nextId++;
  return new Promise((resolve) => {
    const timer = setTimeout(() => { try { ws.close(); } catch {} resolve({ error: "timeout" }); }, timeoutMs);
    ws.onopen = () => ws.send(JSON.stringify({ id, method, params }));
    ws.onmessage = (event) => { const msg = JSON.parse(event.data); if (msg.id !== id) return; clearTimeout(timer); try { ws.close(); } catch {} resolve(msg.error ? { error: msg.error.message } : (msg.result || {})); };
    ws.onerror = () => { clearTimeout(timer); resolve({ error: "ws error" }); };
  });
}
async function evaluate(expression, timeoutMs = 25000) {
  const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }, timeoutMs);
  return r.error ? { error: r.error } : (r.result?.value ?? { error: "no value" });
}
async function shot(name) {
  const r = await send("Page.captureScreenshot", { format: "png" }, 25000);
  if (!r.data) return { error: r.error || "no data" };
  fs.writeFileSync(DIR + "/" + name, Buffer.from(r.data, "base64"));
  return { bytes: fs.statSync(DIR + "/" + name).size };
}
async function press(expression) {
  const rect = await evaluate(expression);
  if (!rect.found || rect.disabled) return rect;
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  return rect;
}
const pressTid = (tid) => press(`(() => {
  const el = document.querySelector("[data-testid='${tid}']");
  if (!el) return { found: false };
  el.scrollIntoView({ block: "center" });
  const r = el.getBoundingClientRect();
  return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: !!el.disabled };
})()`);
const pressText = (label) => press(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const b = [...document.querySelectorAll("button")].find((x) => flat(x.innerText) === ${JSON.stringify(label)} && x.getBoundingClientRect().width > 0);
  if (!b) return { found: false };
  b.scrollIntoView({ block: "center" });
  const r = b.getBoundingClientRect();
  return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: !!b.disabled };
})()`);
const state = () => evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const tid = (t) => { const n = document.querySelector("[data-testid='" + t + "']"); return n ? { text: flat(n.innerText).slice(0, 300), disabled: !!n.disabled } : null; };
  const btn = (t) => { const b = [...document.querySelectorAll("button")].find((x) => flat(x.innerText) === t && x.getBoundingClientRect().width > 0); return b ? { disabled: !!b.disabled } : null; };
  const cards = [...document.querySelectorAll("[data-testid='rev-plan-option']")].map((n) => ({ head: flat(n.innerText).slice(0, 34), tail: flat(n.innerText).slice(-140), select: !!n.querySelector("[data-testid='rev-plan-select']") }));
  return { replan: tid("rev-v3-replan"), replan_apply: tid("rev-v3-replan-apply"), replan_diff: tid("rev-v3-replan-diff"),
    gaps: tid("rev-v3-travel-gaps"), freeze: tid("rev-v3-freeze-routes"), price: tid("rev-v3-accept-price"),
    save: btn("保存为正式候选方案"), select: tid("rev-plan-select"),
    status: [...document.querySelectorAll("[role='status'],[role='alert']")].map((n) => flat(n.innerText)).filter(Boolean).slice(-3), cards };
})()`);

const pages = (await (await fetch("http://127.0.0.1:9335/json/list")).json()).filter((t) => t.type === "page" && (t.url || "").includes("14461"));
wsUrl = pages[0].webSocketDebuggerUrl;
await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
await sleep(700);
emit(`BEFORE ${JSON.stringify(await state())}`);
emit(`REPLAN ${JSON.stringify(await pressTid("rev-v3-replan"))}`);
await sleep(1200);
emit(`DIFF ${JSON.stringify(await state())}`);
emit(`SHOT_DIFF ${JSON.stringify(await shot("replan-select-390-diff.png"))}`);
emit(`APPLY ${JSON.stringify(await pressTid("rev-v3-replan-apply"))}`);
for (let i = 0; i < 15; i += 1) {
  await sleep(2000);
  const s = await state();
  emit(`APPLY_POLL${i} ${JSON.stringify({ save: s.save, status: s.status })}`);
  if (s.save || s.status.some((t) => /已保存|未|失败|请/.test(t))) break;
}
emit(`AFTER_APPLY ${JSON.stringify(await state())}`);
const tick = await press(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const box = [...document.querySelectorAll("input[type='checkbox']")].find((c) => flat((c.closest("label") || {}).innerText || "").includes("按以上时间准备方案"));
  if (!box) return { found: false };
  const lab = box.closest("label");
  lab.scrollIntoView({ block: "center" });
  const r = lab.getBoundingClientRect();
  return { found: true, x: r.left + Math.min(20, r.width / 2), y: r.top + r.height / 2, checked: box.checked };
})()`);
emit(`TICK ${JSON.stringify(tick)}`);
await sleep(500);
emit(`SAVE ${JSON.stringify(await pressText("保存为正式候选方案"))}`);
for (let i = 0; i < 20; i += 1) {
  await sleep(2000);
  const s = await state();
  emit(`SAVE_POLL${i} ${JSON.stringify({ freeze: s.freeze && s.freeze.text, status: s.status })}`);
  if (s.freeze || s.status.some((t) => /未|失败|请/.test(t))) break;
}
emit(`AFTER_SAVE ${JSON.stringify(await state())}`);
emit(`FREEZE ${JSON.stringify(await pressTid("rev-v3-freeze-routes"))}`);
for (let i = 0; i < 36; i += 1) {
  await sleep(5000);
  const s = await state();
  emit(`FREEZE_POLL${i} ${JSON.stringify({ route: s.freeze && s.freeze.text, price: !!s.price })}`);
  if (s.freeze && s.freeze.text && !/正在核实/.test(s.freeze.text)) break;
}
emit(`AFTER_FREEZE ${JSON.stringify(await state())}`);
const s2 = await state();
if (s2.price) {
  emit(`ACCEPT ${JSON.stringify(await pressTid("rev-v3-accept-price"))}`);
  await sleep(6000);
}
emit(`REFRESH ${JSON.stringify(await pressText("刷新方案"))}`);
await sleep(6000);
emit(`AFTER_REFRESH ${JSON.stringify(await state())}`);
const s3 = await state();
const target = await evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const cards = [...document.querySelectorAll("[data-testid='rev-plan-option']")];
  const last = [...cards].reverse().find((n) => n.querySelector("[data-testid='rev-plan-select']"));
  if (!last) return { found: false, cards: cards.map((n) => flat(n.innerText).slice(0, 40)) };
  const b = last.querySelector("[data-testid='rev-plan-select']");
  b.scrollIntoView({ block: "center" });
  const r = b.getBoundingClientRect();
  return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: !!b.disabled, head: flat(last.innerText).slice(0, 40) };
})()`);
emit(`SELECT_TARGET ${JSON.stringify(target)}`);
if (target.found && !target.disabled) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: target.x, y: target.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: target.x, y: target.y, button: "left", clickCount: 1 });
  await sleep(9000);
  emit(`AFTER_SELECT ${JSON.stringify(await state())}`);
  emit(`SHOT_SELECTED ${JSON.stringify(await shot("replan-select-390-selected.png"))}`);
  await evaluate("location.reload(); 'reload'");
  await sleep(10000);
  emit(`AFTER_RELOAD ${JSON.stringify(await state())}`);
  emit(`SHOT_RELOAD ${JSON.stringify(await shot("replan-select-390-reload.png"))}`);
}
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));
