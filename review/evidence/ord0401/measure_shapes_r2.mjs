/**
 * ORD-0401 shape ruler r2 -- the quiet row with its title kept.
 *
 * Road ① asks for "一行标题 + 一句空态 + 动作". The title is the load-bearing half of ORD-0384's
 * honesty ("the two things *the server* reports as outstanding"), so the collapse must not drop it --
 * only the long scope note and the two-sentence empty copy may go. This measures the candidate
 * shapes in the live flow at the panel's own anchor, and reads the button centre back, because the
 * height the quiet row ends up with is what decides how far the traveller has to scroll.
 *
 * Reference numbers taken on the same generation by probe_0401_r1: shipped empty panel top 885,
 * height 325 (zh) / 386 (en), action top 1151, action centre 1173, fold 844, usable bottom 768
 * (fixed `v8-mobile-nav` covers 768..844), document height 1589.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = process.env.ORD0401_BASE ?? "http://127.0.0.1:4781";
const OUT = process.env.ORD0401_OUT ?? "D:/moodle/_qoder_q_ord0401_evidence";
mkdirSync(OUT, { recursive: true });
const WIDTHS = (process.env.ORD0401_WIDTHS ?? "320,390").split(",").map(Number);
const LOCALES = (process.env.ORD0401_LOCALES ?? "zh-CN,en-US").split(",");

const MEASURE = ([shapeKey, copy]) => {
  const shapes = {
    shipped: { kicker: true, h2: true, note: true, sentence: "longEmpty" },
    D_kicker_h2_sentence: { kicker: true, h2: true, note: false, sentence: "quiet" },
    E_kicker_sentence: { kicker: true, h2: false, note: false, sentence: "quiet" },
    F_h2_sentence: { kicker: false, h2: true, note: false, sentence: "quiet" },
    G_naming_sentence: { kicker: true, h2: true, note: false, sentence: "naming" },
  };
  const shape = shapes[shapeKey];
  const panel = document.querySelector('[data-testid="pretrip-checklist"]');
  if (!panel) return { error: "no panel" };
  const before = {
    panel_top: Math.round(panel.getBoundingClientRect().top + window.scrollY),
    doc_height: document.scrollingElement.scrollHeight,
  };
  panel.style.display = "none";
  const host = document.createElement("section");
  host.className = "cn-pretrip";
  /* Put the candidate in the panel's own slot: same parent, same following sibling, so its box is
     the box the shipped quiet row would have. */
  const next = panel.nextElementSibling;
  if (next) next.parentNode.insertBefore(host, next);
  else panel.parentNode.appendChild(host);
  const head = document.createElement("div");
  head.className = "cn-pretrip-head";
  const inner = document.createElement("div");
  if (shape.kicker) {
    const k = document.createElement("span");
    k.className = "v8-kicker";
    k.textContent = copy.kicker;
    inner.appendChild(k);
  }
  if (shape.h2) {
    const h = document.createElement("h2");
    h.textContent = copy.h2;
    inner.appendChild(h);
  }
  head.appendChild(inner);
  if (shape.note) {
    const p = document.createElement("p");
    p.className = "cn-pretrip-note";
    p.textContent = copy.note;
    head.appendChild(p);
  }
  if (shape.kicker || shape.h2 || shape.note) host.appendChild(head);
  const row = document.createElement("div");
  row.className = "cn-pretrip-empty";
  const s = document.createElement("span");
  s.textContent = copy[shape.sentence];
  row.appendChild(s);
  const b = document.createElement("button");
  b.type = "button";
  b.className = "v8-quiet-button";
  b.textContent = copy.action;
  row.appendChild(b);
  host.appendChild(row);

  const hb = b.getBoundingClientRect();
  const hBox = host.getBoundingClientRect();
  const out = {
    shape: shapeKey,
    panel_top: Math.round(hBox.top + window.scrollY),
    panel_height: Math.round(hBox.height),
    action_y: Math.round(hb.y + window.scrollY),
    action_centre: Math.round(hb.y + hb.height / 2 + window.scrollY),
    action_h: Math.round(hb.height),
    doc_height: document.scrollingElement.scrollHeight,
    doc_height_delta: document.scrollingElement.scrollHeight - before.doc_height,
    scroll_px_needed_to_reach_centre: Math.max(
      0,
      Math.round(hb.y + hb.height / 2 + window.scrollY - window.innerHeight + hb.height / 2),
    ),
    distance_to_usable_bottom_768: Math.round(hb.y + hb.height / 2 + window.scrollY - 768),
  };
  host.remove();
  panel.style.display = "";
  return out;
};

