/* ORD-0575 第三问：折叠态那株"没画但占着布局盒"的子树，用户能不能碰到它？
   判据不是"有没有盒"，而是三件事各自的实测：
   1) 键盘：从 summary 起 Tab，能不能把焦点送进 textarea / 提交键（碰得到＝真缺陷：看不见却能按）；
   2) 命中：elementsFromPoint 在键的中心点回谁（折叠帧里必须不是它自己）；
   3) 无障碍树：aria-hidden 语义之外，看 take_snapshot 里有没有它（这条由驱动侧做，本腿只报前两条）。
   只点 summary 与按 Tab，一次写请求都不发。 */
const { chromium } = require("playwright");
const fs = require("fs");
const BASE = process.env.RK_BASE, JID = process.env.RK_JID, OUT = process.env.RK_OUT;
const ARMS = [{ locale: "zh-CN", arm: "zh-CN" }, { locale: "en-US", arm: "en-US" }];
const WIDTHS = [360, 390, 414];

(async () => {
  const doc = { run_id: process.env.RK_RUN || "", tree_at: process.env.RK_TREE || "",
                legs: [], errors: [] };
  const browser = await chromium.launch({ timeout: 180000 });
  try {
    for (const a of ARMS) {
      for (const w of WIDTHS) {
        const ctx = await browser.newContext({ viewport: { width: w, height: 844 },
          deviceScaleFactor: 2, isMobile: true, hasTouch: true, serviceWorkers: "block",
          locale: a.locale });
        const page = await ctx.newPage();
        const perr = [];
        page.on("pageerror", (e) => perr.push(String(e).slice(0, 160)));
        await page.goto(BASE + "/v8/hub", { waitUntil: "networkidle", timeout: 60000 });
        await page.evaluate(([l, j]) => {
          localStorage.setItem("citynexus.locale", l);
          localStorage.setItem("citynexus.v8.journey_id", j);
        }, [a.locale, JID]);
        await page.goto(BASE + "/v8/trips", { waitUntil: "networkidle", timeout: 60000 });
        const cell = { arm: a.arm, vw: w, errors: perr };

        // 折叠态先量命中与"幽灵盒吃了谁"，再走 Tab —— Tab 会把焦点元素滚进视口，
        // 先 Tab 后量的话键的盒会从 y 574 跑到 y 63，读数就废了（本腿第一版就栽在这）。
        await page.evaluate(() => scrollTo(0, 0));
        cell.closed_hit = await page.evaluate(() => {
          const btn = document.querySelector("[data-testid='journey-abort-submit']");
          if (!btn) return null;
          const r = btn.getBoundingClientRect();
          const cx = Math.round((r.left + r.right) / 2), cy = Math.round((r.top + r.bottom) / 2);
          const hit = document.elementFromPoint(cx, cy);
          const nm = (n) => n.tagName.toLowerCase() + (n.getAttribute && n.getAttribute("data-testid") ? "#" + n.getAttribute("data-testid") : "") +
            (n.className && typeof n.className === "string" ? "." + n.className.trim().split(/\s+/).join(".") : "");
          // 幽灵盒到底吃没吃掉"能按的东西"：逐个可交互元素命中测试，中心回别人的才算被吃
          const eaten = [];
          for (const n of document.querySelectorAll("button,a[href],input,textarea,summary,[role='button']")) {
            const rr = n.getBoundingClientRect();
            if (!rr.width || !rr.height) continue;
            const px = Math.round((rr.left + rr.right) / 2), py = Math.round((rr.top + rr.bottom) / 2);
            if (py < 0 || py > innerHeight) continue;
            const hh = document.elementFromPoint(px, py);
            if (!hh) continue;
            const mine = hh === n || n.contains(hh) || hh.contains(n);
            if (!mine) eaten.push({ who: nm(n), got: nm(hh),
                                    self_vis: typeof n.checkVisibility === "function" ? n.checkVisibility({ checkVisibilityCSS: true }) : null,
                                    got_is_the_invisible_button: !!(btn && (hh === btn || btn.contains(hh))) });
          }
          return { rect: { top: Math.round(r.top), bottom: Math.round(r.bottom) },
                   centre: { x: cx, y: cy },
                   hit: hit ? nm(hit) : null, self: hit === btn,
                   vis: typeof btn.checkVisibility === "function" ? btn.checkVisibility({ checkVisibilityCSS: true }) : null,
                   eaten_count: eaten.length, eaten: eaten.slice(0, 8) };
        });
        await page.locator("[data-testid='journey-abort-open']").first().evaluate((n) => n.blur());
        cell.closed_open_before = await page.evaluate(() => {
          const d = document.querySelector("[data-testid='journey-abort'] details");
          return !!(d && d.open);
        });
        await page.locator("[data-testid='journey-abort-open']").first().focus();
        cell.focus_start = await page.evaluate(() => {
          const a = document.activeElement;
          return a ? (a.tagName.toLowerCase() + "#" + (a.getAttribute("data-testid") || a.id || "")) : null;
        });
        const reached = [];
        for (let i = 0; i < 8; i += 1) {
          await page.keyboard.press("Tab");
          const now = await page.evaluate(() => {
            const a = document.activeElement;
            if (!a) return null;
            return { name: a.tagName.toLowerCase() + "#" + (a.getAttribute("data-testid") || a.id || ""),
                     vis: typeof a.checkVisibility === "function" ? a.checkVisibility({ checkVisibilityCSS: true }) : null,
                     in_form: !!(a.closest && a.closest("[data-testid='journey-abort'] details")) };
          });
          if (!now) break;
          reached.push(now);
          if (now.in_form) break;
        }
        cell.tab_walk = reached.map((x) => x.name + "(vis=" + x.vis + ")");
        cell.closed_form_focusable = reached.some((x) => x.in_form);
        cell.closed_form_focus_visible = reached.filter((x) => x.in_form).map((x) => x.vis);

        // 展开态：键必须在视口内且命中自己
        await page.locator("[data-testid='journey-abort-open']").first().evaluate((n) => n.click());
        await page.waitForTimeout(400);
        cell.open_hit = await page.evaluate(() => {
          const btn = document.querySelector("[data-testid='journey-abort-submit']");
          if (!btn) return null;
          const r = btn.getBoundingClientRect();
          const cx = Math.round((r.left + r.right) / 2), cy = Math.round((r.top + r.bottom) / 2);
          const hit = document.elementFromPoint(cx, cy);
          return { rect: { top: Math.round(r.top), bottom: Math.round(r.bottom),
                           left: Math.round(r.left), right: Math.round(r.right) },
                   centre: { x: cx, y: cy }, in_viewport: cy >= 0 && cy <= innerHeight,
                   self: hit === btn || !!(hit && btn.contains(hit)),
                   vis: typeof btn.checkVisibility === "function" ? btn.checkVisibility({ checkVisibilityCSS: true }) : null,
                   hit: hit ? hit.tagName.toLowerCase() + "." + String(hit.className).trim().split(/\s+/).join(".") : null };
        });
        cell.href = page.url();
        doc.legs.push(cell);
        await ctx.close();
      }
    }
  } catch (e) {
    doc.errors.push({ fatal: String(e).slice(0, 300) });
  } finally { await browser.close(); }
  fs.writeFileSync(OUT, JSON.stringify(doc, null, 1) + "\n", "utf-8");
  for (const L of doc.legs) {
    const c = L.closed_hit || {}, o = L.open_hit || {};
    console.log(`${L.arm}/${L.vw} 折叠帧：键盒 ${c.rect ? c.rect.top + ".." + c.rect.bottom : "?"}` +
      ` 中心 ${c.centre ? c.centre.y : "?"} 画没画=${c.vis} 中心命中=${c.hit} 命中自己=${c.self}`);
    console.log(`${L.arm}/${L.vw} 展开帧：键盒 ${o.rect ? o.rect.top + ".." + o.rect.bottom : "?"}` +
      ` 中心 ${o.centre ? o.centre.y : "?"} 屏内=${o.in_viewport} 画没画=${o.vis} 命中自己=${o.self} 命中=${o.hit}`);
    console.log(`  Tab 从 ${L.focus_start} 起走 ${L.tab_walk.length} 步，` +
      `进没进折叠表单=${L.closed_form_focusable} 进去后可见性=${JSON.stringify(L.closed_form_focus_visible)}`);
    console.log(`  路径=${L.tab_walk.join(" -> ").slice(0, 150)}`);
    console.log(`  折叠帧幽灵盒吃掉了几个可交互元素=${c.eaten_count ?? "?"}` +
      (c.eaten && c.eaten.length ? ` 逐枚：${c.eaten.map((e) => `${e.who}(画=${e.self_vis})←${e.got}`).join(" | ").slice(0, 220)}` : ""));
  }
  const n = doc.legs.length;
  console.log(`腿=${n} 折叠帧键不可见=${doc.legs.filter((L) => (L.closed_hit || {}).vis === false).length}` +
    ` 折叠帧能 Tab 进表单=${doc.legs.filter((L) => L.closed_form_focusable).length}` +
    ` 折叠帧幽灵盒吃掉的可交互元素合计=${doc.legs.reduce((a, L) => a + ((L.closed_hit || {}).eaten_count || 0), 0)}` +
    ` 其中自己就没被画出来的=${doc.legs.reduce((a, L) => a + (((L.closed_hit || {}).eaten || []).filter((e) => e.self_vis === false).length), 0)}` +
    ` 画出来了却被吃的=${doc.legs.reduce((a, L) => a + (((L.closed_hit || {}).eaten || []).filter((e) => e.self_vis === true).length), 0)}` +
    ` 展开帧屏内命中自己=${doc.legs.filter((L) => (L.open_hit || {}).self === true && (L.open_hit || {}).in_viewport === true).length}` +
    ` errors=${doc.errors.length}`);
  process.exit(doc.errors.length ? 3 : 0);
})();
