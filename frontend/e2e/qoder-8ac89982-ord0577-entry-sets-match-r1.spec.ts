/**
 * ORD-0577 building · 桌面端那栋没有门口的楼：两套形态的入口集合必须一致（车道 8ac89982）
 *
 * 图纸要的东西，逐条变成断言：
 *  1. **每一屏在两套形态里都有入口**——桌面宽度（1280）与手机宽度（390）各跑一遍十七屏，逐屏读那一屏
 *     有没有一枚**指着自己**的可点入口（侧栏行／底栏按钮／抽屉行），以及那枚的**渲染盒**（要真画出来，
 *     不能只是 DOM 里有个零尺寸的替身）。
 *  2. **两套形态的入口集合逐屏相等**——不是"各有一半"，是逐屏同一枚 key 在两边都答得到；任何一屏
 *     只在其中一边出现，这格立刻红，并**点名是哪一屏、缺的是哪一边**（图纸要求"少任何一屏都要说明"，
 *     所以这里由尺自己说出那句话，而不是靠我事后补）。
 *  3. **点得进去**：桌面宽度下从侧栏点那一行，地址真的会变成那一屏（不是深链绕过、不是手输路径——
 *     图纸把这三样都排除了）。逐屏点一次并回读 `location.pathname`。
 *  4. 负对照：一个不指向任何屏的地址，按外壳自己的回退答"今天"，它在两套形态里都只答今天那一枚——
 *     证明"答到了"这一列不是恒真的。
 *
 * 入口集合从**同一张路由表**现读（`desktopRoutes` 与 `mobileRoutes` 的并集），所以新加一屏藏不住。
 */
import { expect, test } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { ensureDemoJourney } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-8ac89982-ord0577-entry-sets-match-r1.spec.ts";
const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND = resolve(HERE, "..");
const ROUTES_FILE = "src/routes/v8Routes.ts";
const ARMS = [
  { locale: "zh", storage: "zh-CN" },
  { locale: "en", storage: "en" },
];
const DESKTOP = { width: 1280, height: 900 };
const PHONE = { width: 390, height: 844 };
const NEGATIVE_CONTROL = "qoder-0577-not-a-route";

function tableKeys(src: string, table: string): string[] {
  const found = new RegExp("^export const " + table + "\\s*=", "m").exec(src);
  const open = src.indexOf("[", found!.index);
  let depth = 0;
  let end = -1;
  for (let i = open; i < src.length; i += 1) {
    if (src[i] === "[") depth += 1;
    else if (src[i] === "]") {
      depth -= 1;
      if (depth === 0) {
        end = i;
        break;
      }
    }
  }
  return [...new Set([...src.slice(open, end + 1).matchAll(/\bkey:\s*"([a-z0-9-]+)"/g)].map((m) => m[1]))];
}

/** Read the entries each shape paints, with their rendered boxes. */
async function entriesFor(page: import("@playwright/test").Page) {
  return page.evaluate(() => {
    const box = (el: Element | null) => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return [Math.round(r.width), Math.round(r.height)];
    };
    const sidebar = Array.from(document.querySelectorAll("nav.v8-nav button")).map((el) => ({
      aria_current: el.getAttribute("aria-current"),
      text: (el.textContent || "").replace(/\s+/g, " ").trim(),
      box: box(el),
    }));
    const bar = Array.from(document.querySelectorAll("nav.v8-mobile-nav button")).map((el) => ({
      testid: el.getAttribute("data-testid"),
      aria_current: el.getAttribute("aria-current"),
      box: box(el),
    }));
    return { sidebar, bar };
  });
}

