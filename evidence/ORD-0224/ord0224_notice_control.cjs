/* ORD-0224 side finding, attribution control.
 *
 * The gesture probe's final screenshot shows 「底图未加载，显示的是路线示意。」 while 17 OSM raster
 * tiles answered 200, and the same reading taken BEFORE any gesture returned null. Two things
 * could explain that: the gestures I performed caused it, or it simply appears later on its own.
 *
 * This control does everything the probe does except dispatch a single touch event, waits at
 * least as long as a full gesture run, then reads the same notice and the same tile tally.
 *   notice absent here + notice present there  ->  the gesture path owns it
 *   notice present here too                    ->  it is a timing/tiling issue, not my gestures
 */
const PW = process.env.CNX_PW || 'D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright';
const { chromium } = require(PW);
const fs = require('fs');
const path = require('path');

const BASE = process.env.CNX_BASE || 'http://127.0.0.1:8792';
const RUN = process.env.CNX_RUN || 'noticect';
const WAIT = Number(process.env.CNX_WAIT_MS || 22000);
const VW = 390, VH = 844;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const localIso = d => { const o = -d.getTimezoneOffset(), s = o >= 0 ? '+' : '-', p = n => String(n).padStart(2, '0'); return new Date(d.getTime() + o * 60000).toISOString().replace('Z', '') + s + p(Math.floor(Math.abs(o) / 60)) + ':' + p(Math.abs(o) % 60); };
const out = { base: BASE, run_label: RUN, pid: process.pid, wait_ms: WAIT, touchesDispatched: 0, started_at: localIso(new Date()) };

(async () => {
  const browser = await chromium.launch({ headless: true });
  let ctx = null, page = null;
  const offOrigin = [];
  try {
    ctx = await browser.newContext({ viewport: { width: VW, height: VH }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
    await ctx.addInitScript(([id]) => { try { localStorage.setItem('citynexus.v8.journey_id', id); } catch (e) {} }, [process.env.CNX_JOURNEY || '']);
    page = await ctx.newPage();
    page.on('response', r => { const u = r.url(); if (!u.startsWith(BASE)) offOrigin.push(r.status() + ' ' + u.slice(0, 110)); });
    page.on('requestfailed', r => { const u = r.url(); if (!u.startsWith(BASE)) offOrigin.push('FAILED ' + (r.failure() && r.failure().errorText) + ' ' + u.slice(0, 100)); });
    const writes = [];
    page.on('request', r => { if (r.method() !== 'GET' && r.url().includes('/api/')) writes.push(r.method() + ' ' + r.url()); });

    await page.goto(BASE + '/v8/hub', { waitUntil: 'load', timeout: 45000 });

    const readNotice = () => page.evaluate(() => {
      const n = [...document.querySelectorAll('*')].find(e => /底图/.test(e.textContent || '') && e.children.length === 0);
      const host = document.querySelector('.v8-map-panel');
      const cv = host && host.querySelector('canvas');
      const m = window.__cnxMap;
      return {
        present: !!n,
        text: n ? n.textContent.trim().slice(0, 70) : null,
        visible: n ? n.offsetParent !== null : null,
        scrollTop: document.scrollingElement.scrollTop,
        zoom: m ? m.getZoom() : null,
        canvasBox: cv ? (r => [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)])(cv.getBoundingClientRect()) : null,
      };
    });

    const samples = [];
    const t0 = Date.now();
    for (let i = 0; Date.now() - t0 < WAIT; i++) {
      await sleep(2500);
      const s = await readNotice();
      samples.push({ atMs: Date.now() - t0, raster200: offOrigin.filter(u => /^200 https:\/\/tile\./.test(u)).length, failed: offOrigin.filter(u => /^FAILED/.test(u)).length, notice: s });
    }
    out.samples = samples;
    out.writes = writes;
    out.tileOutcome = { raster200: offOrigin.filter(u => /^200 https:\/\/tile\./.test(u)).length, failed: offOrigin.filter(u => /^FAILED/.test(u)).length, offOriginTotal: offOrigin.length };
    await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0224_' + RUN + '.png') }).catch(() => 0);

    const anyNotice = samples.some(s => s.notice.present);
    out.verdict = anyNotice
      ? 'NOTICE_APPEARS_WITHOUT_ANY_TOUCH: 「底图未加载」在零触摸的静置等待里也出现了 → 与手势无关，属瓦片批次/时序判定，不能记在我这一轮的手势路径上'
      : 'NOTICE_ONLY_AFTER_GESTURES: 静置 ' + (WAIT / 1000) + 's、' + out.tileOutcome.raster200 + ' 张底图瓦片 200，屏上始终没有「底图未加载」→ 它是手势之后才出现的，归因指向地图手势路径';
  } catch (e) {
    out.error = String(e && e.message || e).split('\n')[0].slice(0, 200);
    out.verdict = 'ERROR';
  } finally {
    out.ended_at = localIso(new Date());
    out.offOriginRequests = offOrigin.slice(0, 40);
    fs.writeFileSync(path.join(__dirname, 'ord0224_notice_' + RUN + '.json'), JSON.stringify(out, null, 2));
    console.log(JSON.stringify({
      run: RUN, samples: out.samples && out.samples.map(s => s.atMs + 'ms raster200=' + s.raster200 + ' failed=' + s.failed + ' notice=' + (s.notice.present ? 'YES' : 'no')),
      tiles: out.tileOutcome, writes: out.writes, verdict: out.verdict, err: out.error || null,
    }, null, 2));
    if (ctx) await ctx.close().catch(() => 0);
    await browser.close().catch(() => 0);
  }
})();
