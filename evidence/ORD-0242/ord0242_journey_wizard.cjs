/* ORD-0242 follow-up: walk the Journey wizard properly, since I filed that face as degraded
 * precisely because I had not walked 新建→生成→方案列表.
 *
 * Two things are learned here rather than assumed:
 *  - what step 1 actually contains on THIS build (the deployed generation differs from the one I
 *    walked on my own stack last night, and a fresh profile with an ACTIVE scene boots into the
 *    shell, so the only create entry is 试用其他城市);
 *  - which destinations the app itself offers, because inventing a city to get variety is a truth
 *    defect, not a test shortcut.
 *
 * The pass dumps every control it finds at each step before touching anything, then advances with
 * verified touch taps and records every request. Creating a journey writes to _compat.db, the
 * canary copy; nothing here may reach :4781/:4782/:8693 or _live.db.
 */
const PW = process.env.CNX_PW || 'D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright';
const { chromium } = require(PW);
const fs = require('fs');
const path = require('path');

const BASE = 'http://127.0.0.1:4185';
const RUN = process.env.CNX_RUN || 'wiz1';
const VW = 390, VH = 844;
const JOURNEY = '22222222-2222-4222-8222-222222222222';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = { order: 'ORD-0242', part: 'journey-wizard', surface: 'canary @4185/8713', run_label: RUN, pid: process.pid, writes_expected: true, started_at: new Date().toISOString(), steps: [] };

const DUMP = () => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight && r.left < innerWidth && r.right > 0; };
  const txt = s => (s || '').replace(/\s+/g, ' ').trim();
  const idOf = e => { const r = e.getBoundingClientRect(); return e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.className ? '.' + String(e.className).trim().split(/\s+/)[0] : '') + '@' + Math.round(r.x) + ',' + Math.round(r.y) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height); };
  return {
    url: location.pathname,
    h1: [...document.querySelectorAll('h1,h2')].filter(vis).map(e => txt(e.innerText)).filter(Boolean).slice(0, 4),
    steps: [...document.querySelectorAll('.v8-wizard-step, [data-step], li')].filter(vis).map(e => txt(e.innerText).slice(0, 24)).filter(Boolean).slice(0, 8),
    labels: [...document.querySelectorAll('label,legend,.v8-field-label,h3')].filter(vis).map(e => txt(e.innerText).slice(0, 30)).filter(Boolean).slice(0, 20),
    inputs: [...document.querySelectorAll('input,textarea,select')].filter(vis).map(i => ({ id: i.id || null, name: i.name || null, type: i.type || i.tagName.toLowerCase(), placeholder: i.placeholder || null, valueLen: (i.value || '').length, valueHead: (i.value || '').slice(0, 30), required: i.required || i.getAttribute('aria-required') === 'true', disabled: !!i.disabled })),
    buttons: [...document.querySelectorAll('button')].filter(vis).map(b => ({ t: txt(b.innerText).slice(0, 26), disabled: !!b.disabled, aria: b.getAttribute('aria-disabled'), id: b.id || null, cls: String(b.className || '').trim().split(/\s+/)[0], box: (() => { const r = b.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; })() })).filter(x => x.t),
    chips: [...document.querySelectorAll('[role=option], [role=listbox] *, .v8-suggestion, .v8-chip, .v8-city-option')].filter(vis).map(e => txt(e.innerText).slice(0, 26)).filter(Boolean).slice(0, 30),
    body: txt(document.body.innerText).slice(0, 1400),
  };
};

