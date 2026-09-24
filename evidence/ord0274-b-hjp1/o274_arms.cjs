/* ORD-0274 B arm (reconnected transition) - instrument owner HJ-P1 1a986a24.
 *
 * Cells, verbatim from arbiter 5805553583 as relayed in the ledger:
 *   B1 reconnect-first-navigation  old worker + old cache kept, 0 unregister / 0 cache clear;
 *      network restored, the user performs ONE normal navigation.  The bundle that first
 *      executes may be the old generation, but the worker update lifecycle must be recorded.
 *   B2 automatic-convergence       once the new worker installs/activates/claims, the current
 *      page must converge to the new asset graph BY ITSELF (reload or equivalent); the user
 *      action count stays at ONE navigation.
 *   B3 offline-after-convergence   afterwards offline again: a normal navigation must be served
 *      self-consistently by the new worker/new precache - no old-worker + new-shell mixing,
 *      no falling back to the previous generation.
 *
 * Hard rule honoured here: navigator.serviceWorker.getRegistration().unregister() and
 * caches.delete()/clear() are NEVER called.  A grep over this file for those tokens is part
 * of the receipt (see o274_run.py), because "the instrument did not cheat" must be checkable
 * by someone else rather than asserted by me.
 *
 * Nothing computes a verdict: this records.  Derivation lives in o274_derive.py.
 */
const PW = process.env.CNX_PW || 'D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright';
const { chromium } = require(PW);
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const BASE = process.env.CNX_BASE;                 // http://127.0.0.1:<my named port>
const RUN = process.env.CNX_RUN || 'camp1';
const PROFILE = process.env.CNX_PROFILE;           // persistent: this is what "returning client" means
const GEN_A_DIR = process.env.CNX_GEN_A;           // old generation dist (the last successfully installed)
const GEN_B_DIR = process.env.CNX_GEN_B;           // new generation dist
const POINTER = process.env.CNX_POINTER;           // current_root.txt - the redeploy knob
const SHOTS = process.env.CNX_SHOTS || __dirname;
const sleep = ms => new Promise(r => setTimeout(r, ms));

const setRoot = (dir) => { fs.writeFileSync(POINTER, dir, 'utf8'); return { pointer: POINTER, root: path.basename(dir), readBack: fs.readFileSync(POINTER, 'utf8').trim() === dir }; };
const hashDir = (dir) => ({ dir: path.basename(dir),
  bundle: (() => { const m = fs.readFileSync(path.join(dir, 'index.html'), 'utf8').match(/assets\/(index-[\w-]+\.js)/); return m && m[1]; })(),
  worker_sha256: crypto.createHash('sha256').update(fs.readFileSync(path.join(dir, 'v10-sw.js'))).digest('hex'),
  worker_bytes: fs.statSync(path.join(dir, 'v10-sw.js')).size });

const out = { order: 'ORD-0274', arm: 'B (reconnected transition)', session: '1a986a24 HJ-P1',
  role: 'instrument owner + runtime verifier', run_label: RUN, base: BASE, started_at: new Date().toISOString(),
  forbidden_moves_taken: { unregister_called: 0, cache_clear_called: 0 },
  viewport: [390, 844], generations: { A_old: hashDir(GEN_A_DIR), B_new: hashDir(GEN_B_DIR) },
  phases: {}, instrument: { pageErrors: [], navEvents: [] } };

/* evaluate with a short timeout, and say so if it timed out instead of waiting 30 s (trap 27) */
async function probe(page) {
  let r, timedOut = false;
  try {
    r = await Promise.race([
      page.evaluate(async () => {
        const base = (window.__probe)();
        base.registrations = await (window.__regs)();
        base.caches = await (window.__cacheFacts)();
        return base;
      }),
      new Promise((_, rej) => setTimeout(() => rej(new Error('probe timeout')), 12000)),
    ]);
  } catch (e) { timedOut = true; r = { href: page.url(), probeError: String(e.message).slice(0, 80) }; }
  return Object.assign({ atMsSincePhaseStart: Date.now(), measured: !timedOut }, r);
}

