/**
 * ORD-0392 · per-tab testid hit counts at 390x844, run against two generations of the same shell.
 *
 * The tab names are the ones the commander measured, not guesses: `frontend/src/app/V8Experience.tsx`
 * builds the bottom bar as `data-testid={`nav-${item.key}`}`, so the five real names are
 * nav-hub / nav-trips / nav-map / nav-agent / nav-me.
 *
 * Both ports serve a different bundle over the SAME lane-private backend (:8713, a copied sqlite --
 * never `_preview.db`, never :8693/:4781, no demo/reset).  If the registry fold changed what is on
 * screen, the ordered testid list per tab differs; that is the whole acceptance.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const TABS = ["nav-hub", "nav-trips", "nav-map", "nav-agent", "nav-me"];
const JID = "9c6c3d73-8b8e-4f71-beaf-32bc87aba035";
const OUT = "D:/moodle/_qoder_q_ord0369_wk/tabs_0392";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();

async function walk(base, tag) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: "zh-CN" });
  const page = await ctx.newPage();
  await page.addInitScript(([jid, loc]) => {
    localStorage.setItem("citynexus.locale", loc);
    localStorage.setItem("citynexus.v8.journey_id", jid);
  }, [JID, "zh-CN"]);
  const rows = [];
  for (const tab of TABS) {
    await page.goto(`${base}/v8`, { waitUntil: "load" });
    await page.waitForTimeout(2200);
    const control = page.getByTestId(tab);
    const present = await control.count();
    let clicked = false;
    if (present) {
      await control.first().click().then(() => { clicked = true; }).catch(() => {});
      await page.waitForTimeout(1400);
    }
    const read = await page.evaluate(() => {
      const ids = Array.from(document.querySelectorAll("[data-testid]"))
        .map((el) => el.getAttribute("data-testid"));
      const visible = Array.from(document.querySelectorAll("[data-testid]"))
        .filter((el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; })
        .map((el) => el.getAttribute("data-testid"));
      const centreHit = (name) => {
        const el = document.querySelector(`[data-testid="${name}"]`);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) return false;
        const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
        return !!(top && (top === el || el.contains(top) || top.contains(el)));
      };
      return {
        url: location.pathname,
        ids, visible,
        chars: (document.body.innerText || "").length,
        pretrip: visible.filter((x) => x.startsWith("pretrip")).length,
        nav_hit: ["nav-hub", "nav-trips", "nav-map", "nav-agent", "nav-me"].map((n) => [n, centreHit(n)]),
      };
    });
    rows.push({
      tab, control_present: present, clicked: clicked, url: read.url,
      testids_total: read.ids.length, testids_visible: read.visible.length,
      body_chars: read.chars, pretrip_visible: read.pretrip,
      nav_centre_hit: Object.fromEntries(read.nav_hit),
      visible_ids: read.visible,
      screenshot: `${OUT}/${tag}-${tab}.png`,
    });
    await page.screenshot({ path: `${OUT}/${tag}-${tab}.png` });
  }
  await ctx.close();
  return rows;
}

const before = await walk("http://127.0.0.1:4292", "base-0598e4d1");
const after = await walk("http://127.0.0.1:4293", "mine-e54cc36f");

const diffs = [];
for (let i = 0; i < TABS.length; i += 1) {
  const a = before[i];
  const b = after[i];
  for (const f of ["url", "testids_total", "testids_visible", "body_chars", "pretrip_visible"]) {
    if (a[f] !== b[f]) diffs.push(`${a.tab}.${f}: ${a[f]} -> ${b[f]}`);
  }
  if (JSON.stringify(a.visible_ids) !== JSON.stringify(b.visible_ids)) {
    const only = a.visible_ids.filter((x) => !b.visible_ids.includes(x));
    const added = b.visible_ids.filter((x) => !a.visible_ids.includes(x));
    diffs.push(`${a.tab}.ordered_visible_testids differ only_removed=${JSON.stringify(only)} added=${JSON.stringify(added)}`);
  }
}

writeFileSync(`${OUT}/tabs_compare_r3.json`,
  JSON.stringify({ generatedBy: "tabs_0392_r3", viewport: "390x844", backend: ":8713 lane-private copy",
    before, after, diffs }, null, 2) + "\n", "utf-8");
console.log("tab | base ids/vis/chars/pretrip | mine ids/vis/chars/pretrip");
for (let i = 0; i < TABS.length; i += 1) {
  const a = before[i]; const b = after[i];
  console.log(`${a.tab} | ${a.testids_total}/${a.testids_visible}/${a.body_chars}/${a.pretrip_visible} | ${b.testids_total}/${b.testids_visible}/${b.body_chars}/${b.pretrip_visible} | nav_hit_all=${Object.values(b.nav_centre_hit).every(Boolean)}`);
}
console.log("\ndiffs:", diffs.length ? diffs : "none -- same ordered testids on every tab");
await browser.close();