const COPY = {
  "zh-CN": {
    kicker: "行前清单",
    h2: "服务端报出的两类待办",
    note: "这里只列契约写明依据的两类检查：这一代方案的可行性失败、以及等待你决定的恢复方案。完成状态由服务端事实自己消失，不需要你打勾；没跑过的检查不会被打勾，也不会出现在这里。",
    longEmpty:
      "服务端这一代没有报出可行性失败，也没有等待你决定的恢复方案。这里只列契约已经写明依据的两类检查，其余没跑过的检查不会被打勾，也不会出现在这里。",
    quiet: "这一代都没有报出",
    naming: "可行性失败、以及等待你决定的恢复方案，这一代都没有报出",
    action: "去看这一代方案",
  },
  "en-US": {
    kicker: "Before you go",
    h2: "The two things the server reports as outstanding",
    note: "Only the two checks whose fields the contract declares live here: feasibility failures on this plan generation, and a recovery awaiting your decision. Items disappear when the server's fact changes -- nothing is ticked by hand, and a check that was not run is never shown as passed and never shown at all.",
    longEmpty:
      "This generation of the plan reports no feasibility failures and no recovery awaiting your decision. Only the two checks whose fields the contract names live here; a check that was not run is never ticked, and never listed.",
    quiet: "Neither one is open on this generation",
    naming: "No feasibility failure, and no recovery awaiting your decision, on this generation",
    action: "Review this plan generation",
  },
};

const browser = await chromium.launch();
const report = { base: BASE, widths: WIDTHS, arms: [] };
for (const locale of LOCALES) {
  for (const width of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width, height: 844 } });
    const page = await ctx.newPage();
    await page.addInitScript((v) => localStorage.setItem("citynexus.locale", v), locale);
    await page.route((url) => url.pathname.startsWith("/api/"), async (route) =>
      route.request().method() === "GET" ? route.continue() : route.fulfill({ status: 405, body: "{}" }),
    );
    await page.goto(`${BASE}/v8`, { waitUntil: "load" });
    await page.waitForTimeout(1200);
    const demo = page.getByTestId("trial-tianjin-demo");
    if (await demo.count()) {
      await demo.click();
      await page.waitForFunction(() => !!localStorage.getItem("citynexus.v8.journey_id"), null, { timeout: 30_000 }).catch(() => {});
    }
    await page.goto(`${BASE}/v8/hub`, { waitUntil: "load" });
    await page.waitForTimeout(2200);
    const results = [];
    for (const shapeKey of ["shipped", "D_kicker_h2_sentence", "E_kicker_sentence", "F_h2_sentence", "G_naming_sentence"]) {
      results.push(await page.evaluate(MEASURE, [shapeKey, COPY[locale]]));
    }
    report.arms.push({ locale, width, results });
    console.log(`\n=== ${locale} @ ${width}x844 ===`);
    for (const r of results) {
      if (r.error) continue;
      console.log(
        `  ${r.shape.padEnd(20)} top=${String(r.panel_top).padStart(4)} h=${String(r.panel_height).padStart(4)} action_y=${String(r.action_y).padStart(4)} centre=${String(r.action_centre).padStart(4)} doc=${r.doc_height} d=${r.doc_height_delta} to_768=${r.distance_to_usable_bottom_768}`,
      );
    }
    await ctx.close();
  }
}
await browser.close();
writeFileSync(`${OUT}/shape_budget_r2.json`, JSON.stringify(report, null, 2));
