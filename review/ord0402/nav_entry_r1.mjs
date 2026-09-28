import { chromium } from "playwright";
import { writeFileSync } from "node:fs";
const b = await chromium.launch();
const out = { arms: [] };
for (const locale of ["zh-CN", "en"]) {
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  const p = await ctx.newPage();
  await p.addInitScript((v) => localStorage.setItem("citynexus.locale", v), locale);
  await p.addInitScript(() => localStorage.setItem("citynexus.v8.journey_id", "849ccd6f-6feb-403d-80aa-b42e0843ec3b"));
  await p.goto("http://127.0.0.1:4302/v8/hub", { waitUntil: "load" });
  await p.waitForTimeout(1500);
  /* The drawer trigger is identified by the panel it controls, not by its label: the label is
     translated and carries a glyph, and an accessibility-name match proved to be the wrong ruler. */
  const menu = p.locator('[aria-controls="v8-nav-drawer"]');
  const count = await menu.count();
  if (count) await menu.click();
  await p.waitForTimeout(900);
  const labels = await p.evaluate(() => [...document.querySelectorAll("nav button")].map((el) => (el.innerText || "").replace(/\s+/g, " ").trim()).filter(Boolean));
  const hit = await p.evaluate(() => {
    /* At 390 the desktop sidebar is display:none, so its buttons have zero boxes and answering "is
       the entry hittable" from that node would be the same class of error as ORD-0400: a control the
       DOM has and the screen does not. Only a node with a real box counts. */
    const all = [...document.querySelectorAll("nav button")].filter((x) => /回收站|Recycle bin/.test(x.innerText));
    const el = all.find((x) => { const r = x.getBoundingClientRect(); return r.width > 0 && r.height > 0; }) || null;
    if (!el) return { candidates: all.length, visible: 0 };
    const r = el.getBoundingClientRect();
    const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
    return { candidates: all.length, visible: all.filter((x) => x.getBoundingClientRect().width > 0).length, y: Math.round(r.y), h: Math.round(r.height), centre: [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)], self: top === el, on_top: top ? top.tagName.toLowerCase() : null };
  });
  if (count) await p.screenshot({ path: `D:/moodle/_qoder_q_ord0402_evidence/nav-drawer-${locale}.png` });
  out.arms.push({ locale, menu_button_found: !!count, labels, trash_entry: hit });
  if (hit) {
    await p.evaluate(() => {
      const el = [...document.querySelectorAll("nav button")].find(
        (x) => /回收站|Recycle bin/.test(x.innerText) && x.getBoundingClientRect().width > 0,
      );
      el.click();
    });
    await p.waitForTimeout(1600);
    out.arms[out.arms.length - 1].after_tap = await p.evaluate(() => ({
      url: location.pathname,
      panel: !!document.querySelector('[data-testid="journey-trash-panel"]'),
      breadcrumb: document.querySelector(".v8-breadcrumb")?.innerText.replace(/\s+/g, " ").trim(),
    }));
    await p.screenshot({ path: `D:/moodle/_qoder_q_ord0402_evidence/trash-via-nav-${locale}.png` });
  }
  await ctx.close();
}
await b.close();
writeFileSync("D:/moodle/_qoder_q_ord0402_evidence/nav_entry_r1.json", JSON.stringify(out, null, 2));
console.log(JSON.stringify(out.arms.map((a) => ({ locale: a.locale, menu: a.menu_button_found, trash: a.trash_entry, after: a.after_tap, labels: a.labels.slice(0, 12) })), null, 1));
