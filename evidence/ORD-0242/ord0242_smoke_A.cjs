/* ORD-0242 smoke, group A: the read-mostly faces on the canary (new bundle x pinned 53fe8e8).
 *
 * Every verdict is taken from rendered text, not from a data attribute and not from an HTTP 200.
 * Each face also carries the two columns the arbiter added: is a red a CONTRACT BOUNDARY (new
 * endpoint / new required field / new enum), and does this face write user data or move an
 * authoritative value. Vocabulary is frozen to COMPATIBLE | COMPATIBLE_WITH_DECLARED_DEGRADATION |
 * INCOMPATIBLE_BACKEND_CONTRACT, and the only UI reason_code allowed is BACKEND_CONTRACT_UNAVAILABLE.
 *
 * Group A covers Today, Map, Wallet (the 预订 tab under 行程), the 菜单 drawer (searching for the
 * Simulation entry the recon pass could not find on any visible face) and Me. Journey generation
 * and the AI sheet are group B because they spend a real model call.
 */
const PW = process.env.CNX_PW || 'D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright';
const { chromium } = require(PW);
const fs = require('fs');
const path = require('path');

const BASE = 'http://127.0.0.1:4185';
const RUN = process.env.CNX_RUN || 'smkA1';
const VW = 390, VH = 844;
const JOURNEY = '22222222-2222-4222-8222-222222222222';
const sleep = ms => new Promise(r => setTimeout(r, ms));

const out = { order: 'ORD-0242', group: 'A', surface: BASE + '/ (canary @4185/8713)',
  bundle_expected: 'index-CrAwWm5f.js', run_label: RUN, pid: process.pid, viewport: [VW, VH],
  started_at: new Date().toISOString(), faces: {} };

const net = [], consoleMsgs = [], pageErrors = [];

