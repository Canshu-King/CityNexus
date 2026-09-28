/* ORD-0422 -- the final two-arm reading, on the built candidate, with the entry problem fixed.
 *
 * Two things the primary instrument cannot do and this one has to, stated plainly so the artifacts are
 * read correctly:
 *  - its English arm never reached any panel. It finds the sealed-demo entry with
 *    getByText("使用封存的演示行程"), which only exists on a Chinese wizard, so on an English context the
 *    walk stays on the wizard and every `expect` reports NOT_ON_SCREEN for both arms. This file seeds
 *    `citynexus.v8.journey_id` in localStorage instead -- the same state the app itself stores after a
 *    real demo entry -- so both arms really render the panel.
 *  - a controlled <textarea> has no text node, so a leaf walk cannot see the discovery example intent
 *    at all. The value is read from the element here and that hole is named in the delivery.
 *
 * Rows the sealed demo cannot walk are attempted through the product's own doors and, when the server
 * refuses, the refusal is kept as the reason.
 */
import fs from "node:fs";
import { chromium } from "file:///D:/moodle/CityNexus/frontend/node_modules/playwright/index.mjs";
import { execFileSync } from "node:child_process";

const UI = "http://127.0.0.1:4314";
const API = "http://127.0.0.1:8734";
const OUT = "D:/moodle/_qoder_q_ord0422/final3";
fs.mkdirSync(OUT, { recursive: true });
const DEMO = "22222222-2222-4222-8222-222222222222";
const TRAVELER = "11111111-1111-4111-8111-111111111111";

const inv = JSON.parse(execFileSync("git", ["-C", "D:/moodle/CityNexus", "cat-file", "-p",
  "353d1c4f96945de517cacf1ef1c8856345d812f8"], { encoding: "utf-8", maxBuffer: 1 << 24 }));

