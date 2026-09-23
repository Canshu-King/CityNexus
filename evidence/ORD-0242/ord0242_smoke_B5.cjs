/* ORD-0242 group B5: what does the screen actually say after 开始规划, sampled at fixed times.
 *
 * B4 reached the sheet and pressed 开始规划 with a verified touch point, then reported noSample -
 * because its "still working" test included the ellipsis character, and the page is full of
 * truncated text, so the loop never settled and never kept a sample. Meanwhile its request log
 * shows 22 entries and not one of them is a non-GET, which is the interesting part: a planning
 * action that talks to the model should produce a request.
 *
 * So: no inference. Press it, then read the screen at t=10/40/90/150 s and keep every sample plus
 * the complete request list. Whatever the answer is, it comes from rendered text and a named URL.
 */
const PW = process.env.CNX_PW || 'D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright';
const { chromium } = require(PW);
const fs = require('fs');
const path = require('path');

const BASE = 'http://127.0.0.1:4185';
const RUN = process.env.CNX_RUN || 'smkB5';
const VW = 390, VH = 844;
const JOURNEY = '22222222-2222-4222-8222-222222222222';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = { order: 'ORD-0242', group: 'B5', surface: 'canary @4185/8713', run_label: RUN, pid: process.pid, started_at: new Date().toISOString(), samples: [] };

const READ = () => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight; };
  const txt = s => (s || '').replace(/\s+/g, ' ').trim();
  const sheet = document.querySelector('.v8-sheet-backdrop, [role=dialog]');
  return { url: location.pathname,
    h1: [...document.querySelectorAll('h1')].filter(vis).map(x => txt(x.innerText)).find(t => t.length) || null,
    sheetPresent: !!sheet,
    sheetText: sheet ? txt(sheet.innerText).slice(0, 700) : null,
    sheetButtons: sheet ? [...sheet.querySelectorAll('button')].filter(vis).map(b => txt(b.innerText).slice(0, 26)).filter(Boolean).slice(0, 20) : null,
    body: txt(document.body.innerText).slice(0, 1300),
    buttons: [...document.querySelectorAll('button')].filter(vis).map(b => txt(b.innerText).slice(0, 26)).filter(Boolean).slice(0, 34) };
};

async function tapText(page, rx) {
  const probe = await page.evaluate((src) => {
    const re = new RegExp(src, 'i');
    const inVP = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.left >= 0 && r.right <= innerWidth && r.top >= 0; };
    const scope = document.querySelector('.v8-sheet-backdrop, [role=dialog]') || document;
    const b = [...scope.querySelectorAll('button,a')].find(x => re.test(x.innerText || '') && inVP(x));
    if (!b) return { found: false, candidates: [...scope.querySelectorAll('button,a')].filter(inVP).map(x => (x.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 20)).filter(Boolean).slice(0, 18) };
    const r = b.getBoundingClientRect();
    const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
    const hit = document.elementFromPoint(cx, cy);
    return { found: true, label: (b.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 28), point: [cx, cy], hitTag: hit && hit.tagName, pointHitsThisButton: !!(hit && (hit === b || b.contains(hit))) };
  }, rx);
  if (probe.found && probe.pointHitsThisButton) {
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
    page.on('request', r => { const u = r.url(); if (u.includes('/api/')) net.push({ t: 'req', m: r.method(), u: u.replace(BASE, '').split('?')[0] }); });
    page.on('response', r => { const u = r.url(); if (u.includes('/api/')) net.push({ t: 'res', m: r.request().method(), u: u.replace(BASE, '').split('?')[0], s: r.status() }); });
    page.on('console', m => con.push(m.type() + ': ' + String(m.text()).slice(0, 200)));
    page.on('pageerror', e => perr.push(String(e.message).slice(0, 200)));

    await page.goto(BASE + '/v8/hub', { waitUntil: 'load', timeout: 60000 });
    await sleep(9000);
    out.openTap = await tapText(page, 'AI 帮我规划');
    await sleep(4000);
    out.sheetAtOpen = await page.evaluate(READ);
    out.startTap = await tapText(page, '开始规划');
    const t0 = Date.now();
    for (const at of [10000, 40000, 90000, 150000]) {
      while (Date.now() - t0 < at) await sleep(2000);
      const s = await page.evaluate(READ);
      out.samples.push({ atMs: Date.now() - t0, netCount: net.length, ...s });
      await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '_' + at + '.png') }).catch(() => 0);
    }

    const nonGet = net.filter(n => n.t === 'req' && n.m !== 'GET');
    const bad = net.filter(n => n.t === 'res' && n.s >= 400);
    out.requestSummary = { total: net.length, nonGet: nonGet.map(n => n.m + ' ' + n.u), named4xx5xx: bad.map(n => n.s + ' ' + n.m + ' ' + n.u),
      distinctPaths: [...new Set(net.filter(n => n.t === 'req').map(n => n.m + ' ' + n.u))].slice(0, 20) };
    const last = out.samples[out.samples.length - 1];
    out.verdict = !out.startTap.tappedByTouch ? 'NOT_REACHED'
      : (bad.length ? 'INCOMPATIBLE_BACKEND_CONTRACT'
        : (nonGet.length === 0 ? 'COMPATIBLE_WITH_DECLARED_DEGRADATION' : 'COMPATIBLE'));
    out.contract_boundary = bad.length ? '有具名 4xx/5xx：' + bad.map(n => n.s + ' ' + n.u).join(' | ')
      : (nonGet.length === 0 ? '不是契约边界：没有任何后端调用可失败 —— 面板打开了、按钮点得动，但「开始规划」一次请求都没发出去' : '有真实调用且无 4xx/5xx');
    out.whatTheScreenSaid = last ? { atMs: last.atMs, sheetPresent: last.sheetPresent, sheetText: last.sheetText, sheetButtons: last.sheetButtons, h1: last.h1 } : null;
  } catch (e) {
    out.error = String(e && e.message || e).split('\n')[0].slice(0, 200);
    out.verdict = 'ERROR';
  } finally {
    out.ended_at = new Date().toISOString();
    out.net = net; out.console = con; out.pageErrors = perr;
    fs.writeFileSync(path.join(__dirname, 'ord0242_groupB5_' + RUN + '.json'), JSON.stringify(out, null, 2));
    console.log(JSON.stringify({ run: RUN, open: out.openTap && { ok: out.openTap.pointHitsThisButton, tapped: out.openTap.tappedByTouch },
      start: out.startTap && { label: out.startTap.label, point: out.startTap.point, ok: out.startTap.pointHitsThisButton, tapped: out.startTap.tappedByTouch, candidates: out.startTap.candidates },
      samples: (out.samples || []).map(s => ({ at: s.atMs, net: s.netCount, sheet: s.sheetPresent, sheetBtns: (s.sheetButtons || []).slice(0, 6), sheetTextHead: (s.sheetText || '').slice(0, 90) })),
      req: out.requestSummary, verdict: out.verdict, boundary: out.contract_boundary, console_n: con.length, pageErrors: perr.length, err: out.error || null }, null, 2));
    if (ctx) await ctx.close().catch(() => 0);
    await browser.close().catch(() => 0);
  }
})();