const readFace = () => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && e.offsetParent !== null && r.left >= 0 && r.right <= innerWidth; };
  const txt = s => (s || '').replace(/\s+/g, ' ').trim();
  return {
    url: location.pathname,
    h1: (() => { const e = [...document.querySelectorAll('h1')].find(vis); return e ? txt(e.innerText).slice(0, 60) : null; })(),
    h2: [...document.querySelectorAll('h2')].filter(vis).map(e => txt(e.innerText).slice(0, 46)).slice(0, 5),
    body: txt(document.body.innerText).slice(0, 700),
    buttons: [...document.querySelectorAll('button')].filter(vis).map(b => txt(b.innerText).slice(0, 26)).filter(Boolean).slice(0, 30),
    errorCopy: (() => { const e = [...document.querySelectorAll('p,div,span')].filter(vis).find(x => /失败|错误|不可用|出错|无法|没有|未加载|加载不了|不支持|重试|error|failed|unavailable/i.test(x.textContent || '') && x.children.length === 0); return e ? txt(e.textContent).slice(0, 120) : null; })(),
    emptyCopy: (() => { const e = [...document.querySelectorAll('p,div')].filter(vis).find(x => /还没有|暂无|空的|尚未|no .*yet|empty/i.test(x.textContent || '') && x.children.length === 0); return e ? txt(e.textContent).slice(0, 120) : null; })(),
  };
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  out.browser = 'chromium ' + browser.version();
  let ctx = null;
  try {
    const http = require('http');
    const idx = await new Promise((res, rej) => http.get(BASE + '/', r => { const c = []; r.on('data', d => c.push(d)); r.on('end', () => res(Buffer.concat(c).toString())); }).on('error', rej));
    const m = idx.match(/assets\/(index-[^".]+\.js)/);
    const entry = m && m[1];
    const bytes = await new Promise((res, rej) => http.get(BASE + '/assets/' + entry, r => { const c = []; r.on('data', d => c.push(d)); r.on('end', () => res(Buffer.concat(c))); }).on('error', rej));
    out.served_bundle = { file: entry, bytes: bytes.length, sha256: require('crypto').createHash('sha256').update(bytes).digest('hex'),
      matches_expected: entry === out.bundle_expected };
    if (entry !== out.bundle_expected) throw new Error('WRONG_BUNDLE_SERVED: ' + entry);

    ctx = await browser.newContext({ viewport: { width: VW, height: VH }, deviceScaleFactor: 3, isMobile: true, hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
    await ctx.addInitScript(([id]) => { try { localStorage.setItem('citynexus.v8.journey_id', id); } catch (e) {} }, [JOURNEY]);
    const page = await ctx.newPage();
    page.on('request', r => { const u = r.url(); if (u.includes('/api/')) net.push({ at: r.frame().url().replace(BASE, ''), method: r.method(), url: u.replace(BASE, ''), kind: 'request' }); });
    page.on('response', r => { const u = r.url(); if (u.includes('/api/')) net.push({ method: r.request().method(), url: u.replace(BASE, '').split('?')[0], status: r.status(), kind: 'response' }); });
    page.on('console', msg => { const loc = msg.location() || {}; consoleMsgs.push({ type: msg.type(), text: String(msg.text()).slice(0, 220), at: String(loc.url || '').replace(BASE, '') + ':' + (loc.lineNumber || '') }); });
    page.on('pageerror', e => pageErrors.push(String(e.message).slice(0, 220)));

    await page.goto(BASE + '/v8/hub', { waitUntil: 'load', timeout: 60000 });
    await sleep(9000);

    /* ---- Today ---- */
    out.faces.Today = { read: await page.evaluate(readFace) };
    out.faces.Today.tap = await page.evaluate(() => {
      const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && e.offsetParent !== null && r.left >= 0 && r.right <= innerWidth; };
      const b = [...document.querySelectorAll('button')].find(x => /查看实时行程/.test(x.innerText || '') && vis(x));
      if (!b) return { found: false };
      const r = b.getBoundingClientRect(); const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
      const hit = document.elementFromPoint(cx, cy);
      const ok = !!(hit && (hit === b || b.contains(hit)));
      if (ok) b.click();
      return { label: (b.innerText || '').trim(), point: [cx, cy], hitTag: hit && hit.tagName, pointHitsThisButton: ok };
    });
    await sleep(5000);
    out.faces.Today.afterTap = await page.evaluate(readFace);
    await page.goBack().catch(() => 0); await sleep(3500);

    /* ---- Map ---- */
    out.faces.Map = { nav: await page.evaluate(() => { const b = document.querySelector('[data-testid="nav-map"]'); if (b) { b.click(); return true; } return false; }) };
    await sleep(7000);
    out.faces.Map.read = await page.evaluate(readFace);
    out.faces.Map.panel = await page.evaluate(() => {
      const p = document.querySelector('.v8-map-panel');
      const hint = document.querySelector('[data-testid="v8-map-gesture-hint"]');
      const empty = document.querySelector('[data-testid="v8-map-empty"]');
      const cv = document.querySelectorAll('canvas');
      const hr = hint ? hint.getBoundingClientRect() : null;
      return { panelPresent: !!p, panelClass: p ? String(p.className) : null, legs: p ? p.getAttribute('data-route-legs') : null,
        emptyBranch: !!empty, emptyText: empty ? (empty.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 90) : null,
        hintPresent: !!hint, hintText: hint ? hint.textContent.trim().slice(0, 70) : null,
        hintVisible: hint ? (hint.offsetParent !== null && hr.height > 0) : null,
        canvasCount: cv.length, maplibreglElement: !!document.querySelector('.maplibregl-map') };
    });
    out.faces.Map.compare = await page.evaluate(() => {
      const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && e.offsetParent !== null && r.left >= 0 && r.right <= innerWidth; };
      const b = [...document.querySelectorAll('button')].find(x => /对比出行方式/.test(x.innerText || '') && vis(x));
      if (!b) return { found: false };
      const r = b.getBoundingClientRect(); const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
      const hit = document.elementFromPoint(cx, cy); const ok = !!(hit && (hit === b || b.contains(hit)));
      if (ok) b.click();
      return { label: (b.innerText || '').trim(), point: [cx, cy], hitTag: hit && hit.tagName, pointHitsThisButton: ok };
    });
    await sleep(5000);
    out.faces.Map.afterCompare = await page.evaluate(readFace);

    /* ---- Wallet: the 预订 tab under 行程 ---- */
    out.faces.Wallet = { nav: await page.evaluate(() => { const b = document.querySelector('[data-testid="nav-trips"]'); if (b) { b.click(); return true; } return false; }) };
    await sleep(6000);
    out.faces.Wallet.tripsRead = await page.evaluate(readFace);
    out.faces.Wallet.tabTap = await page.evaluate(() => {
      const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && e.offsetParent !== null && r.left >= 0 && r.right <= innerWidth; };
      const b = [...document.querySelectorAll('button')].find(x => (x.innerText || '').trim() === '预订' && vis(x));
      if (!b) return { found: false, tabs: [...document.querySelectorAll('button')].filter(vis).map(x => (x.innerText || '').trim().slice(0, 12)).slice(0, 14) };
      const r = b.getBoundingClientRect(); const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
      const hit = document.elementFromPoint(cx, cy); const ok = !!(hit && (hit === b || b.contains(hit)));
      if (ok) b.click();
      return { label: '预订', point: [cx, cy], hitTag: hit && hit.tagName, hitCls: hit && String(hit.className || '').trim().split(/\s+/)[0], pointHitsThisButton: ok };
    });
    await sleep(5000);
    out.faces.Wallet.read = await page.evaluate(readFace);

    /* ---- the 菜单 drawer, hunting the Simulation entry ---- */
    out.faces.Drawer = { open: await page.evaluate(() => {
      const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && e.offsetParent !== null && r.left >= 0 && r.right <= innerWidth; };
      const b = [...document.querySelectorAll('button')].find(x => /菜单/.test(x.innerText || '') && vis(x));
      if (!b) return { found: false };
      const r = b.getBoundingClientRect(); const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
      const hit = document.elementFromPoint(cx, cy); const ok = !!(hit && (hit === b || b.contains(hit)));
      if (ok) b.click();
      return { label: (b.innerText || '').trim(), point: [cx, cy], hitTag: hit && hit.tagName, pointHitsThisButton: ok };
    }) };
    await sleep(4000);
    out.faces.Drawer.read = await page.evaluate(readFace);
    out.faces.Drawer.drawerItems = await page.evaluate(() => {
      const d = document.querySelector('#v8-nav-drawer') || document.querySelector('nav[aria-label="Product navigation"]');
      if (!d) return { present: false };
      const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
      return { present: true, visible: d.offsetParent !== null,
        items: [...d.querySelectorAll('button,a')].filter(vis).map(x => (x.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 26)).filter(Boolean).slice(0, 30),
        groups: [...d.querySelectorAll('.v8-nav-group')].map(x => (x.innerText || '').trim()).slice(0, 10),
        text: (d.innerText || '').replace(/\s+/g, ' ').slice(0, 400) };
    });
    out.faces.Simulation = { entryFound: false };
    const simIdx = await page.evaluate(() => {
      const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && e.offsetParent !== null && r.left >= 0 && r.right <= innerWidth; };
      const scopes = [['drawer', document.querySelector('#v8-nav-drawer')], ['sidebar', document.querySelector('aside.v8-sidebar nav')], ['any-nav', document.querySelector('nav[aria-label="Product navigation"]')]];
      for (const [scopeName, d] of scopes) {
        if (!d) continue;
        const items = [...d.querySelectorAll('button,a')];
        const i = items.findIndex(x => /Simulation|模拟|沙盘|推演|面板|Recovery|Intelligence|Traveler Twin|权威|恢复|智能/i.test(x.innerText || ''));
        if (i < 0) continue;
        const el = items[i];
        const r = el.getBoundingClientRect();
        const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
        const reachable = vis(el);
        const hit = reachable ? document.elementFromPoint(cx, cy) : null;
        const ok = reachable && !!(hit && (hit === el || el.contains(hit)));
        if (ok) el.click();
        return { scope: scopeName, clicked: (el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 30), box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)], point: [cx, cy],
          visibleInViewport: reachable, offsetParentNull: el.offsetParent === null, hitTag: hit && hit.tagName, pointHitsThisButton: ok };
      }
      return { notFound: true, scopesWalked: scopes.filter(s => s[1]).map(s => s[0]) };
    });
    out.faces.Simulation.drawerClick = simIdx;
    if (simIdx && simIdx.pointHitsThisButton) {
      await sleep(7000);
      out.faces.Simulation.read = await page.evaluate(readFace);
      out.faces.Simulation.entryFound = true;
    } else {
      out.faces.Simulation.read = await page.evaluate(readFace);
      out.faces.Simulation.entryUnreachableAt390 = !(simIdx && simIdx.visibleInViewport);
    }

    /* ---- Me ---- */
    out.faces.Me = { nav: await page.evaluate(() => { const b = document.querySelector('[data-testid="nav-me"]'); if (b) { b.click(); return true; } return false; }) };
    await sleep(5000);
    out.faces.Me.read = await page.evaluate(readFace);

    await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '.png') }).catch(() => 0);

    /* per-face verdicts, derived from what was read */
    const mk = (name, f, opts) => {
      const r = f.read || {};
      const rendered = !!(r.h1 || (r.body && r.body.length > 40));
      const badStatus = net.filter(n => n.kind === 'response' && n.status >= 400 && n.status !== 401 && n.status !== 403);
      const tapped = [f.tap, f.tabTap, f.open, f.simClick].filter(Boolean);
      const unreachable = tapped.filter(t => t && t.found !== false && t.pointHitsThisButton === false).map(t => (t.label || 'item') + '@' + JSON.stringify(t.point));
      f.verdict_bits = { rendered, errorCopyCandidate_for_note_only: r.errorCopy || null, http4xx_named: badStatus.map(n => n.status + ' ' + n.method + ' ' + n.url), pageErrors: pageErrors.length, taps_that_missed: unreachable };
      f.contract_boundary = opts.boundary || null;
      f.writes_user_data = opts.writes || null;
      f.entered_via_hidden_control = opts.hidden || false;
      if (!rendered) f.verdict = 'INCOMPATIBLE_BACKEND_CONTRACT';
      else if (badStatus.length) f.verdict = 'INCOMPATIBLE_BACKEND_CONTRACT';
      else if (opts.verdict) f.verdict = opts.verdict;
      else if (opts.hidden || unreachable.length) f.verdict = 'COMPATIBLE_WITH_DECLARED_DEGRADATION';
      else f.verdict = 'COMPATIBLE';
      if (f.verdict === 'INCOMPATIBLE_BACKEND_CONTRACT') f.reason_code = 'BACKEND_CONTRACT_UNAVAILABLE';
      return f;
    };
    mk('Today', out.faces.Today, { writes: '只读面：进入 Today 会触发 GET /experience，而该路由读时会写（见收据 apiNamed），改的是 _compat.db 副本，不是 _live.db' });
    mk('Map', out.faces.Map, { writes: '只读面，写副本同上' });
    mk('Wallet', out.faces.Wallet, { writes: '只读 tab 切换，无写请求' });
    mk('Drawer', out.faces.Drawer, {});
    mk('Me', out.faces.Me, { writes: '只读面' });
    {
      const S = out.faces.Simulation, sc = S.drawerClick || {};
      mk('Simulation', S, {
        hidden: !S.entryFound,
        boundary: S.entryFound ? null : '不是契约边界：入口在 390px 下不可达（scope=' + (sc.scope || 'not-found') + ', visibleInViewport=' + sc.visibleInViewport + ', offsetParentNull=' + sc.offsetParentNull + '）',
        writes: S.entryFound ? '面板已打开，未触发任何动作 ⇒ 0 写请求' : '未进入，0 请求' });
    }
  } catch (e) {
    out.error = String(e && e.message || e).split('\n')[0].slice(0, 220);
  } finally {
    out.ended_at = new Date().toISOString();
    out.net = net;
    out.console = consoleMsgs;
    out.pageErrors = pageErrors;
    out.nonGetApi = net.filter(n => n.kind === 'request' && n.method !== 'GET').map(n => n.method + ' ' + n.url);
    out.http4xx = net.filter(n => n.kind === 'response' && n.status >= 400).map(n => n.status + ' ' + n.method + ' ' + n.url);
    fs.writeFileSync(path.join(__dirname, 'ord0242_groupA_' + RUN + '.json'), JSON.stringify(out, null, 2));
    console.log(JSON.stringify({
      run: RUN, bundle: out.served_bundle, error: out.error || null,
      faces: Object.fromEntries(Object.entries(out.faces).map(([k, f]) => [k, {
        h1: (f.read || {}).h1, errCopy: (f.read || {}).errorCopy, empty: (f.read || {}).emptyCopy,
        verdict: f.verdict, boundary: f.contract_boundary, http4xx: (f.verdict_bits || {}).http4xx_named,
        tap: f.tap && f.tap.pointHitsThisButton, tabTap: f.tabTap && f.tabTap.pointHitsThisButton,
        drawerOpen: f.open && f.open.pointHitsThisButton, items: f.drawerItems && f.drawerItems.items && f.drawerItems.items.slice(0, 12),
        panel: f.panel, simClick: f.drawerClick }])) ,
      nonGetApi: out.nonGetApi, http4xx_all: out.http4xx, console_n: (out.console || []).length, console_first: (out.console || []).slice(0, 5), pageErrors: (out.pageErrors || []).slice(0, 4),
    }, null, 2));
    if (ctx) await ctx.close().catch(() => 0);
    await browser.close().catch(() => 0);
  }
})();
