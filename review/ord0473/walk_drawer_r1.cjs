/* ORD-0473 drawer walk -- one script, one JSON per arm, used for both the before and the after
   generation.  Every judgement is a *rendered* reading: document.elementFromPoint on the control's
   own centre (a row is "reachable" only if the point hits that row), and the screen text the click
   leaves behind (h1 / breadcrumb innerText, never a data attribute). */
const { chromium } = require("D:\\moodle\\CityNexus\\frontend\\node_modules\\playwright");
const fs = require("fs");

const BASE = process.argv[2];
const OUT = process.argv[3];
const W = Number(process.argv[4] || 390);
const H = Number(process.argv[5] || 844);

const SNAP = () => {
  const vis = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== "none" && s.visibility !== "hidden";
  };
  const q = (sel) => Array.from(document.querySelectorAll(sel));
  const centreHit = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return { box: null, hit: null };
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const top = document.elementFromPoint(cx, cy);
    return {
      box: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
      point: [Math.round(cx), Math.round(cy)],
      hit_tag: top ? top.tagName : null,
      hit_cls: top ? String(top.className).slice(0, 60) : null,
      hit_id: top ? top.id || null : null,
      self: top === el || (top !== null && el.contains(top)),
    };
  };
  const menu = document.querySelector(".v8-mobile-menu");
  const drawer = document.querySelector("#v8-nav-drawer");
  const closeBtn = drawer ? drawer.querySelector(".v8-quiet-button") : null;
  const backdrop = document.querySelector(".v8-drawer-backdrop");
  return {
    path: location.pathname,
    wizard: !!document.querySelector('[data-testid="trial-setup"]'),
    menu_present: !!menu,
    menu_rendered: menu ? menu.innerText : null,
    menu_expanded: menu ? menu.getAttribute("aria-expanded") : null,
    menu_hit: menu ? centreHit(menu) : null,
    drawer_open: !!drawer,
    drawer_hit: drawer ? centreHit(drawer) : null,
    drawer_rows: drawer
      ? Array.from(drawer.querySelectorAll("button:not(.v8-quiet-button)")).map((b) => b.innerText.replace(/\s+/g, " ").trim())
      : [],
    drawer_close_label: closeBtn ? closeBtn.innerText : null,
    backdrop_open: !!backdrop,
    headings: q("h1, .v8-page h1, h2").slice(0, 3).map((e) => e.innerText.replace(/\s+/g, " ").trim().slice(0, 60)),
    breadcrumb: (() => { const b = document.querySelector(".v8-breadcrumb strong"); return b ? b.innerText : null; })(),
    testid_visible: q("[data-testid]").filter(vis).length,
    body_text_len: document.body.innerText.length,
  };
};

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 300)));
  const rec = { base: BASE, viewport: [W, H], steps: [], row_walk: [], errors };

  const shot = async (label) => {
    const s = await page.evaluate(SNAP);
    rec.steps.push({ step: label, ...s });
    return s;
  };
  const tap = async (sel, idx) => {
    const l = idx === undefined ? page.locator(sel) : page.locator(sel).nth(idx);
    let err = null;
    try { await l.click({ timeout: 6000 }); } catch (e) { err = String(e).split("\n")[0].slice(0, 200); }
    await page.waitForTimeout(900);
    return err;
  };

  await page.goto(BASE + "/v8/hub", { waitUntil: "load" });
  await page.waitForTimeout(4000);
  const land = await shot("landing");
  if (land.wizard) {
    rec.door_error = await tap('[data-testid="trial-tianjin-demo"]');
    await page.waitForTimeout(3500);
    await shot("after_demo_door");
  }

  await shot("before_first_press");
  rec.e1 = await tap("button.v8-mobile-menu");
  const afterOpen = await shot("after_first_press_open");

  rec.e2 = await tap("button.v8-mobile-menu");
  const afterSecond = await shot("after_second_press");
  rec.toggle_closed_on_second_press = !afterSecond.drawer_open;

  if (!afterSecond.drawer_open && afterOpen.drawer_open) {
    rec.e3 = await tap("button.v8-mobile-menu");
    await shot("reopened_for_row_walk");
  }

  // each drawer row: scroll it into view, hit-test its own centre, click it, read what the screen says
  const nRows = (await page.locator("#v8-nav-drawer button:not(.v8-quiet-button)").count()) || 0;
  for (let i = 0; i < nRows; i++) {
    const sel = "#v8-nav-drawer button:not(.v8-quiet-button)";
    if (!(await page.locator(sel).count())) {
      await page.locator("button.v8-mobile-menu").first().click({ timeout: 6000 }).catch(() => {});
      await page.waitForTimeout(700);
    }
    const row = page.locator(sel).nth(i);
    if (!(await row.count())) { rec.row_walk.push({ i, error: "row vanished" }); continue; }
    await row.scrollIntoViewIfNeeded().catch(() => {});
    const label = (await row.textContent() || "").replace(/\s+/g, " ").trim();
    const pre = await row.evaluate((el) => {
      const r = el.getBoundingClientRect();
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      const top = document.elementFromPoint(cx, cy);
      return {
        box: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
        point: [Math.round(cx), Math.round(cy)],
        hit_is_self: top === el || (top !== null && el.contains(top)),
        hit_cls: top ? String(top.className).slice(0, 50) : null,
        in_viewport: cy >= 0 && cy <= innerHeight,
      };
    });
    const before = await page.evaluate(SNAP);
    const err = await tap(sel, i);
    const after = await page.evaluate(SNAP);
    rec.row_walk.push({
      i, label, ...pre, error: err,
      path_before: before.path, path_after: after.path,
      screen_text_before: before.headings.join(" / "),
      screen_text_after: after.headings.join(" / "),
      breadcrumb_after: after.breadcrumb,
      drawer_after: after.drawer_open,
      screen_changed: after.path !== before.path || after.headings.join("|") !== before.headings.join("|"),
    });
  }

  // close doors that must exist: the drawer's own close button, the backdrop, Escape
  if (!(await page.locator("#v8-nav-drawer").count())) {
    await page.locator("button.v8-mobile-menu").first().click({ timeout: 6000 }).catch(() => {});
    await page.waitForTimeout(700);
  }
  rec.e4 = await tap("#v8-nav-drawer .v8-quiet-button");
  await shot("after_close_button");
  rec.closed_by_close_button = !(await page.evaluate(() => !!document.querySelector("#v8-nav-drawer")));

  rec.e5 = await tap("button.v8-mobile-menu");
  rec.e6 = await tap(".v8-drawer-backdrop");
  await shot("after_backdrop_press");
  rec.closed_by_backdrop = !(await page.evaluate(() => !!document.querySelector("#v8-nav-drawer")));

  rec.e7 = await tap("button.v8-mobile-menu");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(700);
  rec.closed_by_escape = !(await page.evaluate(() => !!document.querySelector("#v8-nav-drawer")));

  fs.writeFileSync(OUT, JSON.stringify(rec, null, 1));
  console.log("WROTE " + OUT + " steps=" + rec.steps.length + " rows=" + rec.row_walk.length);
  await browser.close();
})();
