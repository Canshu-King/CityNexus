/** End-to-end on the live card after the draft edit: tick 按以上时间准备方案, save the
 * arrangement, freeze transfers, accept the unknown price, refresh plans, press 选用这份方案.
 * Every press is a real pointer event; each step is read back before the next. */
import fs from "node:fs";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/prep-to-select-1.txt";
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
const pressText = (label) => press(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const b = [...document.querySelectorAll("button")].find((x) => flat(x.innerText) === ${JSON.stringify(label)} && x.getBoundingClientRect().width > 0);
  if (!b) return { found: false };
  b.scrollIntoView({ block: "center" });
  const r = b.getBoundingClientRect();
  return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: !!b.disabled };
})()`);
const pressTid = (tid) => press(`(() => {
  const el = document.querySelector("[data-testid='${tid}']");
  if (!el) return { found: false };
  el.scrollIntoView({ block: "center" });
  const r = el.getBoundingClientRect();
  return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: !!el.disabled };
})()`);
const pressCheckbox = () => press(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const box = [...document.querySelectorAll("input[type='checkbox']")].find((c) => flat((c.closest("label") || {}).innerText || "").includes("按以上时间准备方案"));
  if (!box) return { found: false };
  const lab = box.closest("label");
  lab.scrollIntoView({ block: "center" });
  const r = lab.getBoundingClientRect();
  return { found: true, x: r.left + Math.min(20, r.width / 2), y: r.top + r.height / 2, checked: box.checked };
})()`);
const state = () => evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const tid = (t) => { const n = document.querySelector("[data-testid='" + t + "']"); return n ? { text: flat(n.innerText).slice(0, 260), disabled: !!n.disabled } : null; };
  const btn = (t) => { const b = [...document.querySelectorAll("button")].find((x) => flat(x.innerText) === t && x.getBoundingClientRect().width > 0); return b ? { disabled: !!b.disabled } : null; };
  const opt = document.querySelector("[data-testid='rev-plan-option']");
  return { save: btn("保存为正式候选方案"), saved: btn("安排已保存"),
    freeze: tid("rev-v3-freeze-routes"), price: tid("rev-v3-accept-price"),
    refresh: btn("刷新方案"), select: tid("rev-plan-select"),
    generate: tid("rev-v3-generate-plans"),
    option_tail: opt ? flat(opt.innerText).slice(-260) : null,
    status: [...document.querySelectorAll("[role='status'],[role='alert']")].map((n) => flat(n.innerText)).filter(Boolean).slice(-2) };
})()`);

const pages = (await (await fetch("http://127.0.0.1:9335/json/list")).json()).filter((t) => t.type === "page" && (t.url || "").includes("14461"));
wsUrl = pages[0].webSocketDebuggerUrl;
await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
await sleep(600);
emit(`TICK ${JSON.stringify(await pressCheckbox())}`);
await sleep(600);
emit(`SAVE ${JSON.stringify(await pressText("保存为正式候选方案"))}`);
for (let i = 0; i < 20; i += 1) {
  await sleep(2000);
  const s = await state();
  emit(`SAVE_POLL${i} ${JSON.stringify({ saved: s.saved, freeze: s.freeze && s.freeze.text, status: s.status })}`);
  if (s.freeze || (s.status.some((t) => /未|失败|不能|请/.test(t)))) break;
}
emit(`AFTER_SAVE ${JSON.stringify(await state())}`);
emit(`FREEZE ${JSON.stringify(await pressTid("rev-v3-freeze-routes"))}`);
for (let i = 0; i < 36; i += 1) {
  await sleep(5000);
  const s = await state();
  emit(`FREEZE_POLL${i} ${JSON.stringify({ route: s.freeze && s.freeze.text, price: !!s.price, status: s.status })}`);
  if (s.freeze && s.freeze.text && !/正在核实/.test(s.freeze.text)) break;
}
emit(`AFTER_FREEZE ${JSON.stringify(await state())}`);
const s2 = await state();
if (s2.price) {
  emit(`ACCEPT ${JSON.stringify(await pressTid("rev-v3-accept-price"))}`);
  await sleep(6000);
  emit(`AFTER_ACCEPT ${JSON.stringify(await state())}`);
}
emit(`REFRESH ${JSON.stringify(await pressText("刷新方案"))}`);
await sleep(6000);
emit(`AFTER_REFRESH ${JSON.stringify(await state())}`);
const s3 = await state();
if (s3.select && !s3.select.disabled) {
  emit(`SELECT ${JSON.stringify(await pressTid("rev-plan-select"))}`);
  await sleep(9000);
  emit(`AFTER_SELECT ${JSON.stringify(await state())}`);
  emit(`SHOT_SELECTED ${JSON.stringify(await shot("prep-to-select-390-selected.png"))}`);
  await evaluate("location.reload(); 'reload'");
  await sleep(10000);
  emit(`AFTER_RELOAD ${JSON.stringify(await state())}`);
  emit(`SHOT_RELOAD ${JSON.stringify(await shot("prep-to-select-390-reload.png"))}`);
} else {
  emit(`NO_SELECT ${JSON.stringify(s3)}`);
  emit(`SHOT_NO_SELECT ${JSON.stringify(await shot("prep-to-select-390-noselect.png"))}`);
}
await send("Emulation.setDeviceMetricsOverride", { width: 430, height: 932, deviceScaleFactor: 1, mobile: true });
await sleep(2500);
emit(`SHOT_430 ${JSON.stringify(await shot("prep-to-select-430.png"))}`);
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));
