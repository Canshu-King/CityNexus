/**
 * ORD-0577 · 底栏在不是主路由的屏上也要说出所在（车道 8ac89982）
 *
 * 上一枚尺量到：十七屏里底栏答六屏、静十一屏，且静默的每一屏底栏都画着五枚按钮——是"没答案"不是"没底栏"。
 * 这一枚是修好之后的门，判三件事：
 *  1. **每一屏都必须有答案**，而且两种答案不许同时出现、也不许都不出现：主路由那几屏靠某枚按钮的
 *     `aria-current`；其余各屏靠底栏指向屏上已有的那个屏名（`aria-describedby` 指向面包屑里那一枚
 *     `<strong>`，它本来就把这一屏的名字画出来了）。"都不出现"就是回退到静默，"都出现"就是自相矛盾。
 *  2. **可见文字一字未改**：逐屏把底栏五枚按钮的可见文字与随枝交的基线读数逐枚比（基线是改动前那一趟
 *     普查的读数，不是我背下来的），屏名那一列也一并比对。
 *  3. **答案对得上这一屏**：指向的那个名字必须等于面包屑上这一屏的名字，且不是空串——免得"有答案"变成
 *     "指着一个空元素"。
 *
 * 负对照：一个不指向任何屏的地址按外壳自己的回退答成"今天"，所以它必须走第 1 种答案（有 current 的那一种），
 * 不得再挂"不在主路由上"——这一枚防的是我把条件写反。
 */
import { expect, test, type Page } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { ensureDemoJourney } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-8ac89982-ord0577-bar-says-where-r1.spec.ts";
const HERE = dirname(fileURLToPath(import.meta.url));
const ARMS = [
  { locale: "zh", storage: "zh-CN" },
  { locale: "en", storage: "en" },
];
const NEGATIVE_CONTROL = "qoder-0577-not-a-route";
const WHERE_ID = "v8-bar-where";

async function readBar(page: Page) {
  return page.evaluate((whereId) => {
    const nav = document.querySelector("nav.v8-mobile-nav");
    const buttons = Array.from(document.querySelectorAll("nav.v8-mobile-nav button"));
    const described = nav ? nav.getAttribute("aria-describedby") : null;
    const target = described ? document.getElementById(described) : null;
    const crumb = document.querySelector(".v8-breadcrumb strong");
    return {
      landed_href: location.href,
      describedby: described,
      described_present: Boolean(target),
      described_id: target ? target.id : null,
      described_text: target ? (target.textContent || "").trim() : null,
      breadcrumb: (crumb?.textContent || "").trim(),
      buttons: buttons.map((el) => ({
        testid: el.getAttribute("data-testid"),
        aria_current: el.getAttribute("aria-current"),
        contrast_role: el.getAttribute("data-contrast-role"),
        text: (el.textContent || "").replace(/\s+/g, " ").trim(),
      })),
    };
  }, WHERE_ID);
}

test.describe("ORD-0577 the bar says where you are on every screen", () => {
  for (const arm of ARMS) {
    test(`bar-says-where-${arm.locale}`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      test.setTimeout(300_000);
      const baseline = JSON.parse(
        readFileSync(resolve(HERE, `ord0577_bar_texts_baseline_${arm.locale}.json`), "utf8"),
      ) as { screens: { requested: string; texts: string[]; breadcrumb: string }[] };

      await page.addInitScript((loc) => {
        try {
          localStorage.setItem("citynexus.locale", loc);
        } catch {}
      }, arm.storage);
      await ensureDemoJourney(page);

      const rows: Record<string, unknown>[] = [];
      for (const screen of baseline.screens) {
        await page.goto("/v8/" + screen.requested, { waitUntil: "load" });
        await page.waitForTimeout(1300);
        const bar = await readBar(page);
        const current = bar.buttons.filter((b) => b.aria_current === "page").map((b) => b.testid);
        const answeredByButton = current.length === 1;
        const answeredByPointer = Boolean(bar.describedby) && bar.described_present &&
          Boolean(bar.described_text);
        const row = {
          requested: screen.requested,
          current,
          describedby: bar.describedby,
          described_text: bar.described_text,
          breadcrumb: bar.breadcrumb,
          answered_by_button: answeredByButton,
          answered_by_pointer: answeredByPointer,
          texts: bar.buttons.map((b) => b.text),
        };
        rows.push(row);

        expect(row.texts, `${arm.locale}: ${screen.requested} -- the bar's visible words moved`).toEqual(
          screen.texts,
        );
        expect(bar.breadcrumb, `${arm.locale}: ${screen.requested} -- the screen's own name moved`).toBe(
          screen.breadcrumb,
        );
        expect(
          answeredByButton || answeredByPointer,
          `${arm.locale}: ${screen.requested} -- the bar answers nothing here (current=${JSON.stringify(current)}, describedby=${bar.describedby})`
        ).toBe(true);
        expect(
          answeredByButton && answeredByPointer,
          `${arm.locale}: ${screen.requested} -- the bar answers twice (a current button and a pointer at once)`
        ).toBe(false);
        if (answeredByPointer) {
          expect(
            bar.described_text,
            `${arm.locale}: ${screen.requested} -- the bar points at a name that is not this screen's`
          ).toBe(bar.breadcrumb);
        }
      }

      await page.goto("/v8/" + NEGATIVE_CONTROL, { waitUntil: "load" });
      await page.waitForTimeout(1200);
      const control = await readBar(page);
      const controlCurrent = control.buttons.filter((b) => b.aria_current === "page").map((b) => b.testid);
      expect(controlCurrent, "the negative control must land on the Today button").toEqual(["nav-hub"]);
      expect(
        control.describedby,
        "an address that names no screen is answered as Today, so it must not also claim off-route"
      ).toBeNull();

      writeFileSync(
        evidencePath(`ord0577_fixed_${arm.locale}.json`),
        JSON.stringify(
          {
            file: FILE,
            arm: arm.locale,
            shape: "390x844",
            answered_by_button: rows.filter((r) => r.answered_by_button).map((r) => r.requested),
            answered_by_pointer: rows.filter((r) => r.answered_by_pointer).map((r) => r.requested),
            negative_control: { requested: NEGATIVE_CONTROL, current: controlCurrent, describedby: control.describedby },
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
