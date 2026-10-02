/* Derived from checkin_phone_r2.cjs by tools/make_probe_r6.py -- do not hand-edit: the
 * derivation is asserted (five replacement points in the three groups below, each matching
 * exactly once: E1 locale from argv, E2 marks counted in both languages plus by state,
 * E3 the CJK inventory and the control labels actually painted).
 *
 * argv: node checkin_phone_r3.cjs <base> <out.json> <tag> <width> <height> <locale>
 */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\wt3\\frontend\\node_modules\\playwright");
const fs = require("fs");
const path = require("path");

const BASE_URL = process.argv[2] || "http://127.0.0.1:4869";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/checkin_r2.json";
const TAG = process.argv[4] || "FACE";
const W = Number(process.argv[5] || 390);
const H = Number(process.argv[6] || 844);
const LOCALE = process.argv[7] || "zh-CN";

const run = { schema: "CNX_PHONE_CHECKIN_R3", face: BASE_URL, generation: TAG,
  locale: LOCALE,
  viewport: { width: W, height: H }, started_local: new Date().toString(),
  rows: [], requests: [], page_errors: 0 };


async function readState(page) {
  return await page.evaluate(() => {
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const vis = (el) => {
      if (!el) return false;
      const b = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && s.display !== "none" &&
        s.visibility !== "hidden" && Number(s.opacity) !== 0;
    };
    const body = document.body.innerText || "";
    const buttons = Array.from(document.querySelectorAll("[data-testid='stop-checkin']"));
    const notices = Array.from(document.querySelectorAll("[data-testid='stop-checkin-notice']"));
    const ownerOf = (el) => {
      const row = el.closest("[data-testid='trip-stop']");
      const title = row ? row.querySelector(".trip-stop-body b") : null;
      return title ? strip(title.innerText) : "OWNER_UNRESOLVED";
    };
    return {
      path: location.pathname,
      rendered_chars: body.length,
      visible_testid_count: Array.from(document.querySelectorAll("[data-testid]")).filter(vis).length,
      stop_count: document.querySelectorAll("[data-testid='trip-stop']").length,
      checkin_button_count: buttons.length,
      checkin_visible_count: buttons.filter(vis).length,
      marks_stamped_words: (body.match(/已打卡/g) || []).length,
      marks_zh_words: (body.match(/已打卡/g) || []).length,
      marks_en_words: (body.match(/Checked in/g) || []).length,
      marks_by_state: Array.from(document.querySelectorAll("[data-testid='stop-checkin']"))
        .filter((e) => e.getAttribute('data-state') === 'stamped').length,
      fresh_words: (body.match(/打卡/g) || []).length - (body.match(/已打卡/g) || []).length,
      button_words: buttons.map((b) => strip(b.innerText)),
      notice_count: notices.length,
      notice_visible_count: notices.filter(vis).length,
      notices: notices.filter(vis).map((e) => strip(e.innerText)),
      notice_owners: notices.filter(vis).map(ownerOf),
      cjk_chars_on_screen: (body.match(/[\u3400-\u9fff\uf900-\ufaff]/g) || []).length,
      cjk_runs_on_screen: Array.from(new Set((body.match(/[\u3400-\u9fff]+/g) || []).slice(0, 12))),
      control_labels_on_screen: Array.from(new Set(Array.from(
        document.querySelectorAll("[data-testid='stop-checkin']"))
        .map((e) => String(e.innerText || '').replace(/\s+/g, ' ').trim()))),
      uuids_on_screen: Array.from(new Set(body.match(
        /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi) || [])),
      screaming_on_screen: Array.from(new Set(body.match(/[A-Z][A-Z0-9]{2,}(?:_[A-Z0-9]+)+/g) || [])),
      dotted_keys_on_screen: Array.from(new Set(
        body.match(/[a-z][a-zA-Z0-9]{2,}\.[a-zA-Z0-9]+/g) || [])),
    };
  });
}

