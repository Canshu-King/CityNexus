/* ORD-0401 under the REPLACED criterion (CMDR 04:40): the action must sit in the same screen as the
 * empty state it belongs to and must not be covered by any fixed element; reaching it after ONE
 * scroll counts as met, and the scroll itself has to be sayable on screen -- a hint that points at it.
 *
 * The old criterion ("hittable before any scroll") is withdrawn by the same ruling, so this file does
 * not re-price P1..P5; it records, per arm: the empty state's own geometry, the action's centre,
 * document.elementFromPoint before the scroll and after exactly one scroll, who owns the point when it
 * is not the button, and the hint line that is on screen.
 *
 * Empty state needs a journey with nothing outstanding, so it creates one through the product's own
 * POST /api/v1/journeys on this lane's private stack and reads that journey.
 */
import fs from "node:fs";
import { chromium } from "file:///D:/moodle/CityNexus/frontend/node_modules/playwright/index.mjs";

const UI = "http://127.0.0.1:4314";
const API = "http://127.0.0.1:8734";
const OUT = "D:/moodle/_qoder_q_ord0422/ord0401_rescore";
fs.mkdirSync(OUT, { recursive: true });

const j = await (await fetch(API + "/api/v1/travelers", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ display_name: "ORD-0401 rescore traveller", timezone: "Asia/Shanghai" }),
})).json();
const journey = await (await fetch(API + "/api/v1/journeys", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    traveler_id: j.id, title: "ORD-0401 空态一屏", city_code: "CN-350200", timezone: "Asia/Shanghai",
    start_at: "2026-10-20T01:00:00Z", end_at: "2026-10-21T01:00:00Z",
    budget: { amount_minor: 80000, currency: "CNY" },
  }),
})).json();

const PROBE = () => {
  const box = (el) => {
    const r = el.getBoundingClientRect();
    return { top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left),
             w: Math.round(r.width), h: Math.round(r.height) };
  };
  const empty = document.querySelector('[data-testid="pretrip-empty"]');
  const btn = document.querySelector('[data-testid="pretrip-empty-action"]');
  const fixed = [...document.querySelectorAll("*")].filter((e) => {
    const s = getComputedStyle(e);
    return s.position === "fixed" && e.getBoundingClientRect().height > 0
      && e.getBoundingClientRect().top < innerHeight;
  }).map((e) => ({ tag: e.tagName, cls: String(e.className || "").slice(0, 40),
                   top: Math.round(e.getBoundingClientRect().top),
                   bottom: Math.round(e.getBoundingClientRect().bottom) }));
  const leaves = [];
  document.querySelectorAll("body *").forEach((e) => {
    if (e.children.length) return;
    const t = (e.textContent || "").replace(/\s+/g, " ").trim();
    if (!t) return;
    const r = e.getBoundingClientRect();
    if (!(r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight)) return;
    leaves.push(t);
  });
  const centre = btn ? { x: Math.round(btn.getBoundingClientRect().left + btn.getBoundingClientRect().width / 2),
                         y: Math.round(btn.getBoundingClientRect().top + btn.getBoundingClientRect().height / 2) } : null;
  const owner = (e) => (!e ? null : `${e.tagName}${e.id ? "#" + e.id : ""}.${String(e.className || "").slice(0, 36)}`);
  const at = centre ? document.elementFromPoint(centre.x, centre.y) : null;
  return {
    path: location.pathname, scrollTop: Math.round((document.scrollingElement || document.documentElement).scrollTop),
    scrollMax: Math.max(0, (document.scrollingElement || document.documentElement).scrollHeight
      - (document.scrollingElement || document.documentElement).clientHeight),
    viewport: { w: innerWidth, h: innerHeight },
    empty_present: !!empty, empty_box: empty ? box(empty) : null,
    action_present: !!btn, action_label: btn ? btn.textContent.trim() : null,
    action_box: btn ? box(btn) : null, action_centre: centre,
    hit_owner: owner(at), hit_is_action: !!btn && at === btn,
    fixed_on_screen: fixed,
    hint_leaves: leaves.filter((t) => /滚动|下滑|向下|scroll|swipe/i.test(t)),
    scrollable_ancestors: (() => {
      const outList = [];
      let n = btn;
      while (n && n !== document.body) {
        const s = getComputedStyle(n);
        if (n.scrollHeight > n.clientHeight + 8 && ["auto", "scroll"].includes(s.overflowY))
          outList.push({ tag: n.tagName, cls: String(n.className || "").slice(0, 36),
                        max: n.scrollHeight - n.clientHeight });
        n = n.parentElement;
      }
      return outList;
    })(),
  };
};

const browser = await chromium.launch({ channel: "chrome", headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
const page = await ctx.newPage();
const report = { journey: journey.id, traveler: j.id, ui: UI, arms: [] };
for (const locale of ["zh-CN", "en"]) {
  await page.addInitScript(([l, id]) => {
    try {
      localStorage.setItem("citynexus.locale", l);
      localStorage.setItem("citynexus.v8.journey_id", id);
    } catch (e) {}
  }, [locale, journey.id]);
  await page.goto(`${UI}/v8/hub`, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(2600);
  const before = await page.evaluate(PROBE);
  await page.screenshot({ path: `${OUT}/${locale.replace("-", "_")}_before.png` });
  // exactly one scroll: one viewport of the document, which is what a thumb does
  await page.evaluate(() => {
    const el = document.scrollingElement || document.documentElement;
    el.scrollTo({ top: el.scrollTop + el.clientHeight * 0.9, behavior: "instant" });
  });
  await page.waitForTimeout(900);
  const after = await page.evaluate(PROBE);
  await page.screenshot({ path: `${OUT}/${locale.replace("-", "_")}_after_one_scroll.png` });
  report.arms.push({ locale, before, after_one_scroll: after });
}
await ctx.close();
await browser.close();
fs.writeFileSync(`${OUT}/one_scroll_hit_test.json`, JSON.stringify(report, null, 1));
for (const a of report.arms) {
  console.log("%s | empty=%s action=%s label=%s", a.locale, a.before.empty_present,
    a.before.action_present, JSON.stringify(a.before.action_label));
  console.log("   before scroll: top=%s centre=%s hit=%s is_action=%s",
    JSON.stringify(a.before.action_box && a.before.action_box.top),
    JSON.stringify(a.before.action_centre), a.before.hit_owner, a.before.hit_is_action);
  console.log("   after 1 scroll: scrollTop=%s/%s top=%s hit=%s is_action=%s",
    a.after_one_scroll.scrollTop, a.after_one_scroll.scrollMax,
    JSON.stringify(a.after_one_scroll.action_box && a.after_one_scroll.action_box.top),
    a.after_one_scroll.hit_owner, a.after_one_scroll.hit_is_action);
  console.log("   hint on screen: %s", JSON.stringify(a.after_one_scroll.hint_leaves));
  console.log("   scrollable ancestors of the action: %s", JSON.stringify(a.before.scrollable_ancestors));
  console.log("   fixed elements on screen: %s", JSON.stringify(a.before.fixed_on_screen));
}
