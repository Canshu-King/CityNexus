/* ORD-0274 B2, split per arbiter Q19(iii): three arms, one variable each.
 *
 *   fixed_idle     installed gen = d82eb16 (carries the controllerchange fix), dirty wizard,
 *                  no write in flight            -> B2a convergence + B2b field preservation
 *   unfixed_idle   installed gen = c79e2b4f (no fix), same everything else
 *                  -> B2a's 反控: the assertions must be able to fail
 *   fixed_inflight installed gen = d82eb16, a non-idempotent trip write held unsettled by my
 *                  own origin at the moment the new generation is discovered
 *                  -> B2c: no reload that cuts a write in half; convergence after the write
 *                     reaches its terminal state, still without a second user navigation
 *
 * Hard rules honoured: 0 unregister, 0 cache clear, 0 demo/reset, nothing seeded but what this
 * walk itself types.  The only edits to the measured trees are two marker lines in my own
 * exports (window.__cnxVerifierGenerationMarker), which let me read "which generation's code is
 * running" instead of inferring it from a filename.
 */
const PW = process.env.CNX_PW || 'D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright';
const { chromium } = require(PW);
const fs = require('fs');
const path = require('path');

const BASE = process.env.CNX_BASE;
const RUN = process.env.CNX_RUN || 'b2';
const ARM = process.env.CNX_ARM;
const PROFILE = process.env.CNX_PROFILE;
const ROOT_A = process.env.CNX_ROOT_A;
const ROOT_B = process.env.CNX_ROOT_B;
const POINTER = process.env.CNX_POINTER;
const MODEFILE = process.env.CNX_MODEFILE;
const SHOTS = process.env.CNX_SHOTS || __dirname;
const WRITE_MODE = process.env.CNX_WRITE_MODE || 'answer';
const INSTALL_MODE = process.env.CNX_INSTALL_MODE || 'two_navigations';
const DRAFT_KEY = 'citynexus.v8.trial_draft';
const WATCH_MS = 45000;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const setPointer = p => { fs.writeFileSync(POINTER, p, 'utf8'); return { root: path.basename(p), ok: fs.readFileSync(POINTER, 'utf8').trim() === p }; };
const setMode = m => { fs.writeFileSync(MODEFILE, m, 'utf8'); return { written: m, readBack: fs.readFileSync(MODEFILE, 'utf8').trim() }; };

const out = { order: 'ORD-0274', cell: 'B2 (Q19 iii)', arm: RUN, arm_kind: ARM, session: '1a986a24 HJ-P1',
  base: BASE, started_at: new Date().toISOString(), viewport: [390, 844], draft_key: DRAFT_KEY,
  install_mode: INSTALL_MODE, write_mode: WRITE_MODE,
  forbidden_moves_taken: { unregister_called: 0, cache_clear_called: 0 }, phases: {}, instrument: { pageErrors: [], navEvents: [] } };


/* the snapshot that runs in the page lives in SNAP_SOURCE below - one copy, serialised by
   page.evaluate, so the pre-action and post-action readings cannot drift apart */

