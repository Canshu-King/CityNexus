/* ORD-0242 journey wizard, attempt 2: fill what step 1 actually requires.
 *
 * Wiz1 learned the shape and then did nothing: the "three step" wizard puts 目的地 plus TWO
 * required free-text fields (抵达地点 / 离开地点, placeholder 例如：某地站 / 机场) on page one, and my
 * destination lookup keyed on the word 城市 missed the field because its own placeholder reads
 * 例如：天津、东京、新加坡. Both 下一步 taps were therefore correctly refused - step1/step2/step3 dumps
 * came back identical and the run made zero requests and zero writes.
 *
 * This pass fills by placeholder, proves each field's value length changed, then advances and
 * reads every screen. City choice is 北京 on purpose: this order asks whether the new bundle's
 * create→generate→plan-list chain works against pinned 53fe8e8, while whether a given city has
 * catalog rows is ORD-0239's already-filed question and must not be blended into this verdict.
 */
const PW = process.env.CNX_PW || 'D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright';
const { chromium } = require(PW);
const fs = require('fs');
const path = require('path');

const BASE = 'http://127.0.0.1:4185';
const RUN = process.env.CNX_RUN || 'wiz2';
const VW = 390, VH = 844;
const JOURNEY = '22222222-2222-4222-8222-222222222222';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = { order: 'ORD-0242', part: 'journey-wizard-2', surface: 'canary @4185/8713', run_label: RUN, pid: process.pid, city_choice_reason: '北京 chosen because this order tests the create→generate→plan-list chain against pinned 53fe8e8; catalog coverage per city is ORD-0239', started_at: new Date().toISOString(), steps: [] };

const DUMP = () => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight && r.left < innerWidth && r.right > 0; };
  const txt = s => (s || '').replace(/\s+/g, ' ').trim();
  return {
    url: location.pathname,
    h1: [...document.querySelectorAll('h1,h2')].filter(vis).map(e => txt(e.innerText)).filter(Boolean).slice(0, 4),
    stepPills: [...document.querySelectorAll('li')].filter(vis).map(e => txt(e.innerText).slice(0, 16)).filter(Boolean).slice(0, 6),
    labels: [...document.querySelectorAll('label,legend,h3')].filter(vis).map(e => txt(e.innerText).slice(0, 26)).filter(Boolean).slice(0, 16),
    inputs: [...document.querySelectorAll('input,textarea,select')].filter(vis).map(i => ({ type: i.type || i.tagName.toLowerCase(), ph: i.placeholder || null, valueLen: (i.value || '').length, valueHead: (i.value || '').slice(0, 26), required: !!i.required, disabled: !!i.disabled })),
    buttons: [...document.querySelectorAll('button')].filter(vis).map(b => ({ t: txt(b.innerText).slice(0, 24), disabled: !!b.disabled, aria: b.getAttribute('aria-disabled') })).filter(x => x.t),
    body: txt(document.body.innerText).slice(0, 1500),
  };
};

async function tapLabel(page, rx) {
  const probe = await page.evaluate((src) => {
    const re = new RegExp(src, 'i');
    const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight && r.left >= 0 && r.right <= innerWidth; };
    const b = [...document.querySelectorAll('button,a,[role=button]')].find(x => re.test(x.innerText || '') && vis(x));
    if (!b) return { found: false, candidates: [...document.querySelectorAll('button')].filter(vis).map(x => (x.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 20)).filter(Boolean).slice(0, 16) };
    b.scrollIntoView({ block: 'center' });
    const r = b.getBoundingClientRect();
    const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
    const hit = document.elementFromPoint(cx, cy);
    return { found: true, label: (b.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 24), disabled: !!b.disabled, point: [cx, cy], hitTag: hit && hit.tagName, pointHitsThisButton: !!(hit && (hit === b || b.contains(hit))) };
  }, rx);
  if (probe.found && probe.pointHitsThisButton && !probe.disabled) {
    await page.touchscreen.tap(probe.point[0], probe.point[1]).catch(e => { probe.tapError = String(e.message).slice(0, 90); });
    probe.tappedByTouch = true;
  }
  return probe;
}

