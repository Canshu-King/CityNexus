const { chromium } = require("D:/moodle/_qoder_n3_ord0440/frontend/node_modules/playwright");
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  const p = await ctx.newPage();
  await p.goto("http://127.0.0.1:49970/v8/discover", { waitUntil: "load" });
  await p.evaluate(async (tok) => { await fetch("/api/v1/demo/reset", { method: "POST", headers: { "content-type": "application/json", "X-Demo-Reset-Token": tok }, body: "{}" }); }, process.argv[2]);
  const scene = await p.evaluate(() => fetch("/api/v1/demo/scene").then(r => r.json()));
  await p.addInitScript(([l, j]) => { localStorage.setItem("citynexus.locale", l); localStorage.setItem("citynexus.v8.journey_id", j); }, ["zh-CN", scene.journey_id]);
  await p.goto("http://127.0.0.1:49970/v8/discover", { waitUntil: "load" });
  const seal = p.getByText(/使用封存的演示行程|sealed demo/i).first();
  if (await seal.count()) { await seal.click(); await p.waitForTimeout(1200); }
  await p.waitForSelector('[data-testid="prep-panel"]');
  const snap = () => p.evaluate(() => {
    const out = {};
    document.querySelectorAll("body *").forEach((el, i) => {
      const r = el.getBoundingClientRect();
      if (r.top > 400) return;
      const key = (el.tagName + "." + (el.className && el.className.toString ? el.className.toString() : "")).slice(0, 60) + "#" + i;
      out[key] = [Math.round(r.top), Math.round(r.height)];
    });
    return out;
  });
  const a = await snap();
  await p.waitForTimeout(600);
  const bb = await snap();
  const changed = [];
  for (const k of Object.keys(a)) {
    if (bb[k] && JSON.stringify(a[k]) !== JSON.stringify(bb[k])) changed.push([k, a[k], bb[k]]);
  }
  console.log("elements_above_400px_sampled", Object.keys(a).length, "changed_in_600ms", changed.length);
  for (const c of changed.slice(0, 12)) console.log("  ", c[0], c[1], "->", c[2]);
  await b.close();
})().catch((e) => { console.log("PROBE_CRASH", String(e).slice(0, 200)); process.exit(1); });
