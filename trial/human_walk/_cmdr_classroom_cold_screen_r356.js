/* Walk the classroom generation's cold first screen on three viewports and write down what is rendered.
 *
 * The stack was booted by _cmdr_boot_d_stack_r355.py against a brand-new database on D, so what should be
 * on screen is whatever a traveller with no journey sees - not a seeded success state. Nothing here
 * injects DOM, fakes storage or calls the API directly: it loads the address in a real browser, waits for
 * the app to paint, and reports the rendered text plus a screenshot per viewport. A viewport that renders
 * no body text aborts the run, because a blank sheet full of "OK" lines is exactly the fake green this
 * shift has been chasing all night.
 */
const fs = require('fs');
const path = require('path');

const ROOT = 'D:/_cmdr_clean_1030';
const DATA = 'D:/_cmdr_clean_1030_data';
const BASE = process.env.CLASSROOM_FRONTEND_URL || 'http://127.0.0.1:14462/';
const BACKEND = process.env.CLASSROOM_BACKEND_URL || 'http://127.0.0.1:60362';
const RECEIPT = path.join(DATA, 'bw343-classroom-cold-first-screen-three-shapes.txt');
const SHOTS = path.join(DATA, 'screens');
const VIEWPORTS = [
  { name: 'phone_390', width: 390, height: 844 },
  { name: 'tablet_1024', width: 1024, height: 768 },
  { name: 'projector_1280', width: 1280, height: 800 },
];

let playwright;
for (const candidate of ['playwright', 'playwright-core']) {
  try {
    playwright = require(path.join(ROOT, 'frontend', 'node_modules', candidate));
    console.log('PLAYWRIGHT_MODULE', candidate);
    break;
  } catch (error) {
    /* try the next name */
  }
}
if (!playwright) {
  console.error('ABORT no playwright under ' + ROOT + '/frontend/node_modules');
  process.exit(2);
}

function visible(page) {
  return page.evaluate(() => {
    const text = (selector) => Array.from(document.querySelectorAll(selector))
      .map((node) => (node.innerText || node.value || '').trim())
      .filter((value) => value.length > 0);
    const body = (document.body ? document.body.innerText : '').replace(/\s+/g, ' ').trim();
    return {
      title: document.title,
      bodyChars: body.length,
      bodyStart: body.slice(0, 160),
      buttons: text('button').slice(0, 12),
      headings: text('h1,h2').slice(0, 6),
      inputs: document.querySelectorAll('input,textarea,select').length,
    };
  });
}

(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const health = await fetch(BACKEND + '/api/v1/health').then((response) => response.json());
  console.log('BACKEND_HEALTH', JSON.stringify(health));

  const browser = await playwright.chromium.launch();
  const lines = ['CLASSROOM COLD FIRST SCREEN, THREE SHAPES - bw343',
    'frontend ' + BASE + ' backend ' + BACKEND + ' (health ' + health.status + ', ai_state '
    + (health.ai_state || 'unknown') + ')',
    'tree ' + ROOT + ' served from the classroom generation on a brand-new database; no seeded state, '
    + 'no DOM injection, no direct API calls in this walk'];
  const failed = [];

  for (const viewport of VIEWPORTS) {
    const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height },
      deviceScaleFactor: 1 });
    const page = await context.newPage();
    const stamp = new Date().toISOString();
    let report;
    try {
      await page.goto(BASE, { waitUntil: 'load', timeout: 30000 });
      await page.waitForTimeout(2500);
      report = await visible(page);
      const shot = path.join(SHOTS, 'bw343_' + viewport.name + '.png');
      await page.screenshot({ path: shot, fullPage: false });
      report.screenshot = shot;
    } catch (error) {
      report = { error: String(error).slice(0, 160) };
      failed.push(viewport.name);
    }
    lines.push('', viewport.name + ' ' + viewport.width + 'x' + viewport.height + '  ' + stamp);
    lines.push('  title        ' + (report.title || '(none)'));
    lines.push('  body chars   ' + (typeof report.bodyChars === 'number' ? report.bodyChars : 'ERR')
      + '  inputs ' + (typeof report.inputs === 'number' ? report.inputs : '?'));
    lines.push('  headings     ' + JSON.stringify(report.headings || []));
    lines.push('  buttons      ' + JSON.stringify(report.buttons || []));
    lines.push('  first text   ' + JSON.stringify(report.bodyStart || report.error || ''));
    if (report.screenshot) {
      lines.push('  screenshot   ' + report.screenshot + ' bytes=' + fs.statSync(report.screenshot).size);
    }
    if (!report.bodyStart || report.bodyChars < 20) {
      failed.push(viewport.name + ' (rendered text too short)');
    }
    await context.close();
  }
  await browser.close();

  lines.push('', 'TALLY viewports=' + VIEWPORTS.length + ' failed=' + failed.length);
  lines.push('FAILED ' + (failed.length ? failed.join(', ') : 'none'));
  fs.writeFileSync(RECEIPT, lines.join('\n') + '\n');
  console.log(lines.join('\n'));
  console.log('WROTE ' + RECEIPT);
  if (failed.length) {
    console.error('ABORT ' + failed.length + ' viewport(s) did not render a readable first screen');
    process.exit(7);
  }
})();
