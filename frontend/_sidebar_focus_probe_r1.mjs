import { chromium } from "playwright";

const BASE = process.argv[2] ?? "http://localhost:5611";
const JID = process.argv[3] ?? "d13611bd-8c60-4c76-b1ef-200e2e2aff23";

const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
await ctx.addInitScript((jid) => {
  localStorage.setItem("citynexus.v8.journey_id", jid);
  localStorage.removeItem("citynexus.v8.sidebar_collapsed");
}, JID);
const p = await ctx.newPage();
await p.goto(`${BASE}/v8/hub`, { waitUntil: "domcontentloaded" });
await p.waitForSelector(".v8-product-shell", { timeout: 20000 });
await p.click(".v8-mobile-menu");
await p.waitForSelector("#v8-nav-drawer", { timeout: 5000 });
await p.waitForTimeout(400);

const seq = [];
for (let i = 0; i < 12; i++) {
  await p.keyboard.press("Tab");
  seq.push(
    await p.evaluate(() => {
      const a = document.activeElement;
      if (!a) return "none";
      const inDrawer = Boolean(a.closest("#v8-nav-drawer"));
      const r = a.getBoundingClientRect();
      const cs = getComputedStyle(a);
      return {
        tag: a.tagName.toLowerCase(),
        cls: String(a.className || "").slice(0, 24),
        inside_drawer: inDrawer,
        painted: r.width > 0 && r.height > 0 && cs.visibility !== "hidden",
      };
    }),
  );
}

const bg = await p.evaluate(() => {
  const main = document.querySelector(".v8-main");
  return {
    main_aria_hidden: main ? main.getAttribute("aria-hidden") : "no-main",
    main_inert: main ? (main.inert ?? "no-prop") : "no-main",
    drawer_autofocus: Boolean(document.querySelector("#v8-nav-drawer [autofocus]")),
    focus_starts_in_drawer: Boolean(
      document.activeElement && document.activeElement.closest("#v8-nav-drawer"),
    ),
    active_now: document.activeElement ? document.activeElement.tagName : "none",
  };
});

const outside = seq.filter((s) => s !== "none" && !s.inside_drawer && s.painted);

// An inert leak would lock the whole page behind a drawer that is no longer there.
await p.click("#v8-nav-drawer [data-testid='v8-drawer-close']");
await p.waitForTimeout(700);
await p.waitForSelector("#v8-nav-drawer", { state: "detached", timeout: 5000 });
const afterClose = await p.evaluate(() => {
  const main = document.querySelector(".v8-main");
  const ham = document.querySelector(".v8-mobile-menu");
  ham?.focus();
  return {
    drawer_gone: !document.querySelector("#v8-nav-drawer"),
    main_inert_after_close: main ? main.inert : "no-main",
    hamburger_focusable: document.activeElement === ham,
  };
});

console.log(
  JSON.stringify(
    {
      tabs_sampled: seq.length,
      focus_left_drawer_times: outside.length,
      first_outside: outside[0] ?? null,
      background: bg,
      afterClose,
    },
    null,
    1,
  ),
);
await b.close();