async function fillByPh(page, ph, value) {
  const loc = page.locator(`input[placeholder="${ph}"]`).first();
  const before = await page.evaluate(([p]) => { const i = document.querySelector(`input[placeholder="${p}"]`); return i ? (i.value || '').length : -1; }, [ph]);
  await loc.scrollIntoViewIfNeeded().catch(() => {});
  await loc.click({ timeout: 8000 }).catch(e => { });
  await loc.fill(value).catch(e => { });
  await sleep(1200);
  const after = await page.evaluate(([p]) => { const i = document.querySelector(`input[placeholder="${p}"]`); return i ? { len: (i.value || '').length, head: (i.value || '').slice(0, 26) } : null; }, [ph]);
  return { ph, beforeLen: before, after };
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

    out.fills = [
      await fillByPh(page, '例如：天津、东京、新加坡', '北京'),
    ];
    /* the station placeholders are rewritten once a destination exists (wiz2 measured
       例如：某地站 / 机场 -> 例如：北京站 / 机场), so address the two required fields by position */
    const SEL = 'input:not([type])';
    const fieldMap = await page.evaluate(([s]) => [...document.querySelectorAll(s)].filter(i => { const r = i.getBoundingClientRect(); return r.width > 0 && r.height > 0; }).map((i, n) => ({ n, ph: i.placeholder || null, req: !!i.required, len: (i.value || '').length })), [SEL]);
    out.textFieldsAfterDestination = fieldMap;
    out.textFieldsSelectorUsed = SEL;
    for (const idx of [1, 2]) {
      if (!fieldMap.find(f => f.n === idx)) continue;
      const meta = fieldMap.find(f => f.n === idx);
      const loc = page.locator(SEL).nth(idx);
      await loc.scrollIntoViewIfNeeded().catch(() => {});
      await loc.click({ timeout: 8000 }).catch(() => {});
      await loc.fill('北京南站').catch(() => {});
      await sleep(1000);
      out.fills.push({ idx, ph: meta.ph, htmlRequired: meta.req, afterLen: await page.evaluate(([s, i2]) => { const list = [...document.querySelectorAll(s)].filter(x => x.getBoundingClientRect().width > 0); return list[i2] ? (list[i2].value || '').length : -1; }, [SEL, idx]) });
    }
    out.stationFieldCount = fieldMap.filter(f => f.req).length;
    out.step1Filled = await page.evaluate(DUMP);
    await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '_filled.png') }).catch(() => 0);

    out.next1 = await tapLabel(page, '下一步');
    await sleep(6000);
    out.steps.push({ name: 'step2', dump: await page.evaluate(DUMP) });
    await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '_step2.png') }).catch(() => 0);

    out.next2 = await tapLabel(page, '下一步');
    await sleep(6000);
    out.steps.push({ name: 'step3', dump: await page.evaluate(DUMP) });
    await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '_step3.png') }).catch(() => 0);

    out.confirm = await tapLabel(page, '确认创建');
    await sleep(12000);
    out.afterConfirm = await page.evaluate(DUMP);
    await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '_confirm.png') }).catch(() => 0);

    out.gen = await tapLabel(page, '开始规划|生成方案|AI 帮我规划');
    if (gen_tapped(out)) {
      const t0 = Date.now();
      for (const at of [20000, 80000, 150000]) {
        while (Date.now() - t0 < at) await sleep(2000);
        (out.genSamples = out.genSamples || []).push({ atMs: Date.now() - t0, netCount: net.length, dump: await page.evaluate(DUMP) });
      }
    }
    await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '_gen.png') }).catch(() => 0);
    out.httpNamed_4xx5xx = net.filter(n => /^RES [45]/.test(n));
    out.writesNamed = net.filter(n => n.startsWith('REQ '));
  } catch (e) {
    out.error = String(e && e.message || e).split('\n')[0].slice(0, 200);
  } finally {
    out.ended_at = new Date().toISOString();
    out.netEvents = net; out.console = con; out.pageErrors = perr;
    fs.writeFileSync(path.join(__dirname, 'ord0242_wizard_' + RUN + '.json'), JSON.stringify(out, null, 2));
    const brief = d => d ? { url: d.url, h1: d.h1, pills: d.stepPills, labels: (d.labels || []).slice(0, 8), inputs: (d.inputs || []).map(i => i.type + (i.ph ? '(' + i.ph.slice(0, 12) + ')' : '') + (i.required ? '*' : '') + '=' + i.valueLen), buttons: (d.buttons || []).map(b => b.t + (b.disabled ? '[off]' : '')).slice(0, 14) } : null;
    console.log(JSON.stringify({ run: RUN, entry: out.entry && { ok: out.entry.pointHitsThisButton, tapped: out.entry.tappedByTouch },
      fills: out.fills, stationFields: out.stationFieldCount, step1Filled: brief(out.step1Filled),
      next1: out.next1 && { ok: out.next1.pointHitsThisButton, tapped: out.next1.tappedByTouch },
      steps: (out.steps || []).slice(1).map(s => ({ n: s.name, ...brief(s.dump) })),
      next2: out.next2 && { ok: out.next2.pointHitsThisButton, tapped: out.next2.tappedByTouch },
      confirm: out.confirm && { label: out.confirm.label, ok: out.confirm.pointHitsThisButton, tapped: out.confirm.tappedByTouch, candidates: (out.confirm.candidates || []).slice(0, 10) },
      afterConfirm: brief(out.afterConfirm), afterConfirmBodyHead: out.afterConfirm && (out.afterConfirm.body || '').slice(0, 260),
      gen: out.gen && { label: out.gen.label, ok: out.gen.pointHitsThisButton, tapped: out.gen.tappedByTouch },
      genSamples: (out.genSamples || []).map(s => ({ at: s.atMs, net: s.netCount, h1: s.dump.h1, buttons: (s.dump.buttons || []).map(b => b.t).slice(0, 10) })),
      writes: out.writesNamed, http4xx5xx: out.httpNamed_4xx5xx, net_n: net.length, console_n: con.length, pageErrors: perr.length, err: out.error || null }, null, 2));
    if (ctx) await ctx.close().catch(() => 0);
    await browser.close().catch(() => 0);
  }
})();

function gen_tapped(o) { return o.gen && o.gen.tappedByTouch; }
