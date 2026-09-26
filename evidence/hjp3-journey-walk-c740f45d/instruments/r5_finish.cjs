/* Two loose ends from take 3, both mine to close before anything is claimed.
 *
 * 1. The traveller does reach 确认创建 (the wizard walks 1→2→3), and the third press failed only because at step 3
 *    the button is labelled 确认创建 rather than 下一步 - my assumption, not a product stall. So this run presses
 *    the real button and records what comes back and what the screen then says, in a chain where no backend is
 *    listening. The invented defaults the screen itself labels 「我们替你填的」 are what would be sent, so the
 *    read of that POST is the honest answer to "can a traveller actually finish".
 *
 * 2. Take 3's self-test could not show that a collapsed 技术详情 hides text from my reader, because
 *    document.body.innerText already included it. That claim therefore stays unproven here, and the honest test
 *    is element-level: read the <details> node's own innerText at rest and after opening it, and report both.
 *
 * Usage: node r5_finish.cjs <outDir>
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('D:/moodle/CityNexus/frontend/node_modules/playwright');

const OUT = path.resolve(process.argv[2] || 'D:/moodle/_hjp3_0323walk_0926');
const CHAIN = 'http://127.0.0.1:4781';
fs.mkdirSync(OUT, { recursive: true });
const SHA = (s) => crypto.createHash('sha256').update(String(s)).digest('hex');

(async () => {
  const out = { started_at: new Date().toISOString(), chain: CHAIN, viewport: { width: 390, height: 844 } };
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
                                         hasTouch: true, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = await ctx.newPage();
  const legs = [];
  page.on('response', (r) => { if (r.url().indexOf('/api/') >= 0) legs.push({ url: r.url().replace(/^http:\/\/127\.0\.0\.1:\d+/, ''), m: r.request().method(), status: r.status(), ct: r.headers()['content-type'] || null, post_body_len: (r.request().postData() || '').length }); });
  page.on('requestfailed', (rq) => { if (rq.url().indexOf('/api/') >= 0) legs.push({ url: rq.url().replace(/^http:\/\/127\.0\.0\.1:\d+/, ''), m: rq.method(), status: null, failure: (rq.failure() && rq.failure().errorText) || 'failed' }); });

  await page.goto(CHAIN + '/', { waitUntil: 'load', timeout: 60000 });
  await page.waitForTimeout(2000);
  await page.locator('input[placeholder^="例如"]').first().fill('天津');
  const places = page.locator('input[placeholder*="机场"]');
  for (let i = 0; i < await places.count(); i++) await places.nth(i).fill(i ? '天津滨海国际机场' : '天津站');
  const dts = page.locator('input[type="datetime-local"]');
  for (let i = 0; i < await dts.count(); i++) await dts.nth(i).fill(i ? '2026-10-03T20:00' : '2026-10-02T10:00');
  await page.getByText('下一步').first().click({ timeout: 6000 }).catch(() => {});
  await page.waitForTimeout(1400);
  await page.getByText('下一步').first().click({ timeout: 6000 }).catch(() => {});
  await page.waitForTimeout(1600);
  const beforeText = await page.evaluate(() => document.body.innerText);
  /* take 3's press hit the step-dot label, which also reads 确认创建 - the button is found by role here, and
     what was actually pressed is recorded so the claim cannot be "I clicked the button" on an unverified node */
  const btns = await page.evaluate(() => Array.prototype.slice.call(document.querySelectorAll('button'))
    .map((b, i) => ({ i: i, text: (b.innerText || '').trim().slice(0, 24), disabled: !!b.disabled,
                      cls: String(b.className).slice(0, 40), top: Math.round(b.getBoundingClientRect().top) })));
  const target = btns.filter((b) => b.text === '确认创建');
  const roleBtn = page.getByRole('button', { name: '确认创建', exact: true }).first();
  const press = target.length === 0 ? 'no_button_named_确认创建'
    : await roleBtn.click({ timeout: 6000 }).then(() => 'clicked').catch((e) => 'click_failed: ' + String(e.message).slice(0, 60));
  out.candidate_buttons = btns; out.confirm_button_found_by_text = target;
  await page.waitForTimeout(3500);
  const after = await page.evaluate(() => ({ inner: document.body.innerText,
                                             url: location.href,
                                             details: Array.prototype.slice.call(document.querySelectorAll('details'))
                                               .map((d) => ({ open: !!d.open, own_inner_len: (d.innerText || '').trim().length })) }));
  out.press_confirm = { press: press,
                        leg_after_press: legs.slice(-6),
                        painted_before_capped: beforeText.slice(0, 300),
                        painted_after_capped: after.inner.slice(0, 600),
                        painted_after_len: after.inner.length,
                        painted_after_sha256: SHA(after.inner),
                        url_after: after.url, details_after: after.details,
                        still_on_wizard: /确认创建/.test(after.inner),
                        reached_hub: /今天|地图|Copilot|行程列表/.test(after.inner) && !/还需要填写/.test(after.inner) };
  try { out.stored_journey_id = await page.evaluate(() => localStorage.getItem('citynexus.v8.journey_id')); }
  catch (e) { out.stored_journey_id = 'READ_FAILED'; }

  /* the collapse question, asked at element level on a page I author myself */
  const fx = await ctx.newPage();
  await fx.setContent('<details id="d"><summary>技术详情</summary><p id="p">TypeError: x is not a function</p></details>');
  const atRest = await fx.evaluate(() => ({ body_includes: document.body.innerText.indexOf('TypeError') >= 0,
                                            details_own: (document.querySelector('#d').innerText || '').trim().length,
                                            p_own: (document.querySelector('#p').innerText || '').trim().length,
                                            p_textcontent: (document.querySelector('#p').textContent || '').trim().length }));
  await fx.evaluate(() => { document.querySelector('#d').open = true; });
  const opened = await fx.evaluate(() => ({ body_includes: document.body.innerText.indexOf('TypeError') >= 0,
                                            details_own: (document.querySelector('#d').innerText || '').trim().length,
                                            p_own: (document.querySelector('#p').innerText || '').trim().length,
                                            p_textcontent: (document.querySelector('#p').textContent || '').trim().length }));
  out.collapse_self_test = { at_rest: atRest, after_opening: opened,
                             derived: { body_level_read_hides_it_when_collapsed: !atRest.body_includes && opened.body_includes,
                                        element_inner_text_hides_it_when_collapsed: atRest.p_own === 0 && opened.p_own > 0,
                                        element_text_content_never_hides_it: atRest.p_textcontent > 0 },
                             screenshot: (await (async () => { const p = path.join(OUT, 'W3_8_collapse_fixture.png');
                                                               await fx.screenshot({ path: p });
                                                               return { file: path.basename(p), exists: fs.existsSync(p), bytes: fs.statSync(p).size }; })()) };
  const p2 = path.join(OUT, 'W3_9_after_confirm.png');
  await page.screenshot({ path: p2 });
  out.press_confirm.screenshot = { file: path.basename(p2), exists: fs.existsSync(p2), bytes: fs.statSync(p2).size };
  out.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'r5_finish_findings.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({ press: out.press_confirm.press, legs_after: out.press_confirm.leg_after_press,
    still_on_wizard: out.press_confirm.still_on_wizard, reached_hub: out.press_confirm.reached_hub,
    stored_id: out.stored_journey_id, painted_after: out.press_confirm.painted_after_capped.slice(-260),
    collapse: out.collapse_self_test.derived }, null, 1));
  await browser.close();
})().catch((e) => { console.error('FINISH FAILED: ' + String((e && e.message) || e)); process.exit(9); });
