/**
 * ORD-0578 · 带值路由（`/v8/shared/<token>`）上"你在哪"这句由谁来说（车道 8ac89982）
 *
 * 这一族的前几格都问"外壳怎么说你现在在哪屏"。带值路由是例外：源码里它在渲染外壳**之前**就 return 出
 * 自己的 `<main>`，所以那条路上根本没有底栏、没有侧栏、没有面包屑。这枚尺去量它到底画了什么：
 * 哪些外壳件在、有没有面包屑、屏上第一句人话是什么、以及两种形状（行程共享页与海报页）有没有分别。
 *
 * 只读、不判产品：token 是我编的，看的是**一个不指向任何行程的地址会落到什么**——这枚尺量的是
 * "外壳缺席时屏上有没有替它说话"，而不是某个真实分享链接的内容。
 *
 * 两条仪器自检：
 *  1. 负对照：同一趟里也读一个主路由屏（`/v8/hub`），它必须有底栏与面包屑——否则"这枚屏没有底栏"
 *     可能只是整趟都没画出来；
 *  2. 未知 token 与一个格式就不合法的段各读一次：若两者画得一模一样，那么"这个地址没有回答"这件事
 *     与 token 真假无关，那是形状本身的话，不是一次授权失败的偶然。
 */
import { expect, test } from "@playwright/test";
import { writeFileSync } from "node:fs";

import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-8ac89982-ord0578-token-route-chrome-r1.spec.ts";
const ARMS = [
  { locale: "zh", storage: "zh-CN" },
  { locale: "en", storage: "en" },
];
const TOKEN = "qoder-0578-not-a-real-token-test-key";
const MALFORMED = "not-a-share-tail";

async function readScreen(page: import("@playwright/test").Page) {
  return page.evaluate(() => {
    const text = (sel: string) => {
      const el = document.querySelector(sel);
      return el ? (el.textContent || "").replace(/\s+/g, " ").trim() : null;
    };
    return {
      href: location.href,
      pathname: location.pathname,
      body_chars: (document.body.innerText || "").length,
      bottom_bar_present: Boolean(document.querySelector("nav.v8-mobile-nav")),
      sidebar_present: Boolean(document.querySelector("nav.v8-nav")),
      hamburger_present: Boolean(document.querySelector("[data-testid='v8-mobile-menu']")),
      breadcrumb: text(".v8-breadcrumb strong"),
      breadcrumb_present: Boolean(document.querySelector(".v8-breadcrumb")),
      h1: text("h1"),
      main_present: Boolean(document.querySelector("main")),
      shell_present: Boolean(document.querySelector(".v8-product-shell")),
      first_line: (document.body.innerText || "").split("\n").map((l) => l.trim()).filter(Boolean)[0] ?? null,
      announced: text("[role='status'], [role='alert'], .v8-message"),
    };
  });
}

test.describe("ORD-0578 what says where you are on a token route", () => {
  for (const arm of ARMS) {
    test(`token-route-${arm.locale}`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.addInitScript((loc) => {
        try {
          localStorage.setItem("citynexus.locale", loc);
        } catch {}
      }, arm.storage);

      const rows: Record<string, unknown>[] = [];
      const cases = [
        { name: "control_hub", url: "/v8/hub" },
        { name: "token_plain", url: "/v8/shared/" + TOKEN },
        { name: "token_poster", url: "/v8/shared/" + TOKEN + "/poster" },
        { name: "malformed_tail", url: "/v8/shared/" + MALFORMED },
      ];
      for (const c of cases) {
        await page.goto(c.url, { waitUntil: "load" });
        await page.waitForTimeout(1500);
        const read = await readScreen(page);
        rows.push({ name: c.name, requested: c.url, ...read });
        if (c.name === "control_hub") {
          expect(read.bottom_bar_present, "the control screen has no bottom bar -- the whole run is dark")
            .toBe(true);
          expect(read.breadcrumb_present, "the control screen has no breadcrumb").toBe(true);
        }
      }

      const tokenPlain = rows.find((r) => r.name === "token_plain")!;
      const malformed = rows.find((r) => r.name === "malformed_tail")!;
      /* Compare only what is painted -- and not the address, which differs by construction between the two
         cases. (The first version compared whole rows, and the second still compared href and pathname;
         both could only ever answer False, which is a comparison that was never performed. This one lists
         the fields it actually judges, so a reader can see what "the same" means.) */
      const PAINTED = ["bottom_bar_present", "sidebar_present", "hamburger_present",
        "breadcrumb_present", "shell_present", "main_present", "h1", "first_line", "announced"];
      const painted = (r: Record<string, unknown>) => JSON.stringify(PAINTED.map((k) => r[k]));
      const samePaint = painted(tokenPlain) === painted(malformed);

      writeFileSync(
        evidencePath(`ord0578_token_chrome_${arm.locale}.json`),
        JSON.stringify(
          {
            file: FILE,
            arm: arm.locale,
            shape: "390x844",
            token: TOKEN,
            unknown_token_and_malformed_tail_paint_the_same: samePaint,
            rows,
          },
          null,
          1,
        ),
        "utf-8",
      );
    });
  }
});