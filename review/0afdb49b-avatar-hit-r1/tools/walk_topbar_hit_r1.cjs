/* Building walk: the three top-bar controls on a phone -- size, overlap, and whether a tap lands.

Why this probe exists instead of trusting the census: the previous cell found that every screen carries
one control at 28x28 (the avatar, `frontend/src/styles.css:154` fixes width/height in px) while the
factory already declares a 44 floor for buttons at `frontend/src/design-tokens.css:508` -- scoped to
`.v8-page button`, which the top bar is not inside, so the contract silently misses it.  Raising the floor
for the top bar could make two neighbouring controls touch, and an overlapping hit area would trade one
defect (too small to press) for a worse one (presses the wrong thing).  So this probe reads the boxes,
tests pairwise intersection, and presses each control's own centre with elementFromPoint.

argv: node walk_topbar_hit_r1.cjs <base> <out.json> <shot.png>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/tip_walk/frontend/node_modules/playwright");
const fs = require("fs");
const path = require("path");

const BASE_URL = process.argv[2] || "http://127.0.0.1:4894";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/topbar_hit.json";
const SHOT = process.argv[4] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/topbar_hit.png";

const run = { schema: "CNX_BUILDING_TOPBAR_HIT_R1", base: BASE_URL, viewport: { width: 390, height: 844 },
  started: new Date().toString(), controls: [], overlaps: [], taps: [], verdict: null,
  page_errors: [], console_errors: [] };

async function readTopbar(page) {
  return await page.evaluate(() => {
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const ids = ["v8-mobile-menu", "topbar-theme", "topbar-language", "topbar-avatar"];
    const out = [];
    for (const id of ids) {
      const el = document.querySelector("[data-testid='" + id + "']");
      if (!el) continue;
      const b = el.getBoundingClientRect();
      if (b.width <= 0 || b.height <= 0) continue;   // hidden on this shape: not a control a thumb sees
      const s = getComputedStyle(el);
      // The painted box is not the pressable area: a hit-area extension lives in a pseudo-element, which
      // Chrome hit-tests as part of the host.  So sample a grid around the centre and measure the box of
      // points that actually resolve to this control -- that is what a thumb has to aim at.
      const cx = b.left + b.width / 2, cy = b.top + b.height / 2;
      let minx = cx, maxx = cx, miny = cy, maxy = cy, hits = 0;
      for (let dx = -32; dx <= 32; dx += 4) {
        for (let dy = -32; dy <= 32; dy += 4) {
          const top = document.elementFromPoint(cx + dx, cy + dy);
          if (top && (top === el || el.contains(top))) {
            hits++;
            minx = Math.min(minx, cx + dx); maxx = Math.max(maxx, cx + dx);
            miny = Math.min(miny, cy + dy); maxy = Math.max(maxy, cy + dy);
          }
        }
      }
      out.push({ testid: id, words: strip(el.innerText || el.getAttribute("aria-label")).slice(0, 40),
                 w: Math.round(b.width), h: Math.round(b.height),
                 left: Math.round(b.left), right: Math.round(b.right),
                 top: Math.round(b.top), bottom: Math.round(b.bottom),
                 hit_w: Math.round(maxx - minx + 4), hit_h: Math.round(maxy - miny + 4),
                 hit_samples: hits,
                 min_h: s.minHeight, min_w: s.minWidth, height_css: s.height,
                 // if the initials ever stop fitting the disc, this is where it shows: content box vs box
                 scroll_w: el.scrollWidth, scroll_h: el.scrollHeight,
                 radius: s.borderRadius, overflow: s.overflow });
    }
    return { path: location.pathname, controls: out, inner_width: window.innerWidth };
  });
}

function intersect(a, b) {
  const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
  const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
  return (ox > 0 && oy > 0) ? { ox, oy } : null;
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
    isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => run.page_errors.push(String(e).slice(0, 200)));
  page.on("console", (m) => { if (m.type() === "error") run.console_errors.push(m.text().slice(0, 200)); });
  await page.goto(BASE_URL + "/", { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  // the top bar only exists once a journey is open: the first screen is the wizard, which has no shell.
  const anchor = page.locator("[data-testid='trial-tianjin-demo']").first();
  if (await anchor.count()) {
    await anchor.evaluate((el) => el.scrollIntoViewIfNeeded());
    await anchor.click();
    await page.waitForTimeout(1600);
  }
  if (!/hub/.test(await page.evaluate(() => location.pathname))) {
    await page.goto(BASE_URL + "/v8/hub", { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForTimeout(1500);
  }

  const stop = await readTopbar(page);
  run.controls = stop.controls;
  run.inner_width = stop.inner_width;
  for (let i = 0; i < stop.controls.length; i++) {
    for (let j = i + 1; j < stop.controls.length; j++) {
      const hit = intersect(stop.controls[i], stop.controls[j]);
      if (hit) run.overlaps.push({ a: stop.controls[i].testid, b: stop.controls[j].testid,
                                   overlap_x: hit.ox, overlap_y: hit.oy });
    }
  }
  for (const c of stop.controls) {
    const loc = page.locator("[data-testid='" + c.testid + "']").first();
    const landed = await loc.evaluate((el) => {
      const b = el.getBoundingClientRect();
      const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
      return { lands: !!top && (top === el || el.contains(top)),
               hit_testid: top && top.getAttribute ? (top.getAttribute("data-testid") || null) : null };
    });
    run.taps.push({ testid: c.testid, lands: landed.lands, hit_testid: landed.hit_testid });
    if (c.testid === "topbar-language") {
      await loc.click();
      await page.waitForTimeout(900);
      const after = await readTopbar(page);
      const theme = after.controls.find((x) => x.testid === "topbar-theme");
      run.language_switch_reads_theme_word = theme ? theme.words : null;
      await loc.click();
      await page.waitForTimeout(900);
    }
  }
  await page.screenshot({ path: SHOT, clip: { x: 0, y: 0, width: 390, height: 90 } });
  run.shot = SHOT;

  const under = run.controls.filter((c) => c.hit_h < 44 || c.hit_w < 44).map((c) => c.testid);
  const wrongHit = run.taps.filter((t) => !t.lands).map((t) => t.testid);
  const stolen = run.taps.filter((t) => t.hit_testid && t.hit_testid !== t.testid).map((t) => t.testid);
  run.under_floor_by_hit_area = under;
  if (run.controls.length === 0) run.verdict = "NO_TOPBAR_CONTROLS_FOUND";
  else if (wrongHit.length) run.verdict = "CENTRE_HIT_TEST_MISSED";
  else if (stolen.length) run.verdict = "CENTRE_RESOLVES_TO_A_NEIGHBOUR:" + stolen.join(",");
  else if (under.length) run.verdict = "UNDER_FLOOR:" + under.join(",");
  else run.verdict = "ALL_TOPBAR_CONTROLS_MEET_FLOOR_AND_LAND";
  run.finished = new Date().toString();
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  console.log(JSON.stringify({ verdict: run.verdict, path: stop.path, inner_width: run.inner_width,
    controls: run.controls.map((c) => ({ t: c.testid, w: c.w, h: c.h, hit_w: c.hit_w, hit_h: c.hit_h, min_h: c.min_h, scroll: [c.scroll_w, c.scroll_h], radius: c.radius, overflow: c.overflow })),
    overlaps: run.overlaps, taps: run.taps,
    language_switch_reads_theme_word: run.language_switch_reads_theme_word,
    page_errors: run.page_errors.length, console_errors: run.console_errors.length }, null, 1));
  await browser.close();
})();
