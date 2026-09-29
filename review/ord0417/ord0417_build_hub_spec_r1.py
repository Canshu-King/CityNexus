"""ORD-0417 lane: build the hub-screen gate for the same tap-names-the-stop behaviour.

Why a builder and not a hand-written file: the four measurement helpers (`pickHittablePin`,
`markerCensus`, `controlCensus`, `readGlassName`) and the language-arms table are copied VERBATIM out
of the spec this order already landed (`e2e/qoder-ord0417-tap-names-the-stop.spec.ts`, blob
715fc4e0ffc873b2d56b5d41310548af29d8bc45).  A lane that re-defines the ruler to fit a new screen is not
measurable, so the ruler is physically the same code.

usage: python ord0417_build_hub_spec_r1.py <tip spec file> <out spec file>
"""
import sys

SRC, DST = sys.argv[1], sys.argv[2]
spec = open(SRC, encoding="utf-8").read()

start = spec.index("async function pickHittablePin")
end = spec.index("const rows: Record<string, unknown>[] = [];")
helpers = spec[start:end]
if "readGlassName" not in helpers or "controlCensus" not in helpers:
    raise SystemExit("REFUSE: the helper block did not come out whole")

arms = '''
/**
 * ORD-0417 (hub slice) — the traveller's first screen carries a real map with real pins, and a tap on
 * one of them answered nothing.
 *
 * The commander measured it on the live line at 13:36 (`_mapselect_r1/map_select_r1.json`: six markers,
 * a tap on marker 1 at (192, 736), `changed_markers: []`, `visible_name_leaves_delta: 0`, verdict
 * MAP_CLICK_CHANGED_NOTHING_ON_SCREEN) while the same tap on `/v8/map` names the stop on the glass.
 * The cause was in the code, not in the browser: `MapPanel` binds the pin to
 * `selectRef.current?.(point.id ?? null)` (`frontend/src/components/v8/MapPanel.tsx:382`), and the hub's
 * call site passed `data`, `option` and `onNoLocationChange` only
 * (`frontend/src/app/V8Experience.tsx:3069`) — so the optional call discarded the tap in silence while
 * the marker still advertised `role="button"`, `tabindex="0"` and an `aria-pressed` state.  A control
 * that looks focusable, answers a hit-test and then does nothing is the same defect ORD-0417 was opened
 * for, one screen over.  Nothing anywhere declared the hub map an overview: no comment at the call
 * site, and no spec in `frontend/e2e/` asserts that hub pins are inert.
 *
 * So the hub gets the same linkage the map page has, and this file measures it:
 *   hub-tap-named-{zh,en}    the hub panel's own painted text contains the tapped stop's name;
 *   hub-not-aria-{zh,en}     it reaches the eye as painted text, through a visible box, not an
 *                            attribute a reader recites;
 *   hub-unpicked-{zh,en}     before a tap the hub glass names no stop, so no arm can borrow a label;
 *   hub-pressed-{zh,en}      the pin that was tapped reports its own state flip, which is the proof
 *                            the tap reached the pin and not a neighbour sharing its pixel;
 *   hub-geometry-{w}x{h}-{zh,en}
 *                            the same 768 px reachability census as the map-page file, taken twice on
 *                            one scroll offset: the linkage may not cost the hub a reachable control,
 *                            may not grow the band past the 16 px `fitBounds` already paid for, may not
 *                            add a control, and may not clip the name.
 *
 * No response body is rewritten, nothing is mocked, no arm is skipped. Assertions read rendered text,
 * never a data attribute.
 */

const FILE = "e2e/qoder-ord0417-hub-tap-names-the-stop.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const RUN = process.env.CITYNEXUS_E2E_RUN_ID ?? "local";

/* Copied from the map-page file on purpose: same floor, same shapes, same safety gap, same arms. */
const HIT_FLOOR = 768;
const SHAPES: Array<[number, number]> = [[390, 844], [320, 653]];
const ARMS = [
  { locale: "zh", lead: "图上选中的这一站" },
  { locale: "en", lead: "Selected on the map" },
] as const;
const SAFETY_GAP_PX = 16;

async function enterHub(page: Page, arm: (typeof ARMS)[number] | null = null): Promise<void> {
  /* Language before the app's first script, exactly as the map-page file does it, and the journey id
     the seed persisted is never cleared away. */
  if (arm) {
    await page.addInitScript(
      (loc) => {
        try {
          localStorage.setItem("citynexus.locale", loc);
        } catch {}
      },
      arm.locale === "zh" ? "zh-CN" : "en",
    );
  }
  await ensureDemoJourney(page);
  await openScreen(page, "/v8/hub", ["today-heading", "today-attention"]);
  await expect(page.getByTestId("v8-maplibre-panel").first()).toBeVisible({ timeout: 25_000 });
  await page.waitForTimeout(1_500);
}

'''

