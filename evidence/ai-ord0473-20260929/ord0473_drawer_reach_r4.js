// ORD-0473 criterion ②: every drawer entry must be reachable -- scrolled into view, its own
// centre hit-test returns it, and pressing it produces a reaction on screen.
//
// "Reaction" is read three ways so a silent no-op cannot pass: the route changed, the drawer
// closed, or the visible text of the page changed. Each entry is reported with its own box and
// centre coordinates.
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");

const BASE = process.argv[2] || "http://127.0.0.1:4870";
const OUT = process.argv[3] || "D:/moodle/_qoder_ai_ord0387_20260928/ord0473_diag";
const LABEL = process.argv[4] || "tip_ffd84dc";
const ENTRY = ["使用封存的演示行程", "Use the sealed demo journey", "sealed demo", "封存演示"];
const MENU_TEXT = "菜单";

const LIST = () => Array.from(document.querySelectorAll("#v8-nav-drawer button, #v8-nav-drawer a")).map((el, i) => {
  el.scrollIntoView({ block: "center" });
  const r = el.getBoundingClientRect();
  const cx = Math.round(r.left + r.width / 2), cy = Math.round(r.top + r.height / 2);
  const at = document.elementFromPoint(cx, cy);
  return {
    i, text: (el.textContent || "").trim().slice(0, 18),
    box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
    centre: [cx, cy],
    in_viewport: r.top >= 0 && r.bottom <= window.innerHeight && r.width > 0 && r.height > 0,
    hit_is_self: !!(at && (at === el || el.contains(at))),
    hit: at ? at.tagName + "." + String(at.className || "").slice(0, 18) : "none",
  };
});

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
  await page.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
  await page.evaluate(() => localStorage.setItem("citynexus.locale", "zh-CN"));
  await page.goto(BASE + "/v8/hub", { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
  for (const label of ENTRY) {
    const loc = page.getByText(label, { exact: false }).first();
    if (await loc.count()) { await loc.click({ timeout: 8000 }).catch(() => {}); await page.waitForTimeout(2500); break; }
  }
  await page.goto(BASE + "/v8/hub", { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(3000);
  const openMenu = async () => {
    const m = await page.evaluate((txt) => {
      const el = Array.from(document.querySelectorAll("button")).find((e) => (e.textContent || "").trim() === txt);
      if (!el) return null; const r = el.getBoundingClientRect(); return [Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2)];
    }, MENU_TEXT);
    if (!m) return null;
    await page.mouse.click(m[0], m[1]);
    await page.waitForTimeout(900);
    return m;
  };
  const menuCentre = await openMenu();
  const rep = { base: BASE, label: LABEL, menu_centre: menuCentre, served_bundle: await page.evaluate(() => Array.from(document.querySelectorAll("script[src]")).map((s) => s.getAttribute("src")).filter(Boolean)), items: [] };

  const n = (await page.evaluate(LIST)).length;
  for (let idx = 0; idx < n; idx += 1) {
    if (!(await page.evaluate(() => !!document.querySelector("#v8-nav-drawer")))) { await openMenu(); }
    /* r4 fix: the previous version scrolled every item in turn inside LIST and then clicked a
       coordinate captured during that sweep -- by click time the drawer had been scrolled by the
       items after it, so the coordinates were stale and four entries looked dead. Scroll and
       measure exactly one item, then click what was just measured. */
    const before = await page.evaluate(({ sel, idx }) => {
      const all = Array.from(document.querySelectorAll(sel));
      const el = all[idx]; if (!el) return null;
      el.scrollIntoView({ block: "center" });
      const r0 = el.getBoundingClientRect();
      const cx = Math.round(r0.left + r0.width / 2), cy = Math.round(r0.top + r0.height / 2);
      const at = document.elementFromPoint(cx, cy);
      return { i: idx, text: (el.textContent || "").trim().slice(0, 18),
        box: [Math.round(r0.left), Math.round(r0.top), Math.round(r0.width), Math.round(r0.height)],
        centre: [cx, cy],
        in_viewport: r0.top >= 0 && r0.bottom <= window.innerHeight && r0.width > 0 && r0.height > 0,
        hit_is_self: !!(at && (at === el || el.contains(at))),
        hit: at ? at.tagName + "." + String(at.className || "").slice(0, 18) : "none" };
    }, { sel: "#v8-nav-drawer button, #v8-nav-drawer a", idx });
    if (!before) { rep.items.push({ i: idx, text: null, missing: true }); continue; }
    const snap = await page.evaluate(() => ({ path: location.pathname, text: (document.body.innerText || "").length, testids: Array.from(document.querySelectorAll("[data-testid]")).filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; }).length }));
    await page.mouse.click(before.centre[0], before.centre[1]).catch(() => {});
    await page.waitForTimeout(1600);
    const after = await page.evaluate(() => ({ path: location.pathname, text: (document.body.innerText || "").length, testids: Array.from(document.querySelectorAll("[data-testid]")).filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; }).length }));
    const drawerStillOpen = await page.evaluate(() => !!document.querySelector("#v8-nav-drawer"));
    rep.items.push(Object.assign({}, before, {
      before_snap: snap, after_snap: after,
      route_changed: snap.path !== after.path,
      drawer_closed: drawerStillOpen === false,
      text_changed: snap.text !== after.text,
      reacted: snap.path !== after.path || drawerStillOpen === false || snap.text !== after.text,
    }));
  }
  rep.pageerrors = errors;
  await browser.close();
  const file = OUT + "/drawer_reach_" + LABEL + ".json";
  fs.writeFileSync(file, JSON.stringify(rep, null, 1), "utf8");
  console.log("menu_centre", JSON.stringify(menuCentre), "bundle", rep.served_bundle, "items", rep.items.length, "pageerrors", errors.length);
  for (const x of rep.items) {
    console.log(`  "${x.text}" box=${JSON.stringify(x.box)} centre=${JSON.stringify(x.centre)} in_viewport=${x.in_viewport} hit_self=${x.hit_is_self}${x.hit_is_self ? "" : " hit=" + x.hit} reacted=${x.reacted} (route=${x.route_changed} closed=${x.drawer_closed} text=${x.text_changed})`);
  }
  const bad = rep.items.filter((x) => !x.hit_is_self || !x.reacted);
  console.log("FAILING", bad.length, JSON.stringify(bad.map((x) => [x.text, x.hit_is_self, x.reacted])));
  console.log("WROTE", file, fs.statSync(file).size, "B");
})();
