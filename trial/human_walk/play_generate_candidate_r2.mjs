/** Stage 2 (real product click): press 生成正式候选方案 on the live stack, capture the
 * /plans/generate HTTP status, watch the on-screen candidate count, then select a plan,
 * reload and report. Screenshots 390x844 + 430x932 on the same journey. */
import fs from "node:fs";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/candidate-live-2.txt";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(OUT, log.join("\n") + "\n"); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let wsUrl = null; let nextId = 1;
async function send(method, params, timeoutMs = 25000) {
  const ws = new WebSocket(wsUrl); const id = nextId++;
  return new Promise((resolve) => {
    const timer = setTimeout(() => { try { ws.close(); } catch {} resolve({ error: "timeout" }); }, timeoutMs);
    ws.onopen = () => ws.send(JSON.stringify({ id, method, params }));
    ws.onmessage = (event) => { const msg = JSON.parse(event.data); if (msg.id !== id) return; clearTimeout(timer); try { ws.close(); } catch {} resolve(msg.error ? { error: msg.error.message } : (msg.result || {})); };
    ws.onerror = () => { clearTimeout(timer); resolve({ error: "ws error" }); };
  });
}
async function evaluate(expression, timeoutMs = 20000) {
  const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }, timeoutMs);
  return r.error ? { error: r.error } : (r.result?.value ?? { error: "no value" });
}
async function shot(name) {
  const r = await send("Page.captureScreenshot", { format: "png" }, 25000);
  if (!r.data) return { error: r.error || "no data" };
  fs.writeFileSync(DIR + "/" + name, Buffer.from(r.data, "base64"));
  return { bytes: fs.statSync(DIR + "/" + name).size };
}
async function click(testidOrLabel, byTestId) {
  const rect = await evaluate(`(() => {
    const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
    const el = ${byTestId
      ? `document.querySelector("[data-testid='${testidOrLabel}']")`
      : `[...document.querySelectorAll("button")].find((x) => flat(x.innerText) === ${JSON.stringify(testidOrLabel)} && x.getBoundingClientRect().width > 0)`};
    if (!el) return { found: false };
    el.scrollIntoView({ block: "center" });
    const r = el.getBoundingClientRect();
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2, disabled: !!el.disabled, hit_is_self: hit === el || el.contains(hit) };
  })()`);
  if (!rect.found || rect.disabled) return rect;
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  return rect;
}
const state = () => evaluate(`(() => {
  const flat = (v) => String(v ?? "").replace(/\\s+/g, " ").trim();
  const text = flat(document.body.innerText);
  const all = [...text.matchAll(/(\\d+) 份正式候选方案/g)].map((m) => m[1]);
  const selectBtns = [...document.querySelectorAll("button")].filter((b) => flat(b.innerText) === "选用这份方案" && b.getBoundingClientRect().width > 0);
  return { counts: all,
    select: selectBtns.length,
    status: [...document.querySelectorAll("[role='status'],[role='alert']")].map((n) => flat(n.innerText)).filter(Boolean).slice(-3),
    options: [...document.querySelectorAll("[data-testid='rev-plan-option']")].map((n) => flat(n.innerText).slice(0, 50)),
    active: /行程进行中|已出发|旅行进行中/.test(text),
    tail: text.slice(-420) };
})()`);

const pages = (await (await fetch("http://127.0.0.1:9335/json/list")).json()).filter((t) => t.type === "page" && (t.url || "").includes("14461"));
wsUrl = pages[0].webSocketDebuggerUrl;
await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
await sleep(1000);
emit(`TAB ${JSON.stringify(await click("我的旅程", false))}`);
await sleep(2000);
const before = await state();
emit(`BEFORE ${JSON.stringify(before)}`);
emit(`SHOT_BEFORE ${JSON.stringify(await shot("candidate-live2-390-before.png"))}`);
{
  emit(`GENERATE ${JSON.stringify(await click("rev-v3-generate-plans", true))}`);
  let last = null;
  for (let i = 0; i < 20; i += 1) {
    await sleep(3000);
    const s = await state();
    last = s;
    emit(`POLL${i} ${JSON.stringify({ counts: s.counts, select: s.select, status: s.status, options: s.options.length })}`);
    if (s.select > 0 || s.status.some((t) => /已生成|失败|没有|排不下|闭馆/.test(t))) break;
  }
  emit(`AFTER_GENERATE ${JSON.stringify(last)}`);
}
emit(`SHOT_AFTER_GENERATE ${JSON.stringify(await shot("candidate-live2-390-after-generate.png"))}`);
const now = await state();
if (now.select > 0) {
  const rect = await evaluate(`(() => {
    const b = [...document.querySelectorAll("button")].find((x) => String(x.innerText).replace(/\\s+/g, " ").trim() === "选用这份方案" && x.getBoundingClientRect().width > 0);
    if (!b) return { found: false };
    b.scrollIntoView({ block: "center" });
    const r = b.getBoundingClientRect();
    return { found: true, x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`);
  if (rect.found) {
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: rect.x, y: rect.y, button: "left", clickCount: 1 });
  }
  emit(`SELECT ${JSON.stringify(rect)}`);
  await sleep(7000);
  emit(`AFTER_SELECT ${JSON.stringify(await state())}`);
  emit(`SHOT_SELECTED ${JSON.stringify(await shot("candidate-live2-390-selected.png"))}`);
  await evaluate("location.reload(); 'reload'");
  await sleep(9000);
  emit(`AFTER_RELOAD ${JSON.stringify(await state())}`);
  emit(`SHOT_RELOAD ${JSON.stringify(await shot("candidate-live2-390-reload.png"))}`);
}
await send("Emulation.setDeviceMetricsOverride", { width: 430, height: 932, deviceScaleFactor: 1, mobile: true });
await sleep(2500);
emit(`SHOT_430 ${JSON.stringify(await shot("candidate-live2-430.png"))}`);
emit(`END ${new Date().toISOString()}`);
console.log(log.join("\n"));
