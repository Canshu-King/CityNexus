/* ORD-0575 复现腿（playwright 侧）：两臂 × 三档，展开 details 后量提交键的中心命中与重叠面积。
   红线：一次写请求都不发——只点 summary（原生展开，不改服务端），绝不点提交键、不打标、不提问。
   函数全部自包含：playwright 只送被调那一枚的源码（件 RK-163129 的教训）。 */
const { chromium } = require("playwright");
const fs = require("fs");

const PROBE_FILE = process.env.RK_PROBE;
const src = fs.readFileSync(PROBE_FILE, "utf-8").replace(/module\.exports[\s\S]*$/, "");
const PROBE = (0, eval)(src + "\n;PROBE");

const BASE = process.env.RK_BASE;
const JID = process.env.RK_JID;
const OUT = process.env.RK_OUT;
const SHOTS = process.env.RK_SHOTS;
const ARMS = [{ locale: "zh-CN", arm: "zh-CN" }, { locale: "en-US", arm: "en-US" }];
const WIDTHS = [360, 390, 414];

(async () => {
  const doc = { run_id: process.env.RK_RUN || "", base: BASE, tree_at: process.env.RK_TREE || "",
                probe_file: PROBE_FILE, legs: [], errors: [] };
  const browser = await chromium.launch();
  try {
    for (const a of ARMS) {
      for (const w of WIDTHS) {
        const ctx = await browser.newContext({
          viewport: { width: w, height: 844 }, deviceScaleFactor: 2,
          isMobile: true, hasTouch: true, serviceWorkers: "block", locale: a.locale,
        });
        const page = await ctx.newPage();
        const perr = [];
        page.on("pageerror", (e) => perr.push(String(e).slice(0, 200)));
        page.on("console", (m) => { if (m.type() === "error") perr.push("console:" + m.text().slice(0, 160)); });
        await page.goto(BASE + "/v8/hub", { waitUntil: "networkidle", timeout: 60000 });
        await page.evaluate(([loc, jid]) => {
          localStorage.setItem("citynexus.locale", loc);
          localStorage.setItem("citynexus.v8.journey_id", jid);
        }, [a.locale, JID]);
        await page.goto(BASE + "/v8/trips", { waitUntil: "networkidle", timeout: 60000 });
        const seen = await page.evaluate(() => ({
          href: location.href,
          hasAbort: !!document.querySelector("[data-testid='journey-abort']"),
          hasSummary: !!document.querySelector("[data-testid='journey-abort-open']"),
          state: (document.querySelector("[data-testid='journey-abort']") || {}).getAttribute
            ? document.querySelector("[data-testid='journey-abort']").getAttribute("data-abort-state")
            : null,
        }));
        if (!seen.hasAbort || !seen.hasSummary) {
          doc.errors.push({ arm: a.arm, vw: w, why: "屏上没凑齐 journey-abort 与它的 summary",
                            href: seen.href, state: seen.state });
          await ctx.close();
          continue;
        }
        const wasOpen = await page.evaluate(() => {
          const d = document.querySelector("[data-testid='journey-abort'] details.cn-abort__form");
          return !!(d && d.open);
        });
        if (!wasOpen) {
          await page.locator("[data-testid='journey-abort-open']").first().evaluate((n) => n.click());
          await page.waitForTimeout(500);
        }
        const openedNow = await page.evaluate(() => {
          const d = document.querySelector("[data-testid='journey-abort'] details.cn-abort__form");
          return !!(d && d.open);
        });
        const r = await page.evaluate(PROBE, {
          at: new Date().toISOString(), arm: a.arm, vw: w,
          label: "trips/journey-abort-open/" + a.arm + "/" + w,
        });
        // 负对照：把一枚正文盒刻意撑到提交键上，这把尺必须报"中心被接走"，
        // 否则那个 0 是空尺读出来的 0（新闸必须有一次"该红的那一次"）。
        const neg = await page.evaluate(PROBE, {
          at: new Date().toISOString(), arm: a.arm, vw: w, plant_lede: true,
          label: "negative-control/" + a.arm + "/" + w,
        });
        r.negative_control = neg.negative_control;
        // 判"咬没咬"必须读负对照那一次自己算出来的命中，不是读未种之前的 cells[0]
        // （cells[0] 是同一枚 PROBE 在种下去之前算的 hit，拿它判恒不咬＝我自己造的空尺）。
        r.neg_hits_self = (neg.negative_control || {}).hits_self;
        r.neg_hit_name = (neg.negative_control || {}).hit_name;
        r.neg_overlap = (neg.negative_control || {}).overlap;
        r.arm = a.arm; r.vw = w; r.landed = seen.href; r.was_open_before = wasOpen;
        r.opened_now = openedNow; r.abort_state = seen.state;
        r.page_errors = perr.slice(0, 5);
        doc.legs.push(r);
        await page.screenshot({ path: SHOTS + "/abort_" + w + "_" + a.arm + ".png" }).catch(() => {});
        await ctx.close();
      }
    }
  } catch (e) {
    doc.errors.push({ fatal: String(e).slice(0, 300) });
  } finally {
    await browser.close();
  }
  fs.writeFileSync(OUT, JSON.stringify(doc, null, 1) + "\n", "utf-8");
  let hits = 0, stolen = 0;
  for (const L of doc.legs) {
    const k = L.cells[0];
    if (k.button_hits_self) hits++; else stolen++;
    console.log("{arm}/{vw} 开层={o} 键 {bx}..{by} 中心 ({cx},{cy}) 命中自己={h} 接走者={w}"
      .replace("{arm}", L.arm).replace("{vw}", L.vw).replace("{o}", k ? k.opened : "?")
      .replace("{bx}", k ? k.button_rect.left + ".." + k.button_rect.right : "?")
      .replace("{by}", k ? k.button_rect.top + ".." + k.button_rect.bottom : "?")
      .replace("{cx}", k ? k.button_centre.x : "?").replace("{cy}", k ? k.button_centre.y : "?")
      .replace("{h}", k ? k.button_hits_self : "?")
      .replace("{w}", k ? String(k.hit_name).slice(0, 46) : "?"));
    if (k && k.overlapping_ledes.length) {
      for (const ov of k.overlapping_ledes) {
        console.log("    重叠 " + ov.overlap_with_button + " px2 于 " + ov.name +
          "「" + ov.text.slice(0, 28) + "」 rect " + ov.rect.top + ".." + ov.rect.bottom);
      }
    }
  }
  console.log("腿=" + doc.legs.length + " 命中自己=" + hits + " 中心被接走=" + stolen +
    " 页面异常=" + doc.legs.reduce((s, L) => s + (L.page_errors || []).length, 0) +
    " errors=" + doc.errors.length);
  process.exit(doc.errors.length ? 3 : 0);
})();
