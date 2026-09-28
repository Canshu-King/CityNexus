/* CMDR ORD-0413 r1 -- how tall the navigation drawer actually is, in which groups, and what each
 * collapse shape would cost, measured rather than estimated.
 *
 * The commander measured 3,668 px of overflow (evidence/cmdr-ord0400-20260928/drawer_scroll_r3.json,
 * blob 972eb7076fb3cc8299835926ddce7b1bc69c6328). This instrument re-derives that number from the same
 * DOM and then answers the part the order asks for: the items are grouped (TODAY / PLAN / TRAVEL /
 * SYSTEM ...), so the question is per-group and per-shape, not one total.
 *
 * Two kinds of numbers, kept apart on purpose:
 *   measured  -- read off the live DOM at scroll_top=0: box, scrollHeight, clientHeight, each child's
 *                advance (next.offsetTop - this.offsetTop, so the CSS gap travels with it), whether
 *                elementFromPoint(centre) lands inside the item, and centre.y <= hit floor.
 *   computed  -- the collapse shapes. There is NO collapse control in the product today, so these are
 *                arithmetic over the measured advances, and every such row says computed_from_measured.
 *                Nothing here pretends to have observed a UI state that cannot be reached.
 *
 * The hit floor is lane N3's frozen 口径: centre[1] <= 768 with a 390x844 viewport
 * (review/n3_0407_baseline_r1.py:20, blob 825e7850043d3393b6fbc3b347b1c15455a73d8f on
 * refs/heads/review/N3-ord0407-empty-state-actions-r1). 768 = 844 - 76, the bottom-nav band ORD-0406.
 *
 * Usage: node cmdr_drawer_grouping_r1.js <base> <out-dir>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = (process.argv[2] || "http://127.0.0.1:50991/").replace(/\/$/, "");
const OUT = process.argv[3] || "D:/moodle/_qoder_q_ord0413_20260928/probe/_grouping_r1/";
const FLOOR = 768;
const VIEWPORTS = [{ w: 390, h: 844 }, { w: 320, h: 844 }];
const LOCALES = ["zh-CN", "en"];

async function readDrawer(page) {
  return page.evaluate((floor) => {
    const d = document.querySelector("#v8-nav-drawer");
    if (!d) return { present: false };
    const cs = getComputedStyle(d);
    const kids = Array.from(d.children).map((el, i) => {
      const next = d.children[i + 1];
      const r = el.getBoundingClientRect();
      const btn = el.matches("button") ? el : el.querySelector("button");
      const heading = el.querySelector(":scope > .v8-nav-group, :scope span.v8-nav-group");
      let hit = null, centre = null;
      if (btn) {
        const br = btn.getBoundingClientRect();
        centre = [Math.round(br.x + br.width / 2), Math.round(br.y + br.height / 2)];
        const top = document.elementFromPoint(centre[0], centre[1]);
        hit = !!(top && (btn.contains(top) || btn === top));
      }
      return {
        i,
        /* The heading span lives INSIDE the first item's wrapper (`<div><span class=v8-nav-group/>
           <button/></div>`), so a group is "the child that carries a heading, plus the children after
           it until the next heading" -- reading the heading per child would split every group in two.
           The head row also holds a button (关闭 / Close), so it is classified before the button test
           or it counts as a navigation item. */
        kind: el.className.includes("drawer-head") ? "head" : (btn ? "item" : "other"),
        opens_group: heading ? (heading.innerText || "").trim() : null,
        /* The heading box is part of the first item's wrapper, so "hide this group's buttons" cannot
           remove the whole advance -- the heading's own height has to stay. Measured, not assumed. */
        heading_h: heading ? Math.round(heading.getBoundingClientRect().height) : 0,
        label: btn ? (btn.innerText || "").trim().replace(/\s+/g, " ") : (el.innerText || "").trim().replace(/\s+/g, " "),
        group: heading ? (heading.innerText || "").trim() : null,
        height: Math.round(r.height),
        advance: next ? Math.round(next.getBoundingClientRect().top - r.top) : Math.round(r.height),
        top_in_drawer: Math.round(r.top - d.getBoundingClientRect().top),
        centre, hittable: hit, above_floor: centre ? centre[1] <= floor : null,
      };
    });
    return {
      present: true, box: [Math.round(d.getBoundingClientRect().x), Math.round(d.getBoundingClientRect().y),
                            Math.round(d.getBoundingClientRect().width), Math.round(d.getBoundingClientRect().height)],
      scroll_height: d.scrollHeight, client_height: d.clientHeight, scroll_top: d.scrollTop,
      overflow_y: cs.overflowY, touch_action: cs.touchAction,
      children: kids,
    };
  }, FLOOR);
}

