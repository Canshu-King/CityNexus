/* ORD-0224 map-gesture probe: does the on-screen gesture copy match what the map actually does?
 *
 * Arm A (map):      single-finger drag inside the map canvas  -> expect camera moves, page does NOT scroll
 * Arm B (mirror):   identical drag on body text outside the map -> expect page scrolls, camera bit-identical
 * Without arm B the result is not single-variable.
 *
 * Instrument note (why not "did the container transform change"): maplibre v3+ repaints a WebGL canvas,
 * so the CSS transform stays `none` forever and a transform-based assertion is blind to real camera moves.
 * We read map.getCenter()/getZoom() instead. The Map object is reached through the React fiber on
 * .v8-map-panel because MapPanel.tsx loads maplibre via `void import("maplibre-gl")` - container._map,
 * canvas._map and window.maplibregl are all null.
 *
 * Read-only against the UI. Never press 确认创建. Point CNX_BASE at your own isolated stack.
 */
const PW = process.env.CNX_PW || 'D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright';
const { chromium } = require(PW);
const fs = require('fs');
const path = require('path');
const http = require('http');
const crypto = require('crypto');

const BASE = process.env.CNX_BASE || 'http://127.0.0.1:8792';
const RUN = process.env.CNX_RUN || 'gest';
const VW = 390, VH = 844;
const out = { base: BASE, run_label: RUN, pid: process.pid, viewport: [VW, VH] };
out.displacement_rationale = 'Arms A and B share (-90,-60), a horizontal-dominant drag, so B is a same-gesture specificity control for the camera. RETRACTED: matrix run mtx1 said the off-map drag failed to scroll because 60px was "too short". mtx2 refuted that — a short PURE-vertical (0,-60) scrolls DOCUMENT 0->45 and a vertical-dominant (-60,-90) scrolls 0->78, while horizontal-dominant (-90,-60) never scrolls at either start y or step count. Direction, not length, decides whether the browser treats a touch drag as a page scroll. Consequence: arm A2 drags vertical-dominant (0,-120) INSIDE the canvas, because that is the only swipe shape that could steal the page scroll, and arm C uses a long vertical (0,-320) OUTSIDE it to test the page-turn clause of the on-screen sentence.';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const localIso = d => { const o = -d.getTimezoneOffset(), s = o >= 0 ? '+' : '-', p = n => String(n).padStart(2, '0'); return new Date(d.getTime() + o * 60000).toISOString().replace('Z', '') + s + p(Math.floor(Math.abs(o) / 60)) + ':' + p(Math.abs(o) % 60); };
out.started_at = localIso(new Date()); out.started_at_utc = new Date().toISOString();

const get = u => new Promise((res, rej) => http.get(u, r => { const c = []; r.on('data', d => c.push(d)); r.on('end', () => res(Buffer.concat(c))); }).on('error', rej));

