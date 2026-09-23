/* ORD-0242 group A, part 2: finish the two faces part 1 did not actually walk.
 *
 * Part 1 reported Wallet as readable but its 预订 tab was found:false once the visibility helper
 * started requiring the control to sit inside the 390px viewport - the tab strip overflows
 * horizontally, so "not there" and "reachable after scrolling" are different claims and only the
 * second one matters for a user. And the 菜单 button's own centre hit-tested to a DIV, so the
 * drawer never opened; that is either an overlay defect or my point being wrong, and it needs the
 * element chain under the finger to say which.
 *
 * Nothing here clicks an invisible control. If a target cannot be brought on-screen and hit-tested
 * to itself, that is recorded as unreachable instead of being worked around.
 */
const PW = process.env.CNX_PW || 'D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright';
const { chromium } = require(PW);
const fs = require('fs');
const path = require('path');

const BASE = 'http://127.0.0.1:4185';
const RUN = process.env.CNX_RUN || 'smkA2b';
const VW = 390, VH = 844;
const JOURNEY = '22222222-2222-4222-8222-222222222222';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = { order: 'ORD-0242', group: 'A2', surface: 'canary @4185/8713', bundle_expected: 'index-CrAwWm5f.js', run_label: RUN, pid: process.pid, started_at: new Date().toISOString() };

