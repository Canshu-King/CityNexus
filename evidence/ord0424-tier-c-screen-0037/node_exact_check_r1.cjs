/*  ORD-0424 causal arm - exact-node text check, not substring luck.
 *
 *  Takes a base URL and a list of literals and answers, for each, whether some element's OWN trimmed
 *  text equals it exactly (and which tag / testid carries it). A substring of a longer sentence is not
 *  evidence that a hardcoded string is what the traveller reads, so this refuses to count it.
 *  Also walks the attribute channel (title / placeholder / alt / aria-label) with the same equality rule.
 *
 *  CNX_BASE, CNX_PATH, CNX_LITERALS (JSON array), CNX_LABEL, CNX_SHOT (optional png name)
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require(process.env.CNX_PW || 'D:/moodle/_cnx_buildcheck_20260920/frontend/node_modules/playwright');

const BASE = process.env.CNX_BASE || 'http://localhost:4541';
const TARGET = process.env.CNX_PATH || '/legacy';
const LITERALS = JSON.parse(process.env.CNX_LITERALS || '[]');
const LABEL = process.env.CNX_LABEL || 'control';
const OUT = 'D:/moodle/_qoder_lane_S4_0926/work/ord0424';

(async () => {
  const browser = await chromium.launch({ args: ['--no-sandbox'], timeout: 120000 });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'zh-CN' });
  await ctx.addInitScript(() => { localStorage.clear(); }, null);
  const page = await ctx.newPage();
  const net = [];
  page.on('response', (r) => { if (r.url().indexOf('/api/') >= 0) net.push(r.status() + ' ' + r.request().method() + ' ' + r.url().replace(BASE, '')); });
  await page.goto(BASE + TARGET, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(3000);
  const res = [];
  for (const lit of LITERALS) {
    const hit = await page.evaluate((l) => {
      const exact = (t) => (t || '').replace(/\s+/g, ' ').trim() === l;
      const nodes = Array.from(document.querySelectorAll('body *')).filter((e) =>
        Array.from(e.childNodes).some((n) => n.nodeType === 3 && exact(n.textContent)));
      const attrHits = [];
      for (const a of ['title', 'placeholder', 'alt', 'aria-label']) {
        document.querySelectorAll('[' + a + ']').forEach((e) => { if (exact(e.getAttribute(a)) && attrHits.indexOf(a) < 0) attrHits.push(a); });
      }
      const dataHits = [];
      document.querySelectorAll('*').forEach((e) => {
        for (const at of e.attributes) if (at.name.indexOf('data-') === 0 && exact(at.value)) dataHits.push(at.name);
      });
      const bodyHas = (document.body.innerText || '').replace(/\s+/g, ' ').indexOf(l) >= 0;
      return {
        node_exact: nodes.length > 0,
        node_tags: Array.from(new Set(nodes.map((e) => e.tagName.toLowerCase() +
          (e.className ? '.' + String(e.className).split(' ')[0] : '')))).slice(0, 4),
        testids: Array.from(new Set(nodes.map((e) => e.closest('[data-testid]') ? e.closest('[data-testid]').getAttribute('data-testid') : null).filter(Boolean))).slice(0, 4),
        attr_exact: attrHits, data_exact: Array.from(new Set(dataHits)).slice(0, 4),
        substring_in_body: bodyHas,
      };
    }, lit);
    res.push({ literal: lit, label: LABEL, path: TARGET, ...hit });
  }
  const shot = process.env.CNX_SHOT;
  if (shot) await page.screenshot({ path: path.join(OUT, shot) });
  const body = await page.evaluate(() => (document.body.innerText || '').replace(/\s+/g, ' ').trim());
  await browser.close();
  const doc = { label: LABEL, base: BASE, path: TARGET, literals_checked: LITERALS.length,
    body_head: body.slice(0, 300), api_seen: net.slice(0, 6), results: res };
  const file = path.join(OUT, 'exact_' + LABEL + '_r1.json');
  fs.writeFileSync(file, JSON.stringify(doc, null, 1));
  console.log(LABEL, JSON.stringify(res.map((r) => [r.literal.slice(0, 28), r.node_exact, r.substring_in_body, r.data_exact.length > 0])));
})().catch((e) => { console.error('FATAL', e); process.exit(9); });