(async () => {
  const browser = await chromium.launch({ headless: true });
  out.browser = 'chromium ' + browser.version();
  let ctx = null, page = null, cdp = null;
  const writes = [];
  const offOrigin = [];
  try {
    try {
      const html = (await get(BASE + '/')).toString();
      const m = html.match(/assets\/(index-[^".]+\.js)/);
      const a = await get(BASE + '/assets/' + m[1]);
      out.served_bundle = { file: m[1], bytes: a.length, sha256: crypto.createHash('sha256').update(a).digest('hex') };
    } catch (e) { out.served_bundle = { error: String(e.message).slice(0, 80) }; }

  const JOURNEY = process.env.CNX_JOURNEY || '';
  ctx = await browser.newContext({ viewport: { width: VW, height: VH }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  if (JOURNEY) {
    // A stored journey id is the state the user's own phone already holds. There is no
    // journey list/switcher reachable at mobile width, so this is the only way back in.
    await ctx.addInitScript(([id]) => { try { localStorage.setItem('citynexus.v8.journey_id', id); } catch (e) {} }, [JOURNEY]);
    out.entry_mode = 'seeded localStorage journey_id = ' + JOURNEY;
  } else {
    out.entry_mode = 'fresh profile (no stored journey)';
  }
  page = await ctx.newPage();
  page.on('request', r => { if (r.method() !== 'GET' && r.url().includes('/api/')) writes.push(r.method() + ' ' + r.url()); });
  page.on('response', r => { const u = r.url(); if (!u.startsWith(BASE)) offOrigin.push(r.status() + ' ' + u.slice(0, 110)); });
  page.on('requestfailed', r => { const u = r.url(); if (!u.startsWith(BASE)) offOrigin.push('FAILED ' + (r.failure() && r.failure().errorText) + ' ' + u.slice(0, 100)); });
  cdp = await ctx.newCDPSession(page);

  await page.goto(BASE + '/v8/hub', { waitUntil: 'load', timeout: 45000 });
  await sleep(5000);

  out.landing = await page.evaluate(() => ({
    heading: ((document.querySelector('h1,h2') || {}).innerText || '').trim().slice(0, 40),
    hasMapPanel: !!document.querySelector('.v8-map-panel'),
    hasMobileNav: !!document.querySelector('.v8-mobile-nav'),
    url: location.pathname,
    textStart: (document.body.innerText || '').replace(/\s+/g, ' ').slice(0, 140),
  }));

  const hasMap = () => page.evaluate(() => !!document.querySelector('.v8-map-panel canvas'));

  /* Real user path to the map: bottom nav -> 地图. */
  if (!(await hasMap())) {
    out.navToMap = await page.evaluate(() => {
      const b = document.querySelector('[data-testid="nav-map"]') ||
        [...document.querySelectorAll('.v8-mobile-nav button')].find(x => /地图|Map/.test(x.innerText || ''));
      if (!b) return { found: false, navButtons: [...document.querySelectorAll('.v8-mobile-nav button')].map(x => (x.innerText || '').replace(/\s+/g, ' ').trim()) };
      const r = b.getBoundingClientRect();
      b.click();
      return { found: true, txt: (b.innerText || '').replace(/\s+/g, ' ').trim(), box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)] };
    });
    await sleep(4500);
    if (!(await hasMap())) {
      out.urlAfterNav = await page.evaluate(() => location.pathname);
      out.textAfterNav = await page.evaluate(() => (document.body.innerText || '').replace(/\s+/g, ' ').slice(0, 200));
    }
  }

  /* Second fallback: the sealed-demo entry, which is the only UI path that reaches a journey from a fresh profile. */
  if (!(await hasMap())) {
    out.via = 'sealed-demo entry';
    await page.goto(BASE + '/v8/hub', { waitUntil: 'load', timeout: 45000 });
    await sleep(4000);
    await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(y => (y.innerText || '').includes('试用其他城市') && y.getBoundingClientRect().height > 0); if (b) b.click(); });
    await sleep(2500);
    await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(y => /封存的演示行程/.test(y.innerText || '') && y.getBoundingClientRect().height > 0); if (b) { b.scrollIntoView({ block: 'center' }); b.click(); } });
    await sleep(7000);
    if (await hasMap()) { await page.evaluate(() => { const b = document.querySelector('[data-testid="nav-map"]'); if (b) b.click(); }); await sleep(4500); }
  } else {
    out.via = out.navToMap && out.navToMap.found ? 'bottom nav -> 地图' : 'hub already shows the map';
  }

  /* Arm the map: reach the Map instance through the React fiber (documented above). */
  out.map_handle = await page.evaluate(() => {
    const host = document.querySelector('.v8-map-panel');
    if (!host) return { ok: false, why: 'no .v8-map-panel' };
    const key = Object.keys(host).find(k => k.startsWith('__reactFiber$'));
    if (!key) return { ok: false, why: 'no __reactFiber$ on .v8-map-panel' };
    const seen = new Set();
    const isMap = o => o && typeof o.getCenter === 'function' && typeof o.getZoom === 'function';
    let found = null, depth = -1, via = null;
    const scan = (obj, d, label) => {
      if (found || !obj || d > 8 || typeof obj !== 'object') return;
      if (isMap(obj)) { found = obj; depth = d; via = label; return; }
      for (const k of ['stateNode', 'memoizedState', 'return', 'child', 'sibling', 'alternate', 'current', 'elementType']) {
        try { const v = obj[k]; if (v && !seen.has(v) && typeof v === 'object') { seen.add(v); scan(v, d + 1, label + '.' + k); } } catch (e) {}
      }
      if (obj && typeof obj === 'object') {
        for (const k of Object.keys(obj)) {
          if (found) break;
          try { const v = obj[k]; if (v && !seen.has(v) && typeof v === 'object') { seen.add(v); scan(v, d + 1, label + '.' + k); } } catch (e) {}
        }
      }
    };
    scan(host[key], 0, 'fiber');
    if (!found) return { ok: false, why: 'no object with getCenter/getZoom within 8 hops', fiberKey: key };
    window.__cnxMap = found;
    const c = found.getCenter();
    return { ok: true, depth, via, start_center: [c.lng, c.lat], zoom: found.getZoom(), routeLegsAttr: host.getAttribute('data-route-legs'), modesAttr: host.getAttribute('data-route-modes') };
  });
  if (!out.map_handle.ok) throw new Error('MAP_HANDLE_FAILED: ' + out.map_handle.why);

  /* Precondition: the map must actually have a route, or a camera move proves nothing. */
  out.precondition = await page.evaluate(() => {
    const host = document.querySelector('.v8-map-panel');
    const t = (document.body.innerText || '').replace(/\s+/g, ' ');
    const leafOf = root => [...root.querySelectorAll('*')].find(e => /单指|双指/.test(e.textContent || '') && e.children.length === 0);
    const leaf = leafOf(host) || leafOf(document.body);
    const i = t.indexOf('单指');
    return {
      routeLegs: Number(host.getAttribute('data-route-legs') || '-1'),
      canvasPresent: !!host.querySelector('canvas'),
      gestureCopy: leaf ? leaf.textContent.trim().slice(0, 120) : (i >= 0 ? t.slice(Math.max(0, i - 10), i + 70) : null),
      degradationNotice: (t.match(/[^。]*底图[^。]*。/) || [null])[0],
      tileNotice: (() => {
        const n = [...document.querySelectorAll('*')].find(e => /底图/.test(e.textContent || '') && e.children.length === 0);
        if (!n) return null;
        const r = n.getBoundingClientRect();
        return { text: n.textContent.trim().slice(0, 70), visible: n.offsetParent !== null, box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)] };
      })(),
      panelAttrs: Object.fromEntries([...host.attributes].filter(a => /tile|raster|route|status|loaded/i.test(a.name)).map(a => [a.name, a.value])),
      scrollTop: document.scrollingElement.scrollTop,
    };
  });

  const readState = () => page.evaluate(() => {
    const m = window.__cnxMap; const c = m.getCenter();
    const cv = document.querySelector('.v8-map-panel canvas');
    const cr = cv ? cv.getBoundingClientRect() : null;
    const ident = el => {
      if (el === document.scrollingElement || el === document.documentElement) return 'DOCUMENT';
      let s = el.tagName.toLowerCase();
      if (el.id) s += '#' + el.id;
      const cls = (el.className || '').toString().trim().split(/\s+/).slice(0, 2).join('.');
      if (cls) s += '.' + cls;
      return s;
    };
    const scrollers = [];
    const de = document.scrollingElement;
    if (de && de.scrollHeight > de.clientHeight + 8) scrollers.push({ el: ident(de), scrollTop: de.scrollTop, sh: de.scrollHeight, ch: de.clientHeight });
    for (const el of document.querySelectorAll('*')) {
      const st = getComputedStyle(el);
      if (!/(auto|scroll)/.test(st.overflowY)) continue;
      if (el.scrollHeight <= el.clientHeight + 8) continue;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      scrollers.push({ el: ident(el), scrollTop: el.scrollTop, sh: el.scrollHeight, ch: el.clientHeight, inMap: !!el.closest('.v8-map-panel') });
    }
    return {
      center: [c.lng, c.lat], zoom: m.getZoom(), scrollTop: de ? de.scrollTop : null,
      docScrollHeight: de ? de.scrollHeight : null, docClientHeight: de ? de.clientHeight : null,
      vw: window.innerWidth, vh: window.innerHeight,
      canvas: cr ? [Math.round(cr.x), Math.round(cr.y), Math.round(cr.width), Math.round(cr.height)] : null,
      scrollers,
    };
  });

  const drag = async (x, y, dx, dy) => {
    const pt = (type, tx, ty) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x: tx, y: ty, radiusX: 12, radiusY: 12, force: 1 }] });
    await pt('touchStart', x, y);
    for (let i = 1; i <= 10; i++) { await sleep(16); await pt('touchMove', x + (dx * i) / 10, y + (dy * i) / 10); }
    await sleep(60);
    await pt('touchEnd', 0, 0);
    await sleep(900);
  };

  const box = await page.evaluate(() => {
    const r = document.querySelector('.v8-map-panel canvas').getBoundingClientRect();
    const inMap = e => !!e && !!e.closest('.v8-map-panel');
    const cand = [...document.querySelectorAll('p,li,span,h2,h3,article,section,div')].map(e => ({ e, r: e.getBoundingClientRect() }));
    const mapTop = Math.round(r.y);
    /* A neutral off-map target: page body above the map, not the fixed bottom bar, not a control. */
    const pick = ok => {
      const rejected = [];
      for (const x of cand) {
        if (!ok(x)) continue;
        const cx = Math.round(x.r.x + x.r.width / 2), cy = Math.round(x.r.y + x.r.height / 2);
        if (cy < 5 || cy > 839) continue;
        const hit = document.elementFromPoint(cx, cy);
        if (!hit) { rejected.push([cx, cy, 'no-hit']); continue; }
        if (inMap(hit) || inMap(x.e)) { rejected.push([cx, cy, 'in-map']); continue; }
        if (cy >= mapTop - 8) { rejected.push([cx, cy, 'below-map-top']); continue; }
        if (hit.closest('nav,button,a,[role=button]')) { rejected.push([cx, cy, 'interactive:' + hit.tagName + '.' + String(hit.className || '').trim().split(/\s+/)[0]]); continue; }
        if (/(fixed|sticky)/.test(getComputedStyle(hit).position)) { rejected.push([cx, cy, 'fixed-hit']); continue; }
        return { tag: x.e.tagName, cls: String(x.e.className || '').trim().split(/\s+/)[0], txt: (x.e.textContent || '').trim().slice(0, 24), x: cx, y: cy, hitTag: hit.tagName, hitCls: String(hit.className || '').trim().split(/\s+/)[0], hitPosition: getComputedStyle(hit).position, rejectedBefore: rejected.slice(0, 6) };
      }
      return { point: null, rejectedAll: rejected.slice(0, 10) };
    };
    return {
      map: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
      outside: pick(x => x.r.width > 200 && x.r.top > 60 && (x.e.textContent || '').trim().length > 6),
      pageTurn: pick(x => x.r.width > 160 && (x.r.y + x.r.height / 2) >= 340 && (x.r.y + x.r.height / 2) <= mapTop - 20 && (x.e.textContent || '').trim().length > 6),
    };
  });

  const scrollerDelta = (b, a) => {
    const before = {}; (b.scrollers || []).forEach(s => { before[s.el] = s.scrollTop; });
    const moved = [];
    for (const s of (a.scrollers || [])) { if (before[s.el] !== undefined && before[s.el] !== s.scrollTop) moved.push({ el: s.el, from: before[s.el], to: s.scrollTop }); }
    return { moved, subjects: (b.scrollers || []).map(s => s.el + ' ' + s.scrollTop + '/' + s.sh + '>' + s.ch) };
  };

  /* Arm A: drag inside the map. */
  const a0 = await readState();
  await drag(box.map[0] + box.map[2] / 2, box.map[1] + box.map[3] / 2, -90, -60);
  const a1 = await readState();
  out.armA = { where: 'inside map canvas', box: box.map, before: a0, after: a1,
    centerMoved: a0.center[0] !== a1.center[0] || a0.center[1] !== a1.center[1],
    centerDelta: [+(a1.center[0] - a0.center[0]).toFixed(6), +(a1.center[1] - a0.center[1]).toFixed(6)],
    pageScrolled: a1.scrollTop !== a0.scrollTop,
    anyScrollerMoved: scrollerDelta(a0, a1).moved,
    scrollSubjects: scrollerDelta(a0, a1).subjects };

  /* Arm A2: the matrix showed a vertical-dominant swipe is precisely the shape the browser turns
     into a page scroll, so a vertical-dominant drag that STARTS inside the canvas is where the map
     could steal the page. Arm A's (-90,-60) is horizontal-dominant and cannot test that. */
  await page.evaluate(() => { document.scrollingElement.scrollTop = 0; for (const el of document.querySelectorAll('*')) { const st = getComputedStyle(el); if (/(auto|scroll)/.test(st.overflowY)) el.scrollTop = 0; } });
  await sleep(400);
  const e0 = await readState();
  await drag(box.map[0] + box.map[2] / 2, box.map[1] + box.map[3] / 2, 0, -120);
  const e1 = await readState();
  out.armA2 = { where: 'vertical-dominant drag starting inside map canvas', box: box.map, before: e0, after: e1,
    centerMoved: e0.center[0] !== e1.center[0] || e0.center[1] !== e1.center[1],
    centerDelta: [+(e1.center[0] - e0.center[0]).toFixed(6), +(e1.center[1] - e0.center[1]).toFixed(6)],
    pageScrolled: e1.scrollTop !== e0.scrollTop,
    anyScrollerMoved: scrollerDelta(e0, e1).moved };

  /* Control: a zero-displacement tap at the same point must not move the camera. */
  const t0 = await readState();
  const pt0 = (type, tx, ty) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x: tx, y: ty, radiusX: 12, radiusY: 12, force: 1 }] });
  await pt0('touchStart', box.map[0] + box.map[2] / 2, box.map[1] + box.map[3] / 2);
  await sleep(80);
  await pt0('touchEnd', 0, 0);
  await sleep(1200);
  const t1 = await readState();
  out.controlTap = { where: 'same map point, no movement', before: t0.center, after: t1.center,
    centerDrifted: Math.abs(t1.center[0] - t0.center[0]) > 1e-9 || Math.abs(t1.center[1] - t0.center[1]) > 1e-9 };

  /* Arm B (specificity control): the IDENTICAL drag landing outside the map must not move the camera. */
  if (!box.outside || !box.outside.x) { out.armB = { skipped: 'no neutral off-map block', why: box.outside && box.outside.rejectedAll }; }
  else {
    const b0 = await readState();
    await drag(box.outside.x, box.outside.y, -90, -60);
    const b1 = await readState();
    out.armB = { where: 'body text outside map, same displacement as arm A', target: box.outside, before: b0, after: b1,
      centerMoved: b0.center[0] !== b1.center[0] || b0.center[1] !== b1.center[1],
      centerBitIdentical: b0.center[0] === b1.center[0] && b0.center[1] === b1.center[1] };
  }

  /* Arm D: the sentence's second clause, 双指缩放. Two fingers spread apart inside the canvas.
     Runs before arm C; that is harmless because every arm compares to its own before/after. */
  const pinch = async (cx, cy) => {
    const two = (type, a, b) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [
      { x: a[0], y: a[1], radiusX: 12, radiusY: 12, force: 1 }, { x: b[0], y: b[1], radiusX: 12, radiusY: 12, force: 1 }] });
    await two('touchStart', [cx - 40, cy], [cx + 40, cy]);
    for (let i = 1; i <= 10; i++) { await sleep(16); const g = 40 + 5 * i; await two('touchMove', [cx - g, cy], [cx + g, cy]); }
    await sleep(60); await two('touchEnd', [0, 0], [0, 0]); await sleep(1200);
  };
  const d0 = await readState();
  await pinch(box.map[0] + box.map[2] / 2, box.map[1] + box.map[3] / 2);
  const d1 = await readState();
  out.armD = { where: 'two-finger spread inside map canvas', before: d0, after: d1,
    zoomDelta: +(d1.zoom - d0.zoom).toFixed(6), zoomChanged: d0.zoom !== d1.zoom,
    centerMoved: d0.center[0] !== d1.center[0] || d0.center[1] !== d1.center[1],
    anyScrollerMoved: scrollerDelta(d0, d1).moved };

  /* Arm C (separate contract): the sentence also promises that dragging outside the map turns the
     page. That needs a displacement long enough to be a page turn — the drag matrix measured 60px
     as too short on purpose, so this arm uses -320 and asserts a scroll subject advances. */
  if (!box.pageTurn || !box.pageTurn.x) { out.armC = { skipped: 'no neutral off-map block for a long swipe', why: box.pageTurn && box.pageTurn.rejectedAll }; }
  else {
    await page.evaluate(() => { document.scrollingElement.scrollTop = 0; for (const el of document.querySelectorAll('*')) { const st = getComputedStyle(el); if (/(auto|scroll)/.test(st.overflowY)) el.scrollTop = 0; } });
    await sleep(400);
    const c0 = await readState();
    await drag(box.pageTurn.x, box.pageTurn.y, 0, -320);
    const c1 = await readState();
    const dC = scrollerDelta(c0, c1);
    out.armC = { where: 'long vertical swipe outside the map', target: box.pageTurn, before: c0, after: c1,
      documentScrolled: c1.scrollTop !== c0.scrollTop,
      anyScrollerMoved: dC.moved,
      cameraUntouched: c0.center[0] === c1.center[0] && c0.center[1] === c1.center[1],
      scrollSubjects: dC.subjects };
  }

  out.verdict = (() => {
    const A = out.armA, B = out.armB, C = out.armC;
    const readings = [A.before, A.after, out.armA2 && out.armA2.before, out.armA2 && out.armA2.after, B && B.before, B && B.after, C && C.before, C && C.after, out.armD && out.armD.before, out.armD && out.armD.after].filter(Boolean);
    const bad = readings.filter(s => s.vw !== VW || s.vh !== VH);
    if (bad.length) return 'INCOMPLETE_VIEWPORT_DRIFT: ' + bad.map(s => s.vw + 'x' + s.vh).join(',');
    if (out.controlTap && out.controlTap.centerDrifted) return 'INCOMPLETE_CONTROL_TAP_DRIFT: 无位移轻点也改了相机，正例不可归因于拖动';
    if (!A.centerMoved) return 'GESTURE_REGRESSION: 屏上提示「单指拖动地图」，但单指在地图内拖动没有改变相机（Δ=0）';
    if (A.pageScrolled || (A.anyScrollerMoved || []).length) return 'GESTURE_REGRESSION: 单指拖地图同时抢走了页面滚动: ' + JSON.stringify(A.anyScrollerMoved);
    if (out.armA2 && (out.armA2.pageScrolled || (out.armA2.anyScrollerMoved || []).length)) return 'GESTURE_REGRESSION: 在地图内做纵向主导滑动(0,-120)时把页面一起滚走了 ' + JSON.stringify(out.armA2.anyScrollerMoved) + '（文档 ' + out.armA2.before.scrollTop + '→' + out.armA2.after.scrollTop + '）';
    if (!B || B.skipped) return 'INCOMPLETE_MIRROR_ARM';
    if (!B.centerBitIdentical) return 'GESTURE_REGRESSION: 地图外同一手势也改了相机 → arm A 的相机变化不可归因于地图手势';
    if (!C || C.skipped) return 'INCOMPLETE_PAGETURN_ARM: 没能测「想翻这一页就拖地图以外的地方」';
    if (!(C.documentScrolled || (C.anyScrollerMoved || []).length)) return 'GESTURE_REGRESSION: 屏上提示「想翻这一页就拖地图以外的地方」，但在地图外用 -320px 长滑（矩阵实测可滚的位移）没有滚动任何可滚主体 ' + JSON.stringify(C.scrollSubjects);
    if (C.cameraUntouched === false) return 'GESTURE_REGRESSION: 地图外长滑也动了相机';
    if (!out.armD || out.armD.skipped) return 'INCOMPLETE_PINCH_ARM: 没能测「双指缩放」';
    if (!out.armD.zoomChanged) return 'GESTURE_REGRESSION: 屏上提示「双指缩放」，但两指在地图内分离没有改变 zoom（Δ=0）';
    if ((out.armD.anyScrollerMoved || []).length) return 'GESTURE_REGRESSION: 双指缩放同时抢走了页面滚动: ' + JSON.stringify(out.armD.anyScrollerMoved);
    return 'GESTURE_CONTRACT_OK: 单指拖地图→相机动且无任何可滚主体位移；地图外同位移→相机逐位不变；地图外 -320px 长滑→页面翻（' + JSON.stringify(C.anyScrollerMoved.length ? C.anyScrollerMoved : { doc: [C.before.scrollTop, C.after.scrollTop] }) + '）；双指分离→zoom Δ' + out.armD.zoomDelta + '；无位移轻点→相机不动';
  })();
  out.noticeAtEnd = await page.evaluate(() => {
    const n = [...document.querySelectorAll('*')].find(e => /底图/.test(e.textContent || '') && e.children.length === 0);
    if (!n) return { present: false };
    const r = n.getBoundingClientRect();
    return { present: true, text: n.textContent.trim().slice(0, 70), visible: n.offsetParent !== null, box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)] };
  });
  out.tileOutcome = { ok200: offOrigin.filter(u => /^200 https/.test(u)).length, failed: offOrigin.filter(u => /^FAILED/.test(u)).length, raster200: offOrigin.filter(u => /^200 https:\/\/tile\./.test(u)).length };
  await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0224_' + RUN + '.png') }).catch(() => 0);

  out.ended_at = localIso(new Date()); out.ended_at_utc = new Date().toISOString();
  out.nonGetRequests = writes;
  out.offOriginRequests = offOrigin;
  fs.writeFileSync(path.join(__dirname, 'ord0224_gesture_' + RUN + '.json'), JSON.stringify(out, null, 2));
  console.log(JSON.stringify({
    run: RUN, pid: out.pid, bundle: out.served_bundle && out.served_bundle.file, via: out.via,
    legs: out.precondition && out.precondition.routeLegs, mapVia: out.map_handle && out.map_handle.via,
    A: out.armA && { moved: out.armA.centerMoved, d: out.armA.centerDelta, scrolled: out.armA.pageScrolled, scrollers: out.armA.anyScrollerMoved },
    A2: out.armA2 && { moved: out.armA2.centerMoved, d: out.armA2.centerDelta, doc: [out.armA2.before.scrollTop, out.armA2.after.scrollTop], scrollers: out.armA2.anyScrollerMoved },
    tap: out.controlTap && { drifted: out.controlTap.centerDrifted },
    B: out.armB && (out.armB.skipped ? 'skipped' : { cameraMoved: out.armB.centerMoved, bitIdentical: out.armB.centerBitIdentical }),
    D: out.armD && { zoomDelta: out.armD.zoomDelta, centerMoved: out.armD.centerMoved, scrollers: out.armD.anyScrollerMoved },
    C: out.armC && (out.armC.skipped ? 'skipped' : { doc: [out.armC.before.scrollTop, out.armC.after.scrollTop], scrollers: out.armC.anyScrollerMoved, cameraUntouched: out.armC.cameraUntouched }),
    subjects: out.armC && out.armC.scrollSubjects, copy: out.precondition && out.precondition.gestureCopy,
    tileNotice: out.precondition && out.precondition.tileNotice, panelAttrs: out.precondition && out.precondition.panelAttrs, offOrigin: offOrigin.slice(0, 8),
    verdict: out.verdict, err: out.error || null, nonGet: writes.length,
  }, null, 2));
  } catch (e) {
    out.error = String(e && e.message || e).split('\n')[0].slice(0, 200);
    out.ended_at = localIso(new Date()); out.ended_at_utc = new Date().toISOString();
    out.nonGetRequests = writes;
    if (!out.verdict) out.verdict = 'INCOMPLETE';
    fs.writeFileSync(path.join(__dirname, 'ord0224_gesture_' + RUN + '.json'), JSON.stringify(out, null, 2));
    console.log(JSON.stringify({ run: RUN, pid: out.pid, verdict: out.verdict, err: out.error, nonGet: writes.length }, null, 2));
  } finally {
    if (ctx) await ctx.close().catch(() => 0);
    await browser.close().catch(() => 0);
  }
})();
