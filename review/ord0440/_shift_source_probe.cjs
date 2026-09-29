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
  await p.fill('[data-testid="prep-query"]', "云和县");
  await p.click('[data-testid="prep-check"]');
  await p.waitForSelector('[data-testid="prep-verdict"]');
  await p.click('[data-testid="prep-start"]');
  await p.waitForSelector('[data-testid="prep-abandon"]', { timeout: 20000 });
  await p.click('[data-testid="prep-abandon"]');
  await p.waitForSelector('[data-testid="prep-survey"]');
  const series = await p.evaluate(async () => {
    const sel = { topbar: "header, .v8-topbar, .v8-header", kicker: '[data-testid="prep-survey-context"]', sheet: '[data-testid="prep-survey"]', box4: '[data-testid="prep-survey-reason-WE_WERE_UNCLEAR"]' };
    const out = [];
    for (let i = 0; i < 18; i++) {
      const row = {};
      for (const [k, s] of Object.entries(sel)) {
        const el = document.querySelector(s);
        if (!el) { row[k] = null; continue; }
        const r = el.getBoundingClientRect();
        row[k] = [Math.round(r.top), Math.round(r.height)];
      }
      out.push(row);
      await new Promise((res) => setTimeout(res, 200));
    }
    return out;
  });
  const keys = Object.keys(series[0]);
  for (const k of keys) {
    const uniq = [...new Set(series.map((s) => JSON.stringify(s[k])))];
    console.log(k, "distinct", uniq.length, uniq.slice(0, 4).join(" "));
  }
  await b.close();
})().catch((e) => { console.log("PROBE_CRASH", String(e).slice(0, 200)); process.exit(1); });