const api = async (method, path, body, headers = {}) => {
  const r = await fetch(API + path, {
    method, headers: { "Content-Type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const t = await r.text();
  let parsed; try { parsed = JSON.parse(t); } catch { parsed = t.slice(0, 200); }
  return { status: r.status, body: parsed };
};

const COLLECT = () => {
  const seen = new Map();
  const push = () => {
    document.querySelectorAll("body *").forEach((e) => {
      if (e.children.length) return;
      const t = (e.textContent || "").replace(/\s+/g, " ").trim();
      if (!t) return;
      const r = e.getBoundingClientRect();
      if (!(r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight)) return;
      if (!seen.has(t)) seen.set(t, true);
    });
  };
  const scrollers = [document.scrollingElement || document.documentElement];
  document.querySelectorAll("*").forEach((e) => {
    if (e.scrollHeight > e.clientHeight + 8 && e.clientHeight > 120) scrollers.push(e);
  });
  const reached = [];
  scrollers.forEach((el) => {
    const max = Math.max(0, el.scrollHeight - el.clientHeight);
    let deepest = 0;
    for (let y = 0; ; y += Math.max(120, Math.floor(el.clientHeight * 0.5))) {
      el.scrollTop = Math.min(y, max);
      deepest = Math.max(deepest, Math.round(el.scrollTop));
      push();
      if (y >= max) break;
    }
    reached.push({ max, deepest, bottom_reached: deepest >= max - 2 });
    el.scrollTop = 0;
  });
  return {
    path: location.pathname, texts: Array.from(seen.keys()),
    textareas: [...document.querySelectorAll("textarea")].map((e) => e.value),
    inputs: [...document.querySelectorAll("input")].map((e) => e.value).filter(Boolean),
    reached,
  };
};

const browser = await chromium.launch({ channel: "chrome", headless: true });
const report = { ui: UI, api_origin: API, demo_journey: DEMO, api_attempts: [], readings: [] };

/* --- doors the demo does not walk, attempted for real --------------------------------------- */
const caps = await api("POST", `/api/v1/travelers/${TRAVELER}/capabilities/confirm`, [
  { code: "STEP_FREE_REQUIRED", class: "HARD_ACCESSIBILITY_NEED", severity: "HARD", params: {},
    scope: "TRAVELER", source: "USER_CONFIRMED", provenance: "USER_STATED", explicit: true,
    confirmed: true, active: true },
  { code: "QUIET_ENVIRONMENT", class: "SOFT_PREFERENCE", severity: "SOFT", params: {},
    scope: "TRAVELER", source: "USER_STATED", provenance: "USER_STATED", explicit: true,
    confirmed: false, active: true },
]);
const stored = ((await api("GET", `/api/v1/journeys/${DEMO}/experience`)).body.traveler_twin ?? {})
  .explicit_capabilities ?? [];
report.api_attempts.push({
  door: "POST /api/v1/travelers/{id}/capabilities/confirm", status: caps.status,
  severities_sent: ["HARD confirmed=true", "SOFT confirmed=false"],
  confirmed_flags_returned: stored.map((c) => ({ code: c.code, severity: c.severity, confirmed: c.confirmed })),
  conclusion: "both capability doors are /confirm, so no public door leaves a capability unconfirmed -- "
    + "the `Stated; confirmation needed` half of TwinPanel.tsx:14 has no reachable state on this server",
});

const evt = await api("POST", `/api/v1/journeys/${DEMO}/events`, {
  provenance: "SIMULATED", event_type: "TRAFFIC_DELAY", severity: "MAJOR",
  message: "ORD-0422: a simulated delay so the deterministic gate has a trigger.",
  occurred_at: new Date().toISOString(),
});
const rp = await api("POST", `/api/v1/journeys/${DEMO}/replans`,
  { trigger_event_id: evt.body?.id, candidate_count: 1, solver_mode: "deterministic" },
  { "Idempotency-Key": "ord0422-final-" + Date.now() });
report.api_attempts.push({
  door: "POST /api/v1/journeys/{id}/replans", event_status: evt.status, status: rp.status,
  server_answer: rp.status >= 400 ? rp.body : { status: rp.body?.status },
  conclusion: rp.status >= 400
    ? "the deterministic replan refuses with its own named gap, so no PRESENTED proposal can be produced "
      + "for this journey on this data -- the six proposal-gated V14 rows stay NOT_REACHED"
    : "proposal created",
});

/* --- readings ------------------------------------------------------------------------------- */
async function read(label, { route, journey, expect }) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  for (const locale of ["zh-CN", "en"]) {
    await page.addInitScript(([l, id]) => {
      try { localStorage.setItem("citynexus.locale", l); localStorage.setItem("citynexus.v8.journey_id", id); } catch (e) {}
    }, [locale, journey]);
    await page.goto(`${UI}/v8/${route}`, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForTimeout(2600);
    const r = await page.evaluate(COLLECT);
    const leaves = [...r.texts, ...r.textareas, ...r.inputs];
    const all = leaves.join("\n");
    report.readings.push({
      label, route, locale, journey, path: r.path,
      bottom_reached: r.reached.every((x) => x.bottom_reached),
      leaf_count: r.texts.length,
      /* Two matchers, both kept, because they answer different questions:
         `exact` is a rendered leaf equal to the row -- what the English arm has to show for a row to
         count as REACHED, since `V14 · REALITY CHANGED` is not the `CHANGED` badge;
         `substring` is the stricter negative -- a row readable as part of any sentence still counts as
         English leaking onto a Chinese screen. */
      checks: expect.map((e) => ({ text: e, exact: leaves.includes(e), substring: all.includes(e) })),
      leaves,
    });
    await page.screenshot({ path: `${OUT}/${label}_${locale}.png` });
  }
  await ctx.close();
}

const zhPairs = new Map();
{
  const src = fs.readFileSync("D:/moodle/_qoder_q_ord0422/wt/frontend/src/i18n/LocaleContext.tsx", "utf-8");
  const entry = /^ {2}"((?:twin|v14|discovery)\.[A-Za-z0-9_.]+)": "((?:[^"\\]|\\.)*)",$/gm;
  const grab = (name) => {
    const i = src.indexOf(`const ${name}: Dict = {`);
    const out = new Map();
    for (const m of src.slice(i, src.indexOf("\n};", i)).matchAll(entry)) out.set(m[1], m[2].replace(/\\"/g, '"'));
    return out;
  };
  const en = grab("en"), zh = grab("zhCN");
  for (const [k, v] of en) if (zh.has(k)) zhPairs.set(v, zh.get(k));
}

const rowsFor = (file) => inv.rows.filter((r) => r.file.endsWith(file));
const expectFor = (file) => {
  const out = [];
  for (const r of rowsFor(file)) {
    out.push(r.string);
    const pair = zhPairs.get(r.string) || [...zhPairs.keys()].find((k) => r.string.includes(k) && zhPairs.get(k));
    if (pair) out.push(zhPairs.get(r.string));
  }
  return out.filter(Boolean);
};

await read("twin_demo", { route: "twin", journey: DEMO,
  expect: [...expectFor("TwinPanel.tsx"), "已由旅行者确认", "全程免台阶", "安静环境", "Step-free required",
    "Quiet environment", "1 项硬性需求仍按明确声明保留，不会被习得。",
    "1 hard need(s) remain explicit and are never learned."] });
await read("authoritative_demo", { route: "authoritative", journey: DEMO, expect: expectFor("V14RecoveryTruthPanel.tsx") });
await read("discover_demo", { route: "discover", journey: DEMO, expect: expectFor("RealCityDiscoveryPanel.tsx") });

const j2 = await api("POST", "/api/v1/journeys", {
  traveler_id: (await api("POST", "/api/v1/travelers", { display_name: "ORD-0422 plain traveller", timezone: "Asia/Shanghai" })).body.id,
  title: "无偏好行程", city_code: "CN-350200", timezone: "Asia/Shanghai",
  start_at: "2026-10-14T01:00:00Z", end_at: "2026-10-15T01:00:00Z", budget: { amount_minor: 90000, currency: "CNY" },
});
await read("twin_no_preferences", { route: "twin", journey: j2.body?.id,
  expect: ["没有明确偏好", "No explicit preferences"] });

await browser.close();
fs.writeFileSync(`${OUT}/final_readings_r3.json`, JSON.stringify(report, null, 1));

for (const r of report.readings) {
  const yes = r.checks.filter((c) => c.exact).map((c) => c.text);
  console.log(`\n${r.label} [${r.locale}] path=${r.path} bottom=${r.bottom_reached} leaves=${r.leaf_count}`);
  console.log("  ON SCREEN:", JSON.stringify(yes.map((t) => t.slice(0, 46)), null, 0));
  if (r.locale === "zh-CN") {
    const cjk = r.leaves.filter((t) => /[\u4e00-\u9fff]/.test(t));
    console.log("  ZH SENTENCES READ:", JSON.stringify(cjk, null, 0));
  }
}
console.log("\nAPI attempts:");
report.api_attempts.forEach((a) => console.log("  ", JSON.stringify(a).slice(0, 300)));
