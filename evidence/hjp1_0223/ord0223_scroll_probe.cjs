/* ORD-0223 reproducible probe: does the wizard's blocked-press explanation reach the viewport?
 *
 * What it proves (three separate claims, one run):
 *   A. after a refused 下一步 press, window.scrollY stays 0 and #trial-required-hint is below the fold;
 *   B. a MANUAL INSTANT scrollIntoView on that same node moves the document (so the layout is scrollable);
 *   C. a MANUAL SMOOTH scrollIntoView on that same node does NOT move it under this instrument
 *      => C is why an automated gate cannot observe the product's behaviour:"smooth" fix.
 * It also records whether the screen-reader live region #trial-next-reason still carries the stale
 * sentence after the field is fixed (the ORD-0220 ② half).
 *
 * Safety: read-only against the UI. It never presses 确认创建, so it creates no rows.
 * Point it at YOUR OWN isolated stack only (default: the HJ-P1 lane), never the shared preview or a user DB.
 *
 * Run:  node ord0223_scroll_probe.cjs            # uses CNX_BASE or http://127.0.0.1:8752
 *       CNX_BASE=http://127.0.0.1:8799 node ord0223_scroll_probe.cjs
 * Needs: the playwright package (default path below), and a CityNexus frontend+backend on CNX_BASE.
 */
const PW = process.env.CNX_PW || 'D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright';
const { chromium } = require(PW);
const fs = require('fs');
const path = require('path');

const BASE = process.env.CNX_BASE || 'http://127.0.0.1:8752';
const VW = 390, VH = 844;
const out = { base: BASE, viewport: [VW, VH], steps: {} };

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: VW, height: VH }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = await ctx.newPage();
  const writes = [];
  page.on('request', r => { if (r.method() !== 'GET' && r.url().includes('/api/')) writes.push(r.method() + ' ' + r.url()); });

  const snap = () => page.evaluate(() => {
    const hint = document.getElementById('trial-required-hint');
    const lr = document.getElementById('trial-next-reason');
    const hr = hint ? hint.getBoundingClientRect() : null;
    return {
      scrollY: Math.round(window.scrollY),
      docScrollHeight: document.documentElement.scrollHeight,
      innerHeight: window.innerHeight,
      hintPresent: !!hint,
      hintY: hr ? Math.round(hr.y) : null,
      hintInView: hr ? (hr.top > 0 && hr.bottom < window.innerHeight) : null,
      hintVisibleText: hint ? hint.textContent.trim().slice(0, 30) : null,
      liveRegionText: lr ? lr.textContent.trim().slice(0, 30) : 'NO_NODE',
      liveRegionAriaLive: lr ? lr.getAttribute('aria-live') : null,
    };
  });

  const step2Text = () => page.evaluate(() => (document.body.innerText || '').replace(/\s+/g, ' '));

  try {
    await page.goto(BASE + '/v8/hub', { waitUntil: 'load', timeout: 45000 });
    await sleep(4500);
    await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(y => (y.innerText || '').includes('试用其他城市') && y.getBoundingClientRect().height > 0); if (b) b.click(); });
    await sleep(2400);
    for (let i = 0; i < 3; i++) {
      if ((await step2Text()).includes('旅行人数')) break;
      await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(y => y.innerText.trim() === '返回' && y.getBoundingClientRect().height > 0); if (b) b.click(); });
      await sleep(1700);
    }
    out.steps.onStep2 = (await step2Text()).includes('旅行人数');

    /* A fresh browser context has no draft, so the wizard stops at step 1. Walk it forward. */
    if (!out.steps.onStep2) {
      const dest = page.locator('input[placeholder*="例如：天津"]').first();
      out.steps.step1Present = (await dest.count()) > 0;
      if (out.steps.step1Present) {
        await dest.click();
        await page.keyboard.press('Control+a');
        await page.keyboard.press('Delete');
        await dest.type('成都', { delay: 50 });
        await page.waitForSelector('input[placeholder*="成都站"]', { timeout: 25000 }).catch(() => null);
        await sleep(1500);
        const anchors = page.locator('input[placeholder*="成都站"]');
        if ((await anchors.count()) >= 2) {
          for (const [idx, val] of [[0, '成都东站'], [1, '成都天府机场']]) {
            await anchors.nth(idx).click();
            await page.keyboard.press('Control+a');
            await page.keyboard.press('Delete');
            await anchors.nth(idx).pressSequentially(val, { delay: 40 });
          }
          const dt = page.locator('input[type="datetime-local"]');
          await dt.nth(0).fill('2026-12-01T08:00');
          await dt.nth(1).fill('2026-12-04T20:00');
          await sleep(1500);
          await page.locator('button.v8-primary-button').first().click({ force: true });
          await sleep(2500);
        }
      }
      out.steps.onStep2 = (await step2Text()).includes('旅行人数');
      if (!out.steps.onStep2) out.steps.diag = (await step2Text()).slice(0, 120);
    }
    if (!out.steps.onStep2) throw new Error('could not reach wizard step 2 (人数与偏好) on this build; see steps.diag');

    const budget = page.locator('input[type="number"]').nth(2);
    await budget.click({ clickCount: 3 });
    await budget.pressSequentially('0', { delay: 40 });
    await budget.blur();
    await sleep(900);
    out.steps.A_beforePress = await snap();

    await page.locator('button.v8-primary-button').first().click({ force: true });
    await sleep(2500);
    out.steps.A_afterRefusedPress = await snap();

    out.steps.B_manualInstant = await page.evaluate(() => {
      const el = document.getElementById('trial-required-hint');
      if (!el) return 'NO_NODE';
      el.scrollIntoView({ block: 'center' });
      return 'called';
    });
    await sleep(600);
    out.steps.B_afterInstant = await snap();

    await page.evaluate(() => window.scrollTo(0, 0));
    await sleep(300);
    out.steps.C_manualSmooth = await page.evaluate(() => {
      const el = document.getElementById('trial-required-hint');
      if (!el) return 'NO_NODE';
      el.scrollIntoView({ block: 'center', behavior: 'smooth' });
      return 'called';
    });
    const smoothPoll = [];
    for (let i = 0; i < 6; i++) { smoothPoll.push((await snap()).scrollY); await sleep(200); }
    out.steps.C_scrollYSamplesDuringSmooth = smoothPoll;

    await budget.click({ clickCount: 3 });
    await budget.pressSequentially('420', { delay: 40 });
    await budget.blur();
    await sleep(1400);
    out.steps.D_afterFixingField = await snap();
  } catch (e) {
    out.error = String(e.message).split('\n')[0];
  }

  out.nonGetRequests = writes;
  out.verdict = (() => {
    const a = out.steps.A_afterRefusedPress, b = out.steps.B_afterInstant, c = out.steps.C_scrollYSamplesDuringSmooth, d = out.steps.D_afterFixingField;
    if (!a || !b || !c || !d) return 'INCOMPLETE';
    return {
      refusedPressMovedPage: a.scrollY !== 0,
      instantScrollWorks: b.scrollY !== 0 && b.hintInView === true,
      smoothScrollAdvanced: c.some(v => v !== 0),
      visibleHintRecomputedAfterFix: d.hintPresent === false,
      liveRegionStillStaleAfterFix: /还需要填写/.test(d.liveRegionText || ''),
    };
  })();

  fs.writeFileSync(path.join(__dirname, 'ord0223_scroll_probe.json'), JSON.stringify(out, null, 2));
  console.log(JSON.stringify({ base: BASE, error: out.error || null, onStep2: out.steps.onStep2, verdict: out.verdict, nonGetRequests: writes.length }, null, 2));
  await browser.close();
})();
