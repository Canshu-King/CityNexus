/* Commander's jitter probe: does an element on the wizard actually move, or does React re-mount it?

Why: ORD-0349's node `the two legs render as two pictures` screenshots
`[data-testid="trial-sealed-unavailable"]` and hashes the pixels. On lane N1's tree it passed; on a tree that
also contains ORD-0338 甲 it fails with "element is not stable" until the 60 s test timeout. Two causes look
identical from the outside and need different owners:
  (a) the box really keeps moving  -> layout/product defect introduced by 甲, fix belongs to lane D;
  (b) the box is still but the node is re-created (React re-render, e.g. a poll) -> the screenshot comparison
      is the fragile instrument, and the fix belongs to the gate's owner (lane N1), not to the product.
So this samples the bounding rect AND watches the DOM for re-attachment of that node, over the same window
Playwright was waiting in.

usage: node cmdr_jitter_probe_r1.js --wt <worktree> [--seconds 6]
*/
const path = require("path");
const fs = require("fs");
const NM = "D:/moodle/CityNexus/frontend/node_modules";
const { chromium, devices } = require(path.join(NM, "playwright"));

const arg = (k, d) => {
  const i = process.argv.indexOf(k);
  return i > 0 && process.argv[i + 1] ? process.argv[i + 1] : d;
};
const WT = arg("--wt", "D:/moodle/_qoder_cmdr_bisect_0349jia");
const SECONDS = Number(arg("--seconds", "6"));
const OUT = arg("--out", "patrol/jitter_probe.json");

(async () => {
  const front = path.join(WT, "frontend");
  const { spawn } = require("child_process");
  const port = Number(arg("--port", "4461"));
  const srv = spawn("node", ["node_modules/vite/bin/vite.js", "dev", "--host", "127.0.0.1",
                             "--port", String(port)], { cwd: front, shell: true });
  let out = { wt: WT, port, started: new Date().toString() };
  const wait = ms => new Promise(r => setTimeout(r, ms));
  async function up() {
    for (let i = 0; i < 90; i++) {
      try { const r = await fetch(`http://127.0.0.1:${port}/`); if (r.ok) return true; } catch (e) {}
      await wait(1000);
    }
    return false;
  }
  const browser = await chromium.launch();
  try {
    if (!(await up())) { out.error = "vite never answered"; }
    const ctx = await browser.newContext({ ...devices["Pixel 5"], locale: "zh-CN" });
    const page = await ctx.newPage();
    await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle", timeout: 90000 });
    await page.waitForTimeout(2500);
    // The alert node only exists in the sealed-demo state; get there the way a traveller does.
    if (!(await page.locator('[data-testid="trial-sealed-unavailable"]').count())) {
      const btn = page.getByText("使用封存的演示行程", { exact: false }).first();
      if (await btn.count()) {
        await btn.click({ timeout: 8000 }).catch(() => {});
        // --settle 0 samples from the first frame after the click: the point of this probe is whether
        // motion is transient (a scroll animation that ends) or never-ending.  lane N1's node failed for
        // the whole 60 s test timeout, so "it settles later" is not an answer I can accept without looking.
        await page.waitForTimeout(Number(arg("--settle", "0")));
      }
      out.pre_click_used = true;
      out.settle_ms = Number(arg("--settle", "0"));
    }
    out.probe = await page.evaluate(async (seconds) => {
      const sel = '[data-testid="trial-sealed-unavailable"]';
      const el = document.querySelector(sel);
      if (!el) return { present: false, body_head: document.body.innerText.slice(0, 200) };
      const rects = [], t0 = performance.now();
      let reattach = 0, mutation = 0;
      const parent = el.parentElement;
      const mo = new MutationObserver(recs => {
        for (const r of recs) {
          mutation++;
          for (const n of r.removedNodes) if (n === el) reattach++;
          for (const n of r.addedNodes) if (n === el) reattach++;
        }
      });
      mo.observe(parent, { childList: true });
      while (performance.now() - t0 < seconds * 1000) {
        const b = el.getBoundingClientRect();
        const sc = document.querySelector('.cn-onboarding__scroll');
        rects.push([Math.round(performance.now() - t0), +b.x.toFixed(2), +b.y.toFixed(2),
                    +b.width.toFixed(2), +b.height.toFixed(2),
                    sc ? Math.round(sc.scrollTop) : null]);
        await new Promise(r => requestAnimationFrame(() => r()));
        await new Promise(r => setTimeout(r, 40));
      }
      mo.disconnect();
      const xs = new Set(rects.map(r => r[1])), ys = new Set(rects.map(r => r[2]));
      const ws = new Set(rects.map(r => r[3])), hs = new Set(rects.map(r => r[4]));
      const tops = new Set(rects.map(r => r[5]));
      return {
        present: true, samples: rects.length,
        distinct_x: xs.size, distinct_y: ys.size, distinct_w: ws.size, distinct_h: hs.size,
        distinct_scrollTop: tops.size, scroll_tops_seen: Array.from(tops).slice(0, 12),
        moved: xs.size > 1 || ys.size > 1,
        reattached: reattach, mutations: mutation,
        first: rects[0], last: rects[rects.length - 1],
        parent_tag: parent && parent.tagName, scroll_containers: Array.from(
          document.querySelectorAll('.cn-onboarding__scroll')).map(n => ({
            scrollTop: Math.round(n.scrollTop), scrollHeight: n.scrollHeight, clientHeight: n.clientHeight,
          })),
      };
    }, SECONDS);
  } finally {
    srv.kill("SIGTERM");
    require("fs").mkdirSync(path.dirname(OUT), { recursive: true });
    require("fs").writeFileSync(OUT, JSON.stringify(out, null, 1));
    console.log(JSON.stringify(out.probe ?? out, null, 1));
    console.log("verdict_moved=" + (out.probe && out.probe.moved) +
                " reattached=" + (out.probe && out.probe.reattached) + " -> " + OUT);
    await browser.close();
  }
})();
