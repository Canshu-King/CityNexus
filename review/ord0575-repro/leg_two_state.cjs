/* ORD-0575 两态腿：同一屏同一把尺，折叠态与展开态各量一遍，外加"把键滚到屏幕中线"那一态。
   要验的假设：先前那枚"正文盖住提交键"的读数是把**折叠帧的正文盒**与**展开帧的键盒**合进了一次比较。
   算得出：折叠时中止面板只占一行，正文与行程整体上移；展开后面板长高，同一个正文盒 y 会变大。
   若折叠帧的正文盒 ≈ 先前那枚读数里"盖住键"的那个 y，假设成立。
   只点 summary 与滚动，一次写请求都不发。 */
const { chromium } = require("playwright");
const fs = require("fs");
const src = fs.readFileSync(process.env.RK_TWO, "utf-8").replace(/module\.exports[\s\S]*$/, "");
const TWO = (0, eval)(src + "\n;TWO_STATE");
const BASE = process.env.RK_BASE, JID = process.env.RK_JID, OUT = process.env.RK_OUT;
const ARMS = [{ locale: "zh-CN", arm: "zh-CN" }, { locale: "en-US", arm: "en-US" }];
const WIDTHS = [360, 390, 414];

(async () => {
  const doc = { run_id: process.env.RK_RUN || "", tree_at: process.env.RK_TREE || "", legs: [], errors: [] };
  const browser = await chromium.launch({ timeout: 180000 });
  try {
    for (const a of ARMS) {
      for (const w of WIDTHS) {
        const ctx = await browser.newContext({ viewport: { width: w, height: 844 },
          deviceScaleFactor: 2, isMobile: true, hasTouch: true, serviceWorkers: "block", locale: a.locale });
        const page = await ctx.newPage();
        const perr = [];
        page.on("pageerror", (e) => perr.push(String(e).slice(0, 160)));
        await page.goto(BASE + "/v8/hub", { waitUntil: "networkidle", timeout: 60000 });
        await page.evaluate(([l, j]) => {
          localStorage.setItem("citynexus.locale", l);
          localStorage.setItem("citynexus.v8.journey_id", j);
        }, [a.locale, JID]);
        await page.goto(BASE + "/v8/trips", { waitUntil: "networkidle", timeout: 60000 });
        const mk = (state) => ({ arm: a.arm, vw: w, state });
        const closed = await page.evaluate(TWO, mk("closed"));
        // 折叠帧的截图 + 泄漏内容到底画没画：取 textarea 中心的命中栈与它自己那枚的栈
        const leak = await page.evaluate(() => {
          var nameOf = function (n) {
            return n.tagName.toLowerCase() + (n.id ? "#" + n.id : "") +
              (n.className && typeof n.className === "string" ? "." + n.className.trim().split(/\s+/).join(".") : "");
          };
          var ta = document.querySelector("[data-testid='journey-abort-reason']");
          var btn = document.querySelector("[data-testid='journey-abort-submit']");
          var outp = {};
          for (const [k, n] of [["textarea", ta], ["submit", btn]]) {
            if (!n) { outp[k] = null; continue; }
            var r = n.getBoundingClientRect();
            var cx = Math.round((r.left + r.right) / 2), cy = Math.round((r.top + r.bottom) / 2);
            outp[k] = { rect: { top: Math.round(r.top), bottom: Math.round(r.bottom),
                                left: Math.round(r.left), right: Math.round(r.right) },
                        centre: { x: cx, y: cy },
                        stack: Array.prototype.map.call(document.elementsFromPoint(cx, cy).slice(0, 5), nameOf),
                        self_in_stack: document.elementsFromPoint(cx, cy).some(function (m) { return m === n; }),
                        vis: typeof n.checkVisibility === "function" ? n.checkVisibility({ checkVisibilityCSS: true }) : null,
                        opacity: getComputedStyle(n).opacity };
          }
          var d = document.querySelector("[data-testid='journey-abort'] details");
          outp.details_content_visibility = (function () {
            try { return getComputedStyle(d, "::details-content").contentVisibility; } catch (e) { return "取不到"; }
          })();
          outp.details_display = getComputedStyle(d).display;
          // 单变量实验：把这条表单的 display 从 grid 撤成 block（页面内临时改，不落产品字节），
          // 看折叠帧那枚"没画却占着布局盒"的键会不会消失。消失＝盒是这条 grid 规则撑出来的。
          var btn2 = document.querySelector("[data-testid='journey-abort-submit']");
          var before_rects = btn2.getClientRects().length;
          var before_top = Math.round(btn2.getBoundingClientRect().top);
          d.style.display = "block";
          var after_rects = btn2.getClientRects().length;
          var after_top = Math.round(btn2.getBoundingClientRect().top);
          d.style.display = "";
          outp.display_experiment = {
            before_rects: before_rects, before_top: before_top,
            after_rects: after_rects, after_top: after_top,
            section_bottom_after: Math.round(document.querySelector("[data-testid='journey-abort']").getBoundingClientRect().bottom)
          };
          return outp;
        });
        closed.leak = leak;
        await page.screenshot({ path: process.env.RK_SHOTS + "/closed_" + w + "_" + a.arm + ".png" }).catch(() => {});
        await page.locator("[data-testid='journey-abort-open']").first().evaluate((n) => n.click());
        await page.waitForTimeout(400);
        const open = await page.evaluate(TWO, mk("open"));
        open.explains_verbatim = await page.evaluate(() => {
          const e = document.querySelector("[data-testid='journey-abort-explains']");
          if (!e) return null;
          const r = e.getBoundingClientRect();
          const cs = getComputedStyle(e);
          const rng = document.createRange(); rng.selectNodeContents(e);
          return { text: (e.textContent || "").trim(), chars: (e.textContent || "").trim().length,
                   clipped_lines: rng.getClientRects().length,
                   rect: { top: Math.round(r.top), bottom: Math.round(r.bottom), h: Math.round(r.height) },
                   overflow_hidden: cs.overflow === "hidden" || cs.overflow === "clip",
                   scroll_le_client: e.scrollHeight - e.clientHeight,
                   in_viewport: r.top >= 0 && r.bottom <= innerHeight };
        });
        // 第三态：把提交键刻意滚到屏幕中线（先前那把尺的动作），量同一帧
        await page.locator("[data-testid='journey-abort-submit']").first()
          .evaluate((n) => n.scrollIntoView({ block: "center", behavior: "instant" }));
        await page.waitForTimeout(250);
        const centred = await page.evaluate(TWO, mk("open_centred"));
        centred.scroll_y = await page.evaluate(() => Math.round(scrollY));
        // 第四批：展开态把页面从顶滚到底，逐档复位后量同一枚键（滚动污染教训：每档前复位）
        const sweep = [];
        const maxY = await page.evaluate(() => Math.round(document.documentElement.scrollHeight - innerHeight));
        for (const y of [0, Math.round(maxY / 2), maxY]) {
          await page.evaluate((v) => scrollTo(0, v), y);
          await page.waitForTimeout(220);
          const r = await page.evaluate(TWO, mk("open_sweep"));
          r.scroll_y = y;
          sweep.push(r);
        }
        await page.evaluate(() => scrollTo(0, 0));
        for (const r of [closed, open, centred]) { r.landed = page.url(); }
        centred.sweep = sweep;
        closed.page_errors = perr.slice(0, 3);
        doc.legs.push({ arm: a.arm, vw: w, closed, open, centred });
        await ctx.close();
      }
    }
  } catch (e) {
    doc.errors.push({ fatal: String(e).slice(0, 300) });
  } finally { await browser.close(); }
  fs.writeFileSync(OUT, JSON.stringify(doc, null, 1) + "\n", "utf-8");
  for (const L of doc.legs) {
    const f = (s, x) => {
      const le = (x.ledes[0] && x.ledes[0].rect) || {};
      return "{a}/{w} {s}: 开={o} 键={bt} 首枚正文 y={lt}..{lb} 重叠={ov} 中心={cy} 命中自己={h}"
        .replace("{a}", L.arm).replace("{w}", L.vw).replace("{s}", s)
        .replace("{o}", x.details_open).replace("{bt}", x.button_rect ? x.button_rect.top + ".." + x.button_rect.bottom : "无")
        .replace("{lt}", le.top).replace("{lb}", le.bottom).replace("{ov}", x.overlaps)
        .replace("{cy}", x.centre ? x.centre.y : "无").replace("{h}", x.hits_self);
    };
    console.log(f("折叠", L.closed));
    console.log(f("展开", L.open));
    console.log(f("居中", L.centred) + " scrollY=" + L.centred.scroll_y);
    const shift = (L.open.ledes[0] && L.closed.ledes[0])
      ? L.open.ledes[0].rect.top - L.closed.ledes[0].rect.top : null;
    console.log("    同一枚正文盒：展开帧比折叠帧低 " + shift + " px");
    let sweep_bad = 0, sweep_n = 0, sweep_offscreen = 0, sweep_viewed = 0;
    for (const r of (L.centred.sweep || [])) {
      const inview = r.centre && r.centre.y >= 0 && r.centre.y <= 844;
      sweep_n++;
      if (inview) { sweep_viewed++; if (r.hits_self !== true) sweep_bad++; }
      else sweep_offscreen++;
    }
    console.log("      展开态滚动遍历 " + sweep_n + " 档，中心没命中自己=" + sweep_bad);
    for (const st of ["closed", "open", "centred"]) {
      const e = L[st].render_evidence || {};
      console.log("      " + st + " 键渲染证据 offsetParent为null=" + e.offset_parent_null +
        " clientRects=" + e.client_rects_count + " display=" + e.display +
        " visibility=" + e.visibility + " details的display=" + e.details_display);
    }
  }
  process.exit(doc.errors.length ? 3 : 0);
})();
