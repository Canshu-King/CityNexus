/**
 * ORD-0401 shape ruler -- how tall may the empty state be before its action leaves the first screen?
 *
 * The order offers two roads and asks for one to be chosen with a reason. Both roads are decided by
 * one number: the y that the action's centre lands at, given the anchor the panel is mounted at. The
 * measured anchors on the live generation are hero-grid bottom 761, `today-strip` top 771, attention
 * band top 840, panel top 885, fold 844. So *anything* mounted at the current anchor starts 41 px
 * below the screen -- road ① alone cannot reach it no matter what it renders -- and the "before
 * today-strip" anchor leaves 73 px (844 - 771) of budget for card padding + text + a >=44px touch row
 * (Amendment F-2).
 *
 * This instrument does not model that budget and does not position anything absolutely. It inserts a
 * candidate into the *live flow* at the anchor under test, reads the button's real bounding box, and
 * reads where the attention band and the today strip land as a result -- so the cost of the change is
 * measured in the same pass as its benefit. Then it removes the candidate. Copy is the page's own
 * font stack, so line breaks are the browser's answer, not mine.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = process.env.ORD0401_BASE ?? "http://127.0.0.1:4781";
const OUT = process.env.ORD0401_OUT ?? "D:/moodle/_qoder_q_ord0401_evidence";
mkdirSync(OUT, { recursive: true });
const WIDTHS = (process.env.ORD0401_WIDTHS ?? "320,360,390,414").split(",").map(Number);

/* One quiet row, three copy lengths, plus the shipped shape measured where it actually sits. */
const SHAPES = {
  current: { head: true, pieces: ["LONG_EMPTY"] },
  A: { head: false, pieces: ["TITLE", "SHORT", "ACTION"] },
  B: { head: false, pieces: ["SUBJECT", "ACTION"] },
  C: { head: false, pieces: ["TIGHT", "ACTION"] },
};

const MEASURE_FLOW = ([shapeKey, copy, anchor]) => {
  /* Inlined because `page.evaluate` ships this function's source to the page: a helper defined out
     here would not exist there. */
  const BUILD = (key, c) => {
    const shapes = {
      current: { head: true, pieces: ["LONG_EMPTY"] },
      A: { head: false, pieces: ["TITLE", "SHORT", "ACTION"] },
      B: { head: false, pieces: ["SUBJECT", "ACTION"] },
      C: { head: false, pieces: ["TIGHT", "ACTION"] },
    };
    const shape = shapes[key];
    const host = document.createElement("section");
    host.className = "cn-pretrip";
    host.setAttribute("data-probe", key);
    if (shape.head) {
      const head = document.createElement("div");
      head.className = "cn-pretrip-head";
      head.innerHTML =
        `<div><span class="v8-kicker">${c.title}</span><h2>${c.h2}</h2></div>` +
        `<p class="cn-pretrip-note">${c.note}</p>`;
      host.appendChild(head);
    }
    const row = document.createElement("div");
    row.className = "cn-pretrip-empty";
    for (const piece of shape.pieces) {
      const el = document.createElement(piece === "ACTION" ? "button" : "span");
      if (piece === "ACTION") {
        el.className = "v8-quiet-button";
        el.type = "button";
      }
      el.textContent =
        piece === "TITLE" ? c.title
        : piece === "LONG_EMPTY" ? c.longEmpty
        : piece === "SHORT" ? c.shortSentence
        : piece === "SUBJECT" ? c.subjectSentence
        : piece === "TIGHT" ? c.tightSentence
        : c.action;
      row.appendChild(el);
    }
    host.appendChild(row);
    return host;
  };
  const panel = document.querySelector('[data-testid="pretrip-checklist"]');
  const strip = document.querySelector('[data-testid="today-strip"]');
  const band = document.querySelector('[data-testid="today-attention-band"]');
  if (!panel || !strip || !band) return { error: "anchor missing" };
  const pre = {
    strip_top: Math.round(strip.getBoundingClientRect().top + window.scrollY),
    band_top: Math.round(band.getBoundingClientRect().top + window.scrollY),
    doc_height: document.scrollingElement.scrollHeight,
  };
  const host = BUILD(shapeKey, copy);
  const target =
    anchor === "before-today-strip"
      ? strip
      : anchor === "current-anchor"
        ? panel
        : null;
  if (!target) return { error: "unknown anchor" };
  /* The shipped panel is hidden for its own anchor's reading so the two checklists cannot stack. */
  if (anchor === "current-anchor") panel.style.display = "none";
  target.parentNode.insertBefore(host, target);
  const btn = host.querySelector("button");
  const hb = btn?.getBoundingClientRect();
  const hBox = host.getBoundingClientRect();
  const after = {
    strip_top: Math.round(strip.getBoundingClientRect().top + window.scrollY),
    band_top: Math.round(band.getBoundingClientRect().top + window.scrollY),
    doc_height: document.scrollingElement.scrollHeight,
  };
  const out = {
    shape: shapeKey,
    anchor,
    panel_top: Math.round(hBox.top + window.scrollY),
    panel_height: Math.round(hBox.height),
    action: hb
      ? {
          y: Math.round(hb.y + window.scrollY),
          h: Math.round(hb.height),
          w: Math.round(hb.width),
          centre_y: Math.round(hb.y + hb.height / 2 + window.scrollY),
        }
      : null,
    action_centre_in_first_screen: hb ? hb.y + hb.height / 2 <= window.innerHeight : null,
    action_top_in_first_screen: hb ? hb.y + window.scrollY <= window.innerHeight : null,
    hit_test_at_centre: hb
      ? (() => {
          const el = document.elementFromPoint(
            hb.x + hb.width / 2,
            hb.y + hb.height / 2,
          );
          return el ? el.tagName.toLowerCase() + "." + (el.className || "") : "null(outside viewport)";
        })()
      : null,
    push_down: {
      today_strip_px: after.strip_top - pre.strip_top,
      attention_band_px: after.band_top - pre.band_top,
      band_top_after: after.band_top,
      doc_height_delta: after.doc_height - pre.doc_height,
    },
    band_reachable_after_change: after.band_top <= window.innerHeight,
  };
  host.remove();
  if (anchor === "current-anchor") panel.style.display = "";
  return out;
};

