/* ORD-0242 group B2: Simulation and AI, with the verdict bound to arrival, not to a heading.
 *
 * B1 reported three greens it had not earned: its rule was "the page has an h1 or 60 characters",
 * and Today's heading never leaves, so a face that was never reached still read COMPATIBLE. It
 * also left the drawer open while trying to press 帮我规划, so the overlay ate the tap.
 *
 * This pass:
 *  - measures each drawer item's real rect and hit-tests before claiming it is pressable at 390px;
 *  - closes the drawer before touching anything behind it;
 *  - declares arrival only on copy that exists on that face and nowhere else (权威行程执行 for the
 *    Simulation surface, 需要改变什么 for the Copilot sheet), and says NOT_REACHED otherwise.
 */
const PW = process.env.CNX_PW || 'D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright';
const { chromium } = require(PW);
const fs = require('fs');
const path = require('path');

const BASE = 'http://127.0.0.1:4185';
const RUN = process.env.CNX_RUN || 'smkB2';
const VW = 390, VH = 844;
const JOURNEY = '22222222-2222-4222-8222-222222222222';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = { order: 'ORD-0242', group: 'B2', surface: 'canary @4185/8713', run_label: RUN, pid: process.pid, started_at: new Date().toISOString() };

const READ = () => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight; };
  const txt = s => (s || '').replace(/\s+/g, ' ').trim();
  return { url: location.pathname,
    h1: [...document.querySelectorAll('h1')].filter(vis).map(x => txt(x.innerText)).find(t => t.length) || null,
    body: txt(document.body.innerText).slice(0, 1200),
    buttons: [...document.querySelectorAll('button')].filter(vis).map(b => txt(b.innerText).slice(0, 26)).filter(Boolean).slice(0, 34) };
};

