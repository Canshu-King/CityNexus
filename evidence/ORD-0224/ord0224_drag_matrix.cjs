/* ORD-0224 follow-up: a CDP touch drag at (195,500) with dy=-320 scrolled the document 0->305,
 * but the mirror arm's drag at (195,179) with (-90,-60) did not scroll at all. Two variables
 * moved between those two readings, so neither is a conclusion. Hold one at a time and let the
 * machine say which one owns the difference. Whatever survives tells me how to re-arm the
 * mirror arm before the gesture contract is judged at all.
 */
const PW = process.env.CNX_PW || 'D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright';
const { chromium } = require(PW);
const fs = require('fs');
const path = require('path');

const BASE = process.env.CNX_BASE || 'http://127.0.0.1:8792';
const RUN = process.env.CNX_RUN || 'mtx';
const VW = 390, VH = 844;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const localIso = d => { const o = -d.getTimezoneOffset(), s = o >= 0 ? '+' : '-', p = n => String(n).padStart(2, '0'); return new Date(d.getTime() + o * 60000).toISOString().replace('Z', '') + s + p(Math.floor(Math.abs(o) / 60)) + ':' + p(Math.abs(o) % 60); };
const out = { base: BASE, run_label: RUN, pid: process.pid, started_at: localIso(new Date()), cells: [] };

(async () => {
  const browser = await chromium.launch({ headless: true });
  let ctx = null, page = null, cdp = null;
  try {
    ctx = await browser.newContext({ viewport: { width: VW, height: VH }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
    await ctx.addInitScript(([id]) => { try { localStorage.setItem('citynexus.v8.journey_id', id); } catch (e) {} }, [process.env.CNX_JOURNEY || '']);
    page = await ctx.newPage();
    cdp = await ctx.newCDPSession(page);
    await page.goto(BASE + '/v8/hub', { waitUntil: 'load', timeout: 45000 });
    await sleep(6000);

    const drag = async (x, y, dx, dy, steps) => {
      const pt = (type, tx, ty) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x: tx, y: ty, radiusX: 12, radiusY: 12, force: 1 }] });
      await pt('touchStart', x, y);
      for (let i = 1; i <= steps; i++) { await sleep(16); await pt('touchMove', x + (dx * i) / steps, y + (dy * i) / steps); }
      await sleep(60); await pt('touchEnd', 0, 0); await sleep(900);
    };
    const top = () => page.evaluate(() => document.scrollingElement.scrollTop);
    const hitAt = (x, y) => page.evaluate(([a, b]) => { const e = document.elementFromPoint(a, b); return e ? e.tagName.toLowerCase() + (e.className ? '.' + String(e.className).trim().split(/\s+/)[0] : '') : null; }, [x, y]);

    const cells = [
      { label: 'C1 head-of-page, long vertical', x: 195, y: 179, dx: 0, dy: -320, steps: 10 },
      { label: 'C2 mid-page, long vertical (diag1 control)', x: 195, y: 500, dx: 0, dy: -320, steps: 10 },
      { label: 'C3 head-of-page, small diagonal (mirror arm as shipped)', x: 195, y: 179, dx: -90, dy: -60, steps: 10 },
      { label: 'C4 mid-page, small diagonal', x: 195, y: 500, dx: -90, dy: -60, steps: 10 },
      { label: 'C5 head-of-page, same diagonal spread over more moves', x: 195, y: 179, dx: -90, dy: -60, steps: 24 },
      { label: 'D1 mid-page, vertical-dominant same spread (-60,-90)', x: 195, y: 500, dx: -60, dy: -90, steps: 10 },
      { label: 'D2 mid-page, short pure vertical (0,-60)', x: 195, y: 500, dx: 0, dy: -60, steps: 10 },
    ];

    for (const c of cells) {
      await page.evaluate(() => { document.scrollingElement.scrollTop = 0; });
      await sleep(400);
      const before = await top();
      const hit = await hitAt(c.x, c.y);
      await drag(c.x, c.y, c.dx, c.dy, c.steps);
      const after = await top();
      out.cells.push({ label: c.label, start: [c.x, c.y], disp: [c.dx, c.dy], steps: c.steps, hitElement: hit, scrollTop: [before, after], scrolled: after !== before });
    }

    const byLabel = {}; out.cells.forEach(c => { byLabel[c.label.slice(0, 2)] = c.scrolled; });
    out.verdict = (() => {
      const longWorks = byLabel.C1 || byLabel.C2, d1 = byLabel.D1, d2 = byLabel.D2;
      if (!longWorks) return 'LONG_VERTICAL_NO_LONGER_SCROLLS: 与 diag1/mtx1 不一致 → 两跑之间有变量移动，先归因再解释其他格';
      if (d2) return 'HORIZONTAL_COMPONENT_BLOCKS: 纯垂直 60px 能滚(D2=true) 而 (-90,-60) 不能(C3/C4=false) → 我上一轮说"位移幅度不足"是错的，真因是水平分量主导让浏览器不把它当纵向滚动候选';
      if (d1) return 'VERTICAL_THRESHOLD_BETWEEN_60_AND_90: 垂直主导的 -90 能滚(D1) 而纯垂直 -60 不能(D2) → 纵向滚动需要 60~90px 之间的垂直位移，(-90,-60) 的垂直分量不够';
      return 'TOTAL_DISPLACEMENT_OWNS_IT: 垂直主导 -90 与纯垂直 -60 都不能滚，只有 -320 能 → 该页面触摸滚动阈值在 90~320px 之间，与方向无关';
    })();
  } catch (e) {
    out.error = String(e && e.message || e).split('\n')[0].slice(0, 200);
    out.verdict = 'ERROR';
  } finally {
    out.ended_at = localIso(new Date());
    fs.writeFileSync(path.join(__dirname, 'ord0224_matrix_' + RUN + '.json'), JSON.stringify(out, null, 2));
    console.log(JSON.stringify({ run: RUN, cells: out.cells.map(c => c.label.slice(0, 2) + ' ' + c.hitElement + ' ' + c.scrollTop.join('->') + (c.scrolled ? ' SCROLL' : ' still')), verdict: out.verdict, err: out.error || null }, null, 2));
    if (ctx) await ctx.close().catch(() => 0);
    await browser.close().catch(() => 0);
  }
})();
