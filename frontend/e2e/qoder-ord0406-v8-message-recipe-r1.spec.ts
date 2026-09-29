/**
 * ORD-0406 — the recipe the shell's `.v8-message` was waiting for: how each of its two sites is made
 * to render, read back as the painted sentence rather than an attribute.
 *
 *   site 1 -- `<p className="v8-message" role="status" data-testid="address-no-screen">` is derived
 *             (`deepLink.kind === "unknown" && route === "hub"`), so a URL alone drives it: arm A.
 *   site 2 -- `<div className="v8-message" role="status">{message}</div>` is state written by
 *             `setMessage`. The writer reachable without inventing data is the autonomy control on the
 *             Intelligence screen (a PUT against my own private DB); arm B drives it and also records
 *             what a read that answers 404 paints -- neither site.
 *   arm S  -- proof the page under test is this worktree's: the served HTML has to carry this
 *             checkout's own entry line, and under `npm run dev` the only difference from the file on
 *             disk is vite's injected block. Byte-for-byte equality is claimed only for a static port,
 *             where it can actually be measured (the generator does that one).
 */
import { expect, test, type Page } from "@playwright/test";
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { ensureDemoJourney } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

const DEAD_JOURNEY_ID = "0f0f0f0f-0f0f-4f0f-8f0f-0f0f0f0f0f0f";

function write(name: string, body: unknown) {
  const p = evidencePath("qoder-ord0406-recipe", name + ".json");
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, JSON.stringify(body, null, 1), "utf8");
  console.log("O406R " + name + " " + JSON.stringify(body));
}

const readMessages = (page: Page) =>
  page.evaluate(() => {
    const nav = document.querySelector<HTMLElement>(".v8-mobile-nav");
    const hitLine = nav ? Math.round(nav.getBoundingClientRect().top) : null;
    const els = Array.from(document.querySelectorAll<HTMLElement>(".v8-message"));
    const sentences = els.map((el) => {
      const b = el.getBoundingClientRect();
      const cx = Math.round(b.x + b.width / 2);
      const cy = Math.round(b.y + b.height / 2);
      const top = document.elementFromPoint(cx, cy);
      const range = document.createRange();
      range.selectNodeContents(el);
      const bottoms = Array.from(range.getClientRects()).map((r) => Math.round(r.bottom));
      return {
        text: (el.textContent ?? "").replace(/\s+/g, " ").trim(),
        textLength: (el.textContent ?? "").trim().length,
        documentY: Math.round(b.y + (window.scrollY || 0)),
        testid: el.getAttribute("data-testid"),
        role: el.getAttribute("role"),
        box: { y: Math.round(b.y), bottom: Math.round(b.bottom), h: Math.round(b.height) },
        centre: { x: cx, y: cy },
        centreHitSelf: !!(top && (top === el || el.contains(top))),
        paintedLines: bottoms.length,
        lastLineBottom: bottoms.length ? Math.max(...bottoms) : null,
        aboveNav: hitLine === null ? null : (bottoms.length ? Math.max(...bottoms) : 0) <= hitLine,
        visible: b.height > 0 && getComputedStyle(el).visibility !== "hidden",
      };
    });
    return {
      url: location.href,
      lang: document.documentElement.lang || null,
      hitLine,
      count: els.length,
      sentences,
      scrollY: Math.round(window.scrollY || 0),
      docHeight: Math.round(document.documentElement.scrollHeight),
      shellMounted: !!document.querySelector(".v8-product-shell"),
      bodyChars: (document.body.innerText ?? "").length,
    };
  });

test("O406R arm A — a URL alone renders the address verdict inside .v8-message", async ({ browser }) => {
  for (const arm of [{ locale: "zh-CN", expect: "这个地址没有对应的屏" },
                     { locale: "en", expect: "This address names no screen" }] as const) {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: arm.locale });
    const page = await ctx.newPage();
    await page.addInitScript((l: string) => localStorage.setItem("citynexus.locale", l), arm.locale);
    await ensureDemoJourney(page);
    await page.goto("/v8/nosuchscreen", { waitUntil: "load", timeout: 90_000 });
    await expect(page.getByTestId("today-heading").first()).toBeVisible({ timeout: 25_000 });
    await page.waitForTimeout(1200);
    const read = await readMessages(page);
    const verdict = read.sentences.find((s) => s.testid === "address-no-screen") ?? null;
    write("armA_" + arm.locale, { arm: arm.locale, ...read, verdict });
    expect(read.count, "the verdict must render a .v8-message, arm " + arm.locale).toBeGreaterThan(0);
    expect(verdict?.text ?? "", "the sentence has to be painted text, not an attribute")
      .toContain(arm.expect);
    expect(verdict?.text ?? "").toContain("nosuchscreen");
    expect(verdict?.centreHitSelf, "the verdict line must be hit-testable at its own centre").toBe(true);
    expect(verdict?.aboveNav, "and inside the hittable band, above the fixed bar").toBe(true);
    await ctx.close();
  }
});