(async () => {
  fs.rmSync(PROFILE, { recursive: true, force: true });
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    headless: true, viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
    isMobile: true, hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = ctx.pages()[0] || await ctx.newPage();
  page.on('pageerror', e => out.instrument.pageErrors.push(String(e.message).slice(0, 180)));
  page.on('framenavigated', f => { if (f === page.mainFrame()) out.instrument.navEvents.push({ at: Date.now(), href: f.url(), label: 'framenavigated' }); });
  ctx.on('serviceWorker', sw => out.instrument.swWorkers = (out.instrument.swWorkers || []).concat([{ at: Date.now(), url: sw.url() }]));

  // init script: keep a lifecycle ring buffer inside every document, and count document births
  await ctx.addInitScript(() => {
    window.__cnxDocCount = (window.__cnxDocCount || 0);
    window.__cnxDocBirth = Date.now();
    const ev = window.__cnxEvents = [];
    const push = (name, extra) => ev.push(Object.assign({ ev: name, t: Math.round(performance.now()), href: location.href }, extra || {}));
    push('document-start', { scripts: [...document.querySelectorAll('script[src]')].map(s => s.getAttribute('src')) });
    document.addEventListener('DOMContentLoaded', () => push('DOMContentLoaded', { scripts: [...document.querySelectorAll('script[src]')].map(s => s.getAttribute('src').split('/').pop()) }));
    window.addEventListener('load', () => push('load', { scripts: [...document.querySelectorAll('script[src]')].map(s => s.getAttribute('src').split('/').pop()) }));
    if (navigator.serviceWorker) {
      navigator.serviceWorker.addEventListener('controllerchange', () => push('controllerchange', { controller: navigator.serviceWorker.controller && navigator.serviceWorker.controller.scriptURL }));
      navigator.serviceWorker.ready.then(r => push('sw-ready', { active: r.active && r.active.scriptURL, waiting: !!r.waiting, installing: !!r.installing }));
      navigator.serviceWorker.getRegistration().then(r => {
        if (!r) return push('no-registration-yet');
        const track = (w, who) => { if (!w) return; w.addEventListener('statechange', () => push('state:' + who, { state: w.state, script: w.scriptURL })); };
        track(r.installing, 'installing'); track(r.waiting, 'waiting'); track(r.active, 'active');
        r.addEventListener('updatefound', () => { push('updatefound'); track(r.installing, 'installing'); track(r.waiting, 'waiting'); });
      }).catch(() => 0);
    }
    window.__probe = () => {
      const short = u => String(u || '').replace(location.origin, '');
      const leafTexts = [...document.querySelectorAll('body *')].filter(e => {
        if (e.children.length) return false;
        const r = e.getBoundingClientRect(), st = getComputedStyle(e);
        return r.width > 2 && r.height > 2 && st.display !== 'none' && st.visibility !== 'hidden'
          && !/sr-only/.test(typeof e.className === 'string' ? e.className : '')
          && r.bottom > 0 && r.top < innerHeight;
      }).map(e => (e.innerText || '').replace(/\s+/g, ' ').trim()).filter(Boolean);
      return { href: location.href, pathname: location.pathname,
        docNonce: (window.__cnxProbeNonce = window.__cnxProbeNonce || Math.random().toString(36).slice(2)),
        docBirth: window.__cnxDocBirth, docAgeMs: Math.round(performance.now()),
        scripts: [...document.querySelectorAll('script[src]')].map(s => short(s.getAttribute('src'))),
        css: [...document.querySelectorAll('link[rel=stylesheet]')].map(l => short(l.getAttribute('href'))),
        bodyChars: leafTexts.join(' ').length, headings: leafTexts.slice(0, 6),
        controller: !!(navigator.serviceWorker && navigator.serviceWorker.controller),
        controllerScript: navigator.serviceWorker && navigator.serviceWorker.controller && short(navigator.serviceWorker.controller.scriptURL),
        lifecycle: (window.__cnxEvents || []).slice(-40), chromeError: /^chrome-error:/.test(location.href) };
    };
    window.__regs = async () => (await navigator.serviceWorker.getRegistrations()).map(r => ({
      scope: r.scope.replace(location.origin, ''), installing: r.installing && r.installing.state,
      installed: r.installed && r.installed.state, waiting: r.waiting && r.waiting.state,
      activating: r.activating && r.activating.state, active: r.active && r.active.scriptURL.replace(location.origin, '') }));
    window.__cacheFacts = async () => {
      const keys = await caches.keys();
      const prec = keys.find(k => /^workbox-precache-v2-/.test(k)) || null;
      let urls = [], revisions = [];
      if (prec) {
        const ks = (await (await caches.open(prec)).keys()).map(r => r.url);
        urls = ks.map(u => u.replace(location.origin, '')).sort();
        revisions = ks.map(u => { try { return new URL(u).searchParams.get('__WB_REVISION__') || null; } catch (e) { return null; } }).sort();
      }
      return { keys: keys.slice().sort(), precacheName: prec, precacheUrls: urls, revisions };
    };
  });

  out.instrument.probeFunctionsInstalled = true;

  const servedBundle = async () => {
    const html = await (await page.request.get(BASE + '/')).text();
    const m = html.match(/assets\/(index-[\w-]+\.js)/);
    return m && m[1];
  };
  const servedWorker = async () => {
    const r = await page.request.get(BASE + '/v10-sw.js');
    const buf = await r.body();
    return { status: r.status(), bytes: buf.length, sha256: crypto.createHash('sha256').update(buf).digest('hex') };
  };
  const nav = async (label, phase) => {
    const t = Date.now();
    out.instrument.navEvents.push({ at: t, issuedByMe: true, label, phase });
    const r = await page.goto(BASE + '/v8/hub', { waitUntil: 'load', timeout: 45000 }).catch(e => ({ err: String(e.message).slice(0, 120) }));
    return { label, phase, httpStatus: r && r.status ? r.status() : null, err: r && r.err || null, at: t };
  };

  /* ================= P0: become a returning client on the OLD generation ================= */
  let t0 = Date.now();
  const rA = setRoot(GEN_A_DIR);
  out.phases.P0_setup = { root: rA, served_on_disk: await servedBundle(), worker_on_disk: await servedWorker() };
  out.phases.P0_setup.nav1 = await nav('P0-nav1 (install)', 'P0');
  await sleep(15000);
  out.phases.P0_setup.nav2 = await nav('P0-nav2 (take-control)', 'P0');   // a SW controls the SECOND navigation
  await sleep(12000);
  out.phases.P0_setup.precondition = await probe(page);
  out.phases.P0_setup.precondition_navigations_issued = 2;
  await page.screenshot({ path: path.join(SHOTS, 'o274_' + RUN + '_P0_old_gen.png') }).catch(() => 0);

  /* ================= P1: redeploy the OTHER generation, then a network cycle ================= */
  t0 = Date.now();
  const rB = setRoot(GEN_B_DIR);
  out.phases.P1_transition = { root: rB, served_on_disk_now: await servedBundle(), worker_on_disk_now: await servedWorker(),
    note: 'the browser is not told anything; only the disk root behind the same origin moved' };
  await ctx.setOffline(true); await sleep(6000);
  out.phases.P1_transition.offline_sample = await probe(page);
  await ctx.setOffline(false); await sleep(4000);
  out.phases.P1_transition.back_online_sample = await probe(page);

  /* ================= B1: the ONE normal navigation the contract allows ================= */
  t0 = Date.now();
  const beforeB1 = await probe(page);
  out.phases.B1 = { navigations_issued_in_this_cell: [], docNonce_before: beforeB1.docNonce,
    scripts_before: beforeB1.scripts, samples: [] };
  out.phases.B1.navigations_issued_in_this_cell.push(await nav('B1-the-one-navigation', 'B1'));
  for (const at of [3000, 8000, 15000, 25000, 40000, 60000]) {
    while (Date.now() - t0 < at) await sleep(500);
    const p = await probe(page);
    out.phases.B1.samples.push({ atMs: Date.now() - t0, docNonce: p.docNonce, scripts: p.scripts,
      controller: p.controller, controllerScript: p.controllerScript, registrations: p.registrations,
      caches: p.caches && p.caches.precacheUrls ? { keys: p.caches.keys, precacheCount: p.caches.precacheUrls.length,
        precacheName: p.caches.precacheName, revisions: p.caches.revisions } : null,
      lifecycle: p.lifecycle, href: p.href, chromeError: p.chromeError, bodyChars: p.bodyChars,
      headings: p.headings, measured: p.measured, probeError: p.probeError || null });
    if (at === 60000) await page.screenshot({ path: path.join(SHOTS, 'o274_' + RUN + '_B1_end.png') }).catch(() => 0);
  }
  out.phases.B1.lifecycle_after_window = (out.phases.B1.samples[out.phases.B1.samples.length - 1].lifecycle || []);
  out.phases.B1.nav_events_during_cell = out.instrument.navEvents.filter(e => e.at >= t0);

  /* ================= B2: does it converge without me touching it again? ================= */
  out.phases.B2 = { extra_manual_actions_taken: 0, samples_after_60s: [] };
  let t1 = Date.now();
  while (Date.now() - t1 < 60000) {
    await sleep(5000);
    const p = await probe(page);
    out.phases.B2.samples_after_60s.push({ atMs: Date.now() - t1, docNonce: p.docNonce, scripts: p.scripts,
      controllerScript: p.controllerScript, registrations: p.registrations, measured: p.measured });
  }
  const b2_final_before_help = await probe(page);
  out.phases.B2.executed_scripts_before_any_help = b2_final_before_help.scripts;
  out.phases.B2.doc_nonce_changed_without_my_navigation =
    b2_final_before_help.docNonce !== out.phases.B1.docNonce_before;
  if (!(b2_final_before_help.scripts || []).some(s => s.includes(out.generations.B_new.bundle))) {
    out.phases.B2.recovery_costly = { needed_a_second_manual_navigation: true };
    out.phases.B2.extra_manual_actions_taken = 1;
    await nav('B2-EXTRA-manual-navigation (RECOVERY_COSTLY)', 'B2');
    await sleep(12000);
    const p2 = await probe(page);
    out.phases.B2.after_extra_navigation = { docNonce: p2.docNonce, scripts: p2.scripts,
      controllerScript: p2.controllerScript, registrations: p2.registrations, caches: p2.caches };
    await page.screenshot({ path: path.join(SHOTS, 'o274_' + RUN + '_B2_after_extra_nav.png') }).catch(() => 0);
  } else {
    out.phases.B2.recovery_costly = { needed_a_second_manual_navigation: false };
  }

  /* ================= B3: offline again, one normal navigation ================= */
  t0 = Date.now();
  out.phases.B3 = { offline_before: true, samples: [] };
  await ctx.setOffline(true); await sleep(3000);
  out.phases.B3.nav = await nav('B3-one-navigation-while-offline', 'B3');
  for (const at of [3000, 10000, 20000]) {
    while (Date.now() - t0 < at) await sleep(500);
    const p = await probe(page);
    out.phases.B3.samples.push({ atMs: Date.now() - t0, href: p.href, chromeError: p.chromeError,
      scripts: p.scripts, css: p.css, controller: p.controller, controllerScript: p.controllerScript,
      registrations: p.registrations, caches: p.caches, bodyChars: p.bodyChars, headings: p.headings,
      lifecycle: p.lifecycle, measured: p.measured });
  }
  await page.screenshot({ path: path.join(SHOTS, 'o274_' + RUN + '_B3_offline.png') }).catch(() => 0);
  // can the traveller still move around inside the served generation?
  const navTest = await page.evaluate(() => {
    const cands = [...document.querySelectorAll('[data-testid^="nav-"], a[href*="/v8/"]')].filter(e => {
      const r = e.getBoundingClientRect(); return r.width > 2 && r.height > 2;
    }).map(e => ({ tag: e.tagName, testid: e.getAttribute('data-testid'), href: e.getAttribute('href'), txt: (e.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 12) }));
    return { candidates: cands.slice(0, 8) };
  });
  out.phases.B3.nav_test = navTest;
  if (navTest.candidates.length) {
    const el = page.locator('[data-testid^="nav-"]').first();
    const box = await el.boundingBox().catch(() => null);
    if (box) {
      const hit = await page.evaluate(([x, y]) => { const e = document.elementFromPoint(x, y); return e ? { tag: e.tagName, testid: e.getAttribute('data-testid') } : null; }, [box.x + box.width / 2, box.y + box.height / 2]);
      await page.touchscreen.tap(box.x + box.width / 2, box.y + box.height / 2);
      await sleep(5000);
      const after = await probe(page);
      out.phases.B3.in_app_navigation = { tappedBox: box, elementAtPoint: hit, pathname_after: after.pathname,
        scripts_after: after.scripts, bodyChars: after.bodyChars, navigated: after.pathname !== out.phases.B3.samples[2].pathname };
    }
  }
  await ctx.setOffline(false);

  out.instrument.navEventsFinal = out.instrument.navEvents;
  out.ended_at = new Date().toISOString();
  fs.writeFileSync(path.join(__dirname, 'o274_campaign_' + RUN + '.json'), JSON.stringify(out, null, 2));
  console.log(JSON.stringify({ run: RUN, gens: out.generations,
    P0_precond: out.phases.P0_setup.precondition && { scripts: out.phases.P0_setup.precondition.scripts, controller: out.phases.P0_setup.precondition.controller, precache: out.phases.P0_setup.precondition.caches && out.phases.P0_setup.precondition.caches.precacheUrls.length },
    B1_last: (() => { const s = out.phases.B1.samples[out.phases.B1.samples.length - 1]; return { scripts: s.scripts, controllerScript: s.controllerScript, regs: s.registrations, precacheCount: s.caches && s.caches.precacheCount, chromeError: s.chromeError, bodyChars: s.bodyChars }; })(),
    B1_first: (() => { const s = out.phases.B1.samples[0]; return { scripts: s.scripts, controller: s.controller, regs: s.registrations }; })(),
    B2_nonce_changed: out.phases.B2.doc_nonce_changed_without_my_navigation,
    B2: { before_help: out.phases.B2.executed_scripts_before_any_help, recovery: out.phases.B2.recovery_costly, after: out.phases.B2.after_extra_navigation && out.phases.B2.after_extra_navigation.scripts },
    B3_last: (() => { const s = out.phases.B3.samples[out.phases.B3.samples.length - 1]; return { scripts: s.scripts, css: s.css, controllerScript: s.controllerScript, precacheCount: s.caches && s.caches.precacheUrls.length, chromeError: s.chromeError, bodyChars: s.bodyChars }; })(),
    B3_nav: out.phases.B3.in_app_navigation || null,
    pageErrors: out.instrument.pageErrors.slice(0, 4), navCount_total: out.instrument.navEvents.length }, null, 2));
  await ctx.close().catch(() => 0);
})().catch(e => {
  out.fatal = String(e && e.message || e).split('\n')[0].slice(0, 300);
  try { fs.writeFileSync(path.join(__dirname, 'o274_campaign_' + RUN + '.json'), JSON.stringify(out, null, 2)); } catch (_) { }
  console.log(JSON.stringify({ fatal: out.fatal }, null, 2));
  process.exit(1);
});