/* Every control is probed one at a time in the main flow below: scrollIntoViewIfNeeded first, then
   elementFromPoint at the centre -- the shape the order demands, no conclusion about reachability
   from a box measured off-screen. */

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: H },
    hasTouch: W <= 500, isMobile: W <= 500, locale: LOCALE });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => { run.page_errors += 1; run.page_error_heads =
    (run.page_error_heads || []).concat(String(e.message).slice(0, 160)); });
  page.on("response", (res) => {
    const req = res.request();
    if (!/checkins/.test(res.url())) return;
    run.requests.push({ method: req.method(), url: res.url(), http_status: res.status() });
  });

  await page.goto(BASE_URL + "/", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(5000);
  const demo = page.locator("[data-testid='trial-tianjin-demo']").first();
  await demo.click({ timeout: 9000 });
  await page.waitForTimeout(9000);
  await page.goto(BASE_URL + "/v8/trips", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(7000);

  run.rows.push({ arm: TAG + "_1_arrived", state: await readState(page) });

  /* Per-control census: scroll, then elementFromPoint at the centre. */
  const census = [];
  const count = await page.locator("[data-testid='stop-checkin']").count();
  for (let i = 0; i < count; i += 1) {
    const loc = page.locator("[data-testid='stop-checkin']").nth(i);
    await loc.scrollIntoViewIfNeeded().catch(() => { });
    await page.waitForTimeout(350);
    const one = await page.evaluate((idx) => {
      const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
      const el = Array.from(document.querySelectorAll("[data-testid='stop-checkin']"))[idx];
      if (!el) return { index: idx, ABSENT: true };
      const r = el.getBoundingClientRect();
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      const at = document.elementFromPoint(cx, cy);
      const row = el.closest("[data-testid='trip-stop']");
      const title = row ? row.querySelector(".trip-stop-body b") : null;
      const nav = document.querySelector(".v8-mobile-nav");
      const navRect = nav ? nav.getBoundingClientRect() : null;
      return {
        index: idx,
        stop: title ? strip(title.innerText) : "UNKNOWN",
        words: strip(el.innerText),
        box: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
        centre: { x: Math.round(cx), y: Math.round(cy) },
        hit_tag: at ? at.tagName : null,
        hit_words: at ? strip(at.innerText || at.textContent) : null,
        hit_self: at ? (at === el || el.contains(at)) : false,
        in_viewport: r.top >= 0 && r.bottom <= innerHeight,
        overlaps_nav: navRect ? (r.bottom > navRect.top && r.top < navRect.bottom) : null,
        disabled: !!el.disabled,
        state: el.getAttribute('data-state'),
      };
    }, i);
    census.push(one);
  }
  run.rows.push({ arm: TAG + "_2_census_after_scroll", buttons: census });
  run.tap_summary = {
    buttons: census.length,
    pressable_by_centre_hit: census.filter((b) => b && b.hit_self).length,
    unpressable_indices: census.filter((b) => b && !b.hit_self).map((b) => b.index),
    boxes: census.map((b) => (b && b.box ? b.box.w + "x" + b.box.h : null)),
  };

  const shot = async (name) => {
    const png = path.join(path.dirname(OUT), "checkin_" + TAG + "_" + name + ".png");
    try {
      await page.screenshot({ path: png, timeout: 9000, animations: "disabled" });
      return { file: path.basename(png), bytes: fs.statSync(png).size };
    } catch (e) {
      return { file: null, reason: "SHOT_NOT_TAKEN_" + String(e.message).slice(0, 70) };
    }
  };
  run.shots = { arrived: await shot("arrived") };

  const pressable = census.filter((b) => b && b.hit_self);
  const freshIdx = pressable.find((b) => b.state === "fresh"
                      || (/^打卡$/.test(b.words) && !/已打卡/.test(b.words))
                      || /^Check in$/.test(b.words));
  run.fresh_stop_basis = freshIdx ? (freshIdx.state === "fresh" ? "data-state=fresh"
                                    : "word-fallback:" + freshIdx.words) : "NONE";
  if (!freshIdx) {
    run.rows.push({ arm: TAG + "_3_tap_an_unstamped_stop",
      ABORT: "NO_UNSTAMPED_PRESSABLE_STOP", pressable_words: pressable.map((b) => b.words) });
  } else {
    await page.locator("[data-testid='stop-checkin']").nth(freshIdx.index).click({ timeout: 6000 });
    await page.waitForTimeout(6000);
    run.rows.push({ arm: TAG + "_3_after_tapping_unstamped", tapped: freshIdx,
      state: await readState(page) });
    run.shots.after_first_tap = await shot("after_first_tap");

    // same stop a second time: the door refuses, and the screen has to say so about THIS stop
    await page.locator("[data-testid='stop-checkin']").nth(freshIdx.index).click({ timeout: 6000 });
    await page.waitForTimeout(6000);
    run.rows.push({ arm: TAG + "_4_after_tapping_the_same_stop_again", tapped: freshIdx,
      state: await readState(page) });
    run.shots.after_duplicate = await shot("after_duplicate");

    // a second, different stop: two rows must show as two marks, not one shared banner
    const second = pressable.find((b) => b.index !== freshIdx.index &&
      /打卡/.test(b.words) && !/已打卡/.test(b.words));
    if (second) {
      await page.locator("[data-testid='stop-checkin']").nth(second.index).click({ timeout: 6000 });
      await page.waitForTimeout(6000);
      run.rows.push({ arm: TAG + "_5_after_tapping_a_second_stop", tapped: second,
        state: await readState(page) });
      run.shots.after_second = await shot("after_second");
    } else {
      run.rows.push({ arm: TAG + "_5_after_tapping_a_second_stop", ABORT: "NO_SECOND_UNSTAMPED" });
    }
  }

  await ctx.close();
  run.finished_local = new Date().toString();
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(run, null, 2), "utf8");
  const last = run.rows[run.rows.length - 1].state || {};
  console.log("TAG=" + TAG + " VP=" + W + "x" + H + " BUTTONS=" + run.tap_summary.buttons +
    " PRESSABLE=" + run.tap_summary.pressable_by_centre_hit +
    " MARKS=" + (last.marks_stamped_words === undefined ? "NOT_TAKEN" : last.marks_stamped_words) +
    " NOTICES=" + (last.notice_count === undefined ? "NOT_TAKEN" : last.notice_count) +
    " REQ=" + JSON.stringify(run.requests.map((r) => r.method + ":" + r.http_status)) +
    " PAGEERRORS=" + run.page_errors);
  await browser.close();
})().catch((e) => {
  run.FATAL = String(e && e.stack ? e.stack : e).slice(0, 700);
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(run, null, 2), "utf8");
  console.log("FATAL_SEE_JSON " + String(e && e.message).slice(0, 160));
  process.exitCode = 1;
});