const COPY = {
  "zh-CN": {
    title: "行前清单",
    h2: "服务端报出的两类待办",
    note: "这里只列契约写明依据的两类检查：这一代方案的可行性失败、以及等待你决定的恢复方案。完成状态由服务端事实自己消失，不需要你打勾；没跑过的检查不会被打勾，也不会出现在这里。",
    longEmpty:
      "服务端这一代没有报出可行性失败，也没有等待你决定的恢复方案。这里只列契约已经写明依据的两类检查，其余没跑过的检查不会被打勾，也不会出现在这里。",
    action: "去看这一代方案",
    shortSentence: "契约内两类检查这一代都没报出",
    subjectSentence: "行前清单：契约内两类检查这一代都没报出",
    tightSentence: "契约内两类检查都没有报出",
  },
  "en-US": {
    title: "Before you go",
    h2: "The two things the server reports as outstanding",
    note: "Only the two checks whose fields the contract declares live here: feasibility failures on this plan generation, and a recovery awaiting your decision. Items disappear when the server's fact changes -- nothing is ticked by hand, and a check that was not run is never shown as passed and never shown at all.",
    longEmpty:
      "This generation of the plan reports no feasibility failures and no recovery awaiting your decision. Only the two checks whose fields the contract names live here; a check that was not run is never ticked, and never listed.",
    action: "Review this plan generation",
    shortSentence: "Neither check the contract names is open",
    subjectSentence: "Before you go: neither check the contract names is open",
    tightSentence: "Neither named check is open",
  },
};

const browser = await chromium.launch();
const report = { base: BASE, widths: WIDTHS, arms: [] };

for (const locale of Object.keys(COPY)) {
  for (const width of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width, height: 844 } });
    const page = await ctx.newPage();
    await page.addInitScript((v) => localStorage.setItem("citynexus.locale", v), locale);
    await page.route(
      (url) => url.pathname.startsWith("/api/"),
      async (route) =>
        route.request().method() === "GET"
          ? route.continue()
          : route.fulfill({ status: 405, contentType: "application/json", body: "{}" }),
    );
    await page.goto(`${BASE}/v8`, { waitUntil: "load" });
    await page.waitForTimeout(1200);
    const demo = page.getByTestId("trial-tianjin-demo");
    if (await demo.count()) {
      await demo.click();
      await page
        .waitForFunction(() => !!localStorage.getItem("citynexus.v8.journey_id"), null, { timeout: 30_000 })
        .catch(() => {});
    }
    await page.goto(`${BASE}/v8/hub`, { waitUntil: "load" });
    await page.waitForTimeout(2200);
    const results = [];
    for (const shapeKey of Object.keys(SHAPES)) {
      for (const anchor of ["current-anchor", "before-today-strip"]) {
        if (shapeKey === "current" && anchor === "before-today-strip") continue;
        results.push(
          await page.evaluate(MEASURE_FLOW, [shapeKey, COPY[locale], anchor]),
        );
      }
    }
    report.arms.push({
      locale,
      width,
      shipped: results.find((r) => r.shape === "current"),
      candidates: results.filter((r) => r.shape !== "current"),
    });
    await ctx.close();
  }
}
await browser.close();
writeFileSync(`${OUT}/shape_budget_r1.json`, JSON.stringify(report, null, 2));

for (const arm of report.arms) {
  console.log(`\n=== ${arm.locale} @ ${arm.width}x844 ===`);
  for (const r of [arm.shipped, ...arm.candidates]) {
    if (!r || r.error) continue;
    console.log(
      `${r.shape.padEnd(8)} @${r.anchor.padEnd(19)} panel_top=${String(r.panel_top).padStart(4)} h=${String(r.panel_height).padStart(3)} action_y=${String(r.action?.y).padStart(4)} centre=${String(r.action?.centre_y).padStart(4)} in_fold=${String(r.action_centre_in_first_screen).padEnd(5)} band_push=${String(r.push_down.attention_band_px).padStart(3)} band_top_after=${r.push_down.band_top_after}`,
    );
  }
}