async function tapLabel(page, rx, opts) {
  const probe = await page.evaluate(([src, opt]) => {
    const re = new RegExp(src, 'i');
    const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight && r.left >= 0 && r.right <= innerWidth; };
    const pool = [...document.querySelectorAll('button,a,[role=button],li,option')];
    const b = pool.find(x => re.test((x.innerText || '') + ' ' + (x.id || '')) && vis(x) && !(opt && opt.skipDisabled && (x.disabled || x.getAttribute('aria-disabled') === 'true')));
    if (!b) return { found: false, candidates: pool.filter(vis).map(x => (x.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 20)).filter(Boolean).slice(0, 20) };
    b.scrollIntoView({ block: 'center' });
    const r = b.getBoundingClientRect();
    const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
    const hit = document.elementFromPoint(cx, cy);
    return { found: true, label: (b.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 26), disabled: !!b.disabled, point: [cx, cy], hitTag: hit && hit.tagName, hitCls: String((hit && hit.className) || '').trim().split(/\s+/)[0], pointHitsThisButton: !!(hit && (hit === b || b.contains(hit))) };
  }, [rx, opts || {}]);
  if (probe.found && probe.pointHitsThisButton && !probe.disabled) {
    await page.touchscreen.tap(probe.point[0], probe.point[1]).catch(e => { probe.tapError = String(e.message).slice(0, 90); });
    probe.tappedByTouch = true;
  }
  return probe;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  let ctx = null;
  const net = [], con = [], perr = [];
  try {
    ctx = await browser.newContext({ viewport: { width: VW, height: VH }, deviceScaleFactor: 3, isMobile: true, hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
    await ctx.addInitScript(([id]) => { try { localStorage.setItem('citynexus.v8.journey_id', id); } catch (e) {} }, [JOURNEY]);
    const page = await ctx.newPage();
    page.on('request', r => { const u = r.url(); if (u.includes('/api/') && r.method() !== 'GET') net.push('REQ ' + r.method() + ' ' + u.replace(BASE, '').split('?')[0]); });
    page.on('response', r => { const u = r.url(); if (u.includes('/api/') && r.status() >= 400) net.push('RES ' + r.status() + ' ' + r.request().method() + ' ' + u.replace(BASE, '').split('?')[0]); });
    page.on('console', m => con.push(m.type() + ': ' + String(m.text()).slice(0, 200)));
    page.on('pageerror', e => perr.push(String(e.message).slice(0, 200)));

    await page.goto(BASE + '/v8/hub', { waitUntil: 'load', timeout: 60000 });
    await sleep(9000);

    out.entry = await tapLabel(page, '试用其他城市');
    await sleep(6000);
    out.steps.push({ name: 'step1', dump: await page.evaluate(DUMP) });
    await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '_step1.png') }).catch(() => 0);

    /* destination: pick only from what the app itself offers on screen */
    const d1 = out.steps[0].dump;
    const offered = (d1.chips || []).concat((d1.buttons || []).map(b => b.t)).filter(Boolean);
    out.destinationsOffered = offered.slice(0, 30);

    const cityInput = await page.evaluate(() => {
      const i = [...document.querySelectorAll('input')].find(x => /城市|目的地|destination|city/i.test((x.placeholder || '') + ' ' + (x.name || '') + ' ' + (x.id || '')));
      if (!i) return null;
      const r = i.getBoundingClientRect();
      return { id: i.id || null, placeholder: i.placeholder || null, point: [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)] };
    });
    out.cityInput = cityInput;
    if (cityInput) {
      await page.touchscreen.tap(cityInput.point[0], cityInput.point[1]);
      await sleep(1500);
      await page.keyboard.type('北京', { delay: 30 });
      await sleep(4000);
      out.afterTypingCity = await page.evaluate(DUMP);
      await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '_city.png') }).catch(() => 0);
      const pick = await tapLabel(page, '北京');
      out.cityPick = pick;
      await sleep(3000);
    }

    out.steps.push({ name: 'step1_after_city', dump: await page.evaluate(DUMP) });
    const next1 = await tapLabel(page, '下一步', { skipDisabled: false });
    out.next1 = next1;
    await sleep(6000);
    out.steps.push({ name: 'step2', dump: await page.evaluate(DUMP) });
    await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '_step2.png') }).catch(() => 0);

    const next2 = await tapLabel(page, '下一步');
    out.next2 = next2;
    await sleep(6000);
    out.steps.push({ name: 'step3', dump: await page.evaluate(DUMP) });
    await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '_step3.png') }).catch(() => 0);

    out.confirm = await tapLabel(page, '确认创建');
    await sleep(9000);
    out.afterConfirm = await page.evaluate(DUMP);
    out.netAfterConfirm = net.slice();
    await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '_confirm.png') }).catch(() => 0);

    const gen = await tapLabel(page, '开始规划|生成方案|AI 帮我规划');
    out.genTap = gen;
    if (gen.tappedByTouch) {
      const t0 = Date.now();
      for (const at of [20000, 70000, 140000]) {
        while (Date.now() - t0 < at) await sleep(2000);
        (out.genSamples = out.genSamples || []).push({ atMs: Date.now() - t0, netCount: net.length, dump: await page.evaluate(DUMP) });
      }
    }
    out.net = net;
    out.httpNamed_4xx5xx = net.filter(n => /^RES [45]/.test(n));
    out.writesNamed = net.filter(n => n.startsWith('REQ '));
  } catch (e) {
    out.error = String(e && e.message || e).split('\n')[0].slice(0, 200);
  } finally {
    out.ended_at = new Date().toISOString();
    out.console = con; out.pageErrors = perr; out.netEvents = net;
    fs.writeFileSync(path.join(__dirname, 'ord0242_wizard_' + RUN + '.json'), JSON.stringify(out, null, 2));
    const brief = d => d ? { url: d.url, h1: d.h1, labels: (d.labels || []).slice(0, 8), inputs: (d.inputs || []).map(i => i.type + (i.placeholder ? '(' + i.placeholder.slice(0, 14) + ')' : '') + (i.required ? '*' : '')), buttons: (d.buttons || []).map(b => b.t + (b.disabled ? '[off]' : '')).slice(0, 12), chips: (d.chips || []).slice(0, 12) } : null;
    console.log(JSON.stringify({
      run: RUN, entry: out.entry && { label: out.entry.label, ok: out.entry.pointHitsThisButton, tapped: out.entry.tappedByTouch, candidates: (out.entry.candidates || []).slice(0, 10) },
      step1: brief(out.steps[0] && out.steps[0].dump), cityInput: out.cityInput, cityPick: out.cityPick && { ok: out.cityPick.pointHitsThisButton },
      step1b: brief(out.steps[1] && out.steps[1].dump), next1: out.next1 && { label: out.next1.label, ok: out.next1.pointHitsThisButton, tapped: out.next1.tappedByTouch, disabled: out.next1.disabled },
      step2: brief(out.steps[2] && out.steps[2].dump), next2: out.next2 && { label: out.next2.label, ok: out.next2.pointHitsThisButton, tapped: out.next2.tappedByTouch },
      step3: brief(out.steps[3] && out.steps[3].dump), confirm: out.confirm && { label: out.confirm.label, ok: out.confirm.pointHitsThisButton, tapped: out.confirm.tappedByTouch },
      afterConfirm: brief(out.afterConfirm && out.afterConfirm.dump), afterConfirmH1: out.afterConfirm && out.afterConfirm.h1,
      genTap: out.genTap && { label: out.genTap.label, ok: out.genTap.pointHitsThisButton, tapped: out.genTap.tappedByTouch },
      genSamples: (out.genSamples || []).map(s => ({ at: s.atMs, net: s.netCount, h1: s.dump.h1, buttons: (s.dump.buttons || []).map(b => b.t).slice(0, 8) })),
      writes: out.writesNamed, http4xx5xx: out.httpNamed_4xx5xx, net_n: net.length, console_n: con.length, pageErrors: perr.length, err: out.error || null,
    }, null, 2));
    if (ctx) await ctx.close().catch(() => 0);
    await browser.close().catch(() => 0);
  }
})();
