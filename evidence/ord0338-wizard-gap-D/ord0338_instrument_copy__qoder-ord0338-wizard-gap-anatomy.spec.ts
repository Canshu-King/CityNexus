/**
 * ORD-0338 · 号令者 06:05 ⑤ 派下的一件定性题：390×844 下新建行程向导里，
 * 「步骤条与目的地之间那一整块空白」到底是
 *   (a) 等数据的插槽（`:8000` 未恢复 ⇒ 有节点在等填充），还是
 *   (b) 布局留白（那段在 DOM 里根本没有内容节点）。
 *
 * 这一枚门不改产品字节，只出读数。四枚节点各自只回答一个问题，且每个判据都读渲染后的几何
 * （getBoundingClientRect / getComputedStyle / CSSOM），不读源码字符串：
 *
 *   N1 band-has-no-content-node —— 带内相交且自带文字的元素必须为 0 枚；带高必须能由
 *      `.trial-steps` 自己的 computed padding-bottom + margin 派生（量得上，不是猜）。
 *   N2 attribution-single-variable —— 用 `addStyleTag` 只把那一条 padding 置 0（产品字节 0 改），
 *      带高必须正好缩掉那一截；不缩就是别的东西在撑，(b) 的归属就不成立。
 *   N3 not-data-gated —— 网络静默前/后各量一次，带高必须相同；带内也不许有 role=status /
 *      aria-live / skeleton / loading 之类"我在等"的节点。这一枚正面否掉 (a)。
 *   N4 what-the-eye-sees —— 带上方最近的渲染文字与带下方最近的渲染文字（人看到的顺序），
 *      外加一张带 run id 的截图。
 *
 * 读的是这台设备上真实挂载的树：`git archive f45489c6…` 导出，逐文件 blob 与尖一致（外层脚本核）。
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-ord0338-wizard-gap-anatomy.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const clean = (v: string | null | undefined) => String(v ?? "").replace(/\s+/g, " ").trim();

/** Everything the band's anatomy needs, measured in one pass on the live document. */
async function measure(page: Page) {
  return page.evaluate(() => {
    /* Page-side: a helper defined in the spec's Node scope does not exist inside evaluate,
       and referencing one is how every node here died on the first run. */
    const clean = (v: string | null | undefined) => String(v ?? "").replace(/\s+/g, " ").trim();
    const rect = (el: Element) => {
      const r = el.getBoundingClientRect();
      return { top: Math.round(r.top), bottom: Math.round(r.bottom), height: Math.round(r.height) };
    };
    const steps = document.querySelector('[data-testid="trial-steps"]');
    const card = document.querySelector('[data-testid="trial-step1-body"]');
    const city = document.querySelector('[data-testid="trial-city"]');
    if (!steps || !card || !city) return { missing: "trial-steps / trial-step1-body / trial-city" };
    const items = Array.from(steps.querySelectorAll("li"));
    const contentBottom = Math.max(...items.map((li) => li.getBoundingClientRect().bottom));
    const label = city.closest("label")?.querySelector("span") ?? city;
    const bandTop = Math.round(contentBottom);
    const bandBottom = Math.round(label.getBoundingClientRect().top);

    // Every element that actually occupies a row inside the band. A "slot waiting for data"
    // would show up here; pure padding shows up nowhere.
    const inside: Array<Record<string, unknown>> = [];
    for (const el of Array.from(document.querySelectorAll("body *"))) {
      const r = el.getBoundingClientRect();
      if (r.height <= 0 || r.width <= 0) continue;
      /* A section or div that *spans* the band is not a thing standing in it. Counting those is how
         the first run reported 6 members and read as if a slot existed. */
      if (r.top < bandTop - 1 || r.bottom > bandBottom + 1) continue;
      if (el.contains(steps) || el.contains(label) || steps.contains(el) || label.contains(el))
        continue;
      const own = clean(
        Array.from(el.childNodes)
          .filter((n) => n.nodeType === 3)
          .map((n) => n.textContent)
          .join(" "),
      );
      inside.push({
        tag: el.tagName.toLowerCase(),
        testid: el.getAttribute("data-testid"),
        role: el.getAttribute("role"),
        ariaLive: el.getAttribute("aria-live"),
        cls: (el.getAttribute("class") ?? "").slice(0, 60),
        ownText: own.slice(0, 60),
        rect: { top: Math.round(r.top), bottom: Math.round(r.bottom), height: Math.round(r.height) },
      });
    }
    // "waiting for data" affordances anywhere in the band
    const waiting = inside.filter(
      (e) =>
        e.role === "status" ||
        e.role === "alert" ||
        e.ariaLive !== null ||
        /skeleton|loading|placeholder|empty-slot/i.test(String(e.cls)),
    );
    // provenance: which declaration in which sheet/media query sets that padding
    const rules: Array<Record<string, string | null>> = [];
    for (const sheet of Array.from(document.styleSheets)) {
      let list: CSSRuleList | null = null;
      try {
        list = sheet.cssRules;
      } catch {
        continue; // a cross-origin sheet is not an absence, it is unreadable; said so below
      }
      const walk = (rulesIn: CSSRuleList, media: string | null) => {
        for (const rule of Array.from(rulesIn)) {
          if (rule instanceof CSSMediaRule) walk(rule.cssRules, rule.conditionText);
          else if (rule instanceof CSSStyleRule && /\.trial-steps/.test(rule.selectorText))
            rules.push({
              selector: rule.selectorText,
              media,
              paddingBottom: rule.style.getPropertyValue("padding-bottom") || null,
              margin: rule.style.getPropertyValue("margin") || null,
            });
        }
      };
      if (list) walk(list, null);
    }
    const cs = getComputedStyle(steps);
    return {
      viewport: { width: innerWidth, height: innerHeight },
      stepsRect: rect(steps),
      stepItemsRect: items.map((li) => ({ text: clean(li.textContent), ...rect(li) })),
      cardRect: rect(card),
      cityLabel: clean(label.textContent),
      cityLabelRect: rect(label),
      band: { top: bandTop, bottom: bandBottom, height: bandBottom - bandTop },
      bandElements: inside,
      bandWaitingAffordances: waiting,
      computed: {
        stepsPaddingBottom: cs.paddingBottom,
        stepsMarginBottom: cs.marginBottom,
        stepsHeight: cs.height,
        simClearance: getComputedStyle(document.documentElement).getPropertyValue(
          "--cn-sim-float-clearance",
        ),
      },
      cssRulesTouchingTrialSteps: rules,
    };
  });
}

