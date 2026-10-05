/* ORD-0571: measure `/v8/trips` inline actions against the fixed bottom bar, in a browser this
 * script owns (the shared Playwright tab keeps getting navigated away by another session, which makes
 * a pixel reading unattributable).
 *
 * For every stop row it records the action button's box, whether its centre falls inside the nav band
 * at scroll 0, and - the question the order actually asks - whether the traveller can scroll at all so
 * that the centre clears the band. Read-only: no click, no POST, no storage beyond the two keys the
 * product's own boot reads.
 */
const {chromium} = require('playwright');
const fs = require('fs');

const BASE = process.env.CN_FRONT || 'http://127.0.0.1:14901';
const JOURNEYS = (process.env.CN_JOURNEYS || 'b2734f5c-a88a-49ac-b0bc-684c72fc8ea8').split(',');
const OUT = process.env.CN_OUT || 'D:/moodle/_qoder_seed_ord0489/run/ord0571_geometry.json';

(async () => {
  const browser = await chromium.launch();
  const report = {base: BASE, viewport: {w: 390, h: 844}, journeys: []};
  for (const journey of JOURNEYS) {
    const ctx = await browser.newContext({viewport: {width: 390, height: 844}, serviceWorkers: 'block'});
    const page = await ctx.newPage();
    await page.goto(BASE + '/', {waitUntil: 'networkidle'});
    await page.evaluate(([j]) => {
      localStorage.setItem('citynexus.v8.journey_id', j);
      localStorage.setItem('citynexus.locale', 'zh-CN');
    }, [journey]);
    await page.goto(BASE + '/v8/trips', {waitUntil: 'networkidle'});
    const rows = await page.evaluate(() => {
      const nav = document.querySelector('.v8-mobile-nav');
      if (!nav) return {error: 'no nav', pathname: location.pathname};
      const nr = nav.getBoundingClientRect();
      const navTop = Math.round(nr.top), navBottom = Math.round(nr.bottom);
      const de = document.documentElement;
      const maxScroll = de.scrollHeight - window.innerHeight;
      const acts = [];
      for (const b of document.querySelectorAll('button')) {
        const label = (b.textContent || '').trim();
        if (!/详情|打卡/.test(label)) continue;
        const r = b.getBoundingClientRect();
        if (!r.height) continue;
        const pageCenterY = Math.round(r.y + window.scrollY + r.height / 2);
        const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
        const hit = document.elementFromPoint(cx, cy);
        acts.push({
          label, aria: b.getAttribute('aria-label'),
          box: {x: Math.round(r.x), y: Math.round(r.y + window.scrollY), w: Math.round(r.width), h: Math.round(r.height)},
          centerAtScroll0: Math.round(r.y + r.height / 2),
          insideBandAtScroll0: (r.y + r.height / 2) >= navTop && (r.y + r.height / 2) <= navBottom,
          centerWhenScrolledToBottom: pageCenterY - maxScroll,
          canClearNav: (pageCenterY - maxScroll) < navTop,
          hitTagAtScroll0: hit ? hit.tagName : null,
          hitIsNavAtScroll0: !!(hit && nav.contains(hit)),
        });
      }
      return {
        pathname: location.pathname, innerH: window.innerHeight, docScrollH: de.scrollHeight,
        maxScroll, navBand: [navTop, navBottom],
        shellPadBottom: getComputedStyle(document.querySelector('.v8-product-shell')).paddingBottom,
        actionCount: acts.length, actions: acts,
        allClearable: acts.length > 0 && acts.every(a => a.canClearNav),
      };
    });
    report.journeys.push({journey, ...rows});
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(OUT, JSON.stringify(report, null, 1));
  console.log('wrote', OUT);
  for (const j of report.journeys) {
    console.log(`${j.journey} -> ${j.error || `${j.actionCount} actions, allClearable=${j.allClearable}, nav ${j.navBand}, maxScroll ${j.maxScroll}, padBottom ${j.shellPadBottom}`}`);
  }
})();