(async () => {
  fs.rmSync(PROFILE, { recursive: true, force: true });
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    headless: true, viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
    isMobile: true, hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = ctx.pages()[0] || await ctx.newPage();
  page.on('pageerror', e => out.instrument.pageErrors.push(String(e.message).slice(0, 200)));
  out.instrument.apiEvents = [];
  page.on('request', r => { if (r.url().includes('/api/')) out.instrument.apiEvents.push({ atEpoch: Date.now(), ev: 'request', m: r.method(), p: new URL(r.url()).pathname }); });
  page.on('response', r => { if (r.url().includes('/api/')) out.instrument.apiEvents.push({ atEpoch: Date.now(), ev: 'response', m: r.request().method(), p: new URL(r.url()).pathname, s: r.status() }); });
  page.on('requestfailed', r => { if (r.url().includes('/api/')) out.instrument.apiEvents.push({ atEpoch: Date.now(), ev: 'requestfailed', m: r.method(), p: new URL(r.url()).pathname, why: String((r.failure() || {}).errorText || '').slice(0, 40) }); });
  page.on('framenavigated', f => { if (f === page.mainFrame()) out.instrument.navEvents.push({ at: Date.now(), href: f.url(), mine: false }); });
  await ctx.addInitScript(() => {
    const ev = window.__b2Events = [];
    const push = (n, x) => ev.push(Object.assign({ ev: n, t: Math.round(performance.now()), href: location.href }, x || {}));
    push('document-start', { marker: window.__cnxVerifierGenerationMarker || null });
    if (navigator.serviceWorker) {
      navigator.serviceWorker.addEventListener('controllerchange', () =>
        push('controllerchange', { script: navigator.serviceWorker.controller && navigator.serviceWorker.controller.scriptURL }));
      navigator.serviceWorker.getRegistration().then(r => {
        if (!r) return push('no-registration');
        const track = (w, who) => { if (!w) return; w.addEventListener('statechange', () => push('state:' + who, { state: w.state, script: w.scriptURL })); };
        track(r.installing, 'installing'); track(r.waiting, 'waiting'); track(r.active, 'active');
        r.addEventListener('updatefound', () => { push('updatefound'); track(r.installing, 'installing'); track(r.waiting, 'waiting'); });
      }).catch(() => 0);
    }
  });
  const snap = async () => {
    const s = await page.evaluate(SNAP_SOURCE);
    s.registrations = await page.evaluate(async () => (await navigator.serviceWorker.getRegistrations()).map(r => ({
      scope: r.scope.replace(location.origin, ''), installing: r.installing && r.installing.state,
      waiting: r.waiting && r.waiting.state, active: r.active && r.active.scriptURL.replace(location.origin, '') })));
    return s;
  };
  const tap = async (src) => {
    const p = await page.evaluate(([s]) => {
      const re = new RegExp(s, 'i');
      const vis = e => { const r = e.getBoundingClientRect(); return r.width > 2 && r.height > 2 && e.offsetParent !== null; };
      const b = [...document.querySelectorAll('button,a,[role=button]')].filter(vis).find(x => re.test((x.innerText || '').replace(/\s+/g, ' ').trim()));
      if (!b) return { found: false, onScreen: [...document.querySelectorAll('button')].filter(vis).map(x => (x.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 18)).filter(Boolean).slice(0, 14) };
      b.scrollIntoView({ block: 'center' });
      const r = b.getBoundingClientRect(); const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
      const hit = document.elementFromPoint(cx, cy);
      return { found: true, label: (b.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 24), disabled: !!b.disabled,
        point: [cx, cy], hitIsSelf: !!(hit && (hit === b || b.contains(hit))) };
    }, [src]);
    if (p.found && p.hitIsSelf && !p.disabled) { await page.touchscreen.tap(p.point[0], p.point[1]); p.tapped = true; }
    return p;
  };
  const goto = async (label) => {
    out.instrument.navEvents.push({ at: Date.now(), mine: true, label });
    const r = await page.goto(BASE + '/v8/hub', { waitUntil: 'load', timeout: 45000 }).catch(e => null);
    return { label, at: Date.now(), status: r && r.status ? r.status() : null };
  };

  /* ---------- P0: become a returning client on the installed generation ---------- */
  out.phases.P0 = { pointer: setPointer(ROOT_A), mode: setMode('answer'), install_mode: INSTALL_MODE };
  out.phases.P0.nav1 = await goto('P0-nav1-install'); await sleep(15000);
  if (INSTALL_MODE === 'two_navigations') {
    out.phases.P0.nav2 = await goto('P0-nav2-take-control'); await sleep(12000);
    out.phases.P0.navigations_used = 2;
  } else {
    /* ORD-0290 B2b shape: the document must be CLAIMED during its own lifetime, not controlled at
       birth.  Two navigations would hand it a controller from the start, which is the very thing the
       B2b defect excluded - so here we stay on the installing document and wait for the claim. */
    out.phases.P0.claim_wait = [];
    for (const at of [2000, 5000, 9000, 14000, 20000]) {
      while (Date.now() - out.phases.P0.nav1.at < at) await sleep(400);
      const sn = await snap();
      out.phases.P0.claim_wait.push({ atMs: at, controller: sn.controller, marker: sn.marker,
                                      registrations: sn.registrations, lifecycle: sn.lifecycle.slice(-4) });
      if (sn.controller) break;
    }
    out.phases.P0.navigations_used = 1;
  }
  out.phases.P0.snapshot = await snap();
  await page.screenshot({ path: path.join(SHOTS, 'b2_' + RUN + '_P0.png') }).catch(() => 0);

  /* ---------- P1: type a named draft and PROVE each step was actually reached ----------
     Lesson from arm 1: my first version enumerated the visible inputs once and then filled by
     that stale index list, so "arrival" and "departure" both landed on the same field, the
     trip's departure stayed empty, and the wizard correctly refused 下一步.  Both of my taps
     looked like successes (hitIsSelf + tapped) while draft.step never left 1.  Every fill now
     re-enumerates at call time, and every 下一步 is checked against what the product itself
     says - the 「还需要填写」 hint and the step recorded in its own durable draft. */
  const TYPED = { city: '北京', arrival: '北京南站', departure: '北京西站',
    startAt: '2026-10-05T09:30', endAt: '2026-10-07T18:00',
    budget: '480', stay: '150', special: '只看免费和便宜的地方' };
  out.phases.P1 = { typed: TYPED, fills: [], stepChecks: [] };
  const SEL2 = 'input, textarea';

  const fillMatching = async (needle, value, why) => {
    const got = await page.evaluate(([sel, rxSrc]) => {
      const re = new RegExp(rxSrc, 'i');
      const list = [...document.querySelectorAll(sel)].filter(e => {
        const r = e.getBoundingClientRect();
        return r.width > 2 && r.height > 2 && !e.disabled && e.type !== 'hidden';
      });
      for (let i = 0; i < list.length; i++) {
        const e = list[i];
        if ((e.value || '').length) continue;
        const hay = [e.placeholder, e.name, e.getAttribute('aria-label'),
          (e.closest('label') || {}).innerText].filter(Boolean).join(' ');
        if (re.test(hay)) return { i, ph: e.placeholder || null, type: e.type };
      }
      return null;
    }, [SEL2, needle]);
    if (!got) { out.phases.P1.fills.push({ why, skipped: 'no empty visible field matched', needle }); return null; }
    const loc = page.locator(SEL2).nth(got.i);
    await loc.scrollIntoViewIfNeeded().catch(() => 0);
    await loc.click({ timeout: 8000 }).catch(() => 0);
    await loc.fill(String(value)).catch(() => 0);
    await sleep(600);
    const after = await page.evaluate(([sel, i]) => {
      const l = [...document.querySelectorAll(sel)].filter(e => {
        const r = e.getBoundingClientRect(); return r.width > 2 && r.height > 2;
      });
      return l[i] ? { len: (l[i].value || '').length, value: l[i].value } : null;
    }, [SEL2, got.i]);
    out.phases.P1.fills.push({ why, idx: got.i, ph: got.ph, wrote: String(value).length, after });
    return after;
  };

  const nthOfType = async (tf, k, value, why) => {
    const handle = await page.evaluateHandle(([sel, t, i]) => {
      const l = [...document.querySelectorAll(sel)].filter(e => {
        const r = e.getBoundingClientRect();
        return r.width > 2 && r.height > 2 && e.type === t;
      });
      return l[i] || null;
    }, [SEL2, tf, k]);
    const el = handle.asElement();
    if (!el) { out.phases.P1.fills.push({ why, skipped: 'no ' + tf + ' input at index ' + k }); return null; }
    const before = await el.evaluate(n => n.value).catch(() => null);
    await el.scrollIntoViewIfNeeded().catch(() => 0);
    await el.fill(String(value)).catch(() => 0);
    await sleep(600);
    const after = await el.evaluate(n => ({ len: (n.value || '').length, value: n.value })).catch(() => null);
    out.phases.P1.fills.push({ why, type: tf, idx: k, before, wrote: String(value).length, after });
    return after;
  };

  const stepCheck = async (label) => {
    const sn = await snap();
    const missing = (sn.headings || []).filter(h => /还需要填写|请填写|请输入/.test(h));
    const rec = { label, draft_step: sn.draft ? sn.draft.step : null, missing_hint: missing,
      fieldCount: Object.keys(sn.fields || {}).length, marker: sn.marker,
      headings: (sn.headings || []).slice(0, 6) };
    out.phases.P1.stepChecks.push(rec);
    return rec;
  };

  await fillMatching('天津|东京|新加坡|城市', TYPED.city, 'city');
  await fillMatching('站|机场|某地', TYPED.arrival, 'arrival');
  await fillMatching('站|机场|某地', TYPED.departure, 'departure');
  await nthOfType('datetime-local', 0, TYPED.startAt, 'startAt');
  await nthOfType('datetime-local', 1, TYPED.endAt, 'endAt');
  out.phases.P1.afterStep1 = await stepCheck('before first 下一步');

  out.next1 = await tap('下一步');
  await sleep(3500);
  const sc2 = await stepCheck('after first 下一步');
  if (sc2.draft_step !== 2)
    out.arm_invalid_reason = 'step 2 not reached (draft.step=' + sc2.draft_step +
      ', hint=' + JSON.stringify(sc2.missing_hint) + ')';

  out.phases.P1.step2Fields = await page.evaluate(([sel]) => [...document.querySelectorAll(sel)]
    .filter(e => { const r = e.getBoundingClientRect(); return r.width > 2 && r.height > 2; })
    .map(e => ({ tag: e.tagName, type: e.type, ph: e.placeholder || null, value: e.value })), [SEL2]);
  out.phases.P1.step2Buttons = await page.evaluate(() => [...document.querySelectorAll('button')]
    .filter(b => { const r = b.getBoundingClientRect(); return r.width > 2 && r.height > 2; })
    .map(b => (b.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 12)).filter(Boolean));

  await fillMatching('住宿', TYPED.stay, 'stayBudget');
  await fillMatching('总预算|预算', TYPED.budget, 'budget');
  await fillMatching('特殊|要求|备注', TYPED.special, 'specialRequirements');

  const plusHandle = await page.evaluateHandle(() => {
    const host = [...document.querySelectorAll('div,section,fieldset')].find(e =>
      /人数/.test(e.innerText || '') && (e.innerText || '').replace(/\s+/g, ' ').length < 80);
    if (!host) return null;
    return [...host.querySelectorAll('button')].find(b => /^\+|增加/.test((b.innerText || '').trim())) || null;
  });
  const plusEl = plusHandle && plusHandle.asElement ? plusHandle.asElement() : null;
  if (plusEl) {
    const beforeParty = await page.evaluate(() => {
      try { return JSON.parse(localStorage.getItem('citynexus.v8.trial_draft') || 'null'); } catch (e) { return null; }
    });
    await plusEl.click({ timeout: 6000 }).catch(() => 0);
    await sleep(900);
    const afterParty = await page.evaluate(() => {
      try { return JSON.parse(localStorage.getItem('citynexus.v8.trial_draft') || 'null'); } catch (e) { return null; }
    });
    out.phases.P1.partyStepper = { clicked: true,
      partySize_before: beforeParty && beforeParty.draft && beforeParty.draft.partySize,
      partySize_after: afterParty && afterParty.draft && afterParty.draft.partySize };
  } else {
    out.phases.P1.partyStepper = { clicked: false };
  }

  out.next2 = await tap('下一步');
  await sleep(3500);
  const sc3 = await stepCheck('after second 下一步');
  out.phases.P2 = { snapshot: await snap(), confirm_box: await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find(x => /确认创建/.test((x.innerText || '').replace(/\s+/g, ' ')));
    if (!b) return null;
    const r = b.getBoundingClientRect();
    return r.width > 2 && r.height > 2 ? [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)] : null;
  }) };
  if (sc3.draft_step !== 3 && !out.phases.P2.confirm_box)
    out.arm_invalid_reason = (out.arm_invalid_reason ? out.arm_invalid_reason + ' | ' : '') +
      'step 3 not reached (draft.step=' + sc3.draft_step + ', hint=' + JSON.stringify(sc3.missing_hint) + ')';
  await page.screenshot({ path: path.join(SHOTS, 'b2_' + RUN + '_P2_step3.png') }).catch(() => 0);

  /* ---------- P3: the transition, then the ONE action the contract allows ---------- */
  out.phases.P3 = { pointer: setPointer(ROOT_B) };
  if (ARM === 'fixed_inflight') {
    out.phases.P3.mode = setMode(WRITE_MODE);
    out.phases.P3.submit = await tap('确认创建|创建行程');
    await sleep(4000);
    out.phases.P3.during_write = await snap();
    out.phases.P3.update_trigger = await page.evaluate(async () => {
      const r = await navigator.serviceWorker.getRegistration();
      if (!r) return { updated: false, why: 'no registration' };
      try { await r.update(); return { updated: true, via: 'registration.update() while the trip write is unsettled' }; }
      catch (e) { return { updated: false, why: String(e.message).slice(0, 80) }; }
    });
  } else if (ARM === 'b2b_claimed') {
    /* B2b shape: no navigation at all from here. The document was uncontrolled when it registered,
       got claimed during its own lifetime, and must now converge on a generation change that lands
       while it is still open - so the only action is the one the worker takes, never a second hop
       that would hand me a freshly controlled document and hide the defect. */
    out.phases.P3.mode = setMode('answer');
    out.phases.P3.update_trigger = await page.evaluate(async () => {
      const r = await navigator.serviceWorker.getRegistration();
      if (!r) return { updated: false, why: 'no registration' };
      await r.update();
      return { updated: true, via: 'registration.update() on a document claimed during its own lifetime' };
    });
  } else {
    out.phases.P3.mode = setMode('answer');
    await ctx.setOffline(true); await sleep(6000);
    await ctx.setOffline(false); await sleep(4000);
  }
  const before = await snap();
  out.phases.P3.before_action = { marker: before.marker, scripts: before.scripts, docNonce: before.docNonce,
    fields: before.fields, draft: before.draft, leafCount: before.leafCount, registrations: before.registrations };
  if (ARM !== 'fixed_inflight' && ARM !== 'b2b_claimed')
    out.phases.P3.the_one_navigation = await goto('B2-the-one-navigation');
  else out.phases.P3.the_one_navigation = { skipped: 'arm drives no navigation: ' + ARM };
  out.phases.P3.watch = [];
  const t0 = Date.now();
  out.phases.P3.watch_started_at_epoch = t0;
  while (Date.now() - t0 < WATCH_MS) {
    await sleep(4000);
    const s = await snap();
    out.phases.P3.watch.push({ atMs: Date.now() - t0, atEpoch: Date.now(), marker: s.marker, scripts: s.scripts, docNonce: s.docNonce,
      registrations: s.registrations, controller: s.controller, leafCount: s.leafCount,
      headings: s.headings, fieldCount: s.fieldCount, draft_present: !!s.draft,
      lifecycle: s.lifecycle.slice(-6) });
    if (ARM === 'fixed_inflight' && s.marker === 'ORD-0274-next') { out.phases.P3.converged_atMs = Date.now() - t0; break; }
  }
  out.phases.P3.after = await snap();
  await page.screenshot({ path: path.join(SHOTS, 'b2_' + RUN + '_P3_after.png') }).catch(() => 0);
  out.phases.P3.after_written = JSON.parse(JSON.stringify({ marker: out.phases.P3.after.marker,
    scripts: out.phases.P3.after.scripts, docNonce: out.phases.P3.after.docNonce,
    fields: out.phases.P3.after.fields, draft: out.phases.P3.after.draft, headings: out.phases.P3.after.headings,
    registrations: out.phases.P3.after.registrations, leafCount: out.phases.P3.after.leafCount }));
  out.phases.P3.nav_events_total = out.instrument.navEvents.length;
  out.phases.P3.nav_events_mine = out.instrument.navEvents.filter(e => e.mine).map(e => e.label || 'goto');
  out.ended_at = new Date().toISOString();
  fs.writeFileSync(path.join(__dirname, 'b2_' + RUN + '.json'), JSON.stringify(out, null, 2));
  console.log(JSON.stringify({ arm: RUN, kind: ARM,
    P0: { marker: out.phases.P0.snapshot.marker, scripts: out.phases.P0.snapshot.scripts, controller: out.phases.P0.snapshot.controller },
    P1_fills: out.phases.P1.fills, next1: !!out.next1.tapped, next2: !!out.next2.tapped,
    stepDots_before: out.phases.P3.before_action.leafCount,
    watch: out.phases.P3.watch.map(w => ({ t: w.atMs, marker: w.marker, bundle: (w.scripts.join(',').match(/index-[\w-]+\.js/) || [])[0], nonce: w.docNonce.slice(0, 5), draft: w.draft_present })),
    P3: { navs_mine: out.phases.P3.nav_events_mine, trigger: out.phases.P3.update_trigger,
      after_marker: out.phases.P3.after_written.marker, after_scripts: out.phases.P3.after_written.scripts,
      after_nonce: out.phases.P3.after_written.docNonce, before_nonce: out.phases.P3.before_action.docNonce },
    fields_now: Object.keys(out.phases.P3.after_written.fields || {}).length,
    pageErrors: out.instrument.pageErrors.slice(0, 3) }, null, 2));
  await ctx.close().catch(() => 0);
})().catch(e => {
  out.fatal = String(e && e.message || e).split('\n')[0].slice(0, 300);
  try { fs.writeFileSync(path.join(__dirname, 'b2_' + RUN + '.json'), JSON.stringify(out, null, 2)); } catch (_) { }
  console.log(JSON.stringify({ fatal: out.fatal }, null, 2));
  process.exit(1);
});

