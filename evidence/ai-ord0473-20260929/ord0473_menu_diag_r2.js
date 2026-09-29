// ORD-0473 diagnostic round 2: the click does flip state (aria-expanded true, backdrop mounted),
// yet nothing new becomes visible. Enumerate every element that carries the drawer id, its rect
// and computed visibility, and the same for the mounted drawer's own entries -- then take the
// frame, because a number that disagrees with the screenshot is the number that is wrong.
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");

const BASE = process.argv[2] || "http://127.0.0.1:4870";
const OUT = process.argv[3] || "D:/moodle/_qoder_ai_ord0387_20260928/ord0473_diag";
const LABEL = process.argv[4] || "tip_ffd84dc";
const ENTRY = ["使用封存的演示行程", "Use the sealed demo journey", "sealed demo", "封存演示"];

const DUMP = () => {
  const els = Array.from(document.querySelectorAll("#v8-nav-drawer"));
  const info = els.map((el, i) => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    const parentChain = [];
    let p = el.parentElement;
    for (let k = 0; p && k < 6; k += 1) {
      const pr = p.getBoundingClientRect();
      const pcs = getComputedStyle(p);
      parentChain.push({ tag: p.tagName, cls: String(p.className || "").slice(0, 30), display: pcs.display, visibility: pcs.visibility, transform: pcs.transform === "none" ? "none" : "matrix", rect: [Math.round(pr.left), Math.round(pr.top), Math.round(pr.width), Math.round(pr.height)], media_z: pcs.zIndex, pos: pcs.position });
      p = p.parentElement;
    }
    const items = Array.from(el.querySelectorAll("button,a")).map((b) => {
      const br = b.getBoundingClientRect();
      const cx = Math.round(br.left + br.width / 2), cy = Math.round(br.top + br.height / 2);
      const at = document.elementFromPoint(cx, cy);
      return { text: (b.textContent || "").trim().slice(0, 14), box: [Math.round(br.left), Math.round(br.top), Math.round(br.width), Math.round(br.height)], centre: [cx, cy], hit_is_self: !!(at && (at === b || b.contains(at))), hit: at ? at.tagName + "." + String(at.className || "").slice(0, 18) : "none" };
    });
    return {
      idx: i, rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
      display: cs.display, visibility: cs.visibility, opacity: cs.opacity, position: cs.position,
      transform: cs.transform === "none" ? "none" : "matrix", z: cs.zIndex, overflow: cs.overflowY,
      item_count: items.length, items: items.slice(0, 20), ancestors: parentChain,
    };
  });
  const backdrop = document.querySelector(".v8-drawer-backdrop");
  const bs = backdrop ? getComputedStyle(backdrop) : null;
  const br = backdrop ? backdrop.getBoundingClientRect() : null;
  return {
    path: location.pathname,
    drawer_id_count: els.length,
    drawers: info,
    backdrop: backdrop ? { rect: [Math.round(br.left), Math.round(br.top), Math.round(br.width), Math.round(br.height)], display: bs.display, visibility: bs.visibility, zIndex: bs.zIndex, position: bs.position } : null,
    menu: (() => { const m = Array.from(document.querySelectorAll("button")).find((e) => (e.textContent || "").trim() === "菜单"); if (!m) return null; const r = m.getBoundingClientRect(); return { expanded: m.getAttribute("aria-expanded"), box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)] }; })(),
    visible_testids: Array.from(document.querySelectorAll("[data-testid]")).filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; }).length,
  };
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  const rep = { base: BASE, label: LABEL, stages: [] };
  await page.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
  await page.evaluate(() => localStorage.setItem("citynexus.locale", "zh-CN"));
  await page.goto(BASE + "/v8/hub", { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
  for (const label of ENTRY) {
    const loc = page.getByText(label, { exact: false }).first();
    if (await loc.count()) { await loc.click({ timeout: 8000 }).catch(() => {}); await page.waitForTimeout(2500); break; }
  }
  await page.goto(BASE + "/v8/hub", { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(3000);
  rep.stages.push({ stage: "closed", state: await page.evaluate(DUMP) });
  await page.screenshot({ path: OUT + "/shot_" + LABEL + "_closed.png" });
  const mb = await page.evaluate(() => {
    const m = Array.from(document.querySelectorAll("button")).find((e) => (e.textContent || "").trim() === "菜单");
    const r = m.getBoundingClientRect(); return [Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2)];
  });
  await page.mouse.click(mb[0], mb[1]);
  await page.waitForTimeout(1500);
  rep.stages.push({ stage: "after_menu_press", state: await page.evaluate(DUMP) });
  await page.screenshot({ path: OUT + "/shot_" + LABEL + "_after_press.png" });
  await browser.close();
  const file = OUT + "/menu_diag2_" + LABEL + ".json";
  fs.writeFileSync(file, JSON.stringify(rep, null, 1), "utf8");
  for (const st of rep.stages) {
    const s = st.state;
    console.log(`[${st.stage}] drawer_id_count=${s.drawer_id_count} menu=${JSON.stringify(s.menu)} testids=${s.visible_testids} backdrop=${JSON.stringify(s.backdrop)}`);
    s.drawers.forEach((d) => console.log(`   drawer#${d.idx} rect=${JSON.stringify(d.rect)} display=${d.display} visibility=${d.visibility} opacity=${d.opacity} pos=${d.position} z=${d.z} items=${d.item_count} self_hits=${d.items.filter((x) => x.hit_is_self).length}`));
    const open = s.drawers.find((d) => d.rect[2] > 0 && d.rect[3] > 0 && d.visibility === "visible");
    if (open) open.items.slice(0, 6).forEach((x) => console.log(`      item "${x.text}" box=${JSON.stringify(x.box)} centre=${JSON.stringify(x.centre)} hit_self=${x.hit_is_self} hit=${x.hit}`));
  }
  console.log("WROTE", file, fs.statSync(file).size, "B");
})();
