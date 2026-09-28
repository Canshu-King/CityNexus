const { chromium } = require("D:/moodle/_qoder_n3_ord0440/frontend/node_modules/playwright");
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  const p = await ctx.newPage();
  await p.goto("http://127.0.0.1:49970/v8/discover", { waitUntil: "load" });
  await p.evaluate(async (tok) => {
    await fetch("/api/v1/demo/reset", { method: "POST", headers: { "content-type": "application/json", "X-Demo-Reset-Token": tok }, body: "{}" });
  }, process.argv[2]);
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
  const boxes = await p.evaluate(async () => {
    const out = [];
    const el = document.querySelector('[data-testid="prep-survey-reason-WE_WERE_UNCLEAR"]');
    for (let i = 0; i < 20; i++) {
      const r = el.getBoundingClientRect();
      out.push([Math.round(r.top), Math.round(r.left), Math.round(r.height), window.scrollY]);
      await new Promise((res) => setTimeout(res, 200));
    }
    return out;
  });
  const uniq = [...new Set(boxes.map(JSON.stringify))];
  console.log("samples", boxes.length, "distinct_boxes", uniq.length);
  for (const u of uniq.slice(0, 6)) console.log("   ", u);
  await b.close();
})().catch(e => { console.log("PROBE_CRASH", String(e).slice(0, 200)); process.exit(1); });