async function tapText(page, rx, requireInViewport) {
  const probe = await page.evaluate(([rxSrc, strict]) => {
    const re = new RegExp(rxSrc, 'i');
    const inVP = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight; };
    const hasBox = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    const pool = [...document.querySelectorAll('button,a')].filter(e => re.test(e.innerText || '') && (strict ? inVP(e) : hasBox(e)));
    if (!pool.length) return { found: false, test: strict ? 'inViewport' : 'hasBox', candidates: [...document.querySelectorAll('button,a')].filter(e => re.test(e.innerText || '')).map(e => { const r = e.getBoundingClientRect(); return (e.innerText || '').trim().slice(0, 18) + '@' + Math.round(r.x) + ',' + Math.round(r.y) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height); }).slice(0, 6) };
    const b = pool[0];
    b.scrollIntoView({ block: 'center' });
    const r = b.getBoundingClientRect();
    const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
    const hit = document.elementFromPoint(cx, cy);
    const ok = !!(hit && (hit === b || b.contains(hit)));
    return { found: true, label: (b.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 26), rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)], point: [cx, cy],
      inViewport: inVP(b), hitTag: hit && hit.tagName, hitCls: hit && String(hit.className || '').trim().split(/\s+/)[0], pointHitsThisButton: ok };
  }, [rx, !!requireInViewport]);
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
    page.on('request', r => { if (r.method() !== 'GET' && r.url().includes('/api/')) net.push('REQ ' + r.method() + ' ' + r.url().replace(BASE, '').split('?')[0]); });
    page.on('response', r => { const u = r.url(); if (u.includes('/api/') && r.status() >= 400) net.push('RES ' + r.status() + ' ' + r.request().method() + ' ' + u.replace(BASE, '').split('?')[0]); });
    page.on('console', m => con.push(m.type() + ': ' + String(m.text()).slice(0, 200)));
    page.on('pageerror', e => perr.push(String(e.message).slice(0, 200)));

    await page.goto(BASE + '/v8/hub', { waitUntil: 'load', timeout: 60000 });
    await sleep(9000);

    out.menuTap = await tapText(page, '菜单', true);
    await sleep(3500);

    /* Are the drawer rows actually pressable at 390px, or do they only have a box? */
    out.drawerGeometry = await page.evaluate(() => {
      const d = document.querySelector('#v8-nav-drawer');
      if (!d) return { present: false };
      const rows = [...d.querySelectorAll('button,a')].filter(e => (e.innerText || '').trim());
      return { present: true, count: rows.length,
        sample: rows.slice(0, 16).map(e => { const r = e.getBoundingClientRect(); return { t: (e.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 14), x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), inViewport: r.left >= 0 && r.right <= innerWidth, hitSelf: (() => { const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2); const hit = document.elementFromPoint(cx, cy); return !!(hit && (hit === e || e.contains(hit))); })() }; }),
        drawerRect: (() => { const r = d.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; })(),
        drawerPosition: getComputedStyle(d).position };
    });

    out.simTap = await tapText(page, '恢复与执行', false);
    await sleep(7000);
    out.simRead = await page.evaluate(READ);
    out.simReached = /权威行程执行/.test(out.simRead.body || '');
    out.simPanel = out.simReached ? await page.evaluate(() => {
      const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
      const acts = [...document.querySelectorAll('button')].filter(vis).map(b => (b.innerText || '').replace(/\s+/g, ' ').trim()).filter(Boolean);
      return { actionCount: acts.length, actions: acts.slice(0, 24) };
    }) : null;
    await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '_sim.png') }).catch(() => 0);

    /* close the drawer, then walk the AI surface. The AI button lives on Today only, and we are
       standing on the Simulation surface here, so go back first and prove we landed. */
    out.closeTap = await tapText(page, '关闭', false);
    await sleep(2500);
    out.backToToday = await tapText(page, '^今天$', true);
    await sleep(5000);
    out.todayAgain = await page.evaluate(READ);
    out.onToday = /还没休息|AI 帮我规划|今天/.test((out.todayAgain || {}).body || '') && out.todayAgain.url === '/v8/hub';
    out.behindDrawer = await page.evaluate(() => {
      const b = [...document.querySelectorAll('button')].find(x => /AI 帮我规划/.test(x.innerText || ''));
      if (!b) return { present: false };
      const r = b.getBoundingClientRect(); const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
      const hit = document.elementFromPoint(cx, cy);
      return { present: true, point: [cx, cy], hitTag: hit && hit.tagName, hitCls: hit && String(hit.className || '').trim().split(/\s+/)[0], drawerStillUp: !!document.querySelector('#v8-nav-drawer') && document.querySelector('#v8-nav-drawer').getBoundingClientRect().width > 0 };
    });
    out.aiTap = await tapText(page, 'AI 帮我规划', true);
    await sleep(5000);
    out.aiSheet = await page.evaluate(READ);
    out.aiSheetReached = /需要改变什么|询问 Copilot/.test(out.aiSheet.body || '');

    if (out.aiSheetReached) {
      out.askTap = await tapText(page, '为什么这样安排|多待 60 分钟|找附近的室内地点', true);
      if (out.askTap.tappedByTouch) {
        await sleep(2500);
        out.sendTap = await tapText(page, '发送|提交|Send', true);
        const t0 = Date.now();
        for (let i = 0; i < 26; i++) {
          await sleep(5000);
          const s = await page.evaluate(READ);
          const busy = /生成中|思考中|正在处理|请稍候/.test(s.body || '');
          if ((!busy && i >= 1) || Date.now() - t0 > 150000) { out.aiAnswer = { waitedMs: Date.now() - t0, body: s.body.slice(0, 900), buttons: s.buttons.slice(0, 14) }; break; }
          if (i === 25) out.aiAnswer = { waitedMs: Date.now() - t0, timedOut: true, body: s.body.slice(0, 900) };
        }
      }
    }
    await page.screenshot({ path: path.join(__dirname, 'shots', 'ord0242_' + RUN + '_ai.png') }).catch(() => 0);

    out.reached = { Today: /Demo|还没休息|今天/.test((out.simRead && out.simRead.body) || '') };
    out.net = net;
    out.verdicts = {
      Simulation: out.simReached ? 'COMPATIBLE' : 'NOT_REACHED',
      AI: out.aiSheetReached ? (out.aiAnswer ? 'COMPATIBLE' : 'COMPATIBLE_WITH_DECLARED_DEGRADATION') : 'NOT_REACHED',
    };
    out.httpNamed_4xx = net.filter(n => /^RES [45]/.test(n));
  } catch (e) {
    out.error = String(e && e.message || e).split('\n')[0].slice(0, 200);
  } finally {
    out.ended_at = new Date().toISOString();
    out.console = con; out.pageErrors = perr;
    fs.writeFileSync(path.join(__dirname, 'ord0242_groupB2_' + RUN + '.json'), JSON.stringify(out, null, 2));
    console.log(JSON.stringify({ run: RUN, menu: out.menuTap && { point: out.menuTap.point, hit: out.menuTap.hitCls, ok: out.menuTap.pointHitsThisButton },
      drawerGeom: out.drawerGeometry && { pos: out.drawerGeometry.drawerPosition, rect: out.drawerGeometry.drawerRect, count: out.drawerGeometry.count, sample: (out.drawerGeometry.sample || []).slice(0, 6) },
      simTap: out.simTap && { label: out.simTap.label, rect: out.simTap.rect, inViewport: out.simTap.inViewport, hit: out.simTap.hitTag + '.' + out.simTap.hitCls, ok: out.simTap.pointHitsThisButton, tapped: out.simTap.tappedByTouch, candidates: out.simTap.candidates },
      simReached: out.simReached, simH1: out.simRead && out.simRead.h1, simActions: out.simPanel && out.simPanel.actions,
      close: out.closeTap && { ok: out.closeTap.pointHitsThisButton, label: out.closeTap.label }, backToToday: out.backToToday && { label: out.backToToday.label, ok: out.backToToday.pointHitsThisButton, tapped: out.backToToday.tappedByTouch }, onToday: out.onToday, behindDrawer: out.behindDrawer,
      aiTap: out.aiTap && { point: out.aiTap.point, hit: out.aiTap.hitTag + '.' + out.aiTap.hitCls, ok: out.aiTap.pointHitsThisButton, tapped: out.aiTap.tappedByTouch },
      aiReached: out.aiSheetReached, ask: out.askTap && { label: out.askTap.label, ok: out.askTap.pointHitsThisButton, tapped: out.askTap.tappedByTouch },
      send: out.sendTap && { label: out.sendTap.label, ok: out.sendTap.pointHitsThisButton, tapped: out.sendTap.tappedByTouch },
      answer: out.aiAnswer && { waitedMs: out.aiAnswer.waitedMs, timedOut: out.aiAnswer.timedOut, head: (out.aiAnswer.body || '').slice(0, 260) },
      verdicts: out.verdicts, http4xx: out.httpNamed_4xx, netCount: net.length, netHead: net.slice(0, 8), console_n: con.length, console_head: con.slice(0, 3), pageErrors: perr.length, err: out.error || null }, null, 2));
    if (ctx) await ctx.close().catch(() => 0);
    await browser.close().catch(() => 0);
  }
})();