test("O406R arm B — the shared banner renders on an action; a 404 read renders neither site", async ({
  browser,
}) => {
  for (const arm of [{ locale: "zh-CN", button: "启用可逆恢复", expect: "自主恢复已启用" },
                     { locale: "en", button: "Enable reversible recovery",
                       expect: "Autonomous recovery is enabled" }] as const) {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: arm.locale });
    const page = await ctx.newPage();
    await page.addInitScript((l: string) => localStorage.setItem("citynexus.locale", l), arm.locale);
    await ensureDemoJourney(page);
    const calls: unknown[] = [];
    page.on("response", async (r) => {
      if (!r.url().includes("agent-policy")) return;
      calls.push({ status: r.status(), method: r.request().method(),
                   body_head: (await r.text().catch(() => "")).slice(0, 200) });
    });
    /* The action arm runs first on purpose: the dead-link visit below writes a journey reference that
       the next boot has to read, which would otherwise describe that read instead of the banner. */
    await page.goto("/v8/intelligence", { waitUntil: "load", timeout: 90_000 });
    const button = page.getByRole("button", { name: arm.button }).first();
    const screen = await page.evaluate(() => ({
      url: location.href,
      hasControlTowerCard: !!document.querySelector("[data-testid='v17-runtime-status']"),
      bodyHead: (document.body.innerText ?? "").replace(/\s+/g, " ").slice(0, 180),
    }));
    await expect(button, "the control that writes the banner must be on screen: " + JSON.stringify(screen))
      .toBeVisible({ timeout: 25_000 });
    await button.click();
    await page.waitForTimeout(3500);
    const beforeScroll = await readMessages(page);
    /* The page is tall and the banner lands above the current scroll position, so a centre hit there
       is impossible: scroll the sentence into the reachable band before judging reachability. */
    const bannerLocator = page.getByRole("status").filter({ hasText: arm.expect }).first();
    await bannerLocator.scrollIntoViewIfNeeded();
    await page.waitForTimeout(600);
    const read = await readMessages(page);
    const banner = read.sentences.find((x) => x.text.includes(arm.expect)) ?? null;
    read.above_viewport_before_scroll = beforeScroll.sentences.length > 0 &&
      (beforeScroll.sentences[0].box.y < 0 || beforeScroll.sentences[0].box.bottom > beforeScroll.hitLine);
    /* The negative half: what does an unanswerable read paint? */
    const deadPage = await ctx.newPage();
    await deadPage.addInitScript((l: string) => localStorage.setItem("citynexus.locale", l), arm.locale);
    const deadResponses: unknown[] = [];
    deadPage.on("response", async (r) => {
      if (!r.url().includes("/api/v1/journeys/")) return;
      deadResponses.push({ status: r.status(), url: r.url().replace(/^https?:\/\/[^/]+/, ""),
                           body_head: (await r.text().catch(() => "")).slice(0, 240) });
    });
    await deadPage.goto("/v8/" + DEAD_JOURNEY_ID, { waitUntil: "load", timeout: 90_000 });
    await deadPage.waitForTimeout(6000);
    const dead = await readMessages(deadPage);
    write("armB_" + arm.locale, { arm: arm.locale, screen, policy_calls: calls, before_scroll: beforeScroll, ...read, banner,
                                  dead_link: { url: dead.url, message_count: dead.count,
                                               shell_mounted: dead.shellMounted,
                                               body_chars: dead.bodyChars,
                                               responses: deadResponses } });
    expect(banner?.text ?? "", "the shared banner must paint its sentence, arm " + arm.locale)
      .toContain(arm.expect);
    expect(banner?.role).toBe("status");
    expect(banner?.centreHitSelf, "and be hit-testable where it paints").toBe(true);
    expect(banner?.visible).toBe(true);
    expect(dead.count,
      "recorded honestly: an unanswerable journey read leaves no .v8-message on screen").toBe(0);
    await ctx.close();
  }
});

test("O406R arm S — the page under test is this worktree's own entry", async ({ page }) => {
  await ensureDemoJourney(page);
  await page.goto("/v8/hub", { waitUntil: "load", timeout: 90_000 });
  const served = await page.evaluate(async () => {
    const res = await fetch("/", { cache: "no-store" });
    return { status: res.status, origin: location.origin, port: location.port,
             text: await res.text() };
  });
  const disk = readFileSync("index.html", "utf-8");
  const sha = (t: string) => createHash("sha1").update(Buffer.from(t, "utf-8")).digest("hex");
  const lines = disk.split("\n");
  const entryLine = 1 + lines.findIndex((l) => l.includes("/src/main.tsx"));
  const injected = served.text.includes("/@vite/client") && served.text.includes("/@react-refresh");
  write("armS", { origin: served.origin, port: served.port, served_status: served.status,
                  served_bytes: Buffer.byteLength(served.text, "utf-8"),
                  disk_bytes: Buffer.byteLength(disk, "utf-8"),
                  served_sha1_over_bytes: sha(served.text), disk_sha1_over_bytes: sha(disk),
                  served_equals_disk: sha(served.text) === sha(disk),
                  entry_line_in_index_html: entryLine,
                  entry_named_by_served_html: served.text.includes("/src/main.tsx"),
                  dev_injected_block: injected,
                  disk_entry_line_text: lines[entryLine - 1].trim() });
  expect(served.status).toBe(200);
  expect(entryLine, "this checkout's index.html has to name the module entry").toBeGreaterThan(0);
  expect(served.text.includes("/src/main.tsx"),
    "and the HTML the browser ran has to carry that same entry").toBe(true);
  expect(injected, "under `npm run dev` the served HTML differs from disk by vite's injected block")
    .toBe(true);
});