/** One evidence file per node. A module-level variable is not shared across Playwright workers, so
 *  a combined file would carry whichever worker happened to finish last — worse than no file. */
function writeArm(arm: string, payload: Record<string, unknown>) {
  writeFileSync(
    // An arm run writes beside the base run, never over it: two readings in one file is how an
    // experiment erases its own control.
    evidencePath(`ord0338-${arm}${process.env.CNX_ORD0338_SUFFIX ?? ""}.json`),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        file: FILE,
        arm,
        head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        run: process.env.CITYNEXUS_E2E_RUN_ID ?? "dev",
        /* The export carries no .git, so the runner's own head reads "unknown"; the tree identity is
           the sha the outer runner was told to export, plus the per-file blob checks it logged. */
        tree_sha: process.env.CNX_TREE_SHA ?? "CNX_TREE_SHA-unset",
        head_as_reported_by_runner: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        tree: "git archive of the tip; key blobs re-hashed against it before the run",
        question: "步骤条与目的地之间那一整块空白是插槽还是留白",
        ...payload,
      },
      null,
      1,
    ),
  );
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("citynexus.locale", "zh-CN");
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/v8/hub", { waitUntil: "load" });
  await page.waitForSelector('[data-testid="trial-setup"]', { timeout: 60_000 });
  await page.waitForSelector('[data-testid="trial-steps"]', { timeout: 30_000 });
  await page.waitForSelector('[data-testid="trial-city"]', { timeout: 30_000 });
});

