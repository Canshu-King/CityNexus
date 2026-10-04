/**
 * 车道 8ac89982 · 具名控件普查探针（自用仪表，不作为闸交件，也不断言任何东西）
 *
 * 令：把每一屏的可交互控件逐个算出「读屏用户拿到的是什么」，把拿不到的那批列成清单交给
 * 1ba48dbf（无障碍名那一族的修法在其名下）。
 *
 * 判据只有一条，且是从 DOM 自己算的，不是我读代码猜的：一枚控件的可及名依次问
 *   aria-label → aria-labelledby 指向的文本 → 元素自己的可见文字 → 它的 `label[for=id]` 或包裹它的
 *   `label` → title → 内部 img 的 alt → placeholder → submit/button 类 input 的 value；
 * 八问皆空即为「无名」。第一版这把尺漏问了 `label` 那一格（表单控件的正牌名来源），所以 r1 报的
 * 四枚无名有可能是假阳；r2 是修好尺之后的读数，两代读数都留在件里，判语以 r2 为准。`aria-hidden` 的子节点不算名来源（那是装饰），但父按钮必须有名字。
 *
 * 每一枚都记：路由、臂、标签名、data-testid、class、盒子、外层 HTML 前缀、它的图标子节点是不是
 * 唯一内容，以及这一屏实际落到的 href 与屏上标题 —— 深链若被外壳弹回 Today，清单会显出这一点，
 * 不会把「其实是另一屏」读成「这一屏干净」。
 *
 * 形状：本轮只走 390x844（移动端外壳那一条），桌面宽度与抽屉那一族本轮 NOT_MEASURED，写在这里而不是
 * 悄悄少报。探针不 expect 任何东西，所以它不会红；读数一律由 run/ 下的收法器算。
 */
