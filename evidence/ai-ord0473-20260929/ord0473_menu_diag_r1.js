// ORD-0473 diagnostic: is the phone "菜单" button dead because the click never reaches it, or
// because reaching it does nothing?
//
// Two independent ways to press it are recorded so the two causes can be told apart without
// guessing: a real mouse press at the element's own centre (what a finger does), and an in-page
// el.click() (what React sees when nothing intercepts). Whichever one opens the drawer names the
// broken layer.
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");

const BASE = process.argv[2] || "http://127.0.0.1:4870";
const OUT = process.argv[3] || "D:/moodle/_qoder_ai_ord0387_20260928/ord0473_diag";
const LABEL = process.argv[4] || "tip_ffd84dc";

const ENTRY = ["使用封存的演示行程", "Use the sealed demo journey", "sealed demo", "封存演示"];

const STATE = () => {
  const ids = Array.from(document.querySelectorAll("[data-testid]"))
    .map((el) => {
      const r = el.getBoundingClientRect();
      return { id: el.getAttribute("data-testid"), vis: r.width > 0 && r.height > 0 };
    })
    .filter((x) => x.vis);
  const menu = Array.from(document.querySelectorAll("button,a,[role=\"button\"]")).find(
    (el) => (el.textContent || "").trim() === "菜单",
  );
  const mb = menu ? menu.getBoundingClientRect() : null;
  const drawer = document.querySelector("#v8-nav-drawer");
  const db = drawer ? drawer.getBoundingClientRect() : null;
  const centre = mb ? [Math.round(mb.left + mb.width / 2), Math.round(mb.top + mb.height / 2)] : null;
  const at = centre ? document.elementFromPoint(centre[0], centre[1]) : null;
  return {
    path: location.pathname,
    menu_found: !!menu,
    menu_class: menu ? String(menu.className) : null,
    menu_tag: menu ? menu.tagName : null,
    menu_disabled_attr: menu ? menu.getAttribute("disabled") : null,
    menu_aria: menu ? { label: menu.getAttribute("aria-label"), expanded: menu.getAttribute("aria-expanded"), controls: menu.getAttribute("aria-controls") } : null,
    menu_box: mb ? { x: Math.round(mb.left), y: Math.round(mb.top), w: Math.round(mb.width), h: Math.round(mb.height) } : null,
    menu_centre: centre,
    hit_at_centre: at ? at.tagName + "." + String(at.className || "").slice(0, 24) : "none",
    hit_is_the_menu: !!(at && menu && (at === menu || menu.contains(at))),
    visible_testids: ids.length,
    visible_testid_ids: ids.map((x) => x.id).sort(),
    drawer_present: !!drawer,
    drawer_box: db ? { x: Math.round(db.left), y: Math.round(db.top), w: Math.round(db.width), h: Math.round(db.height) } : null,
    drawer_backdrop_present: !!document.querySelector(".v8-drawer-backdrop"),
    body_overflow: getComputedStyle(document.body).overflow,
  };
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const rep = { base: BASE, label: LABEL, served_bundle: null, cases: [] };
  for (const vp of [{ width: 390, height: 844 }, { width: 1280, height: 720 }]) {
    const ctx = await browser.newContext({ viewport: vp });
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
    if (!rep.served_bundle) {
      rep.served_bundle = await page.evaluate(() => Array.from(document.querySelectorAll("script[src]")).map((s) => s.getAttribute("src")).filter(Boolean));
    }
    const before = await page.evaluate(STATE);
    // press 1: a real pointer press at the element's own centre
    let mouseOk = true;
    if (before.menu_centre) {
      await page.mouse.click(before.menu_centre[0], before.menu_centre[1]).catch(() => { mouseOk = false; });
    } else mouseOk = false;
    await page.waitForTimeout(1200);
    const afterMouse = await page.evaluate(STATE);
    // press 2: in-page click(), bypassing whatever sits on top
    await page.evaluate(() => {
      const el = Array.from(document.querySelectorAll("button,a,[role=\"button\"]")).find((e) => (e.textContent || "").trim() === "菜单");
      if (el) el.click();
    });
    await page.waitForTimeout(1200);
    const afterDomClick = await page.evaluate(STATE);
    // press 3: if the drawer is open now, can each drawer entry be hit?
    let entries = [];
    if (afterDomClick.drawer_present) {
      entries = await page.evaluate(() => {
        const nav = document.querySelector("#v8-nav-drawer");
        return Array.from(nav.querySelectorAll("button,a")).map((el) => {
          el.scrollIntoView({ block: "center" });
          const r = el.getBoundingClientRect();
          const cx = Math.round(r.left + r.width / 2), cy = Math.round(r.top + r.height / 2);
          const at = document.elementFromPoint(cx, cy);
          return { text: (el.textContent || "").trim().slice(0, 16), box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)], centre: [cx, cy], hit_is_self: !!(at && (at === el || el.contains(at))), in_viewport: r.top >= 0 && r.bottom <= window.innerHeight };
        });
      });
    }
    rep.cases.push({
      viewport: vp,
      real_mouse_press_attempted: mouseOk,
      before,
      after_real_mouse: {
        drawer_present: afterMouse.drawer_present, testids: afterMouse.visible_testids,
        new_ids: afterMouse.visible_testid_ids.filter((x) => !before.visible_testid_ids.includes(x)).slice(0, 12),
        menu_aria_expanded: afterMouse.menu_aria && afterMouse.menu_aria.expanded,
        drawer_box: afterMouse.drawer_box,
      },
      after_dom_click: {
        drawer_present: afterDomClick.drawer_present, testids: afterDomClick.visible_testids,
        new_ids: afterDomClick.visible_testid_ids.filter((x) => !before.visible_testid_ids.includes(x)).slice(0, 12),
        menu_aria_expanded: afterDomClick.menu_aria && afterDomClick.menu_aria.expanded,
        drawer_box: afterDomClick.drawer_box,
        drawer_backdrop_present: afterDomClick.drawer_backdrop_present,
      },
      drawer_entries: entries.slice(0, 40),
      pageerrors: errors,
    });
    await ctx.close();
  }
  await browser.close();
  const file = OUT + "/menu_diag_" + LABEL + ".json";
  fs.writeFileSync(file, JSON.stringify(rep, null, 1), "utf8");
  for (const c of rep.cases) {
    const b = c.before;
    console.log(`viewport=${c.viewport.width}x${c.viewport.height} menu_found=${b.menu_found} class=${b.menu_class} box=${JSON.stringify(b.menu_box)} centre=${JSON.stringify(b.menu_centre)}`);
    console.log(`   hit_at_centre=${b.hit_at_centre} hit_is_the_menu=${b.hit_is_the_menu} testids=${b.visible_testids}`);
    console.log(`   after real mouse: drawer=${c.after_real_mouse.drawer_present} testids=${c.after_real_mouse.testids} new=${c.after_real_mouse.new_ids.length} aria_expanded=${c.after_real_mouse.menu_aria_expanded}`);
    console.log(`   after el.click(): drawer=${c.after_dom_click.drawer_present} testids=${c.after_dom_click.testids} new=${c.after_dom_click.new_ids.length} backdrop=${c.after_dom_click.drawer_backdrop_present} entries=${c.drawer_entries.length}`);
    console.log(`   pageerrors=${c.pageerrors.length}`);
  }
  console.log("WROTE", file, fs.statSync(file).size, "B");
})();