test("N1 带内没有内容节点，带高可由那一条 padding 派生", async ({ page }) => {
  test.setTimeout(300_000);
  const m = await measure(page);
  writeArm("N1-at-rest", m as Record<string, unknown>);
  expect(m.missing, node("N1", `向导没挂全：${m.missing}`)).toBeUndefined();
  expect(
    m.bandElements.length,
    node("N1", `带里有自带内容的节点，空白不是纯留白：${JSON.stringify(m.bandElements)}`),
  ).toBe(0);
  expect(
    m.band.height > 60,
    node("N1", `带高 ${m.band.height}px，号令者说的那一整块没复现出来`),
  ).toBe(true);
  const pad = parseFloat(m.computed.stepsPaddingBottom);
  const margin = parseFloat(m.computed.stepsMarginBottom);
  expect(
    Math.abs(m.band.height - (pad + margin)) <= 2,
    node("N1", `带高 ${m.band.height} 与 padding-bottom ${pad} + margin-bottom ${margin} 对不上，归属不成立`),
  ).toBe(true);
});

test("N2 只把那一条 padding 置 0，带高正好缩掉那一截（单变量归属）", async ({ page }) => {
  test.setTimeout(300_000);
  const base = await measure(page);
  await page.addStyleTag({ content: ".cn-onboarding .trial-steps { padding-bottom: 0px !important; }" });
  await page.waitForTimeout(250);
  const neutered = await measure(page);
  writeArm("N2-single-variable", {
    base,
    padding_neutered: neutered,
    declared_padding_px: parseFloat(base.computed.stepsPaddingBottom),
    band_shrank_by: base.band.height - neutered.band.height,
    product_bytes_written: 0,
    note: "页面内 addStyleTag，落盘文件一字未动；这一枚只回答『那段空白是不是这条声明撑的』",
  });
  const pad = parseFloat(base.computed.stepsPaddingBottom);
  expect(
    parseFloat(neutered.computed.stepsPaddingBottom),
    node("N2", "addStyleTag 没生效，这一枚臂是空转"),
  ).toBe(0);
  expect(
    Math.abs(base.band.height - neutered.band.height - pad) <= 2,
    node("N2", `带高从 ${base.band.height} 只变到 ${neutered.band.height}，与那条 padding ${pad} 不等量`),
  ).toBe(true);
});

test("N3 网络静默前后带高相同，带内也没有任何「我在等」的节点", async ({ page }) => {
  test.setTimeout(300_000);
  const before = await measure(page);
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(2_000);
  const after = await measure(page);
  writeArm("N3-not-data-gated", {
    before_network_idle: before,
    after_network_idle: after,
    band_height_equal: before.band.height === after.band.height,
    band_height_delta: after.band.height - before.band.height,
    waiting_affordances_in_band: after.bandWaitingAffordances,
  });
  expect(
    Math.abs(after.band.height - before.band.height) <= 2,
    node("N3", `等数据这条不成立：静默前 ${before.band.height}，静默后 ${after.band.height}`),
  ).toBe(true);
  expect(
    after.bandWaitingAffordances.length,
    node("N3", `带里有等待态节点：${JSON.stringify(after.bandWaitingAffordances)}`),
  ).toBe(0);
  expect(
    after.cityLabel,
    node("N3", `带下方第一枚渲染文字不是「目的地」而是「${after.cityLabel}」`),
  ).toContain("目的地");
});

test("N4 人眼看到的顺序与一张带 run id 的截图", async ({ page }) => {
  test.setTimeout(300_000);
  const m = await measure(page);
  const above = m.stepItemsRect.map((s: any) => s.text).join(" | ");
  expect(above, node("N4", `步骤条上方文字异常：${above}`)).toContain("目的地与时间");
  await page.screenshot({
    path: evidencePath(`ui-overnight/ord0338-wizard-gap-${process.env.CITYNEXUS_E2E_RUN_ID ?? "dev"}.png`),
  });
  writeArm("N4-what-the-eye-sees", {
    rendered_above: m.stepItemsRect,
    band: m.band,
    rendered_below: m.cityLabel,
    rendered_below_rect: m.cityLabelRect,
    rule_provenance: m.cssRulesTouchingTrialSteps,
    computed: m.computed,
    band_element_count: m.bandElements.length,
    screenshot: `ord0338-wizard-gap-${process.env.CITYNEXUS_E2E_RUN_ID ?? "dev"}.png`,
  });
});
