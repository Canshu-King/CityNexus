/* Read the DOM behind two things the 390 screenshot showed, so the report describes elements and not vibes.
 *
 * Arm one: every rendered node whose text is 高级设置 - tag, class, role, aria-label, whether it is the
 * summary of a details element, and its box. Arm two: whatever sits in the bottom-right corner, since the
 * shot shows an unlabelled circle there and an unlabelled control is an inaccessible one.
 */
const path = require('path');
const ROOT = 'D:/_cmdr_clean_1030';
const BASE = 'http://127.0.0.1:14462/';
const playwright = require(path.join(ROOT, 'frontend', 'node_modules', 'playwright'));

(async () => {
  const browser = await playwright.chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.goto(BASE, { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(2500);

  const dupes = await page.evaluate(() => {
    const hits = [];
    const walk = (node) => {
      for (const child of node.children) {
        const own = Array.from(child.childNodes).filter((entry) => entry.nodeType === 3)
          .map((entry) => entry.textContent.trim()).join(' ');
        if (own === '高级设置') {
          const box = child.getBoundingClientRect();
          hits.push({
            tag: child.tagName.toLowerCase(),
            cls: child.className.toString().slice(0, 70),
            role: child.getAttribute('role'),
            aria: child.getAttribute('aria-label'),
            parentTag: child.parentElement ? child.parentElement.tagName.toLowerCase() : null,
            parentIsDetails: child.parentElement ? child.parentElement.tagName.toLowerCase() === 'details' : false,
            underlined: getComputedStyle(child).textDecorationLine,
            cursor: getComputedStyle(child).cursor,
            box: [Math.round(box.x), Math.round(box.y), Math.round(box.width), Math.round(box.height)],
            clickable: child.tagName === 'BUTTON' || child.tagName === 'SUMMARY'
              || child.tagName === 'A' || child.getAttribute('role') === 'button',
          });
        }
        walk(child);
      }
    };
    walk(document.body);
    return hits;
  });
  console.log('ADVANCED_SETTINGS_NODES', dupes.length);
  for (const hit of dupes) {
    console.log('  ' + JSON.stringify(hit));
  }

  const corner = await page.evaluate(() => {
    const found = [];
    for (const node of document.querySelectorAll('body *')) {
      const box = node.getBoundingClientRect();
      if (box.width === 0 || box.height === 0) continue;
      const inCorner = box.right > window.innerWidth - 90 && box.bottom > window.innerHeight - 160;
      if (!inCorner) continue;
      const style = getComputedStyle(node);
      const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
      found.push({
        tag: node.tagName.toLowerCase(),
        cls: node.className.toString().slice(0, 60),
        role: node.getAttribute('role'),
        aria: node.getAttribute('aria-label'),
        title: node.getAttribute('title'),
        text: (node.innerText || '').replace(/\s+/g, ' ').slice(0, 24),
        radius: style.borderRadius,
        box: [Math.round(box.x), Math.round(box.y), Math.round(box.width), Math.round(box.height)],
        hitTestSelf: hit === node || node.contains(hit),
      });
    }
    return found;
  });
  console.log('BOTTOM_RIGHT_NODES', corner.length);
  for (const hit of corner) {
    console.log('  ' + JSON.stringify(hit));
  }
  await browser.close();
})();