tail = '''
const rows: Record<string, unknown>[] = [];
const push = (arm: string, v: Record<string, unknown>) => {
  rows.push({ arm, ...v });
  console.log(`${FILE} :: ${arm} — ${JSON.stringify(v)}`);
};

for (const arm of ARMS) {
  test(`hub-tap-named-${arm.locale} — a tap on a hub pin names that stop on the hub's own glass`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await enterHub(page, arm);
    const { census, target } = await pickHittablePin(page);
    expect(
      target,
      node("H1", `${arm.locale}: the hub put no pin on the map that answers a hit-test at its own centre: ${JSON.stringify(census.pins.map((p) => [p.painted, p.centre, p.lands_on_pin]))}`),
    ).not.toBeNull();
    await page.mouse.click(target!.centre[0], target!.centre[1]);
    await page.waitForTimeout(1_800);
    const glass = await readGlassName(page);
    const shot = evidencePath("ord0417-hub", `${RUN}_tap_named_${arm.locale}.png`);
    await page.screenshot({ path: shot });
    push(`hub-tap-named-${arm.locale}`, {
      tapped: { painted: target!.painted, aria: target!.aria, centre: target!.centre },
      glass,
      names_tapped_stop: glass.present && !!target!.aria && String(glass.painted ?? "").includes(target!.aria),
      lead_authored: arm.lead,
      lead_painted: glass.present && String(glass.painted ?? "").includes(arm.lead),
      shot,
    });
    expect(
      glass.present,
      node("H1", `${arm.locale}: after tapping hub pin ${target!.painted} the hub panel painted no name at all (panel text: ${JSON.stringify(glass.panel_text.slice(0, 160))})`),
    ).toBe(true);
    expect(
      glass.panel_text,
      node("H1", `${arm.locale}: the hub glass says ${JSON.stringify(glass.panel_text.slice(0, 160))} but never names the tapped stop ${JSON.stringify(target!.aria)}`),
    ).toContain(target!.aria);
    expect(
      glass.panel_text,
      node("H1", `${arm.locale}: the sentence on the hub is not the dictionary's — expected the lead-in ${JSON.stringify(arm.lead)} in ${JSON.stringify(glass.panel_text.slice(0, 160))}`),
    ).toContain(arm.lead);
  });
}

for (const arm of ARMS) {
  test(`hub-not-aria-${arm.locale} — the hub names the stop where the eye can see it`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await enterHub(page, arm);
    const { target } = await pickHittablePin(page);
    expect(target, node("H2", `${arm.locale}: no hittable hub pin to tap`)).not.toBeNull();
    await page.mouse.click(target!.centre[0], target!.centre[1]);
    await page.waitForTimeout(1_800);
    const cell = await page.evaluate((name: string) => {
      const panel = document.querySelector<HTMLElement>(".v8-map-panel");
      const hits = Array.from(panel?.querySelectorAll<HTMLElement>("*") ?? []).filter(
        (el) => (el.innerText ?? "").includes(name) && el.children.length === 0,
      );
      const el = hits[0] ?? null;
      if (!el) return { found: false as const, leaves: hits.length };
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      const cls = el.className ?? "";
      return {
        found: true as const,
        leaves: hits.length,
        tag: el.tagName.toLowerCase(),
        box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
        display: cs.display,
        visibility: cs.visibility,
        opacity: cs.opacity,
        screen_reader_only: String(cls).includes("v8-sr-only"),
        inside_panel: !!el.closest(".v8-map-panel"),
        text: (el.innerText ?? "").replace(/\\s+/g, " ").trim().slice(0, 120),
      };
    }, target!.aria);
    const shot = evidencePath("ord0417-hub", `${RUN}_not_aria_${arm.locale}.png`);
    await page.locator(".v8-map-panel").first().screenshot({ path: shot });
    push(`hub-not-aria-${arm.locale}`, { cell, shot });
    expect(cell.found, node("H2", `${arm.locale}: the tapped stop's name appears nowhere painted on the hub panel — ${JSON.stringify(cell)}`)).toBe(true);
    expect(cell.screen_reader_only, node("H2", `${arm.locale}: the name is only in a screen-reader layer: ${JSON.stringify(cell)}`)).toBe(false);
    expect([cell.display, cell.visibility, Number(cell.opacity)], node("H2", `${arm.locale}: the naming element is not visible: ${JSON.stringify(cell)}`)).toEqual(["inline", "visible", 1]);
    expect(cell.box![2], node("H2", `${arm.locale}: zero-width naming element: ${JSON.stringify(cell.box)}`)).toBeGreaterThan(0);
    expect(cell.inside_panel, node("H2", `${arm.locale}: the name is painted outside the map panel: ${JSON.stringify(cell)}`)).toBe(true);
  });
}

for (const arm of ARMS) {
  test(`hub-unpicked-${arm.locale} — before a tap the hub glass names no stop`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await enterHub(page, arm);
    const before = await readGlassName(page);
    const pressed = await page.evaluate(() =>
      Array.from(document.querySelectorAll<HTMLElement>(".v8-map-panel .v9-map-marker")).map((el) =>
        el.getAttribute("aria-pressed"),
      ),
    );
    push(`hub-unpicked-${arm.locale}`, { glass: before, aria_pressed_before: pressed });
    expect(
      before.present,
      node("H3", `${arm.locale}: the hub already named a stop before anything was picked (${JSON.stringify(before.panel_text.slice(0, 120))})`),
    ).toBe(false);
    expect(pressed, node("H3", `${arm.locale}: a hub pin claims to be selected before any tap: ${JSON.stringify(pressed)}`)).not.toContain("true");
  });
}

for (const arm of ARMS) {
  test(`hub-pressed-${arm.locale} — the pin that was tapped says so in its own state`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await enterHub(page, arm);
    const { target } = await pickHittablePin(page);
    expect(target, node("H4", `${arm.locale}: no hittable hub pin`)).not.toBeNull();
    await page.mouse.click(target!.centre[0], target!.centre[1]);
    await page.waitForTimeout(1_800);
    const states = await page.evaluate(() =>
      Array.from(document.querySelectorAll<HTMLElement>(".v8-map-panel .v9-map-marker")).map((el) => ({
        painted: (el.textContent ?? "").trim(),
        aria: el.getAttribute("aria-label") ?? "",
        pressed: el.getAttribute("aria-pressed"),
      })),
    );
    const mine = states.find((s) => s.painted === target!.painted);
    push(`hub-pressed-${arm.locale}`, { tapped: target!.painted, states });
    expect(
      mine?.pressed,
      node("H4", `${arm.locale}: hub pin ${target!.painted} was tapped but still reports aria-pressed=${JSON.stringify(mine?.pressed)}; states ${JSON.stringify(states)}`),
    ).toBe("true");
    expect(
      states.filter((s) => s.pressed === "true").length,
      node("H4", `${arm.locale}: more than one hub pin reports a selection: ${JSON.stringify(states)}`),
    ).toBe(1);
    expect(
      states.length,
      node("H4", `${arm.locale}: the hub panel exposes ${states.length} markers, too few to tell a selection apart: ${JSON.stringify(states)}`),
    ).toBeGreaterThanOrEqual(2);
  });
}

for (const [w, h] of SHAPES) {
  for (const arm of ARMS) {
    test(`hub-geometry-${w}x${h}-${arm.locale} — the linkage costs the hub no reachable control`, async ({
      page,
    }) => {
      await page.setViewportSize({ width: w, height: h });
      await enterHub(page, arm);
      const idleControls = await controlCensus(page);
      const { census: idlePins, target } = await pickHittablePin(page);
      expect(target, node("H5", `${w}x${h}/${arm.locale}: no hittable hub pin to tap at this shape`)).not.toBeNull();
      await page.mouse.click(target!.centre[0], target!.centre[1]);
      await page.waitForTimeout(1_800);
      const glass = await readGlassName(page);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(900);
      const liveControls = await controlCensus(page);
      const liveBand = await page.evaluate(() => {
        const b = document.querySelector<HTMLElement>(".v8-map-overlay-stack")?.getBoundingClientRect();
        return b ? [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)] : null;
      });
      const reachable = (list: typeof idleControls) =>
        list.filter((c) => c.hit_test && c.centre_above_floor && c.in_viewport).map((c) => c.key);
      const beforeReachable = reachable(idleControls);
      const afterReachable = new Set(reachable(liveControls));
      const lost = beforeReachable.filter((k) => !afterReachable.has(k));
      const bandGrowth =
        idlePins.band_box && liveBand ? liveBand[3] - idlePins.band_box[3] : null;
      const clip = await page.evaluate(() => {
        const el = document.querySelector<HTMLElement>(".v8-map-panel .v8-map-selected-stop");
        if (!el) return null;
        const r = el.getBoundingClientRect();
        const host = el.closest(".v8-map-caption")?.getBoundingClientRect();
        return {
          box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
          scroll_w: el.scrollWidth,
          client_w: el.clientWidth,
          outside_caption: host ? r.right > host.right + 1 || r.bottom > host.bottom + 1 : null,
        };
      });
      const shot = evidencePath("ord0417-hub", `${RUN}_geometry_${w}x${h}_${arm.locale}.png`);
      await page.screenshot({ path: shot });
      push(`hub-geometry-${w}x${h}-${arm.locale}`, {
        viewport: [w, h],
        hit_floor_px: HIT_FLOOR,
        safety_gap_px: SAFETY_GAP_PX,
        controls_idle: idleControls.length,
        controls_with_selection: liveControls.length,
        reachable_idle: beforeReachable.length,
        reachable_with_selection: afterReachable.size,
        lost,
        band_box_idle: idlePins.band_box,
        band_box_with_selection: liveBand,
        band_growth_px: bandGrowth,
        name_painted: glass.present,
        cell: clip,
        shot,
      });
      expect(
        glass.present,
        node("H5", `${w}x${h}/${arm.locale}: no name was painted on the hub glass at all`),
      ).toBe(true);
      expect(
        bandGrowth,
        node("H5", `${w}x${h}/${arm.locale}: the band grew ${bandGrowth} px past the ${SAFETY_GAP_PX} px safety gap fitBounds reserved: ${JSON.stringify(idlePins.band_box)} -> ${JSON.stringify(liveBand)}`),
      ).toBeLessThanOrEqual(SAFETY_GAP_PX);
      expect(lost, node("H5", `${w}x${h}/${arm.locale} lost a reachable control: ${JSON.stringify(lost)}`)).toEqual([]);
      expect(
        liveControls.length,
        node("H5", `${w}x${h}/${arm.locale}: the linkage must not add a control — ${idleControls.length} -> ${liveControls.length}`),
      ).toBe(idleControls.length);
      expect(clip, node("H5", `${w}x${h}/${arm.locale}: the naming cell vanished from the hub`)).not.toBeNull();
      expect(
        clip!.outside_caption,
        node("H5", `${w}x${h}/${arm.locale}: the name is painted outside its caption box: ${JSON.stringify(clip)}`),
      ).toBe(false);
      expect(
        clip!.scroll_w - clip!.client_w,
        node("H5", `${w}x${h}/${arm.locale}: the name is clipped inside its own box: ${JSON.stringify(clip)}`),
      ).toBeLessThanOrEqual(1);
    });
  }
}

test.afterAll(() => {
  writeFileSync(
    evidencePath("ord0417-hub", `${RUN}_readings.json`),
    JSON.stringify({ file: FILE, run_id: RUN, hit_floor_px: HIT_FLOOR, shapes: SHAPES, rows }, null, 1),
  );
});
'''

body = (
    "import { expect, test, type Page } from \"@playwright/test\";\n"
    "import { writeFileSync } from \"node:fs\";\n"
    "import { ensureDemoJourney, openScreen } from \"./_qoderShellSeed\";\n"
    "import { evidencePath } from \"./_qoderEvidence\";\n"
    + arms
    + helpers
    + tail
)
open(DST, "w", encoding="utf-8", newline="\n").write(body)
print(f"wrote {DST} ({len(body.encode('utf-8'))} bytes)")
