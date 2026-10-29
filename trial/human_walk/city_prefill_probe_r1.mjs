// Three arms on the traveller's first screen: one city in the sentence fills the box, two cities refuse to
// guess, and a box the person typed in is never overwritten.  Reads rendered text and the input's own value;
// clicks are real mouse clicks on an element's own centre after an elementFromPoint hit-test.
import fs from "node:fs";
import { createRequire } from "node:module";
const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const BASE = process.env.WALK_BASE || 'http://127.0.0.1:14522/revolution';
const OUT = process.env.PROBE_LOG || 'D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/city_prefill-1.txt';
const lines = [];
const say = (m) => { lines.push(m); console.log(m); };

(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9335');
  const context = browser.contexts()[0];
  const page = await context.newPage();
  await page.setViewportSize({ width: 390, height: 844 });
  const goal = page.getByTestId('rev-trip-goal');
  const city = page.getByTestId('rev-firstlook-city');
  const hint = page.getByTestId('rev-trip-destination-hint');
  const readBox = async () => ({
    // "(absent)" is itself a reading: it means the first-screen form is no longer on the page.
    value: await city.inputValue({ timeout: 5000 }).catch(() => "(absent)"),
    hint: await hint.isVisible().catch(() => false),
    hintText: (await hint.innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 160),
  });

  const arm = async (label, steps) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await page.evaluate(() => localStorage.clear());
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1200);
    for (const step of steps) await step();
    const box = await readBox();
    say(`ARM ${label} city_value="${box.value}" hint_visible=${box.hint} hint_text=${box.hintText}`);
  };

  await arm('A_one_city_in_sentence', [
    async () => goal.fill('北京玩两天，两个人'),
    async () => page.waitForTimeout(400),
  ]);

  await arm('B_two_cities_refuse_to_guess', [
    async () => goal.fill('从北京去厦门玩两天'),
    async () => page.waitForTimeout(400),
  ]);

  await arm('C_human_typed_first', [
    async () => city.fill('杭州'),
    async () => goal.fill('北京玩两天'),
    async () => page.waitForTimeout(400),
  ]);

  // Arm D is the owner's complaint itself: sentence only, then the first press that used to be blocked.
  await arm('D_first_press_after_sentence', [
    async () => goal.fill('北京玩两天，两个人'),
    async () => page.waitForTimeout(400),
    async () => {
      const button = page.locator('.rev-trip-request-form button[type="submit"]').first();
      const box = await button.boundingBox();
      if (!box) { say('ARM_D submit button has no render box'); return; }
      const cx = Math.round(box.x + box.width / 2);
      const cy = Math.round(box.y + box.height / 2);
      const top = await page.evaluate(([x, y]) => {
        const node = document.elementFromPoint(x, y);
        return node ? (node.getAttribute('data-testid') || node.tagName) : 'NONE';
      }, [cx, cy]);
      say(`ARM_D press label="${(await button.innerText()).replace(/\s+/g, ' ').slice(0, 24)}" centre=${cx},${cy} topmost=${top}`);
      await button.click({ position: { x: Math.round(box.width / 2), y: Math.round(box.height / 2) } });
      await page.waitForTimeout(6000);
      // The press either moves the traveller off the first screen or leaves them in front of the same wall.
      // Reading the city box after a successful press would just time out, so ask the screen instead.
      const formsLeft = await page.locator('.rev-trip-request-form').count();
      const error = await page.locator('.rev-trip-error, [data-testid="rev-trip-error"]').first()
        .innerText().catch(() => '');
      const body = (await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 220);
      say(`ARM_D after_press first_screen_forms=${formsLeft} error_text="${error.replace(/\s+/g, ' ').slice(0, 120)}"`);
      say(`ARM_D screen_headline ${body}`);
    },
  ]);

  // Arm E: a person types first, then keeps writing and the sentence stops naming one place.  The box this
  // screen filled must go back to empty, not keep standing there as the earlier guess.
  await arm('E_sentence_grows_ambiguous', [
    async () => goal.fill('北京玩两天'),
    async () => page.waitForTimeout(300),
    async () => say(`ARM_E after_first_half city_value="${await city.inputValue()}"`),
    async () => goal.fill('北京玩两天，再去厦门'),
    async () => page.waitForTimeout(400),
  ]);

  // Arm F is the negative control for Chinese substring matching: 大厦门 is not a city in this table, but it
  // contains 厦门, so the box would fill with a place the traveller never named.  Reading it, not guessing.
  await arm('F_substring_of_a_longer_word', [
    async () => goal.fill('去大厦门滩玩两天'),
    async () => page.waitForTimeout(400),
  ]);

  // Arm G is the other side of the same rule: a lead-in character makes the spelling count.
  await arm('G_lead_in_counts', [
    async () => goal.fill('12 号到厦门玩两天'),
    async () => page.waitForTimeout(400),
  ]);

  await page.screenshot({ path: OUT.replace(/\.txt$/, '-shot.png') });
  await page.close();
  fs.writeFileSync(OUT, lines.join('\n') + '\n');
  say('PROBE_DONE');
  fs.writeFileSync(OUT, lines.join('\n') + '\n');
})().catch((exc) => { say('PROBE_FAILED ' + String(exc)); fs.writeFileSync(OUT, lines.join('\n') + '\n'); process.exitCode = 1; });
