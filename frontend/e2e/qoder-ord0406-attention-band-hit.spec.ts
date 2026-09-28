/**
 * ORD-0406 -- the fixed bottom bar eats a 76 px band at the foot of the first screen, and the
 * "需要关注" row on Today is sitting inside it. This cell reads geometry on four shapes x two language
 * arms, before any scrolling, and asks one question: can a traveller actually hit that row where it
 * lands, or is it under the nav?
 *
 *   hero    .v8-trip-hero            the first thing on the page; must stay in the first screen
 *   strip   [data-testid=today-strip]
 *   band    [data-testid=today-attention-band]  the row under test
 *   map     .v8-map-panel            must also stay in the first screen
 *   nav     .v8-mobile-nav           the fixed bar; its top edge is the hit line
 *
 * band_hit is deliberately two conditions, not one: the row's box must end above the nav's top edge,
 * AND a hit-test at its centre must come back inside that row. A box that merely clears the bar while
 * something else paints over it would pass the first test and still be unhittable.
 */
import { expect, test, type Browser, type Page } from "@playwright/test";

const SHAPES = [
  [390, 844],
  [360, 800],
  [320, 653],
  [414, 896],
];
const WANTED = {
  hero: ".v8-trip-hero",
  strip: '[data-testid="today-strip"]',
  band: '[data-testid="today-attention-band"]',
  attention: '[data-testid="today-attention"]',
  map: ".v8-map-panel",
  nav: ".v8-mobile-nav",
};

async function openToday(page: Page) {
  await page.goto("/", { waitUntil: "networkidle", timeout: 90000 });
  for (const cand of [page.getByText("使用封存的演示行程", { exact: false }).first(),
                      page.getByText(/sealed demo/i).first()]) {
    if (await cand.count()) {
      await cand.click();
      await page.waitForTimeout(3500);
      break;
    }
  }
  await page.waitForTimeout(800);
}

async function geometry(page: Page) {
  return page.evaluate((sels: Record<string, string>) => {
    const out: Record<string, unknown> = {};
    for (const [k, sel] of Object.entries(sels)) {
      const el = document.querySelector(sel);
      if (!el) {
        out[k] = null;
        continue;
      }
      const r = el.getBoundingClientRect();
      out[k] = { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) };
    }
    const nav = document.querySelector(sels.nav);
    const navH = nav ? nav.getBoundingClientRect().height : 0;
    const shell = document.querySelector(".v8-product-shell");
    const cs = shell ? getComputedStyle(shell) : null;
    const band = document.querySelector(sels.band) as HTMLElement | null;
    let hitInside = false;
    if (band) {
      const r = band.getBoundingClientRect();
      const mid = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
      hitInside = !!(mid && (mid === band || band.contains(mid)));
    }
    const scroller = document.scrollingElement;
    out.hitInside = hitInside;
    out.hitLine = nav ? Math.round(nav.getBoundingClientRect().top) : null;
    out.navHeight = Math.round(navH);
    out.shellPaddingBottom = cs ? cs.paddingBottom : null;
    out.scrollY = scroller ? scroller.scrollTop : (window.scrollY || 0);
    out.docScrollable = (scroller ? scroller.scrollHeight : 0) + "/" + (scroller ? scroller.clientHeight : 0);
    out.innerHeight = window.innerHeight;
    return out;
  }, WANTED);
}

function line(tag: string, locale: string, shape: number[], g: any): string {
  const f = (k: string) => {
    const v = g[k];
    return v ? `[${v.x},${v.y},${v.w},${v.h}]` : "NOT_PRESENT";
  };
  const band = g.band;
  const clear = band && g.hitLine != null ? band.y + band.h <= g.hitLine : false;
  return [
    `O406 ${tag} ${locale} shape=${shape[0]}x${shape[1]}`,
    `viewport_h=${g.innerHeight}`,
    `nav=[${g.nav ? g.nav.x : "?"},${g.nav ? g.nav.y : "?"},${g.nav ? g.nav.w : "?"},${g.nav ? g.nav.h : "?"}]`,
    `nav_height=${g.navHeight}`,
    `hit_line=${g.hitLine}`,
    `hero=${f("hero")}`,
    `strip=${f("strip")}`,
    `band=${f("band")}`,
    `map=${f("map")}`,
    `band_clears_nav=${clear}`,
    `band_hit_test_inside=${g.hitInside}`,
    `band_hit=${clear && g.hitInside}`,
    `shell_padding_bottom=${g.shellPaddingBottom}`,
    `scroll_y=${g.scrollY}`,
    `doc=${g.docScrollable}`,
  ].join(" ");
}

for (const locale of ["zh", "en"]) {
  for (const [w, h] of SHAPES) {
    test(`ORD-0406 ${locale} ${w}x${h} the attention row is hittable before scrolling`, async ({ browser }) => {
      const ctx = await browser.newContext({ viewport: { width: w, height: h }, hasTouch: true, locale });
      const page = await ctx.newPage();
      let g: any = {};
      try {
        await openToday(page);
        g = await geometry(page);
        const band = g.band;
        const clear = !!(band && g.hitLine != null && band.y + band.h <= g.hitLine);
        console.log(line("geometry", locale, [w, h], g));
        expect(g.band, "the attention band has to be on the screen to be hit").not.toBeNull();
        expect(g.nav, "the fixed bottom bar has to exist on a phone shape").not.toBeNull();
        expect(clear,
          `the band ends at ${band ? band.y + band.h : "?"} but the hit line is ${g.hitLine}`).toBe(true);
        expect(g.hitInside,
          "a hit-test at the band's own centre must land back inside the band").toBe(true);
        expect(g.scrollY, "this reading must be taken before any scrolling").toBe(0);
      } finally {
        await ctx.close();
      }
    });
  }
}

test("ORD-0406 the desktop layout keeps all three surfaces on one page", async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, locale: "zh" });
  const page = await ctx.newPage();
  try {
    await openToday(page);
    const g = await geometry(page);
    console.log(line("desktop", "zh", [1280, 800], g) + " nav_present=" + !!g.nav);
    expect(g.band, "the band still renders on a desktop shape").not.toBeNull();
    expect(g.hero, "the hero still renders on a desktop shape").not.toBeNull();
    expect(g.map, "the map still renders on a desktop shape").not.toBeNull();
  } finally {
    await ctx.close();
  }
});

test("ORD-0406 the scroll container pays the bar's own height as bottom padding", async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, locale: "zh" });
  const page = await ctx.newPage();
  try {
    await openToday(page);
    const g = await geometry(page);
    const pad = parseInt(String(g.shellPaddingBottom), 10);
    console.log(`O406 padding zh shape=390x844 nav_height=${g.navHeight} shell_padding_bottom=${g.shellPaddingBottom} pad_equals_nav=${pad === g.navHeight}`);
    expect(pad, "the shell must pay at least the bar's height in bottom padding").toBeGreaterThanOrEqual(g.navHeight);
  } finally {
    await ctx.close();
  }
});
