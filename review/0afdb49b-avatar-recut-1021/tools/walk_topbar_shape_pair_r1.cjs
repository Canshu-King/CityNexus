/* Building walk: the avatar's painted box and its pressable box, at whatever shape the commander asks for.
 *
 * ORD-0694 forbids the phone rule from reaching above 680 px, and says he will read the control at both
 * shapes himself.  This is the same ruler on both arms so his reading and mine can be compared without
 * arguing about instruments: grid-sample elementFromPoint around the centre, report the外接矩形 of the
 * points that resolve to the control, next to the painted rect.
 * argv: node walk_topbar_shape_pair_r1.cjs <base> <out.json> <width> <height>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/recut_avatar/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4895";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/topbar_shape_phone.json";
const W = Number(process.argv[4] || 390);
const H = Number(process.argv[5] || 844);

async function measure(page) {
  return page.evaluate(() => {
    const el = document.querySelector("[data-testid='topbar-avatar']");
    if (!el) return null;
    el.scrollIntoViewIfNeeded();
    const b = el.getBoundingClientRect();
    const cx = b.left + b.width / 2, cy = b.top + b.height / 2;
    let minx = cx, maxx = cx, miny = cy, maxy = cy, n = 0;
    for (let dx = -32; dx <= 32; dx += 4) for (let dy = -32; dy <= 32; dy += 4) {
      const t = document.elementFromPoint(cx + dx, cy + dy);
      if (t && (t === el || el.contains(t))) { n++;
        minx = Math.min(minx, cx + dx); maxx = Math.max(maxx, cx + dx);
        miny = Math.min(miny, cy + dy); maxy = Math.max(maxy, cy + dy); }
    }
    const cs = getComputedStyle(el);
    const other = ["topbar-theme", "topbar-language", "v8-mobile-menu"].map((id) => {
      const o = document.querySelector("[data-testid='" + id + "']");
      if (!o) return null;
      const r = o.getBoundingClientRect();
      return { id, w: Math.round(r.width), h: Math.round(r.height) };
    }).filter(Boolean);
    return { path: location.pathname, painted: [Math.round(b.width), Math.round(b.height)],
             pressable: [Math.round(maxx - minx + 4), Math.round(maxy - miny + 4)], samples: n,
             overflow: cs.overflow, position: cs.position, before_transform: getComputedStyle(el, "::before").inset,
             others: other, inner_width: window.innerWidth };
  });
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, isMobile: W <= 680,
    hasTouch: W <= 680, serviceWorkers: "block", deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", (e) => errs.push(String(e).slice(0, 160)));
  await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  const a = page.locator("[data-testid='trial-tianjin-demo']").first();
  if (await a.count()) { await a.evaluate(e => e.scrollIntoViewIfNeeded()); await a.click(); }
  await page.waitForTimeout(1600);
  const at = await measure(page);
  const shot = OUT.replace(/\.json$/, ".png");
  await page.screenshot({ path: shot, clip: { x: 0, y: 0, width: W, height: Math.min(H, 100) } });
  const doc = { schema: "CNX_BUILDING_TOPBAR_SHAPE_PAIR_R1", base: BASE, viewport: { width: W, height: H },
    avatar: at, shot, page_errors: errs, started: new Date().toString() };
  fs.mkdirSync(require("path").dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(doc, null, 1));
  console.log(JSON.stringify({ viewport: [W, H], path: at && at.path, painted: at && at.painted,
    pressable: at && at.pressable, position: at && at.position, overflow: at && at.overflow,
    before_inset: at && at.before_transform, others: at && at.others, errors: errs.length }, null, 1));
  await browser.close();
})();