async function openDrawerAndRead(page: import("@playwright/test").Page) {
  const menu = page.getByTestId("v8-mobile-menu");
  const shown = await menu.isVisible().catch(() => false);
  if (!shown) return { door_shown: false, rows: [] as unknown[] };
  await menu.click();
  await page.getByTestId("v8-nav-drawer").waitFor({ state: "visible", timeout: 10_000 });
  const rows = await page.evaluate(() =>
    Array.from(document.querySelectorAll("[data-testid^='v8-drawer-entry-']")).map((el) => {
      const r = el.getBoundingClientRect();
      return {
        key: (el.getAttribute("data-testid") || "").replace("v8-drawer-entry-", ""),
        aria_current: el.getAttribute("aria-current"),
        text: (el.textContent || "").replace(/\s+/g, " ").trim(),
        box: [Math.round(r.width), Math.round(r.height)],
      };
    }),
  );
  await page.getByTestId("v8-drawer-close").click();
  return { door_shown: true, rows };
}

/** Scroll a marked row into view, then hit-test its centre: the element under the centre point must be
 *  that row (or inside it). "In the DOM" is not "reachable" -- this is the reachability reading the
 *  drawing asks for: a painted box whose centre actually answers to a pointer. */
async function centreHit(page: import("@playwright/test").Page, selector: string) {
  return page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (!el) return { present: false, scrolled_into_view: false, box: null, centre: null, hit_self: false };
    el.scrollIntoView({ block: "center", inline: "nearest" });
    const r = el.getBoundingClientRect();
    const cx = r.x + r.width / 2;
    const cy = r.y + r.height / 2;
    const inViewport = cx >= 0 && cy >= 0 && cx <= window.innerWidth && cy <= window.innerHeight;
    const under = document.elementFromPoint(cx, cy);
    return {
      present: true,
      scrolled_into_view: inViewport,
      box: [Math.round(r.width), Math.round(r.height)],
      centre: [Math.round(cx), Math.round(cy)],
      hit_self: Boolean(under) && (under === el || el.contains(under)),
    };
  }, selector);
}

