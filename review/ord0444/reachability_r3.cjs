/* ORD-0444 r3 -- is 我的收藏 actually reachable on the screen it is mounted on?
   ORD-0449 and ORD-0450 landed panels on other surfaces after slice 1 was written, and 城市探索 already
   holds two panels above this one, so "it renders" is not the same question as "a traveller can get
   to it". Measured at two shapes: desktop 1280x1000 and phone 390x844.
   Per the house rule, fold is judged on the element's own boxes and a centre hit-test, not on a
   scroll offset. */
const { chromium } = require("playwright");
(async () => {
  const b = await chromium.launch();
  const out = { shapes: {}, started_at: new Date().toISOString() };
  for (const vp of [{ width: 1280, height: 1000 }, { width: 390, height: 844 }]) {
    const page = await b.newPage({ viewport: vp });
    await page.goto("http://localhost:60157/v8/discover", { waitUntil: "load" });
    const entry = page.getByRole("button", { name: "使用封存的演示行程" });
    if (await entry.count()) await entry.first().click();
    await page.waitForSelector('[data-testid="collection-panel"]', { timeout: 30000 });
    const m = await page.evaluate(() => {
      const panel = document.querySelector('[data-testid=' + '"collection-panel"' + ']');
      const btn = document.querySelector('[data-testid=' + '"collection-empty-action"' + ']')
        || document.querySelector('[data-testid=' + '"collection-refresh"' + ']');
      const box = (el) => { const r = el.getBoundingClientRect(); return { top: Math.round(r.top), bottom: Math.round(r.bottom), h: Math.round(r.height) }; };
      const centreHit = (el) => {
        const r = el.getBoundingClientRect();
        const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        return hit ? (panel.contains(hit) ? "inside-panel" : hit.tagName.toLowerCase() + "." + (hit.className || "").toString().slice(0, 30)) : "null";
      };
      const scrollable = (() => {
        let n = panel.parentElement;
        while (n) { if (n.scrollHeight > n.clientHeight + 1) return n.className || n.tagName.toLowerCase(); n = n.parentElement; }
        return null;
      })();
      return {
        viewport: { w: innerWidth, h: innerHeight },
        panel: box(panel), btn: btn ? box(btn) : null,
        panel_top_on_screen_at_load: Math.round(panel.getBoundingClientRect().top),
        centre_hit_panel: centreHit(panel),
        centre_hit_btn: btn ? centreHit(btn) : "no-button",
        doc_scroll_height: document.scrollingElement.scrollHeight,
        nearest_scrollable_ancestor: scrollable,
        hit_chain_at_panel_centre: (() => {
          const r2 = panel.getBoundingClientRect();
          return document.elementsFromPoint(r2.left + r2.width / 2, r2.top + r2.height / 2)
            .slice(0, 3).map((n) => n.tagName.toLowerCase() + "[tid=" + (n.getAttribute("data-testid") || "") + "]");
        })(),
        panels_above_on_this_route: Array.from(document.querySelectorAll('[data-testid]'))
          .map((e) => e.getAttribute('data-testid'))
          .filter((t) => t === 'prep-panel' || t === 'collection-panel' || t === 'v8-pick-bar').length,
      };
    });
    // scroll it into view the way a traveller would, then re-hit-test the button
    await page.locator('[data-testid="collection-panel"]').scrollIntoViewIfNeeded();
    const after = await page.evaluate(() => {
      const btn = document.querySelector('[data-testid="collection-empty-action"]')
        || document.querySelector('[data-testid="collection-refresh"]');
      if (!btn) return { btn_after_scroll: "absent" };
      const r = btn.getBoundingClientRect();
      const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return { btn_after_scroll: { top: Math.round(r.top), in_viewport: r.top >= 0 && r.bottom <= innerHeight, hit: hit ? hit.tagName.toLowerCase() : "null" } };
    });
    // The decisive evidence is a real press, not a coordinate probe: this headless build answers
    // `elementsFromPoint` with a bare `html` even for a button Playwright can click, so the hit
    // chain is recorded and *not* treated as the verdict. Pressing the empty state's action and
    // reading the shelf the server answers back is what "a traveller can get to it" means here.
    let pressed = { pressed: false };
    try {
      const act = page.locator('[data-testid="collection-empty-action"]');
      if (await act.count()) {
        await act.click();
        await page.waitForSelector('[data-testid="collection-shelf"]', { timeout: 20000 });
        pressed = {
          pressed: true,
          shelf_name_after_real_press: await page.locator('[data-testid="collection-shelf-name"]').textContent(),
          shelf_count_after_real_press: await page.locator('[data-testid="collection-shelf"]').count(),
        };
      } else {
        const ref = page.locator('[data-testid="collection-refresh"]').first();
        await ref.click();
        pressed = { pressed: true, pressed_instead: "collection-refresh", rows_after: await page.locator('[data-testid="collection-row"]').count() };
      }
    } catch (e) {
      pressed = { pressed: false, error: String(e && e.message ? e.message : e).slice(0, 120) };
    }
    out.shapes[`${vp.width}x${vp.height}`] = { ...m, ...after, real_press: pressed };
    await page.close();
  }
  await b.close();
  console.log(JSON.stringify(out, null, 1));
  require("fs").writeFileSync("review/ord0444/reachability_r3.json", JSON.stringify(out, null, 1), "utf-8");
})();
