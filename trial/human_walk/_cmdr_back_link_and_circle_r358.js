/* Two follow-ups the screenshot raised, measured rather than described.
 *
 * 1. the underlined 高级设置 at y=719 carries class trial-back-link - a back link wearing a settings
 *    label. Click it and record what actually changes on screen; a label that does not predict the
 *    destination is the defect, so the reading has to be the destination.
 * 2. the shot shows a small circle in the bottom-right with no text on it. List every button with its
 *    class, accessible name and box, and hit-test its own centre, so an unlabelled control is named by
 *    evidence instead of by what it looks like.
 */
const path = require('path');
const fs = require('fs');
const ROOT = 'D:/_cmdr_clean_1030';
const BASE = 'http://127.0.0.1:14462/';
const OUT = 'D:/_cmdr_clean_1030_data/bw345-back-link-destination-and-the-corner-circle.txt';
const playwright = require(path.join(ROOT, 'frontend', 'node_modules', 'playwright'));

const inventory = () => {
  return Array.from(document.querySelectorAll('button,a,[role="button"]')).map((node) => {
    const box = node.getBoundingClientRect();
    const centre = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
    return {
      tag: node.tagName.toLowerCase(),
      cls: node.className.toString().slice(0, 46),
      text: (node.innerText || node.value || '').replace(/\s+/g, ' ').trim().slice(0, 26),
      aria: node.getAttribute('aria-label'),
      title: node.getAttribute('title'),
      box: [Math.round(box.x), Math.round(box.y), Math.round(box.width), Math.round(box.height)],
      radius: getComputedStyle(node).borderRadius,
      hitSelf: centre === node || node.contains(centre),
    };
  });
};

(async () => {
  const browser = await playwright.chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.goto(BASE, { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(2500);
  const lines = ['CLASSROOM COLD SCREEN - WHERE THE BACK LINK GOES, AND WHAT THE CIRCLE IS  bw345',
    'loaded ' + BASE + ' in a real browser at 390x844; the only interaction is a click on a control a '
    + 'traveller would see', ''];

  const before = await page.evaluate(inventory);
  const small = before.filter((row) => row.box[2] <= 64 && row.box[3] <= 64);
  lines.push('BEFORE: ' + before.length + ' controls; the small ones (<=64px) are:');
  for (const row of small) {
    lines.push('  ' + JSON.stringify(row));
  }
  const unlabelled = before.filter((row) => !row.text && !row.aria && !row.title);
  lines.push('UNLABELLED controls (no text, no aria-label, no title): ' + unlabelled.length);
  for (const row of unlabelled) {
    lines.push('  ' + JSON.stringify(row));
  }

  const back = await page.$('button.trial-back-link');
  if (!back) {
    throw new Error('ABORT no button.trial-back-link on this screen, so the earlier reading was wrong');
  }
  const backText = (await back.innerText()).trim();
  const beforeUrl = page.url();
  const beforeBody = (await page.evaluate(() => document.body.innerText)).replace(/\s+/g, ' ').trim();
  await back.click();
  await page.waitForTimeout(2000);
  const afterUrl = page.url();
  const afterBody = (await page.evaluate(() => document.body.innerText)).replace(/\s+/g, ' ').trim();
  const after = await page.evaluate(inventory);

  lines.push('');
  lines.push('CLICK button.trial-back-link labelled 「' + backText + '」');
  lines.push('  url     ' + beforeUrl + '  ->  ' + afterUrl);
  lines.push('  body    ' + beforeBody.length + ' chars -> ' + afterBody.length + ' chars; changed='
    + (beforeBody !== afterBody));
  lines.push('  after   ' + JSON.stringify(afterBody.slice(0, 200)));
  lines.push('  controls ' + before.length + ' -> ' + after.length);
  const openedDetails = await page.$$eval('details[open]', (nodes) => nodes.length);
  lines.push('  details[open] after the click: ' + openedDetails);
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, lines.join('\n') + '\n');
  console.log(lines.join('\n'));
  console.log('WROTE ' + OUT);
  await page.screenshot({ path: 'D:/_cmdr_clean_1030_data/screens/bw345_after_back_link_click.png' });
  await browser.close();
})();
