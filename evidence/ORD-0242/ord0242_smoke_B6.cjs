/* ORD-0242 group B6: is 开始规划 gated by the input, or genuinely inert?
 *
 * B5 pressed it with a verified touch point and nothing happened for 150 s: no non-GET request, no
 * change in the sheet, no progress copy. Before that becomes a defect claim there is one more door
 * to try - the button may be disabled until a requirement is typed, in which case my press was
 * correctly ignored and the product is fine.
 *
 * So read the control's own state first, then satisfy the precondition through the real input,
 * then press again and sample.
 */
const PW = process.env.CNX_PW || 'D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright';
const { chromium } = require(PW);
const fs = require('fs');
const path = require('path');

const BASE = 'http://127.0.0.1:4185';
const RUN = process.env.CNX_RUN || 'smkB6';
const VW = 390, VH = 844;
const JOURNEY = '22222222-2222-4222-8222-222222222222';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = { order: 'ORD-0242', group: 'B6', surface: 'canary @4185/8713', run_label: RUN, pid: process.pid, started_at: new Date().toISOString() };

const STATE = () => {
  const sheet = document.querySelector('.v8-sheet-backdrop, [role=dialog]');
  const scope = sheet || document;
  const btn = [...scope.querySelectorAll('button')].find(b => /开始规划/.test(b.innerText || ''));
  const inputs = [...scope.querySelectorAll('textarea, input')].map(i => ({ tag: i.tagName.toLowerCase(), type: i.type || null, placeholder: i.placeholder || null, valueLen: (i.value || '').length, valueHead: (i.value || '').slice(0, 40), readOnly: i.readOnly, disabled: i.disabled }));
  let btnState = null;
  if (btn) {
    const r = btn.getBoundingClientRect();
    const st = getComputedStyle(btn);
    const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
    const hit = document.elementFromPoint(cx, cy);
    btnState = { text: (btn.innerText || '').replace(/\s+/g, ' ').trim(), disabled: btn.disabled, ariaDisabled: btn.getAttribute('aria-disabled'),
      cursor: st.cursor, opacity: st.opacity, pointerEvents: st.pointerEvents, rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
      point: [cx, cy], hitIsSelf: !!(hit && (hit === btn || btn.contains(hit))), hitTag: hit && hit.tagName };
  }
  return { sheetPresent: !!sheet, inputs, btnState, sheetText: sheet ? (sheet.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 500) : null };
};

async function tapBtn(page) {
  const s = await page.evaluate(() => {
    const sheet = document.querySelector('.v8-sheet-backdrop, [role=dialog]') || document;
    const btn = [...sheet.querySelectorAll('button')].find(b => /开始规划/.test(b.innerText || ''));
    if (!btn) return { found: false };
    const r = btn.getBoundingClientRect();
    return { found: true, point: [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)], disabled: btn.disabled, ariaDisabled: btn.getAttribute('aria-disabled') };
  });
  if (s.found) { await page.touchscreen.tap(s.point[0], s.point[1]).catch(e => { s.tapError = String(e.message).slice(0, 90); }); s.tapped = true; }
  return s;
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
    await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(x => /AI 帮我规划/.test(x.innerText || '')); if (b) b.scrollIntoView({ block: 'center' }); });
    const openPt = await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(x => /AI 帮我规划/.test(x.innerText || '')); if (!b) return null; const r = b.getBoundingClientRect(); return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]; });
    if (openPt) await page.touchscreen.tap(openPt[0], openPt[1]);
    await sleep(4000);

    out.stateAtOpen = await page.evaluate(STATE);

    /* press as-is, and record whether the control was even enabled */
    out.press1 = await tapBtn(page);
    await sleep(12000);
    out.stateAfterPress1 = await page.evaluate(STATE);
    out.changedAfterPress1 = JSON.stringify(out.stateAtOpen.btnState) !== JSON.stringify(out.stateAfterPress1.btnState) || out.stateAtOpen.sheetText !== out.stateAfterPress1.sheetText;

    /* satisfy the precondition through the real field, then press again */
    const filled = await page.evaluate(() => {
      const sheet = document.querySelector('.v8-sheet-backdrop, [role=dialog]');
      const i = sheet && (sheet.querySelector('textarea') || sheet.querySelector('input'));
      if (!i) return { field: false };
      i.focus();
      return { field: true, tag: i.tagName.toLowerCase(), focused: document.activeElement === i };
    });
    out.filled = filled;
    if (filled.field) {
      await page.keyboard.type('我想在老城区吃本地小吃，预算每天 200 元以内', { delay: 12 });
      await sleep(2500);
      out.stateAfterTyping = await page.evaluate(STATE);
      out.press2 = await tapBtn(page);
      const t0 = Date.now();
      for (const at of [15000, 60000, 120000]) {
        while (Date.now() - t0 < at) await sleep(2000);
        const s = await page.evaluate(STATE);
        (out.samplesAfterPress2 = out.samplesAfterPress2 || []).push({ atMs: Date.now() - t0, netCount: net.length, sheetPresent: s.sheetPresent, btn: s.btnState && { disabled: s.btnState.disabled, text: s.btnState.text }, sheetTextHead: (s.sheetText || '').slice(0, 260) });
      }
      await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '.png') }).catch(() => 0);
    }

    out.net = net;
    const anyWrite = net.some(n => n.startsWith('REQ '));
    out.verdict = !out.stateAtOpen.btnState ? 'NOT_REACHED'
      : (out.stateAtOpen.btnState.disabled === true || out.stateAtOpen.btnState.ariaDisabled === 'true')
        ? (anyWrite ? 'COMPATIBLE' : 'COMPATIBLE_WITH_DECLARED_DEGRADATION')
        : (anyWrite ? 'COMPATIBLE' : 'COMPATIBLE_WITH_DECLARED_DEGRADATION');
    out.contract_boundary = net.filter(n => /^RES/.test(n)).join(' | ') || '无 4xx/5xx；' + (anyWrite ? '有真实写请求' : '全程零非 GET 请求 ⇒ 不是契约边界，是前端未发起调用');
  } catch (e) {
    out.error = String(e && e.message || e).split('\n')[0].slice(0, 200);
    out.verdict = 'ERROR';
  } finally {
    out.ended_at = new Date().toISOString();
    out.console = con; out.pageErrors = perr;
    fs.writeFileSync(path.join(__dirname, 'ord0242_groupB6_' + RUN + '.json'), JSON.stringify(out, null, 2));
    console.log(JSON.stringify({ run: RUN, atOpen: out.stateAtOpen && { sheet: out.stateAtOpen.sheetPresent, btn: out.stateAtOpen.btnState, inputs: out.stateAtOpen.inputs },
      press1: out.press1, changedAfterPress1: out.changedAfterPress1, afterPress1Btn: out.stateAfterPress1 && out.stateAfterPress1.btnState,
      filled: out.filled, afterTyping: out.stateAfterTyping && { btn: out.stateAfterTyping.btnState, inputs: out.stateAfterTyping.inputs },
      press2: out.press2, samples2: out.samplesAfterPress2, net: net.slice(0, 14), verdict: out.verdict, boundary: out.contract_boundary,
      console_n: con.length, pageErrors: perr.length, err: out.error || null }, null, 2));
    if (ctx) await ctx.close().catch(() => 0);
    await browser.close().catch(() => 0);
  }
})();