test.describe("ORD-0577 both shapes can reach every screen", () => {
  for (const arm of ARMS) {
    test(`entry-sets-${arm.locale}`, async ({ page }) => {
      test.setTimeout(600_000);
      const src = readFileSync(resolve(FRONTEND, ROUTES_FILE), "utf8");
      const union = [...new Set([...tableKeys(src, "desktopRoutes"), ...tableKeys(src, "mobileRoutes")])];

      await page.addInitScript((loc) => {
        try {
          localStorage.setItem("citynexus.locale", loc);
        } catch {}
      }, arm.storage);
      await page.setViewportSize(PHONE);
      await ensureDemoJourney(page);

      /* The sidebar and the drawer both render their list in the order of the route tables (the shell's
         union), and rows carry no key attribute of their own on the sidebar. So the key of row N is the
         N-th key of that same union, read from source here -- one table, one order, no guessing by word. */
      const desktopKeys = tableKeys(src, "desktopRoutes");
      const mobileKeys = tableKeys(src, "mobileRoutes");
      const unionOrdered = [...desktopKeys, ...mobileKeys.filter((k) => !desktopKeys.includes(k))];

      /* First: name the difference between the two shapes, so a red run says WHICH screens are missing from
         WHICH shape (the drawing requires that, not a per-screen assertion that stops at the first one).
         On the current tip the desktop sidebar draws only `desktopRoutes`, so this leg names trips and me. */
      await page.setViewportSize(DESKTOP);
      await page.goto("/v8/hub", { waitUntil: "load" });
      await page.waitForTimeout(1100);
      const desktopKeysPainted = await page.evaluate(() => document.querySelectorAll("nav.v8-nav button").length);
      const missingFromDesktop = union.filter((k) => unionOrdered.indexOf(k) >= desktopKeysPainted);
      expect(
        missingFromDesktop,
        `desktop sidebar is missing entries for: ${missingFromDesktop.join(", ")} (it paints ${desktopKeysPainted} of the ${union.length} declared screens)`
      ).toEqual([]);

            const perScreen: Record<string, unknown>[] = [];
      /* The phone shape's set is the union too: the bottom bar carries five, the drawer behind the
         hamburger carries the rest, and a screen counts as reachable when either answers. Name the gap
         the same way as the desktop side. */
      await page.setViewportSize(PHONE);
      await page.goto("/v8/hub", { waitUntil: "load" });
      await page.waitForTimeout(1000);
      const drawerKeys = await (async () => {
        const d = await openDrawerAndRead(page);
        return d.rows.map((r) => (r as { key: string }).key);
      })();
      const barKeys = (await entriesFor(page)).bar.map((r) => r.testid?.replace("nav-", ""));
      const phonePainted = new Set([...barKeys, ...drawerKeys]);
      const missingFromPhone = union.filter((k) => !phonePainted.has(k));
      expect(
        missingFromPhone,
        `phone chrome is missing entries for: ${missingFromPhone.join(", ")} (bar ${barKeys.length} + drawer ${drawerKeys.length} of the ${union.length} declared screens)`
      ).toEqual([]);

      for (const key of union) {
        /* Desktop shape: the entry must be the sidebar row, and it must be a real painted box. We
           identify "the row for this key" by the row the shell marks current after we navigate there. */
        await page.setViewportSize(DESKTOP);
        await page.goto("/v8/" + key, { waitUntil: "load" });
        await page.waitForTimeout(1100);
        const desktop = await entriesFor(page);
        const desktopMarked = desktop.sidebar.filter((r) => r.aria_current === "page");
        expect(desktopMarked.length, `desktop ${arm.locale}: ${key} -- ${desktopMarked.length} sidebar rows claim to be this screen`).toBe(1);
        expect(desktopMarked[0].box, `desktop ${arm.locale}: ${key} -- its sidebar row has no painted box`).not.toEqual([0, 0]);
        /* The row that claims this screen must be the row for this key: both the sidebar and the tables render in
           the same order, so the marked row's index must equal this key's index in that shared order. */
        const markedIndex = await page.evaluate(() =>
          Array.from(document.querySelectorAll("nav.v8-nav button")).findIndex(
            (el) => el.getAttribute("aria-current") === "page",
          ),
        );
        expect(markedIndex, `desktop ${arm.locale}: ${key} -- the marked row is not the row for this key`).toBe(
          unionOrdered.indexOf(key),
        );
        /* The reachability reading the drawing asks for: scroll the row into view and hit-test its centre. */
        const desktopHit = await centreHit(page, "nav.v8-nav button[aria-current='page']");
        expect(desktopHit.scrolled_into_view,
               `desktop ${arm.locale}: ${key} -- the sidebar row could not be brought into the viewport (centre ${JSON.stringify(desktopHit.centre)})`).toBe(true);
        expect(desktopHit.hit_self,
               `desktop ${arm.locale}: ${key} -- the centre of the sidebar row is not over that row`).toBe(true);

        /* Phone shape: the bottom bar or the drawer must answer for it. */
        await page.setViewportSize(PHONE);
        await page.goto("/v8/" + key, { waitUntil: "load" });
        await page.waitForTimeout(1100);
        const phone = await entriesFor(page);
        const drawer = await openDrawerAndRead(page);
        const phoneMarkedBar = phone.bar.filter((r) => r.aria_current === "page").map((r) => r.testid);
        const phoneMarkedDrawer = drawer.rows.filter((r) => r.aria_current === "page").map((r) => r.key);
        const phoneBoxOk =
          (phoneMarkedBar.length > 0 && phone.bar.find((r) => r.testid === phoneMarkedBar[0])!.box![0] > 0) ||
          (phoneMarkedDrawer.length > 0);
        expect(phoneMarkedBar.length + phoneMarkedDrawer.length,
               `phone ${arm.locale}: ${key} -- the chrome says nothing about this screen`).toBeGreaterThanOrEqual(1);
        expect(phoneBoxOk, `phone ${arm.locale}: ${key} -- the entry exists but is not painted`).toBe(true);
        /* The same reachability reading on the phone: whichever row answers, its centre must be over it. */
        const phoneSelector = phoneMarkedBar.length > 0
          ? `nav.v8-mobile-nav button[aria-current='page']`
          : "[data-testid='v8-drawer-entry-" + key + "']";
        /* the drawer has to be open for its rows to have a box, so re-open it when the answer came from there */
        if (phoneMarkedBar.length === 0) {
          await page.getByTestId("v8-mobile-menu").click();
          await page.getByTestId("v8-nav-drawer").waitFor({ state: "visible", timeout: 10_000 });
        }
        const phoneHit = await centreHit(page, phoneSelector);
        expect(phoneHit.scrolled_into_view,
               `phone ${arm.locale}: ${key} -- its entry could not be brought into the viewport (centre ${JSON.stringify(phoneHit.centre)})`).toBe(true);
        expect(phoneHit.hit_self,
               `phone ${arm.locale}: ${key} -- the centre of its entry is not over that entry`).toBe(true);
        if (phoneMarkedBar.length === 0) {
          await page.getByTestId("v8-drawer-close").click();
        }

        /* Click test: at desktop width, clicking this screen's own sidebar row must move the address there.
           (The drawing rules out a deep link and a typed address; this is the leg that proves the row
           is the way in.) We always start from Today so the click has to travel. */
        await page.setViewportSize(DESKTOP);
        await page.goto("/v8/hub", { waitUntil: "load" });
        await page.waitForTimeout(900);
        const row = page.locator("nav.v8-nav button").nth(unionOrdered.indexOf(key));
        expect(row, `desktop ${arm.locale}: ${key} -- the sidebar has no row at this key`).toHaveCount(1);
        await row.click();
        await page.waitForTimeout(900);
        const landed = (page.url().match(/\/v8\/([a-z0-9-]+)/) || [])[1] ?? "";
        expect(landed, `desktop ${arm.locale}: clicking the row for ${key} landed on ${landed || "(nowhere)"}`).toBe(key);

        perScreen.push({
          key,
          desktop_sidebar_rows: desktop.sidebar.length,
          desktop_marked: desktopMarked.map((r) => r.text),
          desktop_box: desktopMarked[0].box,
          desktop_centre_hit: desktopHit,
          phone_centre_hit: phoneHit,
          clicked_row_landed_on: landed,
          phone_marked_bar: phoneMarkedBar,
          phone_marked_drawer: phoneMarkedDrawer,
          phone_box_ok: phoneBoxOk,
        });
      }

      /* Negative control: an address naming no screen is answered as Today on both shapes. */
      await page.setViewportSize(DESKTOP);
      await page.goto("/v8/" + NEGATIVE_CONTROL, { waitUntil: "load" });
      await page.waitForTimeout(1000);
      const controlDesktop = (await entriesFor(page)).sidebar.filter((r) => r.aria_current === "page");
      expect(controlDesktop.length, "the negative control was not answered as Today on desktop").toBe(1);
      await page.setViewportSize(PHONE);
      await page.goto("/v8/" + NEGATIVE_CONTROL, { waitUntil: "load" });
      await page.waitForTimeout(1000);
      const controlPhone = (await entriesFor(page)).bar.filter((r) => r.aria_current === "page");
      expect(controlPhone.length, "the negative control was not answered as Today on the phone").toBe(1);

      writeFileSync(
        evidencePath(`ord0577_entry_sets_${arm.locale}.json`),
        JSON.stringify(
          {
            file: FILE,
            arm: arm.locale,
            desktop_shape: `${DESKTOP.width}x${DESKTOP.height}`,
            phone_shape: `${PHONE.width}x${PHONE.height}`,
            screens_in_union: union,
            desktop_rows_painted: desktopKeysPainted,
            phone_bar_keys: barKeys,
            phone_drawer_keys: drawerKeys,
            missing_from_desktop: missingFromDesktop,
            missing_from_phone: missingFromPhone,
            entry_sets_match: missingFromDesktop.length === 0 && missingFromPhone.length === 0,
            negative_control: { requested: NEGATIVE_CONTROL, desktop_marked: controlDesktop.length, phone_marked: controlPhone.length },
            per_screen: perScreen,
          },
          null,
          1,
        ),
        "utf-8",
      );
    });
  }
});