import { test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";

import { ensureDemoJourney } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-8ac89982-named-control-census-r1.spec.ts";

const ROUTES = [
  "hub", "live", "map", "studio", "stay", "discover", "import", "bookings",
  "footprints", "agent", "authoritative", "intelligence", "twin", "trash", "access",
];
const ARMS = [
  { locale: "zh", storage: "zh-CN" },
  { locale: "en", storage: "en" },
];

async function census(page: Page) {
  return page.evaluate(() => {
    const SEL = [
      "button", "a[href]", "input", "select", "textarea", "summary",
      "[role=button]", "[role=link]", "[role=checkbox]", "[role=switch]", "[role=tab]",
      "[role=menuitem]", "[role=combobox]", "[role=searchbox]", "[data-testid=pretrip-empty-action]",
    ].join(",");
    const text = (node: Element | null) => (node?.textContent ?? "").replace(/\s+/g, " ").trim();
    const labelledByText = (el: Element) => {
      const ids = (el.getAttribute("aria-labelledby") ?? "").split(/\s+/).filter(Boolean);
      return ids.map((id) => text(document.getElementById(id))).filter(Boolean).join(" ").trim();
    };
    const rows: Record<string, unknown>[] = [];
    for (const el of Array.from(document.querySelectorAll(SEL))) {
      const node = el as HTMLElement;
      const rect = node.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) continue;
      const style = window.getComputedStyle(node);
      if (style.visibility === "hidden" || style.display === "none") continue;
      const aria = (node.getAttribute("aria-label") ?? "").trim();
      const labelled = labelledByText(node);
      const own = text(node);
      const title = (node.getAttribute("title") ?? "").trim();
      const img = node.querySelector("img");
      const alt = ((img as HTMLImageElement | null)?.alt ?? "").trim();
      const placeholder = (node.getAttribute("placeholder") ?? "").trim();
      /* A form control's own labelling element is a name source the accessible-name algorithm uses,
         so asking six questions and missing this one would report named inputs as unnamed -- that is
         an instrument defect, not a finding. Both shapes are asked: `label[for=id]` and a wrapping
         `label`. */
      const isFormControl = node instanceof HTMLInputElement || node instanceof HTMLSelectElement
        || node instanceof HTMLTextAreaElement;
      const ownId = node.getAttribute("id") ?? "";
      const labelEl = isFormControl && ownId
        ? document.querySelector(`label[for="${CSS.escape(ownId)}"]`)
        : node.closest("label");
      const labelText = labelEl ? text(labelEl).replace(/:$/, "").trim() : "";
      const inputValue =
        node instanceof HTMLInputElement && (node.type === "submit" || node.type === "button")
          ? (node.value ?? "").trim()
          : "";
      const hiddenOnly = node.querySelectorAll("[aria-hidden=true]").length > 0 && own === "";
      const via = aria ? "aria-label" : labelled ? "aria-labelledby" : own ? "text"
        : labelText ? "label-element" : title ? "title" : alt ? "img-alt"
        : placeholder ? "placeholder"
        : inputValue ? "input-value" : "none";
      const name = aria || labelled || own || labelText || title || alt || placeholder || inputValue;
      const classes = Array.from(node.classList);
      rows.push({
        tag: node.tagName.toLowerCase(),
        testid: node.getAttribute("data-testid") ?? null,
        role: node.getAttribute("role") ?? null,
        classes: classes.slice(0, 3).join("."),
        accessible_name: name.slice(0, 80),
        name_via: via,
        unnamed: via === "none",
        decorative_only: hiddenOnly,
        icon_child: !!node.querySelector("svg,i,span[class*=glyph],img"),
        aria_hidden_self: node.getAttribute("aria-hidden") === "true",
        disabled: (node as HTMLButtonElement).disabled === true,
        box: [Math.round(rect.x), Math.round(rect.y), Math.round(rect.width), Math.round(rect.height)],
        html_head: node.outerHTML.replace(/\s+/g, " ").slice(0, 140),
      });
    }
    /* The second dimension, asked separately: an element that the product makes clickable by CSS
       affordance alone (`cursor: pointer` with no button, link or form semantics) is invisible to the
       selector list above, so reporting only that list would read as "nothing is unnamed" while a
       whole class of controls was never in the denominator. Same eight questions, own array. */
    const INTERACTIVE = "button, a[href], input, select, textarea, summary, [role], [contenteditable]";
    const pointerRows: Record<string, unknown>[] = [];
    for (const el of Array.from(document.querySelectorAll("*"))) {
      const node = el as HTMLElement;
      if (node.closest(INTERACTIVE)) continue;
      const rect = node.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) continue;
      if (window.getComputedStyle(node).cursor !== "pointer") continue;
      const aria = (node.getAttribute("aria-label") ?? "").trim();
      const labelled = labelledByText(node);
      const own = text(node);
      const title = (node.getAttribute("title") ?? "").trim();
      const name = aria || labelled || own || title;
      pointerRows.push({
        tag: node.tagName.toLowerCase(),
        testid: node.getAttribute("data-testid") ?? null,
        classes: Array.from(node.classList).slice(0, 3).join("."),
        accessible_name: name.slice(0, 80),
        name_via: aria ? "aria-label" : labelled ? "aria-labelledby" : own ? "text" : title ? "title" : "none",
        unnamed: !(aria || labelled || own || title),
        box: [Math.round(rect.x), Math.round(rect.y), Math.round(rect.width), Math.round(rect.height)],
        html_head: node.outerHTML.replace(/\s+/g, " ").slice(0, 140),
      });
    }
    /* Negative controls, one per dimension. A census that reports "no unnamed control" is only worth
       reading if it can catch one, so each pass is shown a planted element of the shape it claims to
       cover -- an unnamed `button` for the semantic denominator, an unnamed `cursor: pointer` div for
       the affordance denominator -- and must place it in its own list. The probes are removed before
       the reading is returned, so they never enter the counts. */
    const probeButton = document.createElement("button");
    probeButton.setAttribute("data-qoder-census-probe", "interactive");
    probeButton.style.cssText = "position:fixed;left:2px;top:2px;width:40px;height:40px;z-index:99999";
    const probeDiv = document.createElement("div");
    probeDiv.setAttribute("data-qoder-census-probe", "pointer");
    probeDiv.style.cssText = "position:fixed;left:60px;top:2px;width:40px;height:40px;z-index:99999;cursor:pointer";
    document.body.append(probeButton, probeDiv);
    const caughtInteractive = Array.from(document.querySelectorAll(SEL)).some(
      (el) => el.getAttribute("data-qoder-census-probe") === "interactive"
        && !(el.getAttribute("aria-label") ?? "").trim() && !(el.textContent ?? "").trim(),
    );
    const caughtPointer = Array.from(document.querySelectorAll("*")).some(
      (el) => el.getAttribute("data-qoder-census-probe") === "pointer"
        && window.getComputedStyle(el).cursor === "pointer" && !el.closest(INTERACTIVE),
    );
    probeButton.remove();
    probeDiv.remove();
    const heading = document.querySelector("h1, h2, [data-testid=today-heading]");
    return {
      landed_href: location.href,
      screen_title: text(heading).slice(0, 80),
      total_controls: rows.length,
      unnamed: rows.filter((row) => row.unnamed).length,
      pointer_only_candidates: pointerRows.length,
      pointer_only_unnamed: pointerRows.filter((row) => row.unnamed).length,
      rows,
      pointer_rows: pointerRows,
      negative_control_interactive_probe_seen: caughtInteractive,
      negative_control_pointer_probe_seen: caughtPointer,
    };
  });
}

test.describe("lane 8ac89982 named-control census (instrument, not a gate)", () => {
  for (const arm of ARMS) {
    for (const route of ROUTES) {
      test(`census-${route}-${arm.locale}`, async ({ page }) => {
        await page.setViewportSize({ width: 390, height: 844 });
        await page.addInitScript((loc) => {
          try {
            localStorage.setItem("citynexus.locale", loc);
          } catch {}
        }, arm.storage);
        await ensureDemoJourney(page);
        await page.goto(`/v8/${route}`, { waitUntil: "load" });
        await page.waitForTimeout(2_600);
        const reading = await census(page);
        writeFileSync(
          evidencePath(`census_${route}_${arm.locale}.json`),
          JSON.stringify({ file: FILE, route, arm: arm.locale, shape: "390x844", ...reading }, null, 1),
          "utf-8",
        );
        console.log(`CENSUS ${route}/${arm.locale} landed=${reading.landed_href} controls=${reading.total_controls} unnamed=${reading.unnamed} pointer_only=${reading.pointer_only_candidates} pointer_unnamed=${reading.pointer_only_unnamed} probe_interactive_seen=${reading.negative_control_interactive_probe_seen} probe_pointer_seen=${reading.negative_control_pointer_probe_seen}`);
      });
    }
  }
});