function shapes(read) {
  const items = read.children.filter((c) => c.kind === "item");
  const groups = [];
  for (const it of items) {
    if (it.opens_group) groups.push({ name: it.opens_group, items: [] });
    if (!groups.length) groups.push({ name: "(no heading above it)", items: [] });
    groups[groups.length - 1].items.push(it);
  }
  /* Collapsing a group hides its buttons and keeps its heading, so what leaves the stack is
     advance - heading_h for each member. The advance already carries the CSS gap, and the heading is
     measured rather than assumed -- nothing here is estimated from a line-height. */
  const hidden = (g) => g.items.reduce((s, it) => s + (it.advance - it.heading_h), 0);
  const out = [];
  for (const g of groups) {
    const removed = hidden(g);
    out.push({ shape: "collapse_" + g.name, removed_px: removed,
               scroll_height: read.scroll_height - removed,
               overflow_px: read.scroll_height - removed - read.client_height,
               items_left: items.length - g.items.length, how: "computed_from_measured" });
  }
  const allButFirst = groups.slice(1).reduce((s, g) => s + hidden(g), 0);
  const allItems = groups.reduce((s, g) => s + hidden(g), 0);
  out.push({ shape: "only_first_group_open", removed_px: allButFirst, scroll_height: read.scroll_height - allButFirst,
             overflow_px: read.scroll_height - allButFirst - read.client_height, items_left: groups[0].items.length,
             how: "computed_from_measured" });
  out.push({ shape: "all_collapsed_headings_only", removed_px: allItems, scroll_height: read.scroll_height - allItems,
             overflow_px: read.scroll_height - allItems - read.client_height, items_left: 0,
             how: "computed_from_measured" });
  return { groups: groups.map((g) => ({ name: g.name, items: g.items.length,
                                         block_px: g.items.reduce((s, it) => s + it.advance, 0),
                                         hidden_if_collapsed_px: hidden(g),
                                         labels: g.items.map((i) => i.label) })), shapes: out };
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const results = [];
  for (const locale of LOCALES) {
    for (const vp of VIEWPORTS) {
      const page = await browser.newPage({ viewport: { width: vp.w, height: vp.h } });
      const errors = [];
      page.on("pageerror", (e) => errors.push(String(e).slice(0, 200)));
      const rec = { arm: `${locale}@${vp.w}x${vp.h}`, viewport: [vp.w, vp.h], hit_floor_px: FLOOR, errors };
      try {
        await page.goto(BASE + "/v8/hub", { waitUntil: "networkidle", timeout: 60000 });
        const seal = page.getByText("使用封存的演示行程", { exact: false }).first();
        if (await seal.count()) { await seal.click(); await page.waitForTimeout(3200); }
        const wantEn = locale === "en";
        /* The toggle names the language it offers, so its own label says which one is on screen:
           "EN" while the UI is Chinese, "中文" while it is English. Read, not assumed. */
        const langBtn = page.locator("[data-testid='topbar-language']").first();
        const offered = (await langBtn.innerText()).trim();
        const currentlyEn = offered !== "EN";
        if (wantEn !== currentlyEn) {
          await langBtn.click();
          await page.waitForTimeout(1200);
        }
        rec.locale_offered_before = offered;
        rec.locale_offered_after = (await langBtn.innerText()).trim();
        /* aria-controls is the same string in both languages; aria-label is translated
           ("shell.openNav" = 打开导航 / Open navigation), so the handle must not be the words. */
        await page.locator("[aria-controls='v8-nav-drawer']").first().click();
        await page.waitForTimeout(900);
        const read = await readDrawer(page);
        rec.reading = read;
        if (read.present) {
          read.overflow_px = read.scroll_height - read.client_height;
          read.drags_to_bottom = Math.ceil(read.overflow_px / read.client_height);
          const sh = shapes(read);
          rec.groups = sh.groups;
          rec.collapse_shapes = sh.shapes;
          rec.items_total = read.children.filter((c) => c.kind === "item").length;
          rec.items_hittable_at_top = read.children.filter((c) => c.kind === "item" && c.hittable && c.above_floor).length;
          rec.items_hittable_ignoring_floor = read.children.filter((c) => c.kind === "item" && c.hittable).length;
        }
        await page.screenshot({ path: `${OUT}${rec.arm.replace(/[^A-Za-z0-9]/g, "_")}.png` });
      } catch (e) {
        rec.fatal = String(e).slice(0, 200);
      }
      results.push(rec);
      await page.close();
    }
  }
  fs.writeFileSync(`${OUT}receipt.json`, JSON.stringify({
    at: new Date().toISOString(), base: BASE, hit_floor_px: FLOOR,
    floor_source: "review/n3_0407_baseline_r1.py:20 blob 825e7850043d3393b6fbc3b347b1c15455a73d8f",
    results }, null, 1), "utf-8");
  for (const r of results) {
    const read = r.reading || {};
    console.log(r.arm, "present=" + read.present, "box=" + JSON.stringify(read.box), "scroll=" + read.scroll_height,
                "client=" + read.client_height, "overflow=" + read.overflow_px, "drags=" + read.drags_to_bottom,
                "items=" + r.items_total, "hittable@floor=" + r.items_hittable_at_top, "err=" + r.errors.length,
                r.fatal ? "FATAL=" + r.fatal.slice(0, 80) : "");
    for (const g of (r.groups || [])) console.log("    group", g.name, "items=" + g.items, "block_px=" + g.block_px, JSON.stringify(g.labels));
    for (const s of (r.collapse_shapes || [])) console.log("   ", s.how, s.shape, "scroll=" + s.scroll_height, "overflow=" + s.overflow_px, "items_left=" + s.items_left);
  }
  await browser.close();
}
main().catch((e) => { console.log("FATAL", String(e).slice(0, 300)); process.exit(9); });
