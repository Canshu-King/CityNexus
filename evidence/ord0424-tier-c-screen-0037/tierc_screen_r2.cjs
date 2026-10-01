/*  ORD-0424 tier-C screen evidence r2 - the walk extended to the two surfaces r1 never visited.
 *
 *  r1 walked the 34 `/v8/*` addresses and found no tier-1 fallback in what the browser paints. That number
 *  was only half the tree: 85 of the 112 tier-1 rows live in `frontend/src/main.tsx`, which is the
 *  `/legacy` shell (`main.tsx:1373` routes it to <LegacyApp />), and one lives inside the onboarding
 *  wizard that the `/v8` shell shows *before* a journey is selected. Walking neither and reporting zero
 *  would have been a vacuous negative, so this pass walks both, plus the wizard's own steps, and keeps the
 *  full painted corpus per state so any claim can be re-checked against the captured text.
 *
 *  Channels are kept apart on purpose: innerText and the paint attributes (title / placeholder / alt /
 *  aria-label) count as "on screen"; `data-*` is recorded separately because a stylesheet can print it and
 *  nothing here reads the stylesheet.
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require(process.env.CNX_PW || 'D:/moodle/_cnx_buildcheck_20260920/frontend/node_modules/playwright');

const BASE = process.env.CNX_BASE || 'http://localhost:4541';
const OUT = 'D:/moodle/_qoder_lane_S4_0926/work/ord0424';
const JOURNEY = process.env.CNX_JOURNEY || '';
const PANELS = JSON.parse(fs.readFileSync(path.join(OUT, 'panel_ids_r1.json'), 'utf8'));
const AGENDA = JSON.parse(fs.readFileSync(path.join(OUT, 'tier1_agenda_r2.json'), 'utf8'));

const grab = () => {
  const t = (el) => (el.innerText || '').replace(/\s+/g, ' ').trim();
  const attrs = {};
  for (const a of ['title', 'placeholder', 'alt', 'aria-label']) {
    const set = new Set();
    document.querySelectorAll('[' + a + ']').forEach((el) => {
      const v = el.getAttribute(a);
      if (v && v.trim()) set.add(v.trim());
    });
    attrs[a] = Array.from(set);
  }
  const data = {};
  document.querySelectorAll('*').forEach((el) => {
    for (const at of el.attributes) {
      if (at.name.indexOf('data-') !== 0 || !at.value.trim()) continue;
      if (!data[at.name]) data[at.name] = new Set();
      data[at.name].add(at.value.trim());
    }
  });
  const dataOut = {};
  for (const k in data) dataOut[k] = Array.from(data[k]).slice(0, 30);
  return {
    url: location.href, body: t(document.body), paint_attrs: attrs, data_attrs: dataOut,
    buttons: Array.from(document.querySelectorAll('button,a[role=button]')).map(t).filter(Boolean).slice(0, 160),
    inputs: Array.from(document.querySelectorAll('input,textarea,select')).map((i) => ({
      ph: i.getAttribute('placeholder') || '', value: (i.value || '').slice(0, 40), disabled: i.disabled })),
    nodes: document.querySelectorAll('*').length,
  };
};

(async () => {
  const browser = await chromium.launch({ args: ['--no-sandbox'], timeout: 120000 });
  const states = [];
  const errs = [];

  const push = (name, s, extra) => states.push(Object.assign({ state: name, walked_at: new Date().toISOString() }, s, extra || {}));
  const newPage = async (withJourney) => {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'zh-CN' });
    if (withJourney && JOURNEY) {
      await ctx.addInitScript((j) => { localStorage.setItem('citynexus.v8.journey_id', j); }, JOURNEY);
    } else {
      await ctx.addInitScript(() => { localStorage.clear(); }, null);
    }
    ctx.on('pageerror', (e) => errs.push('pageerror ' + String(e).slice(0, 160)));
    ctx.on('console', (m) => { if (m.type() === 'error') errs.push('console.error ' + m.text().slice(0, 160)); });
    return await ctx.newPage();
  };

  /* 1. the /v8 panel addresses */
  let page = await newPage(true);
  for (const p of PANELS) {
    const rec = { url: BASE + '/v8/' + p, error: null, http_status: null };
    try {
      const r = await page.goto(BASE + '/v8/' + p, { waitUntil: 'domcontentloaded', timeout: 45000 });
      rec.http_status = r ? r.status() : null;
      await page.waitForTimeout(1400);
      Object.assign(rec, await page.evaluate(grab));
    } catch (e) { rec.error = String(e).slice(0, 180); }
    push('v8:' + p, rec, { surface: 'v8', panel: p });
  }
  /* 2. the legacy shell, which is where 85 of the rows live */
  for (const l of ['/legacy', '/legacy/']) {
    const rec = { url: BASE + l, error: null, http_status: null };
    try {
      const r = await page.goto(rec.url, { waitUntil: 'domcontentloaded', timeout: 45000 });
      rec.http_status = r ? r.status() : null;
      await page.waitForTimeout(2200);
      Object.assign(rec, await page.evaluate(grab));
    } catch (e) { rec.error = String(e).slice(0, 180); }
    push('legacy' + l, rec, { surface: 'legacy' });
  }
  await page.context().close();

  /* 3. the onboarding wizard, walked by clicking its own controls with no journey selected */
  page = await newPage(false);
  await page.goto(BASE + '/v8/hub', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(1800);
  push('wizard:step1', await page.evaluate(grab), { surface: 'wizard' });
  await page.screenshot({ path: path.join(OUT, 'screen_wizard_step1_r1.png') });
  for (let step = 2; step <= 5; step++) {
    let moved = false, clicked = null, blocked = null;
    try {
      const city = page.locator('input').first();
      if (await city.count()) {
        const ph = await city.getAttribute('placeholder');
        if (ph === null || String(ph).indexOf('城市') >= 0 || String(ph).indexOf('city') >= 0) {
          await city.fill('厦门').catch(() => {});
        }
      }
      const next = page.getByRole('button', { name: /下一步|继续|确认|创建|Start|Next/i }).first();
      if (await next.count()) {
        blocked = await next.isDisabled().catch(() => null);
        if (blocked === false) { await next.click({ timeout: 8000 }); clicked = 'next'; moved = true; }
      }
    } catch (e) { clicked = 'error:' + String(e).slice(0, 80); }
    await page.waitForTimeout(1500);
    const s = await page.evaluate(grab);
    push('wizard:step' + step, s, { surface: 'wizard', clicked, was_disabled: blocked, moved });
    if (!moved) break;
  }
  await page.screenshot({ path: path.join(OUT, 'screen_wizard_last_r1.png') });
  await page.context().close();
  await browser.close();

  /* match every tier-1 literal against both channels */
  const paint = {}, datac = {};
  for (const s of states) {
    paint[s.state] = [s.body || ''].concat(...Object.keys(s.paint_attrs || {}).map((k) => s.paint_attrs[k]))
      .join(' || ');
    datac[s.state] = Object.keys(s.data_attrs || {}).map((k) => (k + ' ' + s.data_attrs[k].join(' '))).join(' || ');
  }
  const rows = [];
  for (const f of AGENDA.faces) {
    for (const r of f.rows) {
      let lit = String(r.literal);
      if (lit.length >= 2 && ((lit[0] === "'" && lit[lit.length - 1] === "'") || (lit[0] === '"' && lit[lit.length - 1] === '"'))) {
        lit = lit.slice(1, -1);
      }
      if (!lit) continue;
      const inPaint = states.filter((s) => paint[s.state].indexOf(lit) >= 0).map((s) => s.state);
      const inData = inPaint.length ? [] : states.filter((s) => datac[s.state].indexOf(lit) >= 0).map((s) => s.state);
      rows.push({ file: f.file, name: f.name, line: r.line, slot: r.slot, band: r.band, literal: lit,
        verdict: inPaint.length ? 'ON_SCREEN' : (inData.length ? 'DATA_ATTR_ONLY' : 'NOT_SEEN_IN_ANY_WALKED_STATE'),
        states_paint: inPaint.slice(0, 10), states_data_only: inData.slice(0, 10) });
    }
  }
  const tally = {};
  for (const r of rows) tally[r.verdict] = (tally[r.verdict] || 0) + 1;
  const byFile = {};
  for (const r of rows) {
    byFile[r.name] = byFile[r.name] || { rows: 0, ON_SCREEN: 0, DATA_ATTR_ONLY: 0, NOT_SEEN: 0 };
    byFile[r.name].rows += 1;
    byFile[r.name][r.verdict === 'NOT_SEEN_IN_ANY_WALKED_STATE' ? 'NOT_SEEN' : r.verdict] += 1;
  }
  fs.writeFileSync(path.join(OUT, 'tierc_screen_r2.json'), JSON.stringify({
    base: BASE, journey_id_used_to_pass_the_shell_gate: JOURNEY || null,
    viewport: '390 px 宽 × 844 px 高', locale: 'zh-CN',
    states_walked: states.length,
    states: states.map((s) => ({ state: s.state, http_status: s.http_status || null, nodes: s.nodes || 0,
      body_chars: (s.body || '').length, error: s.error || null, clicked: s.clicked || null,
      was_disabled: (s.was_disabled === undefined ? null : s.was_disabled), body_head: (s.body || '').slice(0, 260) })),
    pageerrors: errs.slice(0, 12),
    tier1_rows_checked: rows.length, tally, by_file: byFile, rows,
    corpora: states.map((s) => ({ state: s.state, paint: paint[s.state].slice(0, 60000),
      data: datac[s.state].slice(0, 20000) })),
  }, null, 1));
  console.log('states', states.length, 'rows', rows.length, JSON.stringify(tally));
})().catch((e) => { console.error('FATAL', e); process.exit(9); });