/* the snapshot function, as source, so addInitScript and evaluate share one copy */
const SNAP_SOURCE = () => {
  const short = u => String(u || '').replace(location.origin, '');
  const vis = e => { const r = e.getBoundingClientRect(), st = getComputedStyle(e);
    return r.width > 2 && r.height > 2 && st.display !== 'none' && st.visibility !== 'hidden'; };
  const fields = {};
  [...document.querySelectorAll('input,textarea,select')].filter(vis).forEach((el, i) => {
    const lab = (el.closest('label') || {}).innerText
      || (el.id && document.querySelector('label[for="' + el.id + '"]') || {}).innerText
      || el.getAttribute('aria-label') || el.placeholder || ('#' + i);
    const key = String(lab).replace(/\s+/g, ' ').trim().slice(0, 24);
    fields[key + (key in fields ? '[' + i + ']' : '')] = { tag: el.tagName, type: el.type, value: el.value };
  });
  let draft = null, draftError = null;
  try { draft = JSON.parse(localStorage.getItem('citynexus.v8.trial_draft') || 'null'); } catch (e) { draftError = String(e.message).slice(0, 60); }
  const leaf = [...document.querySelectorAll('body *')].filter(e => e.children.length === 0 && vis(e))
    .map(e => (e.innerText || '').replace(/\s+/g, ' ').trim()).filter(Boolean);
  return { href: location.href, marker: window.__cnxVerifierGenerationMarker || null,
    scripts: [...document.querySelectorAll('script[src]')].map(s => short(s.getAttribute('src'))),
    docNonce: (window.__b2Nonce = window.__b2Nonce || Math.random().toString(36).slice(2)),
    fields: fields, fieldCount: Object.keys(fields).length, draft: draft, draftError: draftError,
    headings: leaf.slice(0, 8), leafCount: leaf.length,
    controller: !!(navigator.serviceWorker && navigator.serviceWorker.controller),
    registrations: [], lifecycle: (window.__b2Events || []).slice(-30) };
};