const read = () => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && e.offsetParent !== null && r.left >= 0 && r.right <= innerWidth; };
  const txt = s => (s || '').replace(/\s+/g, ' ').trim();
  return { url: location.pathname, h1: (() => { const e = [...document.querySelectorAll('h1')].find(vis); return e ? txt(e.innerText).slice(0, 60) : null; })(),
    h2: [...document.querySelectorAll('h2')].filter(vis).map(e => txt(e.innerText).slice(0, 44)).slice(0, 6),
    body: txt(document.body.innerText).slice(0, 900),
    buttons: [...document.querySelectorAll('button')].filter(vis).map(b => txt(b.innerText).slice(0, 26)).filter(Boolean).slice(0, 30) };
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  let ctx = null;
  const net = [], consoleMsgs = [], pageErrors = [];
  try {
    ctx = await browser.newContext({ viewport: { width: VW, height: VH }, deviceScaleFactor: 3, isMobile: true, hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
    await ctx.addInitScript(([id]) => { try { localStorage.setItem('citynexus.v8.journey_id', id); } catch (e) {} }, [JOURNEY]);
    const page = await ctx.newPage();
    page.on('request', r => { if (r.method() !== 'GET' && r.url().includes('/api/')) net.push('REQ ' + r.method() + ' ' + r.url().replace(BASE, '')); });
    page.on('response', r => { const u = r.url(); if (u.includes('/api/') && r.status() >= 400) net.push('RES ' + r.status() + ' ' + r.request().method() + ' ' + u.replace(BASE, '').split('?')[0]); });
    page.on('console', m => consoleMsgs.push(m.type() + ': ' + String(m.text()).slice(0, 200)));
    page.on('pageerror', e => pageErrors.push(String(e.message).slice(0, 200)));

    await page.goto(BASE + '/v8/trips', { waitUntil: 'load', timeout: 60000 });
    await sleep(9000);

    /* Where is the 预订 tab, and what is its scroll container? */
    out.tabStrip = await page.evaluate(() => {
      const b = [...document.querySelectorAll('button')].find(x => (x.innerText || '').trim() === '预订');
      if (!b) return { present: false, allTabs: [...document.querySelectorAll('button')].map(x => (x.innerText || '').trim().slice(0, 10)).filter(Boolean).slice(0, 20) };
      let sc = null;
      for (let n = b.parentElement; n; n = n.parentElement) {
        const st = getComputedStyle(n);
        if (/(auto|scroll)/.test(st.overflowX) && n.scrollWidth > n.clientWidth + 4) { sc = n; break; }
      }
      const r = b.getBoundingClientRect();
      return { present: true, rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
        insideViewport: r.left >= 0 && r.right <= innerWidth,
        scroller: sc ? { cls: String(sc.className || '').trim().split(/\s+/)[0], scrollWidth: sc.scrollWidth, clientWidth: sc.clientWidth, scrollLeft: sc.scrollLeft } : null,
        offsetParentCls: b.offsetParent ? String(b.offsetParent.className || '').trim().split(/\s+/)[0] : null };
    });

    /* Try to bring it on-screen the way a thumb would: scroll the strip, then hit-test again. */
    out.tabAfterScroll = await page.evaluate(() => {
      const b = [...document.querySelectorAll('button')].find(x => (x.innerText || '').trim() === '预订');
      if (!b) return { present: false };
      for (let n = b.parentElement; n; n = n.parentElement) {
        const st = getComputedStyle(n);
        if (/(auto|scroll)/.test(st.overflowX) && n.scrollWidth > n.clientWidth + 4) { n.scrollLeft = n.scrollWidth; break; }
      }
      b.scrollIntoView({ block: 'nearest', inline: 'center' });
      const r = b.getBoundingClientRect();
      const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
      const hit = document.elementFromPoint(cx, cy);
      const ok = !!(hit && (hit === b || b.contains(hit)));
      return { rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)], point: [cx, cy], insideViewport: r.left >= 0 && r.right <= innerWidth, hitTag: hit && hit.tagName, hitCls: hit && String(hit.className || '').trim().split(/\s+/)[0], pointHitsThisButton: ok, clicked: ok ? (b.click(), true) : false };
    });
    await sleep(5000);
    out.walletRead = await page.evaluate(read);
    out.walletTabVerdict = out.tabAfterScroll && out.tabAfterScroll.pointHitsThisButton ? 'REACHABLE_AFTER_HORIZONTAL_SCROLL' : 'UNREACHABLE_AT_390';

    /* The 菜单 button: whose box is actually under its own centre? */
    await page.evaluate(() => { const b = document.querySelector('[data-testid="nav-hub"]'); if (b) b.click(); });
    await sleep(4000);
    out.menuProbe = await page.evaluate(() => {
      const b = [...document.querySelectorAll('button')].find(x => /菜单/.test(x.innerText || ''));
      if (!b) return { present: false };
      const r = b.getBoundingClientRect();
      const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
      const hit = document.elementFromPoint(cx, cy);
      const chain = [];
      for (let n = hit; n && chain.length < 6; n = n.parentElement) {
        const st = getComputedStyle(n);
        chain.push(n.tagName.toLowerCase() + (n.id ? '#' + n.id : '') + (n.className ? '.' + String(n.className).trim().split(/\s+/)[0] : '') + ' pos=' + st.position + ' z=' + st.zIndex + ' pe=' + st.pointerEvents);
      }
      const bs = getComputedStyle(b);
      return { present: true, btnRect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)], point: [cx, cy],
        btnPosition: bs.position, btnZ: bs.zIndex, btnPointerEvents: bs.pointerEvents,
        hitIsButtonOrChild: !!(hit && (hit === b || b.contains(hit))), hitTag: hit && hit.tagName, hitCls: hit && String(hit.className || '').trim().split(/\s+/)[0], hitChain: chain,
        btnBoxFromLayout: b.getBoundingClientRect().height > 0, offsetParentNull: b.offsetParent === null };
    });
    /* Try the real touch path on the menu button rather than a DOM click. */
    if (out.menuProbe && out.menuProbe.present) {
      const [x, y] = out.menuProbe.point;
      await page.touchscreen.tap(x, y).catch(e => { out.menuTapError = String(e.message).slice(0, 120); });
      await sleep(4000);
      out.drawerAfterTouchTap = await page.evaluate(() => {
        const d = document.querySelector('#v8-nav-drawer');
        const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
        return { drawerPresent: !!d, drawerVisible: d ? (d.offsetParent !== null) : null,
          items: d ? [...d.querySelectorAll('button,a')].filter(vis).map(x => (x.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 24)).filter(Boolean).slice(0, 24) : null,
          text: d ? (d.innerText || '').replace(/\s+/g, ' ').slice(0, 300) : null };
      });
    }
    await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '.png') }).catch(() => 0);
  } catch (e) {
    out.error = String(e && e.message || e).split('\n')[0].slice(0, 200);
  } finally {
    out.ended_at = new Date().toISOString();
    out.net = net; out.console = consoleMsgs; out.pageErrors = pageErrors;
    fs.writeFileSync(path.join(__dirname, 'ord0242_groupA2_' + RUN + '.json'), JSON.stringify(out, null, 2));
    console.log(JSON.stringify({ run: RUN, tabStrip: out.tabStrip, afterScroll: out.tabAfterScroll, walletVerdict: out.walletTabVerdict,
      walletH1: out.walletRead && out.walletRead.h1, walletButtons: out.walletRead && (out.walletRead.buttons || []).slice(0, 12),
      menu: out.menuProbe, drawer: out.drawerAfterTouchTap, net: net.slice(0, 10), console_n: consoleMsgs.length, pageErrors: pageErrors.length, err: out.error || null }, null, 2));
    if (ctx) await ctx.close().catch(() => 0);
    await browser.close().catch(() => 0);
  }
})();
